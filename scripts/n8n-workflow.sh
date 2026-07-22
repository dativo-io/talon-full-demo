#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
IMAGE="${N8N_IMAGE:-docker.n8n.io/n8nio/n8n:2.30.4}"
WORKFLOW="$ROOT/integrations/n8n/quarterly-compliance-workflow.json"
MODE="${1:-help}"
DEMO_OUTPUT="${N8N_DEMO_OUTPUT:-full}"
N8N_AGENT_CONFIG="$ROOT/config/generated/agents/document-summary/agent.talon.yaml"
N8N_AGENT_BACKUP="$STATE/document-summary.agent.before-n8n.yaml"
N8N_STAGED_BUDGET="0.00301"
PIDS=()
BUDGET_STAGED=0

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }

restore_real_n8n_budget() {
  [[ "$BUDGET_STAGED" == 1 ]] || return 0
  [[ -f "$N8N_AGENT_BACKUP" ]] || {
    echo "ERROR: staged n8n policy backup is missing: $N8N_AGENT_BACKUP" >&2
    return 1
  }
  if ! cp "$N8N_AGENT_BACKUP" "$N8N_AGENT_CONFIG"; then
    echo "ERROR: could not restore canonical document-summary policy; backup retained at $N8N_AGENT_BACKUP" >&2
    return 1
  fi
  rm -f "$N8N_AGENT_BACKUP"
  if command -v talon >/dev/null 2>&1; then
    talon validate --dir "$ROOT/config/generated/agents" >/dev/null \
      || { echo 'ERROR: restored document-summary policy failed Talon validation' >&2; return 1; }
  fi
  # The canonical product-demo registry reload interval is two seconds.
  sleep 3
  BUDGET_STAGED=0
}

cleanup() {
  local pid cleanup_rc=0
  set +e
  restore_real_n8n_budget || cleanup_rc=$?
  for pid in "${PIDS[@]:-}"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  done
  return "$cleanup_rc"
}
trap 'rc=$?; trap - EXIT; cleanup_rc=0; cleanup || cleanup_rc=$?; if [[ "$rc" -eq 0 && "$cleanup_rc" -ne 0 ]]; then rc=$cleanup_rc; fi; exit "$rc"' EXIT

require_common() {
  for cmd in docker jq curl python3 openssl id; do need "$cmd"; done
  docker info >/dev/null 2>&1 || die 'Docker daemon is not available'
  [[ -s "$WORKFLOW" ]] || die "missing workflow artifact: $WORKFLOW"
  jq -e '.id and .name and (.nodes | length > 0)' "$WORKFLOW" >/dev/null \
    || die 'committed n8n workflow is not valid import JSON'
  case "$DEMO_OUTPUT" in full|quiet) ;; *) die 'N8N_DEMO_OUTPUT must be full or quiet' ;; esac
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
  install -d -m 0700 "$runtime" "$output" "$config"
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
    -e TALON_N8N_SESSION_ID="$session" \
    -e TALON_N8N_GATEWAY_URL="$gateway" \
    -v "$runtime:/home/node/.n8n" \
    -v "$ROOT/cases/quarterly-report:/demo/input:ro" \
    -v "$output:/demo/output" \
    -v "$config:/demo/config" \
    "$IMAGE" "$@"
}

prepare_config() {
  local config="$1" workflow_source="$2" key="$3"
  install -d -m 0700 "$config"
  cp "$workflow_source" "$config/workflow.json"
  TALON_DOCUMENT_SUMMARY_KEY="$key" \
    "$ROOT/scripts/render-n8n-credential.sh" "$config/credential.json" >/dev/null
  chmod 0644 "$config/workflow.json"
}

