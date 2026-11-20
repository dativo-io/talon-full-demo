#!/usr/bin/env bash
# Real n8n + published Talon + synthetic order and upstream; no external credentials.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
fixture_pid= talon_pid= action_n8n_container=
cleanup() {
  [[ -z "$action_n8n_container" ]] || docker rm -f "$action_n8n_container" >/dev/null 2>&1 || true
  [[ -z "$talon_pid" ]] || kill "$talon_pid" 2>/dev/null || true
  [[ -z "$fixture_pid" ]] || kill "$fixture_pid" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT
umask 077
BIN="$WORK/bin"
mkdir -p "$BIN" "$WORK/talon" "$WORK/output"
# Default is a published checksum-verified archive. For an explicitly
# development-only compatibility test, supply a pinned core-main binary.
if [[ -n "${TALON_EXTERNAL_BIN:-}" ]]; then
  [[ -x "$TALON_EXTERNAL_BIN" ]] || { echo 'Missing pinned core-main binary' >&2; exit 1; }
  cp "$TALON_EXTERNAL_BIN" "$BIN/talon"
  case "${TALON_EXTERNAL_KIND:-source-main}" in
    source-main)
      echo "DEVELOPMENT-ONLY source-built Talon: ${TALON_CORE_SHA:?set immutable Talon core SHA}"
      "$BIN/talon" version
      echo "This is NOT evidence of a published Talon artifact." ;;
    published-rc2)
      [[ "${TALON_RELEASE_TAG:-}" == "v1.17.0-rc.2" ]] || { echo 'Unexpected RC2 identity' >&2; exit 1; }
      echo "OFFICIAL PRE-RELEASE ARTIFACT: $TALON_RELEASE_TAG (checksum verified by caller)"
      reported="$("$BIN/talon" version)"
      printf '%s\n' "$reported"
      printf '%s\n' "$reported" | head -n1 | grep -Eq '^Talon v?1\.17\.0-rc\.2$' ||
        { echo 'Downloaded binary does not identify as v1.17.0-rc.2' >&2; exit 1; } ;;
    *) echo 'Unsupported TALON_EXTERNAL_KIND' >&2; exit 1 ;;
  esac
else
  version=v1.16.1
  archive=talon_1.16.1_linux_amd64.tar.gz
  curl -fsSL --retry 3 "https://github.com/dativo-io/talon/releases/download/$version/$archive" -o "$WORK/$archive"
  printf '%s  %s\n' bc5147dedfb59608b0be1ec07b6da78ef430bc833ccc7fddfa444760f2e94a4e "$WORK/$archive" | sha256sum -c -
  tar -xzf "$WORK/$archive" -C "$BIN" talon
  reported="$("$BIN/talon" version)"
  printf '%s\n' "$reported"
  [[ "$(printf '%s\n' "$reported" | head -n1)" == "Talon 1.16.1" ]] || { echo 'Unexpected released binary version'; exit 1; }
fi
sha256sum "$BIN/talon"

export TALON_SECRETS_KEY="$(openssl rand -hex 32)"
export TALON_SIGNING_KEY="$(openssl rand -hex 32)"
export TALON_ADMIN_KEY="$(openssl rand -hex 32)"
export TALON_DATA_DIR="$WORK/talon/data"
mkdir -p "$TALON_DATA_DIR"
SHOPIFY_PORT=19091
TALON_PORT=19092
if [[ -n "${TALON_EXTERNAL_BIN:-}" ]]; then
  python3 "$ROOT/fixture.py" --port "$SHOPIFY_PORT" --log "$WORK/fixture.jsonl" --action-fixture >"$WORK/fixture.log" 2>&1 &
else
  python3 "$ROOT/fixture.py" --port "$SHOPIFY_PORT" --log "$WORK/fixture.jsonl" >"$WORK/fixture.log" 2>&1 &
fi
fixture_pid=$!
for _ in $(seq 1 50); do curl -fsS "http://127.0.0.1:$SHOPIFY_PORT/health" >/dev/null 2>&1 && break; sleep .2; done
curl -fsS "http://127.0.0.1:$SHOPIFY_PORT/health" >/dev/null
cd "$WORK/talon"
if [[ -z "${TALON_EXTERNAL_BIN:-}" ]]; then
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
fi
if [[ -n "${TALON_EXTERNAL_BIN:-}" ]]; then
  company_agents='agents_dir: ./agents'
  company_constraints='    constraints:
      forbidden_tools: ["delete_*"]
      action_approvals:
        argument_rules:
          refund-too-large:
            actions: [create_refund_request]
            argument: amount
            type: decimal
            operator: gt
            value: "500.00"
            effect: deny'
  pii_action=block
