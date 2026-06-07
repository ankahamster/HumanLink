"""Audit helpers for the HumanlinkPay gateway."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from .models import AuditRecord
except ImportError:  # pragma: no cover - direct module execution fallback
    from models import AuditRecord


class AuditLogger:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: AuditRecord) -> None:
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.model_dump(), ensure_ascii=True) + "\n")
