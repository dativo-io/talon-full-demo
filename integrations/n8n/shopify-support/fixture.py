"""Visible synthetic Shopify read API, deterministic upstream and optional fake refund ledger.

Never connects to Shopify or payments. The local /refunds route is only enabled
for the core-main canonical Action Gateway acceptance, never for released Stage A.
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import time
import threading
lock = threading.Lock()

p = argparse.ArgumentParser()
p.add_argument("--port", type=int, required=True)
p.add_argument("--log", type=Path, required=True)
p.add_argument("--action-fixture", action="store_true", help="enable synthetic loopback refund ledger, never actual payments")
args = p.parse_args()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass
    def reply(self, code, value):
        data = json.dumps(value).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def record(self, value):
        with lock:
            with args.log.open("a") as f:
                f.write(json.dumps(value) + "\n")
    def do_GET(self):
        if self.path == "/count" and args.action_fixture:
            with lock:
                rows=[json.loads(line) for line in args.log.read_text().splitlines()] if args.log.exists() else []
            calls=[row for row in rows if row.get("kind")=="synthetic_refund_dispatch"]
            self.reply(200, {"calls": len(calls), "operations": [{"ticket_id":c["ticket_id"], "amount":c["amount"], "idempotency":c["idempotency"]} for c in calls]})
        else:
            self.reply(200 if self.path == "/health" else 404, {"ok": self.path == "/health"})
    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        except (ValueError, TypeError):
            self.reply(400, {"error": "invalid JSON"})
            return
        if self.path == "/refunds" and args.action_fixture:
            # Only synthetic test order; the business adapter independently validates
            # what Talon is authorized to dispatch. It is not a Shopify write path.
            ticket=body.get("ticket_id")
            amount=body.get("amount")
            currency=body.get("currency")
            idem=self.headers.get("Idempotency-Key")
            if ticket != "SUP-1001" or currency != "EUR" or not isinstance(amount,str) or not idem or len(idem)>160:
                self.record({"kind":"rejected_refund_dispatch"})
                self.reply(422, {"error":"invalid_business_arguments"})
                return
            import re
            if not re.fullmatch(r"(?:0|[1-9][0-9]{0,6})(?:\.[0-9]{1,2})?", amount):
                self.reply(422, {"error":"invalid_decimal"})
                return
            whole,_,frac=amount.partition(".")
            cents=int(whole)*100+int(frac.ljust(2,"0"))
            if not (0 < cents <= 100000):
                self.reply(422, {"error":"ineligible_amount"})
                return
            self.record({"kind":"synthetic_refund_dispatch", "ticket_id":ticket, "amount":amount, "idempotency":idem})
            self.reply(201, {"refund_id":"synthetic-reviewed-refund", "accepted":True})
            return
        if self.path == "/admin/api/2026-10/graphql.json":
            if self.headers.get("X-Shopify-Access-Token") != "synthetic-read-only":
                self.reply(401, {"errors": [{"message": "unauthorized"}]})
                return
            if body.get("variables") != {"search": "name:#1001"} or not body.get("query", "").startswith("query SupportOrder") or "mutation" in body["query"]:
                self.record({"kind": "unexpected_shopify_request"})
                self.reply(400, {"errors": [{"message": "unexpected request"}]})
                return
            self.record({"kind": "shopify_read"})
            self.reply(200, {"data": {"orders": {"nodes": [{
                "name": "#1001", "email": "buyer@example.test", "test": True,
                "displayFinancialStatus": "PAID", "displayFulfillmentStatus": "UNFULFILLED",
                "totalReceivedSet": {"presentmentMoney": {"amount": "1000.00", "currencyCode": "EUR"}},
                "totalRefundedSet": {"presentmentMoney": {"amount": "0.00", "currencyCode": "EUR"}}
            }], "pageInfo": {"hasNextPage": False}}}})
            return
        if self.path == "/v1/chat/completions":
            if self.headers.get("Authorization") != "Bearer synthetic-provider-key":
                self.reply(401, {"error": {"message": "unauthorized"}})
                return
            messages = body.get("messages", [])
            try:
                facts = json.loads(messages[-1]["content"])
                assert set(facts) == {"issue_hints", "financial_status", "fulfillment_status", "proposed_refund_eur"}
                assert facts["financial_status"] == "PAID"
                assert facts["fulfillment_status"] == "UNFULFILLED"
                assert not any(x in json.dumps(messages) for x in ["buyer@example.test", "PL61109010140000071219812874", "#1001"])
            except (ValueError, KeyError, IndexError, TypeError, AssertionError):
                self.record({"kind": "invalid_provider_payload"})
                self.reply(400, {"error": {"message": "unexpected or non-minimized payload"}})
                return
            refund = facts["proposed_refund_eur"]
            result = {"issue": facts["issue_hints"][0],
                      "recommendation": "refund_review" if refund else ("status_reply" if facts["issue_hints"] == ["order_status"] else "manual_review"),
                      "draft": "Fixture only: your order is not yet fulfilled. We will review the next steps.",
                      "proposed_refund_eur": refund}
            self.record({"kind": "provider_call", "facts": facts})
            self.reply(200, {"id": "chatcmpl-shopify-fixture", "object": "chat.completion",
                "created": int(time.time()), "model": body["model"],
                "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(result)}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 45, "total_tokens": 95}})
            return
        self.record({"kind": "unexpected_post"})
        self.reply(404, {"error": "no financial or other endpoint"})

ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
