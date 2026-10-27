#!/usr/bin/env bash
# Live People Analytics rehearsal: visible infra -> editable policy -> Talon -> one app.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CASE="$ROOT/cases/people-analytics-copilot"
COMPOSE="$CASE/compose.isolated.yaml"
ENV_FILE="$CASE/.state/isolated.env"
POLICY_DIR="$CASE/.state/policy"
ACTION="${1:-help}"
need() { command -v "$1" >/dev/null || { echo "Missing $1" >&2; exit 1; }; }
need docker
need openssl
TALON_PATH="${HR_DEMO_TALON_BIN:-$(command -v talon || true)}"
if [[ -z "$TALON_PATH" || ! -x "$TALON_PATH" ]]; then
  echo "Install Talon or set HR_DEMO_TALON_BIN=/absolute/path/to/talon" >&2; exit 1
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
# Never persist provider credentials in YAML, shell history or .state/isolated.env.
export HR_DEMO_OPENAI_KEY="${HR_DEMO_OPENAI_KEY:-${OPENAI_API_KEY:-}}"
make_config() {
  mkdir -p "$POLICY_DIR"
  for name in agent.talon.yaml proxy.isolated.talon.yaml gateway.talon.yaml; do
    if [[ ! -f "$POLICY_DIR/$name" ]]; then cp "$CASE/$name" "$POLICY_DIR/$name"; fi
  done
  echo "EDITABLE, untracked Talon policy: $POLICY_DIR"
  echo "Edit these YAML files; then run: bash scripts/people-analytics-isolated.sh talon"
}
apply_config() {
  for name in agent.talon.yaml proxy.isolated.talon.yaml gateway.talon.yaml; do
    [[ -f "$POLICY_DIR/$name" ]] || { echo "Missing $POLICY_DIR/$name; run 'config' first" >&2; return 1; }
  done
  # Foreground Talon scaffold + validate. Failed validation prevents any restart.
  dc run --rm --no-deps talon-init
  dc up --no-deps -d --force-recreate talon-mcp
  if [[ -n "$(dc --profile live ps -q talon-gateway)" || -n "$HR_DEMO_OPENAI_KEY" ]]; then
    dc --profile live up --no-deps -d --force-recreate talon-gateway
  fi
}
case "$ACTION" in
  infra)
    dc up --build -d seed hr-server dashboard
    dc exec -T hr-server python3 verify_isolation.py warehouse-info ;;
  config) make_config ;;
  talon)
    apply_config
    echo "Inspect Talon stdout: bash scripts/people-analytics-isolated.sh logs" ;;
  app)
    if [[ -n "$(dc --profile live ps -q talon-gateway)" ]]; then
      export HR_DEMO_AI_MODE=live
    else
      export HR_DEMO_AI_MODE=guided
      echo "GUIDED: no actual model inference. Export OPENAI_API_KEY before 'talon' for LIVE." >&2
    fi
    dc up --no-deps --build -d --force-recreate ui
    echo "Workforce application: http://127.0.0.1:8501" ;;
  reapply)
    apply_config
    echo "Policy reactivated; repeat the SAME dashboard SQL request." ;;
  up)
    dc up --build -d seed hr-server dashboard
    make_config
    apply_config
    export HR_DEMO_AI_MODE=guided
    dc up --no-deps --build -d --force-recreate ui
    echo "Workforce application: http://127.0.0.1:8501 (GUIDED, no LLM)" ;;
  live)
    [[ -n "$HR_DEMO_OPENAI_KEY" ]] || { echo "Set OPENAI_API_KEY before LIVE" >&2; exit 1; }
    make_config
    apply_config
    export HR_DEMO_AI_MODE=live
    dc up --no-deps --build -d --force-recreate ui
    echo "LIVE OpenAI via Talon; provider calls are billable. http://127.0.0.1:8501" ;;
  verify)
    dc exec -T hr-server python3 verify_isolation.py baseline
    dc exec -T ui python3 verify_isolation.py app
    dc exec -T hr-server python3 verify_isolation.py backend-counts
    dc exec -T talon-mcp sh -ec 'talon audit export --format signed-json --session hr-demo-isolated-boundary --output /tmp/hr-boundary-evidence.json >/dev/null; talon audit verify --file /tmp/hr-boundary-evidence.json' ;;
  logs) dc --profile live logs -f --tail 50 talon-mcp talon-gateway hr-server ui ;;
  down) dc --profile live down ;;
  reset) echo "Deleting fictional HR DB and Talon evidence"; dc --profile live down -v ;;
  *) echo "Usage: $0 infra|config|talon|app|reapply|up|live|verify|logs|down|reset" ;;
esac
