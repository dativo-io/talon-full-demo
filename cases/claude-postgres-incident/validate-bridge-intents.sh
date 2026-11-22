#!/usr/bin/env bash
# The MCP bridge's durable per-intent operation ids against a REAL Talon
# Action Gateway (no Docker): every tool call runs a fresh bridge process
# (stdio MCP), so each step also proves the intent ledger survives a restart.
#
#   - a repeat while awaiting approval resumes the SAME operation; the
#     oncall reviewer's approval dispatches nothing; the next repeat
#     dispatches it once;
#   - a second identical intent after the first was reported is a NEW
#     operation with its own approval and one dispatch;
#   - an unknown outcome (the downstream answers HTTP 500 after dispatch) is
#     never retried and never replaced by a new operation;
#   - the company DENY probe (volume_delete) reaches nothing;
#   - every operation's signed lifecycle verifies.
#
# Counts come from an independent downstream (a tiny HTTP server standing in
# for the OrderDesk executor), never from Talon.
#
# NOT PROOF of the OpenShell hop: the bridge sends no agent key, so a local
# header proxy adds the use case's key in front of Talon — it stands in for
# the verified OpenShell workload hop and proves nothing about it. C06–C12
# remain the live OpenShell/Claude lane's.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"
for bin in curl jq openssl node python3; do command -v "$bin" >/dev/null || { echo "MISSING $bin" >&2; exit 2; }; done
TALON="${TALON_CLI:-$(command -v talon || true)}"
[[ -n "$TALON" ]] || { echo "BLOCKED: a Talon binary is required (TALON_CLI)" >&2; exit 2; }
TALON="$(realpath "$TALON")"
WORK="$(mktemp -d)"
PIDS=()
cleanup() {
  local p
  for p in "${PIDS[@]:-}"; do
    if [[ -n "$p" ]]; then kill "$p" 2>/dev/null || true; fi
  done
  rm -rf "$WORK"
}
trap cleanup EXIT
fail() { echo "FAIL: $*" >&2; tail -30 "$WORK/serve.log" >&2 2>/dev/null || true; exit 1; }
free_port() { python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])'; }
wait_http() { for _ in $(seq 1 80); do curl -fsS --max-time 1 "$1" >/dev/null 2>&1 && return 0; sleep 0.25; done; fail "$1 not ready"; }
DOWN_PORT="$(free_port)"; TALON_PORT="$(free_port)"; HOP_PORT="$(free_port)"

# Independent downstream: counts every executed action; /_mode switches the
# answer status (500 = the business system answered, but not success).
cat >"$WORK/downstream.mjs" <<'JS'
import { createServer } from 'node:http';
const calls = {}; let status = 200;
createServer(async (req, res) => {
  let raw = ''; for await (const c of req) raw += c;
  if (req.url === '/_calls') { res.end(JSON.stringify(calls)); return; }
  if (req.url === '/_mode') { status = JSON.parse(raw).status; res.end('{}'); return; }
  const m = /^\/actions\/([a-z_]+)$/.exec(req.url || '');
  if (!m) { res.writeHead(404); res.end('{}'); return; }
  calls[m[1]] = (calls[m[1]] || 0) + 1;
  res.writeHead(status, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ status: status === 200 ? 'done' : 'error', synthetic: true }));
}).listen(Number(process.env.PORT), '127.0.0.1');
JS
PORT="$DOWN_PORT" node "$WORK/downstream.mjs" & PIDS+=("$!")
wait_http "http://127.0.0.1:$DOWN_PORT/_calls"
count() { curl -fsS "http://127.0.0.1:$DOWN_PORT/_calls" | jq -r --arg a "$1" '.[$a] // 0'; }

