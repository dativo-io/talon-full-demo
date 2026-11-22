#!/usr/bin/env bash
# Verify that the executable matches the Talon source used for THIS run.
# No long-lived SHA pin: update the source checkout to origin/main to upgrade.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="${HR_DEMO_TALON_SOURCE_DIR:-$ROOT/.state/talon-source}"
BIN="${1:-${HR_DEMO_TALON_BIN:-}}"
if [[ -z "$BIN" || ! -f "$BIN" || ! -x "$BIN" ]]; then
  echo "FAIL: HR_DEMO_TALON_BIN must point to an executable Linux Talon binary." >&2
  echo "Run: bash ../../scripts/prepare-people-analytics-talon.sh (from the case directory)" >&2
  exit 1
fi
command -v go >/dev/null || { echo "FAIL: Go is needed for build provenance inspection" >&2; exit 1; }
if [[ ! -d "$SOURCE/.git" ]]; then
  echo "FAIL: Talon source checkout not found: $SOURCE" >&2
  echo "Run the prepare helper or set HR_DEMO_TALON_SOURCE_DIR to the checkout used for this build." >&2
  exit 1
fi
EXPECTED="$(git -C "$SOURCE" rev-parse HEAD)"
VCS="$(go version -m "$BIN" 2>/dev/null | sed -n 's/^[[:space:]]*build[[:space:]]*vcs.revision=//p' | head -1 || true)"
if [[ -z "$VCS" || "$VCS" != "$EXPECTED" ]]; then
  echo "FAIL: Talon binary does not match the checked-out Talon source." >&2
  echo "Source checkout: $EXPECTED" >&2
  echo "Binary source:   ${VCS:-unknown}" >&2
  echo "Run the prepare helper to build current main; do not remove read_only from policy." >&2
  exit 1
fi
echo "PASS: Talon source and binary agree: $EXPECTED (resolved main at build time)"
"$BIN" version
