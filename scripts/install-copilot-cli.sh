#!/usr/bin/env bash
set -euo pipefail

# Explicit, opt-in installer for GitHub Copilot CLI. This follows GitHub's
# documented macOS/Linux install-script path, but downloads the installer to a
# temporary file before executing it so network and script failures are visible.

PREFIX="${COPILOT_INSTALL_PREFIX:-$HOME/.local}"
INSTALL_URL="https://gh.io/copilot-install"

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

if command -v copilot >/dev/null 2>&1; then
  say "GitHub Copilot CLI is already installed: $(command -v copilot)"
  copilot --version
  exit 0
fi

command -v curl >/dev/null 2>&1 || die "curl is required"
command -v mktemp >/dev/null 2>&1 || die "mktemp is required"

case "$(uname -s)" in
  Linux|Darwin) ;;
  *) die "this helper supports Linux and macOS; use GitHub's platform-specific installation instructions" ;;
esac

installer="$(mktemp "${TMPDIR:-/tmp}/copilot-install.XXXXXX")"
trap 'rm -f "$installer"' EXIT

say "Downloading the official GitHub Copilot CLI installer..."
curl --proto '=https' --tlsv1.2 --fail --silent --show-error --location \
  "$INSTALL_URL" --output "$installer"
[[ -s "$installer" ]] || die "downloaded installer is empty"

say "Installing GitHub Copilot CLI under $PREFIX/bin..."
PREFIX="$PREFIX" bash "$installer"

binary="$PREFIX/bin/copilot"
if [[ ! -x "$binary" ]]; then
  if command -v copilot >/dev/null 2>&1; then
    binary="$(command -v copilot)"
  else
    die "installer completed but no copilot executable was found"
  fi
fi

say
say "Installed: $binary"
"$binary" --version
say
say "Next: make real-copilot"
say "The demo uses Copilot CLI in BYOK offline mode, so a GitHub login is not required for its model/MCP path."
