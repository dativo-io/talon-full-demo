#!/usr/bin/env python3
"""Static buyer-claim and strategy consistency check. NOT a runtime demo acceptance."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
scorecard = (ROOT / "docs/COMPETITOR_PROOF_SCORECARD.md").read_text()
strategy = (ROOT / "docs/TALON_BUYER_WIN_STRATEGY.md").read_text()
walkthrough = (ROOT / "docs/SHOWCASE_LIVE_WALKTHROUGH.md").read_text()
readme = (ROOT / "README.md").read_text()

def must_have(label, text, terms):
    for term in terms:
        assert term.lower() in text.lower(), (label, "missing", term)
    print("PASS: static contract", label, len(terms), "markers")

must_have("five approved competitors", scorecard, [
    "Bifrost", "LiteLLM", "Portkey", "agentgateway", "TrueFoundry",
    "Enterprise", "MCP", "independent", "source-main", "NOT RUN",
    "signed", "at most once", "UNKNOWN", "n8n 2.48.5",
    "not a published benchmark", "TALON_BUYER_WIN_STRATEGY.md",
])
assert "| **Langfuse**" not in scorecard and "| **Helicone**" not in scorecard, "Old vendors must not appear as competitors"

must_have("all cases and challenger objections", scorecard, [
    "Case A", "Case B", "Case C", "Case D", "Case E", "Case F",
    "People Analytics", "Customer Support", "Shopify", "OrderDesk",
    "Document Processing", "ACME", "buyer", "Fail condition",
    "not tested", "company policy", "approval", "zero",
])
must_have("product thesis and explicit focus", strategy, [
    "control plane for company AI use cases", "cost control", "reliability",
    "shared policy", "session understanding", "proof layer",
    "300–1,000", "Shopify", "second", "UNKNOWN", "source",
    "0–30 days", "30–60 days", "60–90 days", "North-star",
    "Kill", "No invented", "not exactly-once",
])
must_have("existing ACME truth contract", walkthrough, [
    "COMPETITOR_PROOF_SCORECARD.md", "TALON_BUYER_WIN_STRATEGY.md",
    "seven", "Approvals (read-only)", "Talon-forwarded",
    "n8n 2.48.5", "2.30.4", "Registered", "Loaded",
    "Connected", "Governed", "independent", "v1.17.0 stable",
    "NOT RUN", "UNKNOWN", "override", "refund",
])
must_have("overview navigation", readme, [
    "COMPETITOR_PROOF_SCORECARD.md", "TALON_BUYER_WIN_STRATEGY.md",
    "Shopify-style", "read-only", "Approvals", "2.48.5", "2.30.4",
    "legacy", "v1.17.0",
])
for obsolete in ("six pages", "six-page", "competing approval inbox"):
    assert obsolete not in walkthrough.lower(), ("walkthrough", "obsolete", obsolete)
assert "not exactly-once external" in walkthrough, "missing at-most-once business effect boundary"
assert "no comparable feature documented" not in scorecard.lower(), "absence-of-evidence fallacy"
print("PASS: only static claim consistency; actual release, provider, app, reviewer and finance runtimes NOT TESTED by this check")
