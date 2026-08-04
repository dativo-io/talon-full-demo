#!/usr/bin/env python3
"""Loopback-only operator approval service for the support-resolution demo."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import html
import json
import os
import re
import tempfile
import threading
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,160}$")
REQUIRED_REQUEST_FIELDS = (
    "approval_id",
    "session_id",
    "run_nonce",
    "ticket_id",
    "amount_eur",
    "requested_action",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
        return value if isinstance(value, dict) else None
    except FileNotFoundError:
        return None


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


class ApprovalStore:
    def __init__(self, state_dir: Path, signing_key: bytes, public_base_url: str) -> None:
        self.state_dir = state_dir
        self.signing_key = signing_key
        self.public_base_url = public_base_url.rstrip("/")
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        state_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(state_dir, 0o700)

    def _safe_id(self, approval_id: str) -> str:
        if not ID_RE.fullmatch(approval_id):
            raise ValueError("invalid approval_id")
        return approval_id

    def request_path(self, approval_id: str) -> Path:
        return self.state_dir / f"{self._safe_id(approval_id)}.request.json"

    def receipt_path(self, approval_id: str) -> Path:
        return self.state_dir / f"{self._safe_id(approval_id)}.receipt.json"

    def create_request(self, payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        missing = [field for field in REQUIRED_REQUEST_FIELDS if field not in payload]
        if missing:
            raise ValueError(f"missing fields: {', '.join(missing)}")
        approval_id = self._safe_id(str(payload["approval_id"]))
        request = {
            "approval_id": approval_id,
            "session_id": str(payload["session_id"]),
            "run_nonce": str(payload["run_nonce"]),
            "ticket_id": str(payload["ticket_id"]),
            "amount_eur": int(payload["amount_eur"]),
            "requested_action": str(payload["requested_action"]),
            "refund_executed": False,
            "status": "pending",
            "created_at": utc_now(),
        }
        if request["amount_eur"] <= 0:
            raise ValueError("amount_eur must be positive")
        path = self.request_path(approval_id)
        with self.changed:
            current = load_json(path)
            if current is not None:
                comparable = {key: current.get(key) for key in REQUIRED_REQUEST_FIELDS}
                expected = {key: request.get(key) for key in REQUIRED_REQUEST_FIELDS}
                if comparable != expected:
                    raise ValueError("approval_id already belongs to a different request")
                return current, False
            atomic_json(path, request)
            self.changed.notify_all()
        return request, True

    def get_request(self, approval_id: str) -> dict[str, Any] | None:
        return load_json(self.request_path(approval_id))

    def get_receipt(self, approval_id: str) -> dict[str, Any] | None:
        return load_json(self.receipt_path(approval_id))

    def decide(self, approval_id: str, decision: str, operator: str) -> dict[str, Any]:
        if decision not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        with self.changed:
            request = self.get_request(approval_id)
            if request is None:
                raise FileNotFoundError("approval request does not exist")
            existing = self.get_receipt(approval_id)
            if existing is not None:
                if existing.get("decision") != decision:
                    raise ValueError("approval request already has a different decision")
                return existing
            receipt = {
                "approval_id": request["approval_id"],
                "session_id": request["session_id"],
                "run_nonce": request["run_nonce"],
                "ticket_id": request["ticket_id"],
                "amount_eur": request["amount_eur"],
                "requested_action": request["requested_action"],
                "decision": decision,
                "operator": operator or "demo-operator",
                "decided_at": utc_now(),
                "refund_executed": False,
                "signature_alg": "HMAC-SHA256",
            }
            receipt["signature"] = hmac.new(
                self.signing_key, canonical(receipt), hashlib.sha256
            ).hexdigest()
            atomic_json(self.receipt_path(approval_id), receipt)
            self.changed.notify_all()
            return receipt

    def wait_for_receipt(self, approval_id: str, timeout: int) -> dict[str, Any] | None:
        deadline = time.monotonic() + timeout
        with self.changed:
            while True:
                receipt = self.get_receipt(approval_id)
                if receipt is not None:
                    return receipt
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self.changed.wait(min(remaining, 1.0))

    def approval_url(self, approval_id: str) -> str:
        return f"{self.public_base_url}/approval/{approval_id}"


class ApprovalHandler(BaseHTTPRequestHandler):
    server_version = "TalonSupportApproval/1.0"

    @property
    def store(self) -> ApprovalStore:
        return self.server.store  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"approval-service: {self.address_string()} - {fmt % args}", flush=True)

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, status: int, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        parsed = json.loads(raw.decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("request body must be a JSON object")
        return parsed

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path == "/health":
            self._json(HTTPStatus.OK, {"status": "ok"})
            return
        match = re.fullmatch(r"/requests/([A-Za-z0-9._-]+)", path)
        if match:
            approval_id = match.group(1)
            request = self.store.get_request(approval_id)
            if request is None:
                self._json(HTTPStatus.NOT_FOUND, {"error": "request_not_found"})
                return
            receipt = self.store.get_receipt(approval_id)
            self._json(
                HTTPStatus.OK,
                {
                    "request": request,
                    "receipt": receipt,
                    "approval_url": self.store.approval_url(approval_id),
                },
            )
            return
        match = re.fullmatch(r"/wait/([A-Za-z0-9._-]+)", path)
        if match:
            approval_id = match.group(1)
            query = parse_qs(parsed.query)
            timeout = max(1, min(int(query.get("timeout", ["1800"])[0]), 3600))
            if self.store.get_request(approval_id) is None:
                self._json(HTTPStatus.NOT_FOUND, {"error": "request_not_found"})
                return
            receipt = self.store.wait_for_receipt(approval_id, timeout)
            if receipt is None:
                self._json(HTTPStatus.REQUEST_TIMEOUT, {"error": "approval_timeout"})
                return
            self._json(HTTPStatus.OK, receipt)
            return
        match = re.fullmatch(r"/approval/([A-Za-z0-9._-]+)", path)
        if match:
            self._render_approval(match.group(1))
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def _render_approval(self, approval_id: str) -> None:
        request = self.store.get_request(approval_id)
        receipt = self.store.get_receipt(approval_id)
        if request is None:
            self._html(
                HTTPStatus.OK,
                "<!doctype html><meta http-equiv='refresh' content='2'>"
                "<title>Waiting for approval request</title>"
                "<main style='font:16px system-ui;max-width:700px;margin:60px auto'>"
                "<h1>Waiting for the workflow</h1>"
                "<p>The approval request has not reached this gate yet. This page refreshes automatically.</p>"
                "</main>",
            )
            return
        safe = {key: html.escape(str(value)) for key, value in request.items()}
        if receipt is None:
            decision = "Pending operator decision"
            controls = f"""
