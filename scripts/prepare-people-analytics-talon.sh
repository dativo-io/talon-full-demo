#!/usr/bin/env bash
# Build the exact governed-MCP Talon source used by the People Analytics case.
# Does not touch the demo's .env, vault, agent policy, or signed evidence.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPECTED="$(tr -d '[:space:]' < "$ROOT/cases/people-analytics-copilot/TALON_GOVERNED_MCP_COMMIT")"
[[ "$EXPECTED" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid pinned Talon source SHA" >&2; exit 1; }
command -v go >/dev/null || { echo "Go is required to compile the unreleased governed-MCP Talon version" >&2; exit 1; }
command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
[[ "$(uname -s)" == Linux ]] || { echo "Build this binary on the Linux Docker host (not macOS)" >&2; exit 1; }

SOURCE="$ROOT/.state/talon-source"
BINDIR="$ROOT/.state/talon-bin"
mkdir -p "$BINDIR"
if [[ -d "$SOURCE/.git" ]]; then
  # Reuse only our own demo source checkout, not an arbitrary user's Talon tree.
  git -C "$SOURCE" fetch --no-tags origin "$EXPECTED"
else
  [[ ! -e "$SOURCE" ]] || { echo "Source path exists but is not a Git checkout: $SOURCE" >&2; exit 1; }
  git clone https://github.com/dativo-io/talon.git "$SOURCE"
fi
git -C "$SOURCE" checkout --detach "$EXPECTED"
ACTUAL="$(git -C "$SOURCE" rev-parse HEAD)"
[[ "$ACTUAL" == "$EXPECTED" ]] || { echo "Source SHA does not match pinned candidate" >&2; exit 1; }
go -C "$SOURCE" build -o "$BINDIR/talon" ./cmd/talon
"$ROOT/scripts/check-people-analytics-talon-binary.sh" "$BINDIR/talon"
printf '\nUse this binary in your current shell (do not reset existing keys/state):\n'
printf 'export HR_DEMO_TALON_BIN=%q\n' "$BINDIR/talon"
