#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
ENV_FILE="$ROOT/.env"
LATEST_ENV="$STATE/latest-support-session.env"
MODE="${1:-buyer}"

usage() {
  cat <<'EOF'
Usage: bash scripts/present-support.sh [buyer|technical|all]

buyer      Show a concise business receipt for the latest real support run.
technical  Show the Talon session, PII decision, fallback path, cost, and signatures.
all        Show buyer view followed by technical proof.
EOF
}

case "$MODE" in
  buyer|technical|all) ;;
  -h|--help|help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

for cmd in talon jq; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: missing command: $cmd" >&2; exit 1; }
done
[[ -f "$ENV_FILE" ]] || { echo 'ERROR: missing .env; run make real-prepare' >&2; exit 1; }
[[ -f "$LATEST_ENV" ]] || { echo 'ERROR: no completed support run; run make demo-support-buyer or make demo-support-tech' >&2; exit 1; }
# shellcheck disable=SC1090
source "$ENV_FILE"
# shellcheck disable=SC1090
source "$LATEST_ENV"

SESSION="${TALON_SUPPORT_SESSION_ID:-}"
[[ -n "$SESSION" ]] || { echo 'ERROR: TALON_SUPPORT_SESSION_ID is empty' >&2; exit 1; }
EVIDENCE_FILE="${TALON_PRESENT_EVIDENCE_FILE:-$STATE/$SESSION.signed.json}"
VERIFY_FILE="$STATE/$SESSION.verify.txt"
REQUEST_FILE="${TALON_SUPPORT_REQUEST_FILE:-$STATE/$SESSION.request.json}"
RESPONSE_FILE="${TALON_SUPPORT_RESPONSE_FILE:-$STATE/$SESSION.response.json}"

# Recreate the export from Talon's evidence store. Presenter output is never
# trusted as proof and an earlier export cannot satisfy a later presentation.
talon audit export --format signed-json --session "$SESSION" --output "$EVIDENCE_FILE" >/dev/null
talon audit verify --file "$EVIDENCE_FILE" >"$VERIFY_FILE"
for expected in 'Invalid records: 0' 'Missing signature: 0' 'Could not parse: 0' 'Unsupported: 0'; do
  grep -Fq "$expected" "$VERIFY_FILE" || {
    echo "ERROR: evidence verification failed; missing '$expected'" >&2
    cat "$VERIFY_FILE" >&2
    exit 1
  }
done

TOTAL="$(jq '.records | length' "$EVIDENCE_FILE")"
VALID="$(awk -F': ' '/^Valid records:/ {print $2}' "$VERIFY_FILE")"
INVALID="$(awk -F': ' '/^Invalid records:/ {print $2}' "$VERIFY_FILE")"
AGENT="$(jq -r '[.records[].agent_id] | unique | if length == 1 then .[0] else join(", ") end' "$EVIDENCE_FILE")"
MODELS="$(jq -r '[.records[].execution.model_used? | select(type == "string" and length > 0)] | unique | join(", ")' "$EVIDENCE_FILE")"
PII="$(jq -r '[.records[].classification.pii_detected[]?] | unique | sort | join(", ")' "$EVIDENCE_FILE")"
COST="$(jq -r '[.records[].execution.cost // 0] | add // 0' "$EVIDENCE_FILE")"
COST_FMT="$(printf '%.6f' "$COST")"
ALLOWED="$(jq '[.records[] | select(.policy_decision.allowed == true)] | length' "$EVIDENCE_FILE")"
DENIED="$(jq '[.records[] | select(.policy_decision.allowed == false)] | length' "$EVIDENCE_FILE")"
FAILED_PROVIDER="$(jq -r '[.records[] | select(.failover.role == "failed_attempt") | .failover.provider] | unique | join(", ")' "$EVIDENCE_FILE")"
SELECTED_PROVIDER="$(jq -r '[.records[] | select(.failover.role == "fallback_decision") | .failover.provider] | unique | join(", ")' "$EVIDENCE_FILE")"
SKIPPED_PROVIDERS="$(jq -r '[.records[].failover.skipped_candidates[]?.provider] | unique | join(", ")' "$EVIDENCE_FILE")"
REDACTED_RECORDS="$(jq '[.records[] | select((.classification.input_pii_redacted // false) == true or (.classification.pii_redacted // false) == true)] | length' "$EVIDENCE_FILE")"

