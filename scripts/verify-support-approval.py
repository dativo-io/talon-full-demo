#!/usr/bin/env python3
"""Verify the separate operator-approval receipt for the support demo."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def canonical(payload: dict[str, Any]) -> bytes:
    unsigned = {key: value for key, value in payload.items() if key != "signature"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_key(path: Path) -> bytes:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError("approval signing key is empty")
    try:
        return bytes.fromhex(raw)
    except ValueError:
        return raw.encode("utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def parse_time(value: Any, field: str) -> datetime:
    require(isinstance(value, str) and value, f"{field} is missing")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--session", required=True)
    parser.add_argument("--run-nonce", required=True)
    parser.add_argument("--ticket", required=True)
    parser.add_argument("--amount", type=int, required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--decision", choices=("approved", "rejected"))
    parser.add_argument("--finance-handoff", type=Path)
    args = parser.parse_args()

    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    require(isinstance(receipt, dict), "receipt is not a JSON object")
    signature = receipt.get("signature")
    require(isinstance(signature, str) and len(signature) == 64, "receipt signature is missing")
    expected = hmac.new(load_key(args.key), canonical(receipt), hashlib.sha256).hexdigest()
    require(hmac.compare_digest(signature, expected), "operator approval receipt signature is invalid")
    require(receipt.get("signature_alg") == "HMAC-SHA256", "unexpected signature algorithm")
    require(receipt.get("session_id") == args.session, "approval session mismatch")
    require(receipt.get("run_nonce") == args.run_nonce, "approval run nonce mismatch")
    require(receipt.get("ticket_id") == args.ticket, "approval ticket mismatch")
    require(receipt.get("amount_eur") == args.amount, "approval amount mismatch")
    require(receipt.get("requested_action") == args.action, "approval action mismatch")
    require(receipt.get("refund_executed") is False, "approval receipt claims a refund was executed")
    require(receipt.get("decision") in {"approved", "rejected"}, "approval decision is invalid")
    if args.decision:
        require(receipt.get("decision") == args.decision, "approval decision mismatch")
    decided_at = parse_time(receipt.get("decided_at"), "decided_at")

    if args.finance_handoff:
        handoff = json.loads(args.finance_handoff.read_text(encoding="utf-8"))
        require(isinstance(handoff, dict), "finance handoff is not a JSON object")
        require(receipt.get("decision") == "approved", "finance handoff exists without approval")
        for field in ("approval_id", "session_id", "run_nonce", "ticket_id", "amount_eur", "requested_action"):
            require(handoff.get(field) == receipt.get(field), f"finance handoff {field} mismatch")
        require(handoff.get("status") == "approved_for_finance_processing", "finance handoff status mismatch")
        require(handoff.get("refund_executed") is False, "finance handoff claims a refund was executed")
        require(parse_time(handoff.get("created_at"), "finance created_at") >= decided_at, "finance handoff predates approval")

    print(
        "operator approval OK: "
        f"decision={receipt['decision']} ticket={receipt['ticket_id']} "
        f"amount=EUR {receipt['amount_eur']} session={receipt['session_id']}"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"operator approval verification failed: {exc}") from exc
