# Standalone setup

This repository is intentionally separate from Talon. Keep the checkouts as siblings so the demo can copy, not fork, Talon's current canonical product-demo configuration.

## 1. Prerequisites

Required for local validation:

```text
Go 1.23+
Node.js 22+
npm
Git
Python 3
jq
curl
```

Additional real-demo dependencies:

```text
current Talon checkout and binary
OpenAI and Anthropic API keys
GitHub Copilot CLI
Zendesk account with private-app permissions and ZCLI
Docker Compose for n8n
an HTTPS tunnel for the Zendesk adapter
```

## 2. Validate the standalone components

```bash
make validate-local
```

Do not continue to a live presentation if this fails.

## 3. Generate isolated secrets and paths

```bash
make env
source .env
```

The generated `.env` is mode `0600`, ignored by Git, and contains random Talon traffic keys, signing/secrets/admin keys, adapter token, and n8n encryption key. Add provider keys locally; never commit them.

## 4. Copy the current Talon baseline

```bash
TALON_REPO=../talon make bootstrap-config
cat config/generated/TALON_SOURCE_COMMIT
```

This copies:

```text
../talon/examples/product-demo/talon.config.yaml
../talon/examples/product-demo/agents/**
```

It also creates `talon.shadow.config.yaml` by changing only `gateway.mode` to `shadow`. Shadow/enforce selection requires a Talon restart; it is not a per-agent live toggle.

## 5. Build and seed Talon

Build Talon from its own repository and make it available on `PATH`. Use the generated `.env` values consistently for secret seeding and server startup.

```bash
export TALON_GATEWAY_CONFIG="$TALON_CONFIG"

# Provider secrets
talon secrets set local-llama-demo-key not-a-real-key-local-demo --tenant acme --agent customer-support
talon secrets set openai-api-key "$OPENAI_API_KEY" --tenant acme --agent customer-support --agent coding-assistant
talon secrets set anthropic-api-key "$ANTHROPIC_API_KEY" --tenant acme --agent document-summary

# One active Talon key per use case
talon secrets set customer-support-talon-key "$TALON_CUSTOMER_SUPPORT_KEY" --tenant acme --agent customer-support
talon secrets set coding-assistant-talon-key "$TALON_CODING_ASSISTANT_KEY" --tenant acme --agent coding-assistant
talon secrets set document-summary-talon-key "$TALON_DOCUMENT_SUMMARY_KEY" --tenant acme --agent document-summary

talon validate --dir config/generated/agents
talon doctor
```

Start the current gateway on loopback:

```bash
talon serve --host 127.0.0.1 --port 8080 --gateway --gateway-config "$TALON_CONFIG" \
  --proxy-config config/mcp-proxy.example.yaml
```

Verify the product marker and fleet:

```bash
curl -fsS -D- "$TALON_GATEWAY/health"
talon agents --url "$TALON_GATEWAY"
```

## 6. Start local application components

```bash
scripts/start-components.sh
```

Defaults:

```text
Copilot shim       127.0.0.1:8079
Zendesk adapter    127.0.0.1:8443 (plain HTTP behind tunnel TLS)
Release MCP server 127.0.0.1:8090
```

Stop only recorded child processes with:

```bash
scripts/stop-components.sh
```

## 7. Zendesk

1. Package and validate `integrations/zendesk-app` with ZCLI.
2. Expose only the adapter through an authenticated HTTPS tunnel.
3. Install as a private app.
4. Set `adapter_domain` to the hostname only.
5. Set `adapter_token` as the secure setting.
6. Open a synthetic ticket containing requester-authored public and agent/private comments.
7. Confirm the app chooses the newest public requester comment and inserts only the returned draft.

Local ZCLI rendering does not prove secure-setting replacement; the installed app is the required test.

## 8. Copilot CLI

```bash
scripts/reset-billing-fixture.sh
scripts/render-copilot-mcp-config.sh

export COPILOT_PROVIDER_TYPE=openai
export COPILOT_PROVIDER_BASE_URL=http://127.0.0.1:8079/v1/proxy/openai/v1
export COPILOT_PROVIDER_API_KEY="$TALON_CODING_ASSISTANT_KEY"
export COPILOT_MODEL=gpt-4o
export COPILOT_OFFLINE=true

cd cases/billing-demo
copilot --additional-mcp-config=@../../.state/copilot-mcp.json \
  --disable-builtin-mcps \
  --allow-tool=release-gateway \
  --deny-tool='shell(git push)'
```

The fixture has no real remote. The `git push` denial belongs to Copilot CLI. Do not present the Talon MCP release-denial scene while `docs/BLOCKERS.md` remains open.

## 9. n8n

```bash
install -d -m 0777 .state/n8n-output
source .env
docker compose -f integrations/n8n/compose.yaml up
```

Build the workflow in the pinned UI using `integrations/n8n/workflow-spec.md`. Do not invent JSON by hand. Export without credentials, clean-import into a fresh container, reconnect the credential, and rerun before committing an export.

## 10. Evidence gates

Before presenting a live claim, save and inspect Talon output:

```bash
talon audit list --session <session-id>
talon audit export --format signed-json --session <session-id> --output .state/<session>.signed.json
talon audit verify --file .state/<session>.signed.json
```

Never replace actual reason/provider/cost fields with presenter-authored success text.
