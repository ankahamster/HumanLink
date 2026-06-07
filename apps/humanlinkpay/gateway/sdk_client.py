"""HTTP client for talking to the local HumanLink SDK daemon."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

try:
    from .models import CanonicalPaymentIntent
except ImportError:  # pragma: no cover - direct module execution fallback
    from models import CanonicalPaymentIntent


class SDKClientError(RuntimeError):
    """Raised when the SDK daemon returns an error or times out."""


class HumanLinkSDKClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def create_challenge(
        self,
        *,
        intent: CanonicalPaymentIntent,
        action_hash: str,
        display_title: str,
        display_summary: str,
        user_id: str,
        origin: str,
    ) -> dict[str, Any]:
        payload = {
            "action": "payment.transfer",
            "action_params": {
                "payment_intent": intent.model_dump(mode="json"),
                "action_hash": action_hash,
            },
            "display_title": display_title,
            "display_summary": display_summary,
            "risk": "high",
            "origin": origin,
            "user_id": user_id,
        }
        data = await self._request_json("POST", "/auth/challenge", json=payload)
        return data

    async def execute_authentication(self, session_id: str) -> None:
        await self._request_json("POST", f"/auth/execute/{session_id}")

    async def wait_for_completion(
        self,
        session_id: str,
        *,
        timeout_seconds: float = 45.0,
        poll_interval_seconds: float = 1.0,
    ) -> dict[str, Any]:
        elapsed = 0.0
        while elapsed <= timeout_seconds:
            data = await self._request_json("GET", f"/auth/status/{session_id}")
            status = data.get("status")
            if status == "completed":
                return data
            if status == "failed":
                error = data.get("error") or "HumanLink authentication failed"
                raise SDKClientError(error)
            await asyncio.sleep(poll_interval_seconds)
            elapsed += poll_interval_seconds
        raise SDKClientError("Timed out waiting for HumanLink authentication")

    async def create_audit_session(
        self,
        *,
        assertion: dict[str, Any],
        action: str,
        source: str,
        auth_session_id: str,
    ) -> dict[str, Any]:
        payload = {
            "assertion": assertion,
            "action": action,
            "source": source,
            "auth_session_id": auth_session_id,
        }
        return await self._request_json("POST", "/audit/session", json=payload)

    async def _request_json(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise SDKClientError(f"Failed to reach HumanLink SDK: {exc}") from exc

        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise SDKClientError(f"HumanLink SDK error {response.status_code}: {detail}")

        return response.json()
