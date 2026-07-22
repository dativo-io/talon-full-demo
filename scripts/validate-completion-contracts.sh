#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORKFLOW="$ROOT/integrations/n8n/quarterly-compliance-workflow.json"
RUNNER="$ROOT/scripts/n8n-workflow.sh"
COMPOSE="$ROOT/integrations/n8n/compose.yaml"
PACKAGE="$ROOT/scripts/package-zendesk-app.sh"
INSTALLED="$ROOT/scripts/verify-zendesk-installed.sh"
ZENDESK_MANIFEST="$ROOT/integrations/zendesk-app/manifest.json"
ZENDESK_ICON="$ROOT/integrations/zendesk-app/assets/icon_ticket_editor.svg"

for file in "$WORKFLOW" "$RUNNER" "$COMPOSE" "$PACKAGE" "$INSTALLED" "$ZENDESK_MANIFEST" "$ZENDESK_ICON"; do
  [[ -s "$file" ]] || { echo "missing completion artifact: $file" >&2; exit 1; }
done

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
      and (.parameters | tostring | contains("session_budget_exceeded")))
  and (tostring | contains("Bearer ") | not)
' "$WORKFLOW" >/dev/null || {
  echo 'n8n workflow is missing its sequential budget/evidence/credential-free contract' >&2
  exit 1
}

for required in \
  'docker.n8n.io/n8nio/n8n:2.30.4' \
  '--network host' \
  'import:credentials' \
  'import:workflow' \
  'export:workflow --all' \
  'execute --id=' \
  'N8N_RESTRICT_FILE_ACCESS_TO=/demo' \
  'assert_clean_export' \
  'assert_mock_receipts'; do
  grep -Fq -- "$required" "$RUNNER" || { echo "n8n runner missing: $required" >&2; exit 1; }
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
  'talon-reply-assistant.offline.zip' \
  'talon-reply-assistant.zcli.zip'; do
  grep -Fq -- "$required" "$PACKAGE" || { echo "Zendesk package gate missing: $required" >&2; exit 1; }
done
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
  zendesk-package zendesk-zcli-package verify-zendesk-installed; do
  make -n -C "$ROOT" "$target" >/dev/null \
    || { echo "Make target is not runnable: $target" >&2; exit 1; }
done

if find "$ROOT" -path '*/.state/*' -prune -o \
  \( -name '*credential*.json' -o -name 'zcli.apps.config.json' \) -print \
  | grep -v '^$' | grep -v 'quarterly-compliance-workflow.json' >/dev/null; then
  echo 'repository contains a generated credential/config artifact' >&2
  exit 1
fi

echo 'N8N AND ZENDESK COMPLETION CONTRACTS PASSED'
