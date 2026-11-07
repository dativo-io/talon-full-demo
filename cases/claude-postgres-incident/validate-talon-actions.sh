#!/usr/bin/env bash
# Real published Talon Action Gateway preflight, using an authenticated HOST
# agent key. This is NOT a verified OpenShell sandbox hop and not C06–C09 proof.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
for bin in docker curl jq openssl; do command -v "$bin" >/dev/null || { echo "MISSING $bin" >&2; exit 2; }; done
docker info >/dev/null || { echo "BLOCKED Docker" >&2; exit 2; }
TALON="${TALON_CLI:-$(command -v talon || true)}"
[[ -n "$TALON" ]] || { echo "BLOCKED: published Talon binary is required" >&2; exit 2; }
TALON="$(realpath "$TALON")"
WORK="$(mktemp -d)"
COMPOSE=(docker compose -f compose.yaml)
TALON_PID=""
cleanup() {
  [[ -z "$TALON_PID" ]] || { kill "$TALON_PID" 2>/dev/null || true; wait "$TALON_PID" 2>/dev/null || true; }
  "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT
"${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
"${COMPOSE[@]}" up --build -d --wait >/dev/null
for _ in $(seq 1 40); do
  curl -fsS --max-time 2 http://127.0.0.1:9080/_test/state -o "$WORK/before.json" 2>/dev/null && break
  sleep 1
done
[[ -s "$WORK/before.json" ]] || { echo "FAIL: fixture not ready" >&2; exit 1; }
jq -e '.staging.body.sqlstate=="28P01" and .production.rowCount==1000 and .infrastructure.volumeDeleteCalls==0' "$WORK/before.json" >/dev/null

export TALON_DATA_DIR="$WORK/state"
export TALON_SECRETS_KEY="$(openssl rand -hex 32)"
export TALON_SIGNING_KEY="$(openssl rand -hex 32)"
export TALON_ADMIN_KEY="$(openssl rand -hex 24)"
AGENT_KEY="talon-host-preflight-$(openssl rand -hex 10)"
cp config/agent.talon.yaml.template "$WORK/agent.talon.yaml"
sed -i 's/REPLACE_WITH_ACTUAL_SANDBOX_ID/host-preflight-not-a-sandbox/' "$WORK/agent.talon.yaml"
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
(cd "$WORK" && "$TALON" secrets set claude-orderdesk-talon-key "$AGENT_KEY" >/dev/null && "$TALON" secrets set incident-dummy-provider-key fixture-only >/dev/null && "$TALON" validate >/dev/null) ||
  { echo "FAIL: Talon rejected config" >&2; exit 1; }
REVIEW_OUT="$(cd "$WORK" && "$TALON" approver add --name incident-oncall --tenant acme --groups oncall)"
REVIEW_TOKEN="$(grep -oE 'talon_appr_cred_[0-9a-f]+\.[A-Za-z0-9_-]+' <<<"$REVIEW_OUT" | head -n 1)"
[[ -n "$REVIEW_TOKEN" ]] || { echo "FAIL: oncall credential missing" >&2; exit 1; }
(cd "$WORK" && exec "$TALON" serve --host 127.0.0.1 --port 18080 --gateway --gateway-config "$WORK/talon.config.yaml") >"$WORK/serve.log" 2>&1 &
TALON_PID=$!
for _ in $(seq 1 40); do
  curl -fsS --max-time 2 http://127.0.0.1:18080/health -o /dev/null 2>/dev/null && break
  sleep 1
done
curl -fsS --max-time 2 http://127.0.0.1:18080/health -o /dev/null ||
  { echo "FAIL: Talon start"; tail -50 "$WORK/serve.log"; exit 1; }

request() {
  local url="$1" body="$2" actor="${3:-agent}"
  local token="$AGENT_KEY"
  [[ "$actor" != reviewer ]] || token="$REVIEW_TOKEN"
  CODE="$(curl -sS --max-time 10 -o "$WORK/result.json" -w '%{http_code}' -X POST
    -H "Authorization: Bearer $token" -H 'Content-Type: application/json'
    --data "$body" "http://127.0.0.1:18080$url")"
}
fail() { echo "FAIL: $*" >&2; cat "$WORK/result.json" >&2; exit 1; }
request /v1/action-operations '{"operation_id":"host-deny-1","action":"volume_delete","arguments":{"volume_id":"vol_production"}}'
[[ "$CODE" == 403 ]] || fail "company DENY http $CODE"
jq -e '.operation.verdict=="DENY" and .operation.matched_rule_source=="company"' "$WORK/result.json" >/dev/null || fail "not a company-sourced DENY"
curl -fsS http://127.0.0.1:9080/_test/state -o "$WORK/snapshot.json"
jq -e '.infrastructure.volumeDeleteCalls == 0' "$WORK/snapshot.json" >/dev/null || fail "delete reached fake API"
echo "PASS: host-key company DENY; independent fake infra delete count zero"

request /v1/action-operations '{"operation_id":"host-repair-1","action":"reconcile_staging_db_credentials","arguments":{"environment":"staging","service":"orderdesk-api","target_revision":"rev-002"}}'
[[ "$CODE" == 202 ]] || fail "expected approval pending, got $CODE"
APPROVAL_ID="$(jq -er '.operation.approval.id' "$WORK/result.json")"
request /v1/action-operations/host-repair-1/attempts '{}'
[[ "$CODE" == 409 ]] || fail "pre-approval claim allowed"
request "/v1/approvals/$APPROVAL_ID/decisions" '{"decision":"approve","reason":"synthetic recovery"}' reviewer
[[ "$CODE" == 200 ]] || fail "oncall approval failed"
curl -fsS http://127.0.0.1:9080/_test/state -o "$WORK/snapshot.json"
jq -e '.staging.body.sqlstate=="28P01" and ((.dispatchCounts.reconcile_staging_db_credentials // 0)==0)' "$WORK/snapshot.json" >/dev/null || fail "approval caused dispatch"
request /v1/action-operations/host-repair-1/attempts '{}'
[[ "$CODE" == 200 ]] || fail "approved dispatch failed $CODE"
jq -e '.attempt.status=="succeeded"' "$WORK/result.json" >/dev/null || fail "dispatch did not succeed"
request /v1/action-operations/host-repair-1/attempts '{}'
[[ "$CODE" == 409 ]] || fail "replayed operation dispatched"
request /v1/action-operations '{"operation_id":"host-repair-1","action":"inspect_volume","arguments":{"volume_id":"vol_staging"}}'
[[ "$CODE" == 409 ]] || fail "same operation changed arguments accepted"
curl -fsS http://127.0.0.1:9080/_test/state -o "$WORK/snapshot.json"
jq -e '.staging.httpStatus==200 and .production.rowCount==1000 and .production.amountSum=="55555500" and .dispatchCounts.reconcile_staging_db_credentials==1 and .infrastructure.volumeDeleteCalls==0' "$WORK/snapshot.json" >/dev/null || fail "recovery, production or effect counts wrong"
(cd "$WORK" && "$TALON" audit verify --operation host-repair-1 >/dev/null && "$TALON" audit verify --operation host-deny-1 >/dev/null) ||
  fail "signed Talon operation verification"
echo "PASS: real Talon host-key approval, zero preapproval effects, one dispatch, no replay, signed lifecycle"
echo "NOT PROVEN: OpenShell verified workload hop, containment, Claude runtime, consumer C06–C12"
