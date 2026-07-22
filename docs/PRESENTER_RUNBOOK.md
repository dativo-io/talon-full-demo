# Presenter runbook — 10–15 minutes

Use this only after the relevant executable and external gates pass. The short website hero is a separate artifact.

## Demo promise

Show recognizable application shapes using one Talon operating layer:

1. customer support keeps working through PII handling and policy-valid provider fallback;
2. GitHub Copilot CLI uses Talon for model traffic and a synthetic release MCP boundary;
3. n8n preserves useful partial output before Talon denies the next request on a soft session budget;
4. the same Talon evidence can be projected for buyers or expanded for technical reviewers.

Evidence is the proof layer. Never infer provider routes, policy decisions, costs, or signatures from application output alone.

## Truth boundaries

The demo may claim:

- three AI-use-case identities have separate keys and effective controls;
- the LLM gateway runs on `:8080` and the agent-key-authenticated MCP proxy on `:8081`;
- PII can be redacted before provider access;
- provider fallback remains inside the approved provider set;
- routed MCP calls are filtered and enforced by Talon;
- completed n8n output survives a later budget denial;
- session evidence can be exported and verified offline.

The demo must not claim:

- Talon controls Copilot's local shell, filesystem, browser, or direct network actions;
- Copilot CLI permissions are Talon controls;
- the normal Copilot run attempted `release_publish`;
- session budgets are atomic hard reservations;
- HMAC evidence is immutable;
- an offline Zendesk ZIP received Zendesk server-side validation;
- Zendesk browser behavior was machine-proven by Talon evidence.

## Preflight before the audience joins

```bash
make ci
make n8n-validate
make live-check
make zendesk-package
make real-start
make real-status
```

Confirm:

- all services are healthy;
- Ollama is stopped for the support fallback scene;
- provider keys and customer content are not visible;
- `make copilot-install` was completed when presenting Copilot;
- Anthropic was seeded before presenting n8n;
- authenticated ZCLI and installed-app gates are complete before claiming Zendesk installation.

## Scene 1 — customer support (2 minutes)

Buyer audience:

```bash
make demo-support-buyer
```

Technical audience:

```bash
make demo-support-tech
```

Re-present the same session:

```bash
make present-support-all
```

Narrate:

1. synthetic input contains an email and IBAN;
2. Talon redacts both before provider access;
3. the preferred local route fails;
4. `openai-batch` is excluded by policy;
5. OpenAI is selected and the reply completes;
6. the session cost and signed evidence verify.

Say:

> The support workflow kept working without bypassing its data policy or approved provider list. The receipt is calculated from the same signed session a technical reviewer can inspect.

Do not use the generated prose as proof.

## Scene 2 — real Copilot + MCP path (2 minutes)

Buyer audience:

```bash
make demo-copilot-buyer
```

Technical audience:

```bash
make demo-copilot-tech
```

Re-present the same session:

```bash
make present-copilot-all
```

Narrate:

> This is a real Copilot client using Talon for its model and MCP paths. Two permitted release operations reached the synthetic service, no publish operation reached it, cost was attributed to `coding-assistant`, and every evidence record verifies.

State explicitly:

- the scene intentionally performs no local coding or shell action;
- client/session provenance is attribution, not independent process attestation;
- the separate `make live-check` adversarial probe proves runtime enforcement against a client that bypasses discovery.

Do not say “Copilot tried to publish.” Say “No publish call reached the upstream.”

## Scene 3 — n8n partial output (2–3 minutes)

Buyer audience:

```bash
make demo-n8n-buyer
```

Technical audience:

```bash
make demo-n8n-tech
```

Re-present the same session:

```bash
make present-n8n-all
```

Narrate:

1. n8n imports a committed credential-free workflow;
2. synthetic compliance sections run sequentially as `document-summary`;
3. each completed summary is written immediately;
4. completed work consumes session budget;
5. Talon denies the next request before provider dispatch;
6. n8n writes `status.json` and preserves the useful partial report;
7. the denied request carries zero provider cost and remains visible in signed evidence.

Say:

> Talon did not erase completed work or pretend the earlier requests were free. It stopped the next request, preserved what the workflow had already produced, and made the budget boundary auditable.

Do not claim a hard no-overshoot reservation.

## Scene 4 — Zendesk application surface (optional, 2 minutes)

The backend adapter proof is available without a Zendesk account:

```bash
make demo-zendesk-buyer
make demo-zendesk-tech
```

The offline package artifact is available with:

```bash
make zendesk-package
```

Present the installed private app only after:

```bash
zcli login -i
make zendesk-zcli-package
```

and the real Zendesk UI flow is observed and recorded with `make verify-zendesk-installed`.

During the installed-app scene:

1. open a synthetic ticket containing requester public, agent public, and private comments;
2. click **Draft governed reply**;
3. show that the newest public requester-authored comment was selected;
4. show that only the returned draft was inserted;
5. show the run-scoped session identifier;
6. expand matching Talon evidence for provider, PII handling, cost, and signatures.

Do not display the adapter token, Talon key, provider key, or OAuth token.

## Closing proof

For any demonstrated session, use the application presenter first. When a reviewer asks for the native evidence:

```bash
talon audit list --session <session-id>
talon audit export \
  --format signed-json \
  --session <session-id> \
  --output .state/<session-id>.signed.json
talon audit verify --file .state/<session-id>.signed.json
```

Say **tamper-evident and offline-verifiable**, never immutable.

## Recommended order

Buyer meeting:

1. support buyer view;
2. Copilot buyer view;
3. n8n buyer view when workflow cost control is relevant;
4. Zendesk installed app only for a support-operations buyer and only after its external gate.

Technical review:

1. support technical view;
2. Copilot technical view;
3. n8n technical view;
4. `make live-check` for adversarial MCP enforcement and the hermetic budget engine.

## Abort conditions

Stop the live walkthrough when:

- `make ci`, `make n8n-validate`, `make live-check`, `real-start`, or `real-status` fails;
- any application runner or presenter assertion fails;
- buyer and technical projections do not resolve to the same session;
- expected receipts, output artifacts, or current-run evidence are absent;
- evidence has an invalid, missing-signature, malformed, or unsupported record;
- a denied n8n request carries provider cost;
- secure Zendesk setting substitution or installed-app behavior is unproven;
- a route, cost, denial, or signature cannot be read from actual Talon output.
