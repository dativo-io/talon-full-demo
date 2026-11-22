#!/usr/bin/env bash
set -euo pipefail

# Live end-to-end check against a REAL Talon server built from source — no
# mock gateway in the loop. Proves, executably, what docs/VALIDATION.md's
# "Executed live-server run" section records:
#
#   Phase 1 (canonical MCP scene): boot the canonical product-demo config,
#   verify the live fleet view, and run the MCP forbidden-tool scene through
#   Talon's governed POST /mcp (MCP 2026-07-28, Talon #431): the synthetic
#   release server is a trusted MCP action source of the coding-assistant use
#   case; release_status is read-only (one call), release_prepare is prepared
#   and then executed by talon_execute_operation (one call), release_publish
#   is forbidden (hidden, and denied with zero upstream calls when called by
#   name). Nonce-correlated receipts are counted at the upstream; every
#   operation's signed lifecycle is verified offline.
#
#   Phase 2 (session-budget engine): run allow/allow/deny through Talon's
#   REAL budget engine (#198/#283) against a synthetic OpenAI-compatible
#   provider — request 3 denied 403 session_budget_exceeded at zero cost.
#   The cap is measured at runtime (1.5x one request's actual cost), so the
#   scene is robust to pricing-table changes.
#
# Hermetic: everything lives in a temp dir with random keys and free ports;
# the repository's .env, .state, and config/generated are untouched.
#
# Requirements: a dativo-io/talon checkout (TALON_REPO, default ../talon),
# go, python3, jq, curl, openssl. TALON_BIN skips the talon build.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TALON_REPO="${TALON_REPO:-$ROOT/../talon}"
[[ -d "$TALON_REPO/examples/product-demo" ]] || {
  echo "TALON_REPO ($TALON_REPO) is not a Talon checkout; clone current dativo-io/talon main or set TALON_REPO" >&2
  exit 1
}
TALON_HEAD="$(git -C "$TALON_REPO" rev-parse HEAD)"
echo "Talon source checkout for this test: $TALON_HEAD"
# CI checks out current main for every run; local runners may intentionally
# inspect a different Talon checkout. Always report the tested source SHA.

WORK="$(mktemp -d "${TMPDIR:-/tmp}/talon-live-check.XXXXXX")"
PIDS=()
cleanup() {
  local pid
  for pid in "${PIDS[@]:-}"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  done
  # A killed Talon may still be flushing runtime/evidence state. Wait for the
  # owned child processes to exit before deleting the test-only temp store;
  # a concurrent runtime-file write must not turn PASS into a teardown race.
  for pid in "${PIDS[@]:-}"; do
    [[ -n "$pid" ]] && wait "$pid" 2>/dev/null || true
  done
  local attempt
  for attempt in 1 2 3 4 5; do
    if rm -rf "$WORK" 2>/dev/null; then
      return 0
    fi
    sleep 0.2
  done
  echo "ERROR: Talon live-check temp store could not be cleaned: $WORK" >&2
  return 1
}
trap cleanup EXIT

free_port() {
  python3 - <<'PYPORT'
import socket
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    print(sock.getsockname()[1])
PYPORT
}

wait_http() {
  local name="$1" url="$2" log="$3"
  for _ in $(seq 1 100); do
    if curl --fail --silent --max-time 1 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.2
  done
  echo "$name did not become healthy at $url; log follows" >&2
  cat "$log" >&2 || true
  exit 1
}

echo "== live check: building binaries =="
mkdir -p "$WORK/bin"
if [[ -n "${TALON_BIN:-}" ]]; then
  cp "$TALON_BIN" "$WORK/bin/talon"
else
  (cd "$TALON_REPO" && go build -o "$WORK/bin/talon" ./cmd/talon)
fi
(cd "$ROOT" && go build -o "$WORK/bin/release-mcp-server" ./cmd/release-mcp-server)
export PATH="$WORK/bin:$PATH"
export TALON_BIN="$WORK/bin/talon"

