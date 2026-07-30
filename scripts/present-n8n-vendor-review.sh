#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
OUT="$STATE/n8n-vendor-review-output"
ENV_FILE="$ROOT/.env"
RUN_ENV="$STATE/demo-run.env"
LATEST_ENV="$STATE/latest-n8n-vendor-review-session.env"
MODE="${1:-buyer}"

usage() {
  cat <<'USAGE'
Usage: TALON_PRESENT_N8N_VENDOR_REVIEW_SESSION_ID=<session> bash scripts/present-n8n-vendor-review.sh [buyer|technical|all]

buyer      Show the controlled vendor-review business outcome.
technical  Show the egress decisions, PII redaction, cost, artifacts, and signature verification.
all        Show buyer view followed by technical proof.

This command does not run n8n or call a model. It fails closed unless the real imported
workflow produced a review and matching status, and signed Talon evidence proves the
OpenAI egress denial followed by the redacted Anthropic review in one session.
USAGE
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
# shellcheck disable=SC1090
source "$ENV_FILE"

SESSION="${TALON_PRESENT_N8N_VENDOR_REVIEW_SESSION_ID:-}"
if [[ -z "$SESSION" && -f "$LATEST_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$LATEST_ENV"
  SESSION="${TALON_N8N_VENDOR_REVIEW_PRESENTED_SESSION_ID:-}"
fi
if [[ -z "$SESSION" && -f "$RUN_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$RUN_ENV"
  SESSION="${TALON_N8N_VENDOR_REVIEW_SESSION_ID:-}"
fi
[[ -n "$SESSION" ]] || { echo 'ERROR: no vendor-review session; run make demo-n8n-vendor-review-buyer or set TALON_PRESENT_N8N_VENDOR_REVIEW_SESSION_ID' >&2; exit 1; }

REPORT_FILE="$OUT/vendor-contract-review.md"
STATUS_FILE="$OUT/status.json"
[[ -s "$REPORT_FILE" ]] || { echo "ERROR: missing $REPORT_FILE" >&2; exit 1; }
[[ -s "$STATUS_FILE" ]] || { echo "ERROR: missing $STATUS_FILE" >&2; exit 1; }
grep -Fq 'Human legal, privacy, security, and procurement review remains required' "$REPORT_FILE" \
  || { echo 'ERROR: review artifact lacks the human-review boundary' >&2; exit 1; }
jq -e --arg s "$SESSION" '
  .status == "completed"
  and .result == "controlled_vendor_review"
  and .session_id == $s
  and .operational_id == "vendor-contract-review"
  and .denied_destination == "openai"
  and .denied_provider_cost_usd == 0
  and .approved_destination == "anthropic"
  and .human_review_required == true
' "$STATUS_FILE" >/dev/null || { echo 'ERROR: workflow status does not match the requested session and controlled-review contract' >&2; exit 1; }

EVIDENCE_FILE="${TALON_PRESENT_EVIDENCE_FILE:-$STATE/$SESSION.signed.json}"
VERIFY_FILE="$STATE/$SESSION.verify.txt"
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
DESTINATIONS="$(jq -r '[.records[].egress_decision.provider? | select(type == "string" and length > 0)] | unique | join(" → ")' "$EVIDENCE_FILE")"
ALLOWED="$(jq '[.records[] | select(.policy_decision.allowed == true)] | length' "$EVIDENCE_FILE")"
DENIED="$(jq '[.records[] | select(.policy_decision.allowed == false)] | length' "$EVIDENCE_FILE")"
COST="$(jq -r '[.records[].execution.cost // 0] | add // 0' "$EVIDENCE_FILE")"
COST_FMT="$(printf '%.6f' "$COST")"
DENIED_COST="$(jq -r '[.records[] | select(.policy_decision.allowed == false) | (.execution.cost // 0)] | add // 0' "$EVIDENCE_FILE")"
DENIED_COST_FMT="$(printf '%.6f' "$DENIED_COST")"
DOCUMENTS="$(jq -r '.documents_reviewed' "$STATUS_FILE")"
DENIAL_CODE="$(jq -r '.denial_code' "$STATUS_FILE")"

[[ "$TOTAL" -ge 2 ]] || { echo "ERROR: expected at least two vendor-review evidence records for $SESSION" >&2; exit 1; }
[[ "$VALID" == "$TOTAL" && "$INVALID" == "0" ]] || { echo 'ERROR: not every vendor-review record verified' >&2; exit 1; }
[[ "$AGENT" == "vendor-contract-review" ]] || { echo "ERROR: expected vendor-contract-review evidence, found $AGENT" >&2; exit 1; }
[[ "$ALLOWED" -ge 1 && "$DENIED" -ge 1 ]] || { echo "ERROR: expected a denial and an allowed review; found $ALLOWED allowed / $DENIED denied" >&2; exit 1; }
jq -e --arg s "$SESSION" 'all(.records[]; .session_id == $s)' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: exported records do not all belong to the vendor-review session' >&2; exit 1; }
jq -e '
  any(.records[];
    .policy_decision.allowed == false
    and .egress_decision.provider == "openai"
    and .egress_decision.decision == "deny"
    and (.egress_decision.reason == "egress_tier_destination_disallowed" or .egress_decision.reason == "egress_destination_disallowed")
    and (.execution.cost // 0) == 0)
' "$EVIDENCE_FILE" >/dev/null || { echo 'ERROR: signed evidence does not prove the zero-cost OpenAI egress denial' >&2; exit 1; }
jq -e '
  any(.records[];
    .policy_decision.allowed == true
    and .egress_decision.provider == "anthropic"
    and .egress_decision.decision == "allow"
    and .classification.input_tier == 2
    and ((.classification.input_pii_redacted // .classification.pii_redacted // false) == true)
    and (.classification.pii_detected | index("email"))
    and (.classification.pii_detected | index("iban")))
' "$EVIDENCE_FILE" >/dev/null || { echo 'ERROR: signed evidence does not prove confidential-tier email/IBAN redaction on the approved Anthropic request' >&2; exit 1; }
jq -e '
  [.records | sort_by(.timestamp) | .[] | select(.egress_decision != null)] as $r
  | ($r | length) >= 2
  and $r[0].egress_decision.provider == "openai"
  and $r[0].egress_decision.decision == "deny"
  and $r[-1].egress_decision.provider == "anthropic"
  and $r[-1].egress_decision.decision == "allow"
' "$EVIDENCE_FILE" >/dev/null || { echo 'ERROR: evidence timeline does not show denial before approved review' >&2; exit 1; }

umask 077
cat >"$LATEST_ENV" <<EOF_LATEST
export TALON_N8N_VENDOR_REVIEW_PRESENTED_SESSION_ID=$SESSION
export TALON_N8N_VENDOR_REVIEW_EVIDENCE_FILE=$EVIDENCE_FILE
export TALON_N8N_VENDOR_REVIEW_STATUS_FILE=$STATUS_FILE
export TALON_N8N_VENDOR_REVIEW_REPORT_FILE=$REPORT_FILE
EOF_LATEST
chmod 0600 "$LATEST_ENV"

show_buyer() {
  cat <<EOF_BUYER

TALON VERIFIED AI USE CASE
────────────────────────────────────────────────────────────
Use case          n8n vendor contract review
Operational ID    $AGENT
Business outcome  $DOCUMENTS documents reviewed; advisory packet created
Data handling     Confidential input; email + IBAN redacted
Destination rule  OpenAI denied; Anthropic allowed
Denied request    \$$DENIED_COST_FMT provider cost
Model path        ${MODELS:-not recorded} through Talon
Session spend     \$$COST_FMT
Evidence          $VALID valid / $INVALID invalid records
Result            VERIFIED CONTROLLED REVIEW
────────────────────────────────────────────────────────────
What this means: the workflow produced a useful first-pass contract review while
Talon kept the confidential package away from a disallowed destination, redacted
personal and billing identifiers before the approved request, and recorded both
decisions in one verifiable session. Human review remains required.
EOF_BUYER
}

show_technical() {
  cat <<EOF_TECH

TALON TECHNICAL PROOF — N8N VENDOR CONTRACT REVIEW
────────────────────────────────────────────────────────────
Session:          $SESSION
Agent:            $AGENT
Models:           ${MODELS:-not recorded}
Destinations:     ${DESTINATIONS:-not recorded}
Decisions:        $ALLOWED allowed / $DENIED denied
Documents:        $DOCUMENTS
Session cost:     \$$COST_FMT
Denied cost:      \$$DENIED_COST_FMT
Denial code:      $DENIAL_CODE
Evidence:         $EVIDENCE_FILE
Status:           $STATUS_FILE
Review artifact:  $REPORT_FILE
EOF_TECH

  echo
  talon audit list --session "$SESSION"

  cat <<'EOF_TIMELINE'

Evidence timeline (oldest first)
TIME                              DESTINATION  TIER  DECISION  REASON                                COST
EOF_TIMELINE
  jq -r '
    .records
    | sort_by(.timestamp)
    | .[]
    | [
        .timestamp,
        (.egress_decision.provider // "-"),
        ((.classification.input_tier // 0) | tostring),
        (if .policy_decision.allowed then "allow" else "deny" end),
        (.egress_decision.reason // .policy_decision.reasons[0] // "-"),
        ((.execution.cost // 0) | tostring)
      ]
    | @tsv
  ' "$EVIDENCE_FILE"

  cat <<EOF_PROOF

Signed control decisions
  denied:   confidential-tier OpenAI egress, \$$DENIED_COST_FMT provider cost
  allowed:  Anthropic after email + IBAN redaction
  order:    denial recorded before the approved review

Workflow artifacts
  review:   $REPORT_FILE
  status:   $STATUS_FILE

Cryptographic verification
EOF_PROOF
  sed -n '/^Total records:/,/^Unsupported:/p' "$VERIFY_FILE"

  cat <<'EOF_INSPECT'

Inspect records with:
EOF_INSPECT
  jq -r '.records[] | "  talon audit show " + .id' "$EVIDENCE_FILE"

  cat <<'EOF_BOUNDARY'

Scope boundary
  The contract package and review criteria are synthetic. The model output is an
  advisory first pass, not legal advice or a compliance determination. Talon proves
  only the configured controls on traffic routed through it: attribution, egress
  decision, redaction, cost, and signed evidence. Direct provider calls or document
  copies that bypass Talon remain outside this proof.
EOF_BOUNDARY
}

case "$MODE" in
  buyer) show_buyer ;;
  technical) show_technical ;;
  all) show_buyer; show_technical ;;
esac
