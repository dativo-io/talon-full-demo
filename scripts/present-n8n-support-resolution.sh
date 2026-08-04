#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
OUT="$STATE/n8n-support-resolution-output"
ENV_FILE="$ROOT/.env"
RUN_ENV="$STATE/demo-run.env"
LATEST_ENV="$STATE/latest-n8n-support-resolution-session.env"
APPROVAL_VERIFY="$ROOT/scripts/verify-support-approval.py"
MODE="${1:-buyer}"

usage() {
  cat <<'USAGE'
Usage: TALON_PRESENT_N8N_SUPPORT_RESOLUTION_SESSION_ID=<session> bash scripts/present-n8n-support-resolution.sh [buyer|technical|all]

buyer      Show the governed support-resolution business outcome.
technical  Show PII handling, fallback, tool denial, operator decision, artifacts, cost, and signatures.
all        Show buyer view followed by technical proof.

This command does not run n8n or call a model. It fails closed unless the imported
workflow produced matching final artifacts, signed Talon evidence proves the redacted
reply path and zero-cost issue_refund denial, and a separately signed operator receipt
proves the exact current-session approval or rejection.
USAGE
}

case "$MODE" in
  buyer|technical|all) ;;
  -h|--help|help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

for cmd in talon jq python3; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: missing command: $cmd" >&2; exit 1; }
done
[[ -f "$ENV_FILE" ]] || { echo 'ERROR: missing .env; run make real-prepare' >&2; exit 1; }
[[ -s "$APPROVAL_VERIFY" ]] || { echo "ERROR: missing $APPROVAL_VERIFY" >&2; exit 1; }
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
APPROVAL_RECEIPT="$OUT/operator-approval-receipt.json"
FINANCE_FILE="$OUT/finance-refund-request.json"
APPROVAL_KEY="$STATE/$SESSION.approval.key"
[[ -s "$REPORT_FILE" ]] || { echo "ERROR: missing $REPORT_FILE; the workflow may still be waiting for approval" >&2; exit 1; }
[[ -s "$STATUS_FILE" ]] || { echo "ERROR: missing $STATUS_FILE; the workflow may still be waiting for approval" >&2; exit 1; }
[[ -s "$APPROVAL_RECEIPT" ]] || { echo "ERROR: missing $APPROVAL_RECEIPT" >&2; exit 1; }
[[ -s "$APPROVAL_KEY" ]] || { echo "ERROR: missing $APPROVAL_KEY" >&2; exit 1; }

grep -Fq 'Best regards,' "$REPORT_FILE" || { echo 'ERROR: final reply lacks deterministic closing' >&2; exit 1; }
grep -Fq 'ACME Support Team' "$REPORT_FILE" || { echo 'ERROR: final reply lacks deterministic application-owned signature' >&2; exit 1; }
if grep -Eq '\[\[[^]]+\]\]' "$REPORT_FILE"; then
  echo 'ERROR: final reply contains a redaction placeholder' >&2
  exit 1
fi
if grep -Fq 'anna.kowalska@example.test' "$REPORT_FILE" || grep -Fq 'PL61109010140000071219812874' "$REPORT_FILE"; then
  echo 'ERROR: final reply contains raw synthetic identifiers' >&2
  exit 1
fi
if grep -Eiq 'refund (has been|was|is) (issued|completed|processed)|money (has been|was) returned' "$REPORT_FILE"; then
  echo 'ERROR: final reply claims the refund was executed' >&2
  exit 1
fi

jq -e --arg s "$SESSION" '
  .status == "completed"
  and .session_id == $s
  and .operational_id == "customer-support"
  and .ticket_id == "SUP-1042"
  and .refund_amount_eur == 249
  and .reply_draft_created == true
  and .blocked_tool == "issue_refund"
  and .denial_code == "tool_governance_block"
  and .denied_provider_cost_usd == 0
  and .operator_approval_required == true
  and .human_approval_completed == true
  and (.operator_decision == "approved" or .operator_decision == "rejected")
  and .requested_model == "gpt-4o-mini"
  and (.provider_reported_model | type == "string" and length > 0)
  and .refund_executed == false
