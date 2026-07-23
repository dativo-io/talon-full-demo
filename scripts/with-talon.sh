#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/resolve-talon.sh"

resolved="$(resolve_talon_bin "$ROOT" || true)"
if [[ -z "$resolved" ]]; then
  cat >&2 <<'EOF'
ERROR: Talon CLI could not be resolved.

Set TALON_BIN to the executable path, add Talon to PATH, or start the
repository-owned real stack so the CLI can be recovered from its PID file.
EOF
  exit 1
fi

shim_dir="$ROOT/.state/talon-cli-bin"
install -d -m 0700 "$shim_dir"
ln -sfn "$resolved" "$shim_dir/talon"
export PATH="$shim_dir:$PATH"
export TALON_BIN="$resolved"

exec "$@"
