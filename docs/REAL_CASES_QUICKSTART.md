# Real cases: the short path

This is the recommended path for testing the demo against a real provider. The longer [SETUP.md](SETUP.md) remains the reference for manual operation and troubleshooting.

## What each level proves

| Command | Uses a real provider? | What it proves |
|---|---:|---|
| `make validate-local` | No | Repository code, adapters, mock integration, MCP contract, and billing fixture work locally. |
| `make live-check` | No external provider | A real Talon binary enforces MCP policy, attributes identity, signs evidence, and applies the real session-budget engine. |
| `make real-smoke` | **Yes: OpenAI** | A real support request is scanned, redacted, routed through a policy-valid fallback, charged, signed, exported, and verified. |
| `make real-copilot` | **Yes: OpenAI + Copilot CLI** | Real Copilot model traffic and MCP calls pass through Talon under one session and agent identity. |
| Zendesk private app | **Yes: OpenAI + Zendesk** | The installed Zendesk app securely calls the adapter and inserts a governed draft. |
| n8n | **Yes: Anthropic + n8n** | The pinned workflow produces partial output before the next request is denied by the soft session budget. |

## Before you start

You need:

- this repository and `dativo-io/talon` cloned as sibling directories;
- Talon v1.9.3 or newer on `PATH`;
- an OpenAI API key with available quota;
- `jq`, `curl`, `openssl`, Python 3, Git, Go, Node.js and npm.

The fast path binds everything to loopback. Only the optional Zendesk adapter should ever be exposed, and only through an authenticated HTTPS tunnel.

## 1. Prepare once

Keep the real provider key outside `.env`:

```bash
cd ~/talon-full-demo
export OPENAI_API_KEY='sk-...'
make real-prepare
```

`real-prepare` does the work that previously required several manual sections:

1. generates repository-local Talon, agent, signing, adapter and n8n keys when `.env` is absent;
2. copies the canonical three-agent configuration from the sibling Talon checkout;
3. seeds Talon's local encrypted vault;
4. validates the fleet agent directory and runs advisory `talon doctor` checks.

`talon doctor` can print warnings about the single-agent `talon run` default policy or sovereignty defaults. Those warnings are advisory for this fleet gateway demo; `talon validate`, successful startup, the real request, and signed-evidence assertions are the authoritative gates. Any doctor **failure** still stops preparation.

The OpenAI key is written to the Talon vault, not to `.env`. The command does currently pass demo secrets to `talon secrets set` as process arguments; use this only on a trusted single-user demo host.

Anthropic is optional at this stage. Without `ANTHROPIC_API_KEY`, support and Copilot work, while the n8n/document-summary path remains unavailable.

To prepare both providers:

```bash
export OPENAI_API_KEY='sk-...'
export ANTHROPIC_API_KEY='sk-ant-...'
make real-prepare
```

## 2. Start everything

```bash
make real-start
```

This starts and checks:

- Talon LLM gateway on `127.0.0.1:8080`;
- Talon MCP proxy on `127.0.0.1:8081`;
- Copilot session shim on `127.0.0.1:8079`;
- Zendesk adapter on `127.0.0.1:8443`;
- synthetic release MCP server on `127.0.0.1:8090`.

Before starting either Talon process, the wrapper checks both `8080` and `8081`. It refuses to adopt an unknown listener and prints the command needed to inspect it. If a later startup stage fails, repository-owned services are stopped so the next attempt does not inherit a half-started stack.

It also mints a fresh run identity, verifies authenticated MCP initialization, resets the synthetic fixtures, and refuses to continue when Ollama is running. Ollama must be down because the support case intentionally demonstrates a real connection failure followed by policy-valid fallback.

Check the environment at any time:

```bash
make real-status
```

The status command shows the Talon gateway, MCP proxy, Zendesk adapter, release MCP server, Copilot session shim, and whether the GitHub Copilot CLI binary is installed. Missing Copilot CLI is reported as optional until you start the Copilot case.

Logs are written under `.state/logs/`.

## 3. Run the first real case

```bash
make real-smoke
```

`real-smoke` refuses to run unless `real-start` completed successfully and all repository-managed services are still reachable. This prevents a gateway-only partial start from being mistaken for a completed full-stack setup.

The command submits one synthetic support request containing an email address and IBAN. The expected path is:

```text
request
  → Talon detects and redacts email + IBAN
  → preferred local-llama connection fails
  → openai-batch is skipped because the use case policy disallows it
  → OpenAI is selected as the first policy-valid fallback
  → Talon stores signed evidence
  → the script exports and verifies the evidence offline
```

A successful run ends with `REAL CASE PASSED` and prints the session ID and signed evidence file. No real customer data should be used.

## 4. Run the real Copilot case

Install GitHub Copilot CLI once using the explicit repository target:

```bash
make copilot-install
```

This downloads GitHub's official macOS/Linux installer and installs the CLI under `~/.local/bin` by default. Installation is never performed implicitly by `real-start` or `real-copilot`.

