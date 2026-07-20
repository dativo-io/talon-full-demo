#!/usr/bin/env bash
set -euo pipefail

# Live end-to-end check against a REAL Talon server built from source — no
# mock gateway in the loop. Proves, executably, what docs/VALIDATION.md's
# "Executed live-server run" section records:
#
#   Phase 1 (canonical MCP scene): boot the canonical product-demo config,
#   verify the live fleet view, run the MCP forbidden-tool scene through
#   /mcp/proxy (local initialize handshake #367, nonce-correlated allowed
#   calls, TALON_TOOL_FORBIDDEN denial #369, receipts assertion positive and
#   negative), and verify the signed evidence offline.
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
PIN="$(cat "$ROOT/TALON_PINNED_COMMIT")"

[[ -d "$TALON_REPO/examples/product-demo" ]] || {
  echo "TALON_REPO ($TALON_REPO) is not a Talon checkout; clone dativo-io/talon next to this repository or set TALON_REPO" >&2
  exit 1
}
TALON_HEAD="$(git -C "$TALON_REPO" rev-parse HEAD 2>/dev/null || echo unknown)"
if [[ "$TALON_HEAD" != "$PIN" ]]; then
  # Hosted CI sets TALON_STRICT_PIN=1 so an unpinned checkout is a hard failure,
  # not a warning: the executed contract must be against the audited commit.
  if [[ "${TALON_STRICT_PIN:-0}" == "1" ]]; then
    echo "ERROR: TALON_REPO is at $TALON_HEAD; TALON_STRICT_PIN requires $PIN (TALON_PINNED_COMMIT)" >&2
    exit 1
  fi
  echo "WARNING: TALON_REPO is at $TALON_HEAD; this demo is audited against $PIN (TALON_PINNED_COMMIT)" >&2
fi

