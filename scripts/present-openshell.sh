#!/usr/bin/env bash
set -euo pipefail

# Existing Full Demo contract: re-export current-run evidence, verify offline,
# verify full action lifecycle, then project buyer/technical views from SAME run.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-buyer}"
[[ "$MODE" == buyer || "$MODE" == technical || "$MODE" == all ]] \
  || { echo 'Usage: present-openshell.sh buyer|technical|all' >&2; exit 2; }
STATE="$ROOT/.state/openshell"
[[ -s "$ROOT/.env" && -s "$STATE/latest.env" ]] \
  || { echo 'ERROR: OpenShell environment/run not prepared' >&2; exit 1; }
source "$ROOT/.env"
source "$STATE/latest.env"
SESSION="${TALON_SHOWCASE_SESSION:-}"
[[ "$SESSION" =~ ^openshell-[A-Za-z0-9-]+$ ]] || { echo 'ERROR: invalid session' >&2; exit 1; }
CLI="${TALON_BIN:-talon}"
command -v "$CLI" >/dev/null || { echo 'ERROR: audit-capable Talon CLI unavailable' >&2; exit 1; }

EVIDENCE="$STATE/$SESSION.signed.json"
VERIFY="$STATE/$SESSION.verify.txt"
REPORT="$STATE/$SESSION.runtime-report.txt"
RECEIPT="$STATE/$SESSION.result.json"
OP_VERIFY="$STATE/$SESSION.operation-verify.txt"
[[ -s "$RECEIPT" ]] || { echo "ERROR: missing canonical runner receipt $RECEIPT" >&2; exit 1; }
jq -e --arg s "$SESSION" '
  .session_id == $s
  and (.runtime_ref | type == "string" and length > 0)
  and (.refund_operation_id | type == "string" and length > 0)
' "$RECEIPT" >/dev/null || { echo 'ERROR: wrong session or incomplete runtime receipt' >&2; exit 1; }
RUNTIME="$(jq -r '.runtime_ref' "$RECEIPT")"
OP="$(jq -r '.refund_operation_id' "$RECEIPT")"

"$CLI" audit export --format signed-json --session "$SESSION" --output "$EVIDENCE" >/dev/null
"$CLI" audit verify --file "$EVIDENCE" >"$VERIFY"
for condition in 'Invalid records: 0' 'Missing signature: 0' 'Could not parse: 0' 'Unsupported: 0'; do
  grep -Fq "$condition" "$VERIFY" \
    || { echo "ERROR: verification did not establish '$condition'" >&2; cat "$VERIFY" >&2; exit 1; }
done

# Critical product claims must have signed current-session records. A mocked
# agent transcript or a presenter-written receipt can never satisfy this gate.
jq -e --arg s "$SESSION" --arg r "$RUNTIME" '
  (.records | length > 0)
  and all(.records[]; .session_id == $s and .agent_id == "sandboxed-support")
  and any(.records[]; .invocation_type == "gateway"
      and ((.tool_governance.tools_filtered // [] | tostring) | contains("delete_customer")))
  and any(.records[]; .invocation_type == "gateway_response")
  and any(.records[]; .invocation_type == "action_lifecycle"
      and .enforcement.provenance == "talon_enforced"
      and .enforcement.runtime.reference == $r
      and .workload_identity.status == "verified")
' "$EVIDENCE" >/dev/null || {
  echo 'ERROR: session evidence does not prove delegated model, tool filter and authenticated action lifecycle' >&2
  exit 1
}

"$CLI" audit verify --operation "$OP" >"$OP_VERIFY"
grep -Fxq 'Lifecycle: VALID' "$OP_VERIFY" \
  || { echo 'ERROR: refund lifecycle is not verified' >&2; exit 1; }
"$CLI" audit list --runtime-ref "$RUNTIME" --limit 200 --report >"$REPORT"
grep -Fq 'Runtime reference ' "$REPORT" \
  || { echo 'ERROR: runtime report unavailable' >&2; exit 1; }
if grep -Fq 'More records exist:' "$REPORT"; then
  echo 'ERROR: runtime report is paginated/incomplete (requires larger limit)' >&2
  exit 1
fi

# Approval status is verified from Talon's own action lifecycle, not from the
# reviewer script's exit status. OpenShell does NOT own human authorization.
DECISION="$(jq -r --arg op "$OP" '[.records[] | select(.invocation_type == "action_lifecycle" and .action_lifecycle.operation_id == $op and .action_lifecycle.event == "approval_decided") | .action_lifecycle.approval_status] | last // empty' "$EVIDENCE")"
[[ "$DECISION" == approved || "$DECISION" == rejected ]] \
  || { echo 'ERROR: missing exact-operation Talon reviewer decision' >&2; exit 1; }

COUNT="$(jq '.records|length' "$EVIDENCE")"
COST="$(jq '[.records[]|(.execution.cost // 0)]|add // 0' "$EVIDENCE")"
[[ "$COUNT" -ge 1 ]] || { echo 'ERROR: no current-run evidence' >&2; exit 1; }

buyer() {
  cat <<EOF

TALON VERIFIED AI USE CASE — OPENSHELL
────────────────────────────────────────────────────────────
Use case          Sandboxed customer-support agent
Session           $SESSION
Runtime           OpenShell contains the agent
Company policy    Talon governs model and business actions
Forbidden tool    delete_customer filtered
Human decision    $DECISION in Talon's Action Gateway
Refund action     Lifecycle VERIFIED (synthetic downstream)
Model spend       \$$COST (Talon signed-record accounting)
Evidence          $COUNT records; all signatures verified
────────────────────────────────────────────────────────────
A sandboxed agent proposed a consequential action. Company policy
required a separate human decision before the governed dispatch.
EOF
}
technical() {
  cat <<EOF

TALON TECHNICAL PROOF — OPENSHELL
────────────────────────────────────────────────────────────
Session:         $SESSION
Sandbox:         $RUNTIME
Operation:       $OP
Evidence:        $EVIDENCE
Runtime report:  $REPORT

EOF
  cat "$REPORT"
  echo 'Full action lifecycle verification:'
  cat "$OP_VERIFY"
  cat <<'EOF'

Scope:
  OpenShell owns containment/credential injection and applies delegated
  verdicts; Talon owns business policy, Action Gateway and signed decisions.
  Imported containment records are external assertions, not runtime proof.
  The refund endpoint is a mock; no real payment was executed.
EOF
}

case "$MODE" in
  buyer) buyer ;;
  technical) technical ;;
  all) buyer; technical ;;
esac
