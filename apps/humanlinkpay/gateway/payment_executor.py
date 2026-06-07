"""Payment execution layer for the HumanlinkPay gateway."""

from __future__ import annotations

import hashlib
import time
from decimal import Decimal
from typing import Any

from eth_account import Account
from web3 import Web3

try:
    from .config import Settings
    from .models import CanonicalPaymentIntent, ExecutionResult
except ImportError:  # pragma: no cover - direct module execution fallback
    from config import Settings
    from models import CanonicalPaymentIntent, ExecutionResult


DEMO_MERCHANT_ABI: list[dict[str, Any]] = [
    {
        "inputs": [
            {"internalType": "string", "name": "purpose", "type": "string"},
            {"internalType": "bytes32", "name": "actionHash", "type": "bytes32"},
        ],
        "name": "purchase",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "buyer", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "amountWei", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "purpose", "type": "string"},
            {"indexed": True, "internalType": "bytes32", "name": "actionHash", "type": "bytes32"},
        ],
        "name": "ServicePurchased",
        "type": "event",
    },
]


def _amount_to_wei(amount: str) -> int:
    return int((Decimal(amount) * Decimal("1000000000000000000")).to_integral_value())


class StubPaymentExecutor:
    """Returns a deterministic fake tx hash until real chain execution is wired."""

    def execute(self, intent: CanonicalPaymentIntent, action_hash: str) -> ExecutionResult:
        digest = hashlib.sha256(f"{action_hash}:{intent.to}:{intent.amount}".encode("utf-8")).hexdigest()
        return ExecutionResult(
            executed=True,
            mode="stub",
            tx_hash="0x" + digest,
            detail="Stub executor used; no on-chain transaction was broadcast",
        )


