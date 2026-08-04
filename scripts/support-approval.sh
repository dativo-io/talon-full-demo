#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
ENV_FILE="$STATE/n8n-support-resolution-approval.env"
ACTION="${1:-status}"

[[ -f "$ENV_FILE" ]] || {
  echo 'ERROR: no pending support-resolution approval; start make demo-n8n-support-resolution-buyer first' >&2
  exit 1
}
# shellcheck disable=SC1090
source "$ENV_FILE"

: "${TALON_SUPPORT_APPROVAL_URL:?missing approval URL}"
: "${TALON_SUPPORT_APPROVAL_ID:?missing approval ID}"

show_request() {
  curl --fail --silent --show-error \
    "$TALON_SUPPORT_APPROVAL_URL/requests/$TALON_SUPPORT_APPROVAL_ID" | jq .
}

decide() {
  local verb="$1"
  echo
  echo 'HUMAN APPROVAL DECISION'
  echo '────────────────────────────────────────'
  show_request | jq -r '
    .request
    | "Ticket           " + .ticket_id,
      "Requested action " + .requested_action,
      "Amount           EUR " + (.amount_eur|tostring),
      "Talon session    " + .session_id,
      "Refund           not executed"
  '
  echo '────────────────────────────────────────'
  curl --fail --silent --show-error \
    -H 'Accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '{"operator":"demo-operator"}' \
    "$TALON_SUPPORT_APPROVAL_URL/approval/$TALON_SUPPORT_APPROVAL_ID/$verb" | jq .
}

case "$ACTION" in
  approve) decide approve ;;
  reject) decide reject ;;
  status) show_request ;;
  open)
    echo "$TALON_SUPPORT_APPROVAL_PAGE"
    ;;
  *)
    echo 'usage: scripts/support-approval.sh approve|reject|status|open' >&2
    exit 2
    ;;
esac