export TALON_SECRETS_KEY TALON_SIGNING_KEY TALON_ADMIN_KEY
TALON_SECRETS_KEY="$(openssl rand -hex 32)"
TALON_SIGNING_KEY="$(openssl rand -hex 32)"
TALON_ADMIN_KEY="$(openssl rand -hex 24)"
CS_KEY="$(openssl rand -hex 24)"
CA_KEY="$(openssl rand -hex 24)"
DS_KEY="$(openssl rand -hex 24)"
PROBE_KEY="$(openssl rand -hex 24)"

# ---------------------------------------------------------------------------
# Phase 1 — canonical config, MCP forbidden-tool scene, signed evidence
# ---------------------------------------------------------------------------
echo "== phase 1: canonical MCP scene against real Talon =="
# Capture the run start so the evidence assertions can prove records belong to
# THIS run (--since), exercising the same current-run constraint the presenter
# flow uses via TALON_RUN_START_RFC3339.
RUN_TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
CANON="$WORK/canonical"
mkdir -p "$CANON"
cp "$TALON_REPO/examples/product-demo/talon.config.yaml" "$CANON/talon.config.yaml"
cp -R "$TALON_REPO/examples/product-demo/agents" "$CANON/agents"
if [[ -f "$TALON_REPO/pricing/models.yaml" ]]; then
  mkdir -p "$CANON/pricing"
  cp "$TALON_REPO/pricing/models.yaml" "$CANON/pricing/models.yaml"
fi

# A synthetic OpenAI-compatible provider so the coding-assistant LLM call needs
# no real key/network. Only the temp copy of the canonical config is repointed
# at it; the repo's config is untouched.
PROV_LLM_PORT="$(free_port)"
cat > "$WORK/llm_provider.py" <<'PYLLM'
import json, os
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
PORT = int(os.environ['LLM_PORT'])
class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *a): pass
    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length', 0)))
        body = json.dumps({'id': 'chatcmpl-id', 'object': 'chat.completion', 'model': 'gpt-4o-mini',
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'ok'}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 5, 'total_tokens': 15}}).encode()
        self.send_response(200); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self):
        self.send_response(200); self.send_header('Content-Length', '2'); self.end_headers(); self.wfile.write(b'ok')
if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
PYLLM
LLM_PORT="$PROV_LLM_PORT" python3 "$WORK/llm_provider.py" > "$WORK/llm-provider.log" 2>&1 &
PIDS+=("$!")
# Repoint the openai provider base_url at the synthetic provider (in the temp copy only).
python3 - "$CANON/talon.config.yaml" "$PROV_LLM_PORT" <<'PYPATCH'
import re, sys
p, port = sys.argv[1], sys.argv[2]
text = open(p).read()
# Rewrite the openai provider's base_url to the local synthetic provider.
text = re.sub(r'(openai:\n(?:\s+.*\n)*?\s+base_url:\s*)"[^"]*"', r'\g<1>"http://127.0.0.1:%s"' % port, text, count=1)
open(p, 'w').write(text)
PYPATCH

export TALON_DATA_DIR="$WORK/data-canonical"
(cd "$CANON" \
  && talon secrets set local-llama-demo-key not-a-real-key-local-demo --tenant acme --agent customer-support \
  && talon secrets set openai-api-key sk-fake-live-check-only --tenant acme --agent customer-support --agent coding-assistant \
  && talon secrets set anthropic-api-key sk-ant-fake-live-check-only --tenant acme --agent document-summary \
  && talon secrets set customer-support-talon-key "$CS_KEY" --tenant acme --agent customer-support \
  && talon secrets set coding-assistant-talon-key "$CA_KEY" --tenant acme --agent coding-assistant \
  && talon secrets set document-summary-talon-key "$DS_KEY" --tenant acme --agent document-summary) >/dev/null