WORK="$(mktemp -d "${TMPDIR:-/tmp}/talon-live-check.XXXXXX")"
PIDS=()
cleanup() {
  local pid
  for pid in "${PIDS[@]:-}"; do
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
  done
  rm -rf "$WORK"
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
MCP_PROXY_PORT="$(free_port)"
RECEIPTS="$WORK/receipts.jsonl"
: > "$RECEIPTS"
RELEASE_MCP_BIND="127.0.0.1:$MCP_UP_PORT" RELEASE_MCP_RECEIPTS="$RECEIPTS" \
  "$WORK/bin/release-mcp-server" > "$WORK/release-mcp.log" 2>&1 &
PIDS+=("$!")
wait_http release-mcp "http://127.0.0.1:$MCP_UP_PORT/health" "$WORK/release-mcp.log"

sed "s|http://127.0.0.1:8090/mcp|http://127.0.0.1:$MCP_UP_PORT/mcp|" \
  "$ROOT/config/mcp-proxy.example.yaml" > "$WORK/mcp-proxy.yaml"
grep -q "127.0.0.1:$MCP_UP_PORT/mcp" "$WORK/mcp-proxy.yaml" \
  || { echo 'failed to point mcp-proxy config at the synthetic upstream' >&2; exit 1; }

# The demo's real topology: TWO Talon processes sharing one TALON_DATA_DIR (so
# LLM and MCP evidence land in the same signed store, joinable by session).
#   :GW  gateway  — LLM traffic, admin-gated native routes off
#   :MCP proxy-only (no --gateway) — /mcp/proxy authenticates with AGENT keys
#        (TenantKeyMiddleware), so MCP evidence attributes to the authenticated
#        agent (coding-assistant), NOT the proxy config's name, and needs no
#        admin key. exec so $! is talon's real PID.
( cd "$CANON" && exec talon serve --host 127.0.0.1 --port "$GW_PORT" --gateway \
  > "$WORK/talon-gateway.log" 2>&1 ) &
PIDS+=("$!")
wait_http talon-gateway "http://127.0.0.1:$GW_PORT/health" "$WORK/talon-gateway.log"
( cd "$CANON" && exec talon serve --host 127.0.0.1 --port "$MCP_PROXY_PORT" \
  --proxy-config "$WORK/mcp-proxy.yaml" > "$WORK/talon-mcp.log" 2>&1 ) &
PIDS+=("$!")
wait_http talon-mcp "http://127.0.0.1:$MCP_PROXY_PORT/health" "$WORK/talon-mcp.log"

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

# 2) The MCP scene through the PROXY-ONLY process — agent bearer only, NO admin
#    key. If the admin key were still required this call would 401.
MCP_URL="http://127.0.0.1:$MCP_PROXY_PORT/mcp/proxy"
mcp() {
  curl --fail --silent --show-error --max-time 10 "$MCP_URL" \
    -H "Authorization: Bearer $CA_KEY" \
    -H "X-Talon-Session-ID: $SESSION_MCP" \
    -H 'X-Talon-Client: live-check' \
    -H 'Content-Type: application/json' \
    -d "$1"
}

mcp '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"live-check","version":"0.0.1"}}}' \
  | jq -e '.result.serverInfo.name == "talon-mcp-proxy"' >/dev/null \
  || { echo 'MCP initialize was not answered locally by the proxy (#367)' >&2; exit 1; }
mcp '{"jsonrpc":"2.0","method":"notifications/initialized"}' >/dev/null
# tools/list must advertise exactly the two allowed tools AND each must declare
# run_nonce required (the schema the real client is driven by).
# Control A — preventive filtering: the forbidden tool is ABSENT from discovery,
# so a conforming client never sees it. Assert both the exact allowed set and
# that release_publish specifically is not advertised, and that each advertised
# tool marks run_nonce required (the schema a real client is driven by).
LIST="$(mcp '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}')"
echo "$LIST" | jq -e '[.result.tools[].name] | sort == ["release_prepare","release_status"]' >/dev/null \
  || { echo 'tools/list must advertise exactly the two allowed tools' >&2; exit 1; }
echo "$LIST" | jq -e '[.result.tools[].name] | index("release_publish") | not' >/dev/null \
  || { echo 'preventive filtering failed: release_publish must be ABSENT from tools/list discovery' >&2; exit 1; }
echo "$LIST" | jq -e 'all(.result.tools[]; (.inputSchema.required // []) | index("run_nonce"))' >/dev/null \
  || { echo 'each advertised tool must mark run_nonce required (schema-driven client would else omit it)' >&2; exit 1; }
echo "control A (preventive filtering): release_publish absent from discovery; allowed tools require run_nonce"
for tool in release_status release_prepare; do
  mcp "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"$tool\",\"arguments\":{\"version\":\"live\",\"run_nonce\":\"$NONCE\"}}}" \
    | jq -e '.result.isError == false' >/dev/null \
    || { echo "allowed tool $tool failed through the live proxy" >&2; exit 1; }
done
# Control B — runtime enforcement: an ADVERSARIAL probe (this curl, standing in
# for a non-conforming client) submits the undiscovered release_publish anyway.
# Talon must still block it. This is defence-in-depth, NOT "Copilot published".
mcp "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"release_publish\",\"arguments\":{\"version\":\"live\",\"run_nonce\":\"$NONCE\"}}}" \
  | jq -e '.error.data.talon_code == "TALON_TOOL_FORBIDDEN"' >/dev/null \
  || { echo 'release_publish denial must carry talon_code TALON_TOOL_FORBIDDEN (#369)' >&2; exit 1; }
echo "control B (runtime enforcement): adversarial release_publish probe denied with TALON_TOOL_FORBIDDEN"

RELEASE_RUN_NONCE="$NONCE" RELEASE_MCP_RECEIPTS="$RECEIPTS" \
  "$ROOT/scripts/assert-release-blocked.sh" >/dev/null
if RELEASE_RUN_NONCE="stale-run" RELEASE_MCP_RECEIPTS="$RECEIPTS" \
  "$ROOT/scripts/assert-release-blocked.sh" >/dev/null 2>&1; then
  echo 'assert-release-blocked accepted receipts from a different run' >&2
  exit 1
fi
echo "receipts: nonce-correlated proof passes; stale nonce rejected"

# The identity story: EVERY record in the session — the LLM call and the MCP
# calls — must carry agent_id=coding-assistant (assert-evidence enforces that
# all records share the agent), and the forbidden-tool denial must be present.
"$ROOT/scripts/assert-evidence.sh" --session "$SESSION_MCP" --agent coding-assistant \
  --min-denials 1 --deny-reason forbidden_tools --since "$RUN_TS"
echo "identity: LLM and MCP records share agent_id=coding-assistant"

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
  mode: "enforce"
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
