"""Pydantic models used by the HumanlinkPay gateway."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class PolicyDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_HL = "REQUIRE_HL"


class PaymentIntent(BaseModel):
    user_id: str = Field(default="demo-user", alias="userId")
    to: str
    amount: str
    token: str = "ETH"
    purpose: str
    deadline: str | None = None
    nonce: str = Field(default_factory=lambda: str(uuid4()))

    model_config = {"populate_by_name": True}

    @field_validator("to")
    @classmethod
    def normalize_recipient(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Recipient address is required")
        return value.lower()

    @field_validator("token")
    @classmethod
    def normalize_token(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("Token is required")
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: str) -> str:
        try:
            amount = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("Amount must be a valid decimal string") from exc
        if amount <= 0:
            raise ValueError("Amount must be positive")
        return str(amount)

    @field_validator("deadline")
    @classmethod
    def validate_deadline(cls, value: str | None) -> str | None:
        if value is None:
            return value
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    def amount_decimal(self) -> Decimal:
        return Decimal(self.amount)


class CanonicalPaymentIntent(BaseModel):
    user_id: str
    to: str
    amount: str
    token: str
    purpose: str
    deadline: str | None
    nonce: str


class PolicyResult(BaseModel):
    decision: PolicyDecision
    reason: str


class AssertionSummary(BaseModel):
    session_id: str
    audit_session_id: str | None = None
    assertion_id: str
    action_hash: str
    device_did: str | None = None
    humanlink_record_url: str | None = None


class ExecutionResult(BaseModel):
    executed: bool
    mode: str
    tx_hash: str | None = None
    detail: str


class PaymentResponse(BaseModel):
    decision: PolicyDecision
    reason: str
    action_hash: str
    canonical_intent: CanonicalPaymentIntent = Field(alias="canonicalIntent")
    assertion: AssertionSummary | None = None
    execution: ExecutionResult | None = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = {"populate_by_name": True}


class PaymentPreviewResponse(BaseModel):
    decision: PolicyDecision
    reason: str
    action_hash: str
    canonical_intent: CanonicalPaymentIntent = Field(alias="canonicalIntent")
    record_wait_token: str | None = Field(default=None, alias="recordWaitToken")

    model_config = {"populate_by_name": True}


class AuditRecord(BaseModel):
    created_at: str
    decision: PolicyDecision
    reason: str
    action_hash: str
    canonical_intent: dict[str, Any]
    assertion: dict[str, Any] | None = None
    execution: dict[str, Any] | None = None


class HermesChatMessage(BaseModel):
    role: str
    content: str


class HermesChatRequest(BaseModel):
    messages: list[HermesChatMessage]
    user_id: str = Field(default="demo-user", alias="userId")

    model_config = {"populate_by_name": True}


class HermesChatResponse(BaseModel):
    assistant_message: str
    payment_detected: bool = False
    payment_intent: dict[str, Any] | None = None
    missing_fields: list[str] = Field(default_factory=list)
    should_autofill: bool = False