MCP_UP_PORT="$(free_port)"
GW_PORT="$(free_port)"
MCP_PORT="$(free_port)"
RECEIPTS="$WORK/receipts.jsonl"
: > "$RECEIPTS"
RELEASE_MCP_BIND="127.0.0.1:$MCP_UP_PORT" RELEASE_MCP_RECEIPTS="$RECEIPTS" \
  "$WORK/bin/release-mcp-server" > "$WORK/release-mcp.log" 2>&1 &
PIDS+=("$!")
wait_http release-mcp "http://127.0.0.1:$MCP_UP_PORT/health" "$WORK/release-mcp.log"

# The release server is a trusted MCP action source of the coding-assistant
# use case (Talon #431; the MCP proxy and --proxy-config were removed):
# declared in the temp copy of its agent file, never in the repository's.
cat >> "$CANON/agents/coding-assistant/agent.talon.yaml" <<YAMLACT

# Full Demo live check: the synthetic release MCP server as a governed source.
capabilities:
  forbidden_tools: [release_publish]
actions:
  sources:
    release:
      type: mcp
      url: "http://127.0.0.1:$MCP_UP_PORT/mcp"
  definitions:
    release_status:
      source: release
      read_only: true
      review: {fields: [version], non_material: [run_nonce]}
    release_prepare:
      source: release
      review: {fields: [version], non_material: [run_nonce]}
    release_publish:
      source: release
      review: {fields: [version], non_material: [run_nonce]}
YAMLACT
(cd "$CANON" && talon validate --file agents/coding-assistant/agent.talon.yaml >/dev/null) \
  || { echo 'the governed MCP source declaration does not validate' >&2; exit 1; }

# The demo's real topology: TWO Talon processes sharing one TALON_DATA_DIR (so
# LLM and MCP evidence land in the same signed store, joinable by session).
#   :GW  gateway  — LLM traffic, admin-gated native routes off
#   :MCP native serve (no --gateway) — the governed POST /mcp authenticates
#        the use case's key (never the admin key), so MCP evidence attributes
#        to the authenticated agent (coding-assistant). exec so $! is talon's
#        real PID. Both processes discover the release source at start, so
#        the release server is already healthy.
( cd "$CANON" && exec talon serve --host 127.0.0.1 --port "$GW_PORT" --gateway \
  > "$WORK/talon-gateway.log" 2>&1 ) &
PIDS+=("$!")
wait_http talon-gateway "http://127.0.0.1:$GW_PORT/health" "$WORK/talon-gateway.log"
( cd "$CANON" && exec talon serve --host 127.0.0.1 --port "$MCP_PORT" \
  > "$WORK/talon-mcp.log" 2>&1 ) &
PIDS+=("$!")
wait_http talon-mcp "http://127.0.0.1:$MCP_PORT/health" "$WORK/talon-mcp.log"

AGENT_COUNT="$(talon agents --url "http://127.0.0.1:$GW_PORT" --json | jq 'if type == "array" then length else (.agents // .rows // []) | length end')"
[[ "$AGENT_COUNT" == "3" ]] || { echo "expected 3 agents in the live fleet view, got $AGENT_COUNT" >&2; exit 1; }
echo "live fleet view: 3 agents"

SESSION_MCP="live-check-copilot"
NONCE="$(openssl rand -hex 16)"

# 1) An LLM call through the gateway as coding-assistant, same session as the
#    MCP scene — establishes the coding-assistant identity on the LLM side.
LLM_CODE="$(curl --silent --output "$WORK/llm.json" --write-out '%{http_code}' --max-time 15 \
  "http://127.0.0.1:$GW_PORT/v1/proxy/openai/v1/chat/completions" \
  -H "Authorization: Bearer $CA_KEY" -H "X-Talon-Session-ID: $SESSION_MCP" \
  -H 'X-Talon-Client: live-check' -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"draft release note"}]}')"