' "$STATUS_FILE" >/dev/null || { echo 'ERROR: workflow status does not match the operator-gated support session' >&2; exit 1; }

RUN_NONCE="$(jq -r '.run_nonce' "$STATUS_FILE")"
DECISION="$(jq -r '.operator_decision' "$STATUS_FILE")"
APPROVAL_ID="$(jq -r '.approval_id' "$STATUS_FILE")"
TICKET="$(jq -r '.ticket_id' "$STATUS_FILE")"
AMOUNT="$(jq -r '.refund_amount_eur' "$STATUS_FILE")"
BLOCKED_TOOL="$(jq -r '.blocked_tool' "$STATUS_FILE")"
REQUESTED_MODEL="$(jq -r '.requested_model' "$STATUS_FILE")"
PROVIDER_REPORTED_MODEL="$(jq -r '.provider_reported_model' "$STATUS_FILE")"
DOCUMENTS="$(jq -r '.documents_read' "$STATUS_FILE")"

APPROVAL_ARGS=(
  --receipt "$APPROVAL_RECEIPT"
  --key "$APPROVAL_KEY"
  --session "$SESSION"
  --run-nonce "$RUN_NONCE"
  --ticket "$TICKET"
  --amount "$AMOUNT"
  --action "$BLOCKED_TOOL"
  --decision "$DECISION"
)
if [[ "$DECISION" == approved ]]; then
  [[ -s "$FINANCE_FILE" ]] || { echo 'ERROR: approved decision lacks finance-refund-request.json' >&2; exit 1; }
  APPROVAL_ARGS+=(--finance-handoff "$FINANCE_FILE")
  jq -e '.result == "governed_support_resolution" and .action_status == "approved_for_finance_processing" and .finance_handoff_file == "finance-refund-request.json"' "$STATUS_FILE" >/dev/null \
    || { echo 'ERROR: approved workflow status lacks finance handoff state' >&2; exit 1; }
else
  [[ ! -e "$FINANCE_FILE" ]] || { echo 'ERROR: rejected decision created a finance handoff' >&2; exit 1; }
  jq -e '.result == "governed_support_resolution_rejected" and .action_status == "human_rejected" and .finance_handoff_file == null' "$STATUS_FILE" >/dev/null \
    || { echo 'ERROR: rejected workflow status is inconsistent' >&2; exit 1; }
fi
APPROVAL_VERIFY_OUTPUT="$(python3 "$APPROVAL_VERIFY" "${APPROVAL_ARGS[@]}")"

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
ALLOWED="$(jq '[.records[] | select(.policy_decision.allowed == true)] | length' "$EVIDENCE_FILE")"
DENIED="$(jq '[.records[] | select(.policy_decision.allowed == false)] | length' "$EVIDENCE_FILE")"
COST="$(jq -r '[.records[].execution.cost // 0] | add // 0' "$EVIDENCE_FILE")"
COST_FMT="$(printf '%.6f' "$COST")"
DENIED_COST="$(jq -r '[.records[] | select(.policy_decision.allowed == false and (.tool_governance.tools_filtered // [] | index("issue_refund"))) | (.execution.cost // 0)] | add // 0' "$EVIDENCE_FILE")"
DENIED_COST_FMT="$(printf '%.6f' "$DENIED_COST")"

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
export TALON_N8N_SUPPORT_RESOLUTION_APPROVAL_RECEIPT=$APPROVAL_RECEIPT
EOF_LATEST
chmod 0600 "$LATEST_ENV"

