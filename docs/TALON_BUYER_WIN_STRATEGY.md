# Talon buyer-win strategy — proposed CTO/CPO decisions

*Decision memo | 2026-11-20 | Internal strategy, not committed product promises. Source: authoritative product thesis/MVP/operator-boundary documents and current Talon / Full Demo code and CI; competitors verified against their current vendor documentation. External product descriptions are vendor claims, not independently tested alternatives. Owners: Product + Engineering.*

## Executive decision

**Category:** Talon is the **control plane for company AI use cases**. Do not rename the category to "AI gateway", "tool firewall", "agent framework", "compliance platform", "signed evidence ledger", or "PII proxy". In public say **AI use case**; CLI/YAML says **agent**. One `agent.talon.yaml` = one use case/identity/active key; one `talon.config.yaml` is the shared organization policy/infrastructure baseline; no second invented product model.

**Buyer promise:** *Introduce your next production AI application without independently rebuilding its budgets, reliability behavior, company policy, operational visibility and controls for consequential actions.* The four entry pillars are **cost control, reliability, shared policy and session understanding**. Native Action Gateway lets the company safely approve and dispatch consequential actions at supported boundaries. Signed/verifiable evidence is the **proof layer**. Self-hosting, regional/privacy requirements and compliance-support are differentiators and trust accelerants, not the market category.

**Safety contract:** Talon has **at-most-once dispatch within a supported durable boundary, not exactly-once external effects**. After an ambiguous `UNKNOWN`, reconcile the downstream system before any further attempt; human approval authorizes the operation but never dispatches it directly.

**Why it might win:** the alternative is a gateway plus separate application-level review/dispatch engines, event logs, policy implementations and runbooks. We must **measure** whether Talon removes integration and operating burden while meeting the customer's threat model. Bifrost has signed audit logs and MCP approval; TrueFoundry offers MCP human approvals; Portkey has organization policy and agent registry; Solo can inspect MCP tool parameters; LiteLLM has robust MCP/key controls. Never claim those features are exclusive. See [competitive proof scorecard](COMPETITOR_PROOF_SCORECARD.md).

**Current purchase verdict:** Technically promising for a controlled pilot of Shopify-style Customer Support; not yet production-ready for consequential financial effects or a fully integrated four-use-case flagship. The passing source-built n8n + synthetic ledger test is a useful engineering proof, not a published v1.17.0, live Shopify, real-money or multi-app rollout.

## 1. Choose the first buyer, not the largest possible TAM

| Decision | Product recommendation | Why | Discovery falsifier |
| --- | --- | --- | --- |
| **Beachhead buyer** | CTO / VP Engineering / Head of Platform at EU-centric **300–1,000 employee** company running **2–8 production AI use cases**, with ownership fragmented across functions | Owns engineering risk, repeated integration cost and rollout decisions; strong second-use-case story | These leaders already have low-cost standardized control, no new action risk or no deployment authority |
| **Champion** | Senior platform engineer / technical lead who owns gateway, secrets, reliability or incident response | Can perform real install, route an app and independently verify evidence | Integration requires rebuilding the application or paid services beyond their influence |
| **Urgent trigger** | New AI use case with refunds, operations, account changes or other consequential effects; secondary triggers are spend spike, data leak review or failed provider | A decision/action boundary has more differentiated economic value than generic model routing | Customer does not trust external action dispatch or has adequate in-app policy/approval |
| **Initial industries** | E-commerce/customer operations; B2B SaaS with internal automations, document workflows and operational assistants | Concrete revenue/risk outcomes, realistic synthetic staging and independently counted effects | Strict payment vendor restriction prevents Talon insertion; customer requires mandatory HA/SSO beyond current contract |
| **Deprioritize** | Single-app teams buying cheapest model gateway; RAG-only evaluation teams; compliance-only procurement; enterprise infrastructure replacement seeking multi-region HA from day one | Competitors better serve these needs; long feature-comparison sales cycle | They repeatedly have an immediate, measurable multi-use-case control problem despite apparent mismatch |

**Do not redefine the ICP using legal/compliance labels.** EU sovereignty/self-hosting matters when a qualified CTO asks where data and keys reside; it is not, by itself, a purchasing reason. Avoid guaranteeing GDPR/EU AI Act outcomes.

## 2. Win a narrow job-to-be-done, then expand

**The wedge is "govern a production business action without creating a second authorization system."** Shopify-style support is the first economic entry point, with no real payment execution during initial self-service evaluation. The customer has an existing support workflow and the next challenge is a bounded refund. Show: useful draft → independently verified eligibility → company amount restriction → approved exact operation → Talon-controlled claim/dispatch → counted test-store or synthetic result → independently verifiable timeline. `UNKNOWN` is a valid state requiring reconciliation; approval alone does not dispatch.

