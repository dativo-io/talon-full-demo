#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

set +e
bash "$ROOT/scripts/real-demo.sh" status
status_rc=$?
set -e

if [[ -f "$ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.env"
fi

shim_bind="${COPILOT_SHIM_BIND:-127.0.0.1:8079}"
shim_code="$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 1 "http://$shim_bind/health" 2>/dev/null || true)"
if [[ -n "$shim_code" && "$shim_code" != "000" ]]; then
  printf '✓ %-18s %s\n' "Copilot shim" "http://$shim_bind"
else
  printf '✗ %-18s %s\n' "Copilot shim" "http://$shim_bind"
  status_rc=1
fi

copilot=""
if command -v copilot >/dev/null 2>&1; then
  copilot="$(command -v copilot)"
elif [[ -x "$HOME/.local/bin/copilot" ]]; then
  copilot="$HOME/.local/bin/copilot"
fi

if [[ -n "$copilot" ]]; then
  printf '✓ %-18s %s (%s)\n' "Copilot CLI" "$copilot" "$($copilot --version 2>&1 | head -1)"
else
  printf '– %-18s %s\n' "Copilot CLI" "not installed; run make copilot-install"
fi

exit "$status_rc"
