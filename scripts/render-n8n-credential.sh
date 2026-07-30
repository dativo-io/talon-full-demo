#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/.state/n8n-config/talon-document-summary-credential.json}"

external_document_key="${TALON_DOCUMENT_SUMMARY_KEY:-}"
external_generic_key="${TALON_N8N_CREDENTIAL_KEY:-}"
if [[ -f "$ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.env"
fi
[[ -n "$external_document_key" ]] && TALON_DOCUMENT_SUMMARY_KEY="$external_document_key"
[[ -n "$external_generic_key" ]] && TALON_N8N_CREDENTIAL_KEY="$external_generic_key"

credential_key="${TALON_N8N_CREDENTIAL_KEY:-${TALON_DOCUMENT_SUMMARY_KEY:-}}"
credential_id="${TALON_N8N_CREDENTIAL_ID:-talonHeaderAuth1}"
credential_name="${TALON_N8N_CREDENTIAL_NAME:-Talon document-summary}"
[[ -n "$credential_key" ]] || {
  echo 'ERROR: no n8n Talon credential key; set TALON_N8N_CREDENTIAL_KEY or TALON_DOCUMENT_SUMMARY_KEY' >&2
  exit 1
}

command -v jq >/dev/null 2>&1 || { echo 'ERROR: missing command: jq' >&2; exit 1; }
install -d -m 0700 "$(dirname "$OUT")"
umask 077
jq -n \
  --arg id "$credential_id" \
  --arg name "$credential_name" \
  --arg value "Bearer $credential_key" \
  '[{
    id: $id,
    name: $name,
    type: "httpHeaderAuth",
    data: {name: "Authorization", value: $value}
  }]' >"$OUT"
chmod 0600 "$OUT"
printf '%s\n' "$OUT"
