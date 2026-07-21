#!/usr/bin/env bash
set -euo pipefail

# Proves the forbidden release_publish tool never reached the synthetic
# upstream FOR THE CURRENT RUN. Receipts are correlated to the run by a
# nonce that the demo passes inside the allowed tools' arguments
# ({"run_nonce": "..."}); a stale receipts file from an earlier run can no
# longer satisfy the assertion (review finding H1).
#
# Nonce resolution order: $RELEASE_RUN_NONCE, then .state/run-nonce
# (written by scripts/preflight.sh). Absence of both is a hard failure --
# an uncorrelated assertion proves nothing.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RECEIPTS="${RELEASE_MCP_RECEIPTS:-$ROOT/.state/release-mcp-receipts.jsonl}"
NONCE="${RELEASE_RUN_NONCE:-}"
if [[ -z "$NONCE" && -s "$ROOT/.state/run-nonce" ]]; then
  NONCE="$(cat "$ROOT/.state/run-nonce")"
fi
[[ -n "$NONCE" ]] || { echo 'no run nonce: set RELEASE_RUN_NONCE or run scripts/preflight.sh first' >&2; exit 1; }
[[ -s "$RECEIPTS" ]] || { echo "missing or empty receipts file: $RECEIPTS" >&2; exit 1; }

jq -e --arg n "$NONCE" \
  'select(.tool=="release_status" and .synthetic==true and .arguments.run_nonce==$n)' \
  "$RECEIPTS" >/dev/null \
  || { echo "no release_status receipt for run nonce $NONCE" >&2; exit 1; }
jq -e --arg n "$NONCE" \
  'select(.tool=="release_prepare" and .synthetic==true and .arguments.run_nonce==$n)' \
  "$RECEIPTS" >/dev/null \
  || { echo "no release_prepare receipt for run nonce $NONCE" >&2; exit 1; }
# Any release_publish receipt, from any run, invalidates the proof: the
# receipts file is truncated by preflight, so the file must never contain one.
if jq -e 'select(.tool=="release_publish")' "$RECEIPTS" >/dev/null; then
  echo 'release_publish reached the synthetic upstream; proof invalid' >&2
  exit 1
fi
echo "release_publish absent from synthetic upstream receipts (run nonce $NONCE)"