<form method="post" action="/approval/{safe['approval_id']}/approve" style="display:inline-block;margin-right:12px">
  <button style="font-size:18px;padding:12px 20px">Approve finance handoff</button>
</form>
<form method="post" action="/approval/{safe['approval_id']}/reject" style="display:inline-block">
  <button style="font-size:18px;padding:12px 20px">Reject request</button>
</form>"""
        else:
            decision = f"Decision recorded: {html.escape(str(receipt['decision']))}"
            controls = "<p>The waiting workflow has been released.</p>"
        self._html(
            HTTPStatus.OK,
            f"""<!doctype html>
<title>Talon demo operator approval</title>
<main style="font:16px system-ui;max-width:760px;margin:48px auto;line-height:1.45">
  <h1>Human approval required</h1>
  <p><strong>{decision}</strong></p>
  <table style="border-collapse:collapse;width:100%;margin:24px 0">
    <tr><th style="text-align:left;padding:8px;border-bottom:1px solid #ccc">Ticket</th><td style="padding:8px;border-bottom:1px solid #ccc">{safe['ticket_id']}</td></tr>
    <tr><th style="text-align:left;padding:8px;border-bottom:1px solid #ccc">Requested action</th><td style="padding:8px;border-bottom:1px solid #ccc">{safe['requested_action']}</td></tr>
    <tr><th style="text-align:left;padding:8px;border-bottom:1px solid #ccc">Amount</th><td style="padding:8px;border-bottom:1px solid #ccc">EUR {safe['amount_eur']}</td></tr>
    <tr><th style="text-align:left;padding:8px;border-bottom:1px solid #ccc">Talon session</th><td style="padding:8px;border-bottom:1px solid #ccc"><code>{safe['session_id']}</code></td></tr>
    <tr><th style="text-align:left;padding:8px;border-bottom:1px solid #ccc">AI action</th><td style="padding:8px;border-bottom:1px solid #ccc">Blocked by Talon before provider dispatch</td></tr>
    <tr><th style="text-align:left;padding:8px;border-bottom:1px solid #ccc">Refund</th><td style="padding:8px;border-bottom:1px solid #ccc">Not executed</td></tr>
  </table>
  <p>Approval authorizes only a synthetic finance handoff. It does not expose <code>issue_refund</code> to the model and does not execute a payment.</p>
  {controls}
</main>""",
        )

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/requests":
            try:
                request, created = self.store.create_request(self._read_json())
            except (ValueError, json.JSONDecodeError) as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            self._json(
                HTTPStatus.CREATED if created else HTTPStatus.OK,
                {
                    "status": "pending",
                    "request": request,
                    "approval_url": self.store.approval_url(request["approval_id"]),
                },
            )
            return
        match = re.fullmatch(r"/approval/([A-Za-z0-9._-]+)/(approve|reject)", path)
        if match:
            approval_id, action = match.groups()
            decision = "approved" if action == "approve" else "rejected"
            try:
                payload = self._read_json() if self.headers.get("Content-Type", "").startswith("application/json") else {}
                receipt = self.store.decide(approval_id, decision, str(payload.get("operator", "demo-operator")))
            except FileNotFoundError as exc:
                self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
                return
            except (ValueError, json.JSONDecodeError) as exc:
                self._json(HTTPStatus.CONFLICT, {"error": str(exc)})
                return
            if "application/json" in self.headers.get("Accept", ""):
                self._json(HTTPStatus.OK, receipt)
            else:
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", f"/approval/{approval_id}")
                self.send_header("Content-Length", "0")
                self.end_headers()
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--signing-key-file", type=Path, required=True)
    parser.add_argument("--public-base-url")
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("approval service must remain bound to loopback")
    base_url = args.public_base_url or f"http://127.0.0.1:{args.port}"
    server = ThreadingHTTPServer((args.host, args.port), ApprovalHandler)
    server.store = ApprovalStore(args.state_dir, load_key(args.signing_key_file), base_url)  # type: ignore[attr-defined]
    print(f"approval-service listening on {base_url}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
