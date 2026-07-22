#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
ENV_FILE="$ROOT/.env"
RUN_ENV="$STATE/demo-run.env"
LATEST_ENV="$STATE/latest-support-session.env"
MODE="${SUPPORT_DEMO_OUTPUT:-full}"

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

case "$MODE" in
  full|quiet) ;;
  *) die "SUPPORT_DEMO_OUTPUT must be full or quiet" ;;
esac

for cmd in talon jq curl; do
  command -v "$cmd" >/dev/null 2>&1 || die "missing command: $cmd"
done
[[ -f "$ENV_FILE" ]] || die "missing .env; run make real-prepare"
# shellcheck disable=SC1090
source "$ENV_FILE"

curl --fail --silent --max-time 2 "$TALON_GATEWAY/health" >/dev/null \
  || die "Talon gateway is not running; run make real-start"

rm -f "$LATEST_ENV"

# Give every presentation attempt a fresh session and restart the local demo
# components under that run identity. The support call itself goes directly to
# Talon, but using the same run lifecycle keeps all application cases isolated.
if [[ "$MODE" == "quiet" ]]; then
  say "Running one real customer-support request through Talon..."
  transcript="$STATE/support-$(date -u +%Y%m%dT%H%M%SZ).log"
  {
    "$ROOT/scripts/preflight.sh"
    "$ROOT/scripts/stop-components.sh" >/dev/null 2>&1 || true
    "$ROOT/scripts/start-components.sh"
    bash "$ROOT/scripts/real-stack.sh" smoke
  } >"$transcript" 2>&1 || {
    cat "$transcript" >&2
    die "real support case failed; full output is in $transcript"
  }
else
  "$ROOT/scripts/preflight.sh"
  "$ROOT/scripts/stop-components.sh" >/dev/null 2>&1 || true
  "$ROOT/scripts/start-components.sh"
  transcript="$STATE/support-$(date -u +%Y%m%dT%H%M%SZ).log"
  bash "$ROOT/scripts/real-stack.sh" smoke 2>&1 | tee "$transcript"
fi

[[ -f "$RUN_ENV" ]] || die "support run did not create $RUN_ENV"
# shellcheck disable=SC1090
source "$RUN_ENV"
SESSION="real-support-$TALON_DEMO_RUN_ID"
EVIDENCE="$STATE/$SESSION.signed.json"
REQUEST="$STATE/$SESSION.request.json"
RESPONSE="$STATE/$SESSION.response.json"

[[ -s "$EVIDENCE" ]] || die "missing signed evidence for $SESSION"
[[ -s "$REQUEST" ]] || die "missing request artifact for $SESSION"
[[ -s "$RESPONSE" ]] || die "missing response artifact for $SESSION"

umask 077
cat >"$LATEST_ENV" <<EOF
export TALON_SUPPORT_SESSION_ID=$SESSION
export TALON_SUPPORT_EVIDENCE_FILE=$EVIDENCE
export TALON_SUPPORT_REQUEST_FILE=$REQUEST
export TALON_SUPPORT_RESPONSE_FILE=$RESPONSE
export TALON_SUPPORT_TRANSCRIPT=$transcript
EOF
chmod 0600 "$LATEST_ENV"

if [[ "$MODE" == "quiet" ]]; then
  say
  say "REAL SUPPORT CASE PASSED"
  say "  Real provider request completed; Talon verification passed"
  say "  Session: $SESSION"
  say "  Full transcript retained at: $transcript"
fi
