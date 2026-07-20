# Presenter runbook — 10–15 minutes

Use this only after `make ci`, `make preflight`, and every relevant external gate in `docs/BLOCKERS.md` passes. The short website hero is a separate artifact and remains unchanged.

## Demo promise

Show three existing application shapes using one Talon control plane:

1. Zendesk Support requests a governed reply draft.
2. GitHub Copilot CLI fixes a real failing local test and reaches a synthetic release service through Talon's MCP proxy.
3. n8n writes useful partial report output before a later request is denied by the configured soft session budget.

Evidence is the proof layer. The applications do not invent provider routes, policy decisions, costs, or signatures.

## Truth boundaries

The demo may claim:

- one Talon server authenticates three AI-use-case identities;
- traffic reaches Talon through current OpenAI-compatible, Anthropic, and MCP interfaces;
- policy can redact or deny before provider/tool execution when the request crosses a Talon interception boundary;
- allowed MCP calls reach the synthetic release server while forbidden `release_publish` does not;
- session-scoped signed evidence can be exported and verified offline.

The demo must not claim:

- Talon controls Copilot's local shell, filesystem, browser, or direct network actions;
- the Copilot `git push` restriction is a Talon feature;
- session budgets are atomic hard reservations;
- one denial automatically creates `needs-attention` health;
- HMAC evidence is immutable or proves that the configured policy was correct;
- Zendesk secure settings, real Copilot BYOK, n8n import/export, or provider behavior were validated unless the presenter actually completed those gates.

## Topology

```text
Zendesk ticket editor
  -> Zendesk server-side request proxy
  -> authenticated HTTPS tunnel
  -> adapter 127.0.0.1:8443
  -> Talon 127.0.0.1:8080/v1/proxy/<provider>/v1/chat/completions

GitHub Copilot CLI
  -> session shim 127.0.0.1:8079
  -> Talon 127.0.0.1:8080/v1/proxy/openai/v1/...

Copilot remote HTTP MCP
  -> Talon 127.0.0.1:8080/mcp/proxy
  -> synthetic release MCP 127.0.0.1:8090/mcp

n8n 127.0.0.1:5678
  -> host.docker.internal:8080/v1/proxy/anthropic/v1/messages
```

Only the Zendesk adapter is exposed outside loopback, through an authenticated HTTPS tunnel.

## Before the audience joins

```bash
make ci
make preflight
scripts/reset-billing-fixture.sh
scripts/render-copilot-mcp-config.sh
```

Confirm:

- current Talon source commit is recorded in `config/generated/TALON_SOURCE_COMMIT`;
- Talon, adapter, shim, release MCP, and optional n8n health checks pass;
- Ollama is stopped for any deliberate fallback scene;
- `.state/release-mcp-receipts.jsonl` is empty;
- the billing fixture fails and has no Git remote;
- provider keys and customer content are not visible on screen;
- the evidence signing key is available to Talon but never printed.

## Scene 1 — Zendesk Support (3 minutes)

1. Open a synthetic ticket with a requester public comment, an agent public comment, and a private comment.
2. Click **Draft with Talon**.
3. Point out that the app fetched the Ticket Comments API and selected the newest public requester-authored comment; it did not use `ticket.comment.text`.
4. Show the inserted draft and its `zendesk-ticket-<numeric-id>` session identifier.
5. Inspect Talon evidence for that session. Read provider, policy, PII action, and cost only from the record.

Do not display the adapter token, Talon agent key, or provider key. The adapter response contains only `draft` and `session_id`.

## Scene 2 — Copilot model path and local fixture (3 minutes)

1. Start Copilot inside `cases/billing-demo` with the exact command in `docs/SETUP.md`.
2. Show that `npm test` fails before the fix.
3. Ask Copilot to implement the minimal correction and rerun the test.
4. Show the passing test and local diff.
5. State explicitly: the shim governs only Copilot's model API traffic by adding session attribution; file edits and shell commands stay local and outside Talon.
6. Show that the repository has no Git remote and that direct push is denied by Copilot CLI permissions.

## Scene 3 — MCP release boundary (3 minutes)

This scene is permitted only after the current-Talon end-to-end gate passes.

1. Ask Copilot to call `release_status` and `release_prepare` through `release-gateway`.
2. Ask for `release_publish`.
3. Show the native Talon denial.
4. Run:

```bash
scripts/assert-release-blocked.sh
```

5. Display the synthetic upstream receipt file. It must contain `release_status` and `release_prepare`, and no `release_publish`.
6. Inspect the signed Talon evidence. It must carry authenticated `coding-assistant`, the asserted Copilot session, one request-scoped correlation ID, and the native deterministic tool-denial explanation.

The synthetic release server has no external publishing implementation; even an allowed call can only append a local synthetic receipt.

## Scene 4 — n8n partial business output (2–3 minutes)

1. Run the workflow built and clean-imported from the pinned n8n `2.30.4` UI.
2. Let successful sections write individual `*.summary.md` files.
3. Show the later Talon denial caused by projected session spend plus the next estimate exceeding the soft cap.
4. Run:

```bash
scripts/assemble-n8n-report.sh
```

5. Open the partial report and `status.json`.
6. Show evidence that the denied request did not reach the provider. Do not claim a hard no-overshoot reservation.

If the workflow has not been exported and clean-imported from the pinned version, describe this as an implementation specification, not a completed scene.

## Closing proof (1–2 minutes)

For each demonstrated session:

```bash
talon audit export \
  --format signed-json \
  --session <session-id> \
  --output .state/<session-id>.signed.json

talon audit verify --file .state/<session-id>.signed.json
```

Tamper only with a disposable copy, rerun verification, and show failure. Say **tamper-evident and offline-verifiable**, never immutable.

The truthful normal fleet conclusion is:

```text
customer-support   healthy
coding-assistant   healthy
```

Show `document-summary blocked` only after a real configured period/session condition actually blocks new work. One MCP denial alone does not justify `needs-attention`.

## Abort conditions

Stop the live walkthrough and fall back to local artifacts when:

- `make ci` or preflight fails;
- secure Zendesk setting substitution is unproven;
- Copilot does not use the configured provider or MCP server;
- a forbidden MCP call appears in upstream receipts;
- Talon evidence lacks authenticated agent/session attribution;
- n8n was not clean-imported from the pinned version;
- a provider route, cost, denial, or signature cannot be read from actual Talon output.
