# ACME — live customer adoption walkthrough

**Status: implementation specification, NOT a runnable unified showcase.** The Operations Console is merged but stable release acceptance remains open in [Talon #533](https://github.com/dativo-io/talon/issues/533). This guide describes the approved target and the gates for turning it into executable instructions. See [#47](https://github.com/dativo-io/talon-full-demo/issues/47), [#48](https://github.com/dativo-io/talon-full-demo/issues/48), [#49](https://github.com/dativo-io/talon-full-demo/issues/49), [#50](https://github.com/dativo-io/talon-full-demo/issues/50). Do not run illustrative commands or advertise unverified scenes as completed.

## The product story

**One company. Multiple AI use cases. One control plane.** We show a CTO how existing applications progressively adopt AI with cost control, reliability, shared policy and session understanding. Signed evidence is the proof layer, not a substitute for independent application outcomes.

| Business use case | Existing implementation | Primary value |
| --- | --- | --- |
| People Analytics | [Workforce/DuckDB](../cases/people-analytics-copilot/README.md) | Shared policy |
| Customer Support | [Existing support/adapter paths](AUDIENCE_DEMOS.md) | Reliability |
| OrderDesk | [Claude/Postgres contract](CLAUDE_POSTGRES_INCIDENT_CONTRACT.md) | Bounded agent actions |
| Document Processing | [Existing n8n workflows](AUDIENCE_DEMOS.md) | Cost control |

People Analytics is the launch demo (PR #46); ACME is the post-release product flagship. The n8n refund pilot (#34–35) remains a focused action-governance scenario. Full ACME and OrderDesk do not block #533. No new console features, approval UI, second evidence store, business applications or policy engine.

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
- **Do:** install official verified binary/container, show version and native init/validate and config files. Securely prompt for disposable OpenAI and Anthropic API keys, provision using supported vault/delegation, register the first keyed HR use case before gateway startup (#48). Pair using short-lived local console code.
- **Show:** native organization/use-case/provider configuration (secret references only), Overview and System. **Expect:** actual readiness and empty traffic history, not necessarily an empty configured fleet.
- **Prove:** artifact hashes, config and runtime roles, secure local pairing. **Troubleshoot:** identity registry, signing/vault key continuity, runtime state. No raw credential exposure in terminal output/history, argv where avoidable, logs, browser, screenshots or sandbox. A missing provider/failed preflight stops LIVE; don't silently switch modes.
- **Transition:** first real application integration.

### 3. People Analytics (05–09)

- **Context / Say:** "HR wants meaningful answers without unrestricted employee-level exports."
- **Do:** follow the existing manual Workforce integration (#46); show allowed aggregate, real OpenAI analytics, explicit forbidden export probe and separate rejected SQL through allowed tool. Modify policy on synthetic data, validate/activate, repeat same action without app code change, restore secure policy.
- **Show:** Workforce result; AI Use Cases Summary, Effective Policy, Configuration, Sessions and Evidence.
- **Expect / Prove:** allowed dispatch, denial never dispatched, HR validation rejection downstream; independent HR counters and actual session IDs, CLI/API/UI parity, signed HMAC verification, loaded vs current config. Fixed charts bypass Talon.
- **Troubleshoot:** inspect actual loaded generation and tool discovery; do not claim changed policy before activation. Guided mode is not LLM output.
- **Transition:** authorization alone isn't service reliability.

### 4. Customer Support (09–12)

- **Context / Say:** "A provider outage shouldn't force a service outage or bypass company rules."
- **Do:** onboard support in shared runtime (#48/#49), run synthetic email/IBAN request with controlled local primary failure, prohibited fallback candidate and approved real OpenAI fallback.
- **Show:** actual support reply, provider path/decision, cost and session outcome. **Expect / Prove:** actual fallback and redaction as recorded; independent request/fixture observations; signed session and genuine provider spend.
- **Troubleshoot:** verify model pricing, provider configuration, policy and live credentials; do not claim fallback if provider failed.
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
- **Expect / Prove:** all supported use cases in one installation, actual traffic and costs, canonical CLI/API/UI projections and independent effects. One proof manifest tied to exact same run; no mixed or stale artifacts. HMAC is tamper-evident, not immutable. Tenant filtering isn't an auth boundary; only intercepted actions governed.
- **Troubleshoot:** distinguish not configured, degraded, offline, unavailable and unknown. Show any missing measurement honestly. Configuration/approval writes remain outside read-only console.
- **Transition:** one bounded customer pilot, not a claim of universal governance.

## Proposed command surface (not implemented)

Reuse existing make targets wherever possible. #48 and #50 own the actual executable interface:

| Operation | Candidate target |
| --- | --- |
| Preflight/dependency prep, app-only start | `showcase-preflight`, `showcase-apps-start` |
| Install/init/connect providers | `showcase-install`, `showcase-init`, `showcase-connect-providers` |
| Start runtime/pair console | `showcase-talon-start`, `showcase-console` |
| Staged application identity/config | `showcase-onboard-hr`, `showcase-onboard-support`, `showcase-onboard-engineering`, `showcase-onboard-documents` |
| Independent modes and proof | `showcase-live`, `showcase-guided`, `showcase-verify` |
| Operator lifecycle | `showcase-status`, `showcase-reset`, `showcase-stop` |

## Exit gates

- [ ] #46 passes candidate then stable published artifact People Analytics acceptance, six pages and documented secure pairing; record in #533.
- [ ] #48 supports one proved runtime, secure real key entry, actual identities and active config.
- [ ] #49 support and n8n end-to-end proof; #42–44 integrated incident gates and shared-runtime compatibility.
- [ ] #50 exact native step-by-step commands and prompts, interactive LIVE rehearsal, automated LIVE and keyless verification, safe reset and actual timings.
- [ ] One same-run fail-closed manifest references versions/digests, policy identity where recorded, session/operation IDs, independent counts, actual cost/currency/availability and signature results. Reuse OrderDesk proof.
- [ ] Actual console screenshots/recordings safely redacted and labeled with verified published artifact provenance. Buyer and technical views of same run. No secrets, fabricated data, unsupported claims or preloaded success.
