# ACME — live customer adoption walkthrough

**Status: implementation specification, NOT a runnable unified showcase.** Talon `v1.17.0-rc.2` is an annotated source tag on core commit `3f3f20dff910dc2416c8d82467de2d4e2dd8acc5` (2026-11-21): PRs #562–#569 and #572 are merged, including seven-area read-only Console, native registration, reviewer, exact-action policy, n8n reference, operations and First Production Pilot runbook. A tag is *not* a verified publicly published binary or consumer runtime. [Core n8n LIVE CI](https://github.com/dativo-io/talon/actions/runs/44786799917) passed with **n8n 2.48.5**; Full Demo still pins **2.30.4**, so do not assume compatibility. The final consumer baseline is the complete verified official **v1.17.0 stable** release, including Console, quickstart, generic argument authorization, reviewer, n8n reference, registration, production operations, pilot runbook and security upgrade (core PRs #562–569 and #572). RC.1 does not contain the complete release. Core [#561](https://github.com/dativo-io/talon/issues/561) and [#533](https://github.com/dativo-io/talon/issues/533) own release acceptance; Full Demo is an independent consumer, not a publication dependency. This guide describes the approved target and the gates for turning it into executable instructions. See [#47](https://github.com/dativo-io/talon-full-demo/issues/47), [#48](https://github.com/dativo-io/talon-full-demo/issues/48), [#49](https://github.com/dativo-io/talon-full-demo/issues/49), [#50](https://github.com/dativo-io/talon-full-demo/issues/50). Do not run illustrative commands or advertise unverified scenes as completed.

## The product story

**One company. Multiple AI use cases. One control plane.** Talon is the control plane for a company's AI use cases. For CTOs, VPs of Engineering, Heads of AI and platform leaders, the cost of each new deployment is not just LLM access: it is reinventing cost control, reliability, shared policy and session understanding. Show existing applications incrementally joining one installation and reusing its company baseline. Signed evidence is the proof layer, not a substitute for independent outcomes. Self-hosting, privacy, sovereignty and compliance support are differentiators, not the product category.

| Business use case | Existing implementation | Primary value |
| --- | --- | --- |
| People Analytics | [Workforce/DuckDB](../cases/people-analytics-copilot/README.md) | Shared policy |
| Customer Support | [Existing support/adapter paths](AUDIENCE_DEMOS.md) | Reliability and governed business actions |
| OrderDesk | [Claude/Postgres contract](CLAUDE_POSTGRES_INCIDENT_CONTRACT.md) | Bounded agent actions |
| Document Processing | [Existing n8n workflows](AUDIENCE_DEMOS.md) | Cost control |