Then launch the case:

```bash
make real-copilot
```

The demo configures Copilot CLI in BYOK offline mode:

- `COPILOT_PROVIDER_BASE_URL` points to the local Talon session shim;
- the generated Talon coding-assistant key is used as the provider credential;
- `COPILOT_OFFLINE=true` prevents GitHub authentication and telemetry for this session;
- the OpenAI model call still reaches the internet through Talon because Talon is the configured provider path.

A GitHub login is therefore not required for this model/MCP demo path. GitHub-hosted Copilot features such as GitHub's built-in MCP and cloud delegation are deliberately unavailable and unnecessary here.

Before launch, `make real-copilot` verifies that the installed CLI supports the exact flags used by the demo: `--additional-mcp-config`, `--disable-builtin-mcps`, `--allow-tool`, and `--deny-tool`.

The command resets the failing billing fixture, renders a fresh per-run MCP configuration, prints the exact task and nonce, then launches Copilot with:

- model traffic routed through the local Talon session shim;
- MCP traffic routed through the agent-key-authenticated Talon MCP proxy;
- built-in MCP servers disabled;
- direct `git push` denied by Copilot CLI.

Talon governs the model API traffic and MCP calls routed through it. Copilot's local shell commands and file edits remain outside Talon's control.

After exiting Copilot:

```bash
cd ~/talon-full-demo
source .env
source .state/demo-run.env
npm test --prefix cases/billing-demo
scripts/assert-release-blocked.sh
scripts/assert-evidence.sh \
  --session "$TALON_COPILOT_SESSION_ID" \
  --agent coding-assistant \
  --min-denials 1 \
  --deny-reason forbidden_tools
```

## 5. Optional Zendesk case

The local adapter is already running after `make real-start`. The remaining work cannot be automated by this repository because it happens in your Zendesk account and tunnel provider:

1. expose only `127.0.0.1:8443` through an authenticated HTTPS tunnel;
2. package and upload `integrations/zendesk-app` as a private Zendesk Support app;
3. configure `adapter_domain` with the tunnel hostname only;
4. configure `adapter_token` with `ZENDESK_ADAPTER_TOKEN` from `.env` as a secure setting;
5. test with a synthetic ticket.

Local ZCLI preview is not sufficient because it does not prove Zendesk secure-setting substitution. See [SETUP.md §7](SETUP.md#7-zendesk-private-app).

## 6. Optional n8n case

The n8n path is not yet one-command reproducible. The Compose image is pinned, but the workflow still must be built from `integrations/n8n/workflow-spec.md`, exported without credentials, and clean-imported into a fresh pinned container before the repository can claim a completed real n8n scene.

See [SETUP.md §9](SETUP.md#9-n8n). Do not present n8n as completed until that external gate is satisfied.

## Stop and restart

```bash
make real-stop
```

A later `make real-start` mints a new run ID and restarts the local components. Run `make real-prepare` again only when provider keys, generated local keys, or the canonical Talon configuration change.

## Common failures

### `OPENAI_API_KEY is required`

Export it in the current shell before `make real-prepare`:

```bash
export OPENAI_API_KEY='sk-...'
```

### `GitHub Copilot CLI is not installed or is not on PATH`

Run the explicit installer, then retry:

```bash
make copilot-install
make real-copilot
```

The wrapper also discovers the default non-root installation at `~/.local/bin/copilot`, even when that directory has not yet been added to the interactive shell's `PATH`. Set `COPILOT_BIN=/absolute/path/to/copilot` to use another installation.

### Copilot CLI does not support a required flag

The installed version is too old for this demo. Update it with:

```bash
make copilot-install
```

The official installer updates the existing installation. Then rerun `make real-copilot`.

### Port 8080 or 8081 is already in use

The helper refuses to adopt a process it did not start. First stop any repository-owned services, then inspect the conflicting listener:

```bash
make real-stop || true
sudo ss -ltnp 'sport = :8081'
```

Read the command and PID printed by `ss`. Stop only the stale service you recognize, for example:

```bash
sudo kill <pid>
make real-start
```

Do not kill an unrelated system service. The same procedure applies to port `8080`.

### `the full stack was not started successfully`

`real-start` failed or the services were stopped. Resolve the first startup error, then run:

```bash
make real-start
make real-smoke
```

### Ollama is running

Stop it before `make real-start`; this scenario needs the preferred local provider to fail so Talon can prove fallback.

### Provider returns quota, authentication, or billing errors

That is an upstream account problem, not a Talon policy result. Correct the provider account/key and rerun `make real-prepare`, then `make real-start` and `make real-smoke`.

### `.env` is missing but `.state/talon` exists

The encrypted Talon state is tied to the original `TALON_SECRETS_KEY`. Restore the matching `.env`, or deliberately reset the generated demo state:

```bash
make real-stop || true
rm -rf .state config/generated .env
make real-prepare   # with OPENAI_API_KEY exported
```
