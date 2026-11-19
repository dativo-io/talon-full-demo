"""Visible synthetic order API and deterministic upstream provider; no financial endpoint."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import time

p = argparse.ArgumentParser()
p.add_argument("--port", type=int, required=True)
p.add_argument("--log", type=Path, required=True)
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
        with args.log.open("a") as f:
            f.write(json.dumps(value) + "\n")
    def do_GET(self):
        self.reply(200 if self.path == "/health" else 404, {"ok": self.path == "/health"})
    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        except (ValueError, TypeError):
            self.reply(400, {"error": "invalid JSON"})
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
