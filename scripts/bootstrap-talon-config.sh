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
# Ship Talon's operator pricing table next to the config so served costs come
# from the real table instead of embedded defaults (the server resolves
# pricing/models.yaml relative to its working directory, like agents_dir).
if [[ -f "$TALON_REPO/pricing/models.yaml" ]]; then
  mkdir -p "$STAGE/pricing"
  cp "$TALON_REPO/pricing/models.yaml" "$STAGE/pricing/models.yaml"
fi
git -C "$TALON_REPO" rev-parse HEAD > "$STAGE/TALON_SOURCE_COMMIT"
PIN_FILE="$ROOT/TALON_PINNED_COMMIT"
if [[ -s "$PIN_FILE" ]] && [[ "$(cat "$STAGE/TALON_SOURCE_COMMIT")" != "$(cat "$PIN_FILE")" ]]; then
  echo "WARNING: TALON_REPO is at $(cat "$STAGE/TALON_SOURCE_COMMIT"); this demo is audited against $(cat "$PIN_FILE") (TALON_PINNED_COMMIT)" >&2
fi

# Shadow mode is a runtime override since Talon v1.9.3 (#368), run from the
# generated-config directory because agents_dir resolves against the server cwd:
#   (cd config/generated && talon serve --gateway --gateway-mode shadow --proxy-config ../mcp-proxy.example.yaml)
# No shadow copy of the YAML is generated any more. The previous approach
# (regex-editing the mode key) silently produced an enforce config named
# "shadow" because gateway.mode is nested, not top-level; do not resurrect it.

rm -rf "$OUT"
mkdir -p "$(dirname "$OUT")"
mv "$STAGE" "$OUT"
trap - EXIT

echo "Copied canonical Talon product-demo config to $OUT from $(cat "$OUT/TALON_SOURCE_COMMIT")"
echo "Serve (agents_dir is cwd-relative): (cd $OUT && talon serve --host 127.0.0.1 --port 8080 --gateway --proxy-config ../mcp-proxy.example.yaml)"
echo "Shadow demo: same command plus --gateway-mode shadow"
