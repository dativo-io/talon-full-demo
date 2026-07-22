#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
IMAGE="${N8N_IMAGE:-docker.n8n.io/n8nio/n8n:2.30.4}"
WORKFLOW="$ROOT/integrations/n8n/quarterly-compliance-workflow.json"
MODE="${1:-help}"
VOLUMES=()
PIDS=()

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }

cleanup() {
  local pid volume
  for pid in "${PIDS[@]:-}"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  done
  if [[ "${N8N_KEEP_VOLUMES:-0}" != 1 ]]; then
    for volume in "${VOLUMES[@]:-}"; do
      [[ -n "$volume" ]] && docker volume rm -f "$volume" >/dev/null 2>&1 || true
    done
  fi
}
trap cleanup EXIT

require_common() {
  for cmd in docker jq curl python3 openssl; do need "$cmd"; done
  docker info >/dev/null 2>&1 || die 'Docker daemon is not available'
  [[ -s "$WORKFLOW" ]] || die "missing workflow artifact: $WORKFLOW"
  jq -e '.id and .name and (.nodes | length > 0)' "$WORKFLOW" >/dev/null \
    || die 'committed n8n workflow is not valid import JSON'
}

free_port() {
  python3 - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    print(sock.getsockname()[1])
PY
}

new_volume() {
  local suffix volume
  suffix="$(openssl rand -hex 4)"
  volume="talon-full-demo-n8n-${suffix}"
  docker volume create "$volume" >/dev/null
  VOLUMES+=("$volume")
  printf '%s\n' "$volume"
}

run_n8n() {
  local volume="$1" output="$2" config="$3" session="$4" gateway="$5"
  shift 5
  docker run --rm \
    --network host \
    -e N8N_ENCRYPTION_KEY="$N8N_ENCRYPTION_KEY" \
    -e N8N_DIAGNOSTICS_ENABLED=false \
    -e N8N_VERSION_NOTIFICATIONS_ENABLED=false \
    -e N8N_TEMPLATES_ENABLED=false \
    -e N8N_RUNNERS_ENABLED=true \
    -e N8N_RUNNERS_MODE=internal \
    -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false \
    -e N8N_RESTRICT_FILE_ACCESS_TO=/demo \
    -e TALON_N8N_SESSION_ID="$session" \
    -e TALON_N8N_GATEWAY_URL="$gateway" \
    -v "$volume:/home/node/.n8n" \
    -v "$ROOT/cases/quarterly-report:/demo/input:ro" \
    -v "$output:/demo/output" \
    -v "$config:/demo/config" \
    "$IMAGE" "$@"
}

prepare_config() {
  local config="$1" workflow_source="$2" key="$3"
  install -d -m 0777 "$config"
  cp "$workflow_source" "$config/workflow.json"
  TALON_DOCUMENT_SUMMARY_KEY="$key" \
    "$ROOT/scripts/render-n8n-credential.sh" "$config/credential.json" >/dev/null
  chmod 0644 "$config/workflow.json"
}

