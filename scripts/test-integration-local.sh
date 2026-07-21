#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
PIDS=()

cleanup() {
  local pid
  for pid in "${PIDS[@]:-}"; do
    kill -TERM "$pid" 2>/dev/null || true
  done
  for pid in "${PIDS[@]:-}"; do
    wait "$pid" 2>/dev/null || true
  done
  rm -rf "$TMP"
}
trap cleanup EXIT INT TERM

free_port() {
  python3 - <<'PYPORT'
import socket
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    print(sock.getsockname()[1])
PYPORT
}
wait_for() {
  local name="$1" url="$2" log="$3"
  for _ in $(seq 1 100); do
    if curl --fail --silent --max-time 1 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.05
  done
  echo "$name did not become ready at $url" >&2
  cat "$log" >&2 || true
  return 1
}

MOCK_PORT="$(free_port)"
SHIM_PORT="$(free_port)"
ADAPTER_PORT="$(free_port)"
MCP_PORT="$(free_port)"

MOCK_TALON_PORT="$MOCK_PORT" MOCK_TALON_LOG="$TMP/requests.jsonl" \
  python3 "$ROOT/mock/mock_talon.py" >"$TMP/mock.log" 2>&1 &
PIDS+=("$!")
TALON_GATEWAY="http://127.0.0.1:$MOCK_PORT" TALON_COPILOT_SESSION_ID=copilot-billing-demo \
  COPILOT_SHIM_BIND="127.0.0.1:$SHIM_PORT" \
  "$ROOT/bin/copilot-session-shim" >"$TMP/shim.log" 2>&1 &
PIDS+=("$!")
ZENDESK_ADAPTER_TOKEN=adapter-secret TALON_GATEWAY="http://127.0.0.1:$MOCK_PORT" \
  TALON_CUSTOMER_SUPPORT_KEY=customer-key TALON_CUSTOMER_SUPPORT_PROVIDER=local-llama \
  TALON_CUSTOMER_SUPPORT_MODEL=llama3.2:1b ZENDESK_ADAPTER_BIND="127.0.0.1:$ADAPTER_PORT" \
  "$ROOT/bin/zendesk-adapter" >"$TMP/adapter.log" 2>&1 &
PIDS+=("$!")
RELEASE_MCP_BIND="127.0.0.1:$MCP_PORT" RELEASE_MCP_RECEIPTS="$TMP/receipts.jsonl" \
  "$ROOT/bin/release-mcp-server" >"$TMP/mcp.log" 2>&1 &
PIDS+=("$!")

wait_for mock "http://127.0.0.1:$MOCK_PORT/health" "$TMP/mock.log"
wait_for zendesk-adapter "http://127.0.0.1:$ADAPTER_PORT/health" "$TMP/adapter.log"
wait_for release-mcp "http://127.0.0.1:$MCP_PORT/health" "$TMP/mcp.log"

REQ='{"model":"gpt-4o","messages":[{"role":"user","content":"hello"}],"stream":true}'
curl --fail --silent --show-error --max-time 10 \
  "http://127.0.0.1:$SHIM_PORT/v1/proxy/openai/v1/chat/completions?demo=1" \
  -H 'Authorization: Bearer coding-key' -H 'Content-Type: application/json' -d "$REQ" \
  | jq -e '.choices[0].message.content|length>0' >/dev/null

curl --fail --silent --show-error --max-time 10 \
  "http://127.0.0.1:$ADAPTER_PORT/v1/zendesk/draft" \
  -H 'Authorization: Bearer adapter-secret' -H 'Content-Type: application/json' \
  -d '{"ticket_id":"1042","subject":"Refund not received","requester":{"name":"Demo Customer","email":"demo.customer@example.com"},"message":"Synthetic request. IBAN: DE89370400440532013000"}' \
  | jq -e '.session_id=="zendesk-ticket-1042" and (.draft|length>0) and (keys|sort)==["draft","session_id"]' >/dev/null

python3 - "$TMP/requests.jsonl" "$REQ" <<'PYREQ'
import json
from pathlib import Path
import sys

rows = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
assert len(rows) == 2, rows
assert rows[0]['path'] == '/v1/proxy/openai/v1/chat/completions?demo=1'
assert rows[0]['headers']['authorization'] == 'Bearer coding-key'
assert rows[0]['headers']['x-talon-session-id'] == 'copilot-billing-demo'
assert rows[0]['headers']['x-talon-client'] == 'github-copilot-cli-full-demo'
assert rows[0]['body_raw'] == sys.argv[2]
assert rows[1]['path'] == '/v1/proxy/local-llama/v1/chat/completions'
assert rows[1]['headers']['authorization'] == 'Bearer customer-key'
assert rows[1]['headers']['x-talon-session-id'] == 'zendesk-ticket-1042'
assert rows[1]['body']['model'] == 'llama3.2:1b'
PYREQ

