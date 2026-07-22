#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/.state/n8n-config/talon-document-summary-credential.json}"

external_key="${TALON_DOCUMENT_SUMMARY_KEY:-}"
if [[ -f "$ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.env"
fi
[[ -n "$external_key" ]] && TALON_DOCUMENT_SUMMARY_KEY="$external_key"
[[ -n "${TALON_DOCUMENT_SUMMARY_KEY:-}" ]] || {
  echo 'ERROR: TALON_DOCUMENT_SUMMARY_KEY is empty; run make env or make real-prepare' >&2
  exit 1
}

command -v jq >/dev/null 2>&1 || { echo 'ERROR: missing command: jq' >&2; exit 1; }
install -d -m 0700 "$(dirname "$OUT")"
umask 077
jq -n \
  --arg value "Bearer $TALON_DOCUMENT_SUMMARY_KEY" \
  '[{
    id: "talonHeaderAuth1",
    name: "Talon document-summary",
    type: "httpHeaderAuth",
    data: {name: "Authorization", value: $value}
  }]' >"$OUT"
chmod 0600 "$OUT"
printf '%s\n' "$OUT"
