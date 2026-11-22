#!/usr/bin/env bash
# Reject an old stable/RC binary before it silently rejects the HR read_only MCP schema.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED="$(tr -d '[:space:]' < "$ROOT/cases/people-analytics-copilot/TALON_GOVERNED_MCP_COMMIT")"
BIN="${1:-${HR_DEMO_TALON_BIN:-}}"
if [[ -z "$BIN" || ! -f "$BIN" || ! -x "$BIN" ]]; then
  echo "FAIL: HR_DEMO_TALON_BIN must point to an existing executable Linux Talon binary." >&2
  echo "Run: bash scripts/prepare-people-analytics-talon.sh" >&2
  exit 1
fi
if ! command -v go >/dev/null; then
  echo "FAIL: Go is required to inspect this source-built candidate's VCS provenance." >&2
  exit 1
fi
VCS="$(go version -m "$BIN" | sed -n 's/^[[:space:]]*build[[:space:]]*vcs.revision=//p' | head -1)"
if [[ "$VCS" != "$EXPECTED" ]]; then
  echo "FAIL: Talon binary source does not match the governed-MCP acceptance pin." >&2
  echo "Expected: $EXPECTED" >&2
  echo "Found: ${VCS:-no embedded VCS revision; installed release/old candidate?}" >&2
  echo "The four HR actions use read_only: true, supported by this exact source." >&2
  echo "Run: bash scripts/prepare-people-analytics-talon.sh" >&2
  exit 1
fi
echo "PASS: correct source-built Talon binary: $EXPECTED"
"$BIN" version