import_and_execute() {
  local runtime="$1" output="$2" config="$3" session="$4" gateway="$5"
  install -d -m 0700 "$runtime" "$output" "$config"
  rm -f "$output"/*.summary.md "$output/status.json" 2>/dev/null || true

  run_n8n "$runtime" "$output" "$config" "$session" "$gateway" \
    import:credentials --input=/demo/config/credential.json >/dev/null
  run_n8n "$runtime" "$output" "$config" "$session" "$gateway" \
    import:workflow --input=/demo/config/workflow.json >/dev/null
  run_n8n "$runtime" "$output" "$config" "$session" "$gateway" \
    export:workflow --all --output=/demo/config/imported-workflows.json >/dev/null

  local workflow_id
  workflow_id="$(jq -r 'if type == "array" then .[0].id else .id end' "$config/imported-workflows.json")"
  [[ -n "$workflow_id" && "$workflow_id" != null ]] || die 'could not resolve imported n8n workflow id'

  run_n8n "$runtime" "$output" "$config" "$session" "$gateway" \
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
  if [[ "$MODE" == validate ]]; then
    grep -Fq 'Synthetic compliance summary.' "${summaries[0]}" \
      || die 'mock n8n summary did not contain provider output'
  fi
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
  jq -s -e --arg session "$session" --arg auth "Bearer $key" '
    [ .[] | select(.headers["x-talon-session-id"] == $session) ] as $r
    | ($r | length) == 2
    and $r[0].denied == false
    and $r[1].denied == true
    and $r[1].cost_usd == 0
    and all($r[]; .path == "/v1/proxy/anthropic/v1/messages")
    and all($r[]; .headers.authorization == $auth)
    and all($r[]; .headers["x-talon-client"] == "n8n-quarterly-report-full-demo")
  ' "$log" >/dev/null || die 'mock receipts do not prove sequential allow-then-budget-deny behavior'
}

recover_stale_budget_stage() {
  [[ -f "$N8N_AGENT_BACKUP" ]] || return 0
  say 'Recovering canonical document-summary policy from an interrupted n8n run...'
  BUDGET_STAGED=1
  restore_real_n8n_budget
}

stage_real_n8n_budget() {
  need talon
  [[ -f "$N8N_AGENT_CONFIG" ]] || die "missing generated document-summary config: $N8N_AGENT_CONFIG"
  [[ -f "$ROOT/TALON_PINNED_COMMIT" && -f "$ROOT/config/generated/TALON_SOURCE_COMMIT" ]] \
    || die 'missing Talon pin/source metadata; rerun make real-prepare'

  local pin source
  pin="$(tr -d '[:space:]' <"$ROOT/TALON_PINNED_COMMIT")"
  source="$(tr -d '[:space:]' <"$ROOT/config/generated/TALON_SOURCE_COMMIT")"
  [[ "$source" == "$pin" ]] \
    || die "generated Talon config is from $source, but the demo is pinned to $pin; rerun make real-prepare from the pinned checkout"
  grep -Eq '^[[:space:]]+max_cost:[[:space:]]+0\.01([[:space:]]|$)' "$N8N_AGENT_CONFIG" \
    || die 'document-summary canonical session max_cost is not 0.01; refusing to overwrite an operator-modified policy'

  install -d -m 0700 "$STATE"
  cp "$N8N_AGENT_CONFIG" "$N8N_AGENT_BACKUP"
  chmod 0600 "$N8N_AGENT_BACKUP"
  BUDGET_STAGED=1

  python3 - "$N8N_AGENT_CONFIG" "$N8N_STAGED_BUDGET" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
cap = sys.argv[2]
text = path.read_text()
updated, count = re.subn(
    r'(?m)^(\s+max_cost:\s*)[0-9]+(?:\.[0-9]+)?(\s*(?:#.*)?)$',
    rf'\g<1>{cap}\2',
    text,
    count=1,
)
if count != 1:
    raise SystemExit('could not stage document-summary session budget')
path.write_text(updated)
PY

  talon validate --dir "$ROOT/config/generated/agents" >/dev/null
  # The pinned product-demo config reloads agents every two seconds.
  sleep 3

  umask 077
  cat >"$STATE/n8n-budget-stage.env" <<EOF
export TALON_N8N_CANONICAL_SESSION_BUDGET=0.01
export TALON_N8N_STAGED_SESSION_BUDGET=$N8N_STAGED_BUDGET
export TALON_N8N_BUDGET_SOURCE_COMMIT=$source
EOF
  chmod 0600 "$STATE/n8n-budget-stage.env"
}

validate_mode() {
  require_common
  local work port log key gateway session1 session2
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
  prepare_config "$work/config-one" "$WORKFLOW" "$key"
  import_and_execute "$work/runtime-one" "$work/output-one" "$work/config-one" "$session1" "$gateway" >/dev/null
  assert_output_contract "$work/output-one" "$session1"
  assert_clean_export "$work/config-one/imported-workflows.json" "$key"
  assert_mock_receipts "$log" "$session1" "$key"

  session2="n8n-clean-import-two-$(openssl rand -hex 3)"
  prepare_config "$work/config-two" "$work/config-one/imported-workflows.json" "$key"
  import_and_execute "$work/runtime-two" "$work/output-two" "$work/config-two" "$session2" "$gateway" >/dev/null
  assert_output_contract "$work/output-two" "$session2"
  assert_clean_export "$work/config-two/imported-workflows.json" "$key"
  assert_mock_receipts "$log" "$session2" "$key"

  rm -rf "$work"
  say 'N8N WORKFLOW VALIDATION PASSED'
  say '  committed workflow imported and executed against the budget contract'
  say '  credential-free export imported into a second clean n8n 2.30.4 runtime'
  say '  both runs preserved one completed section and stopped the next request at zero provider cost'
}

real_mode() {
  require_common
  need talon
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

  recover_stale_budget_stage
  "$ROOT/scripts/preflight.sh"
  # shellcheck disable=SC1091
  source "$STATE/demo-run.env"
  stage_real_n8n_budget

  local config output runtime gateway transcript
  config="$STATE/n8n-config"
  output="$STATE/n8n-output"
  runtime="$STATE/n8n-runtime"
  gateway="http://127.0.0.1:8080"
  transcript="$STATE/n8n-$(date -u +%Y%m%dT%H%M%SZ).log"
  rm -rf "$config" "$output" "$runtime"
  prepare_config "$config" "$WORKFLOW" "$TALON_DOCUMENT_SUMMARY_KEY"

  if [[ "$DEMO_OUTPUT" == quiet ]]; then
    say 'Running the committed n8n workflow through Talon...'
    {
      say "Staged session budget: \$$N8N_STAGED_BUDGET (canonical \$0.01 restored after the run)"
      import_and_execute "$runtime" "$output" "$config" "$TALON_N8N_SESSION_ID" "$gateway"
    } >"$transcript" 2>&1 || {
      cat "$transcript" >&2
      die "real n8n case failed; full output is in $transcript"
    }
  else
    say "Staged document-summary session budget at \$$N8N_STAGED_BUDGET for this run; canonical \$0.01 will be restored."
    import_and_execute "$runtime" "$output" "$config" "$TALON_N8N_SESSION_ID" "$gateway" \
      2>&1 | tee "$transcript"
  fi
  assert_output_contract "$output" "$TALON_N8N_SESSION_ID"
  assert_clean_export "$config/imported-workflows.json" "$TALON_DOCUMENT_SUMMARY_KEY"

  say
  say 'REAL N8N CASE COMPLETED'
  say "  Session: $TALON_N8N_SESSION_ID"
  say "  Output:  $output"
  say "  Transcript: $transcript"
  say '  Canonical document-summary policy will be restored on exit'
  say '  Next: make present-n8n-all'
}

case "$MODE" in
  validate) validate_mode ;;
  real) real_mode ;;
  *)
    cat >&2 <<'EOF'
Usage: bash scripts/n8n-workflow.sh validate|real

validate  Import, execute, export, clean-import, and execute again in pinned n8n 2.30.4 against mock Talon's budget contract.
real      Stage a run-scoped budget, run the committed workflow through Talon + Anthropic, then restore canonical policy.
EOF
    exit 2
    ;;
esac
