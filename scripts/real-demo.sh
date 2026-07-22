#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
LOGS="$STATE/logs"
ENV_FILE="$ROOT/.env"
CONFIG_DIR="$ROOT/config/generated"
READY_FILE="$STATE/real-demo-ready.env"

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }

load_env() {
  local external_openai="${OPENAI_API_KEY:-}"
  local external_anthropic="${ANTHROPIC_API_KEY:-}"

  if [[ ! -f "$ENV_FILE" ]]; then
    [[ ! -d "$STATE/talon" ]] || die ".env is missing but encrypted Talon state still exists. Remove .state and run again, or restore the matching .env."
    say "No .env found; generating local demo keys..."
    "$ROOT/scripts/generate-env.sh" >/dev/null
  fi
  # shellcheck disable=SC1090
  source "$ENV_FILE"

  # An exported provider key wins over the empty placeholder in .env. This lets
  # operators keep real provider keys out of the repository-local file.
  [[ -n "$external_openai" ]] && export OPENAI_API_KEY="$external_openai"
  [[ -n "$external_anthropic" ]] && export ANTHROPIC_API_KEY="$external_anthropic"

  # Optional provider variables are conditions, not the function result. Without
  # this explicit success, a missing Anthropic export returns status 1 and `set -e`
  # aborts OpenAI-only support/start/stop paths before they do any work.
  return 0
}

require_common() {
  local cmd
  for cmd in talon jq curl openssl python3 git; do need "$cmd"; done
}

pid_alive() {
  local pidfile="$1"
  [[ -f "$pidfile" ]] || return 1
  local pid
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null
}

wait_http() {
  local name="$1" url="$2" log="$3"
  local i
  for i in $(seq 1 100); do
    if curl --fail --silent --max-time 1 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.1
  done
  printf '%s did not become healthy at %s\n' "$name" "$url" >&2
  tail -80 "$log" >&2 2>/dev/null || true
  return 1
}

start_talon() {
  local name="$1" port="$2"
  shift 2
  local pidfile="$STATE/$name.pid"
  local log="$LOGS/$name.log"

  if pid_alive "$pidfile"; then
    say "$name already running (pid $(cat "$pidfile"))"
    return 0
  fi
  rm -f "$pidfile"
  mkdir -p "$LOGS"
  if curl --silent --max-time 1 "http://127.0.0.1:$port/health" >/dev/null 2>&1; then
    die "port $port already answers HTTP but is not owned by this demo; stop the existing service first"
  fi

  (
    cd "$CONFIG_DIR"
    nohup talon serve --host 127.0.0.1 --port "$port" "$@" >"$log" 2>&1 &
    echo "$!" >"$pidfile"
  )
  wait_http "$name" "http://127.0.0.1:$port/health" "$log"
  curl --silent --dump-header - --output /dev/null "http://127.0.0.1:$port/health" \
    | grep -qi '^x-talon-service: talon' \
    || die "service on port $port is not Talon (missing X-Talon-Service marker)"
  say "$name ready on 127.0.0.1:$port"
}

stop_pid() {
  local name="$1" expected="$2"
  local pidfile="$STATE/$name.pid"
  [[ -f "$pidfile" ]] || return 0
  local pid command_line
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  if [[ ! "$pid" =~ ^[0-9]+$ ]] || ! kill -0 "$pid" 2>/dev/null; then
    rm -f "$pidfile"
    return 0
  fi
  command_line="$(ps -p "$pid" -o args= 2>/dev/null || true)"
  if [[ "$command_line" != *"$expected"* ]]; then
    printf 'Refusing to stop pid %s for %s: command does not match (%s)\n' "$pid" "$name" "$command_line" >&2
    return 1
  fi
  kill "$pid" 2>/dev/null || true
  local i
  for i in $(seq 1 50); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.1
  done
  kill -9 "$pid" 2>/dev/null || true
  rm -f "$pidfile"
  say "$name stopped"
}