else
  company_agents=''
  company_constraints=''
  pii_action=redact
fi
cat >talon.config.yaml <<YAML
${company_agents}
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
      pii_action: ${pii_action}
      daily_cost: 10.00
    log_prompts: false
    log_responses: false
${company_constraints}
YAML
if [[ -n "${TALON_EXTERNAL_BIN:-}" ]]; then
  # Native registration has one independently authenticated operational key.
  registration="$("$BIN/talon" agents add customer-support --tenant acme --owner support-operations --description "Shopify support draft through Talon" 2>&1)"
  DEMO_TALON_KEY="$(printf '%s\n' "$registration" | grep -oE 'talon_uc_[0-9a-f]{48}' | head -n1)"
  [[ -n "$DEMO_TALON_KEY" ]] || { echo 'Native registration failed' >&2; printf '%s\n' "$registration" | sed -E 's/talon_uc_[0-9a-f]{48}/[REDACTED]/g' >&2; exit 1; }
  echo 'PASS: native registered customer-support with an issued Talon use-case key'
  # The official core-main action definition and use-case rule, under the SAME
  # customer-support operational identity as the already connected model route.
  : "${TALON_CORE_DIR:?set pinned Talon core checkout}"
  [[ -f "$TALON_CORE_DIR/examples/n8n-refund/use-case-action.append.yaml" ]] || exit 1
  sed "s#https://refunds.internal/v1/refunds#http://127.0.0.1:$SHOPIFY_PORT/refunds#" \
    "$TALON_CORE_DIR/examples/n8n-refund/use-case-action.append.yaml" \
    >> "$WORK/talon/agents/customer-support/agent.talon.yaml"
  "$BIN/talon" agents show customer-support --effective >"$WORK/effective-before.txt"
  grep -F 'delete_' "$WORK/effective-before.txt" >/dev/null || { echo 'Mandatory company constraint not inherited' >&2; exit 1; }
  reviewer_info="$("$BIN/talon" approver add --name synthetic-support-lead --tenant acme --groups support-leads)"
  DEMO_REVIEWER_KEY="$(printf '%s\n' "$reviewer_info" | grep -oE 'talon_appr_cred_[0-9a-f]+\.[A-Za-z0-9_-]+' | head -n1)"
  [[ -n "$DEMO_REVIEWER_KEY" ]] || { echo 'No independently scoped reviewer key' >&2; exit 1; }
  unset reviewer_info
  echo 'PASS: independent native reviewer registered outside n8n and use-case key scope'
else
  DEMO_TALON_KEY=synthetic-talon-agent-key
  "$BIN/talon" secrets set customer-support-talon-key "$DEMO_TALON_KEY" >/dev/null
fi
"$BIN/talon" secrets set openai-api-key synthetic-provider-key >/dev/null
"$BIN/talon" validate
"$BIN/talon" serve --port "$TALON_PORT" --gateway --gateway-config talon.config.yaml >"$WORK/talon.log" 2>&1 &
talon_pid=$!
for _ in $(seq 1 100); do curl -fsS "http://127.0.0.1:$TALON_PORT/health" >/dev/null 2>&1 && break; sleep .2; done
curl -fsS "http://127.0.0.1:$TALON_PORT/health" >/dev/null || { cat "$WORK/talon.log"; exit 1; }

IMAGE="${N8N_IMAGE:-docker.n8n.io/n8nio/n8n:2.30.4}"
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
if scenario.startswith("refund"):
    amount={"refund":"249","refund25":"25","refund750":"750"}[scenario]
    s=s.replace("Order #1001 status","Order #1001 refund").replace("When will my order #1001 arrive?","Please review order #1001 refund EUR "+amount+" for damaged product.")
if scenario=="wrong_sender": s=s.replace("buyer@example.test","other@example.test")
n["parameters"]["jsCode"]=s
w["active"]=False
Path(dest).write_text(json.dumps(w))
PY
  cat >"$dir/config/credentials.json" <<JSON
