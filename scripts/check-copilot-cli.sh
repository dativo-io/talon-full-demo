#!/usr/bin/env bash
set -euo pipefail

COPILOT="${1:-}"
[[ -n "$COPILOT" ]] || { echo 'usage: check-copilot-cli.sh /path/to/copilot' >&2; exit 2; }
[[ -x "$COPILOT" ]] || { echo "Copilot binary is not executable: $COPILOT" >&2; exit 1; }

version="$($COPILOT --version 2>&1 || true)"
[[ -n "$version" ]] || { echo "could not read Copilot CLI version from $COPILOT" >&2; exit 1; }

# GitHub documents `copilot help` as the complete command reference. Some
# releases expose only a subset through `copilot --help`, so prefer the full
# form and fall back only for older binaries.
help="$($COPILOT help 2>&1 || true)"
if [[ -z "$help" ]]; then
  help="$($COPILOT --help 2>&1 || true)"
fi

# Gate only capabilities that affect correctness. Banner/color switches are
# cosmetic and intentionally excluded because current stable builds may omit
# them even when the functional programmatic interface is present.
for flag in --prompt --no-ask-user --additional-mcp-config --disable-builtin-mcps --allow-tool --deny-tool --no-custom-instructions; do
  grep -q -- "$flag" <<<"$help" || {
    echo "Copilot CLI at $COPILOT does not report required functional flag $flag." >&2
    echo "Inspect its complete interface with: $COPILOT help" >&2
    exit 1
  }
done

printf '%s\n' "$version"
