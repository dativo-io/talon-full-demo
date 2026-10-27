"""Deterministic OpenAI-compatible provider for credential-free Talon LIVE AI contract.

The mock stands behind a REAL Talon LLM gateway. It does not replace Talon,
and is NOT evidence that OpenAI's actual API was called.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CALLS = {"completions": 0, "with_tool_result": 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/health":
            return self.send(200, {"ok": True})
        if self.path == "/debug/status":
            return self.send(200, CALLS)
        return self.send(404, {"error": "not found"})

    def do_POST(self):
        if self.path not in ("/v1/chat/completions", "/chat/completions"):
            return self.send(404, {"error": "not found"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 200000:
                return self.send(400, {"error": "invalid size"})
            body = json.loads(self.rfile.read(size))
            messages = body["messages"]
            CALLS["completions"] += 1
            saw_tool_result = any(m.get("role") == "tool" for m in messages)
            if saw_tool_result:
                CALLS["with_tool_result"] += 1
                recent_tool = [m for m in messages if m.get("role") == "tool"][-1]
                tool_content = json.loads(recent_tool["content"])
                metrics = json.loads(tool_content[0]["text"])
                if not metrics.get("source", "").startswith("DuckDB"):
                    return self.send(400, {"error": "provider did not receive DuckDB-backed tool result"})
                if not metrics.get("cohorts"):
                    return self.send(400, {"error": "missing aggregate results"})
                cohort = metrics["cohorts"][0]
                rate = cohort["months"][-1]["attrition_rate_pct"]
                answer = (f"Based on DuckDB results, {cohort['department']} had {rate:.2f}% "
                          "monthly attrition in September 2026. These are descriptive aggregate "
                          "figures, not causal explanations.")
                message = {"role": "assistant", "content": answer}
                reason = "stop"
            else:
                offered = {tool["function"]["name"] for tool in body.get("tools", [])}
                if "hr_employee_export" in offered:
                    return self.send(400, {"error": "sensitive export exposed to LLM"})
                if "hr_attrition_summary" not in offered:
                    return self.send(400, {"error": "missing approved attrition tool", "received_tools": sorted(offered), "request_keys": sorted(body.keys()), "tool_choice": body.get("tool_choice")})
                message = {"role": "assistant", "content": None, "tool_calls": [
                    {"id": "call_hr_analytics_1", "type": "function", "function": {
                        "name": "hr_attrition_summary", "arguments": "{\"months\":6}"}}]}
                reason = "tool_calls"
            return self.send(200, {
                "id": "chatcmpl-hr-mock", "object": "chat.completion",
                "created": 1793116800, "model": "gpt-4o-mini",
                "choices": [{"index": 0, "message": message, "finish_reason": reason}],
                "usage": {"prompt_tokens": 25, "completion_tokens": 25, "total_tokens": 50}
            })
        except (KeyError, ValueError, TypeError):
            return self.send(400, {"error": "invalid completion request"})


if __name__ == "__main__":
    port = int(os.environ.get("HR_MOCK_LLM_PORT", "9092"))
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
