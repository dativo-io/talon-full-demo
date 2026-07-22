#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

find_copilot() {
  if [[ -n "${COPILOT_BIN:-}" ]]; then
    [[ -x "$COPILOT_BIN" ]] || die "COPILOT_BIN is not executable: $COPILOT_BIN"
    printf '%s\n' "$COPILOT_BIN"
    return 0
  fi
  if command -v copilot >/dev/null 2>&1; then
    command -v copilot
    return 0
  fi
  if [[ -x "$HOME/.local/bin/copilot" ]]; then
    printf '%s\n' "$HOME/.local/bin/copilot"
    return 0
  fi
  return 1
}

COPILOT="$(find_copilot || true)"
if [[ -z "$COPILOT" ]]; then
  cat >&2 <<'MESSAGE'
ERROR: GitHub Copilot CLI is not installed or is not on PATH.

Install the official CLI with:
  make copilot-install

Then run:
  make real-copilot
MESSAGE
  exit 1
fi

version="$($COPILOT --version 2>&1 || true)"
[[ -n "$version" ]] || die "could not read Copilot CLI version from $COPILOT"

help="$($COPILOT --help 2>&1 || true)"
for flag in --additional-mcp-config --disable-builtin-mcps --allow-tool --deny-tool; do
  grep -q -- "$flag" <<<"$help" \
    || die "Copilot CLI at $COPILOT does not support $flag. Update it with: make copilot-install"
done

say "Using GitHub Copilot CLI: $version"
say "Binary: $COPILOT"

export PATH="$(dirname "$COPILOT"):$PATH"
exec bash "$ROOT/scripts/real-demo.sh" copilot
