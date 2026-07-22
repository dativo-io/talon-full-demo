#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
ENV_FILE="$ROOT/.env"
RUN_ENV="$STATE/demo-run.env"
LATEST_ENV="$STATE/latest-zendesk-session.env"
MODE="${ZENDESK_DEMO_OUTPUT:-full}"

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

case "$MODE" in
  full|quiet) ;;
  *) die "ZENDESK_DEMO_OUTPUT must be full or quiet" ;;
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
transcript="$STATE/zendesk-$(date -u +%Y%m%dT%H%M%SZ).log"

run_case() {
  "$ROOT/scripts/preflight.sh"
  "$ROOT/scripts/stop-components.sh" >/dev/null 2>&1 || true
  "$ROOT/scripts/start-components.sh"
  # shellcheck disable=SC1090
  source "$RUN_ENV"

  local ticket_id session request response evidence http
  ticket_id="$(date -u +%Y%m%d%H%M%S)"
  session="zendesk-ticket-$ticket_id-$TALON_DEMO_RUN_ID"
  request="$STATE/$session.request.json"
  response="$STATE/$session.response.json"
  evidence="$STATE/$session.signed.json"

  jq -nc \
    --arg ticket_id "$ticket_id" \
    --arg subject 'Refund request awaiting review' \
    --arg name 'Anna Kowalska' \
    --arg email 'anna.kowalska@example.com' \
    --arg message 'Please confirm that you received my refund request. Refund account IBAN: DE89370400440532013000.' \
    '{ticket_id:$ticket_id,subject:$subject,requester:{name:$name,email:$email},message:$message}' >"$request"

  say "Sending one synthetic Zendesk ticket through the real adapter and Talon..."
  http="$(curl -sS -o "$response" -w '%{http_code}' -X POST \
    "http://${ZENDESK_ADAPTER_BIND:-127.0.0.1:8443}/v1/zendesk/draft" \
    -H "Authorization: Bearer $ZENDESK_ADAPTER_TOKEN" \
    -H 'Content-Type: application/json' \
    --data-binary @"$request")"

  [[ "$http" == "200" ]] || {
    echo "Zendesk adapter request failed with HTTP $http" >&2
    jq . "$response" >&2 2>/dev/null || cat "$response" >&2
    return 1
  }
  jq -e --arg s "$session" '.session_id == $s and (.draft | type == "string" and length > 0)' "$response" >/dev/null \
    || { echo 'Zendesk adapter response did not contain the expected session and draft' >&2; return 1; }

  talon audit export --format signed-json --session "$session" --output "$evidence" >/dev/null
  "$ROOT/scripts/assert-evidence.sh" \
    --session "$session" \
    --agent customer-support \
    --since "$TALON_RUN_START_RFC3339"

  jq -e 'any(.records[]; ((.classification.input_pii_redacted // false) == true or (.classification.pii_redacted // false) == true)
      and (.classification.pii_detected | index("email"))
      and (.classification.pii_detected | index("iban"))
      and .classification.input_tier == 2)' "$evidence" >/dev/null \
    || { echo 'Zendesk evidence did not prove email + IBAN redaction' >&2; return 1; }
  jq -e 'any(.records[]; .failover.role == "failed_attempt"
      and .failover.provider == "local-llama"
      and .failover.error_class == "connection_error")' "$evidence" >/dev/null \
    || { echo 'Zendesk evidence did not prove the local-provider failure' >&2; return 1; }
  jq -e 'any(.records[]; .failover.role == "fallback_decision"
      and .failover.provider == "openai"
      and any(.failover.skipped_candidates[]?; .provider == "openai-batch"
        and .filter == "agent_provider_allowlist"))' "$evidence" >/dev/null \
    || { echo 'Zendesk evidence did not prove policy-valid fallback to OpenAI' >&2; return 1; }
  jq -e 'any(.records[]; .orchestration.client == "zendesk-support-full-demo")' "$evidence" >/dev/null \
    || { echo 'Zendesk evidence did not preserve the adapter client attribution' >&2; return 1; }

  umask 077
  cat >"$LATEST_ENV" <<EOF
export TALON_ZENDESK_SESSION_ID=$session
export TALON_ZENDESK_EVIDENCE_FILE=$evidence
export TALON_ZENDESK_REQUEST_FILE=$request
export TALON_ZENDESK_RESPONSE_FILE=$response
export TALON_ZENDESK_TRANSCRIPT=$transcript
EOF
  chmod 0600 "$LATEST_ENV"

  say
  say "REAL ZENDESK ADAPTER CASE PASSED"
  say "  Synthetic ticket produced a governed reply draft"
  say "  Session: $session"
  say "  Evidence: $evidence"
  if [[ "$MODE" == "full" ]]; then
    say
    jq -r '.draft' "$response"
  fi
}

if [[ "$MODE" == "quiet" ]]; then
  say "Running the real Zendesk adapter path through Talon..."
  run_case >"$transcript" 2>&1 || {
    cat "$transcript" >&2
    die "real Zendesk adapter case failed; full output is in $transcript"
  }
  # The complete pass is in the transcript; keep the buyer terminal concise.
  # shellcheck disable=SC1090
  source "$LATEST_ENV"
  say
  say "REAL ZENDESK ADAPTER CASE PASSED"
  say "  Real adapter request completed; Talon verification passed"
  say "  Session: $TALON_ZENDESK_SESSION_ID"
  say "  Full transcript retained at: $transcript"
else
  run_case 2>&1 | tee "$transcript"
fi
