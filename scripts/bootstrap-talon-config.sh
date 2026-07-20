#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TALON_REPO="${TALON_REPO:-${1:-$ROOT/../talon}}"
SRC="$TALON_REPO/examples/product-demo"
OUT="$ROOT/config/generated"

for path in "$SRC/talon.config.yaml" "$SRC/agents"; do
  [[ -e "$path" ]] || { echo "missing canonical Talon demo source: $path" >&2; exit 1; }
done
[[ -d "$TALON_REPO/.git" ]] || { echo "TALON_REPO is not a Git checkout: $TALON_REPO" >&2; exit 1; }

rm -rf "$OUT"
mkdir -p "$OUT"
cp "$SRC/talon.config.yaml" "$OUT/talon.config.yaml"
cp -R "$SRC/agents" "$OUT/agents"
cp "$OUT/talon.config.yaml" "$OUT/talon.shadow.config.yaml"

git -C "$TALON_REPO" rev-parse HEAD > "$OUT/TALON_SOURCE_COMMIT"
python3 - "$OUT/talon.shadow.config.yaml" <<'PYCFG'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text()
updated, count = re.subn(r'(?m)^mode:\s*[^#\n]+', 'mode: shadow', text, count=1)
if count != 1:
    raise SystemExit('could not find exactly one top-level gateway mode field')
path.write_text(updated)
PYCFG

echo "Copied canonical Talon product-demo config to $OUT from $(cat "$OUT/TALON_SOURCE_COMMIT")"
