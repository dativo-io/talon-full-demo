#!/usr/bin/env python3
"""Synthetic priced OpenAI-wire provider for ACME document budget acceptance.

No network, no credentials, no real LLM. Counters are independently hosted by
this mock, not sourced from Talon's evidence. Deliberately very large usage
creates a measurable $0.30 cost at the explicit pinned local price table.
"""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock

parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, required=True)
args = parser.parse_args()
lock = Lock()
requests = 0


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def reply(self, status, value):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        with lock:
            count = requests
        if self.path == "/health":
            return self.reply(200, {"healthy": True})
        if self.path == "/count":
            return self.reply(200, {"calls": count})
        self.reply(404, {"error": "not_found"})

    def do_POST(self):
        global requests
        size = int(self.headers.get("Content-Length", "0"))
        try:
            request = json.loads(self.rfile.read(size))
        except ValueError:
            return self.reply(400, {"error": "bad_json"})
        if self.path != "/v1/chat/completions":
            return self.reply(404, {"error": "not_found"})
        if request.get("model") != "gpt-4o-mini":
            return self.reply(400, {"error": "unsupported_model"})
        with lock:
            requests += 1
        self.reply(200, {
            "id": "chatcmpl-acme-synthetic-doc",
            "object": "chat.completion",
            "model": "gpt-4o-mini",
            "choices": [{"index": 0, "message": {
                "role": "assistant", "content":
                "Synthetic document summary is available for operator review.",
            }, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 400000, "completion_tokens": 400000,
                      "total_tokens": 800000},
        })


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()
