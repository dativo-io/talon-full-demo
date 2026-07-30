#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKFLOW="$ROOT/integrations/n8n/quarterly-compliance-workflow.json"
RUNNER="$ROOT/scripts/n8n-workflow.sh"
VALIDATE_AGENT="$ROOT/scripts/validate-agent-policy.sh"
PRESENTER="$ROOT/scripts/present-n8n.sh"
VENDOR_WORKFLOW="$ROOT/integrations/n8n/vendor-contract-review-workflow.json"
VENDOR_RUNNER="$ROOT/scripts/n8n-vendor-review.sh"
VENDOR_PRESENTER="$ROOT/scripts/present-n8n-vendor-review.sh"
VENDOR_POLICY="$ROOT/config/agent-overlays/vendor-contract-review/agent.talon.yaml"
VENDOR_SEED="$ROOT/scripts/seed-vendor-review.sh"
LATEST_RECORDER="$ROOT/scripts/record-latest-n8n-session.sh"
WITH_TALON="$ROOT/scripts/with-talon.sh"
AUDIT_RESOLVER="$ROOT/scripts/resolve-talon-audit.sh"
MAKEFILE="$ROOT/Makefile"
COMPOSE="$ROOT/integrations/n8n/compose.yaml"
PACKAGE="$ROOT/scripts/package-zendesk-app.sh"
INSTALLED="$ROOT/scripts/verify-zendesk-installed.sh"
ZENDESK_MANIFEST="$ROOT/integrations/zendesk-app/manifest.json"
ZENDESK_ICON="$ROOT/integrations/zendesk-app/assets/icon_ticket_editor.svg"
MOCK_TALON="$ROOT/mock/mock_talon.py"

for file in \
  "$WORKFLOW" "$RUNNER" "$VALIDATE_AGENT" "$PRESENTER" \
  "$VENDOR_WORKFLOW" "$VENDOR_RUNNER" "$VENDOR_PRESENTER" "$VENDOR_POLICY" "$VENDOR_SEED" "$LATEST_RECORDER" \
  "$WITH_TALON" "$AUDIT_RESOLVER" "$MAKEFILE" "$COMPOSE" "$PACKAGE" "$INSTALLED" \
  "$ZENDESK_MANIFEST" "$ZENDESK_ICON" "$MOCK_TALON"; do
  [[ -s "$file" ]] || { echo "missing completion artifact: $file" >&2; exit 1; }
done

for input in \
  "$ROOT/cases/vendor-contract-review/01-vendor-profile.md" \
  "$ROOT/cases/vendor-contract-review/02-data-processing-addendum.md" \
  "$ROOT/cases/vendor-contract-review/03-review-policy.md"; do
  [[ -s "$input" ]] || { echo "missing vendor-review input: $input" >&2; exit 1; }
done

grep -Fq 'maria.santos@example.test' "$ROOT/cases/vendor-contract-review/01-vendor-profile.md" \
  || { echo 'vendor-review fixture lacks the synthetic email signal' >&2; exit 1; }
grep -Fq 'DE89370400440532013000' "$ROOT/cases/vendor-contract-review/01-vendor-profile.md" \
  || { echo 'vendor-review fixture lacks the synthetic IBAN signal' >&2; exit 1; }

jq -e '
  .id == "talonQuarterly01"
  and .active == false
  and ([.nodes[].type] | index("n8n-nodes-base.splitInBatches"))
  and ([.nodes[].type] | index("n8n-nodes-base.httpRequest"))
  and ([.nodes[].type] | index("n8n-nodes-base.readWriteFile"))
  and ([.nodes[].type] | index("n8n-nodes-base.stopAndError"))
  and any(.nodes[]; .name == "Summarize Through Talon"
      and .parameters.options.response.response.fullResponse == true
      and .parameters.options.response.response.neverError == true
      and .credentials.httpHeaderAuth.id == "talonHeaderAuth1")
  and any(.nodes[]; .name == "Budget Stopped Next Request"
      and (.parameters | tostring | contains("session_budget_exceeded"))
      and (.parameters | tostring | contains("error?.type"))
      and (.parameters | tostring | contains("error?.code")))
  and (tostring | contains("Bearer ") | not)
' "$WORKFLOW" >/dev/null || {
  echo 'n8n workflow is missing its sequential budget/evidence/real-error-schema/credential-free contract' >&2
  exit 1
}

jq -e '
  .id == "talonVendorReview01"
  and .active == false
  and (.nodes | length) >= 10
  and any(.nodes[]; .name == "Probe Disallowed OpenAI Destination"
      and (.parameters.url | contains("/openai/"))
      and .parameters.options.response.response.fullResponse == true
      and .parameters.options.response.response.neverError == true
      and .credentials.httpHeaderAuth.id == "talonVendorReviewAuth1")
  and any(.nodes[]; .name == "Require Egress Denial"
      and (.parameters.jsCode | contains("egress_tier_destination_disallowed"))
      and (.parameters.jsCode | contains("egress_destination_disallowed")))
  and any(.nodes[]; .name == "Review Through Approved Anthropic"
      and (.parameters.url | contains("/anthropic/"))
      and .credentials.httpHeaderAuth.id == "talonVendorReviewAuth1")
  and any(.nodes[]; .name == "Build Review Status"
      and (.parameters.jsCode | contains("controlled_vendor_review"))
      and (.parameters.jsCode | contains("human_review_required")))
  and (tostring | contains("Bearer ") | not)