**The expansion is "use the same operating layer for a second application."** A genuinely different People Analytics workload should inherit the same *applicable* company-level provider/data restriction while having its own identity, budget and permission overrides. Demonstrate the first app remains connected and governed. Repeat with Document Processing cost admission, then OrderDesk bounded engineering actions. Do **not** copy an application-specific refund rule into HR and call it inheritance.

**Buyer journey:**
1. Evaluate an anonymous, digest-pinned public Talon artifact and transparent boundaries (no source build marketed as published).
2. Connect an **existing** Customer Support application; obtain real request/decision evidence before touching financial operations.
3. Introduce an eligible, safely isolated synthetic action: allow / independent review / deny, plus replay, changed args, restart and `UNKNOWN`; never equate HTTP success with payment settled.
4. Connect People Analytics under the same mandatory policy, using a second native `talon agents add`/identity; verify registered, loaded, connected and governed separately.
5. Investigate a failure and cost decision from **one native seven-area read-only Console** (Overview, AI Use Cases, Approvals, Sessions, Costs, Configuration, System), CLI and signed evidence. Review decisions stay in the separately authorized native reviewer interface; console never writes policy/approval.
6. Complete production-readiness review, owner assignment, supported backup/verify/restore and bounded pilot acceptance. Talon core release remains independent of Full Demo.

## 3. What to ship, and what NOT to ship

| Tier | Deliver or harden | Do not build in this tier | Rationale |
| --- | --- | --- | --- |
| P0 — dependable product | Complete stable v1.17.0 official binaries/images with verifiable digests; single-node persistent quickstart/runbook; native use-case registration and rotation; no-secret console pairing; correct effective company policy | Another demo bootstrap/reviewer/approval engine; "source-main is a release" workaround | Without a repeatable artifact installation the product is not buyable |
| P0 — action contract | Generic trusted action schema, exact decimal/argument identity, independent reviewer credentials, policy allow/deny/review, durable operation/claim, `UNKNOWN`, independent adapter effects, signed lifecycle and explicit recovery | Product-specific "refund module"; exactly-once external effect guarantee; broad arbitrary tool magic | Differentiation requires enforceable semantics, not a tool deny prompt |
| P0 — customer proof | Supported official n8n stock-node path; **tested two real n8n workflow graphs or a deliberately packaged and tested combined install**; Shopify-style read/draft/handoff; second HR application in same persistent runtime; measured integration | "Four use cases" registry-only cards, pre-seeded dashboards, simulated finance called LIVE | Converts flagship from promise to independently reproduced proof |
| P1 — operator operations | One clear session/action story; policy source, denies and actual attempts; precise costs/UTC windows; read-only Approvals; native CLI/API/UI parity; backup/restore/replay acceptance | Second UI write surface; custom demo control plane; broad BI analytics suite | Reduce incident investigation cost instead of chasing tracing breadth |
| P1 — workflow adapters | One outstanding community-ready n8n reference; one customer-support integration recipe; one OpenAI-compatible and one Anthropic route; useful HTTP webhook patterns | Dozens of framework connectors or an agent development framework | Customers already have apps; "connect not rebuild" |
| Later, only if validated | Multi-instance HA, identity/SSO enterprise controls, multiple regions, formal attestations, developer SDK or broader framework support | Memory/vector DB, A2A/trust mesh, provider-optimizer parity, fleet AI-generated health, full GRC | Outside current wedge; a buyer asking for these first is likely not the launch ICP |

**De-risk support carefully:** an isolated *synthetic* refund adapter and reviewable proposal are useful without a live Shopify write. A real Shopify test-store dispatcher is a separately authorized technical security milestone, not a condition for running the first no-money demo. Do not imply that Shopify read token can dispatch writes.

## 4. Competition: win by measured composition, not invented feature gaps

| Rival | Rational reason to choose it | Talon must outperform on this measurable customer task | Why Talon may lose |
| --- | --- | --- | --- |
| **Bifrost (Maxim AI)** | OSS gateway with model/MCP governance, signed audit, tool approvals and reusable access profiles | Existing application business-action **operation** (exact arguments, separate reviewer, durable claim/unknown, evidence joined to synthetic ledger) and second-app integration with fewer independently managed systems | Feature breadth/OSS community and current routing/security stack already sufficient |
| **LiteLLM** | Very broad provider support, virtual keys, budgets, reliable gateway/MCP, familiar ops | Policy-to-business-effect across model + action path with less custom approval/ledger code; one session explanation | If customer has no consequential actions, LiteLLM already addresses the job |
| **Portkey** | Agent registry, org policies, MCP governance, routing, tracing and an established platform | Lower setup burden for two **pre-existing** applications; test same baseline + action lifecycle instead of comparing checklist breadth | Mature dashboard and integrations or existing Portkey deployment win |
| **Solo.io agentgateway** | Policy engine for HTTP/MCP/A2A, CEL guardrails, external auth and strong platform extensibility | Complete operation/reviewer/durable state out of box vs building/integrating external services; repeatable app-first runbook | Sophisticated platform teams prefer policy building blocks and Kubernetes ecosystem |
| **TrueFoundry** | Model/MCP gateway, agent identity, built-in MCP human approval, enterprise deployment | Exact argument-binding, approval-vs-dispatch separation, reconciliation and signed **independent effect** without inventing new state engine | Existing TrueFoundry approval/operation workflow may meet requirements; integrated enterprise operations more mature |