export TALON_DATA_DIR="$WORK/state" TALON_SECRETS_KEY TALON_SIGNING_KEY TALON_ADMIN_KEY
TALON_SECRETS_KEY="$(openssl rand -hex 32)"; TALON_SIGNING_KEY="$(openssl rand -hex 32)"; TALON_ADMIN_KEY="$(openssl rand -hex 24)"
unset TALON_GATEWAY_CONFIG TALON_AGENTS_DIR TALON_APPROVER_KEY
AGENT_KEY="talon-bridge-intents-$(openssl rand -hex 10)"
sed -e "s|http://127.0.0.1:9080|http://127.0.0.1:$DOWN_PORT|g" -e 's/REPLACE_WITH_ACTUAL_SANDBOX_ID/bridge-intents-not-a-sandbox/' \
  "$ROOT/config/agent.talon.yaml.template" >"$WORK/agent.talon.yaml"
cat >"$WORK/talon.config.yaml" <<'YAML'
gateway:
  enabled: true
  listen_prefix: "/v1/proxy"
  providers:
    openai:
      enabled: true
      secret_name: incident-dummy-provider-key
      base_url: "https://api.openai.com"
  organization_policy:
    constraints:
      forbidden_tools: [volume_delete]
      action_approvals:
        rules:
          orderdesk_staging_repair:
            actions: [reconcile_staging_db_credentials]
            approver_groups: [oncall]
YAML
mkdir -p "$TALON_DATA_DIR"
(cd "$WORK" && "$TALON" secrets set claude-orderdesk-talon-key "$AGENT_KEY" >/dev/null && "$TALON" secrets set incident-dummy-provider-key fixture-only >/dev/null && "$TALON" validate >/dev/null) || fail "Talon rejected config"
REVIEW_TOKEN="$(cd "$WORK" && "$TALON" approver add --name incident-oncall --tenant acme --groups oncall | grep -oE 'talon_appr_cred_[0-9a-f]+\.[A-Za-z0-9_-]+' | head -n1)"
[[ -n "$REVIEW_TOKEN" ]] || fail "oncall credential missing"
(cd "$WORK" && exec "$TALON" serve --host 127.0.0.1 --port "$TALON_PORT" --gateway --gateway-config "$WORK/talon.config.yaml") >"$WORK/serve.log" 2>&1 & PIDS+=("$!")
wait_http "http://127.0.0.1:$TALON_PORT/health"

# Stand-in for the verified OpenShell hop (NOT hop proof): adds the key.
cat >"$WORK/hop.mjs" <<'JS'
import { createServer, request } from 'node:http';
createServer((req, res) => {
  const up = request({ host: '127.0.0.1', port: Number(process.env.TALON_PORT), path: req.url, method: req.method,
    headers: { ...req.headers, authorization: 'Bearer ' + process.env.AGENT_KEY } }, (r) => {
    res.writeHead(r.statusCode || 502, r.headers); r.pipe(res);
  });
  up.on('error', () => { res.writeHead(502); res.end('{}'); });
  req.pipe(up);
}).listen(Number(process.env.PORT), '127.0.0.1');
JS
PORT="$HOP_PORT" TALON_PORT="$TALON_PORT" AGENT_KEY="$AGENT_KEY" node "$WORK/hop.mjs" & PIDS+=("$!")
for _ in $(seq 1 40); do curl -sS --max-time 1 -o /dev/null "http://127.0.0.1:$HOP_PORT/health" 2>/dev/null && break; sleep 0.25; done

