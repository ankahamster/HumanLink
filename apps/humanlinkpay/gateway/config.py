"""Runtime configuration for the HumanlinkPay gateway."""

from __future__ import annotations

import os
from pathlib import Path


def _parse_allowlist(raw: str) -> list[str]:
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


def _read_env_file(env_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


class Settings:
    """Simple environment-backed settings container."""

    def __init__(self) -> None:
        gateway_dir = Path(__file__).resolve().parent
        app_dir = gateway_dir.parent
        project_root = app_dir.parents[1]
        runtime_dir = gateway_dir / "runtime"

        file_settings: dict[str, str] = {}
        for env_path in [
            project_root / "contracts" / ".env",
            gateway_dir / ".env",
        ]:
            file_settings.update(_read_env_file(env_path))

        env_settings = {key: value for key, value in os.environ.items() if value is not None}
        merged = {**file_settings, **env_settings}

        self.app_name = "HumanlinkPay Gateway"
        self.host = merged.get("HUMANLINKPAY_GATEWAY_HOST", "127.0.0.1")
        self.port = int(merged.get("HUMANLINKPAY_GATEWAY_PORT", "8787"))
        self.sdk_base_url = merged.get("HUMANLINKPAY_SDK_URL", "http://127.0.0.1:8765")
        self.default_user_id = merged.get("HUMANLINKPAY_DEFAULT_USER_ID", "demo-user")
        self.origin = merged.get("HUMANLINKPAY_ORIGIN", "HumanlinkPay")
        self.payment_threshold_eth = float(merged.get("HUMANLINKPAY_THRESHOLD_ETH", "0.001"))
        self.allowed_recipients = _parse_allowlist(
            merged.get("HUMANLINKPAY_ALLOWLIST", "0xdemomerchant")
        )
        self.execution_mode = merged.get("HUMANLINKPAY_EXECUTION_MODE", "stub")
        self.chain_id = int(merged.get("HUMANLINKPAY_CHAIN_ID", merged.get("HUMANLINK_WALLET_CHAIN_ID", "11155111")))
        self.rpc_url = merged.get("HUMANLINKPAY_SEPOLIA_RPC_URL", merged.get("SEPOLIA_RPC_URL", ""))
        self.private_key = merged.get("HUMANLINKPAY_PRIVATE_KEY", merged.get("SEPOLIA_PRIVATE_KEY", ""))
        self.demo_merchant_address = merged.get("HUMANLINKPAY_DEMO_MERCHANT_ADDRESS", "")
        self.wait_for_receipt = merged.get("HUMANLINKPAY_WAIT_FOR_RECEIPT", "true").lower() == "true"
        self.auto_open_demo_ui = merged.get("HUMANLINKPAY_AUTO_OPEN_DEMO_UI", "true").lower() == "true"
        self.hermes_command = merged.get("HUMANLINKPAY_HERMES_COMMAND", "hermes")
        self.hermes_provider = merged.get("HUMANLINKPAY_HERMES_PROVIDER", "deepseek")
        self.hermes_model = merged.get("HUMANLINKPAY_HERMES_MODEL", "deepseek-chat")
        self.hermes_timeout_seconds = int(merged.get("HUMANLINKPAY_HERMES_TIMEOUT_SECONDS", "90"))
        self.audit_log_path = Path(
            merged.get(
                "HUMANLINKPAY_AUDIT_LOG_PATH",
                str(runtime_dir / "gateway_audit.jsonl"),
            )
        )
        self.runtime_dir = runtime_dir

    def ensure_runtime_dirs(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