prepare() {
  require_common
  load_env
  [[ -n "${OPENAI_API_KEY:-}" ]] || die "OPENAI_API_KEY is required. Run: export OPENAI_API_KEY='sk-...'"

  local talon_repo="${TALON_REPO:-$ROOT/../talon}"
  [[ -d "$talon_repo/examples/product-demo" ]] || die "clone dativo-io/talon next to this repo, or set TALON_REPO"

  say "[1/4] Copying the pinned Talon demo configuration..."
  TALON_REPO="$talon_repo" "$ROOT/scripts/bootstrap-talon-config.sh" >/dev/null
  export TALON_GATEWAY_CONFIG="$TALON_CONFIG"

  say "[2/4] Seeding Talon's local vault..."
  talon secrets set local-llama-demo-key not-a-real-key-local-demo \
    --tenant acme --agent customer-support >/dev/null
  talon secrets set openai-api-key "$OPENAI_API_KEY" \
    --tenant acme --agent customer-support --agent coding-assistant >/dev/null

  local anthropic_ready=1
  local anthropic_value="${ANTHROPIC_API_KEY:-}"
  if [[ -z "$anthropic_value" ]]; then
    anthropic_ready=0
    anthropic_value="not-configured-anthropic-demo-key"
  fi
  talon secrets set anthropic-api-key "$anthropic_value" \
    --tenant acme --agent document-summary >/dev/null

  talon secrets set customer-support-talon-key "$TALON_CUSTOMER_SUPPORT_KEY" \
    --tenant acme --agent customer-support >/dev/null
  talon secrets set coding-assistant-talon-key "$TALON_CODING_ASSISTANT_KEY" \
    --tenant acme --agent coding-assistant >/dev/null
  talon secrets set document-summary-talon-key "$TALON_DOCUMENT_SUMMARY_KEY" \
    --tenant acme --agent document-summary >/dev/null

  say "[3/4] Validating configuration..."
  talon validate --dir "$CONFIG_DIR/agents"
  talon doctor

  say "[4/4] Recording readiness..."
  mkdir -p "$STATE"
  {
    printf 'REAL_DEMO_PREPARED_AT=%q\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'REAL_DEMO_ANTHROPIC_READY=%q\n' "$anthropic_ready"
  } >"$READY_FILE"
  chmod 0600 "$READY_FILE"

  say
  say "Prepared. Next: make real-start"
  if [[ "$anthropic_ready" == 0 ]]; then
    say "OpenAI support/Copilot tests are ready. Anthropic/n8n remains disabled until ANTHROPIC_API_KEY is supplied and real-prepare is run again."
  fi
}

start() {
  require_common
  load_env
  [[ -f "$READY_FILE" ]] || die "not prepared; run: export OPENAI_API_KEY='sk-...' && make real-prepare"
  [[ -f "$CONFIG_DIR/talon.config.yaml" ]] || die "missing generated config; run make real-prepare"
  export TALON_GATEWAY_CONFIG="$TALON_CONFIG"

  if curl --fail --silent --max-time 1 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    die "Ollama is running on :11434. Stop it so the real support case can demonstrate fallback."
  fi

  start_talon talon-gateway 8080 --gateway
  start_talon talon-mcp-proxy 8081 --proxy-config ../mcp-proxy.example.yaml

  say "Minting a fresh run identity and checking both Talon boundaries..."
  "$ROOT/scripts/preflight.sh"
  "$ROOT/scripts/stop-components.sh" >/dev/null 2>&1 || true
  "$ROOT/scripts/start-components.sh"

  say
  say "Everything is running. Next: make real-smoke"
  say "Logs: $LOGS"
}

smoke() {
  require_common
  load_env
  curl --fail --silent --max-time 2 "$TALON_GATEWAY/health" >/dev/null \
    || die "Talon gateway is not running; run make real-start"

  if [[ -f "$STATE/demo-run.env" ]]; then
    # shellcheck disable=SC1090
    source "$STATE/demo-run.env"
  fi

  local run_id="${TALON_DEMO_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)}"
  local session="real-support-$run_id"
  local request="$STATE/$session.request.json"
  local response="$STATE/$session.response.json"
  local evidence="$STATE/$session.signed.json"

  mkdir -p "$STATE"
  jq -nc \
    --arg model "${TALON_CUSTOMER_SUPPORT_MODEL:-llama3.2:1b}" \
    --arg prompt 'Draft a short reply confirming receipt of Anna Kowalska’s refund request. Email: anna.kowalska@example.com IBAN: DE89370400440532013000' \
    '{model:$model,max_tokens:150,messages:[{role:"user",content:$prompt}]}' >"$request"

  say "Sending one real customer-support request through Talon..."
  local http
  http="$(curl -sS -o "$response" -w '%{http_code}' -X POST \
    "$TALON_GATEWAY/v1/proxy/${TALON_CUSTOMER_SUPPORT_PROVIDER:-local-llama}/v1/chat/completions" \
    -H "Authorization: Bearer $TALON_CUSTOMER_SUPPORT_KEY" \
    -H "X-Talon-Session-ID: $session" \
    -H 'Content-Type: application/json' \
    --data-binary @"$request")"

  if [[ "$http" != 200 ]]; then
    printf 'Request failed with HTTP %s\n' "$http" >&2
    jq . "$response" >&2 2>/dev/null || cat "$response" >&2
    tail -80 "$LOGS/talon-gateway.log" >&2 2>/dev/null || true
    exit 1
  fi

  talon audit export --format signed-json --session "$session" --output "$evidence" >/dev/null
  "$ROOT/scripts/assert-evidence.sh" --session "$session" --agent customer-support

  jq -e 'any(.records[]; .classification.input_pii_redacted==true
      and (.classification.pii_detected|index("email"))
      and (.classification.pii_detected|index("iban"))
      and .classification.input_tier==2)' "$evidence" >/dev/null \
    || die "evidence did not prove input PII redaction"
  jq -e 'any(.records[]; .failover.role=="failed_attempt"
      and .failover.provider=="local-llama"
      and .failover.error_class=="connection_error")' "$evidence" >/dev/null \
    || die "evidence did not prove the local-provider failure"
  jq -e 'any(.records[]; .failover.role=="fallback_decision"
      and .failover.provider=="openai"
      and any(.failover.skipped_candidates[]?; .provider=="openai-batch"
        and .filter=="agent_provider_allowlist"))' "$evidence" >/dev/null \
    || die "evidence did not prove policy-valid fallback to OpenAI"

  say
  say "REAL CASE PASSED"
  say "  PII: email + IBAN redacted before provider access"
  say "  Reliability: local-llama failed; disallowed openai-batch was skipped; OpenAI was selected"
  say "  Evidence: signatures valid and saved to $evidence"
  say "  Session: $session"
  say
  jq -r '.choices[0].message.content // .content[0].text // "(response saved to file)"' "$response"
}

