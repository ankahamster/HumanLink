"""Bridge between the gateway and the local Hermes CLI."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

try:
    from .config import Settings
    from .models import HermesChatRequest, HermesChatResponse
except ImportError:  # pragma: no cover - direct module execution fallback
    from config import Settings
    from models import HermesChatRequest, HermesChatResponse


SYSTEM_PROMPT = """You are Hermes, a natural Chinese-speaking AI payment assistant inside the HumanlinkPay demo.

You must respond with a single JSON object and nothing else.

Required JSON schema:
{
  "assistant_message": "string",
  "payment_detected": true or false,
  "payment_intent": {
    "userId": "demo-user",
    "to": "0x...",
    "amount": "0.0011",
    "token": "ETH",
    "purpose": "Buy API access"
  } or null,
  "missing_fields": ["to", "amount", "purpose"] or [],
  "should_autofill": true or false
}

Rules:
- Chat naturally in Chinese.
- If the user is only greeting, asking who you are, or making small talk, answer naturally and set payment_detected=false.
- Only set payment_detected=true when the user clearly expresses an intent to pay, transfer, send, or authorize a payment.
- Extract payment fields from the conversation when present.
- If a payment is intended but required fields are missing, set payment_detected=true, set payment_intent to the partial object when possible, list the missing fields, and ask for the missing information naturally.
- When token is not specified, use ETH.
- Keep userId as demo-user unless the conversation explicitly provides another user id.
- Never invent a wallet address or amount.
- The HumanlinkPay risk threshold is 0.001 ETH. You may mention that naturally when helpful, but do not execute the payment yourself.
"""


def _format_messages(messages: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for message in messages:
        role = message.get("role", "user")
        content = (message.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines)


def _read_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        cleaned_value = value.strip()
        if len(cleaned_value) >= 2 and cleaned_value[0] == cleaned_value[-1] and cleaned_value[0] in {"'", '"'}:
            cleaned_value = cleaned_value[1:-1]
        values[key.strip()] = cleaned_value
    return values


def _debug_report(hypothesis_id: str, location: str, msg: str, data: dict[str, Any]) -> None:
    # #region debug-point hermes-empty-stdout
    env_path = Path(__file__).resolve().parents[1] / ".dbg" / "hermes-empty-stdout.env"
    debug_server_url = "http://127.0.0.1:7777/event"
    debug_session_id = "hermes-empty-stdout"
    try:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("DEBUG_SERVER_URL="):
                    debug_server_url = line.split("=", 1)[1].strip()
                elif line.startswith("DEBUG_SESSION_ID="):
                    debug_session_id = line.split("=", 1)[1].strip()
        payload = {
            "sessionId": debug_session_id,
            "runId": "pre-fix",
            "hypothesisId": hypothesis_id,
            "location": location,
            "msg": f"[DEBUG] {msg}",
            "data": data,
        }
        request = urllib.request.Request(
            debug_server_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(request, timeout=1).read()
    except Exception:
        pass
    # #endregion


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(raw_text):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(raw_text[index:])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue
    raise ValueError(f"Hermes output is not valid JSON: {raw_text!r}")


class HermesBridge:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.runtime_home = settings.runtime_dir / "hermes_home"
        self.runtime_home.mkdir(parents=True, exist_ok=True)
        (self.runtime_home / "logs").mkdir(parents=True, exist_ok=True)
        (self.runtime_home / "sessions").mkdir(parents=True, exist_ok=True)

    def chat(self, request: HermesChatRequest) -> HermesChatResponse:
        transcript = _format_messages([message.model_dump(mode="json") for message in request.messages])
        user_context = f"Current user id: {request.user_id or self.settings.default_user_id}"
        prompt = (
            f"{SYSTEM_PROMPT}\n\n"
            f"{user_context}\n"
            f"Conversation transcript:\n{transcript}\n"
        )

        command = [
            self.settings.hermes_command,
            "--provider",
            self.settings.hermes_provider,
            "-m",
            self.settings.hermes_model,
            "-z",
            prompt,
        ]

        env = os.environ.copy()
        hermes_env = _read_env_file(Path.home() / ".hermes" / ".env")
        env.update(hermes_env)
        env["HERMES_HOME"] = str(self.runtime_home)
        _debug_report(
            "A",
            "hermes_bridge.py:chat:pre-run",
            "Prepared Hermes subprocess inputs",
            {
                "command": command,
                "prompt_length": len(prompt),
                "transcript_length": len(transcript),
                "runtime_home": str(self.runtime_home),
                "cwd": os.getcwd(),
                "env_keys_present": sorted(key for key in hermes_env.keys() if "KEY" in key or "TOKEN" in key),
            },
        )

        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=self.settings.hermes_timeout_seconds,
            check=False,
            env=env,
        )
        _debug_report(
            "B",
            "hermes_bridge.py:chat:post-run",
            "Hermes subprocess completed",
            {
                "returncode": completed.returncode,
                "stdout_length": len(completed.stdout or ""),
                "stderr_length": len(completed.stderr or ""),
                "stdout_preview": (completed.stdout or "")[:400],
                "stderr_preview": (completed.stderr or "")[:400],
            },
        )
        if completed.returncode != 0:
            stderr = completed.stderr.strip() or completed.stdout.strip() or "Hermes command failed"
            raise RuntimeError(stderr)

        raw_stdout = completed.stdout.strip()
        _debug_report(
            "C",
            "hermes_bridge.py:chat:pre-parse",
            "Parsing Hermes stdout as JSON",
            {
                "raw_stdout_length": len(raw_stdout),
                "raw_stdout_preview": raw_stdout[:400],
            },
        )
        parsed = _extract_json_object(raw_stdout)
        return HermesChatResponse.model_validate(parsed)