[[ "$LLM_CODE" == "200" ]] || { echo "coding-assistant LLM call failed: HTTP $LLM_CODE" >&2; cat "$WORK/llm.json" >&2; exit 1; }
echo "LLM call: coding-assistant reached the gateway (session $SESSION_MCP)"

# 2) The MCP scene through the native serve's governed /mcp — the use case's
#    key only, NO admin key (the admin key is refused on /mcp).
MCP_URL="http://127.0.0.1:$MCP_PORT/mcp"
# Current Talon main enforces MCP 2026-07-28 (#447), with request
# _meta, explicit wire headers, and server/discover (no initialize).
mcp() {
  local body="$1" method name
  method="$(jq -r '.method' <<<"$body")"
  name="$(jq -r '.params.name // empty' <<<"$body")"
  body="$(jq -c '.params = (.params // {}) | .params._meta = {
    "io.modelcontextprotocol/protocolVersion": "2026-07-28",
    "io.modelcontextprotocol/clientInfo": {"name":"live-check","version":"1.0"},
    "io.modelcontextprotocol/clientCapabilities": {}
  }' <<<"$body")"
  local -a extra=()
  if [[ "$method" == "tools/call" ]]; then
    extra+=( -H "Mcp-Name: $name" )
  fi
  curl --fail --silent --show-error --max-time 10 "$MCP_URL" \
    -H "Authorization: Bearer $CA_KEY" \
    -H "X-Talon-Session-ID: $SESSION_MCP" \
    -H "X-Talon-Client: live-check" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "MCP-Protocol-Version: 2026-07-28" \
    -H "Mcp-Method: $method" \
    "${extra[@]}" \
    -d "$body"
}

mcp '{"jsonrpc":"2.0","id":1,"method":"server/discover","params":{}}' \
  | jq -e '.result.capabilities.extensions["io.dativo.talon/governance"].schemaVersion == 1' >/dev/null \
  || { echo 'MCP server/discover did not advertise governance extension (#372)' >&2; exit 1; }
LIST="$(mcp '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}')"
echo "$LIST" | jq -e '[.result.tools[].name] | sort == ["release_prepare","release_status","talon_execute_operation"]' >/dev/null \
  || { echo 'tools/list must advertise exactly the two governed tools and talon_execute_operation' >&2; echo "$LIST" >&2; exit 1; }
echo "$LIST" | jq -e '[.result.tools[].name] | index("release_publish") | not' >/dev/null \
  || { echo 'preventive filtering failed: release_publish must be ABSENT from tools/list discovery' >&2; exit 1; }
echo "$LIST" | jq -e 'all(.result.tools[] | select(.name != "talon_execute_operation"); (.inputSchema.required // []) | index("run_nonce"))' >/dev/null \
  || { echo 'each governed tool must mark run_nonce required (schema-driven client would else omit it)' >&2; exit 1; }
echo "control A (preventive filtering): release_publish absent from discovery; governed tools require run_nonce"
receipts_for() { jq -s --arg t "$1" --arg n "$NONCE" '[.[] | select(.tool == $t and .arguments.run_nonce == $n)] | length' "$RECEIPTS"; }
gov() { jq -r '(.result._meta // .error.data)["io.dativo.talon/governance"] | '"$1"; }
OPS=()

# release_status is read-only (trusted Talon overlay): one call, one receipt.
OUT="$(mcp "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"release_status\",\"arguments\":{\"version\":\"live\",\"run_nonce\":\"$NONCE\"}}}")"
jq -e '.result.isError == false' <<<"$OUT" >/dev/null && [[ "$(gov .code <<<"$OUT")" == "allowed" ]] \
  || { echo "read-only release_status failed through the governed /mcp: $OUT" >&2; exit 1; }
[[ "$(receipts_for release_status)" == "1" ]] || { echo "release_status: expected 1 upstream receipt, got $(receipts_for release_status)" >&2; exit 1; }
OPS+=("$(gov .operationId <<<"$OUT")")

