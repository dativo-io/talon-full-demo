#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKFLOW="$ROOT/integrations/n8n/customer-support-resolution-workflow.json"
RUNNER="$ROOT/scripts/n8n-support-resolution.sh"
PRESENTER="$ROOT/scripts/present-n8n-support-resolution.sh"
POLICY="$ROOT/config/agent-overlays/customer-support/agent.talon.yaml"
SEED="$ROOT/scripts/seed-support-resolution.sh"
RECORDER="$ROOT/scripts/record-latest-n8n-session.sh"
RUN_ID="$ROOT/scripts/new-demo-run.sh"
MOCK="$ROOT/mock/mock_talon.py"
MAKEFILE="$ROOT/Makefile"

for file in "$WORKFLOW" "$RUNNER" "$PRESENTER" "$POLICY" "$SEED" "$RECORDER" "$RUN_ID" "$MOCK" "$MAKEFILE"; do
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

jq -e '
  .id == "talonSupportResolution01"
  and .active == false
  and (.nodes | length) >= 11
  and any(.nodes[]; .name == "Draft Reply Through Talon"
      and (.parameters.url | contains("/local-llama/"))
      and .parameters.options.response.response.fullResponse == true
      and .parameters.options.response.response.neverError == true
      and .credentials.httpHeaderAuth.id == "talonSupportResolutionAuth1")
  and any(.nodes[]; .name == "Probe Forbidden Refund Action"
      and (.parameters.url | contains("/openai/"))
      and (.parameters.jsonBody | contains("issue_refund"))
      and .credentials.httpHeaderAuth.id == "talonSupportResolutionAuth1")
  and any(.nodes[]; .name == "Require Refund Action Denial"
      and (.parameters.jsCode | contains("forbidden tools"))
      and (.parameters.jsCode | contains("tool_governance_block")))
  and any(.nodes[]; .name == "Build Resolution Status"
      and (.parameters.jsCode | contains("governed_support_resolution"))
      and (.parameters.jsCode | contains("human_approval_required")))
  and (tostring | contains("Bearer ") | not)
' "$WORKFLOW" >/dev/null || {
  echo 'support-resolution workflow lost its draft/tool-denial/credential-free contract' >&2
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
  'MOCK_TALON_DENY_TOOL=issue_refund' \
  'talonSupportResolutionAuth1' \
  'n8n-customer-support-resolution-full-demo' \
  'assert_mock_receipts' \
  'tool_governance_block' \
  'human-approval boundary'; do
  grep -Fq -- "$required" "$RUNNER" \
    || { echo "support-resolution runner missing: $required" >&2; exit 1; }
done

for required in \
  'talon audit export' \
  'talon audit verify --file' \
  'all(.records[]; .session_id == $s)' \
  '.tool_governance.tools_requested' \
  '.tool_governance.tools_filtered' \
  'index("issue_refund")' \
  'failed_attempt' \
  'fallback_decision' \
  'Direct provider calls or payment actions'; do
  grep -Fq -- "$required" "$PRESENTER" \
    || { echo "support-resolution presenter missing: $required" >&2; exit 1; }
done

for required in \
  'config/agent-overlays/customer-support/agent.talon.yaml' \
  'talon validate --dir'; do
  grep -Fq -- "$required" "$SEED" \
    || { echo "support-resolution seed missing: $required" >&2; exit 1; }
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