class Web3PaymentExecutor:
    """Executes Sepolia transfers or DemoMerchant purchases using a local signer."""

    def __init__(self, settings: Settings) -> None:
        if not settings.rpc_url:
            raise ValueError("Missing Sepolia RPC URL for real payment execution")
        if not settings.private_key:
            raise ValueError("Missing private key for real payment execution")

        self.settings = settings
        self.web3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        if not self.web3.is_connected():
            raise ValueError(f"Unable to connect to RPC: {settings.rpc_url}")
        self.account = Account.from_key(settings.private_key)

    def _reset_provider(self) -> None:
        self.web3 = Web3(Web3.HTTPProvider(self.settings.rpc_url))

    def _should_retry_rpc_error(self, exc: Exception) -> bool:
        text = f"{type(exc).__name__}: {exc}"
        markers = (
            "RemoteDisconnected",
            "Connection aborted",
            "ConnectionError",
            "Read timed out",
            "Max retries exceeded",
            "502 Bad Gateway",
            "503 Service Unavailable",
            "504 Gateway Time-out",
        )
        return any(marker in text for marker in markers)

    def _rpc_call(self, label: str, fn):
        last_exc: Exception | None = None
        for attempt in range(1, 4):
            try:
                return fn()
            except Exception as exc:
                last_exc = exc
                if attempt >= 3 or not self._should_retry_rpc_error(exc):
                    raise
                self._reset_provider()
                time.sleep(0.6)
        if last_exc:
            raise last_exc
        raise RuntimeError(f"RPC call failed unexpectedly: {label}")

    def execute(self, intent: CanonicalPaymentIntent, action_hash: str) -> ExecutionResult:
        if self.settings.execution_mode == "demo_merchant":
            return self._execute_demo_merchant(intent, action_hash)
        return self._execute_native_transfer(intent)

    def _execute_native_transfer(self, intent: CanonicalPaymentIntent) -> ExecutionResult:
        recipient = Web3.to_checksum_address(intent.to)
        value = _amount_to_wei(intent.amount)
        nonce = self._rpc_call(
            "_execute_native_transfer:get_transaction_count",
            lambda: self.web3.eth.get_transaction_count(self.account.address),
        )
        tx = {
            "chainId": self.settings.chain_id,
            "nonce": nonce,
            "from": self.account.address,
            "to": recipient,
            "value": value,
            "gas": 21000,
        }
        fee_params = self._fee_params()
        tx.update(fee_params)
        signed = self.account.sign_transaction(tx)
        tx_hash = self._rpc_call(
            "_execute_native_transfer:send_raw_transaction",
            lambda: self.web3.eth.send_raw_transaction(signed.raw_transaction),
        )
        self._wait_for_receipt_if_needed(tx_hash)
        return ExecutionResult(
            executed=True,
            mode="native_transfer",
            tx_hash=tx_hash.hex(),
            detail=f"Sent {intent.amount} ETH to {recipient} on Sepolia",
        )

    def _execute_demo_merchant(self, intent: CanonicalPaymentIntent, action_hash: str) -> ExecutionResult:
        if not self.settings.demo_merchant_address:
            raise ValueError("Missing DemoMerchant address for demo_merchant mode")

        contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(self.settings.demo_merchant_address),
            abi=DEMO_MERCHANT_ABI,
        )
        value = _amount_to_wei(intent.amount)
        nonce = self._rpc_call(
            "_execute_demo_merchant:get_transaction_count",
            lambda: self.web3.eth.get_transaction_count(self.account.address),
        )
        tx = contract.functions.purchase(
            intent.purpose,
            bytes.fromhex(action_hash),
        ).build_transaction(
            {
                "chainId": self.settings.chain_id,
                "nonce": nonce,
                "from": self.account.address,
                "value": value,
            }
        )
        if "gas" not in tx:
            tx["gas"] = self._rpc_call(
                "_execute_demo_merchant:estimate_gas",
                lambda: self.web3.eth.estimate_gas(tx),
            )
        fee_params = self._fee_params()
        tx.update(fee_params)
        signed = self.account.sign_transaction(tx)
        tx_hash = self._rpc_call(
            "_execute_demo_merchant:send_raw_transaction",
            lambda: self.web3.eth.send_raw_transaction(signed.raw_transaction),
        )
        self._wait_for_receipt_if_needed(tx_hash)
        return ExecutionResult(
            executed=True,
            mode="demo_merchant",
            tx_hash=tx_hash.hex(),
            detail=(
                f"Called DemoMerchant.purchase for {intent.amount} ETH; "
                "ServicePurchased event should be emitted on Sepolia"
            ),
        )

    def _fee_params(self) -> dict[str, int]:
        latest_block = self._rpc_call(
            "_fee_params:get_block",
            lambda: self.web3.eth.get_block("latest"),
        )
        try:
            priority_fee = int(
                self._rpc_call("_fee_params:max_priority_fee", lambda: self.web3.eth.max_priority_fee)
            )
        except Exception:  # pragma: no cover - provider dependent
            priority_fee = self.web3.to_wei(2, "gwei")

        base_fee = latest_block.get("baseFeePerGas")
        if base_fee is not None:
            max_fee = int(base_fee) * 2 + priority_fee
            return {
                "maxPriorityFeePerGas": priority_fee,
                "maxFeePerGas": max_fee,
            }

        gas_price = int(self._rpc_call("_fee_params:gas_price", lambda: self.web3.eth.gas_price))
        return {"gasPrice": gas_price}

    def _wait_for_receipt_if_needed(self, tx_hash: bytes) -> None:
        if not self.settings.wait_for_receipt:
            return
        receipt = self._rpc_call(
            "_wait_for_receipt_if_needed:wait_for_receipt",
            lambda: self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180),
        )
        if receipt.status != 1:
            raise ValueError(f"Transaction reverted on-chain: {receipt.transactionHash.hex()}")


def create_payment_executor(settings: Settings) -> StubPaymentExecutor | Web3PaymentExecutor:
    if settings.execution_mode == "stub":
        return StubPaymentExecutor()
    if settings.execution_mode in {"native_transfer", "demo_merchant"}:
        return Web3PaymentExecutor(settings)
    raise ValueError(f"Unsupported execution mode: {settings.execution_mode}")
