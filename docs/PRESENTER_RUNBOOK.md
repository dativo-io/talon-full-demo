# Presenter runbook — 10–15 minutes

Use this only after the relevant executable and external gates pass. The short website hero is a separate artifact.

## Demo promise

Show recognizable application shapes using one Talon control plane:

1. Zendesk Support requests a governed reply draft.
2. GitHub Copilot CLI completes one bounded, approved local command sequence and reaches a synthetic release service through Talon's MCP proxy.
3. n8n preserves useful partial output before a later request crosses the configured soft session budget.

Evidence is the proof layer. Never infer provider routes, policy decisions, costs, or signatures from application output alone.

## Truth boundaries

The demo may claim:

- one Talon fleet configuration defines three AI-use-case identities with separate keys;
- the LLM gateway runs on `:8080` and the agent-key-authenticated MCP proxy runs on `:8081`, sharing configuration and evidence state;
- policy can redact or deny before provider or tool execution at a Talon interception boundary;
- allowed MCP calls reach the synthetic release server while no `release_publish` receipt reaches it;
- session-scoped signed evidence can be exported and verified offline.

The demo must not claim:

- Talon controls Copilot's local shell, filesystem, browser, or direct network actions;
- Copilot CLI permissions are Talon controls;
- the bounded Copilot scene proves free-form code generation or patch-edit quality;
- the real Copilot run attempted `release_publish` when that tool was removed from discovery;
- session budgets are atomic hard reservations;
- one denial automatically creates a fleet `needs-attention` state;
- HMAC evidence is immutable;
- Zendesk, Copilot, n8n, or provider behavior was validated unless that gate actually passed.

## Topology

```text
Zendesk ticket editor
  -> adapter 127.0.0.1:8443
  -> Talon LLM gateway 127.0.0.1:8080

GitHub Copilot CLI
  -> session shim 127.0.0.1:8079
  -> Talon LLM gateway 127.0.0.1:8080

Copilot remote HTTP MCP
  -> Talon MCP proxy 127.0.0.1:8081
  -> synthetic release MCP 127.0.0.1:8090

n8n 127.0.0.1:5678
  -> Talon LLM gateway 127.0.0.1:8080
```

Only the optional Zendesk adapter may be exposed outside loopback, through an authenticated HTTPS tunnel.

## Scene 0 — preflight before the audience joins

Run:

```bash
make ci
make live-check
make real-start
make real-status
```

`make live-check` is the go/no-go proof for the real Talon MCP and session-budget behavior. It uses a throwaway environment and separately proves:

- preventive filtering: `release_publish` is absent from `tools/list`;
- runtime enforcement: a clearly labelled adversarial client that bypasses discovery receives `TALON_TOOL_FORBIDDEN`;
- current-session signed evidence carries the authenticated `coding-assistant` identity.

Confirm:

- all real-stack services are healthy;
- Ollama is stopped for the support fallback scene;
- provider keys and customer content are not visible;
- `make copilot-install` has been completed when presenting Copilot;
- n8n and Zendesk external gates are either proven or omitted.

## Scene 1 — real support request (2 minutes)

Run:

```bash
make real-smoke
```

Narrate only what the command proves:

1. synthetic input contains an email and IBAN;
2. Talon redacts both before provider access;
3. the preferred local model fails to connect;
4. a disallowed fallback candidate is skipped;
5. OpenAI is selected;
6. signed evidence verifies offline.

Do not treat the generated prose as the proof. The `REAL CASE PASSED` assertions and evidence file are the proof.

## Scene 2 — bounded real Copilot + MCP path (2 minutes)

Run exactly:

```bash
make real-copilot
```

Do not open Copilot separately, paste a task, resume an old session, or improvise additional prompts.

The command automatically:

1. restores and verifies the known failing billing fixture;
2. creates a fresh Talon session and nonce;
3. runs one non-interactive Copilot prompt with a two-minute hard limit;
4. gives Copilot no general file-write permission;
5. permits only `npm run fix-demo`, `npm test`, `release_status`, and `release_prepare`;
6. verifies the exact one-file diff and passing test;
7. verifies nonce-correlated `release_status` and `release_prepare` receipts;
8. verifies no `release_publish` receipt reached the upstream;
9. verifies current-run signed evidence is attributed to `coding-assistant`.

`npm run fix-demo` is a committed, fail-closed fixture command that performs exactly the known one-line correction. This keeps the scene deterministic and isolates what is being demonstrated: the real Copilot client, model routing, MCP policy, identity, receipts, and evidence.

A valid presentation ends with:

```text
REAL COPILOT CASE PASSED
```

and the exact one-line diff.

State explicitly:

- Copilot's model API traffic and MCP calls passed through Talon;
- Copilot invoked the approved local correction and test commands;
- those local shell actions remained outside Talon's control;
- this proves the client-integration path, not Copilot's autonomous patch quality;
- the real Copilot run demonstrates the conforming-client path;
- the separate `make live-check` adversarial probe demonstrates runtime enforcement against a client that bypasses discovery.

Do not narrate “Copilot tried to publish.” A conforming client cannot select a tool it never discovered.

## Scene 3 — optional Zendesk Support (2–3 minutes)

Present only after the private app and secure-setting substitution are proven.

1. Open a synthetic ticket with requester public, agent public, and private comments.
2. Click **Draft with Talon**.
3. Show that the app selects the newest public requester-authored comment.
4. Show the inserted draft and run-scoped session identifier.
5. Inspect Talon evidence for provider, policy, PII action, and cost.

Do not display the adapter token, Talon key, or provider key.

## Scene 4 — optional n8n partial output (2–3 minutes)

Present only after the workflow has been exported without credentials and clean-imported into the pinned n8n version.

1. Run the workflow.
2. Let successful sections write their partial summaries.
3. Show the later Talon denial caused by projected session spend plus the next estimate crossing the soft cap.
4. Run:

```bash
scripts/assemble-n8n-report.sh
```

5. Open the partial report and `status.json`.
6. Show evidence that the denied request did not reach the provider.

Do not claim a hard no-overshoot reservation.

## Closing proof

For any demonstrated session:

```bash
talon audit export \
  --format signed-json \
  --session <session-id> \
  --output .state/<session-id>.signed.json

talon audit verify --file .state/<session-id>.signed.json
```

Say **tamper-evident and offline-verifiable**, never immutable.

The truthful normal fleet conclusion is:

```text
customer-support   healthy
coding-assistant   healthy
```

Show another state only after an actual configured condition produces it.

## Abort conditions

Stop the live walkthrough when:

- `make ci`, `make live-check`, `real-start`, or `real-status` fails;
- `make real-copilot` exceeds its time limit or any automatic assertion fails;
- Copilot changes more than `src/invoice.mjs`;
- expected MCP receipts or current-run evidence are absent;
- a `release_publish` receipt appears upstream;
- secure Zendesk setting substitution is unproven;
- n8n was not clean-imported from the pinned version;
- a route, cost, denial, or signature cannot be read from actual Talon output.
