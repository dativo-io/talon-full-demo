#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

stop_one() {
  local name="$1"
  local pidfile="$ROOT/.state/$name.pid"
  [[ -f "$pidfile" ]] || return 0

  local pid expected command
  IFS=$'\t' read -r pid expected < "$pidfile" || true
  if [[ ! "$pid" =~ ^[0-9]+$ ]] || [[ -z "$expected" ]]; then
    echo "invalid pid file for $name; removing it without signalling" >&2
    rm -f "$pidfile"
    return 0
  fi
  if ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$pidfile"
    return 0
  fi

  command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
  case "$command" in
    *"$expected"*) ;;
    *)
      echo "refusing to stop pid $pid for $name: command does not match $expected" >&2
      rm -f "$pidfile"
      return 1
      ;;
  esac

  kill -TERM "$pid"
  for _ in $(seq 1 50); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.1
  done
  if kill -0 "$pid" 2>/dev/null; then
    command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    case "$command" in
      *"$expected"*) kill -KILL "$pid" ;;
      *) echo "pid $pid changed identity during shutdown; not killing" >&2 ;;
    esac
  fi
  wait "$pid" 2>/dev/null || true
  rm -f "$pidfile"
}

status=0
for name in zendesk-adapter copilot-shim release-mcp talon-mcp talon-gateway; do
  stop_one "$name" || status=1
done
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  N8N_ENCRYPTION_KEY="${N8N_ENCRYPTION_KEY:-stop-only-placeholder}" \
    docker compose -f "$ROOT/integrations/n8n/compose.yaml" down || status=1
fi
exit "$status"
