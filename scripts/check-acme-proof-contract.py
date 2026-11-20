#!/usr/bin/env python3
"""Fail closed on ACME buyer-proof contract regressions; NOT an E2E runtime test."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
expect = {
    "docs/SHOWCASE_LIVE_WALKTHROUGH.md": [
        "COMPETITOR_PROOF_SCORECARD.md", "seven", "Approvals (read-only)",
        "Talon-forwarded", "n8n 2.48.5", "2.30.4", "Registered", "Loaded",
        "Connected", "Governed", "independent", "v1.17.0 stable", "NOT RUN",
        "unknown", "override", "Talon", "refund",
    ],
    "docs/COMPETITOR_PROOF_SCORECARD.md": [
        "Portkey", "LiteLLM", "Langfuse", "LangSmith", "Helicone",
        "company policy", "at most once", "UNKNOWN", "n8n 2.48.5",
        "source-built", "independent", "signed",
        "not a published benchmark",
    ],
    "README.md": [
        "COMPETITOR_PROOF_SCORECARD.md", "Shopify-style",
        "read-only", "Approvals", "2.48.5", "2.30.4",
        "legacy", "v1.17.0",
    ],
}
for filename, needles in expect.items():
    txt = (ROOT / filename).read_text()
    for value in needles:
        assert value.lower() in txt.lower(), (filename, f"missing: {value}")
    print("PASS demo proof contract:", filename)
walk = (ROOT / "docs/SHOWCASE_LIVE_WALKTHROUGH.md").read_text().lower()
for obsolete in ("six pages", "six-page", "competing approval inbox", "exactly-once external"):
    assert obsolete not in walk, f"obsolete claim in walkthrough: {obsolete}"
print("PASS: no obsolete console-count or unsafe exactly-once claims")
print("NOTE: this is a static demo truth contract; does not test runtime, published artifact, provider, reviewer or finance")
