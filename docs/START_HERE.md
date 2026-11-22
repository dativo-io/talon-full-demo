# Start here — Dativo Talon Full Demo

**One company, several AI applications, one operating layer.** This is a shareable entry point for someone who has not worked on Talon. You do not need to install anything to understand the demonstration.

[Talon](https://github.com/dativo-io/talon) is the control plane for a company's **AI use cases**. It provides common **cost controls, reliability behavior, shared policy, and session visibility** for requests routed through it. Signed, verifiable evidence explains its decisions; evidence supports audits but is not itself a compliance guarantee.

**This repository is not the Talon product distribution.** It contains independent, synthetic, production-shaped applications plus the scripts and CI that test whether Talon really governs them. The applications retain their own business logic and backend security.

## A company with four different use cases

| Existing application | Useful job | What Talon adds | Explore |
| --- | --- | --- | --- |
| Customer Support | Look up fictional orders and prepare a support response | Company rules for PII and refund decisions, separate approval and controlled dispatch | [Shopify/n8n support](../integrations/n8n/shopify-support/README.md) |
| People Analytics | Explore aggregated workforce trends in a browser | Governed HR tool access; employee export blocked before dispatch | [Workforce example](../cases/people-analytics-copilot/README.md) |
| OrderDesk / Engineering | Diagnose and repair a local PostgreSQL staging incident | Explicit action authorization, independent review and replay protection | [Incident example](../cases/claude-postgres-incident/README.md) |
| Document Processing | Summarize synthetic documents | Session spending visibility and denial of a later request over budget | [Document workflow](../integrations/n8n/README.md) |

The important story is **not** any particular integration or feature. It is that different applications keep their own purpose while company-wide controls and verifiable decisions can be operated together. n8n is an orchestrator used by some cases, not another AI use case.

## Choose the path that fits you

- **Understand the concept (no setup):** Read the [short repository overview](../README.md), then the [demo catalog](DEMO_CATALOG.md). This is enough for an introductory conversation.
- **Follow one application end to end (Linux + Docker):** Use the [People Analytics operator playbook](../cases/people-analytics-copilot/PLAYBOOK.md). It is an **example**, not a prerequisite or the definition of Talon. Default GUIDED mode uses fictional data and needs no paid model key.
- **Check the multi-application claim (technical):** Review the [ACME journey](DEMO_EXPERIENCE_INDEX.md), [test matrix](TEST_MATRIX.md) and [GitHub Actions for the repository](https://github.com/dativo-io/talon-full-demo/actions). The isolated tests and one-installation fleet test provide different kinds of evidence.
- **Evaluate a specific application:** Follow its linked README above. Some individual guides include historical compatibility material; their current-vs-historical status is marked.

## What the proof does — and does not — establish

**Demonstrated by source-built/current-main acceptance:** a single Talon installation can apply shared policy to four distinct use-case identities; a real local DuckDB/PostgreSQL fixture and independently counted synthetic commerce/model effects can be compared with Talon's signed records; and the native read-only Operations Console can show the resulting activity. See the [test matrix](TEST_MATRIX.md) for the exact test and its status.

**Not demonstrated by those tests:** a persistent customer production installation of all four complete UIs, paid inference, a real Shopify payment, or a full Claude Code/OpenShell end-to-end environment. Do not present a historical prerelease check as proof that current `main` works, or a source build as a published stable release.

**Security boundary:** Talon only governs model/MCP/action traffic that actually passes through it. It does not control a direct shell command, database query, browser action or API call that bypasses Talon. An asserted session ID is correlation, not authentication; HMAC records are tamper-evident, not immutable; session budget caps may be soft.

## How to reproduce today's behavior

For **active source-built demos**, resolve the current [Talon `main`](https://github.com/dativo-io/talon/tree/main) at execution time, record its exact SHA/checksum for that run, and let integration tests fail visibly on incompatibility. There is **no permanent Talon source SHA required for active demos**. Historical pinned RC2 checks remain labeled as such. See the [operator playbook](../cases/people-analytics-copilot/PLAYBOOK.md) or the [repository commands](../README.md) for setup; a passing CI check is not a substitute for your own environment's acceptance.

**For a first conversation:** choose whichever case is closest to the reader's work, show the useful business result, then one Talon decision, the independent downstream outcome and the signed evidence. The wider value is the shared operating model across all four.
