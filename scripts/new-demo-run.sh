#!/usr/bin/env bash
set -euo pipefail

# Mint one per-rehearsal demo-run identity so a fresh run cannot be satisfied by
# a previous run's Talon evidence, session, or budget state. Everything that
# carries a session or correlation derives from a single TALON_DEMO_RUN_ID.
#
# Writes .state/demo-run.env (mode 0600). Consumers (start-components.sh,
# render-copilot-mcp-config.sh, the Zendesk adapter, assemble-n8n-report.sh,
# assert-evidence.sh) source or read these values. preflight.sh calls this at
# the start of every run; run it before starting local components so the shim
# and adapter pick up the per-run sessions.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
install -d -m 0700 "$ROOT/.state"

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$(openssl rand -hex 3)"
START_RFC3339="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
NONCE="$(openssl rand -hex 16)"

# The release nonce also lives in .state/run-nonce for assert-release-blocked.sh.
printf '%s' "$NONCE" > "$ROOT/.state/run-nonce"
chmod 0600 "$ROOT/.state/run-nonce"

OUT="$ROOT/.state/demo-run.env"
umask 077
cat > "$OUT" <<EOF_RUN
# Generated per demo run by scripts/new-demo-run.sh — do not commit.
export TALON_DEMO_RUN_ID=$RUN_ID
export TALON_RUN_START_RFC3339=$START_RFC3339
export TALON_COPILOT_SESSION_ID=copilot-$RUN_ID
export TALON_N8N_SESSION_ID=n8n-$RUN_ID
export TALON_N8N_VENDOR_REVIEW_SESSION_ID=n8n-vendor-review-$RUN_ID
export RELEASE_RUN_NONCE=$NONCE
EOF_RUN
chmod 0600 "$OUT"

echo "Demo run id: $RUN_ID"
echo "  copilot session:       copilot-$RUN_ID"
echo "  n8n session:           n8n-$RUN_ID"
echo "  vendor-review session: n8n-vendor-review-$RUN_ID"
echo "  run nonce:             $NONCE"
echo "  values written to $OUT (source it, or let the demo scripts read it)"
