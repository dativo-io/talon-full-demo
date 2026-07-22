# Real cases: the short path

This is the recommended path for testing the demo against real providers. The longer [SETUP.md](SETUP.md) remains the manual reference.

## What each level proves

| Command | Real provider? | What it proves |
|---|---:|---|
| `make validate-local` | No | Repository code, adapters, mock integration, MCP contract, and billing fixture work locally. |
| `make live-check` | No external provider | A real Talon binary enforces MCP policy, attributes identity, signs evidence, and applies the real session-budget engine. |
| `make real-smoke` | OpenAI | A real support request is redacted, routed through policy-valid failover, charged, signed, exported, and verified. |
| `make real-copilot` | OpenAI + Copilot CLI | One bounded real Copilot run uses Talon for model traffic, calls two allowed MCP tools, and produces current-run evidence. |
| `make demo-copilot-buyer` | OpenAI + Copilot CLI | Runs the same real case and ends on a concise buyer-readable receipt derived from signed evidence. |
| `make demo-copilot-tech` | OpenAI + Copilot CLI | Runs the same real case and expands its Talon session, MCP boundary, attribution, cost, and signature verification. |
| Zendesk private app | OpenAI + Zendesk | The installed Zendesk app securely calls the adapter and inserts a governed draft. |
| n8n | Anthropic + n8n | The pinned workflow demonstrates a soft session-budget boundary. This remains externally gated. |

## Prerequisites

You need:

- this repository and `dativo-io/talon` cloned as sibling directories;
- Talon v1.9.3 or newer on `PATH`;
- an OpenAI API key with available quota;
- `jq`, `curl`, `openssl`, Python 3, Git, Go, Node.js and npm.

Everything in the fast path binds to loopback. Only the optional Zendesk adapter should ever be exposed, and only through an authenticated HTTPS tunnel.

## 1. Prepare once

Keep the real provider key outside `.env`:

```bash
cd ~/talon-full-demo
export OPENAI_API_KEY='sk-...'
make real-prepare
```

`real-prepare`:

1. generates repository-local demo keys when `.env` is absent;
2. copies the canonical three-agent Talon configuration;
3. seeds Talon's encrypted local vault;
4. validates the fleet agent directory;
5. runs advisory `talon doctor` checks.

Warnings about the single-agent default policy or sovereignty defaults are advisory for this fleet gateway demo. Any doctor **failure** still stops preparation.

Anthropic is optional until the n8n/document-summary case:

```bash
export ANTHROPIC_API_KEY='sk-ant-...'
make real-prepare
```

## 2. Start the stack

```bash
make real-start
```

This starts and checks:

- Talon LLM gateway on `127.0.0.1:8080`;
- Talon MCP proxy on `127.0.0.1:8081`;
- Copilot session shim on `127.0.0.1:8079`;
- Zendesk adapter on `127.0.0.1:8443`;
- synthetic release MCP server on `127.0.0.1:8090`.

The wrapper checks both Talon ports before starting either process, refuses to adopt unknown listeners, and rolls back repository-owned services after partial failures.

Check readiness at any time:

```bash
make real-status
```

Logs are written under `.state/logs/`.

## 3. Run the real support case

```bash
make real-smoke
```

Expected path:

```text
synthetic support request
  → Talon detects and redacts email + IBAN
  → preferred local-llama connection fails
  → disallowed openai-batch fallback is skipped
  → OpenAI is selected
  → Talon stores signed evidence
  → the script exports and verifies that evidence
```

A successful run ends with `REAL CASE PASSED` and prints the session and signed evidence file.

## 4. Run and present the bounded real Copilot case

Install GitHub Copilot CLI once:

```bash
make copilot-install
```

Choose one audience flow.

### Buyer, product, or executive audience

```bash
make demo-copilot-buyer
```

The real Copilot client still runs, but its detailed transcript is retained under `.state/`. The visible ending is a concise receipt computed from a fresh signed Talon export:

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

### Platform, security, architecture, or engineering audience

```bash
make demo-copilot-tech
```

This streams the real client and then prints the native Talon session summary, chronological evidence timeline, MCP action boundary, attribution, cost, and signed-file verification totals.

### Re-present the exact same completed session

These commands do not rerun Copilot:

```bash
make present-copilot       # buyer receipt
make present-copilot-tech  # technical proof
make present-copilot-all   # both, buyer first
```

Both views recreate and verify the signed export for `TALON_COPILOT_SESSION_ID` from `.state/demo-run.env`. They are two projections of the same evidence—not separate presenter-authored stories.

Do **not** open Copilot separately and paste a task. The real driver invokes Copilot programmatically with one bounded prompt.

The underlying command automatically:

