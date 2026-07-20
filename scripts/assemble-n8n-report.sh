#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/.state/n8n-output"
# Per-run output filename so a rehearsal's report cannot be confused with an
# earlier run's (run id from scripts/new-demo-run.sh via make preflight).
if [[ -f "$ROOT/.state/demo-run.env" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.state/demo-run.env"
fi
if [[ -n "${TALON_DEMO_RUN_ID:-}" ]]; then
  TARGET="$OUT/quarterly-summary.partial.${TALON_DEMO_RUN_ID}.md"
else
  TARGET="$OUT/quarterly-summary.partial.md"
fi
[[ -d "$OUT" ]] || { echo "missing n8n output directory: $OUT" >&2; exit 1; }

mapfile -d '' files < <(find "$OUT" -maxdepth 1 -type f -name '*.summary.md' -print0 | sort -z)
(( ${#files[@]} > 0 )) || { echo 'no completed n8n section files' >&2; exit 1; }
{
  printf '# Quarterly compliance summary\n\n_Synthetic demonstration data._\n\n'
  for file in "${files[@]}"; do
    cat "$file"
    printf '\n'
  done
} > "$TARGET"
printf '%s\n' "$TARGET"
