#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
OUT="$STATE/n8n-support-resolution-output"
ENV_FILE="$ROOT/.env"
RUN_ENV="$STATE/demo-run.env"
LATEST_ENV="$STATE/latest-n8n-support-resolution-session.env"
MODE="${1:-buyer}"

usage() {
  cat <<'USAGE'
Usage: TALON_PRESENT_N8N_SUPPORT_RESOLUTION_SESSION_ID=<session> bash scripts/present-n8n-support-resolution.sh [buyer|technical|all]

buyer      Show the governed support-resolution business outcome.
technical  Show PII handling, fallback, tool denial, cost, artifacts, and signatures.
all        Show buyer view followed by technical proof.

This command does not run n8n or call a model. It fails closed unless the imported
workflow produced matching artifacts and signed Talon evidence proves the redacted
reply path followed by a zero-cost `issue_refund` schema denial in one session.
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

SESSION="${TALON_PRESENT_N8N_SUPPORT_RESOLUTION_SESSION_ID:-}"
if [[ -z "$SESSION" && -f "$LATEST_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$LATEST_ENV"
  SESSION="${TALON_N8N_SUPPORT_RESOLUTION_PRESENTED_SESSION_ID:-}"
fi
if [[ -z "$SESSION" && -f "$RUN_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$RUN_ENV"
  SESSION="${TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID:-}"
fi
[[ -n "$SESSION" ]] || { echo 'ERROR: no support-resolution session; run make demo-n8n-support-resolution-buyer' >&2; exit 1; }

REPORT_FILE="$OUT/customer-support-resolution.md"
STATUS_FILE="$OUT/status.json"
[[ -s "$REPORT_FILE" ]] || { echo "ERROR: missing $REPORT_FILE" >&2; exit 1; }
[[ -s "$STATUS_FILE" ]] || { echo "ERROR: missing $STATUS_FILE" >&2; exit 1; }
grep -Fq 'refund was not executed and requires human support and finance approval' "$REPORT_FILE" \
  || { echo 'ERROR: resolution packet lacks the human-approval boundary' >&2; exit 1; }
jq -e --arg s "$SESSION" '
  .status == "completed"
  and .result == "governed_support_resolution"
  and .session_id == $s
  and .operational_id == "customer-support"
  and .ticket_id == "SUP-1042"
  and .refund_amount_eur == 249
  and .reply_draft_created == true
  and .blocked_tool == "issue_refund"
  and .denial_code == "tool_governance_block"
  and .denied_provider_cost_usd == 0
  and .action_status == "human_approval_required"
  and .human_approval_required == true
' "$STATUS_FILE" >/dev/null || { echo 'ERROR: workflow status does not match the requested governed support session' >&2; exit 1; }

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
PII="$(jq -r '[.records[].classification.pii_detected[]?] | unique | sort | join(", ")' "$EVIDENCE_FILE")"
FAILED_PROVIDER="$(jq -r '[.records[] | select(.failover.role == "failed_attempt") | .failover.provider] | unique | join(", ")' "$EVIDENCE_FILE")"
SELECTED_PROVIDER="$(jq -r '[.records[] | select(.failover.role == "fallback_decision") | .failover.provider] | unique | join(", ")' "$EVIDENCE_FILE")"
SKIPPED_PROVIDERS="$(jq -r '[.records[].failover.skipped_candidates[]?.provider] | unique | join(", ")' "$EVIDENCE_FILE")"
APPROVED_MODELS="$(jq -r '[.records[] | select(.policy_decision.allowed == true and (.execution.cost // 0) > 0) | .execution.model_used? | select(type == "string" and length > 0)] | unique | join(", ")' "$EVIDENCE_FILE")"
BLOCKED_MODELS="$(jq -r '[.records[] | select(.policy_decision.allowed == false and (.tool_governance.tools_filtered // [] | index("issue_refund"))) | .execution.model_used? | select(type == "string" and length > 0)] | unique | join(", ")' "$EVIDENCE_FILE")"
ALLOWED="$(jq '[.records[] | select(.policy_decision.allowed == true)] | length' "$EVIDENCE_FILE")"
DENIED="$(jq '[.records[] | select(.policy_decision.allowed == false)] | length' "$EVIDENCE_FILE")"
COST="$(jq -r '[.records[].execution.cost // 0] | add // 0' "$EVIDENCE_FILE")"
COST_FMT="$(printf '%.6f' "$COST")"
DENIED_COST="$(jq -r '[.records[] | select(.policy_decision.allowed == false and (.tool_governance.tools_filtered // [] | index("issue_refund"))) | (.execution.cost // 0)] | add // 0' "$EVIDENCE_FILE")"
DENIED_COST_FMT="$(printf '%.6f' "$DENIED_COST")"
DOCUMENTS="$(jq -r '.documents_read' "$STATUS_FILE")"
TICKET="$(jq -r '.ticket_id' "$STATUS_FILE")"
AMOUNT="$(jq -r '.refund_amount_eur' "$STATUS_FILE")"
BLOCKED_TOOL="$(jq -r '.blocked_tool' "$STATUS_FILE")"

[[ "$TOTAL" -ge 3 ]] || { echo "ERROR: expected fallback and tool-denial evidence for $SESSION" >&2; exit 1; }
[[ "$VALID" == "$TOTAL" && "$INVALID" == "0" ]] || { echo 'ERROR: not every support-resolution record verified' >&2; exit 1; }
[[ "$AGENT" == "customer-support" ]] || { echo "ERROR: expected customer-support evidence, found $AGENT" >&2; exit 1; }
jq -e --arg s "$SESSION" 'all(.records[]; .session_id == $s)' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: exported records do not all belong to the support-resolution session' >&2; exit 1; }
jq -e 'any(.records[];
    .policy_decision.allowed == true
    and ((.classification.input_pii_redacted // .classification.pii_redacted // false) == true)
    and .classification.input_tier == 2
    and (.classification.pii_detected | index("email"))
    and (.classification.pii_detected | index("iban")))' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: signed evidence does not prove confidential email/IBAN redaction' >&2; exit 1; }
jq -e 'any(.records[]; .failover.role == "failed_attempt" and .failover.provider == "local-llama" and .failover.error_class == "connection_error")' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: signed evidence does not prove the local provider failure' >&2; exit 1; }
jq -e 'any(.records[]; .failover.role == "fallback_decision" and .failover.provider == "openai" and any(.failover.skipped_candidates[]?; .provider == "openai-batch" and .filter == "agent_provider_allowlist"))' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: signed evidence does not prove policy-valid OpenAI fallback' >&2; exit 1; }
jq -e 'any(.records[];
    .policy_decision.allowed == false
    and (.policy_decision.reasons | index("tool governance block"))
    and (.tool_governance.tools_requested | index("issue_refund"))
    and (.tool_governance.tools_filtered | index("issue_refund"))
    and (.execution.cost // 0) == 0)' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: signed evidence does not prove the zero-cost issue_refund schema denial' >&2; exit 1; }
jq -e '
  ([.records[] | select(.failover.role == "fallback_decision") | .timestamp] | max) as $allowed
  | ([.records[] | select(.policy_decision.allowed == false and (.tool_governance.tools_filtered // [] | index("issue_refund"))) | .timestamp] | min) as $denied
  | $allowed != null and $denied != null and $allowed < $denied
' "$EVIDENCE_FILE" >/dev/null || { echo 'ERROR: evidence timeline does not show the draft before the refund-action denial' >&2; exit 1; }

umask 077
cat >"$LATEST_ENV" <<EOF_LATEST
export TALON_N8N_SUPPORT_RESOLUTION_PRESENTED_SESSION_ID=$SESSION
export TALON_N8N_SUPPORT_RESOLUTION_EVIDENCE_FILE=$EVIDENCE_FILE
export TALON_N8N_SUPPORT_RESOLUTION_STATUS_FILE=$STATUS_FILE
export TALON_N8N_SUPPORT_RESOLUTION_REPORT_FILE=$REPORT_FILE
EOF_LATEST
chmod 0600 "$LATEST_ENV"

show_buyer() {
  cat <<EOF_BUYER

TALON VERIFIED AI USE CASE
────────────────────────────────────────────────────────────
Use case          n8n customer-support resolution
Operational ID    $AGENT
Business outcome  $TICKET reply drafted; EUR $AMOUNT refund queued for approval
Data handling     Confidential input; email + IBAN redacted
Reliability       ${FAILED_PROVIDER:-local model} unavailable; ${SELECTED_PROVIDER:-approved fallback} selected
Policy boundary   $BLOCKED_TOOL blocked before provider dispatch
Denied request    \$$DENIED_COST_FMT provider cost
Approved model    ${APPROVED_MODELS:-not recorded}
Session spend     \$$COST_FMT
Evidence          $VALID valid / $INVALID invalid records
Result            VERIFIED GOVERNED RESOLUTION
────────────────────────────────────────────────────────────
What this means: the workflow produced a usable customer reply despite a provider
failure, but it could not expose the financial refund action to the model. The
draft survived and the refund moved to human support and finance approval.
EOF_BUYER
}

show_technical() {
  cat <<EOF_TECH

TALON TECHNICAL PROOF — N8N CUSTOMER SUPPORT RESOLUTION
────────────────────────────────────────────────────────────
Session:          $SESSION
Agent:            $AGENT
Decisions:        $ALLOWED allowed / $DENIED denied
Documents:        $DOCUMENTS
Ticket:           $TICKET
Refund amount:    EUR $AMOUNT
PII:              $PII
Failed route:     ${FAILED_PROVIDER:-not recorded}
Selected route:   ${SELECTED_PROVIDER:-not recorded}
Skipped route:    ${SKIPPED_PROVIDERS:-none}
Approved model:   ${APPROVED_MODELS:-not recorded}
Blocked model:    ${BLOCKED_MODELS:-not dispatched}
Blocked tool:     $BLOCKED_TOOL
Session cost:     \$$COST_FMT
Denied cost:      \$$DENIED_COST_FMT
Evidence:         $EVIDENCE_FILE
Status:           $STATUS_FILE
Resolution:       $REPORT_FILE
EOF_TECH

  echo
  talon audit list --session "$SESSION"

  cat <<'EOF_TIMELINE'

Evidence timeline (oldest first)
TIME                              ROLE / SURFACE       PROVIDER / MODEL       DECISION  FILTERED TOOLS  COST
EOF_TIMELINE
  jq -r '
    .records
    | sort_by(.timestamp)
    | .[]
    | [
        .timestamp,
        (if (.tool_governance.tools_filtered // [] | length) > 0 then "tool_schema" elif (.failover.role // "") != "" then .failover.role else .invocation_type end),
        (if (.failover.provider // "") != "" then .failover.provider else (.execution.model_used // "-") end),
        (if .policy_decision.allowed then "allow" else "deny" end),
        ((.tool_governance.tools_filtered // []) | join(",")),
        ((.execution.cost // 0) | tostring)
      ]
    | @tsv
  ' "$EVIDENCE_FILE"

  cat <<EOF_PROOF

Policy-valid service path
  1. Preferred local provider failed: $FAILED_PROVIDER
  2. Disallowed candidate was skipped: $SKIPPED_PROVIDERS
  3. Approved fallback drafted the reply: $SELECTED_PROVIDER / ${APPROVED_MODELS:-not recorded}
  4. Later request exposed $BLOCKED_TOOL: denied before provider dispatch

Data boundary
  Detected: $PII
  Evidence proves email + IBAN were redacted before the approved provider request.

Action boundary
  Requested tool: $BLOCKED_TOOL
  Forwarded tool: none
  Denied provider cost: \$$DENIED_COST_FMT

Workflow artifacts
  resolution: $REPORT_FILE
  status:     $STATUS_FILE

Cryptographic verification
EOF_PROOF
  sed -n '/^Total records:/,/^Unsupported:/p' "$VERIFY_FILE"

  cat <<'EOF_INSPECT'

Inspect records with:
EOF_INSPECT
  jq -r '.records[] | "  talon audit show " + .id' "$EVIDENCE_FILE"

  cat <<'EOF_BOUNDARY'

Scope boundary
  The ticket, account, and policy are synthetic. Talon did not execute, approve,
  or decline a refund. It blocked a governed model request whose tool schema
  exposed issue_refund. Human support and finance systems remain responsible for
  the real action. Direct provider calls or payment actions that bypass Talon are
  outside this proof.
EOF_BOUNDARY
}

case "$MODE" in
  buyer) show_buyer ;;
  technical) show_technical ;;
  all) show_buyer; show_technical ;;
esac
