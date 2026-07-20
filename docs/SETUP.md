# Standalone setup

This repository is intentionally separate from Talon. Keep the checkouts as siblings so the demo copies the current canonical product-demo configuration instead of maintaining a stale fork.

## Prerequisites

Repository-local validation requires:

- Go 1.23 or newer;
- Node.js 22 or newer;
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
```

It records the source Talon commit and creates `talon.shadow.config.yaml` by changing only the gateway mode. Shadow/enforce selection is gateway-wide and restart-bound.

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

Current Talon CLI contract, audited against `main` commit `24046ca690a616c2710c3084d59857839364bcf3`:

```bash
talon serve \
  --host 127.0.0.1 \
  --port 8080 \
  --gateway \
  --gateway-config "$TALON_CONFIG" \
  --proxy-config config/mcp-proxy.example.yaml
```

Both the LLM gateway and `POST /mcp/proxy` use the same loopback Talon server on port 8080.

Verify:

```bash
curl -fsS -D- "$TALON_GATEWAY/health"
talon agents --url "$TALON_GATEWAY"
```

The runtime fleet check has shipped since Talon v1.9.0 (`internal/cmd/agents_queue.go`); an explicit `--url` is authoritative and errors rather than silently falling back to the offline config view.

To run the same config in shadow mode for the policy-comparison beat, do
not edit YAML; use the v1.9.3 runtime override (#368):

```bash
talon serve --host 127.0.0.1 --port 8080 --gateway \
  --gateway-config "$TALON_CONFIG" \
  --proxy-config config/mcp-proxy.example.yaml \
  --gateway-mode shadow
```

## 6. Start local components

```bash
scripts/start-components.sh
```

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
install -d -m 0777 .state/n8n-output
source .env
docker compose -f integrations/n8n/compose.yaml up
```

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
