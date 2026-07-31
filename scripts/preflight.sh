#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/.env" ]] || { echo "missing $ROOT/.env; run make env" >&2; exit 1; }
# shellcheck disable=SC1091
source "$ROOT/.env"

for cmd in go node npm jq curl openssl python3 git talon; do
  command -v "$cmd" >/dev/null || { echo "missing command: $cmd" >&2; exit 1; }
done
for var in TALON_GATEWAY TALON_MCP_GATEWAY TALON_COPILOT_SESSION_ID TALON_N8N_SESSION_ID \
           TALON_N8N_VENDOR_REVIEW_SESSION_ID TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID \
           TALON_CUSTOMER_SUPPORT_KEY TALON_CODING_ASSISTANT_KEY TALON_DOCUMENT_SUMMARY_KEY \
           TALON_VENDOR_CONTRACT_REVIEW_KEY ZENDESK_ADAPTER_TOKEN N8N_ENCRYPTION_KEY; do
  [[ -n "${!var:-}" ]] || { echo "$var is empty" >&2; exit 1; }
done
[[ -f "$TALON_CONFIG" ]] || { echo "missing generated Talon config: $TALON_CONFIG" >&2; exit 1; }

# Mint the per-run identity FIRST (before local components start), so the shim,
# adapter, and rendered Copilot config all pick up per-run sessions.
"$ROOT/scripts/new-demo-run.sh"
# shellcheck disable=SC1091
source "$ROOT/.state/demo-run.env"

# Talon control plane: BOTH processes must be up. The gateway serves LLM traffic
# on :8080; the MCP proxy serves /mcp/proxy on :8081 (TALON_MCP_GATEWAY). A prior
# version checked only :8080, so preflight could pass with the MCP proxy down.
curl --fail --silent --show-error --max-time 5 "$TALON_GATEWAY/health" >/dev/null
curl --fail --silent --show-error --max-time 5 "$TALON_MCP_GATEWAY/health" >/dev/null

# A generic /health does not prove that agent-key auth and /mcp/proxy routing
# actually work. Do a real authenticated MCP initialize with the coding-assistant
# bearer (no admin key): it must be answered locally by talon-mcp-proxy.
mcp_init="$(curl --fail --silent --show-error --max-time 5 "$TALON_MCP_GATEWAY/mcp/proxy" \
  -H "Authorization: Bearer $TALON_CODING_ASSISTANT_KEY" \
  -H "X-Talon-Session-ID: $TALON_COPILOT_SESSION_ID" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"preflight","version":"0.0.1"}}}' 2>/dev/null || true)"
echo "$mcp_init" | jq -e '.result.serverInfo.name == "talon-mcp-proxy"' >/dev/null 2>&1 \
  || { echo "MCP proxy at $TALON_MCP_GATEWAY did not answer an authenticated initialize (agent-key auth / routing broken)" >&2; exit 1; }

# Local components (release MCP upstream, adapter) are verified here when already
# running; their authoritative readiness gate is scripts/start-components.sh.
# The Copilot shim has no local /health (every path proxies to Talon) — it is
# gated at the connection level by start-components.
curl --fail --silent --show-error --max-time 5 "http://${ZENDESK_ADAPTER_BIND:-127.0.0.1:8443}/health" >/dev/null 2>&1 \
  || echo "note: Zendesk adapter not up yet (start-components will gate it)" >&2
curl --fail --silent --show-error --max-time 5 "http://${RELEASE_MCP_BIND:-127.0.0.1:8090}/health" >/dev/null 2>&1 \
  || echo "note: release MCP upstream not up yet (start-components will gate it)" >&2

if curl --fail --silent --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo 'Ollama must be stopped for the fallback demonstration' >&2
  exit 1
fi

rm -rf "$ROOT/.state/n8n-output" \
       "$ROOT/.state/n8n-vendor-review-output" \
       "$ROOT/.state/n8n-support-resolution-output"
# 0777 ONLY because the pinned n8n container writes to these loopback bind mounts
# as its own non-root UID. They are throwaway demo scratch dirs, NOT a deployment
# pattern — a real deployment matches the container UID or uses named volumes.
install -d -m 0777 \
  "$ROOT/.state/n8n-output" \
  "$ROOT/.state/n8n-vendor-review-output" \
  "$ROOT/.state/n8n-support-resolution-output"
install -d -m 0700 "$ROOT/.state"
: > "$ROOT/.state/release-mcp-receipts.jsonl"
chmod 0600 "$ROOT/.state/release-mcp-receipts.jsonl"
# The per-run nonce is minted by scripts/new-demo-run.sh (above) into
# .state/run-nonce and .state/demo-run.env; the demo passes {"run_nonce": "..."}
# in every allowed release tool call and scripts/assert-release-blocked.sh only
# accepts receipts carrying it, so stale receipts cannot fake a denial run.

if (cd "$ROOT/cases/billing-demo" && npm test >/dev/null 2>&1); then
  echo 'billing fixture unexpectedly passes; reset it before the demo' >&2
  exit 1
fi

echo 'Preflight passed'
