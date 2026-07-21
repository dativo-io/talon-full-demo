# Standalone setup

This repository is intentionally separate from Talon. Keep the checkouts as siblings so the demo copies the current canonical product-demo configuration instead of maintaining a stale fork.

## Prerequisites

Repository-local validation requires:

- Go 1.23 or newer;
- Node.js 20 or newer (hosted CI pins 22);
- Git;
- Python 3;
- `jq`;
- `curl`.

The live walkthrough additionally requires:

- a current `dativo-io/talon` checkout and binary;
- provider keys for the routes you actually demonstrate;
- GitHub Copilot CLI;
- a Zendesk account with private-app permissions and ZCLI;
- Docker Compose for n8n;
- an authenticated HTTPS tunnel for the Zendesk adapter.

## 1. Validate the repository

```bash
make ci
```

This is the same command GitHub Actions runs. Do not continue to external setup when it fails.

With a `dativo-io/talon` checkout next to this repository you can also run the
live end-to-end proof against a real Talon server (no mock): `make live-check`.
It builds Talon, runs the MCP forbidden-tool scene and the real session-budget
engine in a throwaway temp dir, and is the recommended go/no-go check before
presenting (see `docs/VALIDATION.md`).

## 2. Generate isolated local secrets

```bash
make env
source .env
```

The generated `.env` is mode `0600`, ignored by Git, and contains random Talon traffic keys, signing/secrets/admin keys, an adapter token, and an n8n encryption key. Add provider keys only to the local file. Never commit it.

## 3. Copy the current Talon demo baseline

```bash
TALON_REPO=../talon make bootstrap-config
cat config/generated/TALON_SOURCE_COMMIT
```

The command copies:

```text
../talon/examples/product-demo/talon.config.yaml
../talon/examples/product-demo/agents/**
../talon/pricing/models.yaml            # so served costs use the real table
```

It records the source Talon commit in `TALON_SOURCE_COMMIT` and warns if the checkout does not match `TALON_PINNED_COMMIT` (the audited commit this demo tracks). No shadow config file is generated: shadow mode is the v1.9.3 `--gateway-mode shadow` runtime override (see section 5), gateway-wide and restart-bound.

## 4. Seed Talon secrets

Build Talon from its own repository and expose the binary on `PATH`. Then use the generated `.env` values consistently:

```bash
export TALON_GATEWAY_CONFIG="$TALON_CONFIG"

talon secrets set local-llama-demo-key not-a-real-key-local-demo \
  --tenant acme --agent customer-support

talon secrets set openai-api-key "$OPENAI_API_KEY" \
  --tenant acme --agent customer-support --agent coding-assistant

talon secrets set anthropic-api-key "$ANTHROPIC_API_KEY" \
  --tenant acme --agent document-summary

talon secrets set customer-support-talon-key "$TALON_CUSTOMER_SUPPORT_KEY" \
  --tenant acme --agent customer-support

talon secrets set coding-assistant-talon-key "$TALON_CODING_ASSISTANT_KEY" \
  --tenant acme --agent coding-assistant

talon secrets set document-summary-talon-key "$TALON_DOCUMENT_SUMMARY_KEY" \
  --tenant acme --agent document-summary

talon validate --dir config/generated/agents
talon doctor
```

Provider keys remain in Talon's vault. The Zendesk browser and adapter never receive them.

## 5. Start Talon

Current Talon CLI contract, audited against `main` commit `24046ca690a616c2710c3084d59857839364bcf3` and executed against a server built from that commit.

Run **two** Talon processes that share one data directory (`TALON_DATA_DIR`),
both started from `config/generated`. The split exists for a governance reason,
not convenience — see the note below.

```bash
cd config/generated

# 1) LLM gateway on :8080 — Copilot model traffic, Zendesk drafts, n8n.
talon serve --host 127.0.0.1 --port 8080 --gateway &

# 2) MCP proxy on :8081 — the release-tool boundary, agent-key authenticated.
talon serve --host 127.0.0.1 --port 8081 --proxy-config ../mcp-proxy.example.yaml &
```

Both share `TALON_DATA_DIR` (set in `.env`), so LLM and MCP evidence land in the
same signed store, joinable by session.

The two processes share one SQLite `TALON_DATA_DIR`. Treat this as a
**low-concurrency demo topology** — the demo issues requests sequentially, so
write contention does not arise — not a claim of formally supported multi-process
Talon operation. For higher concurrency or a production deployment, give each
process its own data directory (evidence stays per-process) or run a single
process, until Talon documents shared-store multi-process support.

**Why two processes (identity + least privilege).** In v1.9.3 a single-process
`--gateway` also serving `--proxy-config` puts `/mcp/proxy` behind admin-only
middleware (fail-closed native-execution route, upstream #266): the agent bearer
alone gets 401, so the client would have to carry the operator admin key, and
Talon — seeing no authenticated agent — attributes MCP evidence to the proxy
config's own name (`coding-assistant-release-tools`) rather than the acting
agent. A **proxy-only** process (no `--gateway`) authenticates `/mcp/proxy` with
**agent keys** (`TenantKeyMiddleware`), so the `coding-assistant` bearer both
authenticates and owns the evidence: MCP records and the agent's LLM records
share `agent_id = coding-assistant` and the same session, and the Copilot process
never holds the admin key. This is executed and asserted by `make live-check`.

Run each server from `config/generated`: the canonical config's `agents_dir: agents`
resolves relative to the server's working directory in v1.9.3 (upstream's own
`examples/product-demo/demo.sh` also starts the server from the directory holding
`talon.config.yaml`). Started from the repository root it fails at boot with
"gateway mode requires at least one keyed agent".

Verify both:

