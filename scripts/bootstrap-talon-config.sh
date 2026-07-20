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

# Stage into a temp dir and move into place at the end so a failure can never
# leave a partially populated config/generated behind (atomic publish).
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/talon-bootstrap.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT

cp "$SRC/talon.config.yaml" "$STAGE/talon.config.yaml"
cp -R "$SRC/agents" "$STAGE/agents"
git -C "$TALON_REPO" rev-parse HEAD > "$STAGE/TALON_SOURCE_COMMIT"

# Shadow mode is a runtime override since Talon v1.9.3 (#368):
#   talon serve --gateway --gateway-mode shadow --config config/generated/talon.config.yaml
# No shadow copy of the YAML is generated any more. The previous approach
# (regex-editing the mode key) silently produced an enforce config named
# "shadow" because gateway.mode is nested, not top-level; do not resurrect it.

rm -rf "$OUT"
mkdir -p "$(dirname "$OUT")"
mv "$STAGE" "$OUT"
trap - EXIT

echo "Copied canonical Talon product-demo config to $OUT from $(cat "$OUT/TALON_SOURCE_COMMIT")"
echo "Shadow demo: talon serve --gateway --gateway-mode shadow --config $OUT/talon.config.yaml"
