# Full Demo documentation

The **source of truth for current demonstrations** is [the repository README](../README.md), followed by the [four-use-case catalog](DEMO_CATALOG.md) and [runtime acceptance matrix](TEST_MATRIX.md). Historical component instructions remain accessible but are never promoted to current release acceptance by implication.

## Start with a buyer

| Read this | What it answers |
| --- | --- |
| [ACME journey and verification levels](DEMO_EXPERIENCE_INDEX.md) | What an operator sees across four existing ACME applications, with actual vs target status |
| [Current demo catalog](DEMO_CATALOG.md) | Where the real code lives; which paths need keys, Docker, browser, or actual payment credentials |
| [First Production Pilot](GOVERNED_MCP_FIRST_PILOT.md) | Real native Talon identity, company baseline, governed MCP and HTTP Action Gateway onboarding |
| [Live walkthrough spec](SHOWCASE_LIVE_WALKTHROUGH.md) | 10–15 / 20–25 minute target narrative and its remaining non-runnable UI/release gates |
| [Buyer-win strategy](TALON_BUYER_WIN_STRATEGY.md) · [competitor proof scorecard](COMPETITOR_PROOF_SCORECARD.md) | Differentiation from existing gateways without overstating untested comparisons |

## Run or audit the evidence

| Read this | What it contains |
| --- | --- |
| [Test matrix and reproducible current-main commands](TEST_MATRIX.md) | GitHub Actions lanes, source SHA, synthetic vs real boundaries, PASS/NOT RUN |
| [Validation guide](VALIDATION.md) | Local source/build/test prerequisites and historical test paths |
| [RC2 consumer acceptance](RC2_CONSUMER_ACCEPTANCE.md) | Historical checksum-verified prerelease evidence, distinct from current-main governance |
| [Audience views](AUDIENCE_DEMOS.md) | Original per-case presenter commands; **legacy** scripts may not work on merged Talon main |

## Application-owned sources

**Active source-pinned governance cases:** [People Analytics / DuckDB](../cases/people-analytics-copilot/README.md) · [Shopify/n8n support](../integrations/n8n/shopify-support/README.md) · [OrderDesk/PostgreSQL](../cases/claude-postgres-incident/README.md) · [n8n document-processing workflows](../integrations/n8n/README.md). The documentary budget is proven in the shared fleet with a deterministic synthetic provider; the original n8n document client runs a separate clean-import fixture.

**Other integrations / historical gallery:** [Zendesk](../integrations/zendesk-app/README.md), [legacy Copilot](../integrations/copilot/README.md), [n8n historical library](../integrations/n8n/README.md), and the [unabridged previous README](../README_LEGACY.md).

## Non-negotiable trust boundaries

Talon controls only intercepted model/MCP/action requests. The new-client MCP contract is authenticated `POST /mcp` and the actual HTTP Action Gateway; removed proxy interfaces are not current. A native reviewer decision does not dispatch an operation; a later bound claim does. A signed lifecycle and a counted synthetic backend do not establish live payment execution. The native Console is **read-only**, even in its Approvals area. The source-built four-use-case [same-installation proof](https://github.com/dativo-io/talon-full-demo/actions/runs/45014911307) is not a published stable `v1.17.0` install, simultaneous four-client UI run, or genuine Claude/OpenShell C01–C12.