1. mints a fresh Talon session and nonce for the attempt;
2. restarts the local shim and synthetic integration components with that identity;
3. invokes Copilot CLI with `--prompt` and `--no-ask-user`;
4. allows only `release_status` and `release_prepare` from the `release-gateway` MCP server;
5. explicitly denies shell commands and file writes in the client;
6. terminates the complete Copilot process group after 90 seconds by default;
7. independently verifies nonce-correlated MCP receipts, the absence of a publish receipt, and current-run signed Talon evidence.

A successful real run ends with:

```text
REAL COPILOT CASE PASSED
```

The default time limit can be adjusted for diagnosis, not for presentations:

```bash
COPILOT_DEMO_TIMEOUT_SECONDS=120 make real-copilot
```

A run that times out or fails any independent assertion does not count as a pass.

### What Talon proves in this case

- Copilot model traffic reaches OpenAI through the Talon session shim.
- MCP traffic reaches the Talon MCP proxy using the `coding-assistant` agent key.
- Allowed `release_status` and `release_prepare` calls reach the synthetic upstream.
- No `release_publish` receipt reaches the upstream.
- Current-run cost and records are attributed to `coding-assistant`.
- The signed evidence export verifies with zero invalid, missing-signature, malformed, or unsupported records.

The scene proves the real Copilot client path, governed model traffic, governed MCP traffic, identity, cost, and evidence. It does not claim Talon governs local coding actions or that Copilot successfully edits code. Client/session provenance remains attribution, not independent process attestation.

## 5. Optional Zendesk case

After `make real-start`, the local adapter is already running. The remaining work happens in your Zendesk account and tunnel provider:

1. expose only `127.0.0.1:8443` through an authenticated HTTPS tunnel;
2. package and upload `integrations/zendesk-app` as a private Zendesk Support app;
3. configure `adapter_domain` with the tunnel hostname only;
4. configure `adapter_token` with `ZENDESK_ADAPTER_TOKEN` from `.env` as a secure setting;
5. test with a synthetic ticket.

Local ZCLI preview is not sufficient because it does not prove Zendesk secure-setting substitution. See [SETUP.md §7](SETUP.md#7-zendesk-private-app).

## 6. Optional n8n case

The n8n path is not yet one-command reproducible. The Compose image is pinned, but the workflow still must be built from `integrations/n8n/workflow-spec.md`, exported without credentials, and clean-imported into a fresh pinned container.

See [SETUP.md §9](SETUP.md#9-n8n). Do not present n8n as completed until that gate passes.

## Stop and restart

```bash
make real-stop
```

A later `make real-start` mints a new run identity. Run `make real-prepare` again only when provider keys, generated local keys, or canonical Talon configuration change.

## Common failures

### Copilot attempts shell commands, file edits, or reports permission denied

That is not part of the current real-client scene. Pull the current repository and use only the bounded MCP driver:

```bash
cd ~/talon-full-demo
git pull --ff-only
make demo-copilot-buyer   # or: make demo-copilot-tech
```

The current command allows only the two release MCP tools, explicitly denies shell and write operations, and terminates after 90 seconds. Do not resume an old Copilot session.

### The buyer or technical presenter reports an assertion error

Do not present that session. The projection fails closed when the signed export, session attribution, exact MCP tool set, upstream receipts, or verification totals do not match. Rerun:

```bash
make real-status
make real-copilot
make present-copilot-all
```

### `GitHub Copilot CLI is not installed or is not on PATH`

```bash
make copilot-install
make demo-copilot-buyer
```

The wrapper also discovers `~/.local/bin/copilot`. Set `COPILOT_BIN=/absolute/path/to/copilot` for another installation.

### Copilot CLI does not support a required flag

```bash
make copilot-install
```

The installer updates the existing installation.

### Port 8080 or 8081 is already in use

```bash
make real-stop || true
sudo ss -ltnp 'sport = :8081'
```

Stop only the stale process you recognize, then rerun `make real-start`. The same procedure applies to port `8080`.

### `the full stack was not started successfully`

Resolve the first startup error, then run:

```bash
make real-start
make real-smoke
```

### Ollama is running

Stop it before `make real-start`; the support scenario intentionally requires the preferred local provider to fail.

### Provider returns quota, authentication, or billing errors

Correct the provider account/key and rerun `make real-prepare`, `make real-start`, and the relevant real case.

### `.env` is missing but `.state/talon` exists

The encrypted state is tied to the original `TALON_SECRETS_KEY`. Restore the matching `.env`, or deliberately reset:

```bash
make real-stop || true
rm -rf .state config/generated .env
make real-prepare   # with OPENAI_API_KEY exported
```
