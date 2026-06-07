"""Minimal Hermes adapter for forwarding payment intents to HumanlinkPay gateway."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
import webbrowser
from datetime import datetime, timedelta, timezone
from typing import Any


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Forward structured Hermes payment arguments to the HumanlinkPay gateway"
    )
    parser.add_argument("--gateway", default="http://127.0.0.1:8787/api/pay", help="Gateway /api/pay URL")
    parser.add_argument("--json-input", help="Structured Hermes tool arguments as a JSON string")
    parser.add_argument(
        "--stdin-json",
        action="store_true",
        help="Read structured Hermes tool arguments from stdin as JSON",
    )
    parser.add_argument("--user-id", default="demo-user", help="Default user id")
    parser.add_argument("--to", help="Recipient wallet address")
    parser.add_argument("--amount", help="Amount in ETH")
    parser.add_argument("--token", default="ETH", help="Token symbol")
    parser.add_argument("--purpose", help="Payment purpose")
    parser.add_argument("--deadline-minutes", type=int, default=10, help="Deadline offset in minutes")
    parser.add_argument("--nonce", help="Optional nonce override")
    parser.add_argument(
        "--no-open-record",
        action="store_true",
        help="Do not automatically open the HumanLink audit record page when present",
    )
    return parser


def load_structured_args(args: argparse.Namespace) -> dict[str, Any]:
    if args.json_input:
        return json.loads(args.json_input)
    if args.stdin_json:
        raw = sys.stdin.read().strip()
        if not raw:
            raise ValueError("Expected JSON on stdin")
        return json.loads(raw)
    return {}


def choose_value(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def build_payment_intent(args: argparse.Namespace, structured: dict[str, Any]) -> dict[str, Any]:
    user_id = choose_value(structured.get("userId"), structured.get("user_id"), args.user_id)
    recipient = choose_value(structured.get("to"), structured.get("recipient"), args.to)
    amount = choose_value(structured.get("amount"), args.amount)
    token = choose_value(structured.get("token"), args.token)
    purpose = choose_value(
        structured.get("purpose"),
        structured.get("description"),
        structured.get("summary"),
        args.purpose,
    )
    deadline = choose_value(
        structured.get("deadline"),
        (
            datetime.now(timezone.utc) + timedelta(minutes=args.deadline_minutes)
        ).isoformat(),
    )
    nonce = choose_value(structured.get("nonce"), args.nonce, str(uuid.uuid4()))

    missing = [
        field
        for field, value in {"to": recipient, "amount": amount, "purpose": purpose}.items()
        if value is None
    ]
    if missing:
        raise ValueError(f"Missing required payment fields: {', '.join(missing)}")

    return {
        "userId": user_id,
        "to": recipient,
        "amount": str(amount),
        "token": token,
        "purpose": purpose,
        "deadline": deadline,
        "nonce": nonce,
    }


def call_gateway(gateway_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        gateway_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def format_hermes_response(result: dict[str, Any]) -> dict[str, Any]:
    assertion = result.get("assertion") or {}
    execution = result.get("execution") or {}
    canonical_intent = result.get("canonicalIntent") or {}
    decision = result.get("decision")

    summary_parts = [
        f"decision={decision}",
        result.get("reason", ""),
    ]
    if execution.get("tx_hash"):
        summary_parts.append(f"tx={execution['tx_hash']}")

    return {
        "ok": decision in {"ALLOW", "REQUIRE_HL"},
        "summary": " | ".join(part for part in summary_parts if part),
        "decision": decision,
        "requires_humanlink": decision == "REQUIRE_HL",
        "payment_intent": canonical_intent,
        "humanlink_record_url": assertion.get("humanlink_record_url"),
        "tx_hash": execution.get("tx_hash"),
        "execution_mode": execution.get("mode"),
        "raw": result,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        structured = load_structured_args(args)
        payload = build_payment_intent(args, structured)
    except (ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2

    try:
        result = call_gateway(args.gateway, payload)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(json.dumps({"ok": False, "error": "Gateway request failed", "detail": detail}), file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(json.dumps({"ok": False, "error": f"Gateway unavailable: {exc}"}), file=sys.stderr)
        return 1

    formatted = format_hermes_response(result)
    print(json.dumps(formatted, indent=2, ensure_ascii=False))

    record_url = formatted.get("humanlink_record_url")
    if record_url and not args.no_open_record:
        try:
            webbrowser.open(record_url, new=2, autoraise=True)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