import_and_execute() {
  local volume="$1" output="$2" config="$3" session="$4" gateway="$5"
  install -d -m 0777 "$output"
  rm -f "$output"/*.summary.md "$output/status.json" 2>/dev/null || true

  run_n8n "$volume" "$output" "$config" "$session" "$gateway" \
    import:credentials --input=/demo/config/credential.json >/dev/null
  run_n8n "$volume" "$output" "$config" "$session" "$gateway" \
    import:workflow --input=/demo/config/workflow.json >/dev/null
  run_n8n "$volume" "$output" "$config" "$session" "$gateway" \
    export:workflow --all --output=/demo/config/imported-workflows.json >/dev/null

  local workflow_id
  workflow_id="$(jq -r 'if type == "array" then .[0].id else .id end' "$config/imported-workflows.json")"
  [[ -n "$workflow_id" && "$workflow_id" != null ]] || die 'could not resolve imported n8n workflow id'

  run_n8n "$volume" "$output" "$config" "$session" "$gateway" \
    execute --id="$workflow_id"
}

assert_output_contract() {
  local output="$1" session="$2"
  mapfile -d '' summaries < <(find "$output" -maxdepth 1 -type f -name '*.summary.md' -print0 | sort -z)
  (( ${#summaries[@]} >= 1 )) || die 'n8n produced no completed section files'
  [[ -s "$output/status.json" ]] || die 'n8n did not preserve a session-budget status artifact'
  jq -e --arg session "$session" '
    .status == "partial"
    and .reason == "session_budget_exceeded"
    and .session_id == $session
    and .provider_cost_usd == 0
  ' "$output/status.json" >/dev/null \
    || die 'n8n status.json does not match the budget-stop contract'
  grep -Fq 'Synthetic compliance summary.' "${summaries[0]}" \
    || [[ "$MODE" == real ]] \
    || die 'mock n8n summary did not contain provider output'
}

assert_clean_export() {
  local exported="$1" forbidden="$2"
  [[ -s "$exported" ]] || die 'n8n did not export the imported workflow'
  jq -e '(if type == "array" then . else [.] end)
    | length == 1
    and all(.[]; (.nodes | length) >= 10)' "$exported" >/dev/null \
    || die 'exported n8n workflow lost its node graph'
  if grep -Fq "$forbidden" "$exported"; then
    die 'exported n8n workflow contains the Talon credential secret'
  fi
  jq -e '(if type == "array" then . else [.] end)
    | all(.[]; all(.nodes[]; (.credentials // {}) | tostring | contains("Bearer ") | not))' \
    "$exported" >/dev/null \
    || die 'exported n8n workflow contains an inline Authorization value'
}

assert_mock_receipts() {
  local log="$1" session="$2" key="$3"
  jq -e --arg session "$session" --arg auth "Bearer $key" '
    [select(.headers["x-talon-session-id"] == $session)] as $r
    | ($r | length) == 2
    and $r[0].denied == false
    and $r[1].denied == true
    and $r[1].cost_usd == 0
    and all($r[]; .path == "/v1/proxy/anthropic/v1/messages")
    and all($r[]; .headers.authorization == $auth)
    and all($r[]; .headers["x-talon-client"] == "n8n-quarterly-report-full-demo")
  ' "$log" >/dev/null || die 'mock receipts do not prove sequential allow-then-budget-deny behavior'
}

validate_mode() {
  require_common
  local work port log key gateway volume1 volume2 session1 session2
  work="$(mktemp -d "${TMPDIR:-/tmp}/talon-n8n-validation.XXXXXX")"
  port="$(free_port)"
  log="$work/mock-talon.jsonl"
  key="n8n-validation-key"
  gateway="http://127.0.0.1:$port"
  N8N_ENCRYPTION_KEY="n8n-validation-encryption-key-$(openssl rand -hex 16)"
  export N8N_ENCRYPTION_KEY

  MOCK_TALON_PORT="$port" MOCK_TALON_LOG="$log" MOCK_TALON_SESSION_BUDGET_REQUESTS=1 \
    python3 "$ROOT/mock/mock_talon.py" >"$work/mock-talon.log" 2>&1 &
  PIDS+=("$!")
  for _ in $(seq 1 50); do
    curl -fsS "$gateway/health" >/dev/null 2>&1 && break
    sleep 0.1
  done
  curl -fsS "$gateway/health" >/dev/null || die 'mock Talon did not become ready'

  session1="n8n-clean-import-one-$(openssl rand -hex 3)"
  volume1="$(new_volume)"
  prepare_config "$work/config-one" "$WORKFLOW" "$key"
  import_and_execute "$volume1" "$work/output-one" "$work/config-one" "$session1" "$gateway" >/dev/null
  assert_output_contract "$work/output-one" "$session1"
  assert_clean_export "$work/config-one/imported-workflows.json" "$key"
  assert_mock_receipts "$log" "$session1" "$key"

  session2="n8n-clean-import-two-$(openssl rand -hex 3)"
  volume2="$(new_volume)"
  prepare_config "$work/config-two" "$work/config-one/imported-workflows.json" "$key"
  import_and_execute "$volume2" "$work/output-two" "$work/config-two" "$session2" "$gateway" >/dev/null
  assert_output_contract "$work/output-two" "$session2"
  assert_clean_export "$work/config-two/imported-workflows.json" "$key"
  assert_mock_receipts "$log" "$session2" "$key"

  rm -rf "$work"
  say 'N8N WORKFLOW VALIDATION PASSED'
  say '  committed workflow imported and executed against the budget contract'
  say '  credential-free export imported into a second clean n8n 2.30.4 volume'
  say '  both runs preserved one completed section and stopped the next request at zero provider cost'
}

real_mode() {
  require_common
  [[ -f "$ROOT/.env" ]] || die 'missing .env; run make real-prepare'
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  [[ -n "${N8N_ENCRYPTION_KEY:-}" ]] || die 'N8N_ENCRYPTION_KEY is empty; run make env'
  [[ -n "${TALON_DOCUMENT_SUMMARY_KEY:-}" ]] || die 'TALON_DOCUMENT_SUMMARY_KEY is empty; run make real-prepare'
  [[ -f "$STATE/real-demo-ready.env" ]] || die 'real demo is not prepared; run make real-prepare'
  # shellcheck disable=SC1091
  source "$STATE/real-demo-ready.env"
  [[ "${REAL_DEMO_ANTHROPIC_READY:-0}" == 1 ]] \
    || die 'Anthropic was not seeded during real-prepare; export ANTHROPIC_API_KEY and rerun make real-prepare'
  curl -fsS "${TALON_GATEWAY:-http://127.0.0.1:8080}/health" >/dev/null \
    || die 'Talon gateway is not healthy; run make real-start'

  "$ROOT/scripts/preflight.sh"
  # shellcheck disable=SC1091
  source "$STATE/demo-run.env"
  local config output volume gateway
  config="$STATE/n8n-config"
  output="$STATE/n8n-output"
  gateway="http://127.0.0.1:8080"
  rm -rf "$config" "$output"
  prepare_config "$config" "$WORKFLOW" "$TALON_DOCUMENT_SUMMARY_KEY"
  volume="$(new_volume)"

  say 'Running the committed n8n workflow through Talon...'
  import_and_execute "$volume" "$output" "$config" "$TALON_N8N_SESSION_ID" "$gateway"
  assert_output_contract "$output" "$TALON_N8N_SESSION_ID"
  assert_clean_export "$config/imported-workflows.json" "$TALON_DOCUMENT_SUMMARY_KEY"

  say
  say 'REAL N8N CASE COMPLETED'
  say "  Session: $TALON_N8N_SESSION_ID"
  say "  Output:  $output"
  say '  Next: make present-n8n-all'
}

case "$MODE" in
  validate) validate_mode ;;
  real) real_mode ;;
  *)
    cat >&2 <<'EOF'
Usage: bash scripts/n8n-workflow.sh validate|real

validate  Import, execute, export, clean-import, and execute again in pinned n8n 2.30.4 against mock Talon's budget contract.
real      Run the same committed workflow against the prepared real Talon + Anthropic path.
EOF
    exit 2
    ;;
esac