```bash
curl -fsS -D- "$TALON_GATEWAY/health"       # :8080 gateway
curl -fsS -D- "$TALON_MCP_GATEWAY/health"   # :8081 MCP proxy
talon agents --url "$TALON_GATEWAY"
```

The runtime fleet check has shipped since Talon v1.9.0 (`internal/cmd/agents_queue.go`); an explicit `--url` is authoritative and errors rather than silently falling back to the offline config view.

To run the gateway in shadow mode for the policy-comparison beat, do not edit
YAML; use the v1.9.3 runtime override (#368) on the gateway process:

```bash
cd config/generated
talon serve --host 127.0.0.1 --port 8080 --gateway --gateway-mode shadow &
```

## 5b. Mint the demo run and verify the control plane

```bash
make preflight
```

Run this **after** Talon and **before** local components. It mints a fresh
`TALON_DEMO_RUN_ID` into `.state/demo-run.env` (per-run session ids, run start
time, release nonce) so each run's evidence is isolated from earlier runs, and it
hard-verifies that both the gateway (`:8080`) and the MCP proxy (`:8081`) are up —
including a real authenticated MCP `initialize` against `/mcp/proxy`, which a
generic `/health` cannot prove. Re-run it for every rehearsal.

## 6. Start local components

```bash
scripts/start-components.sh
```

`start-components.sh` sources `.state/demo-run.env`, so the Copilot shim and
Zendesk adapter attribute traffic to this run's sessions; its readiness gates are
the authoritative health check for the adapter, shim, and release MCP server.

Defaults:

```text
Copilot shim        127.0.0.1:8079
Zendesk adapter     127.0.0.1:8443 (plain HTTP behind tunnel TLS)
Release MCP server  127.0.0.1:8090
```

Stop only the PID-verified child processes recorded by the start script:

```bash
scripts/stop-components.sh
```

## 7. Zendesk private app

1. Validate and package `integrations/zendesk-app` with ZCLI.
2. Expose only the adapter through an authenticated HTTPS tunnel.
3. Install the app privately.
4. Configure `adapter_domain` as a hostname only; no scheme, path, localhost, or IP literal.
5. Configure `adapter_token` as the secure header-scoped setting.
6. Use a synthetic ticket containing requester-authored public comments plus agent/private comments.
7. Confirm the app selects the newest public requester comment and inserts only the returned draft.

Local ZCLI rendering does not prove secure-setting substitution. The installed private app is the required test.

## 8. GitHub Copilot CLI

Reset the dependency-free fixture and render a session-only MCP config:

```bash
scripts/reset-billing-fixture.sh
scripts/render-copilot-mcp-config.sh
```

The rendered config points at the **MCP-proxy process** (`$TALON_MCP_GATEWAY`,
`:8081`) and authenticates with the `coding-assistant` agent bearer only — no
admin key. Because that process is proxy-only (agent-key authenticated), the MCP
release-tool actions carry `agent_id = coding-assistant`, the same identity as
the Copilot model traffic through the gateway. `make live-check` executes and
asserts this: the LLM call and the MCP calls in one session all attribute to
`coding-assistant`. (See §5 for why the MCP proxy runs as its own process.)

Configure Copilot's current BYOK variables:

```bash
export COPILOT_PROVIDER_TYPE=openai
export COPILOT_PROVIDER_BASE_URL=http://127.0.0.1:8079/v1/proxy/openai/v1
export COPILOT_PROVIDER_API_KEY="$TALON_CODING_ASSISTANT_KEY"
export COPILOT_MODEL=gpt-4o
export COPILOT_OFFLINE=true
```

Then:

```bash
cd cases/billing-demo
copilot \
  --additional-mcp-config=@../../.state/copilot-mcp.json \
  --disable-builtin-mcps \
  --allow-tool='release-gateway' \
  --deny-tool='shell(git push)'
```

The fixture has no Git remote. The direct `git push` denial belongs to Copilot CLI, not Talon. The model must support streaming and tool calling.

Talon issues #346 and #350 are fixed on current `main`. Still run the complete proof in `docs/BLOCKERS.md`: allowed tools must reach the synthetic upstream, `release_publish` must not, and the signed evidence must carry the authenticated agent plus session/correlation attribution.

## 9. n8n

The Compose file is pinned to n8n `2.30.4` and exposes only loopback port 5678:

```bash
install -d -m 0777 .state/n8n-output   # demo-only: the container writes here as its own UID
source .env
docker compose -f integrations/n8n/compose.yaml up
```

The `0777` is a throwaway demo scratch directory for the loopback container, not
a deployment pattern — a real deployment matches the container UID or uses a
named volume instead of world-writable permissions.

Build the workflow from `integrations/n8n/workflow-spec.md` in that pinned UI. Export without credentials, clean-import into a fresh container running the same version, reconnect the Header Auth credential, and rerun before committing workflow JSON. No workflow export is currently claimed.

## 10. Evidence gates

Before presenting a live claim:

```bash
talon audit list --session <session-id>
talon audit export \
  --format signed-json \
  --session <session-id> \
  --output .state/<session-id>.signed.json
talon audit verify --file .state/<session-id>.signed.json
```

Provider routes, redaction, cost, policy decisions, identity, session attribution, and signatures must come from Talon output. Never replace native reason fields with presenter-authored success text.

## Security boundaries

- All data and tool effects are synthetic.
- Services bind to loopback by default.
- Only the Zendesk adapter crosses the local boundary, through authenticated TLS termination.
- Talon governs LLM traffic and MCP calls routed through it; local shell, filesystem, browser, and direct API actions remain outside its control.
- HMAC evidence is tamper-evident and verifiable, not immutable.
- Session budgets are soft caps.
