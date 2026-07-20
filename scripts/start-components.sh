#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/.env" ]] || { echo "missing $ROOT/.env; run make env" >&2; exit 1; }
# shellcheck disable=SC1091
source "$ROOT/.env"
make -C "$ROOT" build
mkdir -p "$ROOT/.state/logs"

start() {
  local name="$1"
  local executable="$2"
  shift 2
  local pidfile="$ROOT/.state/$name.pid"
  if [[ -f "$pidfile" ]]; then
    local old_pid old_executable
    IFS=$'\t' read -r old_pid old_executable < "$pidfile" || true
    if [[ "$old_pid" =~ ^[0-9]+$ ]] && kill -0 "$old_pid" 2>/dev/null; then
      echo "$name already appears to be running as pid $old_pid; run scripts/stop-components.sh" >&2
      exit 1
    fi
    rm -f "$pidfile"
  fi
  "$@" >"$ROOT/.state/logs/$name.log" 2>&1 &
  local pid=$!
  printf '%s\t%s\n' "$pid" "$executable" > "$pidfile"
}

start release-mcp "$ROOT/bin/release-mcp-server" \
  env RELEASE_MCP_BIND="${RELEASE_MCP_BIND:-127.0.0.1:8090}" \
      RELEASE_MCP_RECEIPTS="${RELEASE_MCP_RECEIPTS:-$ROOT/.state/release-mcp-receipts.jsonl}" \
      "$ROOT/bin/release-mcp-server"
start copilot-shim "$ROOT/bin/copilot-session-shim" \
  env TALON_GATEWAY="$TALON_GATEWAY" \
      TALON_COPILOT_SESSION_ID="$TALON_COPILOT_SESSION_ID" \
      COPILOT_SHIM_BIND="${COPILOT_SHIM_BIND:-127.0.0.1:8079}" \
      "$ROOT/bin/copilot-session-shim"
start zendesk-adapter "$ROOT/bin/zendesk-adapter" \
  env ZENDESK_ADAPTER_TOKEN="$ZENDESK_ADAPTER_TOKEN" \
      TALON_GATEWAY="$TALON_GATEWAY" \
      TALON_CUSTOMER_SUPPORT_KEY="$TALON_CUSTOMER_SUPPORT_KEY" \
      TALON_CUSTOMER_SUPPORT_PROVIDER="${TALON_CUSTOMER_SUPPORT_PROVIDER:-local-llama}" \
      TALON_CUSTOMER_SUPPORT_MODEL="${TALON_CUSTOMER_SUPPORT_MODEL:-llama3.2:1b}" \
      ZENDESK_ADAPTER_BIND="${ZENDESK_ADAPTER_BIND:-127.0.0.1:8443}" \
      "$ROOT/bin/zendesk-adapter"

echo 'Started local integration components; start Talon and n8n separately.'
