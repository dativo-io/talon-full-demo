# Presenter runbook — 10–15 minutes

Use this only after the relevant executable and external gates pass. The short website hero is a separate artifact.

## Demo promise

Show recognizable application shapes using one Talon control plane:

1. Zendesk Support requests a governed reply draft.
2. GitHub Copilot CLI uses Talon for model traffic and reaches a synthetic release service through Talon's MCP proxy.
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
- the bounded Copilot scene proves code generation or patch-edit quality;
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

## Scene 2 — real Copilot + MCP path (1–3 minutes)

This scene has two audience projections over the same Talon evidence. Choose one before the meeting; do not improvise between them.

### Buyer-oriented run

Run:

```bash
make demo-copilot-buyer
```

The real Copilot CLI still executes. Its full client transcript is retained under `.state/`, while the terminal stays focused on the decision receipt:

```text
TALON VERIFIED AI USE CASE
Use case          GitHub Copilot CLI
Operational ID    coding-assistant
Business outcome  Release status checked; release prepared
Action boundary   release_publish did not reach the upstream
Data handling     <detected data>; input redaction recorded
Model path        <model> through Talon
Session cost      <actual cost>
Evidence          <valid> valid / 0 invalid records
Result            VERIFIED
```

Narrate:

> This is one company AI use case with an operational identity. Its model traffic and two permitted release actions passed through Talon. Talon attributed the session cost and generated a record we can verify independently. The publish action did not reach the release service.

Do not explain evidence IDs, JSON fields, cached-token accounting, or Copilot's local tool schemas unless asked.

### Technical run

Run:

```bash
make demo-copilot-tech
```

This streams the real Copilot interaction and then prints:

- the native `talon audit list --session` summary;
- the evidence timeline in chronological order;
- the exact MCP operations that reached the upstream;
- the absent `release_publish` boundary;
- signed-file verification totals;
- commands for inspecting each MCP evidence record;
- the attribution and local-action scope boundaries.

Use this version for platform, security, architecture, and engineering audiences.

### Re-present the same completed run

Neither command below reruns Copilot. They export and verify the latest session from `.state/demo-run.env`, so the buyer and technical projections cannot drift from one another:

```bash
make present-copilot       # concise buyer receipt
make present-copilot-tech  # detailed technical proof
make present-copilot-all   # both, buyer first
```

Do not open Copilot separately, paste a task, resume an old session, or improvise additional prompts.

The underlying real run automatically:

1. creates a fresh Talon session and nonce;
2. runs one non-interactive Copilot prompt with a 90-second hard limit;
3. permits only `release_status` and `release_prepare` from the synthetic release MCP server;
4. explicitly denies shell commands and file writes in the Copilot client;
5. verifies nonce-correlated `release_status` and `release_prepare` receipts;
6. verifies no `release_publish` receipt reached the upstream;
7. verifies current-run signed evidence is attributed to `coding-assistant`.

A valid run must first end with:

```text
REAL COPILOT CASE PASSED
```

State explicitly:

- Copilot's model API traffic and MCP calls passed through Talon;
- the scene intentionally performs no local coding or shell action;
- this proves the real client, model, MCP, acting-identity, receipt, cost, and evidence path;
- client/session provenance is attribution, not independent process attestation;
- the separate `make live-check` adversarial probe demonstrates runtime enforcement against a client that bypasses discovery.

Do not narrate “Copilot tried to publish.” A conforming client cannot select a tool it never discovered. Say: “No publish call reached the upstream.”

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
- either Copilot demo command exceeds its time limit or any automatic assertion fails;
- the buyer and technical views do not resolve to the same `TALON_COPILOT_SESSION_ID`;
- expected MCP receipts or current-run evidence are absent;
- a `release_publish` receipt appears upstream;
- evidence has any invalid, missing-signature, malformed, or unsupported record;
- secure Zendesk setting substitution is unproven;
- n8n was not clean-imported from the pinned version;
- a route, cost, denial, or signature cannot be read from actual Talon output.