# release_prepare is consequential: the first call PREPARES (operation id,
# nothing sent), talon_execute_operation executes it exactly once.
OUT="$(mcp "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"release_prepare\",\"arguments\":{\"version\":\"live\",\"run_nonce\":\"$NONCE\"}}}")"
PREP_OP="$(gov .operationId <<<"$OUT")"
[[ "$(gov .code <<<"$OUT")" == "operation_prepared" && -n "$PREP_OP" ]] \
  || { echo "release_prepare must be prepared first: $OUT" >&2; exit 1; }
[[ "$(receipts_for release_prepare)" == "0" ]] || { echo 'preparing release_prepare reached the upstream' >&2; exit 1; }
OUT="$(mcp "{\"jsonrpc\":\"2.0\",\"id\":5,\"method\":\"tools/call\",\"params\":{\"name\":\"talon_execute_operation\",\"arguments\":{\"operation_id\":\"$PREP_OP\"}}}")"
jq -e '.result.isError == false' <<<"$OUT" >/dev/null && [[ "$(gov .code <<<"$OUT")" == "allowed" ]] \
  || { echo "talon_execute_operation for release_prepare failed: $OUT" >&2; exit 1; }
OUT="$(mcp "{\"jsonrpc\":\"2.0\",\"id\":6,\"method\":\"tools/call\",\"params\":{\"name\":\"talon_execute_operation\",\"arguments\":{\"operation_id\":\"$PREP_OP\"}}}")"
[[ "$(gov .code <<<"$OUT")" == "operation_already_succeeded" ]] || { echo "a repeated execute must be refused: $OUT" >&2; exit 1; }
[[ "$(receipts_for release_prepare)" == "1" ]] || { echo "release_prepare: expected exactly 1 upstream receipt, got $(receipts_for release_prepare)" >&2; exit 1; }
OPS+=("$PREP_OP")
echo "allowed calls: release_status 1 receipt (read-only), release_prepare 0 receipts when prepared, 1 when executed, still 1 after a repeat"

# Control B — runtime enforcement: an ADVERSARIAL probe (this curl, standing in
# for a non-conforming client) submits the undiscovered release_publish anyway.
# Talon must still block it. This is defence-in-depth, NOT "Copilot published".
OUT="$(mcp "{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"tools/call\",\"params\":{\"name\":\"release_publish\",\"arguments\":{\"version\":\"live\",\"run_nonce\":\"$NONCE\"}}}")"
jq -e '.error.data["io.dativo.talon/governance"].code == "policy_denied" and .error.data["io.dativo.talon/governance"].decision == "deny" and .error.data["io.dativo.talon/governance"].evidence.committed == true' <<<"$OUT" >/dev/null \
  || { echo "release_publish denial must carry committed policy_denied governance extension (#372): $OUT" >&2; exit 1; }
[[ "$(receipts_for release_publish)" == "0" ]] || { echo 'release_publish reached the upstream' >&2; exit 1; }
OPS+=("$(gov .operationId <<<"$OUT")")
echo "control B (runtime enforcement): adversarial release_publish probe denied (policy_denied), 0 upstream receipts"

RELEASE_RUN_NONCE="$NONCE" RELEASE_MCP_RECEIPTS="$RECEIPTS" \
  "$ROOT/scripts/assert-release-blocked.sh" >/dev/null
if RELEASE_RUN_NONCE="stale-run" RELEASE_MCP_RECEIPTS="$RECEIPTS" \
  "$ROOT/scripts/assert-release-blocked.sh" >/dev/null 2>&1; then
  echo 'assert-release-blocked accepted receipts from a different run' >&2
  exit 1
fi
echo "receipts: nonce-correlated proof passes; stale nonce rejected"

# The identity story: EVERY record in the session — the LLM call and every
# governed MCP lifecycle record (joined to the client's session by its
# X-Talon-Session-ID, as untrusted attribution) — must carry
# agent_id=coding-assistant (assert-evidence enforces that all records share
# the agent), and the forbidden-tool denial must be present.
"$ROOT/scripts/assert-evidence.sh" --session "$SESSION_MCP" --agent coding-assistant \
  --min-denials 1 --deny-reason "action forbidden by use_case policy (forbidden_tools: release_publish)" --since "$RUN_TS"
