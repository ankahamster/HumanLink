"""Minimal FastAPI gateway for the HumanlinkPay demo."""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
import webbrowser
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

try:
    from .audit import AuditLogger
    from .config import Settings
    from .hermes_bridge import HermesBridge
    from .models import (
        AssertionSummary,
        AuditRecord,
        CanonicalPaymentIntent,
        HermesChatRequest,
        HermesChatResponse,
        PaymentIntent,
        PaymentPreviewResponse,
        PaymentResponse,
        PolicyDecision,
    )
    from .payment_executor import create_payment_executor
    from .policy import PaymentPolicyEngine
    from .sdk_client import HumanLinkSDKClient, SDKClientError
except ImportError:  # pragma: no cover - direct module execution fallback
    from audit import AuditLogger
    from config import Settings
    from hermes_bridge import HermesBridge
    from models import (
        AssertionSummary,
        AuditRecord,
        CanonicalPaymentIntent,
        HermesChatRequest,
        HermesChatResponse,
        PaymentIntent,
        PaymentPreviewResponse,
        PaymentResponse,
        PolicyDecision,
    )
    from payment_executor import create_payment_executor
    from policy import PaymentPolicyEngine
    from sdk_client import HumanLinkSDKClient, SDKClientError


settings = Settings()
FRONTEND_INDEX = Path(__file__).resolve().parents[1] / "frontend" / "index.html"
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}
policy_engine = PaymentPolicyEngine(
    threshold_eth=settings.payment_threshold_eth,
    allowed_recipients=settings.allowed_recipients,
)
sdk_client = HumanLinkSDKClient(settings.sdk_base_url)
audit_logger = AuditLogger(settings.audit_log_path)
payment_executor = create_payment_executor(settings)
hermes_bridge = HermesBridge(settings)
WAIT_TOKEN_TTL_SECONDS = 600
authorized_wait_tokens: dict[str, float] = {}


def canonicalize_intent(intent: PaymentIntent) -> CanonicalPaymentIntent:
    return CanonicalPaymentIntent(
        user_id=intent.user_id,
        to=intent.to,
        amount=intent.amount,
        token=intent.token,
        purpose=intent.purpose,
        deadline=intent.deadline,
        nonce=intent.nonce,
    )


