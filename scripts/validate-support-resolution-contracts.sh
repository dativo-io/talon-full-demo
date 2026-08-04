#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKFLOW_BASE="$ROOT/integrations/n8n/customer-support-resolution-workflow.json"
WORKFLOW_RENDERER="$ROOT/scripts/render-support-resolution-workflow.py"
RUNNER="$ROOT/scripts/n8n-support-resolution.sh"
PRESENTER="$ROOT/scripts/present-n8n-support-resolution.sh"
APPROVAL_SERVER="$ROOT/scripts/support-approval-server.py"
APPROVAL_CLI="$ROOT/scripts/support-approval.sh"
APPROVAL_VERIFY="$ROOT/scripts/verify-support-approval.py"
POLICY="$ROOT/config/agent-overlays/customer-support/agent.talon.yaml"
SEED="$ROOT/scripts/seed-support-resolution.sh"
RECORDER="$ROOT/scripts/record-latest-n8n-session.sh"
RUN_ID="$ROOT/scripts/new-demo-run.sh"
MOCK="$ROOT/mock/mock_talon.py"
MAKEFILE="$ROOT/Makefile"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

for file in \
  "$WORKFLOW_BASE" "$WORKFLOW_RENDERER" "$RUNNER" "$PRESENTER" \
  "$APPROVAL_SERVER" "$APPROVAL_CLI" "$APPROVAL_VERIFY" \
  "$POLICY" "$SEED" "$RECORDER" "$RUN_ID" "$MOCK" "$MAKEFILE"; do
  [[ -s "$file" ]] || { echo "missing support-resolution artifact: $file" >&2; exit 1; }
done

for input in \
  "$ROOT/cases/customer-support-resolution/01-ticket.md" \
  "$ROOT/cases/customer-support-resolution/02-account-context.md" \
  "$ROOT/cases/customer-support-resolution/03-refund-policy.md"; do
  [[ -s "$input" ]] || { echo "missing support-resolution input: $input" >&2; exit 1; }
done

grep -Fq 'anna.kowalska@example.test' "$ROOT/cases/customer-support-resolution/01-ticket.md"
grep -Fq 'PL61109010140000071219812874' "$ROOT/cases/customer-support-resolution/01-ticket.md"
grep -Fq 'issue_refund' "$ROOT/cases/customer-support-resolution/03-refund-policy.md"

python3 -m py_compile "$WORKFLOW_RENDERER" "$APPROVAL_SERVER" "$APPROVAL_VERIFY"
python3 "$WORKFLOW_RENDERER" "$WORKFLOW_BASE" "$TMP/workflow.json"
jq -e '
  .id == "talonSupportResolution01"
  and .active == false
  and (.nodes | length) >= 18
  and any(.nodes[]; .name == "Draft Reply Through Talon"
      and (.parameters.url | contains("/local-llama/"))
      and (.parameters.jsonBody | contains("llama3.2:1b"))
      and (.parameters.jsonBody | contains("write only the body"))
      and (.parameters.jsonBody | contains("Do not include a subject line")))
  and any(.nodes[]; .name == "Require Reply Draft"
      and (.parameters.jsCode | contains("Reply contains a redaction placeholder"))
      and (.parameters.jsCode | contains("entry_requested_model"))
      and (.parameters.jsCode | contains("llama3.2:1b"))
      and (.parameters.jsCode | contains("fallback_target_model"))
      and (.parameters.jsCode | contains("gpt-4o-mini"))
      and (.parameters.jsCode | contains("provider_reported_model")))
  and any(.nodes[]; .name == "Probe Forbidden Refund Action"
      and (.parameters.url | contains("/openai/"))
      and (.parameters.jsonBody | contains("issue_refund")))
  and any(.nodes[]; .name == "Create Human Approval Request"
      and (.parameters.jsonBody | contains("RELEASE_RUN_NONCE"))
      and (.parameters.jsonBody | contains("TALON_SUPPORT_APPROVAL_ID")))
  and any(.nodes[]; .name == "Wait for Operator Decision"
      and (.parameters.url | contains("/wait/")))
  and any(.nodes[]; .name == "Validate Operator Decision"
      and (.parameters.jsCode | contains("Operator approval receipt binding mismatch")))
  and any(.nodes[]; .name == "Operator Approved?")
  and any(.nodes[]; .name == "Build Approved Artifacts"
      and (.parameters.jsCode | contains("approved_for_finance_processing"))
      and (.parameters.jsCode | contains("entry_requested_model"))
      and (.parameters.jsCode | contains("fallback_target_model"))
      and (.parameters.jsCode | contains("ACME Support Team"))
      and (.parameters.jsCode | contains("refund_executed: false")))
  and any(.nodes[]; .name == "Write Finance Handoff")
  and any(.nodes[]; .name == "Build Rejected Artifacts"
      and (.parameters.jsCode | contains("human_rejected")))
  and any(.nodes[]; .name == "Write Rejected Status")
  and (tostring | contains("Bearer ") | not)
