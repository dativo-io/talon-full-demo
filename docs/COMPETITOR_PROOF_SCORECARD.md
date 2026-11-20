# Competitive buyer-proof scorecard — all open ACME demo cases

*Reviewed 2026-11-20 | Internal adversarial procurement comparison; **not a published benchmark**, not a vendor hands-on test, and not evidence of market-share ranking. Buyers may combine two competing products. Implementation status refers only to independently observed Talon/Full Demo CI where specified. Supersedes the earlier Portkey/LiteLLM/Langfuse/LangSmith/Helicone selection. Approved competitors: **Bifrost, LiteLLM, Portkey AI, Solo.io agentgateway and TrueFoundry**.*

Strategy and sequencing: [Talon buyer-win strategy](TALON_BUYER_WIN_STRATEGY.md). Demo definitions: [ACME walkthrough](SHOWCASE_LIVE_WALKTHROUGH.md). The buyer promise remains **one company policy and operating layer across distinct AI use cases**, not "our LLM gateway is universally best."

**Version hygiene:** The historical joined development-only refund proof uses real **n8n 2.48.5** with a pinned Talon source-main build and synthetic Shopify/provider/ledger. An older Stage A path uses n8n 2.30.4 with a published v1.16.1 binary. Neither by itself proves a full v1.17.0 stable consumer journey; RC2 detection-only skip is not runtime acceptance.

## Evidence rules (apply to all competitors)

- **Vendor-documented** = official documentation or marketing confirms a capability. This does **not** mean we independently installed/tested it, and an enterprise-only feature is not assumed available in OSS. Lack of a feature in public documentation means **not verified**, not absent.
- **Talon demonstrated** = actual Full Demo/GitHub Actions runtime test with source commit/release provenance, explicit synthetic vs genuine external systems and independent downstream count. **Talon target** = no successful integrated acceptance yet. CI green on a static assertion is not proof of a runtime scene.
- A comparable experiment must use the **same** target existing app and exact threat model, policy, traffic, model/provider, business ledger, failure/retry conditions, key provenance and outcome counters. Otherwise report different configurations, not a winner.
- No invented price/latency/capability scores. Use the **buyer decision gates** below. No product is declared incapable of approximating Talon's solution through an application-specific service or adjacent component.

## Five credible alternative stacks

