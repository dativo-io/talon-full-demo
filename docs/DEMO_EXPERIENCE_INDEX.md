# Dativo Talon Full Demo — one coherent ACME journey

*Canonical customer journey for the **merged** four-use-case Full Demo main (PRs #45, #46, #52 and #51). **PASS:** source-built one-process company governance and signed proof. **NOT RUN:** all four complete app UIs concurrently on a persistent official stable release. Updated November 22, 2026 for Talon core main `156188dea65cb6feab01aa92093a00e7717a6dd6`. The published RC2 remains historical release evidence, not this architecture.*

**New-customer, source-pinned adoption recipe:** [ACME First Production Pilot — governed MCP and HTTP Action Gateway](GOVERNED_MCP_FIRST_PILOT.md). Component instructions plus a separate **passing shared, single-process governance run** ([real one-installation ACME acceptance (all three CI jobs passed)](https://github.com/dativo-io/talon-full-demo/actions/runs/45014911307)), but not an accepted official-release, full customer-UI deployment.

## Current adoption path — governed MCP, one canonical Action Gateway

**Exact integration baseline:** Talon main `156188dea65cb6feab01aa92093a00e7717a6dd6` (PR #589 merged), **source-built, not a stable release**. The supported MCP client endpoint is **`POST /mcp`** with the authenticated AI use-case key. The removed `/mcp/proxy` and `--proxy-config` are not options for a new customer. The HR service is an `actions.sources.hr` trusted MCP source with read-only aggregates executed in one call. Export is denied and must never reach HR; an HR SQL error **after** authorized dispatch is `UNKNOWN`, not an access-policy denial. A consequential MCP action first prepares an exact operation, then `talon_execute_operation` attempts a single dispatched effect; independent reviewers decide approvals *without dispatch*. Talon generates operation identities, binds arguments, and produces signed Action Gateway lifecycles; operation replay adds no effect, changed arguments conflict, and UNKNOWN stops blind retries. **OrderDesk's existing governed HTTP Action Gateway bridge is appropriate and is not rewritten as an MCP bridge.**

Start with **merged main**: [People Analytics](../cases/people-analytics-copilot/README.md), [OrderDesk](../cases/claude-postgres-incident/README.md), [Shopify/n8n](../integrations/n8n/shopify-support/README.md), plus the [four-case catalog](DEMO_CATALOG.md) and [test matrix](TEST_MATRIX.md). The earlier #45/#46/#51/#52 PR links remain provenance, not instructions to check out unmerged branches. Cite source-built, browser, Compose and counted-backend CI results when using the word **accepted**. A model/provider call outside Talon, direct shell access, or a raw application-to-backend request is not governed. A supplied `X-Talon-Session-ID` is only correlation, never authorization. The Operations Console reports observed MCP readiness and signed evidence; it is read-only, and reviewer decisions remain an authenticated CLI/API action.

**Minimal pilot contract:** company baseline in `talon.config.yaml` → native `talon agents add` for Support and HR → one distinct use-case key and `agent.talon.yaml` each → HR trusted MCP source on loopback → both apps actually send requests through Talon → confirm independent support/HR counters and signed `talon audit verify --operation`. A registered or configured agent is not proof that it is connected or governed. The HR Docker network, UI and seven-area native Console need the specific #46 browser/Compose acceptance, not just a CLI response.

## What the buyer should understand within 30 seconds

**ACME is one company with existing AI applications.** Talon sits at supported request/action boundaries and gives ACME a shared **company AI policy**, cost/reliability controls, per-use-case operational identities, session understanding, a single native read-only Operations Console and verifiable evidence. We do **not** replace ACME's applications or pretend Talon governs direct out-of-path activity.

**Promise to prove:** "We can introduce more AI applications without independently reinventing how we operate and control each one." The key buying test is adding the **second existing application** under an unchanged, applicable company rule, while the first remains genuinely working.

## One fleet — four apps, four owners, not five

| ACME application (business owner) | Useful job | Memorable Talon intervention | Outside Talon's scope / separate enforcement | Where to find the real consumer code |
| --- | --- | --- | --- | --- |
| **Customer Support** (Support Ops) | Look up a synthetic Shopify test order and draft a safe customer reply; evaluate requested refunds | Company amount deny >€500; independent exact review for >€50–€500; synthetic €25 allow/€249 review/€750 deny with signed action and counted ledger. Provider reliability/PII demonstration only where tested | Shopify read-only API credential, independent merchant eligibility, actual Shopify effect and customer email delivery | [Shopify reference](../integrations/n8n/shopify-support/README.md) — PR #52; separate older Zendesk/support examples remain historical |
| **People Analytics** (HR/data) | Real workforce aggregate through DuckDB-backed existing application | Talon intercepts HR MCP export request, rejects forbidden call before HR dispatch, signs evidence | SQL/backend authorization still independently rejects prohibited data access; direct DuckDB charts not Talon | [Workforce analytics](../cases/people-analytics-copilot/README.md) — PR #46 |
| **OrderDesk / Engineering** (Eng on-call) | Investigate and repair synthetic PostgreSQL staging credentials | Generic Talon company tool deny and exact staging repair action with outside on-call reviewer; actual production row/volume safety | OpenShell containment of shell/egress **is not Talon control**; current host-key preflight isn't Claude/OpenShell same-hop acceptance | [OrderDesk case](../cases/claude-postgres-incident/README.md) — PR #45 |
| **Document Processing** (Operations) | Produce useful document results and evaluate remaining budget | Priced next-request admission denial, no upstream call for blocked request, signed session | Partial output must actually exist; no hard invoice ceiling, no invented LLM result | [Document Processing / n8n flows](../README.md) and [walkthrough](SHOWCASE_LIVE_WALKTHROUGH.md) |

**n8n is orchestration inside Support and Document Processing, not a fifth AI application.** One `agent.talon.yaml`, one active Talon key and operational identity per AI use case; shared mandatory policy is in company `talon.config.yaml`. Configuration, registered use case, loaded policy, intercepted requests and verified enforcement are four different facts.

**Shared-company technical acceptance: PASS on exact main source.** [real one-installation ACME acceptance (all three CI jobs passed)](https://github.com/dativo-io/talon-full-demo/actions/runs/45014911307) executed four native use-case identities through **one running Talon**, with one `gateway.organization_policy`, independent business counters, one signed store/proof pack and one paired native seven-area Console. Support model traffic and HR MCP traffic reached different downstream systems under distinct keys; OrderDesk staging repair and Document Processing cost admission were also enforced. The run verified **41 signed records and eight valid action lifecycles**, and zero unauthorized export, oversized refund or volume-delete dispatches. It used a temporary CI installation with synthetic provider/Shopify finance and real local DuckDB/PostgreSQL; the actual n8n UI and Claude/OpenShell model runtime were **not** part of this shared process test (n8n 2.48.5 is tested separately). **Published official-artifact persistent deployment, four actual application UIs, restart/recovery and paid models: NOT RUN.** Do not represent this as fully customer-live.

**Native Talon core proof is stronger:** The [published RC2 release pipeline](https://github.com/dativo-io/talon/actions/runs/44881314831) passed its official **first/second use case onboarding, shared company policy, SDK traffic, independent action claims, seven-page Console, restart, cold backup/restore and key replacement** on the released binary/image. That proves *product primitives*, not our specific Full Demo ACME apps running together. Avoid both understating RC2 and overstating Full Demo.

## Two presentation formats; same evidence, no separate dashboard

| Format | Story and sequence | Exit criterion |
| --- | --- | --- |
| **First Production Pilot · 10–15 minutes (target)** | Existing support enquiry → native policy/evidence and synthetic refund decision → second **People Analytics** registration under same company policy → native Console sees both and source/decision | Official artifact with digest; two *independently connected and governed* use cases in **one persistent runtime**, real native identities, same-run business/decision evidence |
| **Full ACME · 20–25 minutes (target)** | Same pilot, plus scoped provider reliability/PII, document budget admission, OrderDesk staged incident and system recovery where actually proved | Four actually connected apps, one company baseline, meaningful results, signed evidence, independent downstream counters, no fake cost/availability; only claim fully live stages when passed |

Read-only native Talon Console **seven areas**: Overview · AI Use Cases · Approvals · Sessions · Costs · Configuration · System. It **does not** approve operations or edit policies. The independent reviewer uses authorized native CLI/API. No bespoke demo dashboard, reviewer inbox, policy editor or second action engine.

## Choose the truthful verification level

| Level | Permitted claim | Not permitted |
| --- | --- | --- |
| **SPEC** | Proposed acceptance and future operator steps | "This is already runnable end to end" |
| **GUIDED** | Deterministic fixtures and actual Talon enforcement, with visible fixture label | "Model/provider generated it live" |
| **TAG-BUILT RC2 SOURCE** | Executable compiled from immutable `v1.17.0-rc.2` commit `3f3f20dff910dc2416c8d82467de2d4e2dd8acc5`, real n8n and synthetic services | "Verified official binary digest" or "published release passed" |
| **PUBLISHED RC2 BINARY** | Actual artifact downloaded with release manifest SHA-256, executed against named scenario | "Stable v1.17.0", LIVE model, real Shopify payment |
| **LIVE PROVIDER / TEST STORE** | Actual authorized inference and/or explicit development-store test request with independent observed response | Exactly-once external financial effect, assumed payout settlement, universal out-of-path governance |
| **ACME ACCEPTED** | Official digest-pinned release + one shared persistent company deployment + two/four real apps (as claimed), paired Console, native restart/recovery, same-run session/action evidence and business counters | Claims based only on isolated green PR workflows |

RC2 is now a [published GitHub prerelease](https://github.com/dativo-io/talon/releases/tag/v1.17.0-rc.2). The Linux/amd64 SHA256 is `5ba2021a7da0ad704a4c3b21e319e05b96fa0347d7d43318ed30bead357ba47c`. **The published-artifact Full Demo run must still execute and pass; publication alone is NOT an acceptance PASS.** A GitHub Actions run whose availability check succeeds but consumer job skips is **not** a runtime PASS.

## Same-run evidence checklist — use for EVERY scene

```text
Company ACME | core provenance: exact git tag/commit OR release image/binary SHA256
Mode: SPEC / GUIDED / TAG-SOURCE / PUBLISHED-ARTIFACT / LIVE / TEST-STORE
Use case: business name, owner, separate native identity/key ID (never secret)
Baseline: effective, loaded company restriction + explicit use-case overlay
Session: real intercepted request/action IDs, actual provider/model/tool attempts
Verdict: allow / deny / review / approved / claim / dispatched / UNKNOWN as observed
Business outcome: independent HR/Shopify-synthetic/Postgres/document counter/result
Evidence: signed export and actual talon audit verify status from SAME run
Recovery: real restart/restore/replay if presented
Status: PASS / FAIL / NOT RUN; never infer from a prefilled screen or config
```

Be precise: **approval is not dispatch**; **at-most-once Talon dispatch is not exactly-once external effect**; a failed/timeout action may be `UNKNOWN`, requiring reconciliation before reattempt. Budget admission is estimate-based, not guaranteed provider invoice cap. Tamper-evident HMAC records aren't immutable or a compliance attestation. Only intercepted traffic/actions are governed.

## Operator/presenter links

- [**Verified published-RC2 Full Demo consumer acceptance (four component paths)**](RC2_CONSUMER_ACCEPTANCE.md)
- [Live walkthrough and scene-by-scene claims](SHOWCASE_LIVE_WALKTHROUGH.md)
- [Buyer-win strategy and decision gates](TALON_BUYER_WIN_STRATEGY.md)
- [Bifrost / LiteLLM / Portkey / Solo agentgateway / TrueFoundry scorecard](COMPETITOR_PROOF_SCORECARD.md)
- [Customer adoption friction and still-missing proof](CUSTOMER_ADOPTION_FRICTION.md)
- [Original full ACME roadmap and acceptance issue #47](https://github.com/dativo-io/talon-full-demo/issues/47)
- [Shared runtime #48](https://github.com/dativo-io/talon-full-demo/issues/48), [Support+document #49](https://github.com/dativo-io/talon-full-demo/issues/49), [presenter #50](https://github.com/dativo-io/talon-full-demo/issues/50)

## What makes the merged repository "great" rather than merely green

1. **Start from customer value:** a helpful support result and actual employee aggregate, then show the company rule and business effect. A model refuses a request by itself is **not** Talon intervention.
2. **No story drift:** single ACME, four apps, one effective shared policy, one identity per use case, seven read-only Console areas; no fifth n8n app, alternate approval service or invented business numbers.
3. **One click to the evidence source:** every demo claim links the actual session, operation, signed verifier and independently measured outcome from the **same execution**. Unsupported fields are visibly blank/NOT RUN.
4. **Operator honesty:** write down how the binary was obtained, whether CI executed a source build or published artifact, which provider is deterministic and whether a real external payment occurred (normally **no**).
5. **No conflicting launch commands:** honor official native registration, published-image no-clone quickstart and supported persistent/backup/restore path; historical per-case scripts remain labelled as such until migration is tested. A demo consumer must not invent Talon product interfaces.
6. **Documented merge rehearsal:** CI assembles PRs #45/#46/#52/#51 on main and checks the resulting repository's docs/tests so individually green branches cannot hide contradictions. That rehearsal does not replace real unified ACME runtime acceptance.