People Analytics is the launch demo (PR #46); ACME is the post-release product flagship. The n8n refund pilot (#34–35, [PR #52](https://github.com/dativo-io/talon-full-demo/pull/52)) remains inside the existing Shopify-style Customer Support app, not a fifth application. Its Stage A real n8n + published Talon + synthetic Shopify/provider test passes; canonical refund Stage B remains unintegrated. See the [competitive proof scorecard](COMPETITOR_PROOF_SCORECARD.md) for five alternative products, skeptical buyer questions and falsifiable same-run evidence. Full Demo, including People Analytics and OrderDesk, does not block core publication. No new console features, approval UI, second evidence store, business applications or policy engine.

## Skeptical buyer gate — evidence, not feature bingo

Read the [approved five-competitor reality check](COMPETITOR_PROOF_SCORECARD.md) and [buyer-win strategy](TALON_BUYER_WIN_STRATEGY.md) before presenting. The competitors are **Bifrost, LiteLLM, Portkey, Solo.io agentgateway and TrueFoundry**; the old Langfuse/LangSmith/Helicone shortlist is superseded. Competitors already offer sophisticated gateways, budget controls, guardrails, tracing, failover and human review in various stacks. Talon needs to prove **one company policy plus independently authorized consequential actions across genuinely different existing applications**, not claim a unique monopoly on each feature.

Use the proof sequence: actual useful business output → request crossing a supported Talon boundary → authoritative loaded/effective company rule → actual Talon intervention → independent downstream counter/outcome → same-session signed evidence → Console/CLI parity. A model-generated statement, configured YAML or green pre-seeded dashboard is insufficient. Demonstrate one deliberate direct bypass as **uncontrolled and unobserved** rather than asserting universal agent control. Label source-built current-main vs released, fixture vs LIVE, priced vs unknown and NOT RUN gates conspicuously.

## Buyer-proof progression by existing application

The **two-app pilot** is the purchasing hinge, not another security feature demo. Use one native company policy, two distinct keys and one runtime; never confuse two independently successful CI fixtures with an integrated fleet. Ask the following objections aloud and show the counterexample **and the buyer's useful business outcome**. Do not replace runtime proof with presentation screens.

| Scene | Skeptical buyer objection | Minimum action + source of independent truth | Claim/status boundary |
| --- | --- | --- | --- |
| People Analytics (#46) | "Portkey, Solo, Bifrost and TrueFoundry can deny MCP tools already." | Actual workforce aggregate and forbidden employee export, native policy before SQL, SQL service guard independently rejects unsafe query; then demonstrate same applicable company rule on support | Existing standalone HR proof; **second-app shared rule NOT RUN** |
| Customer Support reliability (#49) | "LiteLLM, Portkey and Bifrost already have fallback and PII controls." | Real order enquiry; transient provider failure; forbidden candidate skipped; policy-valid fallback called; separate raw PII input tests Talon redaction/block and upstream bytes/count | Synthetic PII deny and app minimization passed; combined **LIVE provider failover NOT RUN** |
| Shopify refund (#34/#52) | "TrueFoundry already pauses MCP calls and Solo can inspect tool arguments." | Actual n8n draft output, merchant eligibility, company €25 allow / €249 independent reviewer / €750 deny; 0 effect on approval and deny, 1 on claim; exact replay/UNKNOWN, signed lifecycle, independent synthetic ledger | **Source-built main + synthetic** action proof; standalone export is read/draft, second imported official workflow governs action; no Shopify payment |
| OrderDesk (#42–45) | "The coding agent can still call a shell or API around your gateway." | Real Claude/OpenShell sandbox, Talon action boundary, separate containment proof, staging 503→200 and production row/volume invariants, same-run reviewer/action signatures | **HOST-key preflight only**; C01–C12 end-to-end sandbox still NOT RUN |
| Document Processing (#49) | "Bifrost and LiteLLM enforce budgets." | Genuine useful partial document output, next priced request denied at Talon admission, no provider call after deny, signed cost session; correct UTC/estimate boundaries | Deterministic provider contract; **full document LIVE n8n path NOT RUN** |
| Shared ACME (#47–50) | "Why not a Bifrost access profile or Portkey org registry?" | One digest-pinned Talon; Customer Support then HR native registration, loaded/effective company rule and independently governed traffic for both; 7-area read-only Console and time-to-second-app | **Unified two-app/four-app acceptance NOT RUN** |

**Sales priority:** Show useful Customer Support work and the safe synthetic consequential action, then onboard a fundamentally different application without creating another policy engine. The narrower 10–15 minute pilot must complete all four registered/loaded/connected/governed checks for the second use case. Keep the deeper OrderDesk and document scenes optional until their real contracts pass. Bifrost's documented signed audit and TrueFoundry's tool approvals remove any excuse to say these features are unique.

## Canonical company setup and onboarding proof

- Use the supported version-pinned published artifact path; no Go, source build or floating `latest` for Talon. The official no-clone quickstart (core #563) is an optional independent demonstration of policy decisions and evidence without provider keys. It tears down by default and does not show the console or a business action; do **not** treat it as ACME's persistent installation. Use the released supported persistent profile and pairing instructions for the shared journey. The official demo Compose path and the production profile are not interchangeable without verification.
- One AI use case = one `agent.talon.yaml` = one operational identity = one active Talon key. `talon.config.yaml` is the company policy/infrastructure configuration. Configure the baseline once, before connecting the first use case, then apply explicit use-case policy overrides which cannot weaken mandatory company constraints. YAML is the source of truth. Prefer the merged core-main native registration `talon agents add <name> --tenant acme --owner <team>` (#567); verify the final released syntax. No API or console write surface added by Full Demo.
- Use the same applicable mandatory company constraint in two different existing use cases (e.g., a forbidden model in both routed model paths, if supported by the final baseline). Execute actual permitted traffic and a denial/probe in both; show same company rule/source where recorded, zero dispatch where denied and independent counters where observable. Test attempted weaker override using actual released semantics; never imply refund rules apply to unrelated HR calls or that direct app interactions are governed.

| Acceptance stage (not product UI status names) | Independent proof |
| --- | --- |
| Registered | Valid native use-case config and operational identity/key binding; scrub key values. |
| Loaded | Authoritative runtime fleet view and effective/active policy, not a directory scan or a config edit alone. |
| Connected | Actual request from that application reaches its supported Talon boundary with matching identity and session/evidence IDs. |
| Governed | A real allow/deny/approval as appropriate under loaded policy, plus observed business result or independent non-dispatch/counter. |

Verify each stage for every scene, record PASS/FAIL/NOT RUN with supporting evidence; the short pilot must reach all four stages for both use cases. These are acceptance checks, not a new product object or dashboard taxonomy.

### Native adoption KPIs (rehearsal targets, not measured claims)

| Metric | Target | Start / end |
| --- | --- | --- |
| Install + console pairing | <3 min | First native install/deploy command to successful pair on prepared host |
| First use case | <5 min | First registration to independently verified governed request |
| Second use case | <2 min | Second registration to independently verified inherited control, first remains connected |
| Denied-action investigation | <1 min | Operator starts from actual denial/session to policy explanation and verified evidence |
| Duplicate governance infrastructure | 0 | No new application-specific policy engine, reviewer authority, audit store or Talon lifecycle manager |

Record actual elapsed time per stage and end-to-end, dependencies/image prefetch and app prep excluded, failures/workarounds and environment/release digests. Record NOT RUN where unavailable. Target short 10–15 minutes and deep 20–25 minutes; optional technical proofs/recovery exercises separately timed, not omitted acceptance criteria.

## First Production Pilot — adoption comes first

The Full Demo exists to (1) independently validate the product as a customer, (2) reduce integration effort, and (3) demonstrate value. [OSS #561](https://github.com/dativo-io/talon/issues/561) owns engineering readiness; [Enterprise #32](https://github.com/dativo-io/talon-enterprise/issues/32) owns activation of a real external company's AI use case. A demo run is neither a release verdict nor customer activation. Core publishes the complete v1.17.0 independently; PR #46 provides independent consumer corroboration. Customer-facing demonstrations use verified official stable releases only.

### Short LIVE customer journey (10–15 minutes, target)

Use a subset of the exact same runtime and application, not another demo implementation. This path is gated on complete stable v1.17.0 and consumer #34/#49 proof; align with the official production-pilot runbook (#569), not a second product implementation.

| Stage | What the customer sees and verifies |
| --- | --- |
| 0–3 min | Install released Talon on the supported persistent path, establish company baseline and provider references, pair Operations Console when ready; show actual YAML, no secrets. |
| 3–5 min | Register Customer Support natively; show identity, loaded/effective policy, and connect the existing workflow. Execute a real request; show applicable inherited rule and trusted action catalog. |
| 5–10 min | First show a useful Shopify-style order enquiry and **internal draft** through Talon. Then, only after real canonical action integration passes, run eligible synthetic EUR 25 allow, EUR 750 deny and EUR 249 approval-required operations. Approval alone causes zero dispatch; a subsequent Talon claim creates one independent synthetic finance request. Until then mark action NOT RUN, never substitute the legacy approval server. |
| 10–12 min | Inspect real session, signed evidence, actual provenance and independent finance ledger. |
| 12–15 min | Register existing HR use case natively; prove loaded, connected and governed by the same applicable company restriction, without recreating it. Show original support still works. |

Use the exact RC2-tagged-source generic typed argument-aware policy and official stock-node n8n reference (#564–566, #569 merged); adapt business inputs and synthetic finance endpoint, not authorization or dispatch. Use the actual released representation of exact decimals/currency, not floating point assumptions. Refund is one example of a generic rule. Talon-forwarded dispatch: EUR <=50 allow; >50 and <=500 exact human approval; >500 deny. Test boundaries 50/50.01/500/500.01, missing/wrong currency or type, unauthorized attempts, altered arguments, exact replay and ambiguous failure. No direct n8n finance dispatch, local approval authority or missing product logic supplied by demo. Approval authorizes an exact operation; it does not execute it. At-most-once dispatch per operation within the supported durable-state boundary is not exactly-once external business effects. UNKNOWN means an external effect may or may not have occurred; never blindly retry. A synthetic refund request never moves real money. Preserve the existing support reliability, HR, OrderDesk and document budget scenes: no fifth application.

### Reusable customer integration recipes

Each application guide must independently state: what it does before Talon, exact native connection changes, identity/company policy, intercepted and bypass paths, business value, and independent verification. Publish exact artifact pins and tested commands only after execution. Keep application integration visible; wrappers are optional conveniences.

### Production recovery and customer friction

Exercise the released single-node production operations and pilot runbooks (core #568/#569; #48 owns consumer proof); use native backup/verify and documented stopped restore, not a custom recovery manager; preserve vault keys, config, evidence, operations and ledger, verify before/after. Backup/restore where practical. Record NOT RUN if unavailable. Demo reset is not recovery.

Maintain a friction report during implementation, not an invented outcome:
| Attempted step / exact version | Expected customer experience | Actual result or NOT RUN | Workaround | Adoption severity | Owner / issue |
| --- | --- | --- | --- | --- | --- |
| Clean artifact install/pair, register, policy, action, evidence, restart, second use case | As documented for selected release | Record actual result | Record only used workaround | Blocker / high / medium / low | OSS #533/#561 for product defects; Full Demo for demo defects; presenter polish separately |


## RC2 contract provenance and consumer acceptance

- **Source tag:** `v1.17.0-rc.2` annotated tag resolves to `3f3f20dff910dc2416c8d82467de2d4e2dd8acc5`. The tag's presence and green Talon core CI do not establish downloadable artifact provenance.
- **Release run:** [Talon RC2 release verification](https://github.com/dativo-io/talon/actions/runs/44881314831). Check its outcome and published asset digest; when this guide was updated, it was in progress, not PASS.
- **Demo source-tag test:** [Shopify/HR/OrderDesk/Document candidate CI in PR #52](https://github.com/dativo-io/talon-full-demo/pull/52) now includes this exact tagged commit as source-build candidate. Its PASS proves its tested component contracts only, not unified ACME or a stable binary.
- **Published artifact test:** when actual RC2 release/asset exists, download exact digest and execute the real multi-case run. A success from the availability probe with a skipped consumer job is **NOT RUN**, not PASS.
- **Merge consistency:** [ACME combined-PR merge rehearsal](https://github.com/dativo-io/talon-full-demo/pull/51) merges PRs #45/#46/#52/#51 into a temporary tree and runs shared tests; it is independent from RC2 binary acceptance.

## Presenter verification levels

- **SPEC:** requirement/illustrative command only.
- **GUIDED:** deterministic mock fixture; *real Talon* may enforce a rule, but never describe synthetic model or synthetic business state as a paid/external system.
- **SOURCE-MAIN SYNTHETIC:** real Talon compiled from pinned main + real n8n and independently counted synthetic provider/Shopify/finance; this is not a released artifact, and upstream reference's `UNKNOWN` suite may be a separate fixture.
- **PUBLISHED-ARTIFACT SYNTHETIC:** publicly downloadable SHA256-verified Talon tag actually executes every required scene on independent fixtures. **A green "RC2 available?" detection job whose consumer test skips is NOT an RC2 runtime pass.**
- **LIVE PROVIDER / TEST STORE:** actual provider or explicitly authorized Shopify development-store transaction, plus independent results; never call test-store refund a real payment/customer production effect.
- **ACME ACCEPTED:** persistent digest-pinned official artifact; real two-app shared-company control, lifecycle evidence, native recovery and seven-area Console parity. No full acceptance from isolated PR workflows.

Every presenter beat needs a same-run manifest with **what changed in the business application**, actual Talon boundary/decision, effective company policy source, independent count/state, signed evidence, artifact and test mode. If no evidence, mark **NOT RUN** rather than filling cards with hardcoded plausible facts.

## Modes and preflight

- **Interactive LIVE (primary sales path, target 20–25 min):** human-visible installation, credential provisioning, native config, policy changes and staged onboarding. Real OpenAI and Anthropic calls; model-selected actions and deterministic probes explicitly distinguished.
- **Automated LIVE:** same scenarios, real providers, noninteractive supported credential input, same evidence and checks.
- **Keyless:** real Talon and controlled/deterministic fixtures; no external credentials; clearly distinguish mocked responses and genuine enforcement.

Prebuild app images/download dependencies and validate Docker/platform/network before the meeting. Record exact binary/image/version/commit and hashes; install from exact approved candidate artifacts before release, then verified stable public artifacts; no Talon source build in the normal adoption path. A release tag alone is not proof of scene success. Use fresh demo-owned state, not a seeded success dashboard. Never destroy unrelated installations or regenerate encryption/signing keys over retained evidence. Offline or unverified results must remain visible. Record real durations; times below are targets.

## Presenter runbook — target stages

Each Do step below states the operation and owning acceptance task. Replace it with exact tested native commands, wrapper equivalents, sample prompts and recovery instructions as the relevant implementation lands. Existing standalone commands are documented in [README](../README.md) and [audience views](AUDIENCE_DEMOS.md); do not present them as a unified runtime yet.

### 1. Meet ACME (00–02)

- **Context / Say:** "These teams already have working applications. Each wants to introduce AI; why should each rebuild its own operational infrastructure?"
- **Do:** start app-only infrastructure, show workforce aggregates, support/automation context and OrderDesk staging failure. Do not execute governed AI before setup (#48).
- **Show:** actual app surfaces. **Expect:** seeded synthetic data, independently working charts and deliberately failing staging endpoint once available.
- **Prove:** application health/counters; no Talon traffic. **Troubleshoot:** check app dependencies; stop on missing fixture.
- **Transition:** introduce one shared operating layer.

### 2. Install, initialize and connect providers (02–05)

- **Context / Say:** "Talon is a self-hosted control plane; let's install exactly what you can install."
- **Do:** install official verified binary/container, show version and native init/validate and config files. Securely prompt for disposable OpenAI and Anthropic API keys, provision using supported vault/delegation, establish the shared company baseline, then register the first keyed HR use case using the released native registration path before gateway startup if required (#48). Follow the released startup/pairing order, not a requirement to show an unsupported empty fleet. Pair using short-lived local console code.
- **Show:** native organization/use-case/provider configuration (secret references only), Overview and System. **Expect:** actual readiness and empty traffic history, not necessarily an empty configured fleet.
- **Prove:** artifact hashes, config and runtime roles, secure local pairing. **Troubleshoot:** identity registry, signing/vault key continuity, runtime state. No raw credential exposure in terminal output/history, argv where avoidable, logs, browser, screenshots or sandbox. A missing provider/failed preflight stops LIVE; don't silently switch modes.
- **Transition:** first real application integration.

### 3. People Analytics (05–09)

- **Context / Say:** "HR wants meaningful answers without unrestricted employee-level exports." A skeptical buyer says Portkey/Solo/Bifrost can already deny MCP. Respond by showing *application SQL protection plus company-wide Talon control*, and set up the second-app inheritance proof; this is not proprietary tool filtering.
- **Do:** follow the existing manual Workforce integration (#46); show allowed aggregate, real OpenAI analytics, explicit forbidden export probe and separate rejected SQL through allowed tool. Modify policy on synthetic data, validate/activate, repeat same action without app code change, restore secure policy.
- **Show:** Workforce result; AI Use Cases Summary, Effective Policy, Configuration, Sessions and Evidence.
- **Expect / Prove:** allowed dispatch, denial never dispatched, HR validation rejection downstream; independent HR counters and actual session IDs, CLI/API/UI parity, signed HMAC verification, loaded vs current config. Fixed charts bypass Talon.
- **Troubleshoot:** inspect actual loaded generation and tool discovery; do not claim changed policy before activation. Guided mode is not LLM output.
- **Transition:** HR is governed. Can another team reuse this exact company baseline without rebuilding governance?

### 4. Customer Support (09–12)

- **Context / Say:** "A provider outage shouldn't force a service outage or bypass company rules." LiteLLM/Bifrost/Portkey already do routing; show **a disallowed fallback candidate being skipped** and actual decision evidence. The Shopify Stage A minimized prompt is not itself Talon PII redaction.
- **Do:** onboard support using the same company baseline and native registration (#48/#49), prove the four onboarding stages, run a shared applicable company restriction probe and verify HR remains working; then run the synthetic email/IBAN request with controlled local primary failure, prohibited fallback candidate and approved real OpenAI fallback.
- **Show:** actual Shopify-style order enquiry, sanitized order facts, useful review-only draft and structured handoff (Stage A), then genuine provider path/decision, cost and session outcome from independently verified LIVE reliability scene. The current Shopify Stage A test uses synthetic orders and a deterministic provider; do not confuse it with real Shopify or paid inference. **Expect / Prove:** actual fallback and redaction as recorded; independent request/fixture observations; signed session and genuine provider spend.
- **Troubleshoot:** verify model pricing, provider configuration, policy and live credentials; do not claim fallback if provider failed.
- **Action-governance extension:** consume the official current-main Action Gateway workflow inside the same Customer Support application, with trusted business eligibility, generic company-deny rule, native independent reviewer and Talon-forwarded claim to a counted synthetic finance endpoint. The upstream n8n reference passed only on 2.48.5; verify Full Demo 2.30.4 or explicitly upgrade to the tested pin before claiming coverage. Stage A is draft-only; never treat a proposed amount as merchant eligibility. On the complete verified stable v1.17.0 release, run the same allow/deny/approval path from the short pilot in Customer Support. Inspect exact action proof, actual provenance and independent finance ledger; use the short version here to fit the full target, with extended tests outside live presentation.
- **Transition:** AI agents can perform consequential actions as well as generate text.

### 5. OrderDesk (12–17; gated)

- **Context / Say:** "We want an engineer's agent to restore service, not obtain unconstrained operational authority." Solo/TrueFoundry can govern tool calls; earn trust by distinguishing Talon's intercepted operations from OpenShell's independently verified sandbox/egress containment.
- **Do:** after all [C01–C12](CLAUDE_POSTGRES_INCIDENT_CONTRACT.md) pass (#42–44, PR #45), start real Claude Code in OpenShell; diagnose staging SQLSTATE 28P01. Execute explicit same-hop adversarial volume-delete probe, legitimate sealed staging repair proposal, external reviewer approval and subsequent attempt.
- **Show:** actual 503 then 200 business endpoint; use-case/session/action lifecycle/evidence in the real released console where recorded; canonical CLI/API for missing fields. **Expect / Prove:** company denial and zero fake delete calls; preapproval zero execution, approval alone zero dispatch, one authorized repair and independent unchanged production data/volume; replay/conflict/stale/unknown behavior covered in technical extension. OpenShell containment is independently proved, not attributed to Talon.
- **Troubleshoot:** refuse buyer-ready if any ratified gate is FAIL/UNKNOWN; no host-key or direct-executor stand-in. Reviewer and provider authority outside sandbox. No real destructive API.
- **Transition:** operational authority also needs financial control.

### 6. Document Processing (17–21)

- **Context / Say:** "Teams should be able to use different providers without losing control of spend." Bifrost and LiteLLM already sell budgets: lead with useful **partial document output** and the independently blocked *next request* before provider access. The admission estimate is not a billing guarantee.
- **Do:** onboard existing n8n Anthropic document workflow (#48/#49). Use known priced model, deliberately small positive cap, genuine first useful output and actual subsequent admission denial. Preserve completed work.
- **Show:** real workflow results and Costs page. **Expect / Prove:** actual partial output, signed budget deny and no provider dispatch for denied request, actual charges and currency where measured. Compare session-specific CLI cost and console UTC windows without conflating them.
- **Troubleshoot:** check cap, pricing and actual observed estimate/settlement; unavailable pricing or budget state is not exhaustion. Admission is estimate-based, not an invoice ceiling. Do not fabricate cost or force a success result.
- **Transition:** return to operating the whole company.

### 7. Operate ACME (21–25)

- **Context / Say:** "We didn't replace ACME's applications. We introduced one operating layer to adopt more AI use cases without independently rebuilding AI infrastructure for every team." Portkey has a registry, Bifrost access profiles and TrueFoundry identity. **Measure second-app operational duplication actually removed**, not merely number of cards visible.
- **Do / Show:** Overview readiness and fleet attention; AI Use Cases summary/effective policy; **Approvals (read-only)**, Sessions and evidence detail with actual ID search; Costs; Configuration and System. Current core main has **seven** primary areas, with reviewer decisions only via native CLI/API. Verify a real signature. Ask the prospect which existing use case they could pilot first.
- **Expect / Prove:** all four use cases registered, loaded, connected and governed in one installation; common applicable company constraint and explicit safe use-case overrides, actual traffic and costs, canonical CLI/API/UI projections and independent effects. Show shared policy once, not four duplicated policies. One proof manifest tied to exact same run; no mixed or stale artifacts. HMAC is tamper-evident, not immutable. Tenant filtering isn't an auth boundary; only intercepted actions governed.
- **Troubleshoot:** distinguish not configured, degraded, offline, unavailable and unknown. Show any missing measurement honestly. Configuration/approval writes remain outside read-only console.
- **Transition:** one bounded customer pilot, not a claim of universal governance.

## Proposed command ownership (not implemented)

Use the core release's exact native interfaces for Talon operations, including the published artifact install, initialization/persistent deployment, provider secret provisioning, console pairing, use-case registration/effective policy, reviewer, audit verification and backup/restore. Do not introduce showcase-install/init/connect-providers/console/onboard wrappers as mandatory substitutes. Verify the final syntax before publishing runnable commands.

Full Demo owns only fixture orchestration and same-run proof; reuse current Makefile conventions. These candidate names are NOT implemented:

| Fixture operation | Candidate target |
| --- | --- |
| Check environment and prebuild application fixtures | `showcase-preflight` |
| Start ordinary applications without Talon | `showcase-apps-start` |
| Run existing application scenes against configured Talon (shared implementation) | `showcase-live`, `showcase-guided` |
| Verify independent business effects and join canonical evidence references | `showcase-verify` |
| Inspect and stop/reset demo-owned application state | `showcase-status`, `showcase-stop`, `showcase-reset` |

Convenience automation may invoke native operations transparently for CI and automated LIVE; it must expose the exact equivalent customer commands, preserve secrets and failure semantics, and never build an alternate Talon lifecycle manager. Reset is not production recovery.

## Exit gates

- [ ] #46 passes supported stable published artifact People Analytics acceptance, all **seven current-main areas** including read-only Approvals and documented secure pairing; any candidate-only runs are separate, record in #533/#561. RC.1 does not satisfy integrated acceptance.
- [ ] #48 supports one proved runtime, secure real key entry, native identities, common company baseline, four onboarding stages per use case, second use case inheriting same applicable mandatory control and first still working.
- [ ] #49 support and n8n end-to-end proof; #42–44 integrated incident gates and shared-runtime compatibility.
- [ ] #50 exact native step-by-step commands and prompts, four integration recipes, short 10–15 min production-pilot and deep 20–25 min ACME LIVE rehearsals, automated LIVE and keyless verification, actual timings, safe reset and separately verified persistent restart/recovery.
- [ ] #34/#49 released argument-aware customer-support action contract passes allow/deny/approval, replay and unauthorized checks; adoption friction report links actual defects and observations.
- [ ] One same-run fail-closed manifest references versions/digests, policy identity where recorded, session/operation IDs, independent counts, actual cost/currency/availability and signature results, four onboarding verdicts per use case and actual timing measurements. Reuse OrderDesk proof.
- [ ] Actual console screenshots/recordings safely redacted and labeled with verified published artifact provenance. Buyer and technical views of same run. No secrets, fabricated data, unsupported claims or preloaded success.