' "$VENDOR_WORKFLOW" >/dev/null || {
  echo 'vendor-review workflow is missing its egress-deny/approved-review/credential-free contract' >&2
  exit 1
}

grep -Fq "'type':'session_budget_exceeded'" "$MOCK_TALON" \
  || { echo 'mock Talon does not emit the real error.type budget contract' >&2; exit 1; }
if grep -Fq "'code':'session_budget_exceeded'" "$MOCK_TALON"; then
  echo 'mock Talon still masks the real gateway schema by adding error.code' >&2
  exit 1
fi
for required in 'MOCK_TALON_DENY_PROVIDER' 'egress_tier_destination_disallowed' "rec['denial_code']"; do
  grep -Fq -- "$required" "$MOCK_TALON" \
    || { echo "mock Talon lacks vendor-review egress contract: $required" >&2; exit 1; }
done

for required in \
  'docker.n8n.io/n8nio/n8n:2.30.4' \
  '--network host' \
  'import:credentials' \
  'import:workflow' \
  'export:workflow --all' \
  'execute --id=' \
  'N8N_RESTRICT_FILE_ACCESS_TO=/demo' \
  'assert_clean_export' \
  'assert_mock_receipts' \
  'N8N_STAGED_BUDGET="0.00301"' \
  'TALON_SOURCE_COMMIT' \
  'stage_real_n8n_budget' \
  'restore_real_n8n_budget' \
  'validate-agent-policy.sh' \
  'canonical session max_cost is not 0.01'; do
  grep -Fq -- "$required" "$RUNNER" || { echo "n8n runner missing: $required" >&2; exit 1; }
done

for required in \
  'docker.n8n.io/n8nio/n8n:2.30.4' \
  'cases/vendor-contract-review' \
  'TALON_N8N_VENDOR_REVIEW_SESSION_ID' \
  'talonVendorReviewAuth1' \
  'import:credentials' \
  'export:workflow --all' \
  'MOCK_TALON_DENY_PROVIDER=openai' \
  'assert_mock_receipts' \
  'controlled_vendor_review' \
  'human-review boundary'; do
  grep -Fq -- "$required" "$VENDOR_RUNNER" \
    || { echo "vendor-review runner missing: $required" >&2; exit 1; }
done

if grep -Fq -- 'talon validate --dir' "$RUNNER"; then
  echo 'n8n runner depends on Talon directory validation unavailable in the released demo CLI' >&2
  exit 1
fi
grep -Fq -- 'talon validate --file "$POLICY_FILE"' "$VALIDATE_AGENT" \
  || { echo 'single-agent helper does not use the released Talon --file validation contract' >&2; exit 1; }

for required in \
  'allowed_providers: ["openai", "anthropic"]' \
  'default_action: deny' \
  'tier: confidential' \
  'allowed_providers: ["anthropic"]' \
  'input_scan: true' \
  'redact_input: true' \
  'vendor-contract-review-talon-key'; do
  grep -Fq -- "$required" "$VENDOR_POLICY" \
    || { echo "vendor-review policy missing: $required" >&2; exit 1; }
done
for required in \
  '--agent customer-support --agent coding-assistant --agent vendor-contract-review' \
  '--agent document-summary --agent vendor-contract-review' \
  'vendor-contract-review-talon-key' \
  'talon validate --dir' \
  'talon doctor'; do
  grep -Fq -- "$required" "$VENDOR_SEED" \
    || { echo "vendor-review seeding contract missing: $required" >&2; exit 1; }
done

for required in \
  'talon_supports_demo_audit' \
  "grep -Fq -- '--session'" \
  "grep -Fq -- 'signed-json'" \
  "grep -Fq -- '--file'" \
  'TALON_PINNED_COMMIT' \
  'git -C "$source" worktree add --detach' \
  'CGO_ENABLED=1 go build' \
  '.state/talon-audit-cli'; do
  grep -Fq -- "$required" "$AUDIT_RESOLVER" \
    || { echo "audit CLI resolver missing compatibility contract: $required" >&2; exit 1; }
done
for required in \
  'TALON_CLI_PROFILE:-runtime' \
  'resolve_talon_audit_bin' \
  'audit export --session' \
  'audit verify'; do
  grep -Fq -- "$required" "$WITH_TALON" \
    || { echo "Talon wrapper missing audit profile contract: $required" >&2; exit 1; }
