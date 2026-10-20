#!/usr/bin/env bash
set -euo pipefail

# Adapter into Talon's canonical OpenShell showcase; no second Talon gateway,
# separate evidence store or demo-owned action governance implementation.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state/openshell"
COMMAND="${1:-help}"
die() { echo "ERROR (OpenShell demo): $*" >&2; exit 1; }

if [[ "$COMMAND" == "help" ]]; then
  echo 'Usage: real-openshell.sh prepare|start|status|run|approval-status|approve|reject|validate|stop'
  exit 0
fi

# Same .env as all other Full Demo cases, retaining an explicit command-line
# opt-in when the file was generated before OpenShell support existed.
external_enabled="${TALON_OPENSHELL_ENABLED:-}"
[[ ! -f "$ROOT/.env" ]] || source "$ROOT/.env"
[[ -z "$external_enabled" ]] || TALON_OPENSHELL_ENABLED="$external_enabled"
: "${TALON_OPENSHELL_ENABLED:=0}"
[[ "$TALON_OPENSHELL_ENABLED" == 0 || "$TALON_OPENSHELL_ENABLED" == 1 ]] \
  || die 'TALON_OPENSHELL_ENABLED must be 0 or 1'
if [[ "$TALON_OPENSHELL_ENABLED" != 1 && "$COMMAND" != "validate" ]]; then
  if [[ "$COMMAND" == stop || "$COMMAND" == status ]]; then
    echo 'OpenShell case disabled'; exit 0
  fi
  die 'OpenShell is opt-in: set TALON_OPENSHELL_ENABLED=1 and rerun make real-prepare'
fi

TALON_REPO="${TALON_REPO:-$ROOT/../talon}"
RUNNER="${TALON_OPENSHELL_SHOWCASE_RUNNER:-$TALON_REPO/examples/openshell/showcase/demo.sh}"
[[ -f "$RUNNER" ]] || die "canonical Talon showcase runner missing: $RUNNER. This is a main-repo prerequisite."
[[ -d "$TALON_REPO/.git" ]] || die "TALON_REPO must be a checkout: $TALON_REPO"
# PR #501 merged at this commit. Older builds must never pass by accident.
git -C "$TALON_REPO" merge-base --is-ancestor da61c47866a3d6aea787c762360f62f6b99089a2 HEAD \
  || die 'Talon checkout predates merged OpenShell PR #501'
if [[ "$COMMAND" != validate ]]; then
  command -v talon >/dev/null || die 'Talon CLI unavailable'
  talon audit list --help 2>&1 | grep -Fq -- '--runtime-ref' \
    || die 'Installed Talon CLI predates OpenShell runtime evidence support'
fi

export TALON_SHOWCASE_EMBEDDED=1
export TALON_SHOWCASE_CONFIG_DIR="$ROOT/config/generated"
export TALON_SHOWCASE_TALON_DATA_DIR="${TALON_DATA_DIR:-$ROOT/.state/talon}"
export TALON_SHOWCASE_RUN_DIR="$STATE"
export TALON_SHOWCASE_TALON_URL="${TALON_GATEWAY:-http://127.0.0.1:8080}"
export TALON_SHOWCASE_AGENT=sandboxed-support
export TALON_SHOWCASE_PROVIDER_MODE="${TALON_OPENSHELL_PROVIDER_MODE:-mock}"
export TALON_SHOWCASE_TALON_BIN="${TALON_BIN:-$(command -v talon || true)}"
mkdir -p "$STATE"
chmod 0700 "$STATE"

load_latest() {
  [[ -s "$STATE/latest.env" ]] || die 'No completed/active OpenShell run; run make real-openshell'
  source "$STATE/latest.env"
  [[ "${TALON_SHOWCASE_SESSION:-}" =~ ^openshell-[A-Za-z0-9-]+$ ]] || die 'invalid last-run session'
  export TALON_SHOWCASE_SESSION TALON_SHOWCASE_OPERATION_PREFIX
}

case "$COMMAND" in
  prepare)
    [[ -f "$TALON_SHOWCASE_CONFIG_DIR/talon.config.yaml" ]] || die 'canonical configuration has not been bootstrapped'
    bash "$RUNNER" prepare ;;
  start)
    [[ -s "$ROOT/.state/demo-run.env" ]] || die 'shared run identity missing'
    curl -fsS --max-time 2 "$TALON_SHOWCASE_TALON_URL/health" >/dev/null || die 'shared Talon gateway unavailable'
    bash "$RUNNER" start ;;
  status|validate|stop)
    bash "$RUNNER" "$COMMAND" ;;
  run)
    [[ -s "$ROOT/.state/real-demo-started.env" && -s "$ROOT/.state/demo-run.env" ]] \
      || die 'run make real-start before running the OpenShell case'
    source "$ROOT/.state/demo-run.env"
    nonce="$(openssl rand -hex 5)"
    export TALON_SHOWCASE_SESSION="openshell-$TALON_DEMO_RUN_ID-$nonce"
    export TALON_SHOWCASE_OPERATION_PREFIX="openshell-refund-$TALON_DEMO_RUN_ID-$nonce"
    export TALON_SHOWCASE_RUN_START="${TALON_RUN_START_RFC3339:-}"
    ( umask 077
      printf 'export TALON_SHOWCASE_SESSION=%q\n' "$TALON_SHOWCASE_SESSION"
      printf 'export TALON_SHOWCASE_OPERATION_PREFIX=%q\n' "$TALON_SHOWCASE_OPERATION_PREFIX"
    ) > "$STATE/latest.env.tmp"
    chmod 0600 "$STATE/latest.env.tmp"
    mv "$STATE/latest.env.tmp" "$STATE/latest.env"
    bash "$RUNNER" run ;;
  approval-status|approve|reject)
    load_latest
    bash "$RUNNER" "$COMMAND" ;;
  *) die "Unknown command: $COMMAND" ;;
esac
