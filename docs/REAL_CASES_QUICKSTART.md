# Real cases: the short path

This is the recommended path for testing the demo against real providers. The longer [SETUP.md](SETUP.md) remains the manual reference.

## What each level proves

| Command | Real provider? | What it proves |
|---|---:|---|
| `make validate-local` | No | Repository code, adapters, mock integration, MCP contract, and billing fixture work locally. |
| `make live-check` | No external provider | A real Talon binary enforces MCP policy, attributes identity, signs evidence, and applies the real session-budget engine. |
| `make real-smoke` | OpenAI | A real support request is redacted, routed through policy-valid failover, charged, signed, exported, and verified. |
| `make real-copilot` | OpenAI + Copilot CLI | One bounded real Copilot run changes exactly one source file, passes its test, calls two allowed MCP tools, and produces current-run evidence. |
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

## 4. Run the bounded real Copilot case

Install GitHub Copilot CLI once:

```bash
make copilot-install
```

Then run:

```bash
make real-copilot
```

Do **not** open Copilot separately and paste a task. `make real-copilot` now drives the CLI programmatically with one bounded prompt.

The command automatically:

1. restores the billing fixture from the outer repository's committed failing baseline;
2. mints a fresh Talon session and nonce for this attempt;
3. restarts the local shim and integration components with that identity;
4. invokes Copilot CLI with `--prompt` and `--no-ask-user`;
5. allows only the intended source-file write, one `npm test`, and the two allowed release MCP tools;
6. terminates the entire Copilot process group after 180 seconds by default;
7. independently verifies the exact one-file diff, passing test, MCP receipts, and current-run signed Talon evidence.

The task itself is deliberately narrow: remove per-line invoice rounding, run the test once, then call `release_status` and `release_prepare`. This is a Talon integration demonstration, not a benchmark of open-ended autonomous debugging.

A successful run ends with:

```text
REAL COPILOT CASE PASSED
```

and prints the exact diff, Talon session, and transcript path.

The default time limit can be adjusted for diagnosis, not for presentations:

```bash
COPILOT_DEMO_TIMEOUT_SECONDS=240 make real-copilot
```

A run that times out or fails any independent assertion does not count as a pass.

### What Talon proves in this case

- Copilot model traffic reaches OpenAI through the Talon session shim.
- MCP traffic reaches the Talon MCP proxy using the coding-assistant agent key.
- Allowed `release_status` and `release_prepare` calls reach the synthetic upstream.
- No `release_publish` receipt reaches the upstream.
- Current-run records are signed and attributed to `coding-assistant`.

Talon does not govern Copilot's local file edit or local `npm test`; those remain local client actions.

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

### Copilot runs for many minutes or consumes excessive tokens

That was the behavior of the old interactive driver. Stop the session with `Ctrl+C`, pull the current repository, and use only the bounded command:

```bash
cd ~/talon-full-demo
git pull --ff-only
make real-copilot
```

The new command restores the fixture from the committed baseline and terminates after 180 seconds. Do not resume the old Copilot session.

### `GitHub Copilot CLI is not installed or is not on PATH`

```bash
make copilot-install
make real-copilot
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
