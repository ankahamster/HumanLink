"""Minimal mock agent that sends a PaymentIntent to the HumanlinkPay gateway."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a mock PaymentIntent to the HumanlinkPay gateway")
    parser.add_argument("--gateway", default="http://127.0.0.1:8787/api/pay", help="Gateway /api/pay URL")
    parser.add_argument("--user-id", default="demo-user", help="Demo user id")
    parser.add_argument("--to", required=True, help="Recipient wallet or DemoMerchant contract address")
    parser.add_argument("--amount", default="0.005", help="Amount in ETH")
    parser.add_argument("--token", default="ETH", help="Token symbol")
    parser.add_argument("--purpose", default="Buy API access", help="Payment purpose")
    parser.add_argument("--deadline-minutes", type=int, default=10, help="Deadline offset in minutes")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    payload = {
        "userId": args.user_id,
        "to": args.to,
        "amount": args.amount,
        "token": args.token,
        "purpose": args.purpose,
        "deadline": (datetime.now(timezone.utc) + timedelta(minutes=args.deadline_minutes)).isoformat(),
        "nonce": str(uuid.uuid4()),
    }

    request = urllib.request.Request(
        args.gateway,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print("Gateway request failed", file=sys.stderr)
        print(detail, file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Gateway unavailable: {exc}", file=sys.stderr)
        return 1

    result = json.loads(body)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    assertion = result.get("assertion") or {}
    record_url = assertion.get("humanlink_record_url")
    if record_url:
        print(f"\nHumanLink record UI: {record_url}")

    execution = result.get("execution") or {}
    tx_hash = execution.get("tx_hash")
    if tx_hash:
        print(f"Transaction hash: {tx_hash}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
