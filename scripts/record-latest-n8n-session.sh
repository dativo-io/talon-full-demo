#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_ENV="$ROOT/.state/demo-run.env"
[[ -f "$RUN_ENV" ]] || { echo "missing $RUN_ENV" >&2; exit 1; }
# shellcheck disable=SC1090
source "$RUN_ENV"
umask 077

case "${1:-}" in
  quarterly)
    [[ -n "${TALON_N8N_SESSION_ID:-}" ]] || { echo 'TALON_N8N_SESSION_ID is empty' >&2; exit 1; }
    cat >"$ROOT/.state/latest-n8n-session.env" <<EOF_QUARTERLY
export TALON_N8N_PRESENTED_SESSION_ID=$TALON_N8N_SESSION_ID
EOF_QUARTERLY
    ;;
  vendor-review)
    [[ -n "${TALON_N8N_VENDOR_REVIEW_SESSION_ID:-}" ]] || { echo 'TALON_N8N_VENDOR_REVIEW_SESSION_ID is empty' >&2; exit 1; }
    cat >"$ROOT/.state/latest-n8n-vendor-review-session.env" <<EOF_VENDOR
export TALON_N8N_VENDOR_REVIEW_PRESENTED_SESSION_ID=$TALON_N8N_VENDOR_REVIEW_SESSION_ID
EOF_VENDOR
    ;;
  *)
    echo 'usage: scripts/record-latest-n8n-session.sh quarterly|vendor-review' >&2
    exit 2
    ;;
esac
