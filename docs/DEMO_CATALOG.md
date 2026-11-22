# ACME demo catalog — the executable cases

*Scope: four independent business applications governed by one Talon operating layer. [Start here](START_HERE.md) for a first-time reader; [test matrix](TEST_MATRIX.md) for current acceptance. The November 22 historical source-built run used producer commit `156188dea65cb6feab01aa92093a00e7717a6dd6`; current CI resolves Talon `main` anew per run and records the SHA. The original customer PRs #45, #46, #52 and #51 are merged. This catalog distinguishes real Talon execution from mocks, proposals and released-artifact claims.*

The business promise is to take **four existing applications** and adopt one shared Talon policy/identity/evidence layer without replacing their business logic. Historical single-installation acceptance: [PASS 45014911307](https://github.com/dativo-io/talon-full-demo/actions/runs/45014911307) (one Talon process, four native use-case keys, real local DuckDB and PostgreSQL, separately counted synthetic merchant and document providers, 41 signed records, eight action lifecycles, paired native Console). Current repo automation re-tests this contract.

## Four production-shaped, synthetic applications

| ACME owner / case | Application source and direct acceptance | Talon differentiator | Acceptance and limitations |
| --- | --- | --- | --- |
| **Support Ops · Customer Support** | [n8n Shopify-style reference](../integrations/n8n/shopify-support/README.md), [real n8n 2.48.5 harness](../integrations/n8n/shopify-support/test-n8n.sh) | Company PII block; typed €25 allow, €249 separate independent review, €750 company deny; claim/replay/ledger/signatures | Real imported workflow and Talon gateway; **synthetic** Shopify order, upstream model and refund ledger. Stock-node read/draft and separate official action graph; not single community import, no real payment or email |
| **HR · People Analytics** | [DuckDB / workforce application](../cases/people-analytics-copilot/README.md), [governed MCP acceptance](../scripts/test-people-analytics-talon.sh) and [Console/browser](../scripts/test-people-analytics-operator-console.py) | Authenticated `POST /mcp`; per-agent tool discovery; approved aggregate; policy-denied export before dispatch; after-dispatch SQL failure UNKNOWN; signed evidence | Real HR service and browser/isolated Compose; deterministic/credential-free upstream for default tests, actual OpenAI opt-in |
| **Eng on-call · OrderDesk** | [PostgreSQL staging outage and bridge](../cases/claude-postgres-incident/README.md), [fixture](../cases/claude-postgres-incident/validate-fixture.sh), [HTTP Action Gateway](../cases/claude-postgres-incident/validate-talon-actions.sh) | Company volume-delete DENY, separate on-call approval, staging-only revision repair; production 1000 rows unaffected; durable intent/replay/UNKNOWN | **Real local PostgreSQL 16** and actual Talon HTTP action proof. **NOT RUN:** actual Claude Code ↔ OpenShell sandbox same-hop C01–C12; no claim of universal shell/egress governance |
| **Operations · Document Processing** | [n8n quarterly workflow](../integrations/n8n/quarterly-compliance-workflow.json), [n8n integration guide](../integrations/n8n/README.md), [source-built session budget](../scripts/test-live-talon.sh) | Two priced requests admitted, third stopped at Talon **before** upstream; signed session + independent count | Real Talon admission in fleet with deterministic synthetic model. The historical n8n 2.30.4 clean-import flow is a separate mock/fixture test, **not** a simultaneously operating fourth UI in the shared fleet |

**One company, not one app:** `scripts/test-acme-one-fleet.py` brings together four distinct Talon identities, a single company policy and signed store. `n8n` is infrastructure inside two cases, not a fifth application. Native Console areas are Overview, AI Use Cases, Approvals, Sessions, Costs, Configuration and System; all read-only. Actual approvals occur through authorized reviewer CLI/API.

## Other existing demos (preserved, not promoted)

| Example | Where it lives | What can be honestly shown |
| --- | --- | --- |
| Historical support-resolution approval workflow | [n8n flow](../integrations/n8n/customer-support-resolution-workflow.json), [legacy gallery](../README_LEGACY.md) | Deterministic mock clean-import and **separate demo-specific operator gate**, not native Talon refund authorization |
| Vendor-contract review | [n8n flow](../integrations/n8n/vendor-contract-review-workflow.json) | Document review and egress-policy fixture; real-provider path requires credentials; historical `2.30.4` |
| Zendesk adapter / app | [app](../integrations/zendesk-app/README.md), [adapter](../README_LEGACY.md) | Offline packaged ZIP and loopback adapter; **actual installed Zendesk browser NOT RUN** |
| GitHub Copilot CLI | [Copilot guide](../integrations/copilot/README.md), [legacy gallery](../README_LEGACY.md) | Historical MCP proxy contract; removed `/mcp/proxy` means **NOT current-main compatible** |
| OpenShell generic sandbox demo | [legacy gallery](../README_LEGACY.md), [OrderDesk acceptance contract](CLAUDE_POSTGRES_INCIDENT_CONTRACT.md) | Separate sandbox proof requires real OpenShell/Claude and verified workload hop; **NOT RUN** for current ACME |
| Billing, TokenEconomizer and additional research fixtures | [billing](../cases/billing-demo/README.md), [legacy catalog](../README_LEGACY.md) | Source study/compatibility exercises, not fifth or sixth ACME customer use cases |

## Navigation / decision

**Buyer:** [ACME 20–25 minute target journey](DEMO_EXPERIENCE_INDEX.md) → this catalog → [bounded proof transcript](TEST_MATRIX.md). **Engineer:** start with each application's README and its direct test script, then run `python3 scripts/test-acme-one-fleet.py` using [the main README's reproducible setup](../README.md). **Auditor:** check the exact producer SHA, actual run statuses, per-system counters, company-effective rule, independent approval and `talon audit verify --operation`.

Do not present a proposed client flow as a run, fake a Shopify payment, count a mock provider as paid inference, confuse UNKNOWN with DENY, or claim Talon governs a direct out-of-path shell/API request.