echo "identity: LLM and MCP records share agent_id=coding-assistant"
for op in "${OPS[@]}"; do
  talon audit verify --operation "$op" | grep -q 'Lifecycle: VALID' \
    || { echo "signed lifecycle of $op does not verify" >&2; exit 1; }
done
echo "signed lifecycle: ${#OPS[@]} governed MCP operations verify (talon audit verify --operation)"

# ---------------------------------------------------------------------------
# Phase 2 — session-budget engine: allow / allow / deny with a measured cap
# ---------------------------------------------------------------------------
echo "== phase 2: session-budget engine against real Talon =="
BUDGET="$WORK/budget"
mkdir -p "$BUDGET/agents/budget-probe"
PROV_PORT="$(free_port)"
BUDGET_PORT="$(free_port)"

cat > "$WORK/fake_provider.py" <<'PYPROV'
import json, os
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ['FAKE_PORT'])

# Large usage numbers make one request's REAL cost dwarf the fixed 500/500
# pre-request estimate, so the measured 1.5x cap denies exactly at request 3
# regardless of pricing-table values.
class H(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def log_message(self, *a): pass
    def do_POST(self):
        self.rfile.read(int(self.headers.get('Content-Length', 0)))
        body = json.dumps({'id': 'chatcmpl-live', 'object': 'chat.completion', 'model': 'gpt-4o-mini',
            'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'synthetic live-check reply'}, 'finish_reason': 'stop'}],
            'usage': {'prompt_tokens': 400000, 'completion_tokens': 400000, 'total_tokens': 800000}}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Length', '2')
        self.end_headers()
        self.wfile.write(b'ok')

if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
PYPROV
FAKE_PORT="$PROV_PORT" python3 "$WORK/fake_provider.py" > "$WORK/fake-provider.log" 2>&1 &
PIDS+=("$!")

cat > "$BUDGET/talon.config.yaml" <<EOF
gateway:
  enabled: true
  listen_prefix: "/v1/proxy"
  providers:
    mock-openai:
      enabled: true
      secret_name: "mock-openai-key"
      base_url: "http://127.0.0.1:$PROV_PORT"
      region: "LOCAL"
      api_family: "openai"
      allowed_models: ["gpt-4o-mini"]
  organization_policy:
    defaults:
      pii_action: "warn"
      tool_policy_action: "block"
    log_prompts: false
    log_responses: false
  rate_limits:
    global_requests_per_min: 600
    per_agent_requests_per_min: 120
  timeouts:
    connect_timeout: 5s
    request_timeout: 60s
    stream_idle_timeout: 60s
agents_dir: agents
agents_reload_interval: "2s"
EOF

# Current main treats a missing price as a safety denial (#399). Explicitly
# price the local OpenAI-wire fixture: it is a counted synthetic commercial
# endpoint, not a zero-cost local LLM. Keep this under the temp directory.
mkdir -p "$BUDGET/pricing"
cat > "$BUDGET/pricing/models.yaml" <<'YAMLPRICE'
version: "1"
currency: USD
providers:
  openai:
    models:
      gpt-4o-mini:
        input_per_1m: 0.15
        output_per_1m: 0.60
  mock-openai:
    inherit: openai
YAMLPRICE

write_probe_agent() {
  local max_cost="$1"
  cat > "$BUDGET/agents/budget-probe/agent.talon.yaml" <<EOF
agent:
  name: budget-probe
  description: "Live-check probe agent for the session-budget scene"
  version: "1.0.0"
  tenant_id: acme
  key:
    secret_name: budget-probe-talon-key
policies:
  allowed_providers: ["mock-openai"]
  cost_limits:
    monthly: 100.00
  session_limits:
    max_cost: $max_cost
EOF
}
write_probe_agent 0   # 0 = no session budget for the measurement probe

export TALON_DATA_DIR="$WORK/data-budget"
(cd "$BUDGET" \
  && talon secrets set mock-openai-key fake-key-live-check --tenant acme --agent budget-probe \
  && talon secrets set budget-probe-talon-key "$PROBE_KEY" --tenant acme --agent budget-probe) >/dev/null

start_budget_talon() {
  # exec so BUDGET_TALON_PID is talon's real PID; otherwise the restart below
  # would kill only the subshell and the cap-0 server would keep answering.
  ( cd "$BUDGET" && exec talon serve --host 127.0.0.1 --port "$BUDGET_PORT" --gateway \
    > "$WORK/talon-budget.log" 2>&1 ) &
  BUDGET_TALON_PID="$!"
  PIDS+=("$BUDGET_TALON_PID")
  wait_http talon-budget "http://127.0.0.1:$BUDGET_PORT/health" "$WORK/talon-budget.log"
}
budget_call() {
  local session="$1" out="$2"
  curl --silent --output "$out" --write-out '%{http_code}' --max-time 15 \
    "http://127.0.0.1:$BUDGET_PORT/v1/proxy/mock-openai/v1/chat/completions" \
    -H "Authorization: Bearer $PROBE_KEY" -H 'Content-Type: application/json' \
    -H "X-Talon-Session-ID: $session" \
    -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"live budget scene"}]}'
}

