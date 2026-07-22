# Standalone setup

This repository is intentionally separate from Talon. Keep the checkouts as siblings so the demo copies the canonical product-demo configuration instead of maintaining a stale fork.

For the shortest real-provider path, start with [REAL_CASES_QUICKSTART.md](REAL_CASES_QUICKSTART.md). This document is the manual reference.

## Prerequisites

Repository-local validation requires:

- Go 1.23 or newer;
- Node.js 20 or newer;
- Git and Python 3;
- `jq` and `curl`.

The live walkthrough additionally requires:

- a current `dativo-io/talon` checkout and Talon binary;
- provider keys for the routes being demonstrated;
- GitHub Copilot CLI for the optional Copilot case;
- a Zendesk account, ZCLI, and authenticated HTTPS tunnel for the optional Zendesk case;
- Docker Compose for the optional n8n case.

## 1. Validate the repository

```bash
make ci
```

This is the same contract GitHub Actions runs. Do not continue to external setup when it fails.

With `dativo-io/talon` cloned next to this repository, also run:

```bash
make live-check
```

`live-check` builds and starts a real Talon server in a throwaway directory, proves MCP preventive filtering and runtime enforcement, verifies acting identity and signed evidence, and exercises the real session-budget engine.

## 2. Generate isolated local secrets

```bash
make env
source .env
```

The generated `.env` is mode `0600`, ignored by Git, and contains random Talon traffic keys, signing/secrets/admin keys, an adapter token, and an n8n encryption key. It does not fetch any external credentials.

For the automated real path, keep provider keys in the current shell and run `make real-prepare`; the helper stores them in Talon's encrypted local vault rather than writing them to `.env`.

## 3. Copy the canonical Talon demo baseline

```bash
TALON_REPO=../talon make bootstrap-config
cat config/generated/TALON_SOURCE_COMMIT
```

The command copies:

```text
../talon/examples/product-demo/talon.config.yaml
../talon/examples/product-demo/agents/**
../talon/pricing/models.yaml
```

It records the source commit in `TALON_SOURCE_COMMIT` and warns when the checkout differs from `TALON_PINNED_COMMIT`.

## 4. Seed Talon secrets manually

Build Talon from its own repository and put the binary on `PATH`. Then:

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

The automated equivalent is:

```bash
export OPENAI_API_KEY='sk-...'
export ANTHROPIC_API_KEY='sk-ant-...'   # optional until n8n
make real-prepare
```

## 5. Start Talon manually

The audited v1.9.3 topology uses two Talon processes sharing the same low-concurrency demo data directory:

```bash
cd config/generated

# LLM gateway: Copilot model traffic, Zendesk drafts, n8n.
talon serve --host 127.0.0.1 --port 8080 --gateway &

# MCP boundary: agent-key-authenticated release tools.
talon serve --host 127.0.0.1 --port 8081 \
  --proxy-config ../mcp-proxy.example.yaml &
```

Both processes share `TALON_DATA_DIR`, so LLM and MCP evidence are joinable by session. This is a sequential demo topology, not a general production recommendation for shared SQLite concurrency.

### Why the MCP proxy is separate

In v1.9.3, combining gateway and proxy configuration places `/mcp/proxy` behind the gateway's admin-only middleware. A proxy-only process instead authenticates with the coding-assistant agent key, so MCP records carry the acting `agent_id = coding-assistant` without giving the client the Talon admin key. `make live-check` executes and asserts this boundary.

Start both processes from `config/generated`, because the canonical `agents_dir: agents` path is relative to the working directory.

Verify:

```bash
curl -fsS "$TALON_GATEWAY/health"
curl -fsS "$TALON_MCP_GATEWAY/health"
talon agents --url "$TALON_GATEWAY"
```

For the normal automated path, use:

```bash
make real-start
make real-status
```

## 6. Mint a run and start local components manually

After both Talon processes are healthy:

```bash
make preflight
scripts/stop-components.sh || true
scripts/start-components.sh
```

`preflight` creates a fresh run ID, Copilot/n8n session IDs, run start timestamp, and release nonce in `.state/demo-run.env`. It also performs an authenticated MCP initialization—not only a generic health check.

The local defaults are:

```text
Copilot shim        127.0.0.1:8079
Zendesk adapter     127.0.0.1:8443
Release MCP server  127.0.0.1:8090
```

Stop only PID-verified repository children:

```bash
scripts/stop-components.sh
```

## 7. Zendesk private app

1. Validate and package `integrations/zendesk-app` with ZCLI.
2. Expose only the adapter through an authenticated HTTPS tunnel.
3. Install the app privately.
4. Configure `adapter_domain` as a hostname only—no scheme, path, localhost, or IP literal.
5. Configure `adapter_token` as the secure header-scoped setting.
6. Use a synthetic ticket containing requester-authored public comments plus agent/private comments.
7. Confirm the app selects the newest public requester comment and inserts only the returned draft.

Local ZCLI rendering does not prove secure-setting substitution. The installed private app is the required test.

## 8. GitHub Copilot CLI

Install the CLI explicitly once:

```bash
make copilot-install
```

Run the supported case only through:

```bash
make real-copilot
```

Do not start a separate interactive session or paste a task manually. The wrapper:

1. restores and verifies the committed failing billing fixture;
2. creates a fresh Talon session and nonce;
3. restarts the shim and synthetic release service under that run identity;
4. runs Copilot programmatically in BYOK offline mode;
5. points model traffic at the local Talon session shim;
6. points MCP traffic at the agent-key-authenticated Talon MCP proxy;
7. permits only `npm run fix-demo`, `npm test`, `release_status`, and `release_prepare`;
8. gives Copilot no general file-write permission;
9. enforces a 120-second wall-clock limit;
10. independently verifies the exact source diff, passing test, nonce-correlated receipts, absent `release_publish` receipt, and signed current-run evidence.

The committed `npm run fix-demo` command performs exactly the known one-line billing correction and fails unless the expected regression appears exactly once. This intentionally tests the real Copilot client and Talon integration path, not Copilot's free-form patch generation.

The default model is `gpt-4o-mini`; override it only for diagnosis:

```bash
COPILOT_MODEL=gpt-4o make real-copilot
```

The fixture has no Git remote. Copilot CLI's local shell permissions are client controls, not Talon controls. Talon governs only model and MCP traffic routed through its boundaries.

## 9. n8n

The Compose file is pinned to n8n `2.30.4` and exposes only loopback port 5678:

```bash
install -d -m 0777 .state/n8n-output
source .env
docker compose -f integrations/n8n/compose.yaml up
```

The `0777` directory is throwaway demo scratch space for a container UID, not a deployment pattern.

The workflow must still be built from `integrations/n8n/workflow-spec.md`, exported without credentials, and clean-imported into a fresh pinned container before the repository can claim a completed real n8n scene.

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

Provider routes, redaction, cost, policy decisions, identity, session attribution, and signatures must come from Talon output. Never replace native evidence with presenter-authored success text.

## Security and truth boundaries

- All data and tool effects are synthetic.
- Services bind to loopback by default.
- Only the optional Zendesk adapter crosses the local boundary, through authenticated TLS termination.
- Talon governs LLM traffic and MCP calls routed through it; local shell, filesystem, browser, and direct API actions remain outside its control.
- The Copilot scene proves the real client-integration path, not autonomous code-edit quality.
- HMAC evidence is tamper-evident and offline-verifiable, not immutable.
- Session budgets are soft caps.
