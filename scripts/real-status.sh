#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
ENV_FILE="$ROOT/.env"
READY_FILE="$STATE/real-demo-ready.env"
status_rc=0

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1091
  source "$ENV_FILE"
else
  printf '✗ %-18s %s\n' "Demo environment" ".env is missing; run make real-prepare"
  status_rc=1
fi

check_url() {
  local label="$1" url="$2"
  if curl --fail --silent --max-time 1 "$url" >/dev/null 2>&1; then
    printf '✓ %-18s %s\n' "$label" "$url"
  else
    printf '✗ %-18s %s\n' "$label" "$url"
    status_rc=1
  fi
}

# Check every required service directly. Do not delegate to real-demo.sh: status
# must work in a fresh shell after provider keys have already been seeded into
# Talon's vault, even when OPENAI_API_KEY and ANTHROPIC_API_KEY are not exported.
check_url "Talon gateway" "${TALON_GATEWAY:-http://127.0.0.1:8080}/health"
check_url "Talon MCP proxy" "${TALON_MCP_GATEWAY:-http://127.0.0.1:8081}/health"
check_url "Copilot shim" "http://${COPILOT_SHIM_BIND:-127.0.0.1:8079}/health"
check_url "Zendesk adapter" "http://${ZENDESK_ADAPTER_BIND:-127.0.0.1:8443}/health"
check_url "Release MCP" "http://${RELEASE_MCP_BIND:-127.0.0.1:8090}/health"

copilot=""
if [[ -x "$HOME/.local/bin/copilot" ]]; then
  copilot="$HOME/.local/bin/copilot"
elif command -v copilot >/dev/null 2>&1; then
  copilot="$(command -v copilot)"
fi

if [[ -n "$copilot" ]]; then
  version="$($copilot --version 2>&1 | head -1 || true)"
  printf '✓ %-18s %s (%s)\n' "Copilot CLI" "$copilot" "${version:-version unavailable}"
else
  printf '– %-18s %s\n' "Copilot CLI" "not installed; run make copilot-install"
fi

if [[ -f "$READY_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$READY_FILE"
  if [[ "${REAL_DEMO_ANTHROPIC_READY:-0}" == 1 ]]; then
    printf '✓ %-18s %s\n' "Anthropic key" "seeded"
  else
    printf '– %-18s %s\n' "Anthropic key" "not configured; OpenAI paths remain available"
  fi
else
  printf '– %-18s %s\n' "Preparation" "metadata missing"
fi

exit "$status_rc"
