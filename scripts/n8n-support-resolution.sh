#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
IMAGE="${N8N_IMAGE:-docker.n8n.io/n8nio/n8n:2.30.4}"
WORKFLOW="$ROOT/integrations/n8n/customer-support-resolution-workflow.json"
INPUT="$ROOT/cases/customer-support-resolution"
MODE="${1:-help}"
DEMO_OUTPUT="${N8N_SUPPORT_RESOLUTION_DEMO_OUTPUT:-full}"
PIDS=()

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }

cleanup() {
  local pid
  set +e
  for pid in "${PIDS[@]:-}"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

require_common() {
  local cmd
  for cmd in docker jq curl python3 openssl id; do need "$cmd"; done
  docker info >/dev/null 2>&1 || die 'Docker daemon is not available'
  [[ -s "$WORKFLOW" ]] || die "missing workflow artifact: $WORKFLOW"
  [[ -d "$INPUT" ]] || die "missing support-resolution input: $INPUT"
  jq -e '.id == "talonSupportResolution01" and .name and (.nodes | length >= 11)' "$WORKFLOW" >/dev/null \
    || die 'committed support-resolution workflow is not valid import JSON'
  case "$DEMO_OUTPUT" in full|quiet) ;; *) die 'N8N_SUPPORT_RESOLUTION_DEMO_OUTPUT must be full or quiet' ;; esac
}

free_port() {
  python3 - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    print(sock.getsockname()[1])
PY
}

run_n8n() {
  local runtime="$1" output="$2" config="$3" session="$4" gateway="$5"
  shift 5
  install -d -m 0700 "$runtime" "$config"
  install -d -m 0777 "$output"
  docker run --rm \
    --network host \
    --user "$(id -u):$(id -g)" \
    -e HOME=/home/node \
    -e N8N_USER_FOLDER=/home/node/.n8n \
    -e N8N_ENCRYPTION_KEY="$N8N_ENCRYPTION_KEY" \
    -e N8N_DIAGNOSTICS_ENABLED=false \
    -e N8N_VERSION_NOTIFICATIONS_ENABLED=false \
    -e N8N_TEMPLATES_ENABLED=false \
    -e N8N_RUNNERS_ENABLED=true \
    -e N8N_RUNNERS_MODE=internal \
    -e N8N_BLOCK_ENV_ACCESS_IN_NODE=false \
    -e N8N_RESTRICT_FILE_ACCESS_TO=/demo \
    -e TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID="$session" \
    -e TALON_N8N_GATEWAY_URL="$gateway" \
    -v "$runtime:/home/node/.n8n" \
    -v "$INPUT:/demo/input:ro" \
    -v "$output:/demo/output" \
    -v "$config:/demo/config" \
    "$IMAGE" "$@"
}

prepare_config() {
  local config="$1" workflow_source="$2" key="$3"
  install -d -m 0700 "$config"
  cp "$workflow_source" "$config/workflow.json"
  TALON_N8N_CREDENTIAL_KEY="$key" \
  TALON_N8N_CREDENTIAL_ID=talonSupportResolutionAuth1 \
  TALON_N8N_CREDENTIAL_NAME='Talon customer-support' \
    "$ROOT/scripts/render-n8n-credential.sh" "$config/credential.json" >/dev/null
  chmod 0644 "$config/workflow.json"
}

import_and_execute() {
  local runtime="$1" output="$2" config="$3" session="$4" gateway="$5"
  install -d -m 0700 "$runtime" "$config"
  install -d -m 0777 "$output"
  rm -f "$output/customer-support-resolution.md" "$output/status.json" 2>/dev/null || true

  run_n8n "$runtime" "$output" "$config" "$session" "$gateway" \
    import:credentials --input=/demo/config/credential.json >/dev/null
  run_n8n "$runtime" "$output" "$config" "$session" "$gateway" \
    import:workflow --input=/demo/config/workflow.json >/dev/null
  run_n8n "$runtime" "$output" "$config" "$session" "$gateway" \
    export:workflow --all --output=/demo/config/imported-workflows.json >/dev/null

  local workflow_id
  workflow_id="$(jq -r 'if type == "array" then .[0].id else .id end' "$config/imported-workflows.json")"
  [[ -n "$workflow_id" && "$workflow_id" != null ]] || die 'could not resolve imported support-resolution workflow id'

  run_n8n "$runtime" "$output" "$config" "$session" "$gateway" execute --id="$workflow_id"
}