start_budget_talon
[[ "$(budget_call live-check-probe "$WORK/probe.json")" == "200" ]] \
  || { echo 'budget measurement probe was not allowed' >&2; cat "$WORK/probe.json" >&2; exit 1; }
talon audit export --format signed-json --session live-check-probe --output "$WORK/probe-evidence.json" >/dev/null
ACTUAL_COST="$(jq '[.records[].execution.cost] | add' "$WORK/probe-evidence.json")"
python3 -c "import sys; sys.exit(0 if ($ACTUAL_COST) > 0 else 1)" \
  || { echo "probe request cost must be positive, got $ACTUAL_COST" >&2; exit 1; }
CAP="$(python3 -c "print('%.6f' % (1.5 * ($ACTUAL_COST)))")"
echo "measured per-request cost $ACTUAL_COST; session cap set to $CAP"

kill "$BUDGET_TALON_PID" 2>/dev/null || true
for _ in $(seq 1 50); do
  curl --silent --max-time 1 "http://127.0.0.1:$BUDGET_PORT/health" >/dev/null 2>&1 || break
  sleep 0.2
done
write_probe_agent "$CAP"
start_budget_talon

SESSION_BUDGET="live-check-budget"
[[ "$(budget_call "$SESSION_BUDGET" "$WORK/b1.json")" == "200" ]] || { echo 'budget request 1 not allowed' >&2; exit 1; }
[[ "$(budget_call "$SESSION_BUDGET" "$WORK/b2.json")" == "200" ]] || { echo 'budget request 2 not allowed' >&2; exit 1; }
[[ "$(budget_call "$SESSION_BUDGET" "$WORK/b3.json")" == "403" ]] || { echo 'budget request 3 not denied' >&2; cat "$WORK/b3.json" >&2; exit 1; }
jq -e '.error.code == "session_budget_exceeded"' "$WORK/b3.json" >/dev/null \
  || { echo 'denial body must carry code session_budget_exceeded' >&2; cat "$WORK/b3.json" >&2; exit 1; }
echo "budget engine: request 1 allowed, request 2 allowed, request 3 denied 403 session_budget_exceeded"

"$ROOT/scripts/assert-evidence.sh" --session "$SESSION_BUDGET" --agent budget-probe \
  --min-denials 1 --deny-reason session_budget_exceeded --since "$RUN_TS"

echo "LIVE CHECK PASSED against Talon $TALON_HEAD"