| Vendor | What its buyer already gets (documented) | Why Talon may **not** win | Critical question to ask the vendor |
| --- | --- | --- | --- |
| **Bifrost (Maxim AI)** | Model/MCP gateway, tool discovery/execution, deny-by-default per-key tool access, hierarchical budgets, identity/access profiles, governance and auditing. Its docs/marketing describe human gating and signed audit; verify OSS vs enterprise packaging. [governance](https://www.getmaxim.ai/resources/governance) · [MCP gateway](https://www.getmaxim.ai/mcp-gateway) · [editions](https://www.getmaxim.ai/pricing) | Existing OSS gateway and profiles may already centralize everything except business-state dispatch. Its audit capabilities undercut "only Talon has signed evidence." | Show exact `order_id/amount/currency` approval, state after approval (before execution), one durable claim and replay/UNKNOWN/independent finance effect using no parallel authorization engine. What is edition-gated? |
| **LiteLLM** | Large provider breadth, virtual keys/team budgets, cost attribution, fallbacks and key/team MCP permissions. Current MCP docs include `require_approval` tool-handling modes; do not claim that LiteLLM cannot manage MCP tools or that all approvals are absent. [virtual keys](https://docs.litellm.ai/docs/proxy/virtual_keys) · [MCP](https://docs.litellm.ai/docs/mcp) · [fallback](https://docs.litellm.ai/docs/proxy/reliability) | Existing LiteLLM + internal approval/ledger service may do the job with near-zero switching cost. | Which server-side durable operation store, independent reviewer, exact args, forward-only-on-claim and UNKNOWN reconciliation does the proposed LiteLLM *stack* provide? How much code runs outside LiteLLM? |
| **Portkey AI** | Agent Gateway with registry and org-wide control, routing, tracing, guardrails, MCP registry/tool policy, budgets and team integration. [Agent Gateway](https://portkey.ai/blog/agent-gateway/) · [MCP gateway](https://portkey.ai/features/mcp) · [tool provisioning](https://portkey.ai/blog/tool-provisioning-in-mcp-servers-controlling-ai-agent-access-in-production/) | Its company adoption story substantially overlaps Talon's; cannot pitch fleet registry, tool deny, failover or policy-in-one-place as unique. | Demonstrate signed `policy→operation→approval→claim→effect` including retry and restart without a separate workflow-owned authority, on **two existing applications**. Record actual integration effort. |
| **Solo.io agentgateway** | HTTP/LLM/MCP policy, external auth, CEL expressions and enterprise MCP guardrail processors that can inspect/change tool arguments. **Caveat:** public Solo policy docs say `mcp.tool.arguments` is available *post-request* and is **not** available in their MCP authorization rules; request-time argument guardrails are a separate mechanism. Edition matters. [MCP auth/CEL variables](https://docs.solo.io/agentgateway/standalone/latest/documentation/configuration/security/authorization/mcp-authz/) · [guardrails](https://docs.solo.io/agentgateway/standalone/latest/documentation/mcp/guardrails/about/) · [external auth](https://docs.solo.io/agentgateway/standalone/latest/documentation/configuration/security/external-authz/) | It offers a flexible infrastructure fabric for customers comfortable operating policy services; Talon cannot win a generic CEL or HTTP gateway comparison on breadth. | What additional state/approval/dispatch components produce one exact operation identity, `UNKNOWN`, and an independent effect count? Are required controls in Solo Enterprise or OSS? |
| **TrueFoundry** | AI/model/MCP gateway, agent identity/governance, observability and a documented human-in-the-loop MCP tool gate. A matched call can pause; a compatible caller processes approval metadata. [gateway](https://www.truefoundry.com/ai-gateway) · [human gate](https://tfy.app/blog/mcp-tool-approval-human-gate-call-path) · [MCP tool approval](https://www.truefoundry.com/blog/mcp-tool-approvals-explained) | Native HITL makes "we have approvals" an invalid differentiator; enterprise buyer may prefer its integrated stack. | After reviewer approval but before explicit dispatch, is business effect still zero? Can exact operation binding, durable at-most-once dispatch, `UNKNOWN`, reconciliation and signed independent outcomes be shown? |

**No blanket feature-superiority claim:** Bifrost/Portkey/TrueFoundry already market broad control-plane functionality. The test is the **total operational footprint** for governed business actions plus repeatable second-application onboarding.

## All-case matrix — customer alternatives vs Talon's current claim

The cells describe plausible competitor *paths*, not hands-on PASS/FAIL verdicts.

| Demo / buying job | Bifrost | LiteLLM | Portkey | Solo agentgateway | TrueFoundry | Talon acceptance state |
| --- | --- | --- | --- | --- | --- | --- |
| **People Analytics**: bound HR MCP data access | MCP per-key tools/filters | Per-key/team MCP controls | Agent/tool policy | MCP auth + enterprise guardrail processors | MCP RBAC + identity | **Separate case runtime passed:** bounded aggregates, denied export, independent SQL rejection, signed evidence. Shared company override across HR+support NOT RUN |
| **Customer Support reliability**: privacy and failover | Model routing/fallback/guardrails | Strong fallback/key budgets | Routing, guardrails, traces | LLM policy/routing | Model gateway/guardrails | Shopify draft uses **app-side minimization**; this is not proof of Talon redaction. Multi-candidate policy-valid LIVE fallback remains NOT RUN in joined path |
| **Shopify refund**: bounded operation | Model-proposed/tool execution; approval options | MCP/keys + customer-owned action state | MCP tool policy / customer approval service | Argument guardrail / ext-auth + action state | Native MCP HITL | **Source-main synthetic joined test passed:** €25 allow, €249 review, €750 deny, replay/conflict, signed lifecycle, independently counted fake finance; NOT a Shopify payment |
| **OrderDesk/Engineering**: safe repair | Coding-agent/MCP controls | Key/tool permissions | Agent/MCP registry/policy | Strong network/MCP policy hooks | MCP authorization and approval | PostgreSQL fixture + HOST-key Talon preflight passed; real Claude/OpenShell same-hop C01–C12 NOT RUN/NOT PASSED |
| **Document Processing**: budget stop | Hierarchical budgets | Team/key budgets | Usage/budgets | Traffic/rate limits; verify cost admission separately | Gateway budgets | Separate synthetic provider admission + signed evidence contract; official candidate/latest artifact compatibility under test; LIVE document work + cap NOT RUN |
| **Unified ACME**: adopt a second/third AI app | Shared profiles and keys | Shared proxy/key/team setup | Agent registry/org policy | Shared gateway policy fabric | Agent registry/identity | One customer-support runtime + separate HR fixture proven; **same shared persistent 2-app/4-app governance not accepted** |

### Scorecard interpretation

**We do not award numeric competitor feature scores without hands-on equivalence tests.** A vendor gets `Documented` only for an official source, `Validated` only after actually running the same contract, `Unknown` if not assessed. Talon gets `PASS` for a specific test/run only, `PARTIAL` when the relevant fixture runs but the claimed buyer path is missing, and `NOT RUN` when no matching evidence exists. Green unrelated CI never upgrades a row.

## Case A — People Analytics (PR #46): prove company inheritance, not generic tool deny

**Buyer objection:** "My data platform already enforces SQL grants. Portkey, Bifrost, Solo and TrueFoundry can restrict agent tools. Why add Talon?"

**Demo must show:** (1) existing DuckDB app producing a useful aggregate; (2) distinct real SQL/backend policy (bad SQL rejected by HR independently); (3) routed MCP allow and deny before dispatch, zero upstream export call; (4) actual signed Talon session/evidence and SQL/dispatch counter; (5) native fleet identity, **loaded effective company rule** and application-specific override; (6) **same** applicable mandatory company rule holding for *another existing* app under a separate key; show HR still works. Do not attribute fixed local charts or direct SQL to Talon.

**Fail condition:** a static permission YAML, configured-but-never-connected HR identity, app-owned SQL denial mislabeled Talon, or arbitrary cross-app rules copied manually. **Current status:** first four on synthetic/released historical paths observed; cross-app inheritance and published v1.17.0 Console/browser are unverified.

**Competitive test:** ask Bifrost, Portkey and TrueFoundry to produce identical allowed/denied requests, one shared rule, two distinct registered app identities and exact time to second integration. Ask Solo for specific edition/guardrail policy used. Talon wins only if *integration and investigation* are demonstrably simpler.

## Case B — Customer Support reliability/privacy: do not substitute app minimization for redaction

**Buyer objection:** "LiteLLM/Portkey/Bifrost already route, retry and redact. Why switch?"

**Demo must show:** (1) useful Shopify-style order enquiry and correct draft, not compliance theatre; (2) actual routed model request after safe trusted order lookup; (3) deliberate transient primary failure, unsupported/disallowed fallback skipped, approved configured fallback attempted (real provider if LIVE); (4) independent provider call counts, response/error truth, actual Talon cost and signed session attempts; (5) *separate* direct PII test with a structured synthetic email/IBAN crossing Talon, actual gateway block/redact and upstream absence/redacted bytes. No inference of Talon redaction from a pre-minimized prompt.

**Fail condition:** a canned reply, fake fallback log, "no PII" because app stripped fields, wrong-cost estimated as invoiced, bypass direct provider not disclosed. **Current status:** source-main PII **block** and count passed in synthetic Shopify integration, but full LIVE policy-valid fallback and independent PII-redaction wire proof remain NOT RUN.

**Competitive test:** same primary outage, disallowed fallback candidate and key/tenant policy on LiteLLM, Portkey and Bifrost. Talon wins only if explanation, per-use-case controls and integration add measurable benefit; routing alone is parity.

## Case C — Shopify refunds (PR #52): make the business operation, not approval alone, the proof

**Buyer objection:** "TrueFoundry can pause tool calls. Bifrost supports tool execution, Solo can inspect arguments. What is Talon's additional job?"

**Demo must show:** trust-bound business inputs (ticket, `order_id`, independent *merchant* refund eligibility, exact decimal `amount`, currency, destination/transaction), not model wishes. A company mandatory rule denies >€500, review >€50 through €500, allow ≤€50 **only for independently eligible** test orders. `€25` one synthetic call; `€249` zero before reviewer, **zero immediately after reviewer approval**, one only after authorized claim; `€750` zero; wrong/missing currency/type, €50/50.01/500/500.01; wrong reviewer, tampered arguments, replay/conflict and concurrent claims; restart/restore and real `UNKNOWN` reconciliation. Every action joined to same use-case identity/session/operation with verified signed lifecycle and independent ledger, without extra approval engine.

**Caveats:** Talon dispatches *at most once per operation inside the supported durable boundary*, not exactly-once external business effects. `UNKNOWN` may already have effected a call; blind retries are forbidden. Approval authorizes an exact operation **without dispatch**. Shopify's actual payment result must be verified independently; a synthetic ledger is not real Shopify. The current `shopify-support.workflow.json` is read/draft-only, and the passed joined test imports the official action workflow **as a second graph**; the test harness bridges real saved draft outputs. Do not call it a single ready-to-publish n8n template.

**Current status:** [joined synthetic core-main run 44826457464](https://github.com/dativo-io/talon-full-demo/actions/runs/44826457464) previously passed; latest PR CI and published RC2 end-to-end acceptance must be checked separately. No real payments. Compare alternative end-to-end operation states rather than simply asking "do you have an approval feature?"

## Case D — OrderDesk/Engineering (PR #45 plus #42–44): show the actual intercept boundary

**Buyer objection:** "Solo has network/CEL authorization, Bifrost supports coding agents. Can Talon really protect production from Claude Code?"

**Demo must show:** real OpenShell sandbox and real Claude Code/process identity, same-session Talon model request + exact Action Gateway call from inside supported boundary; deny a synthetic `volume_delete` before any dispatched executor call; reviewer distinct from agent; allow only sealed staging repair with independent service 503→200, real PostgreSQL staging correction and **production unchanged** (1000 test rows / protected volume). Independently prove OpenShell containment of an **out-of-path** direct request and a reachable positive control; attribute containment to OpenShell, not Talon. Signed Talon receipt + independent Postgres/infra counters + same run.

**Fail condition:** host-key preflight or shell-policy screenshot called agent-intercept execution; direct executor test called Talon approval; fabricated recovery; exception to production invariants. **Current status:** Postgres/fixture and actual Talon HOST-key action preflight pass, but C01–C12 same-hop Claude/OpenShell proof remains **not accepted**.

**Competitive test:** require Solo (specify OSS vs Enterprise), Bifrost and TrueFoundry to reproduce the full identity, tool/action and independent backend contract. Talon should not invent containment claims.

## Case E — Document Processing: prove pre-admission utility, not merely a cost dashboard

**Buyer objection:** "LiteLLM/Bifrost already enforce budgets. What do you add?"

**Demo must show:** a real n8n document workflow with a known priced model gives a useful partial output **before** Talon's next-request budget admission denies; capture requested vs allowed model, actual estimate/settlement, currency/UTC window, session evidence and **zero upstream dispatch for denial**; verify first work persists. Separate the contract test's deterministic Anthropic-wire fixture from LIVE provider. Cost warning webhook and hard cap should be shown only if implemented/tested in the exact released version. Admission estimate isn't an invoice guarantee.

**Fail condition:** an artificial refusal unsupported by Talon, denied work falsely described as completed, model pricing unknown, missing provider count, soft cap called hard invoice cap. **Current status:** deterministic cost/admission contract is present; integrated full n8n LIVE document flow/published v1.17.0 remains pending. Lead with completed document business value; spend policy is secondary.

**Competitive test:** same budget, model pricing, concurrency and reservation contract on LiteLLM and Bifrost, independently observe upstream calls. Talon has to win in per-use-case operational clarity rather than generic budget availability.

## Case F — First Production Pilot + ACME (PR #51 / #47–50): test the actual economic promise

**Buyer objection:** "Our Bifrost access profiles or Portkey agent registry already centralize policy. Do you reduce implementation work or add another gateway?"

**Demo must show:** one official digest-pinned *persistent* Talon deployment, company YAML baseline, native separate operational identities/active keys for Customer Support and People Analytics, real registered→loaded→connected→governed transitions for both **without duplicating applicable mandatory company policy**; original application still operating. Then extend to OrderDesk and Document Processing with separate primary value each. Seven read-only Console areas incl Approvals; native reviewer outside Console; single-source effective policies, costs, session and evidence parity. Measure actual native commands, durations, bypass and restart/restore. Use one same-run manifest with artifact/digest, use-case/session/operation IDs, policy, verdict, downstream counters, evidence verification and explicit missing fields.

**Fail condition:** two independent Talon processes masquerading as a fleet; reused demo credentials; registered-only cards; mismatched signed evidence and backend counters; source-built checkout called official RC2; failed RC2 availability job called acceptance. **Current status:** #51 is still an implementation specification with passing static proof check; the full shared ACME and shorter second-app pilot are not end-to-end accepted.

**Competitive test:** give each competing stack a prepared host and the same two existing apps; stopwatch actual support needed and count additional policy engines, reviewer services, state stores, dashboards, vault keys and bespoke adapters. Buyer win only if fewer independently operated governance pieces at comparable correctness.

## Head-to-head buyer trial rubric (score only after comparable external tests)

| Criterion | Weight | Operational evidence |
| --- | ---: | --- |
| Consequential action integrity and failure/replay/UNKNOWN safety | **30%** | Independent ledger, reviewer separation, exact-bound operation, replay & restart |
| Two-app adoption and policy reuse | **25%** | Native first/second use case, no duplicate company rule, measured setup and ongoing work |
| Diagnosis, evidence and governance clarity | **15%** | Actual session root cause, CLI/Console parity, falsifiable signed records |
| Reliability and preventive spending | **10%** | True provider call counts during fallback/denial, actual cost attribution |
| Security/deployment fit | **10%** | Local secret isolation, operator boundaries, release checksums, restore |
| Operational cost and product fit | **10%** | Number of moving parts, comparable fully burdened support and deployment cost |
| **Total** | **100%** | Do not score marketing claims as zero or automatically award Talon maximum |

Record every score as **NOT TESTED** until a common fixture has actually been run. The criteria and weights are **proposed** for the target midmarket buyer; confirm ranking with at least five interviews.

## Commercial objection handling — where Talon loses fairly

- "I only have one production bot and need model routing" → **LiteLLM/Bifrost/Portkey** may be a better purchase; do not oversell Talon.
- "I already use a policy gateway and a reliable homegrown action ledger" → quantify migration cost and actual remaining operational pain; if little, **do not replace it**.
- "We are heavily invested in Kubernetes/Envoy and need advanced ext-auth" → **Solo** likely fits better until Talon proves simpler end-to-end semantics.
- "Our workflows already use an enterprise MCP approval platform" → **TrueFoundry** must be tested on same exact action contract; do not pretend approval is unique.
- "We need HA across regions/SSO and compliance certification now" → defer if out of Talon's supported delivery boundary; evidence and self-hosting don't equal compliance.

## Source links — vendor-owned, verify editions at decision time

**Bifrost:** [MCP](https://www.getmaxim.ai/mcp-gateway) · [governance](https://www.getmaxim.ai/resources/governance) · [pricing](https://www.getmaxim.ai/pricing)

**LiteLLM:** [MCP permission management](https://docs.litellm.ai/docs/mcp_control) · [virtual keys](https://docs.litellm.ai/docs/proxy/virtual_keys) · [reliability](https://docs.litellm.ai/docs/proxy/reliability)

**Portkey:** [Agent Gateway](https://portkey.ai/blog/agent-gateway/) · [MCP governance](https://portkey.ai/features/mcp) · [tool provisioning](https://portkey.ai/blog/tool-provisioning-in-mcp-servers-controlling-ai-agent-access-in-production/)

**Solo:** [MCP auth variable availability](https://docs.solo.io/agentgateway/standalone/latest/documentation/configuration/security/authorization/mcp-authz/) · [argument guardrails](https://docs.solo.io/agentgateway/standalone/latest/documentation/mcp/guardrails/about/) · [external policy](https://docs.solo.io/agentgateway/standalone/latest/documentation/configuration/security/external-authz/) (some docs describe **Solo Enterprise**, not OSS)

**TrueFoundry:** [MCP human gate](https://tfy.app/blog/mcp-tool-approval-human-gate-call-path) · [MCP approvals](https://www.truefoundry.com/blog/mcp-tool-approvals-explained) · [gateway](https://www.truefoundry.com/ai-gateway)
