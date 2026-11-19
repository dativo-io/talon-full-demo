# ACME — live customer adoption walkthrough

**Status: implementation specification, NOT a runnable unified showcase.** The final consumer baseline is the complete verified official **v1.17.0 stable** release, including Console, quickstart, generic argument authorization, reviewer, n8n reference, registration, production operations, pilot runbook and security upgrade (core PRs #562–569 and #572). RC.1 does not contain the complete release. Core [#561](https://github.com/dativo-io/talon/issues/561) and [#533](https://github.com/dativo-io/talon/issues/533) own release acceptance; Full Demo is an independent consumer, not a publication dependency. This guide describes the approved target and the gates for turning it into executable instructions. See [#47](https://github.com/dativo-io/talon-full-demo/issues/47), [#48](https://github.com/dativo-io/talon-full-demo/issues/48), [#49](https://github.com/dativo-io/talon-full-demo/issues/49), [#50](https://github.com/dativo-io/talon-full-demo/issues/50). Do not run illustrative commands or advertise unverified scenes as completed.

## The product story

**One company. Multiple AI use cases. One control plane.** Talon is the control plane for a company's AI use cases. For CTOs, VPs of Engineering, Heads of AI and platform leaders, the cost of each new deployment is not just LLM access: it is reinventing cost control, reliability, shared policy and session understanding. Show existing applications incrementally joining one installation and reusing its company baseline. Signed evidence is the proof layer, not a substitute for independent outcomes. Self-hosting, privacy, sovereignty and compliance support are differentiators, not the product category.

| Business use case | Existing implementation | Primary value |
| --- | --- | --- |
| People Analytics | [Workforce/DuckDB](../cases/people-analytics-copilot/README.md) | Shared policy |
| Customer Support | [Existing support/adapter paths](AUDIENCE_DEMOS.md) | Reliability and governed business actions |
| OrderDesk | [Claude/Postgres contract](CLAUDE_POSTGRES_INCIDENT_CONTRACT.md) | Bounded agent actions |
| Document Processing | [Existing n8n workflows](AUDIENCE_DEMOS.md) | Cost control |

People Analytics is the launch demo (PR #46); ACME is the post-release product flagship. The n8n refund pilot (#34–35) is a focused action-governance scenario integrated into Customer Support, not a fifth application. Full Demo, including People Analytics and OrderDesk, does not block core publication. No new console features, approval UI, second evidence store, business applications or policy engine.

## Canonical company setup and onboarding proof

- Use the supported version-pinned published artifact path; no Go, source build or floating `latest` for Talon. The official no-clone quickstart (core #563) is an optional independent demonstration of policy decisions and evidence without provider keys. It tears down by default and does not show the console or a business action; do **not** treat it as ACME's persistent installation. Use the released supported persistent profile and pairing instructions for the shared journey. The official demo Compose path and the production profile are not interchangeable without verification.
- One AI use case = one `agent.talon.yaml` = one operational identity = one active Talon key. `talon.config.yaml` is the company policy/infrastructure configuration. Configure the baseline once, before connecting the first use case, then apply explicit use-case policy overrides which cannot weaken mandatory company constraints. YAML is the source of truth. Prefer the released native registration command (core #567 proposes `talon agents add`; verify final syntax). No API or console write surface added by Full Demo.
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
| 5–10 min | Run real EUR 25 allow, EUR 750 deny and EUR 249 approval-required refund requests. Reviewer sees exact subject; approval alone causes zero dispatch; authorized attempt creates one synthetic finance request. |
| 10–12 min | Inspect real session, signed evidence, actual provenance and independent finance ledger. |
| 12–15 min | Register existing HR use case natively; prove loaded, connected and governed by the same applicable company restriction, without recreating it. Show original support still works. |

Use the released generic typed argument-aware policy and official stock-node n8n reference (#564–566, #569); adapt business inputs and synthetic finance endpoint, not authorization or dispatch. Use the actual released representation of exact decimals/currency, not floating point assumptions. Refund is one example of a generic rule. Talon-forwarded dispatch: EUR <=50 allow; >50 and <=500 exact human approval; >500 deny. Test boundaries 50/50.01/500/500.01, missing/wrong currency or type, unauthorized attempts, altered arguments, exact replay and ambiguous failure. No direct n8n finance dispatch, local approval authority or missing product logic supplied by demo. Approval authorizes an exact operation; it does not execute it. At-most-once dispatch per operation within the supported durable-state boundary is not exactly-once external business effects. UNKNOWN means an external effect may or may not have occurred; never blindly retry. A synthetic refund request never moves real money. Preserve the existing support reliability, HR, OrderDesk and document budget scenes: no fifth application.

### Reusable customer integration recipes

Each application guide must independently state: what it does before Talon, exact native connection changes, identity/company policy, intercepted and bypass paths, business value, and independent verification. Publish exact artifact pins and tested commands only after execution. Keep application integration visible; wrappers are optional conveniences.

### Production recovery and customer friction

Exercise the released single-node production operations and pilot runbooks (core #568/#569; #48 owns consumer proof); use native backup/verify and documented stopped restore, not a custom recovery manager; preserve vault keys, config, evidence, operations and ledger, verify before/after. Backup/restore where practical. Record NOT RUN if unavailable. Demo reset is not recovery.

Maintain a friction report during implementation, not an invented outcome:
| Attempted step / exact version | Expected customer experience | Actual result or NOT RUN | Workaround | Adoption severity | Owner / issue |
| --- | --- | --- | --- | --- | --- |
| Clean artifact install/pair, register, policy, action, evidence, restart, second use case | As documented for selected release | Record actual result | Record only used workaround | Blocker / high / medium / low | OSS #533/#561 for product defects; Full Demo for demo defects; presenter polish separately |


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

- **Context / Say:** "HR wants meaningful answers without unrestricted employee-level exports."
- **Do:** follow the existing manual Workforce integration (#46); show allowed aggregate, real OpenAI analytics, explicit forbidden export probe and separate rejected SQL through allowed tool. Modify policy on synthetic data, validate/activate, repeat same action without app code change, restore secure policy.
- **Show:** Workforce result; AI Use Cases Summary, Effective Policy, Configuration, Sessions and Evidence.
- **Expect / Prove:** allowed dispatch, denial never dispatched, HR validation rejection downstream; independent HR counters and actual session IDs, CLI/API/UI parity, signed HMAC verification, loaded vs current config. Fixed charts bypass Talon.
- **Troubleshoot:** inspect actual loaded generation and tool discovery; do not claim changed policy before activation. Guided mode is not LLM output.
- **Transition:** HR is governed. Can another team reuse this exact company baseline without rebuilding governance?

### 4. Customer Support (09–12)

- **Context / Say:** "A provider outage shouldn't force a service outage or bypass company rules."
- **Do:** onboard support using the same company baseline and native registration (#48/#49), prove the four onboarding stages, run a shared applicable company restriction probe and verify HR remains working; then run the synthetic email/IBAN request with controlled local primary failure, prohibited fallback candidate and approved real OpenAI fallback.
- **Show:** actual support reply, provider path/decision, cost and session outcome. **Expect / Prove:** actual fallback and redaction as recorded; independent request/fixture observations; signed session and genuine provider spend.
- **Troubleshoot:** verify model pricing, provider configuration, policy and live credentials; do not claim fallback if provider failed.
- **Action-governance extension:** on the complete verified stable v1.17.0 release, run the same real allow/deny/approval refund path from the short pilot in Customer Support. Inspect exact action proof, actual provenance and independent finance ledger; use the short version here to fit the full target, with extended tests outside live presentation.
- **Transition:** AI agents can perform consequential actions as well as generate text.

### 5. OrderDesk (12–17; gated)

- **Context / Say:** "We want an engineer's agent to restore service, not obtain unconstrained operational authority."
- **Do:** after all [C01–C12](CLAUDE_POSTGRES_INCIDENT_CONTRACT.md) pass (#42–44, PR #45), start real Claude Code in OpenShell; diagnose staging SQLSTATE 28P01. Execute explicit same-hop adversarial volume-delete probe, legitimate sealed staging repair proposal, external reviewer approval and subsequent attempt.
- **Show:** actual 503 then 200 business endpoint; use-case/session/action lifecycle/evidence in the real released console where recorded; canonical CLI/API for missing fields. **Expect / Prove:** company denial and zero fake delete calls; preapproval zero execution, approval alone zero dispatch, one authorized repair and independent unchanged production data/volume; replay/conflict/stale/unknown behavior covered in technical extension. OpenShell containment is independently proved, not attributed to Talon.
- **Troubleshoot:** refuse buyer-ready if any ratified gate is FAIL/UNKNOWN; no host-key or direct-executor stand-in. Reviewer and provider authority outside sandbox. No real destructive API.
- **Transition:** operational authority also needs financial control.

### 6. Document Processing (17–21)

- **Context / Say:** "Teams should be able to use different providers without losing control of spend."
- **Do:** onboard existing n8n Anthropic document workflow (#48/#49). Use known priced model, deliberately small positive cap, genuine first useful output and actual subsequent admission denial. Preserve completed work.
- **Show:** real workflow results and Costs page. **Expect / Prove:** actual partial output, signed budget deny and no provider dispatch for denied request, actual charges and currency where measured. Compare session-specific CLI cost and console UTC windows without conflating them.
- **Troubleshoot:** check cap, pricing and actual observed estimate/settlement; unavailable pricing or budget state is not exhaustion. Admission is estimate-based, not an invoice ceiling. Do not fabricate cost or force a success result.
- **Transition:** return to operating the whole company.

### 7. Operate ACME (21–25)

- **Context / Say:** "We didn't replace ACME's applications. We introduced one operating layer to adopt more AI use cases without independently rebuilding AI infrastructure for every team."
- **Do / Show:** Overview readiness and fleet attention; AI Use Cases summary/effective policy; Sessions and evidence detail with actual ID search; Costs; Configuration and System. Verify a real signature. Ask the prospect which existing use case they could pilot first.
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

- [ ] #46 passes supported stable published artifact People Analytics acceptance, six pages and documented secure pairing; any candidate-only runs are separate, record in #533/#561. RC.1 does not satisfy integrated acceptance.
- [ ] #48 supports one proved runtime, secure real key entry, native identities, common company baseline, four onboarding stages per use case, second use case inheriting same applicable mandatory control and first still working.
- [ ] #49 support and n8n end-to-end proof; #42–44 integrated incident gates and shared-runtime compatibility.
- [ ] #50 exact native step-by-step commands and prompts, four integration recipes, short 10–15 min production-pilot and deep 20–25 min ACME LIVE rehearsals, automated LIVE and keyless verification, actual timings, safe reset and separately verified persistent restart/recovery.
- [ ] #34/#49 released argument-aware customer-support action contract passes allow/deny/approval, replay and unauthorized checks; adoption friction report links actual defects and observations.
- [ ] One same-run fail-closed manifest references versions/digests, policy identity where recorded, session/operation IDs, independent counts, actual cost/currency/availability and signature results, four onboarding verdicts per use case and actual timing measurements. Reuse OrderDesk proof.
- [ ] Actual console screenshots/recordings safely redacted and labeled with verified published artifact provenance. Buyer and technical views of same run. No secrets, fabricated data, unsupported claims or preloaded success.