SESSION_SUFFIX="$(openssl rand -hex 4)"
export TALON_ACTION_BASE_URL="http://127.0.0.1:$HOP_PORT" TALON_SESSION_ID="bridge-intents-$SESSION_SUFFIX"
export ORDERDESK_INTENT_LEDGER="$WORK/ledger/intents.json"
RECONCILE='{"environment":"staging","service":"orderdesk-api","target_revision":"rev-002"}'
# One fresh bridge process per tool call (a restart between every step).
bridge_call() {
  printf '%s\n' "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"reconcile_staging_db_credentials\",\"arguments\":$RECONCILE}}" |
    node --experimental-strip-types "$REPO/cases/claude-postgres-incident/src/mcp-bridge.ts" |
    head -n1 | jq -c '.result.content[0].text | fromjson'
}
approve() {
  local apr
  apr="$(curl -fsS -H "Authorization: Bearer $AGENT_KEY" "http://127.0.0.1:$TALON_PORT/v1/action-operations/$1" | jq -er '.operation.approval.id')"
  curl -fsS -o /dev/null -X POST -H "Authorization: Bearer $REVIEW_TOKEN" -H 'Content-Type: application/json' \
    --data '{"decision":"approve","reason":"synthetic oncall approval"}' "http://127.0.0.1:$TALON_PORT/v1/approvals/$apr/decisions" ||
    fail "oncall approval of $1"
}
expect() { # phase, result
  [[ "$(jq -r .phase <<<"$2")" == "$1" ]] || fail "expected phase $1, got $2"
}
OPS=()

R="$(bridge_call)"; expect approval_pending "$R"; A="$(jq -r .operation_id <<<"$R")"
R="$(bridge_call)"; expect approval_pending "$R"
[[ "$(jq -r .operation_id <<<"$R")" == "$A" ]] || fail "a repeat while awaiting approval must resume $A"
approve "$A"
[[ "$(count reconcile_staging_db_credentials)" == 0 ]] || fail "approval or pending repeats dispatched"
R="$(bridge_call)"; expect dispatched "$R"
[[ "$(jq -r .operation_id <<<"$R")" == "$A" ]] || fail "the approved repeat must claim $A"
[[ "$(count reconcile_staging_db_credentials)" == 1 ]] || fail "expected 1 dispatch"
OPS+=("$A")
echo "PASS: pending repeat resumed $A across bridge restarts; approval sent nothing; one dispatch"

R="$(bridge_call)"; expect approval_pending "$R"; B="$(jq -r .operation_id <<<"$R")"
[[ "$B" != "$A" ]] || fail "a second identical intent must be a new operation"
approve "$B"
R="$(bridge_call)"; expect dispatched "$R"
[[ "$(count reconcile_staging_db_credentials)" == 2 ]] || fail "expected 2 dispatches"
OPS+=("$B")
echo "PASS: a second identical intent is a new operation ($B) with its own approval and one dispatch"

curl -fsS -o /dev/null -X POST --data '{"status":500}' "http://127.0.0.1:$DOWN_PORT/_mode"
R="$(bridge_call)"; expect approval_pending "$R"; C="$(jq -r .operation_id <<<"$R")"
approve "$C"
R="$(bridge_call)"; expect outcome_unknown "$R"
for _ in 1 2; do
  R="$(bridge_call)"; expect outcome_unknown "$R"
  [[ "$(jq -r .operation_id <<<"$R")" == "$C" ]] || fail "an unknown intent must never become a new operation"
done
[[ "$(count reconcile_staging_db_credentials)" == 3 ]] || fail "an unknown outcome was retried"
OPS+=("$C")
echo "PASS: unknown outcome ($C) never retried, never replaced; downstream calls 3"

(cd "$REPO/cases/claude-postgres-incident" && node --experimental-strip-types src/mcp-bridge.ts --probe-volume-delete >/dev/null) || fail "company DENY probe"
[[ "$(count volume_delete)" == 0 ]] || fail "volume_delete reached the downstream"
echo "PASS: company DENY probe; volume_delete downstream count 0"

for op in "${OPS[@]}"; do
  (cd "$WORK" && "$TALON" audit verify --operation "$op" | grep -q 'Lifecycle: VALID') || fail "signed lifecycle of $op"
done
echo "PASS: ${#OPS[@]} operations verify (talon audit verify --operation)"
echo "NOT PROVEN: OpenShell verified workload hop (a local header proxy stood in), containment, Claude runtime, consumer C06–C12"
