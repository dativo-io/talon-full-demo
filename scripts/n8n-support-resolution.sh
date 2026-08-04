#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
IMAGE="${N8N_IMAGE:-docker.n8n.io/n8nio/n8n:2.30.4}"
WORKFLOW_BASE="$ROOT/integrations/n8n/customer-support-resolution-workflow.json"
WORKFLOW_RENDERER="$ROOT/scripts/render-support-resolution-workflow.py"
APPROVAL_SERVER="$ROOT/scripts/support-approval-server.py"
APPROVAL_CLI="$ROOT/scripts/support-approval.sh"
APPROVAL_VERIFY="$ROOT/scripts/verify-support-approval.py"
INPUT="$ROOT/cases/customer-support-resolution"
MODE="${1:-help}"
DEMO_OUTPUT="${N8N_SUPPORT_RESOLUTION_DEMO_OUTPUT:-full}"
PIDS=()
APPROVAL_URL=""

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }

cleanup() {
  local pid
  set +e
  for pid in "${PIDS[@]:-}"; do
    [[ -n "$pid" ]] && kill -TERM "$pid" 2>/dev/null || true
  done
  for pid in "${PIDS[@]:-}"; do
    [[ -n "$pid" ]] && wait "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT

require_common() {
  local cmd file
  for cmd in docker jq curl python3 openssl id; do need "$cmd"; done
  docker info >/dev/null 2>&1 || die 'Docker daemon is not available'
  for file in "$WORKFLOW_BASE" "$WORKFLOW_RENDERER" "$APPROVAL_SERVER" "$APPROVAL_CLI" "$APPROVAL_VERIFY"; do
    [[ -s "$file" ]] || die "missing support-resolution artifact: $file"
  done
  [[ -d "$INPUT" ]] || die "missing support-resolution input: $INPUT"
  jq -e '.id == "talonSupportResolution01" and .name and (.nodes | length >= 11)' "$WORKFLOW_BASE" >/dev/null \
    || die 'committed support-resolution base workflow is not valid n8n JSON'
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

approval_id_for() {
  local session="$1" nonce="$2"
  python3 - "$session" "$nonce" <<'PY'
import hashlib, sys
value = '|'.join([sys.argv[1], sys.argv[2], 'SUP-1042', '249', 'issue_refund'])
print('apr_' + hashlib.sha256(value.encode()).hexdigest()[:20])
PY
}

render_workflow() {
  local output="$1"
  python3 "$WORKFLOW_RENDERER" "$WORKFLOW_BASE" "$output"
  jq -e '
    .id == "talonSupportResolution01"
    and any(.nodes[]; .name == "Create Human Approval Request")
    and any(.nodes[]; .name == "Wait for Operator Decision")
    and any(.nodes[]; .name == "Operator Approved?")
    and any(.nodes[]; .name == "Write Finance Handoff")
    and any(.nodes[]; .name == "Write Rejected Status")
    and (tostring | contains("TALON_SUPPORT_APPROVAL_URL"))
    and (tostring | contains("ACME Support Team"))
  ' "$output" >/dev/null || die 'rendered support workflow lost its operator-approval contract'
}

run_n8n() {
  local runtime="$1" output="$2" config="$3" session="$4" gateway="$5" approval_url="$6" approval_id="$7" run_nonce="$8"
  shift 8
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
    -e TALON_SUPPORT_APPROVAL_URL="$approval_url" \
    -e TALON_SUPPORT_APPROVAL_ID="$approval_id" \
    -e RELEASE_RUN_NONCE="$run_nonce" \
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
  local runtime="$1" output="$2" config="$3" session="$4" gateway="$5" approval_url="$6" approval_id="$7" run_nonce="$8"
  install -d -m 0700 "$runtime" "$config"
  install -d -m 0777 "$output"
  rm -f \
    "$output/customer-support-resolution.md" \
    "$output/status.json" \
    "$output/operator-approval-receipt.json" \
    "$output/finance-refund-request.json" 2>/dev/null || true

  run_n8n "$runtime" "$output" "$config" "$session" "$gateway" "$approval_url" "$approval_id" "$run_nonce" \
    import:credentials --input=/demo/config/credential.json >/dev/null
  run_n8n "$runtime" "$output" "$config" "$session" "$gateway" "$approval_url" "$approval_id" "$run_nonce" \
    import:workflow --input=/demo/config/workflow.json >/dev/null
  run_n8n "$runtime" "$output" "$config" "$session" "$gateway" "$approval_url" "$approval_id" "$run_nonce" \
    export:workflow --all --output=/demo/config/imported-workflows.json >/dev/null

  local workflow_id
  workflow_id="$(jq -r 'if type == "array" then .[0].id else .id end' "$config/imported-workflows.json")"
  [[ -n "$workflow_id" && "$workflow_id" != null ]] || die 'could not resolve imported support-resolution workflow id'

  run_n8n "$runtime" "$output" "$config" "$session" "$gateway" "$approval_url" "$approval_id" "$run_nonce" \
    execute --id="$workflow_id"
}

start_approval_server() {
  local state_dir="$1" key_file="$2" port="$3"
  install -d -m 0700 "$state_dir"
  [[ -s "$key_file" ]] || { openssl rand -hex 32 >"$key_file"; chmod 0600 "$key_file"; }
  python3 "$APPROVAL_SERVER" \
    --host 127.0.0.1 \
    --port "$port" \
    --state-dir "$state_dir" \
    --signing-key-file "$key_file" \
    >"$state_dir/server.log" 2>&1 &
  PIDS+=("$!")
  APPROVAL_URL="http://127.0.0.1:$port"
  for _ in $(seq 1 100); do
    curl -fsS "$APPROVAL_URL/health" >/dev/null 2>&1 && return 0
    sleep 0.1
  done
  cat "$state_dir/server.log" >&2 || true
  die 'support approval service did not become healthy'
}

write_approval_env() {
  local url="$1" approval_id="$2" session="$3" nonce="$4" key_file="$5" state_dir="$6"
  local env_file="$STATE/n8n-support-resolution-approval.env"
  umask 077
  cat >"$env_file" <<EOF_APPROVAL
export TALON_SUPPORT_APPROVAL_URL=$url
export TALON_SUPPORT_APPROVAL_ID=$approval_id
export TALON_SUPPORT_APPROVAL_PAGE=$url/approval/$approval_id
export TALON_SUPPORT_APPROVAL_SESSION_ID=$session
export TALON_SUPPORT_APPROVAL_RUN_NONCE=$nonce
export TALON_SUPPORT_APPROVAL_KEY_FILE=$key_file
export TALON_SUPPORT_APPROVAL_STATE_DIR=$state_dir
EOF_APPROVAL
  chmod 0600 "$env_file"
}

wait_for_approval_request() {
  local url="$1" approval_id="$2" worker_pid="$3"
  for _ in $(seq 1 1800); do
    if curl -fsS "$url/requests/$approval_id" >/dev/null 2>&1; then
      return 0
    fi
    if ! kill -0 "$worker_pid" 2>/dev/null; then
      wait "$worker_pid" || true
      return 1
    fi
    sleep 0.2
  done
  return 1
}

assert_no_final_artifacts() {
  local output="$1"
  local path
  for path in \
    "$output/customer-support-resolution.md" \
    "$output/status.json" \
    "$output/operator-approval-receipt.json" \
    "$output/finance-refund-request.json"; do
    [[ ! -e "$path" ]] || die "final artifact exists before operator decision: $path"
  done
}

run_with_approval_gate() {
  local runtime="$1" output="$2" config="$3" session="$4" gateway="$5" approval_url="$6" approval_id="$7" nonce="$8" transcript="$9" decision="${10:-}"
  if [[ "$DEMO_OUTPUT" == quiet ]]; then
    import_and_execute "$runtime" "$output" "$config" "$session" "$gateway" "$approval_url" "$approval_id" "$nonce" \
      >"$transcript" 2>&1 &
  else
    import_and_execute "$runtime" "$output" "$config" "$session" "$gateway" "$approval_url" "$approval_id" "$nonce" \
      > >(tee "$transcript") 2>&1 &
  fi
  local worker_pid="$!"
  PIDS+=("$worker_pid")

  wait_for_approval_request "$approval_url" "$approval_id" "$worker_pid" || {
    cat "$transcript" >&2 || true
    die "n8n did not reach the operator approval gate; full output is in $transcript"
  }
  assert_no_final_artifacts "$output"

  if [[ -n "$decision" ]]; then
    curl --fail --silent --show-error \
      -H 'Accept: application/json' \
      -H 'Content-Type: application/json' \
      -d '{"operator":"validation-operator"}' \
      "$approval_url/approval/$approval_id/$decision" >/dev/null
  else
    say
    say 'HUMAN APPROVAL REQUIRED'
    say '────────────────────────────────────────────────────────────'
    curl -fsS "$approval_url/requests/$approval_id" | jq -r '
      .request
      | "Ticket           " + .ticket_id,
        "Requested action " + .requested_action,
        "Amount           EUR " + (.amount_eur|tostring),
        "Talon session    " + .session_id,
        "AI action        blocked by Talon before provider dispatch",
        "Refund           not executed"
    '
    say '────────────────────────────────────────────────────────────'
    say 'Open the approval page:'
    say "  $approval_url/approval/$approval_id"
    say
    say 'Or, from another shell on this host:'
    say '  make approve-n8n-support-resolution'
    say '  make reject-n8n-support-resolution'
    say
    say 'The workflow is blocked. No final status or finance handoff exists yet.'
  fi

  if ! wait "$worker_pid"; then
    cat "$transcript" >&2 || true
    die "n8n support-resolution case failed after the operator gate; full output is in $transcript"
  fi
}

assert_output_contract() {
  local output="$1" session="$2" nonce="$3" key_file="$4" expected_decision="$5"
  local report="$output/customer-support-resolution.md"
  local status="$output/status.json"
  local receipt="$output/operator-approval-receipt.json"
  local finance="$output/finance-refund-request.json"
  [[ -s "$report" ]] || die 'n8n did not produce customer-support-resolution.md'
  [[ -s "$status" ]] || die 'n8n did not produce support-resolution status.json'
  [[ -s "$receipt" ]] || die 'n8n did not preserve the signed operator approval receipt'

  grep -Fq 'Best regards,' "$report" || die 'support reply lacks deterministic closing'
  grep -Fq 'ACME Support Team' "$report" || die 'support reply lacks deterministic application-owned signature'
  ! grep -Eq '\[\[[^]]+\]\]' "$report" || die 'support reply contains a redaction placeholder'
  ! grep -Fq 'anna.kowalska@example.test' "$report" || die 'support reply contains raw synthetic email'
  ! grep -Fq 'PL61109010140000071219812874' "$report" || die 'support reply contains raw synthetic IBAN'
  ! grep -Eiq 'refund (has been|was|is) (issued|completed|processed)|money (has been|was) returned' "$report" \
    || die 'support reply incorrectly claims the refund was executed'

  jq -e --arg session "$session" --arg nonce "$nonce" --arg decision "$expected_decision" '
    .status == "completed"
    and .session_id == $session
    and .run_nonce == $nonce
    and .operational_id == "customer-support"
    and .documents_read >= 3
    and .ticket_id == "SUP-1042"
    and .refund_amount_eur == 249
    and .reply_draft_created == true
    and .blocked_tool == "issue_refund"
    and .denial_code == "tool_governance_block"
    and .denied_provider_cost_usd == 0
    and .operator_approval_required == true
    and .human_approval_completed == true
    and .operator_decision == $decision
    and .entry_requested_model == "llama3.2:1b"
    and .fallback_target_model == "gpt-4o-mini"
    and (.provider_reported_model | type == "string" and length > 0)
    and .refund_executed == false
  ' "$status" >/dev/null || die 'status.json does not match the operator-gated support contract'

  if [[ "$expected_decision" == approved ]]; then
    jq -e '.result == "governed_support_resolution" and .action_status == "approved_for_finance_processing" and .finance_handoff_file == "finance-refund-request.json"' "$status" >/dev/null \
      || die 'approved status does not record the synthetic finance handoff'
    [[ -s "$finance" ]] || die 'approved workflow did not create finance-refund-request.json'
    python3 "$APPROVAL_VERIFY" \
      --receipt "$receipt" --key "$key_file" --session "$session" --run-nonce "$nonce" \
      --ticket SUP-1042 --amount 249 --action issue_refund --decision approved \
      --finance-handoff "$finance" >/dev/null
  else
    jq -e '.result == "governed_support_resolution_rejected" and .action_status == "human_rejected" and .finance_handoff_file == null' "$status" >/dev/null \
      || die 'rejected status does not record the operator rejection'
    [[ ! -e "$finance" ]] || die 'rejected workflow created a finance handoff'
    python3 "$APPROVAL_VERIFY" \
      --receipt "$receipt" --key "$key_file" --session "$session" --run-nonce "$nonce" \
      --ticket SUP-1042 --amount 249 --action issue_refund --decision rejected >/dev/null
  fi

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
    and all(.[];
      .id == "talonSupportResolution01"
      and any(.nodes[]; .name == "Wait for Operator Decision")
      and any(.nodes[]; .name == "Write Finance Handoff")
      and any(.nodes[]; .name == "Write Rejected Status"))' "$exported" >/dev/null \
    || die 'exported support-resolution workflow lost its operator-gated graph'
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
  local work port log key gateway approval_port approval_state approval_key approval_url rendered
  work="$(mktemp -d "${TMPDIR:-/tmp}/talon-n8n-support-resolution.XXXXXX")"
  port="$(free_port)"
  log="$work/mock-talon.jsonl"
  key="n8n-support-resolution-validation-key"
  gateway="http://127.0.0.1:$port"
  approval_port="$(free_port)"
  approval_state="$work/approval-state"
  approval_key="$work/approval.key"
  openssl rand -hex 32 >"$approval_key"
  chmod 0600 "$approval_key"
  start_approval_server "$approval_state" "$approval_key" "$approval_port"
  approval_url="$APPROVAL_URL"
  rendered="$work/rendered-workflow.json"
  render_workflow "$rendered"
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

  local session1 nonce1 approval1 transcript1
  session1="n8n-support-clean-one-$(openssl rand -hex 3)"
  nonce1="$(openssl rand -hex 16)"
  approval1="$(approval_id_for "$session1" "$nonce1")"
  transcript1="$work/run-one.log"
  prepare_config "$work/config-one" "$rendered" "$key"
  run_with_approval_gate "$work/runtime-one" "$work/output-one" "$work/config-one" "$session1" "$gateway" "$approval_url" "$approval1" "$nonce1" "$transcript1" approve
  assert_output_contract "$work/output-one" "$session1" "$nonce1" "$approval_key" approved
  assert_clean_export "$work/config-one/imported-workflows.json" "$key"
  assert_mock_receipts "$log" "$session1" "$key"

  local session2 nonce2 approval2 transcript2
  session2="n8n-support-clean-two-$(openssl rand -hex 3)"
  nonce2="$(openssl rand -hex 16)"
  approval2="$(approval_id_for "$session2" "$nonce2")"
  transcript2="$work/run-two.log"
  prepare_config "$work/config-two" "$work/config-one/imported-workflows.json" "$key"
  run_with_approval_gate "$work/runtime-two" "$work/output-two" "$work/config-two" "$session2" "$gateway" "$approval_url" "$approval2" "$nonce2" "$transcript2" approve
  assert_output_contract "$work/output-two" "$session2" "$nonce2" "$approval_key" approved
  assert_clean_export "$work/config-two/imported-workflows.json" "$key"
  assert_mock_receipts "$log" "$session2" "$key"

  local session3 nonce3 approval3 transcript3
  session3="n8n-support-reject-$(openssl rand -hex 3)"
  nonce3="$(openssl rand -hex 16)"
  approval3="$(approval_id_for "$session3" "$nonce3")"
  transcript3="$work/run-three.log"
  prepare_config "$work/config-three" "$rendered" "$key"
  run_with_approval_gate "$work/runtime-three" "$work/output-three" "$work/config-three" "$session3" "$gateway" "$approval_url" "$approval3" "$nonce3" "$transcript3" reject
  assert_output_contract "$work/output-three" "$session3" "$nonce3" "$approval_key" rejected
  assert_mock_receipts "$log" "$session3" "$key"

  rm -rf "$work"
  say 'N8N SUPPORT RESOLUTION VALIDATION PASSED'
  say '  workflow blocked until an explicit approval or rejection bound to the current session and nonce'
  say '  approval created a signed receipt and synthetic finance handoff; rejection created no handoff'
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

  local config output runtime gateway transcript rendered approval_state approval_key approval_port approval_url approval_id
  config="$STATE/n8n-support-resolution-config"
  output="$STATE/n8n-support-resolution-output"
  runtime="$STATE/n8n-support-resolution-runtime"
  gateway="http://127.0.0.1:8080"
  transcript="$STATE/n8n-support-resolution-$(date -u +%Y%m%dT%H%M%SZ).log"
  rendered="$STATE/n8n-support-resolution-workflow.rendered.json"
  approval_state="$STATE/n8n-support-resolution-approval-state"
  approval_key="$STATE/$TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID.approval.key"
  approval_port="$(free_port)"
  approval_id="$(approval_id_for "$TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID" "$RELEASE_RUN_NONCE")"

  rm -rf "$config" "$output" "$runtime" "$approval_state"
  rm -f "$approval_key"
  render_workflow "$rendered"
  prepare_config "$config" "$rendered" "$TALON_CUSTOMER_SUPPORT_KEY"
  start_approval_server "$approval_state" "$approval_key" "$approval_port"
  approval_url="$APPROVAL_URL"
  write_approval_env "$approval_url" "$approval_id" "$TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID" "$RELEASE_RUN_NONCE" "$approval_key" "$approval_state"

  say 'Running the committed customer-support resolution through Talon...'
  run_with_approval_gate \
    "$runtime" "$output" "$config" "$TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID" "$gateway" \
    "$approval_url" "$approval_id" "$RELEASE_RUN_NONCE" "$transcript" "${TALON_SUPPORT_APPROVAL_AUTO_DECISION:-}"

  local final_decision
  final_decision="$(jq -r '.operator_decision' "$output/status.json")"
  assert_output_contract "$output" "$TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID" "$RELEASE_RUN_NONCE" "$approval_key" "$final_decision"
  assert_clean_export "$config/imported-workflows.json" "$TALON_CUSTOMER_SUPPORT_KEY"

  say
  say 'REAL N8N SUPPORT RESOLUTION COMPLETED'
  say "  Session:     $TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID"
  say "  Decision:    $final_decision"
  say "  Resolution:  $output/customer-support-resolution.md"
  say "  Approval:    $output/operator-approval-receipt.json"
  if [[ "$final_decision" == approved ]]; then
    say "  Finance:     $output/finance-refund-request.json"
  else
    say '  Finance:     not created'
  fi
  say "  Status:      $output/status.json"
  say "  Transcript:  $transcript"
  say '  Next: make present-n8n-support-resolution-all'
}

case "$MODE" in
  validate) validate_mode ;;
  real) real_mode ;;
  *)
    cat >&2 <<'USAGE'
Usage: bash scripts/n8n-support-resolution.sh validate|real

validate  Clean-import twice with explicit auto-approval and exercise the rejection branch.
real      Run through real Talon, then block until the operator approves or rejects.
USAGE
    exit 2
    ;;
esac
