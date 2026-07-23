#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${TALON_CLI_PROFILE:-runtime}"

case "$PROFILE" in
  runtime)
    # shellcheck disable=SC1091
    source "$ROOT/scripts/resolve-talon.sh"
    resolved="$(resolve_talon_bin "$ROOT" || true)"
    ;;
  audit)
    # shellcheck disable=SC1091
    source "$ROOT/scripts/resolve-talon-audit.sh"
    resolved="$(resolve_talon_audit_bin "$ROOT" || true)"
    ;;
  *)
    echo "ERROR: unknown TALON_CLI_PROFILE: $PROFILE" >&2
    exit 2
    ;;
esac

if [[ -z "$resolved" ]]; then
  if [[ "$PROFILE" == audit ]]; then
    cat >&2 <<'EOF'
ERROR: an audit-capable Talon CLI could not be resolved.

The presenter requires audit export --session, signed-json, and audit verify
--file. Set TALON_AUDIT_BIN to a compatible executable, or keep a sibling
../talon checkout so the pinned CLI can be built and cached automatically.
EOF
  else
    cat >&2 <<'EOF'
ERROR: Talon CLI could not be resolved.

Set TALON_BIN to the executable path, add Talon to PATH, or start the
repository-owned real stack so the CLI can be recovered from its PID file.
EOF
  fi
  exit 1
fi

shim_dir="$ROOT/.state/talon-cli-bin"
install -d -m 0700 "$shim_dir"
ln -sfn "$resolved" "$shim_dir/talon"
export PATH="$shim_dir:$PATH"
export TALON_BIN="$resolved"

exec "$@"