Treat vendor pages as **capability claims**, not a PASS in a head-to-head test. Do not use `no comparable feature documented` to claim absence. Query the exact vendor feature/edition/implementation and demand a demo with same synthetic ledger, retry/UNKNOWN and independent reviewer contract.

## 5. How we measure buyer value

**North-star product metric — Active Governed AI Use Cases (AGUC):** count distinct production use-case identities with actual intercepted traffic in the last 30 days and independently attributable Talon policy/operations evidence. **Do not** count registered-only configurations, generic simulated sessions or mere permission-denial volume. Break out customer-confirmed *value-bearing governance events* (budget stop, valid fallback, prevented forbidden action, correctly authorized business action) rather than maximizing block counts.

| Funnel / outcome | Proposed target to validate, NOT measured fact | Instrument / acceptance |
| --- | --- | --- |
| Time to first governed request | Prepared-host install and pair **<3 minutes**; first existing use case **<5 minutes** | Operator command timestamps, installed tag/digest, actual intercepted request + evidence; disclose prefetch/test-fixture prep |
| Second-app integration | **<2 minutes** after configuration prep, using same unchanged applicable mandatory rule | Before/after policy, own key/identity, both apps live, zero duplicate policy engine |
| Denial diagnosis | **<1 minute** from actual denial/session to loaded rule + independent signed evidence | User observed investigation, not a script that already knows answer |
| Repeatability | **At least 90%** of assisted technical pilots reproduce the minimum two-app journey without developer intervention; sample size >=10 | 10 consecutive external environment pilots, recorded setup failures, exceptions and help needed |
| Operations | No undocumented lost operations or silent retry of `UNKNOWN`; backup/restore and replay pass controlled incident drill | Separate effect ledger, immutable operation identity/durable state, signed recovery receipts |
| Buyer activation | At least **3 of first 5 qualified pilots** agree to a defined production rollout (hypothesis) | Product decision recorded by actual buyer and named owned use cases, not demo views |
| Buyer differentiation | **>=3 of 5** qualified competitive evaluations can name a specific task Talon removes relative to current stack | Structured win/loss interviews: existing tools, additional services, engineering hours and risk |

Do not translate engineering e2e duration into "customer installed in three minutes"; npm/Docker/build/image prefetch and keys must be itemized.

## 6. Go-to-market and pricing experiments

**Motion:** technical founder-led discovery → 20-minute verified buyer demo → 30-day bounded design-partner pilot → written go/no-go. Secure a technical champion and an economic buyer before costly integration. Prefer two real applications with owners over broad organization demos.

**Lead hook:** *"How many separate controls, approval systems and logs will you maintain when your third AI application goes live?"* Offer a five-minute "AI-use-case inventory / control duplication" discovery, then show one live policy-to-business-outcome. Avoid "GDPR-ready AI gateway" or claims of cost savings without customer baselines.

**Public proof assets:** 90-second buyer scenario, exact tagged install, one runnable reference workflow (or explicitly two documented imports), same-run verification manifest, negative controls, reproducible CI, one-page limitations, and competitor comparison showing **where Talon loses**. A community template drives discovery but must not pretend to perform refund execution before test-store validation.

**Commercial packaging hypotheses:**
- Free OSS: one supported self-hosted runtime, core policy/cost/reliability/session evidence and canonical developer integrations. Do not deliberately cripple trustworthy enforcement.
- Paid *support/operations* offer only after actual demand: installation assistance, response SLA, operational support, migration help and optional organization capabilities users request. Clarify what is actually open-source vs paid before pricing pages.
- Test **annual support contract vs per-active-production-use-case** pricing in discovery. Avoid usage-per-token tax competing with gateway providers; avoid seat-based reviewer pricing until customer interviews validate it.
- Ask each design partner: current gateway + tracing + action workflow cost, engineering days added per use case, cost of near-misses, who approves spending and what makes them switch. **No invented price points or savings ratios** before these interviews.

## 7. Sequence and kill / change-pivot criteria

