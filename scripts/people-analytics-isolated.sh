#!/usr/bin/env bash
# Synthetic isolated HR demo. Talon is a real binary; Docker is the network boundary.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CASE="$ROOT/cases/people-analytics-copilot"
COMPOSE="$CASE/compose.isolated.yaml"
ENV_FILE="$CASE/.state/isolated.env"
ACTION="${1:-help}"
need() { command -v "$1" >/dev/null || { echo "Missing $1" >&2; exit 1; }; }
need docker
need openssl
TALON_PATH="${HR_DEMO_TALON_BIN:-$(command -v talon || true)}"
if [[ -z "$TALON_PATH" || ! -x "$TALON_PATH" ]]; then
  echo "Install a Talon binary or set HR_DEMO_TALON_BIN=/absolute/path/to/talon" >&2; exit 1
fi
export HR_DEMO_TALON_BIN="$TALON_PATH"
mkdir -p "$CASE/.state"
if [[ ! -f "$ENV_FILE" ]]; then
  umask 077
  {
    printf 'HR_DEMO_SECRETS_KEY=%s\n' "$(openssl rand -hex 32)"
    printf 'HR_DEMO_SIGNING_KEY=%s\n' "$(openssl rand -hex 32)"
    printf 'HR_DEMO_ADMIN_KEY=%s\n' "$(openssl rand -hex 24)"
  } > "$ENV_FILE"
fi
chmod 600 "$ENV_FILE"
dc() { docker compose -f "$COMPOSE" --env-file "$ENV_FILE" "$@"; }
export HR_DEMO_OPENAI_KEY="${HR_DEMO_OPENAI_KEY:-${OPENAI_API_KEY:-}}"
case "$ACTION" in
  up)
    export HR_DEMO_AI_MODE=guided
    dc up --build -d seed hr-server dashboard talon-init talon-mcp ui
    echo "Guided dashboard: http://127.0.0.1:8501"
    echo "Next: bash scripts/people-analytics-isolated.sh verify"
    ;;
  live)
    [[ -n "$HR_DEMO_OPENAI_KEY" ]] || { echo "Set OPENAI_API_KEY for a REAL model" >&2; exit 1; }
    export HR_DEMO_AI_MODE=live
    dc --profile live up --build --force-recreate -d talon-init talon-mcp talon-gateway ui
    echo "External provider is enabled through Talon; billable calls possible."
    echo "Live structured request/response metadata: authenticated proof console -> trace logs."
    echo "Optional full synthetic-only payload preview: HR_DEMO_TRACE_PAYLOADS=1 bash scripts/people-analytics-isolated.sh live"
    echo "Live dashboard: http://127.0.0.1:8501"
    ;;
  verify)
    for i in {1..40}; do
      if dc exec -T ui python3 -c 'from urllib.request import urlopen; urlopen("http://talon-mcp:8080/health", timeout=2)' >/dev/null 2>&1; then break; fi
      sleep 1
    done
    echo "== BEFORE: privileged backend can perform direct employee export =="
    dc exec -T hr-server python3 verify_isolation.py baseline
    echo "== AFTER: restricted app can reach only safe dashboard + Talon =="
    dc exec -T ui python3 verify_isolation.py app
    dc exec -T hr-server python3 verify_isolation.py backend-counts
    echo "== SIGNED EVIDENCE: independently verify the same isolated session =="
    dc exec -T talon-mcp sh -ec 'talon audit export --format signed-json --session hr-demo-isolated-boundary --output /tmp/hr-boundary-evidence.json >/dev/null; talon audit verify --file /tmp/hr-boundary-evidence.json'
    echo "PASS: before/after HR isolation, Talon allow/deny and signed evidence"
    ;;
  presenter)
    echo "Starting separate host-only presenter UI. This has Docker operator authority;"
    echo "it is not inside the isolated AI workload and requires a one-time access token."
    exec python3 "$ROOT/scripts/people_analytics_presenter.py" --serve
    ;;
  logs) dc logs --tail 100 hr-server dashboard talon-mcp ui ;;
  down) dc --profile live down ;;
  reset)
    echo "WARNING: deleting synthetic DuckDB and demo Talon state volumes"
    dc --profile live down -v
    ;;
  *) echo "Usage: bash scripts/people-analytics-isolated.sh up|presenter|verify|live|logs|down|reset" ;;
esac