done
for target in \
  present-copilot present-copilot-tech present-copilot-all demo-copilot-buyer demo-copilot-tech \
  present-n8n present-n8n-tech present-n8n-all demo-n8n-buyer demo-n8n-tech \
  present-n8n-vendor-review present-n8n-vendor-review-tech present-n8n-vendor-review-all \
  demo-n8n-vendor-review-buyer demo-n8n-vendor-review-tech; do
  make -n -C "$ROOT" "$target" | grep -Fq 'TALON_CLI_PROFILE=audit' \
    || { echo "$target does not select the audit-capable Talon CLI profile" >&2; exit 1; }
done

for required in \
  '.session_budget.limit' \
  '.session_budget.spent' \
  '.session_budget.estimate' \
  'signed session_budget {limit, spent, estimate}' \
  'The signed deny' \
  'record, not the presenter'; do
  grep -Fq -- "$required" "$PRESENTER" || { echo "n8n presenter missing signed budget proof: $required" >&2; exit 1; }
done

for required in \
  '.egress_decision.provider == "openai"' \
  '.egress_decision.provider == "anthropic"' \
  'input_pii_redacted' \
  'index("email")' \
  'index("iban")' \
  'all(.records[]; .session_id == $s)' \
  'Human review remains required' \
  'Direct provider calls or document'; do
  grep -Fq -- "$required" "$VENDOR_PRESENTER" \
    || { echo "vendor-review presenter missing signed control/boundary proof: $required" >&2; exit 1; }
done

for required in \
  'network_mode: host' \
  'N8N_LISTEN_ADDRESS: 127.0.0.1' \
  'TALON_N8N_GATEWAY_URL:' \
  'N8N_RESTRICT_FILE_ACCESS_TO: /demo'; do
  grep -Fq -- "$required" "$COMPOSE" || { echo "n8n compose missing: $required" >&2; exit 1; }
done

jq -e '
  .author.name and .author.email and .author.url
  and .location.support.ticket_editor.url == "assets/iframe.html"
  and any(.parameters[]; .name == "adapter_token" and .secure == true and (.scopes | index("header")))
' "$ZENDESK_MANIFEST" >/dev/null || {
  echo 'Zendesk manifest is missing author, ticket-editor, or secure-header settings' >&2
  exit 1
}
grep -Fq 'viewBox=' "$ZENDESK_ICON" || { echo 'Zendesk ticket-editor icon lacks a viewBox' >&2; exit 1; }

for required in \
  'offline-structure-and-secret-scan' \
  'authenticated-zcli-validation-and-package' \
  '@zendesk/zcli@$ZCLI_VERSION' \
  'apps:validate' \
  'apps:package' \
  'sha256sum' \
  'zipfile.ZipFile' \
  'testzip()' \
  'unsafe ZIP path' \
  'symbolic links are not allowed' \
  'talon-reply-assistant.offline.zip' \
  'talon-reply-assistant.zcli.zip'; do
  grep -Fq -- "$required" "$PACKAGE" || { echo "Zendesk package gate missing: $required" >&2; exit 1; }
done
if grep -Eq '(^|[[:space:]])unzip([[:space:]]|$)' "$PACKAGE"; then
  echo 'Zendesk package gate still depends on the optional unzip executable' >&2
  exit 1
fi
for required in \
  'operator-confirmed-ui-plus-talon-evidence' \
  'ZENDESK_SECURE_SETTING_CONFIRMED' \
  'ZENDESK_NEWEST_REQUESTER_COMMENT_CONFIRMED' \
  'ZENDESK_DRAFT_INSERTED_CONFIRMED' \
  'talon audit verify --file' \
  'zendesk-support-full-demo'; do
  grep -Fq -- "$required" "$INSTALLED" || { echo "Zendesk installed-app gate missing: $required" >&2; exit 1; }
done

for target in \
  n8n-validate real-n8n demo-n8n-buyer demo-n8n-tech \
  n8n-vendor-review-validate real-n8n-vendor-review demo-n8n-vendor-review-buyer demo-n8n-vendor-review-tech \
  zendesk-package zendesk-zcli-package verify-zendesk-installed; do
  make -n -C "$ROOT" "$target" >/dev/null \
    || { echo "Make target is not runnable: $target" >&2; exit 1; }
done

for required in 'record-latest-n8n-session.sh quarterly' 'record-latest-n8n-session.sh vendor-review'; do
  grep -Fq -- "$required" "$MAKEFILE" \
    || { echo "Makefile does not pin the latest successful n8n session: $required" >&2; exit 1; }
done

if find "$ROOT" -path '*/.state/*' -prune -o \
  \( -name '*credential*.json' -o -name 'zcli.apps.config.json' \) -print \
  | grep -v '^$' | grep -v 'quarterly-compliance-workflow.json' >/dev/null; then
  echo 'repository contains a generated credential/config artifact' >&2
  exit 1
fi

echo 'N8N AND ZENDESK COMPLETION CONTRACTS PASSED'