curl --fail --silent --show-error --max-time 10 "http://127.0.0.1:$MCP_PORT/mcp" \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}' \
  | jq -e '.result.serverInfo.name=="talon-demo-release"' >/dev/null
curl --fail --silent --show-error --max-time 10 "http://127.0.0.1:$MCP_PORT/mcp" \
  -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | jq -e '.result.tools|length==3' >/dev/null
RUN_NONCE="$(python3 -c 'import secrets;print(secrets.token_hex(16))')"
for tool in release_status release_prepare; do
  curl --fail --silent --show-error --max-time 10 "http://127.0.0.1:$MCP_PORT/mcp" \
    -H 'Content-Type: application/json' \
    -d "{\"jsonrpc\":\"2.0\",\"id\":3,\"method\":\"tools/call\",\"params\":{\"name\":\"$tool\",\"arguments\":{\"version\":\"demo\",\"run_nonce\":\"$RUN_NONCE\"}}}" \
    | jq -e '.result.isError==false' >/dev/null
done
# Nonce-correlated denial proof (finding H1): passes for the current run...
RELEASE_RUN_NONCE="$RUN_NONCE" RELEASE_MCP_RECEIPTS="$TMP/receipts.jsonl" \
  "$ROOT/scripts/assert-release-blocked.sh" >/dev/null
# ...fails for a different nonce even though the same receipts file exists
# (a stale file from an earlier run can no longer fake success)...
if RELEASE_RUN_NONCE="stale-run" RELEASE_MCP_RECEIPTS="$TMP/receipts.jsonl" \
  "$ROOT/scripts/assert-release-blocked.sh" >/dev/null 2>&1; then
  echo 'assert-release-blocked accepted receipts from a different run' >&2
  exit 1
fi
# ...and fails when release_publish reached the upstream.
curl --fail --silent --show-error --max-time 10 "http://127.0.0.1:$MCP_PORT/mcp" \
  -H 'Content-Type: application/json' \
  -d "{\"jsonrpc\":\"2.0\",\"id\":4,\"method\":\"tools/call\",\"params\":{\"name\":\"release_publish\",\"arguments\":{\"version\":\"demo\",\"run_nonce\":\"$RUN_NONCE\"}}}" \
  >/dev/null
if RELEASE_RUN_NONCE="$RUN_NONCE" RELEASE_MCP_RECEIPTS="$TMP/receipts.jsonl" \
  "$ROOT/scripts/assert-release-blocked.sh" >/dev/null 2>&1; then
  echo 'assert-release-blocked missed a release_publish receipt' >&2
  exit 1
fi

# Session-budget scenario (finding H2): request 1 allowed, request 2 allowed,
# request 3 denied with 403 session_budget_exceeded and zero simulated cost.
BUDGET_PORT="$(free_port)"
MOCK_TALON_PORT="$BUDGET_PORT" MOCK_TALON_LOG="$TMP/budget.jsonl" \
  MOCK_TALON_SESSION_BUDGET_REQUESTS=2 \
  python3 "$ROOT/mock/mock_talon.py" >"$TMP/budget-mock.log" 2>&1 &
PIDS+=("$!")
wait_for budget-mock "http://127.0.0.1:$BUDGET_PORT/health" "$TMP/budget-mock.log"
budget_call() {
  curl --silent --output /dev/null --write-out '%{http_code}' --max-time 10 \
    "http://127.0.0.1:$BUDGET_PORT/v1/proxy/openai/v1/chat/completions" \
    -H 'Authorization: Bearer doc-key' -H 'Content-Type: application/json' \
    -H 'X-Talon-Session-ID: n8n-quarterly-report' \
    -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"summarize"}]}'
}
[[ "$(budget_call)" == "200" ]] || { echo 'budget request 1 not allowed' >&2; exit 1; }
[[ "$(budget_call)" == "200" ]] || { echo 'budget request 2 not allowed' >&2; exit 1; }
[[ "$(budget_call)" == "403" ]] || { echo 'budget request 3 not denied' >&2; exit 1; }
python3 - "$TMP/budget.jsonl" <<'PYBUDGET'
import json, sys
from pathlib import Path

rows = [json.loads(line) for line in Path(sys.argv[1]).read_text().splitlines()]
assert len(rows) == 3, rows
assert [r['denied'] for r in rows] == [False, False, True]
assert rows[2]['cost_usd'] == 0.0, 'denied request must incur zero simulated cost'
PYBUDGET

echo 'Local HTTP integration passed'