show_buyer() {
  local business human_gate
  if [[ "$DECISION" == approved ]]; then
    business="$TICKET reply drafted; human-approved finance handoff created"
    human_gate="EUR $AMOUNT request explicitly approved"
  else
    business="$TICKET reply drafted; finance handoff rejected"
    human_gate="EUR $AMOUNT request explicitly rejected"
  fi
  cat <<EOF_BUYER

TALON VERIFIED AI USE CASE
────────────────────────────────────────────────────────────
Use case          n8n customer-support resolution
Operational ID    $AGENT
Business outcome  $business
Data handling     Confidential input; email + IBAN redacted
Reliability       ${FAILED_PROVIDER:-local model} unavailable; ${SELECTED_PROVIDER:-approved fallback} selected
AI authority      $BLOCKED_TOOL blocked before provider dispatch
Human gate        $human_gate
Refund status     not executed
Denied request    \$$DENIED_COST_FMT provider cost
Approved model    ${APPROVED_MODELS:-$REQUESTED_MODEL}
Session spend     \$$COST_FMT
Talon evidence    $VALID valid / $INVALID invalid records
Operator receipt  HMAC-SHA256 verified
Result            VERIFIED GOVERNED RESOLUTION
────────────────────────────────────────────────────────────
What this means: the workflow produced a usable customer reply despite a provider
failure. Talon prevented the model from receiving the financial refund action.
The workflow then stopped until a demo operator made an explicit decision for this
exact ticket, amount, session, and run. The refund itself was not executed.
EOF_BUYER
}

show_technical() {
  cat <<EOF_TECH

TALON TECHNICAL PROOF — N8N CUSTOMER SUPPORT RESOLUTION
────────────────────────────────────────────────────────────
Session:          $SESSION
Agent:            $AGENT
Inputs:           ticket + account context + refund policy
Decisions:        $ALLOWED Talon allowed / $DENIED Talon denied
Ticket:           $TICKET
Refund amount:    EUR $AMOUNT
PII:              $PII
Failed route:     ${FAILED_PROVIDER:-not recorded}
Selected route:   ${SELECTED_PROVIDER:-not recorded}
Skipped route:    ${SKIPPED_PROVIDERS:-none}
Requested model:  $REQUESTED_MODEL
Provider model:   $PROVIDER_REPORTED_MODEL
Evidence model:   ${APPROVED_MODELS:-not recorded}
Blocked tool:     $BLOCKED_TOOL
Operator decision:$DECISION
Approval ID:      $APPROVAL_ID
Refund executed:  no
Session cost:     \$$COST_FMT
Denied cost:      \$$DENIED_COST_FMT
Talon evidence:   $EVIDENCE_FILE
Approval receipt: $APPROVAL_RECEIPT
Status:           $STATUS_FILE
Resolution:       $REPORT_FILE
EOF_TECH
  if [[ "$DECISION" == approved ]]; then
    echo "Finance handoff:  $FINANCE_FILE"
  else
    echo 'Finance handoff:  not created'
  fi

  echo
  talon audit list --session "$SESSION"

  cat <<'EOF_TIMELINE'

Talon evidence timeline (oldest first)
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

AI action boundary
  Requested tool: $BLOCKED_TOOL
  Forwarded tool: none
  Denied provider cost: \$$DENIED_COST_FMT

Human continuation boundary
  $APPROVAL_VERIFY_OUTPUT
  Talon did not approve the refund. The separate operator gate decided whether the
  workflow could create a synthetic finance handoff after Talon blocked AI authority.

Workflow artifacts
  resolution: $REPORT_FILE
  status:     $STATUS_FILE
  approval:   $APPROVAL_RECEIPT
EOF_PROOF
  if [[ "$DECISION" == approved ]]; then
    echo "  finance:    $FINANCE_FILE"
  else
    echo '  finance:    not created after rejection'
  fi

  cat <<'EOF_CRYPTO'

Cryptographic verification — Talon evidence
EOF_CRYPTO
  sed -n '/^Total records:/,/^Unsupported:/p' "$VERIFY_FILE"
  echo
  echo 'Cryptographic verification — operator receipt'
  echo "  $APPROVAL_VERIFY_OUTPUT"

  cat <<'EOF_INSPECT'

Inspect Talon records with:
EOF_INSPECT
  jq -r '.records[] | "  talon audit show " + .id' "$EVIDENCE_FILE"

  cat <<'EOF_BOUNDARY'

Scope boundary
  The ticket, account, policy, approval service, and finance handoff are synthetic.
  Talon did not execute, approve, or decline a refund. It blocked a governed model
  request whose tool schema exposed issue_refund. A separate loopback operator gate
  controlled only workflow continuation. Direct provider calls or payment actions
  that bypass the governed paths remain outside this proof.
EOF_BOUNDARY
}

case "$MODE" in
  buyer) show_buyer ;;
  technical) show_technical ;;
  all) show_buyer; show_technical ;;
esac
