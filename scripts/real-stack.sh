#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
MARKER="$STATE/real-demo-started.env"
IMPL="$ROOT/scripts/real-demo.sh"
STARTING=0

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

pid_owned() {
  local name="$1" port="$2"
  local pidfile="$STATE/$name.pid"
  [[ -f "$pidfile" ]] || return 1
  local pid command_line
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  command_line="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  [[ "$command_line" == *"talon serve"* && "$command_line" == *"--port $port"* ]]
}

port_open() {
  python3 - "$1" <<'PYPORT'
import socket
import sys

port = int(sys.argv[1])
with socket.socket() as sock:
    sock.settimeout(0.3)
    raise SystemExit(0 if sock.connect_ex(("127.0.0.1", port)) == 0 else 1)
PYPORT
}

show_port_owner() {
  local port="$1"
  say "Inspect the listener with:"
  say "  sudo ss -ltnp 'sport = :$port'"
  if command -v ss >/dev/null 2>&1; then
    ss -ltnp "sport = :$port" 2>/dev/null || true
  fi
}

require_free_or_owned() {
  local name="$1" port="$2"
  if ! port_open "$port"; then
    return 0
  fi
  if pid_owned "$name" "$port"; then
    return 0
  fi

  printf 'ERROR: port %s is already in use by a process not owned by this demo.\n' "$port" >&2
  show_port_owner "$port" >&2
  printf 'Stop the stale process, then rerun make real-start. The demo will not adopt an unknown service.\n' >&2
  return 1
}

check_http() {
  local label="$1" url="$2"
  curl --fail --silent --max-time 2 "$url" >/dev/null 2>&1 \
    || die "$label is not healthy at $url; run make real-status and inspect .state/logs"
}

check_tcp() {
  local label="$1" port="$2"
  port_open "$port" || die "$label is not listening on 127.0.0.1:$port; run make real-status and inspect .state/logs"
}

cleanup_failed_start() {
  STARTING=0
  say "Start failed; stopping services started by this repository..." >&2
  bash "$IMPL" stop >/dev/null 2>&1 || true
  rm -f "$MARKER"
}

cleanup_on_exit() {
  local rc=$?
  if [[ "$rc" -ne 0 && "$STARTING" -eq 1 ]]; then
    cleanup_failed_start
  fi
}
trap cleanup_on_exit EXIT

start_stack() {
  STARTING=1
  rm -f "$MARKER"

  # Check both Talon ports before starting either process. This prevents a
  # gateway-only partial start when an older MCP process still owns :8081.
  require_free_or_owned talon-gateway 8080
  require_free_or_owned talon-mcp-proxy 8081

  bash "$IMPL" start

  [[ -f "$STATE/demo-run.env" ]] || die "start did not create .state/demo-run.env"

  check_http "Talon gateway" "http://127.0.0.1:8080/health"
  check_http "Talon MCP proxy" "http://127.0.0.1:8081/health"
  check_http "Zendesk adapter" "http://127.0.0.1:8443/health"
  check_http "Release MCP" "http://127.0.0.1:8090/health"
  check_tcp "Copilot shim" 8079

  {
    printf 'REAL_DEMO_STARTED_AT=%q\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } >"$MARKER"
  chmod 0600 "$MARKER"
  STARTING=0

  say "Full real-demo stack is ready. Next: make real-smoke"
}

smoke_case() {
  [[ -f "$MARKER" ]] || die "the full stack was not started successfully; run make real-start"
  [[ -f "$STATE/demo-run.env" ]] || die "missing run identity; run make real-start"

  check_http "Talon gateway" "http://127.0.0.1:8080/health"
  check_http "Talon MCP proxy" "http://127.0.0.1:8081/health"
  check_http "Zendesk adapter" "http://127.0.0.1:8443/health"
  check_http "Release MCP" "http://127.0.0.1:8090/health"
  check_tcp "Copilot shim" 8079

  bash "$IMPL" smoke
}

stop_stack() {
  set +e
  bash "$IMPL" stop
  local rc=$?
  set -e
  rm -f "$MARKER"
  exit "$rc"
}

case "${1:-help}" in
  start) start_stack ;;
  smoke) smoke_case ;;
  stop) stop_stack ;;
  *)
    cat >&2 <<'USAGE'
Usage: scripts/real-stack.sh start|smoke|stop
USAGE
    exit 2
    ;;
esac