assert_output_contract() {
  local output="$1" session="$2"
  local report="$output/customer-support-resolution.md"
  local status="$output/status.json"
  [[ -s "$report" ]] || die 'n8n did not produce customer-support-resolution.md'
  [[ -s "$status" ]] || die 'n8n did not produce support-resolution status.json'
  grep -Fq 'refund was not executed and requires human support and finance approval' "$report" \
    || die 'support-resolution packet omitted the human-approval boundary'
  jq -e --arg session "$session" '
    .status == "completed"
    and .result == "governed_support_resolution"
    and .session_id == $session
    and .operational_id == "customer-support"
    and .documents_read >= 3
    and .ticket_id == "SUP-1042"
    and .refund_amount_eur == 249
    and .reply_draft_created == true
    and .blocked_tool == "issue_refund"
    and .denial_code == "tool_governance_block"
    and .denied_provider_cost_usd == 0
    and .action_status == "human_approval_required"
    and .human_approval_required == true
  ' "$status" >/dev/null || die 'status.json does not match the governed support-resolution contract'
  if [[ "$MODE" == validate ]]; then
    grep -Fq 'We received your synthetic refund request' "$report" \
      || die 'mock support-resolution report did not contain provider output'
  fi
}

assert_clean_export() {
  local exported="$1" forbidden="$2"
  [[ -s "$exported" ]] || die 'n8n did not export the imported support-resolution workflow'
  jq -e '(if type == "array" then . else [.] end)
    | length == 1
    and all(.[]; .id == "talonSupportResolution01" and (.nodes | length >= 11))' "$exported" >/dev/null \
    || die 'exported support-resolution workflow lost its node graph'
  if grep -Fq "$forbidden" "$exported"; then
    die 'exported support-resolution workflow contains the Talon credential secret'
  fi
  jq -e '(if type == "array" then . else [.] end)
    | all(.[]; all(.nodes[]; (.credentials // {}) | tostring | contains("Bearer ") | not))' \
    "$exported" >/dev/null || die 'exported support-resolution workflow contains inline Authorization'
}

assert_mock_receipts() {
  local log="$1" session="$2" key="$3"
  jq -s -e --arg session "$session" --arg auth "Bearer $key" '
    [ .[] | select(.headers["x-talon-session-id"] == $session) ] as $r
    | ($r | length) == 2
    and ($r[0].path | contains("/local-llama/"))
    and $r[0].denied == false
    and ($r[1].path | contains("/openai/"))
    and $r[1].denied == true
    and $r[1].denial_code == "tool_governance_block"
    and $r[1].cost_usd == 0
    and ($r[1].tool_names | index("issue_refund"))
    and all($r[]; .headers.authorization == $auth)
    and all($r[]; .headers["x-talon-client"] == "n8n-customer-support-resolution-full-demo")
  ' "$log" >/dev/null || die 'mock receipts do not prove reply-then-zero-cost-refund-denial behavior'
}

validate_mode() {
  require_common
  local work port log key gateway session1 session2
  work="$(mktemp -d "${TMPDIR:-/tmp}/talon-n8n-support-resolution.XXXXXX")"
  port="$(free_port)"
  log="$work/mock-talon.jsonl"
  key="n8n-support-resolution-validation-key"
  gateway="http://127.0.0.1:$port"
  N8N_ENCRYPTION_KEY="n8n-support-resolution-encryption-$(openssl rand -hex 16)"
  export N8N_ENCRYPTION_KEY

  MOCK_TALON_PORT="$port" MOCK_TALON_LOG="$log" MOCK_TALON_DENY_TOOL=issue_refund \
    python3 "$ROOT/mock/mock_talon.py" >"$work/mock-talon.log" 2>&1 &
  PIDS+=("$!")
  for _ in $(seq 1 50); do
    curl -fsS "$gateway/health" >/dev/null 2>&1 && break
    sleep 0.1
  done
  curl -fsS "$gateway/health" >/dev/null || die 'mock Talon did not become ready'

  session1="n8n-support-clean-one-$(openssl rand -hex 3)"
  prepare_config "$work/config-one" "$WORKFLOW" "$key"
  import_and_execute "$work/runtime-one" "$work/output-one" "$work/config-one" "$session1" "$gateway" >/dev/null
  assert_output_contract "$work/output-one" "$session1"
  assert_clean_export "$work/config-one/imported-workflows.json" "$key"
  assert_mock_receipts "$log" "$session1" "$key"

  session2="n8n-support-clean-two-$(openssl rand -hex 3)"
  prepare_config "$work/config-two" "$work/config-one/imported-workflows.json" "$key"
  import_and_execute "$work/runtime-two" "$work/output-two" "$work/config-two" "$session2" "$gateway" >/dev/null
  assert_output_contract "$work/output-two" "$session2"
  assert_clean_export "$work/config-two/imported-workflows.json" "$key"
  assert_mock_receipts "$log" "$session2" "$key"

  rm -rf "$work"
  say 'N8N SUPPORT RESOLUTION VALIDATION PASSED'
  say '  committed workflow created a reply, blocked issue_refund, and preserved no credential values'
  say '  credential-free export imported and executed in a second clean n8n 2.30.4 runtime'
}

real_mode() {
  require_common
  [[ -f "$ROOT/.env" ]] || die 'missing .env; run make real-prepare'
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  [[ -n "${N8N_ENCRYPTION_KEY:-}" ]] || die 'N8N_ENCRYPTION_KEY is empty; run make env'
  [[ -n "${TALON_CUSTOMER_SUPPORT_KEY:-}" ]] || die 'TALON_CUSTOMER_SUPPORT_KEY is empty; rerun make real-prepare'
  [[ -f "$STATE/real-demo-ready.env" ]] || die 'real demo is not prepared; run make real-prepare'
  curl -fsS "${TALON_GATEWAY:-http://127.0.0.1:8080}/health" >/dev/null \
    || die 'Talon gateway is not healthy; run make real-start'

  "$ROOT/scripts/preflight.sh"
  # shellcheck disable=SC1091
  source "$STATE/demo-run.env"

  local config output runtime gateway transcript
  config="$STATE/n8n-support-resolution-config"
  output="$STATE/n8n-support-resolution-output"
  runtime="$STATE/n8n-support-resolution-runtime"
  gateway="http://127.0.0.1:8080"
  transcript="$STATE/n8n-support-resolution-$(date -u +%Y%m%dT%H%M%SZ).log"
  rm -rf "$config" "$output" "$runtime"
  prepare_config "$config" "$WORKFLOW" "$TALON_CUSTOMER_SUPPORT_KEY"

  if [[ "$DEMO_OUTPUT" == quiet ]]; then
    say 'Running the committed customer-support resolution through Talon...'
    import_and_execute "$runtime" "$output" "$config" "$TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID" "$gateway" \
      >"$transcript" 2>&1 || {
        cat "$transcript" >&2
        die "real n8n support-resolution case failed; full output is in $transcript"
      }
  else
    import_and_execute "$runtime" "$output" "$config" "$TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID" "$gateway" \
      2>&1 | tee "$transcript"
  fi
  assert_output_contract "$output" "$TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID"
  assert_clean_export "$config/imported-workflows.json" "$TALON_CUSTOMER_SUPPORT_KEY"

  say
  say 'REAL N8N SUPPORT RESOLUTION COMPLETED'
  say "  Session:    $TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID"
  say "  Resolution: $output/customer-support-resolution.md"
  say "  Status:     $output/status.json"
  say "  Transcript: $transcript"
  say '  Next: make present-n8n-support-resolution-all'
}

case "$MODE" in
  validate) validate_mode ;;
  real) real_mode ;;
  *)
    cat >&2 <<'USAGE'
Usage: bash scripts/n8n-support-resolution.sh validate|real

validate  Clean-import twice in pinned n8n 2.30.4 against mock reply-then-tool-denial behavior.
real      Run the committed support resolution through real Talon + OpenAI fallback.
USAGE
    exit 2
    ;;
esac