### 0–30 days — complete product truth
- Finish release pipeline and exact digest verification for the full 1.17.0 contract; RC2 must not count if only draft/absent.
- Reconcile existing open PRs and historical pins; all release-focused test lanes must be green **and actually execute the claimed binary**.
- Reproduce native registrations + two connected apps in one persistent runtime; real company rule inherited and tested, first app still operating.
- Finish Action Gateway/Shopify synthetic ledger integration into a documented **user-repeatable** setup; prove failure/UNKNOWN/restart with native operations.
- Publish explicit coverage matrix (GUIDED vs LIVE vs TEST-STORE) and buyer video with no unverified effects.

### 30–60 days — five design-partner interviews and two live pilots
- Recruit at least five EU midmarket CTO/platform owners with multiple existing production AI uses; prioritize one with regulated operational actions.
- Observe **unassisted** setup/recovery and collect time-to-first/second use case, per-app code change, duplicate controls eliminated, incidents diagnosed.
- Ask for a comparable demonstration from existing gateway/provider; do not declare victory without alternatives.
- Refine docs/CLI/adapter only where buyer fails; resist console or framework-feature detours.

### 60–90 days — decide repeatability
- Convert at least two pilots into weekly governed traffic and one consequential synthetic/prod-approved operation, with named owner and verified evidence.
- Publish a factual case study with before/after duplicated plumbing and support effort (with customer permission).
- If <3/5 pilots cite real added value or require extensive custom work, **narrow** the wedge to an embeddable Action Gateway add-on rather than full gateway replacement.
- If buyers consistently prioritize route price/performance and never need action review, **do not chase** Bifrost/LiteLLM breadth. Reassess category/ICP.
- If the native reviewer/operation semantics cannot be made reliable under crash/UNKNOWN and security testing, **do not ship real monetary dispatch**.
- If buyers demand HA/SSO before any trial, either choose a narrower segment or explicitly plan enterprise readiness **after** validating value.

## 8. Decision boundary and current proof status

- **Proven in prior CI:** source-built pinned Talon + real n8n 2.48.5 + synthetic Shopify/provider/ledger; €25 allow, €249 independent approval, €750 deny, signed operation lifecycles and replay/conflict; source-built HR model+MCP path and HR denied export in separate jobs. These are separate from an official stable release and a four-app persistent shared fleet.
- **Not accepted:** real Shopify test-store transaction, real paid provider fallback in integrated support, published v1.17.0 end-to-end proof, buyer-facing paired seven-page Console on that release, multi-app common-policy adoption, complete OrderDesk Claude/OpenShell C01–C12 and native production restore.
- **Security:** supported intercepted boundaries only; no arbitrary coding-agent shell/file/browser control. A verified HMAC detects changes *relative to its signing key*, not immutable/auditor-independent custody. Approval authorizes; Talon may dispatch at most once within supported durable state; an external system may process an unknown request, so reconcile before retrying. Budget admission is estimate-based, not an exact invoice ceiling.
- **Earlier 2026-07 project notes** contain implementation/roadmap statements that may be outdated after core-main PRs #562–569. Product thesis/four-pillars/identity/boundary remain authoritative; **validate executable syntax and shipped semantics against the selected official artifact**.

## Sources for customer comparison (reviewed 2026-11-20)

- Bifrost [governance](https://www.getmaxim.ai/resources/governance), [MCP gateway](https://www.getmaxim.ai/mcp-gateway), [pricing/edition split](https://www.getmaxim.ai/pricing).
- LiteLLM [MCP access](https://docs.litellm.ai/docs/mcp_control), [keys/budgets](https://docs.litellm.ai/docs/proxy/virtual_keys), [fallback](https://docs.litellm.ai/docs/proxy/reliability).
- Portkey [Agent Gateway](https://portkey.ai/blog/agent-gateway/), [MCP](https://portkey.ai/features/mcp), [org tool provisioning](https://portkey.ai/blog/tool-provisioning-in-mcp-servers-controlling-ai-agent-access-in-production/).
- Solo [MCP auth](https://docs.solo.io/agentgateway/standalone/latest/documentation/configuration/security/authorization/mcp-authz/), [guardrails](https://docs.solo.io/agentgateway/standalone/latest/documentation/mcp/guardrails/about/), [external auth](https://docs.solo.io/agentgateway/standalone/latest/documentation/configuration/security/external-authz/). **Verify Solo Enterprise vs OSS availability per capability.**
- TrueFoundry [AI Gateway](https://www.truefoundry.com/ai-gateway), [MCP human gate behavior](https://tfy.app/blog/mcp-tool-approval-human-gate-call-path), [approval documentation/explainer](https://www.truefoundry.com/blog/mcp-tool-approvals-explained).
