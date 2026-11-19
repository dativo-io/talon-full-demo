#!/usr/bin/env bash
# Real n8n + published Talon + synthetic order and upstream; no external credentials.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
fixture_pid= talon_pid=
cleanup() {
  [[ -z "$talon_pid" ]] || kill "$talon_pid" 2>/dev/null || true
  [[ -z "$fixture_pid" ]] || kill "$fixture_pid" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT
umask 077
BIN="$WORK/bin"
mkdir -p "$BIN" "$WORK/talon" "$WORK/output"
version=v1.16.1
archive=talon_1.16.1_linux_amd64.tar.gz
curl -fsSL --retry 3 "https://github.com/dativo-io/talon/releases/download/$version/$archive" -o "$WORK/$archive"
printf '%s  %s\n' bc5147dedfb59608b0be1ec07b6da78ef430bc833ccc7fddfa444760f2e94a4e "$WORK/$archive" | sha256sum -c -
tar -xzf "$WORK/$archive" -C "$BIN" talon
reported="$("$BIN/talon" version)"
printf '%s\n' "$reported"
[[ "$(printf '%s\n' "$reported" | head -n1)" == "Talon 1.16.1" ]] || { echo 'Unexpected released binary version'; exit 1; }
sha256sum "$BIN/talon"
export TALON_SECRETS_KEY="$(openssl rand -hex 32)"
export TALON_SIGNING_KEY="$(openssl rand -hex 32)"
export TALON_ADMIN_KEY="$(openssl rand -hex 32)"
export TALON_DATA_DIR="$WORK/talon/data"
mkdir -p "$TALON_DATA_DIR"
SHOPIFY_PORT=19091
TALON_PORT=19092
python3 "$ROOT/fixture.py" --port "$SHOPIFY_PORT" --log "$WORK/fixture.jsonl" >"$WORK/fixture.log" 2>&1 &
fixture_pid=$!
for _ in $(seq 1 50); do curl -fsS "http://127.0.0.1:$SHOPIFY_PORT/health" >/dev/null 2>&1 && break; sleep .2; done
curl -fsS "http://127.0.0.1:$SHOPIFY_PORT/health" >/dev/null
cd "$WORK/talon"
cat >agent.talon.yaml <<'YAML'
agent:
  name: customer-support
  description: Shopify read-only support fixture
  version: "1.0.0"
  tenant_id: acme
  key:
    secret_name: customer-support-talon-key
capabilities:
  forbidden_tools: ["issue_refund"]
policies:
  cost_limits:
    daily: 10
    monthly: 100
  data_classification:
    input_scan: true
audit:
  log_level: detailed
  retention_days: 7
  include_prompts: false
  include_responses: false
YAML
cat >talon.config.yaml <<YAML
gateway:
  enabled: true
  providers:
    openai:
      enabled: true
      secret_name: openai-api-key
      base_url: "http://127.0.0.1:$SHOPIFY_PORT"
      allowed_models: ["gpt-4o-mini"]
  organization_policy:
    defaults:
      pii_action: redact
      daily_cost: 10.00
    log_prompts: false
    log_responses: false
YAML
"$BIN/talon" secrets set customer-support-talon-key synthetic-talon-agent-key >/dev/null
"$BIN/talon" secrets set openai-api-key synthetic-provider-key >/dev/null
"$BIN/talon" validate
"$BIN/talon" serve --port "$TALON_PORT" --gateway --gateway-config talon.config.yaml >"$WORK/talon.log" 2>&1 &
talon_pid=$!
for _ in $(seq 1 100); do curl -fsS "http://127.0.0.1:$TALON_PORT/health" >/dev/null 2>&1 && break; sleep .2; done
curl -fsS "http://127.0.0.1:$TALON_PORT/health" >/dev/null || { cat "$WORK/talon.log"; exit 1; }

IMAGE=docker.n8n.io/n8nio/n8n:2.30.4
docker pull "$IMAGE"
echo "n8n image digest:"
docker image inspect "$IMAGE" --format '{{join .RepoDigests ","}}'
export N8N_ENCRYPTION_KEY="$(openssl rand -hex 32)"
prepare() {
  local dir="$1" export_file="$2" scenario="$3"
  mkdir -p "$dir/runtime" "$dir/config"
  python3 - "$export_file" "$dir/config/workflow.json" "$scenario" <<'PY'
import json,sys
from pathlib import Path
src,dest,scenario=sys.argv[1:]
w=json.loads(Path(src).read_text())
if isinstance(w,list): w=w[0]
n=next(n for n in w["nodes"] if n["name"]=="Operator settings and sample")
s=n["parameters"]["jsCode"]
s=s.replace("http://127.0.0.1:8080","http://127.0.0.1:19092")
if scenario=="refund": s=s.replace("Order #1001 status","Order #1001 refund").replace("When will my order #1001 arrive?","Please review order #1001 refund EUR 249 for damaged product.")
if scenario=="wrong_sender": s=s.replace("buyer@example.test","other@example.test")
n["parameters"]["jsCode"]=s
w["active"]=False
Path(dest).write_text(json.dumps(w))
PY
  cat >"$dir/config/credentials.json" <<'JSON'
[
 {"id":"ShopifyReadOnlyHeader","name":"Shopify read-only (X-Shopify-Access-Token)","type":"httpHeaderAuth","data":{"name":"X-Shopify-Access-Token","value":"synthetic-read-only"}},
 {"id":"TalonSupportHeader","name":"Talon customer-support (Authorization)","type":"httpHeaderAuth","data":{"name":"Authorization","value":"Bearer synthetic-talon-agent-key"}}
]
JSON
}
run_n8n() {
  local dir="$1"; shift
  docker run --rm --network host --user "$(id -u):$(id -g)" \
    -e HOME=/home/node -e N8N_USER_FOLDER=/home/node/.n8n \
    -e N8N_ENCRYPTION_KEY -e N8N_DIAGNOSTICS_ENABLED=false \
    -e N8N_VERSION_NOTIFICATIONS_ENABLED=false -e N8N_TEMPLATES_ENABLED=false \
    -e N8N_RUNNERS_ENABLED=true -e N8N_RUNNERS_MODE=internal \
    -v "$dir/runtime:/home/node/.n8n" -v "$dir/config:/demo/config" \
    "$IMAGE" "$@"
}
run_case() {
  local dir="$1" input="$2" scenario="$3" expected="$4"
  prepare "$dir" "$input" "$scenario"
  run_n8n "$dir" import:credentials --input=/demo/config/credentials.json >/dev/null
  run_n8n "$dir" import:workflow --input=/demo/config/workflow.json >/dev/null
  run_n8n "$dir" export:workflow --all --output=/demo/config/export.json >/dev/null
  local id
  id="$(python3 -c 'import json,sys; w=json.load(open(sys.argv[1])); print((w[0] if isinstance(w,list) else w)["id"])' "$dir/config/export.json")"
  ! grep -Eq 'synthetic-read-only|synthetic-talon-agent-key|synthetic-provider-key' "$dir/config/export.json"
  run_n8n "$dir" execute --id="$id" --rawOutput >"$dir/result.log" 2>&1 || { cat "$dir/result.log"; exit 1; }
  # n8n can emit startup log lines before the JSON. Locate actual execution data
  # and assert the terminal node result (never grep the embedded workflow source).
  python3 - "$dir/result.log" "$scenario" "$expected" "$dir/final.json" <<'PY'
import json,sys
from pathlib import Path
log,scenario,expected,dest=sys.argv[1:]
raw=Path(log).read_text()
decoder=json.JSONDecoder()
data=None
for i,line in enumerate(raw.splitlines(keepends=True)):
    if line.strip().startswith("{"):
        try:
            candidate,_=decoder.raw_decode("".join(raw.splitlines(keepends=True)[i:]).lstrip())
        except ValueError:
            continue
        if isinstance(candidate,dict) and isinstance(candidate.get("data"),dict) and "resultData" in candidate["data"]:
            data=candidate
            break
assert data is not None, "no structured n8n execution result"
res=data["data"]["resultData"]
assert not res.get("error"),res.get("error")
node="Manual review only" if scenario=="wrong_sender" else "Review-only support result"
assert res["lastNodeExecuted"]==node,res.get("lastNodeExecuted")
items=res["runData"][node][-1]["data"]["main"][0]
assert len(items)==1,items
out=items[0]["json"]
assert out["refund_execution"]=="unavailable" and out["message_sent"] is False,out
if scenario=="wrong_sender":
    assert out["status"]=="manual_review" and out["reason"]==expected,out
    assert "Draft through Talon" not in res["runData"]
else:
    assert out["status"]==expected and out["draft"].startswith("Fixture only:"),out
    assert out["proposed_refund_eur"]==("249.00" if scenario=="refund" else None),out
    assert out["merchant_eligibility"]=="not_established"
Path(dest).write_text(json.dumps(out))
PY
  echo "PASS n8n $scenario: $expected"
}
run_case "$WORK/one" "$ROOT/shopify-support.workflow.json" status draft_ready_for_operator_review
run_case "$WORK/two" "$WORK/one/config/export.json" refund draft_ready_for_operator_review
run_case "$WORK/three" "$ROOT/shopify-support.workflow.json" wrong_sender order_or_requester_not_verified
python3 - "$WORK/fixture.jsonl" <<'PY'
import json,sys
from collections import Counter
from pathlib import Path
records=[json.loads(l) for l in Path(sys.argv[1]).read_text().splitlines()]
assert Counter(r["kind"] for r in records)=={"shopify_read":3,"provider_call":2}, records
assert [r["facts"]["proposed_refund_eur"] for r in records if r["kind"]=="provider_call"]==[None,"249.00"], records
print("PASS: 3 read-only Shopify requests, 2 minimized upstream calls, unauthorized stop, no financial request")
PY
"$BIN/talon" audit export --format signed-json --output "$WORK/output/evidence.json"
"$BIN/talon" audit verify --file "$WORK/output/evidence.json"
python3 - "$WORK/output/evidence.json" "$WORK/one/final.json" "$WORK/two/final.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
records=d["records"]
s=[r for r in records if str(r.get("session_id","")).startswith("shopify-support-")]
expected={json.load(open(p))["session_id"] for p in sys.argv[2:]}
assert len(expected)==2,expected
assert expected.issubset({r["session_id"] for r in s}), records
print("PASS: signed evidence for actual Shopify-support Talon requests:",len(s))
PY
echo 'PASS Stage A real n8n + checksum-pinned Talon + synthetic Shopify and provider (NOT live Shopify or model)'
