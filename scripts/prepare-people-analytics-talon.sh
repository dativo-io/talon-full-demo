#!/usr/bin/env bash
# Build the current Talon main for the local People Analytics demo.
# Keep all source/build artifacts outside the case's vault and evidence state.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/.state/talon-source"
BINDIR="$ROOT/.state/talon-bin"
command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
command -v go >/dev/null || { echo "Go is required to build Talon main" >&2; exit 1; }
[[ "$(uname -s)" == Linux ]] || { echo "Build on the Linux Docker host, not macOS" >&2; exit 1; }

mkdir -p "$BINDIR"
if [[ -d "$SOURCE/.git" ]]; then
  # Keep demo source independent of the developer's main Talon worktree.
  git -C "$SOURCE" fetch --no-tags origin main
else
  [[ ! -e "$SOURCE" ]] || { echo "Not a Git checkout: $SOURCE" >&2; exit 1; }
  git clone --branch main --single-branch https://github.com/dativo-io/talon.git "$SOURCE"
fi
# Detached snapshot of main fetched for THIS run, not a fixed commit.
git -C "$SOURCE" checkout --detach "$(git -C "$SOURCE" rev-parse refs/remotes/origin/main)"
RESOLVED_SHA="$(git -C "$SOURCE" rev-parse HEAD)"
echo "Building current dativo-io/talon main: $RESOLVED_SHA"
go -C "$SOURCE" build -o "$BINDIR/talon" ./cmd/talon
HR_DEMO_TALON_SOURCE_DIR="$SOURCE" bash "$ROOT/scripts/check-people-analytics-talon-binary.sh" "$BINDIR/talon"
printf '\nUse this binary in your current shell (no state reset):\n'
printf 'export HR_DEMO_TALON_BIN=%q\n' "$BINDIR/talon"
