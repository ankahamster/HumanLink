"""Policy evaluation for HumanlinkPay payment intents."""

from __future__ import annotations

from decimal import Decimal

try:
    from .models import PaymentIntent, PolicyDecision, PolicyResult
except ImportError:  # pragma: no cover - direct module execution fallback
    from models import PaymentIntent, PolicyDecision, PolicyResult


class PaymentPolicyEngine:
    def __init__(self, *, threshold_eth: float, allowed_recipients: list[str]) -> None:
        self.threshold = Decimal(str(threshold_eth))
        self.allowed_recipients = {recipient.lower() for recipient in allowed_recipients}

    def evaluate(self, intent: PaymentIntent) -> PolicyResult:
        if intent.to not in self.allowed_recipients:
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason="Recipient is not in the allowlist",
            )

        if intent.token != "ETH":
            return PolicyResult(
                decision=PolicyDecision.DENY,
                reason="Only native ETH is supported in the first gateway version",
            )

        if intent.amount_decimal() > self.threshold:
            return PolicyResult(
                decision=PolicyDecision.REQUIRE_HL,
                reason=f"Amount exceeds threshold {self.threshold} ETH",
            )

        return PolicyResult(
            decision=PolicyDecision.ALLOW,
            reason=f"Amount is within auto-approval threshold {self.threshold} ETH",
        )