[
 {"id":"ShopifyReadOnlyHeader","name":"Shopify read-only (X-Shopify-Access-Token)","type":"httpHeaderAuth","data":{"name":"X-Shopify-Access-Token","value":"synthetic-read-only"}},
 {"id":"TalonSupportHeader","name":"Talon customer-support (Authorization)","type":"httpHeaderAuth","data":{"name":"Authorization","value":"Bearer ${DEMO_TALON_KEY}"}}
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
  ! grep -Fq "$DEMO_TALON_KEY" "$dir/config/export.json"
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
    assert out["proposed_refund_eur"]==({"refund":"249.00","refund25":"25.00","refund750":"750.00"}.get(scenario)),out
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
if [[ -n "${TALON_EXTERNAL_BIN:-}" ]]; then
  before="$(grep -c '"kind": "provider_call"' "$WORK/fixture.jsonl")"
  status="$(curl -sS -o "$WORK/pii-denial.json" -w '%{http_code}' \
    -H "Authorization: Bearer $DEMO_TALON_KEY" -H "Content-Type: application/json" \
    -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Email buyer@example.test and IBAN PL61109010140000071219812874"}]}' \
    "http://127.0.0.1:$TALON_PORT/v1/proxy/openai/v1/chat/completions")"
  [[ "$status" == 400 || "$status" == 403 ]] || { echo "Expected company PII denial, got HTTP $status" >&2; exit 1; }
  after="$(grep -c '"kind": "provider_call"' "$WORK/fixture.jsonl")"
  [[ "$before" == "$after" ]] || { echo 'Company PII deny reached provider' >&2; exit 1; }
  "$BIN/talon" audit export --format signed-json --output "$WORK/output/evidence-after-denial.json" >/dev/null
  "$BIN/talon" audit verify --file "$WORK/output/evidence-after-denial.json" >/dev/null
  "$BIN/talon" agents show customer-support --effective >"$WORK/effective-after.txt"
  grep -F 'delete_' "$WORK/effective-after.txt" >/dev/null
  echo 'PASS: native use case inherited company PII denial; zero provider dispatch and valid signatures'
fi
if [[ -n "${TALON_EXTERNAL_BIN:-}" ]]; then
  # Two more verified merchant-test-order proposals from the exact same n8n
  # support workflow and Talon use-case key. These are NOT authorization.
  run_case "$WORK/four" "$ROOT/shopify-support.workflow.json" refund25 draft_ready_for_operator_review
  run_case "$WORK/five" "$ROOT/shopify-support.workflow.json" refund750 draft_ready_for_operator_review
  # Same process, policy, keys and business fixture: continue into canonical
  # native action operations without replacing the running Talon process.
  source "$ROOT/test-current-main-actions.sh"
fi
echo 'PASS Stage A real n8n + actual Talon binary + synthetic Shopify and provider (NOT live Shopify or model)'
if [[ -n "${TALON_EXTERNAL_BIN:-}" ]]; then
  if [[ "${TALON_EXTERNAL_KIND:-source-main}" == "published-rc2" ]]; then
    echo 'NOTE: prerelease artifact compatibility only; NOT final stable or a real Shopify/payment run'
  else
    echo 'NOTE: source-built pinned Talon commit is development only, not a released artifact'
  fi
fi
 ||
        { echo 'Downloaded binary does not identify as v1.17.0-rc.2' >&2; exit 1; } ;;
    *) echo "Unsupported TALON_EXTERNAL_KIND" >&2; exit 1 ;;
  esac
else
  version=v1.16.1
  archive=talon_1.16.1_linux_amd64.tar.gz
  curl -fsSL --retry 3 "https://github.com/dativo-io/talon/releases/download/$version/$archive" -o "$WORK/$archive"
  printf '%s  %s\n' bc5147dedfb59608b0be1ec07b6da78ef430bc833ccc7fddfa444760f2e94a4e "$WORK/$archive" | sha256sum -c -
  tar -xzf "$WORK/$archive" -C "$BIN" talon
  reported="$("$BIN/talon" version)"
  printf '%s\n' "$reported"
  [[ "$(printf '%s\n' "$reported" | head -n1)" == "Talon 1.16.1" ]] || { echo 'Unexpected released binary version'; exit 1; }
fi
sha256sum "$BIN/talon"

