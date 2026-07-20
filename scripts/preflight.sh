#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/.env" ]] || { echo "missing $ROOT/.env; run make env" >&2; exit 1; }
# shellcheck disable=SC1091
source "$ROOT/.env"

for cmd in go node npm jq curl openssl python3 git talon; do
  command -v "$cmd" >/dev/null || { echo "missing command: $cmd" >&2; exit 1; }
done
for var in TALON_GATEWAY TALON_CUSTOMER_SUPPORT_KEY TALON_CODING_ASSISTANT_KEY TALON_DOCUMENT_SUMMARY_KEY ZENDESK_ADAPTER_TOKEN N8N_ENCRYPTION_KEY; do
  [[ -n "${!var:-}" ]] || { echo "$var is empty" >&2; exit 1; }
done
[[ -f "$TALON_CONFIG" ]] || { echo "missing generated Talon config: $TALON_CONFIG" >&2; exit 1; }

curl --fail --silent --show-error --max-time 5 "$TALON_GATEWAY/health" >/dev/null
curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8443/health >/dev/null
curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8090/health >/dev/null
if curl --fail --silent --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo 'Ollama must be stopped for the fallback demonstration' >&2
  exit 1
fi

rm -rf "$ROOT/.state/n8n-output"
install -d -m 0777 "$ROOT/.state/n8n-output"
install -d -m 0700 "$ROOT/.state"
: > "$ROOT/.state/release-mcp-receipts.jsonl"
chmod 0600 "$ROOT/.state/release-mcp-receipts.jsonl"

if (cd "$ROOT/cases/billing-demo" && npm test >/dev/null 2>&1); then
  echo 'billing fixture unexpectedly passes; reset it before the demo' >&2
  exit 1
fi

echo 'Preflight passed'