copilot_case() {
  require_common
  need copilot
  load_env
  curl --fail --silent --max-time 2 "$TALON_GATEWAY/health" >/dev/null \
    || die "Talon gateway is not running; run make real-start"
  curl --fail --silent --max-time 2 "$TALON_MCP_GATEWAY/health" >/dev/null \
    || die "Talon MCP proxy is not running; run make real-start"
  [[ -f "$STATE/demo-run.env" ]] || die "missing run identity; run make real-start"
  # shellcheck disable=SC1090
  source "$STATE/demo-run.env"

  "$ROOT/scripts/reset-billing-fixture.sh"
  "$ROOT/scripts/render-copilot-mcp-config.sh"
  local nonce
  nonce="$(cat "$STATE/run-nonce")"

  say
  say "Copilot will open in the failing billing fixture. Give it this task:"
  say "------------------------------------------------------------"
  cat <<EOF_PROMPT
Run npm test and inspect the failure. Make the smallest correction needed,
rerun the tests, and show the diff. Then list the release-gateway tools and
call release_status and release_prepare with this run_nonce: $nonce
Do not modify unrelated files.
EOF_PROMPT
  say "------------------------------------------------------------"
  say

  cd "$ROOT/cases/billing-demo"
  exec env \
    COPILOT_PROVIDER_TYPE=openai \
    COPILOT_PROVIDER_BASE_URL="http://127.0.0.1:8079/v1/proxy/openai/v1" \
    COPILOT_PROVIDER_API_KEY="$TALON_CODING_ASSISTANT_KEY" \
    COPILOT_MODEL="${COPILOT_MODEL:-gpt-4o}" \
    COPILOT_OFFLINE=true \
    copilot \
      --additional-mcp-config=@../../.state/copilot-mcp.json \
      --disable-builtin-mcps \
      --allow-tool='release-gateway' \
      --deny-tool='shell(git push)'
}

status() {
  load_env
  local ok=0
  check_url() {
    local label="$1" url="$2"
    if curl --fail --silent --max-time 1 "$url" >/dev/null 2>&1; then
      printf '✓ %-18s %s\n' "$label" "$url"
    else
      printf '✗ %-18s %s\n' "$label" "$url"
      ok=1
    fi
  }
  check_url "Talon gateway" "$TALON_GATEWAY/health"
  check_url "Talon MCP proxy" "$TALON_MCP_GATEWAY/health"
  check_url "Zendesk adapter" "http://${ZENDESK_ADAPTER_BIND:-127.0.0.1:8443}/health"
  check_url "Release MCP" "http://${RELEASE_MCP_BIND:-127.0.0.1:8090}/health"
  if [[ -f "$READY_FILE" ]]; then
    # shellcheck disable=SC1090
    source "$READY_FILE"
    [[ "${REAL_DEMO_ANTHROPIC_READY:-0}" == 1 ]] \
      && say "✓ Anthropic key seeded" \
      || say "– Anthropic key not configured (OpenAI paths still available)"
  fi
  return "$ok"
}

stop() {
  load_env
  "$ROOT/scripts/stop-components.sh" >/dev/null 2>&1 || true
  stop_pid talon-mcp-proxy "talon serve" || true
  stop_pid talon-gateway "talon serve" || true
}

usage() {
  cat <<'USAGE'
Usage: scripts/real-demo.sh <command>

Commands:
  prepare  Generate local keys/config and seed Talon's vault. Requires OPENAI_API_KEY.
  start    Start the gateway, MCP proxy, adapter, shim, and synthetic release server.
  smoke    Run one real OpenAI-backed support case and verify signed evidence.
  copilot  Launch real Copilot CLI through Talon in the billing fixture.
  status   Show which demo services are reachable.
  stop     Stop services started by this repository.

Fast path:
  export OPENAI_API_KEY='sk-...'
  make real-prepare
  make real-start
  make real-smoke
  make real-copilot   # optional, requires Copilot CLI
USAGE
}

case "${1:-help}" in
  prepare) prepare ;;
  start) start ;;
  smoke) smoke ;;
  copilot) copilot_case ;;
  status) status ;;
  stop) stop ;;
  help|-h|--help) usage ;;
  *) usage >&2; exit 2 ;;
esac