export TALON_SECRETS_KEY="$(openssl rand -hex 32)"
export TALON_SIGNING_KEY="$(openssl rand -hex 32)"
export TALON_ADMIN_KEY="$(openssl rand -hex 32)"
export TALON_DATA_DIR="$WORK/talon/data"
mkdir -p "$TALON_DATA_DIR"
SHOPIFY_PORT=19091
TALON_PORT=19092
if [[ -n "${TALON_EXTERNAL_BIN:-}" ]]; then
  python3 "$ROOT/fixture.py" --port "$SHOPIFY_PORT" --log "$WORK/fixture.jsonl" --action-fixture >"$WORK/fixture.log" 2>&1 &
else
  python3 "$ROOT/fixture.py" --port "$SHOPIFY_PORT" --log "$WORK/fixture.jsonl" >"$WORK/fixture.log" 2>&1 &
fi
fixture_pid=$!
for _ in $(seq 1 50); do curl -fsS "http://127.0.0.1:$SHOPIFY_PORT/health" >/dev/null 2>&1 && break; sleep .2; done
curl -fsS "http://127.0.0.1:$SHOPIFY_PORT/health" >/dev/null
cd "$WORK/talon"
if [[ -z "${TALON_EXTERNAL_BIN:-}" ]]; then
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
fi
if [[ -n "${TALON_EXTERNAL_BIN:-}" ]]; then
  company_agents='agents_dir: ./agents'
  company_constraints='    constraints:
      forbidden_tools: ["delete_*"]
      action_approvals:
        argument_rules:
          refund-too-large:
            actions: [create_refund_request]
            argument: amount
            type: decimal
            operator: gt
            value: "500.00"
            effect: deny'
  pii_action=block
else
  company_agents=''
  company_constraints=''
  pii_action=redact
fi
cat >talon.config.yaml <<YAML
${company_agents}
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
      pii_action: ${pii_action}
      daily_cost: 10.00
    log_prompts: false
    log_responses: false
${company_constraints}
YAML
if [[ -n "${TALON_EXTERNAL_BIN:-}" ]]; then
  # Native registration has one independently authenticated operational key.
  registration="$("$BIN/talon" agents add customer-support --tenant acme --owner support-operations --description "Shopify support draft through Talon" 2>&1)"
  DEMO_TALON_KEY="$(printf '%s\n' "$registration" | grep -oE 'talon_uc_[0-9a-f]{48}' | head -n1)"
  [[ -n "$DEMO_TALON_KEY" ]] || { echo 'Native registration failed' >&2; printf '%s\n' "$registration" | sed -E 's/talon_uc_[0-9a-f]{48}/[REDACTED]/g' >&2; exit 1; }
  echo 'PASS: native registered customer-support with an issued Talon use-case key'
  # The official core-main action definition and use-case rule, under the SAME
  # customer-support operational identity as the already connected model route.
  : "${TALON_CORE_DIR:?set pinned Talon core checkout}"
  [[ -f "$TALON_CORE_DIR/examples/n8n-refund/use-case-action.append.yaml" ]] || exit 1
  sed "s#https://refunds.internal/v1/refunds#http://127.0.0.1:$SHOPIFY_PORT/refunds#" \
    "$TALON_CORE_DIR/examples/n8n-refund/use-case-action.append.yaml" \
    >> "$WORK/talon/agents/customer-support/agent.talon.yaml"
  "$BIN/talon" agents show customer-support --effective >"$WORK/effective-before.txt"
  grep -F 'delete_' "$WORK/effective-before.txt" >/dev/null || { echo 'Mandatory company constraint not inherited' >&2; exit 1; }
  reviewer_info="$("$BIN/talon" approver add --name synthetic-support-lead --tenant acme --groups support-leads)"
  DEMO_REVIEWER_KEY="$(printf '%s\n' "$reviewer_info" | grep -oE 'talon_appr_cred_[0-9a-f]+\.[A-Za-z0-9_-]+' | head -n1)"
  [[ -n "$DEMO_REVIEWER_KEY" ]] || { echo 'No independently scoped reviewer key' >&2; exit 1; }
  unset reviewer_info
  echo 'PASS: independent native reviewer registered outside n8n and use-case key scope'
else
  DEMO_TALON_KEY=synthetic-talon-agent-key
  "$BIN/talon" secrets set customer-support-talon-key "$DEMO_TALON_KEY" >/dev/null