' "$TMP/workflow.json" >/dev/null || {
  echo 'rendered support workflow lost its draft, model route, denial, blocking approval, or output contract' >&2
  exit 1
}

for required in \
  'forbidden_tools: ["issue_refund"]' \
  'allowed_providers: ["local-llama", "openai"]' \
  'input_scan: true' \
  'customer-support-talon-key'; do
  grep -Fq -- "$required" "$POLICY" \
    || { echo "support-resolution policy missing: $required" >&2; exit 1; }
done
if grep -Eq '^[[:space:]]+use_case:' "$POLICY"; then
  echo 'support-resolution overlay uses agent.use_case, unsupported by the released Talon runtime floor' >&2
  exit 1
fi

for required in \
  'start_approval_server' \
  'wait_for_approval_request' \
  'assert_no_final_artifacts' \
  'TALON_SUPPORT_APPROVAL_AUTO_DECISION' \
  'make approve-n8n-support-resolution' \
  'finance-refund-request.json' \
  'operator-approval-receipt.json' \
  'verify-support-approval.py' \
  '.entry_requested_model == "llama3.2:1b"' \
  '.fallback_target_model == "gpt-4o-mini"' \
  'mock receipts do not prove reply-then-zero-cost-refund-denial behavior'; do
  grep -Fq -- "$required" "$RUNNER" \
    || { echo "support-resolution runner missing: $required" >&2; exit 1; }
done

for required in \
  'talon audit export' \
  'talon audit verify --file' \
  'verify-support-approval.py' \
  'Operator receipt  HMAC-SHA256 verified' \
  'Human gate' \
  'Refund status     not executed' \
  'Entry model:' \
  'Fallback target:' \
  'ticket + account context + refund policy' \
  'Direct provider calls or payment actions'; do
  grep -Fq -- "$required" "$PRESENTER" \
    || { echo "support-resolution presenter missing: $required" >&2; exit 1; }
done
if grep -Fq 'queued for approval' "$PRESENTER" || grep -Fq 'Blocked model:' "$PRESENTER"; then
  echo 'support-resolution presenter contains superseded or misleading wording' >&2
  exit 1
fi

for required in \
  '127.0.0.1' \
  'approval service must remain bound to loopback' \
  'HMAC-SHA256' \
  '/wait/' \
  'Approve finance handoff' \
  'Reject request' \
  'refund_executed'; do
  grep -Fq -- "$required" "$APPROVAL_SERVER" \
    || { echo "approval service missing: $required" >&2; exit 1; }
done
for required in \
  'compare_digest' \
  'approval run nonce mismatch' \
  'finance handoff predates approval' \
  'finance handoff exists without approval'; do
  grep -Fq -- "$required" "$APPROVAL_VERIFY" \
    || { echo "approval verifier missing: $required" >&2; exit 1; }
done

for required in \
  'MOCK_TALON_DENY_TOOL' \
  'tool_governance_block' \
  'Request contains forbidden tools' \
  "rec['tool_names']"; do
  grep -Fq -- "$required" "$MOCK" \
    || { echo "mock Talon lacks support-resolution contract: $required" >&2; exit 1; }
done

grep -Fq 'TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID=n8n-support-resolution-' "$RUN_ID" \
  || { echo 'new-demo-run does not mint a support-resolution session' >&2; exit 1; }
grep -Fq 'record-latest-n8n-session.sh support-resolution' "$MAKEFILE" \
  || { echo 'Makefile does not pin the latest support-resolution session' >&2; exit 1; }
grep -Fq 'support-resolution)' "$RECORDER" \
  || { echo 'session recorder does not support support-resolution' >&2; exit 1; }

for target in \
  n8n-support-resolution-validate real-n8n-support-resolution \
  present-n8n-support-resolution present-n8n-support-resolution-tech present-n8n-support-resolution-all \
  approve-n8n-support-resolution reject-n8n-support-resolution status-n8n-support-resolution-approval \
  demo-n8n-support-resolution-buyer demo-n8n-support-resolution-tech; do
  make -n -C "$ROOT" "$target" >/dev/null \
    || { echo "Make target is not runnable: $target" >&2; exit 1; }
done

for target in \
  present-n8n-support-resolution present-n8n-support-resolution-tech present-n8n-support-resolution-all \
  demo-n8n-support-resolution-buyer demo-n8n-support-resolution-tech; do
  make -n -C "$ROOT" "$target" | grep -Fq 'TALON_CLI_PROFILE=audit' \
    || { echo "$target does not select the audit-capable Talon CLI profile" >&2; exit 1; }
done

echo 'N8N SUPPORT RESOLUTION COMPLETION CONTRACTS PASSED'