"""Structured tracing guards: real data provenance without leaking API keys."""
import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch

from runtime_trace import trace, previews_enabled, _scrub

class TraceContractTests(unittest.TestCase):
    def test_metadata_without_prompt_payload_by_default(self):
        with patch.dict(os.environ, {"HR_DEMO_TRACE": "1", "HR_DEMO_TRACE_PAYLOADS": "0"}):
            self.assertFalse(previews_enabled())
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                trace("llm.gateway.request", "hr-demo-foo", model="gpt-4o-mini",
                      request_payload="[metadata only]")
            data = json.loads(output.getvalue().split("HR_AI_TRACE ", 1)[1])
            self.assertEqual(data["session"], "hr-demo-foo")
            self.assertEqual(data["request_payload"], "[metadata only]")
            self.assertEqual(data["observer"], "demo-application (not provider wire capture)")

    def test_synthetic_payload_preview_is_explicit_and_redacted(self):
        with patch.dict(os.environ, {"HR_DEMO_TRACE_PAYLOADS": "1"}):
            self.assertTrue(previews_enabled())
        payload = _scrub({"Authorization": "Bearer sk-demoAbcdefghijklmn",
                          "body": "Bearer someCredential sk-anotherlongexample0123456",
                          "nested": {"api_key": "raw-key"}})
        as_json = json.dumps(payload)
        self.assertNotIn("demoAbcdef", as_json)
        self.assertNotIn("someCredential", as_json)
        self.assertNotIn("raw-key", as_json)
        self.assertIn("[redacted]", as_json)

    def test_tracing_can_be_disabled(self):
        with patch.dict(os.environ, {"HR_DEMO_TRACE": "0"}):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                trace("llm.gateway.response", "x", usage={"total_tokens": 10})
            self.assertEqual(output.getvalue(), "")

if __name__ == "__main__":
    unittest.main()