def compute_action_hash(intent: CanonicalPaymentIntent) -> str:
    payload = json.dumps(intent.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_record_url(sdk_base_url: str, audit_session_id: str) -> str:
    return f"{sdk_base_url}/ui/humanlink_record?audit_session_id={audit_session_id}"


def build_demo_url() -> str:
    return f"http://{settings.host}:{settings.port}/ui/payment-demo"


def prune_wait_tokens() -> None:
    now = time.time()
    expired = [token for token, expires_at in authorized_wait_tokens.items() if expires_at <= now]
    for token in expired:
        authorized_wait_tokens.pop(token, None)


def issue_wait_token() -> str:
    prune_wait_tokens()
    token = f"record-{secrets.token_urlsafe(18)}"
    authorized_wait_tokens[token] = time.time() + WAIT_TOKEN_TTL_SECONDS
    return token


def is_valid_wait_token(token: str | None) -> bool:
    if not token:
        return False
    prune_wait_tokens()
    expires_at = authorized_wait_tokens.get(token)
    return bool(expires_at and expires_at > time.time())


def validate_assertion(
    *,
    assertion: dict,
    session_id: str,
    expected_action_hash: str,
) -> None:
    actual_action_hash = assertion.get("challenge", {}).get("action_hash")
    if actual_action_hash != expected_action_hash:
        raise HTTPException(
            status_code=502,
            detail={
                "error": "Assertion action hash mismatch",
                "expected_action_hash": expected_action_hash,
                "actual_action_hash": actual_action_hash,
                "session_id": session_id,
            },
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.ensure_runtime_dirs()
    if settings.auto_open_demo_ui:
        threading.Timer(1.0, lambda: webbrowser.open(build_demo_url(), new=2, autoraise=True)).start()
    yield


app = FastAPI(
    title="HumanlinkPay Gateway",
    version="0.1.0",
    description="Minimal payment gateway skeleton for the HumanlinkPay demo",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": settings.app_name,
        "sdk_base_url": settings.sdk_base_url,
        "execution_mode": settings.execution_mode,
    }


@app.get("/ui/payment-demo")
async def payment_demo() -> FileResponse:
    if not FRONTEND_INDEX.exists():
        raise HTTPException(status_code=404, detail="Payment demo UI not found")
    return FileResponse(FRONTEND_INDEX, headers=NO_CACHE_HEADERS)


@app.get("/ui/waiting-humanlink-record", response_class=HTMLResponse)
async def waiting_humanlink_record(token: str | None = None) -> HTMLResponse:
    if not is_valid_wait_token(token):
        return HTMLResponse(
            """
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <title>无有效 HumanLink 授权</title>
  </head>
  <body>
    <script>
      window.setTimeout(() => {
        try {
          window.close();
        } catch {}
      }, 0);
    </script>
    <p>Invalid HumanLink wait token.</p>
  </body>
</html>
            """,
            headers=NO_CACHE_HEADERS,
        )
    return HTMLResponse(
        """
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>等待 HumanLink 审计页</title>
    <style>
      body {
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        background: #0b1020;
        color: #eef3ff;
        font-family: Inter, system-ui, sans-serif;
      }
      .card {
        width: min(520px, calc(100vw - 32px));
        padding: 28px;
        border-radius: 20px;
        background: #121933;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 18px 40px rgba(0,0,0,0.28);
      }
      h1 { margin-top: 0; font-size: 24px; }
      p { color: #9fb0d9; line-height: 1.7; }
      .countdown {
        color: #ffce52;
        font-weight: 700;
      }
    </style>
  </head>
  <body>
    <div class="card">
      <h1>等待 HumanLink 审计页</h1>
      <p>Gateway 已触发 HumanLink SDK。请在设备上完成指纹授权，成功后这个页面会自动跳转到对应的审计记录页面。</p>
      <p id="countdown" class="countdown">请在 30 秒内完成授权，页面会持续等待并在拿到审计链接后自动跳转。</p>
    </div>
    <script>
      const params = new URLSearchParams(window.location.search);
      const token = params.get("token");
      const countdownEl = document.getElementById("countdown");
      let remainingSeconds = 30;

      function storageKey() {
        return token ? `humanlinkpay-record-url:${token}` : "";
      }

      function renderCountdown() {
        if (remainingSeconds > 0) {
          countdownEl.textContent = `请在 ${remainingSeconds} 秒内完成授权，页面会持续等待并在拿到审计链接后自动跳转。`;
          return;
        }
        countdownEl.textContent = "已等待 30 秒。如果设备侧仍在处理中，请继续完成授权；拿到审计链接后这里会自动跳转。";
      }

      function redirectIfReady() {
        const key = storageKey();
        if (!key) {
          return false;
        }
        const raw = window.localStorage.getItem(key);
        if (!raw) {
          return false;
        }
        try {
          const payload = JSON.parse(raw);
          if (payload && payload.url) {
            window.localStorage.removeItem(key);
            window.location.replace(payload.url);
            return true;
          }
        } catch {}
        return false;
      }

      renderCountdown();
      const countdownTimer = window.setInterval(() => {
        remainingSeconds = Math.max(remainingSeconds - 1, 0);
        renderCountdown();
      }, 1000);

      const redirectTimer = window.setInterval(() => {
        redirectIfReady();
      }, 500);

      window.addEventListener("storage", () => {
        redirectIfReady();
      });

      window.addEventListener("beforeunload", () => {
        window.clearInterval(countdownTimer);
        window.clearInterval(redirectTimer);
      });
    </script>
  </body>
</html>
        """,
        headers=NO_CACHE_HEADERS,
    )


@app.post("/api/hermes/chat", response_model=HermesChatResponse)
async def hermes_chat(request: HermesChatRequest) -> HermesChatResponse:
    try:
        return hermes_bridge.chat(request)
    except Exception as exc:
        raise HTTPException(status_code=502, detail={"error": f"Hermes chat failed: {exc}"}) from exc


@app.post("/api/pay/preview", response_model=PaymentPreviewResponse)
async def preview_payment(intent: PaymentIntent) -> PaymentPreviewResponse:
    canonical_intent = canonicalize_intent(intent)
    action_hash = compute_action_hash(canonical_intent)
    policy_result = policy_engine.evaluate(intent)
    return PaymentPreviewResponse(
        decision=policy_result.decision,
        reason=policy_result.reason,
        action_hash=action_hash,
        canonicalIntent=canonical_intent,
        recordWaitToken=issue_wait_token() if policy_result.decision == PolicyDecision.REQUIRE_HL else None,
    )


@app.post("/api/pay", response_model=PaymentResponse)
async def create_payment(intent: PaymentIntent) -> PaymentResponse:
    canonical_intent = canonicalize_intent(intent)
    action_hash = compute_action_hash(canonical_intent)
    policy_result = policy_engine.evaluate(intent)

    assertion_summary = None
    execution_result = None

    if policy_result.decision == PolicyDecision.REQUIRE_HL:
        display_title = "Agent Payment Authorization"
        display_summary = (
            f"Send {canonical_intent.amount} {canonical_intent.token} "
            f"to {canonical_intent.to} for {canonical_intent.purpose}"
        )

        try:
            challenge_response = await sdk_client.create_challenge(
                intent=canonical_intent,
                action_hash=action_hash,
                display_title=display_title,
                display_summary=display_summary,
                user_id=canonical_intent.user_id or settings.default_user_id,
                origin=settings.origin,
            )
            action_hash = challenge_response.get("challenge", {}).get("action_hash", action_hash)
            auth_session_id = challenge_response["session_id"]
            await sdk_client.execute_authentication(auth_session_id)
            status_response = await sdk_client.wait_for_completion(auth_session_id)
            assertion = status_response.get("assertion")
            if not assertion:
                raise SDKClientError("SDK completed without returning an assertion")
            validate_assertion(
                assertion=assertion,
                session_id=auth_session_id,
                expected_action_hash=action_hash,
            )

            audit_session = await sdk_client.create_audit_session(
                assertion=assertion,
                action="payment.transfer",
                source="humanlinkpay-gateway",
                auth_session_id=auth_session_id,
            )
            audit_session_id = audit_session["audit_session_id"]
            assertion_summary = AssertionSummary(
                session_id=auth_session_id,
                audit_session_id=audit_session_id,
                assertion_id=assertion["id"],
                action_hash=action_hash,
                device_did=assertion.get("device", {}).get("id"),
                humanlink_record_url=build_record_url(settings.sdk_base_url, audit_session_id),
            )
        except SDKClientError as exc:
            raise HTTPException(status_code=502, detail={"error": str(exc), "action_hash": action_hash}) from exc

    if policy_result.decision in {PolicyDecision.ALLOW, PolicyDecision.REQUIRE_HL}:
        try:
            execution_result = payment_executor.execute(canonical_intent, action_hash)
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail={"error": f"Payment execution failed: {exc}", "action_hash": action_hash},
            ) from exc

    response = PaymentResponse(
        decision=policy_result.decision,
        reason=policy_result.reason,
        action_hash=action_hash,
        canonicalIntent=canonical_intent,
        assertion=assertion_summary,
        execution=execution_result,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    audit_logger.write(
        AuditRecord(
            created_at=response.created_at,
            decision=response.decision,
            reason=response.reason,
            action_hash=response.action_hash,
            canonical_intent=response.canonical_intent.model_dump(mode="json"),
            assertion=response.assertion.model_dump(mode="json") if response.assertion else None,
            execution=response.execution.model_dump(mode="json") if response.execution else None,
        )
    )

    return response
