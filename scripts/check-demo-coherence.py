#!/usr/bin/env python3
"""Check post-merge Full Demo consistency, not a runtime/release acceptance.

Intentionally run against a combined local tree with #45/#46/#51/#52 applied.
A green result can never prove an actual model, Talon or financial transaction.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
docs = ROOT / "docs"
index = (docs / "DEMO_EXPERIENCE_INDEX.md").read_text()
walk = (docs / "SHOWCASE_LIVE_WALKTHROUGH.md").read_text()
strategy = (docs / "TALON_BUYER_WIN_STRATEGY.md").read_text()
competitors = (docs / "COMPETITOR_PROOF_SCORECARD.md").read_text()

def require(message, predicate):
    assert predicate, message
    print("PASS coherent Full Demo:", message)

for name in ("Customer Support", "People Analytics", "OrderDesk", "Document Processing"):
    require(f"ACME includes {name}", name in index and name in walk)
for name in ("Bifrost", "LiteLLM", "Portkey", "agentgateway", "TrueFoundry"):
    require(f"approved competitor {name}", name in competitors and name in strategy)
for old in ("| **Langfuse**", "| **LangSmith**", "| **Helicone**"):
    require(f"obsolete competitor not a current scorecard row {old}", old not in competitors)

for rel in (
    "docs/SHOWCASE_LIVE_WALKTHROUGH.md",
    "docs/COMPETITOR_PROOF_SCORECARD.md",
    "docs/TALON_BUYER_WIN_STRATEGY.md",
    "docs/CUSTOMER_ADOPTION_FRICTION.md",
    "cases/people-analytics-copilot/README.md",
    "cases/claude-postgres-incident/README.md",
    "integrations/n8n/shopify-support/README.md",
    "integrations/n8n/shopify-support/shopify-support.workflow.json",
    "integrations/n8n/shopify-support/test-n8n.sh",
):
    require(f"integrated case/file present: {rel}", (ROOT / rel).is_file())

for name in ("Overview", "AI Use Cases", "Approvals", "Sessions", "Costs", "Configuration", "System"):
    require(f"Console area {name}", name in index)
require("Console review is read-only", "read-only" in index.lower() and "approval is not dispatch" in index.lower())
require("n8n is integration rather than fifth app", "not a fifth" in index.lower())
require("source-build does not assert published artifact", "tag-built rc2 source" in index.lower() and "published rc2 binary" in index.lower())
require("UNKNOWN and at-most-once are qualified", "unknown" in index.lower() and "at-most-once" in index.lower() and "not exactly-once" in index.lower())
require("two-app pilot is explicitly NOT yet accepted", "two-app" in index.lower() and "not a fully runnable unified" in index.lower())

# No broken local links within the canonical merged buyer index.
for link in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", index):
    base = link.split("#", 1)[0].split("?", 1)[0]
    if not base or "://" in base or base.startswith(("mailto:", "#")):
        continue
    require(f"index link target exists: {base}", (docs / base).exists())

workflow = json.loads((ROOT / "integrations/n8n/shopify-support/shopify-support.workflow.json").read_text())
require("Shopify Stage A export inactive", workflow.get("active") is False)
require("Shopify export is stock nodes", all(n["type"].startswith("n8n-nodes-base.") for n in workflow["nodes"]))
http = [n for n in workflow["nodes"] if n["type"] == "n8n-nodes-base.httpRequest"]
require("Shopify Stage A has only safe HTTP calls", len(http) == 2 and
        {n["name"] for n in http} == {"Read Shopify order", "Draft through Talon"})
serialized = json.dumps(workflow)
for dangerous in ("refundCreate", "orderCancel", "mutation Refund", "X-Shopify-Access-Token: synthetic", "talon_appr_cred_"):
    require(f"no mutation or reviewer credential in Stage A export: {dangerous}", dangerous not in serialized)

print("PASS: merged-document and workflow consistency ONLY; not a Talon runtime, RC2 artifact or ACME live verification")