[[ "$TOTAL" -ge 1 ]] || { echo "ERROR: no evidence records for $SESSION" >&2; exit 1; }
[[ "$VALID" == "$TOTAL" && "$INVALID" == "0" ]] || { echo 'ERROR: not every support record verified' >&2; exit 1; }
[[ "$AGENT" == "customer-support" ]] || { echo "ERROR: expected customer-support evidence, found $AGENT" >&2; exit 1; }
jq -e --arg s "$SESSION" 'all(.records[]; .session_id == $s)' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: exported records do not all belong to the support session' >&2; exit 1; }
jq -e 'any(.records[]; ((.classification.input_pii_redacted // false) == true or (.classification.pii_redacted // false) == true)
    and (.classification.pii_detected | index("email"))
    and (.classification.pii_detected | index("iban"))
    and .classification.input_tier == 2)' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: evidence does not prove email + IBAN redaction' >&2; exit 1; }
jq -e 'any(.records[]; .failover.role == "failed_attempt"
    and .failover.provider == "local-llama"
    and .failover.error_class == "connection_error")' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: evidence does not prove the local provider failure' >&2; exit 1; }
jq -e 'any(.records[]; .failover.role == "fallback_decision"
    and .failover.provider == "openai"
    and any(.failover.skipped_candidates[]?; .provider == "openai-batch"
      and .filter == "agent_provider_allowlist"))' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: evidence does not prove policy-valid fallback to OpenAI' >&2; exit 1; }
[[ -s "$REQUEST_FILE" && -s "$RESPONSE_FILE" ]] || { echo 'ERROR: support request/response artifacts are missing' >&2; exit 1; }
jq -e '(.choices[0].message.content // .content[0].text // "") | type == "string" and length > 0' "$RESPONSE_FILE" >/dev/null \
  || { echo 'ERROR: support response contains no draft' >&2; exit 1; }

show_buyer() {
  cat <<EOF

TALON VERIFIED AI USE CASE
────────────────────────────────────────────────────────────
Use case          Customer support assistant
Operational ID    $AGENT
Business outcome  Customer reply drafted
Data handling     Email + IBAN redacted before provider access
Reliability       ${FAILED_PROVIDER:-local model} unavailable; ${SELECTED_PROVIDER:-approved fallback} selected
Policy boundary   ${SKIPPED_PROVIDERS:-disallowed fallback} was not eligible
Model path        ${MODELS:-not recorded} through Talon
Session cost      \$$COST_FMT
Evidence          $VALID valid / $INVALID invalid records
Result            VERIFIED
────────────────────────────────────────────────────────────
What this means: the support use case kept working when its preferred provider
failed, without bypassing data policy or the approved provider list.
EOF
}

show_technical() {
  cat <<EOF

TALON TECHNICAL PROOF — CUSTOMER SUPPORT
────────────────────────────────────────────────────────────
Session:       $SESSION
Agent:         $AGENT
Decisions:     $ALLOWED allowed / $DENIED denied
PII:           $PII
Redacted:      $REDACTED_RECORDS evidence record(s)
Failed route:  ${FAILED_PROVIDER:-not recorded}
Selected:      ${SELECTED_PROVIDER:-not recorded}
Skipped:       ${SKIPPED_PROVIDERS:-none}
Evidence:      $EVIDENCE_FILE
Request:       $REQUEST_FILE
Response:      $RESPONSE_FILE
EOF

  echo
  talon audit list --session "$SESSION"

  cat <<'EOF'

Evidence timeline (oldest first)
TIME                              ROLE / SURFACE             PROVIDER / MODEL       DECISION  COST
EOF
  jq -r '
    .records
    | sort_by(.timestamp)
    | .[]
    | [
        .timestamp,
        (if (.failover.role // "") != "" then .failover.role else .invocation_type end),
        (if (.failover.provider // "") != "" then .failover.provider else (.execution.model_used // "-") end),
        (if .policy_decision.allowed then "allow" else "deny" end),
        ((.execution.cost // 0) | tostring)
      ]
    | @tsv
  ' "$EVIDENCE_FILE"

  cat <<EOF

Policy-valid reliability path
  1. Preferred local provider failed with a connection error: $FAILED_PROVIDER
  2. Disallowed candidate was skipped: $SKIPPED_PROVIDERS
  3. Allowed fallback was selected: $SELECTED_PROVIDER

Data boundary
  Detected: $PII
  Evidence proves email + IBAN were redacted before provider access.

Cryptographic verification
EOF
  sed -n '/^Total records:/,/^Unsupported:/p' "$VERIFY_FILE"

  cat <<'EOF'

Inspect records with:
EOF
  jq -r '.records[] | "  talon audit show " + .id' "$EVIDENCE_FILE"

  cat <<'EOF'

Scope boundary
  This proves the real Talon gateway path, PII redaction, policy-valid failover,
  cost attribution, and signed evidence. The generated prose is not the proof.
EOF
}

case "$MODE" in
  buyer) show_buyer ;;
  technical) show_technical ;;
  all) show_buyer; show_technical ;;
esac
