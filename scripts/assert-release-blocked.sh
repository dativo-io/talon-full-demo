#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RECEIPTS="${RELEASE_MCP_RECEIPTS:-$ROOT/.state/release-mcp-receipts.jsonl}"
[[ -s "$RECEIPTS" ]] || { echo "missing or empty receipts file: $RECEIPTS" >&2; exit 1; }

jq -e 'select(.tool=="release_status" and .synthetic==true)' "$RECEIPTS" >/dev/null
jq -e 'select(.tool=="release_prepare" and .synthetic==true)' "$RECEIPTS" >/dev/null
if jq -e 'select(.tool=="release_publish")' "$RECEIPTS" >/dev/null; then
  echo 'release_publish reached the synthetic upstream; proof invalid' >&2
  exit 1
fi
echo 'release_publish absent from synthetic upstream receipts'
