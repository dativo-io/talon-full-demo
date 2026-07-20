#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/.state/n8n-output"
TARGET="$OUT/quarterly-summary.partial.md"
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