fi
"$BIN/talon" secrets set openai-api-key synthetic-provider-key >/dev/null
"$BIN/talon" validate
"$BIN/talon" serve --port "$TALON_PORT" --gateway --gateway-config talon.config.yaml >"$WORK/talon.log" 2>&1 &
talon_pid=$!
for _ in $(seq 1 100); do curl -fsS "http://127.0.0.1:$TALON_PORT/health" >/dev/null 2>&1 && break; sleep .2; done
curl -fsS "http://127.0.0.1:$TALON_PORT/health" >/dev/null || { cat "$WORK/talon.log"; exit 1; }

IMAGE="${N8N_IMAGE:-docker.n8n.io/n8nio/n8n:2.30.4}"
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
if scenario.startswith("refund"):
    amount={"refund":"249","refund25":"25","refund750":"750"}[scenario]
    s=s.replace("Order #1001 status","Order #1001 refund").replace("When will my order #1001 arrive?","Please review order #1001 refund EUR "+amount+" for damaged product.")
if scenario=="wrong_sender": s=s.replace("buyer@example.test","other@example.test")
n["parameters"]["jsCode"]=s
w["active"]=False
Path(dest).write_text(json.dumps(w))
PY
  cat >"$dir/config/credentials.json" <<JSON
[
 {"id":"ShopifyReadOnlyHeader","name":"Shopify read-only (X-Shopify-Access-Token)","type":"httpHeaderAuth","data":{"name":"X-Shopify-Access-Token","value":"synthetic-read-only"}},
 {"id":"TalonSupportHeader","name":"Talon customer-support (Authorization)","type":"httpHeaderAuth","data":{"name":"Authorization","value":"Bearer ${DEMO_TALON_KEY}"}}
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
  ! grep -Fq "$DEMO_TALON_KEY" "$dir/config/export.json"
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
    assert out["proposed_refund_eur"]==({"refund":"249.00","refund25":"25.00","refund750":"750.00"}.get(scenario)),out
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
if [[ -n "${TALON_EXTERNAL_BIN:-}" ]]; then
  before="$(grep -c '"kind": "provider_call"' "$WORK/fixture.jsonl")"
  status="$(curl -sS -o "$WORK/pii-denial.json" -w '%{http_code}' \
    -H "Authorization: Bearer $DEMO_TALON_KEY" -H "Content-Type: application/json" \
    -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Email buyer@example.test and IBAN PL61109010140000071219812874"}]}' \
    "http://127.0.0.1:$TALON_PORT/v1/proxy/openai/v1/chat/completions")"
  [[ "$status" == 400 || "$status" == 403 ]] || { echo "Expected company PII denial, got HTTP $status" >&2; exit 1; }
  after="$(grep -c '"kind": "provider_call"' "$WORK/fixture.jsonl")"
  [[ "$before" == "$after" ]] || { echo 'Company PII deny reached provider' >&2; exit 1; }
  "$BIN/talon" audit export --format signed-json --output "$WORK/output/evidence-after-denial.json" >/dev/null
  "$BIN/talon" audit verify --file "$WORK/output/evidence-after-denial.json" >/dev/null
  "$BIN/talon" agents show customer-support --effective >"$WORK/effective-after.txt"
  grep -F 'delete_' "$WORK/effective-after.txt" >/dev/null
  echo 'PASS: native use case inherited company PII denial; zero provider dispatch and valid signatures'
fi
if [[ -n "${TALON_EXTERNAL_BIN:-}" ]]; then
  # Two more verified merchant-test-order proposals from the exact same n8n
  # support workflow and Talon use-case key. These are NOT authorization.
  run_case "$WORK/four" "$ROOT/shopify-support.workflow.json" refund25 draft_ready_for_operator_review
  run_case "$WORK/five" "$ROOT/shopify-support.workflow.json" refund750 draft_ready_for_operator_review
  # Same process, policy, keys and business fixture: continue into canonical
  # native action operations without replacing the running Talon process.
  source "$ROOT/test-current-main-actions.sh"
fi
echo 'PASS Stage A real n8n + actual Talon binary + synthetic Shopify and provider (NOT live Shopify or model)'
if [[ -n "${TALON_EXTERNAL_BIN:-}" ]]; then echo 'NOTE: source-built pinned core main is development only, not a released artifact'; fi
