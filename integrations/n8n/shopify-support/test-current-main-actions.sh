#!/usr/bin/env bash
# Sourced in the same Bash process as test-n8n.sh after real Shopify-style
# n8n draft runs. Development-only: Talon core main, deterministic upstream,
# real n8n, and independently counted synthetic refund adapter. NO PAYMENTS.
set -euo pipefail
: "$TALON_EXTERNAL_BIN" "$TALON_CORE_DIR" "$DEMO_TALON_KEY" "$DEMO_REVIEWER_KEY" "$TALON_PORT"
echo '== Stage B: canonical action gateway in the SAME Talon runtime and support identity'
for pair in 'two 249.00' 'four 25.00' 'five 750.00'; do
  set -- $pair
  python3 - "$WORK/$1/final.json" "$2" <<'PY'
import json,sys
v=json.load(open(sys.argv[1]))
assert v["ticket_id"]=="SUP-1001" and v["status"]=="draft_ready_for_operator_review",v
assert v["proposed_refund_eur"]==sys.argv[2],v
assert v["merchant_eligibility"]=="not_established",v
assert v["refund_execution"]=="unavailable" and not v["message_sent"],v
PY
done

ACTION_DIR="$WORK/action"; mkdir -p "$ACTION_DIR/runtime" "$ACTION_DIR/config"
python3 - "$TALON_CORE_DIR/examples/n8n-refund/refund-approval.workflow.json" "$ACTION_DIR/config/workflow.json" "$TALON_PORT" <<'PY'
import json,sys
w=json.load(open(sys.argv[1]))
assert w["active"] is False
n={node["name"] for node in w["nodes"]}
assert {"Talon: establish operation","Talon: read operation","Talon: claim (Talon dispatches)","Wait for reviewer"}<=n
assert all(x["type"].startswith("n8n-nodes-base.") for x in w["nodes"])
http=[x for x in w["nodes"] if x["type"]=="n8n-nodes-base.httpRequest"]
assert len(http)==3 and all("/v1/action-operations" in x["parameters"]["url"] for x in http)
assert all("/refunds" not in x["parameters"]["url"] for x in http)
w["id"]="acmeshopifyaction01"
for x in w["nodes"]:
    if x["name"]=="Config": x["parameters"]["assignments"]["assignments"][0]["value"]="http://127.0.0.1:"+sys.argv[3]
    for cred in x.get("credentials",{}).values():
        if cred.get("name")=="Talon refund-bot key":
            cred.update({"id":"talon-shopify-action-key","name":"Talon customer-support action key"})
json.dump([w],open(sys.argv[2],"w"))
PY
ACTION_CALLER="$(openssl rand -hex 24)"
cat >"$ACTION_DIR/config/credentials.json" <<JSON
[
  {"id":"talon-shopify-action-key","name":"Talon customer-support action key","type":"httpHeaderAuth","data":{"name":"Authorization","value":"Bearer $DEMO_TALON_KEY"}},
  {"id":"refund-webhook-caller","name":"Refund webhook caller","type":"httpHeaderAuth","data":{"name":"X-Refund-Caller","value":"$ACTION_CALLER"}}
]
JSON
run_n8n "$ACTION_DIR" import:credentials --input=/demo/config/credentials.json >/dev/null
run_n8n "$ACTION_DIR" import:workflow --input=/demo/config/workflow.json >/dev/null
run_n8n "$ACTION_DIR" publish:workflow --id=acmeshopifyaction01 >/dev/null
run_n8n "$ACTION_DIR" export:workflow --all --output=/demo/config/export.json >/dev/null
! grep -Fq "$DEMO_TALON_KEY" "$ACTION_DIR/config/export.json"
! grep -Fq "$ACTION_CALLER" "$ACTION_DIR/config/export.json"
! grep -Fq "$DEMO_REVIEWER_KEY" "$ACTION_DIR/config/export.json"
! grep -Fq '/refunds' "$ACTION_DIR/config/export.json"
echo 'PASS official stock-node workflow imported/published without secrets or adapter URL'

N8N_ACTION_PORT=19413
ACTION_WEBHOOK="http://127.0.0.1:$N8N_ACTION_PORT/webhook/talon-refund"
action_n8n_container="acme-shopify-refund-$$"
docker run -d --name "$action_n8n_container" --network host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/home/node -e N8N_USER_FOLDER=/home/node/.n8n -e N8N_ENCRYPTION_KEY \
  -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_VERSION_NOTIFICATIONS_ENABLED=false \
  -e N8N_TEMPLATES_ENABLED=false -e N8N_PERSONALIZATION_ENABLED=false \
  -e N8N_HIRING_BANNER_ENABLED=false -e N8N_LOG_LEVEL=warn -e N8N_PORT="$N8N_ACTION_PORT" \
  -e N8N_LISTEN_ADDRESS=127.0.0.1 -e GENERIC_TIMEZONE=UTC \
  -v "$ACTION_DIR/runtime:/home/node/.n8n" "$IMAGE" start >"$ACTION_DIR/container-id"
found=no
for _ in $(seq 1 180); do
  code="$(curl -sS --max-time 3 -o /dev/null -w '%{http_code}' -X POST "$ACTION_WEBHOOK" -H 'Content-Type: application/json' -d '{}' 2>/dev/null || true)"
  if [[ "$code" == 403 ]]; then found=yes; break; fi
  sleep 1
done
[[ "$found" == yes ]] || { docker logs "$action_n8n_container" | tail -n 80; echo 'Secured webhook unavailable' >&2; exit 1; }
echo 'PASS actual published n8n webhook denies unauthenticated ingress'

count_actions() {
  curl -fsS "http://127.0.0.1:$SHOPIFY_PORT/count" | python3 -c 'import json,sys;print(json.load(sys.stdin)["calls"])'
}
action_payload() {
  printf '{"ticket_id":"SUP-1001","amount":"%s","currency":"EUR","request_id":"shopify-%s"}' "$1" "$2"
}
submit_action() {
  curl -sS -o "$2" -w '%{http_code}' --max-time 120 -X POST "$ACTION_WEBHOOK" \
    -H 'Content-Type: application/json' -H "X-Refund-Caller: $ACTION_CALLER" -d "$1"
}
result_field() {
  python3 - "$1" <<'PY'
import json,sys
print(json.load(open(sys.argv[1])).get("result",""))
PY
}
verify_lifecycle() {
  "$BIN/talon" audit verify --operation "$1" >"$ACTION_DIR/$1.verify" 2>&1
  grep -F 'Lifecycle: VALID' "$ACTION_DIR/$1.verify" >/dev/null || { cat "$ACTION_DIR/$1.verify"; return 1; }
  echo "PASS signed lifecycle: $1"
}
[[ "$(count_actions)" == 0 ]] || { echo 'Preauthorization synthetic finance dispatch' >&2; exit 1; }

status="$(submit_action "$(action_payload 750.00 750)" "$ACTION_DIR/deny.json")"
[[ "$status" == 403 && "$(result_field "$ACTION_DIR/deny.json")" == denied && "$(count_actions)" == 0 ]] || { echo 'Company 750 denial failed' >&2; cat "$ACTION_DIR/deny.json"; exit 1; }
verify_lifecycle refund-SUP-1001-shopify-750
echo 'PASS EUR750 company DENY: zero business effects'

status="$(submit_action "$(action_payload 25.00 25)" "$ACTION_DIR/allow.json")"
[[ "$status" == 200 && "$(result_field "$ACTION_DIR/allow.json")" == refunded && "$(count_actions)" == 1 ]] || { echo '25 allowance failed' >&2; cat "$ACTION_DIR/allow.json"; exit 1; }
verify_lifecycle refund-SUP-1001-shopify-25
echo 'PASS EUR25 ALLOW: one Talon-forwarded independently counted synthetic effect'

status="$(submit_action "$(action_payload 25.00 25)" "$ACTION_DIR/replay.json")"
[[ "$status" == 200 && "$(result_field "$ACTION_DIR/replay.json")" == refunded && "$(count_actions)" == 1 ]] || exit 1
status="$(submit_action "$(action_payload 26.00 25)" "$ACTION_DIR/conflict.json")"
[[ "$status" == 409 && "$(count_actions)" == 1 ]] || exit 1
echo 'PASS stable retry returns recorded outcome, conflicting arguments cannot re-dispatch'

submit_action "$(action_payload 249.00 249)" "$ACTION_DIR/review.json" >"$ACTION_DIR/review.status" &
review_request_pid=$!
approval_id=''
for _ in $(seq 1 45); do
  approval_id="$(TALON_APPROVER_KEY="$DEMO_REVIEWER_KEY" "$BIN/talon" approvals list --url "http://127.0.0.1:$TALON_PORT" --json 2>/dev/null | python3 -c 'import json,sys
try: print(next((a["approval_id"] for a in json.load(sys.stdin).get("approvals",[]) if a.get("approval_id")),""))
except Exception: print("")')"
  [[ -n "$approval_id" ]] && break
  sleep 1
done
[[ -n "$approval_id" && "$(count_actions)" == 1 ]] || { echo 'Review pending did not preserve zero effects' >&2; exit 1; }
TALON_APPROVER_KEY="$DEMO_REVIEWER_KEY" "$BIN/talon" approvals show "$approval_id" \
 --url "http://127.0.0.1:$TALON_PORT" --json >"$ACTION_DIR/approval.json"
python3 - "$ACTION_DIR/approval.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1]))
assert "refund-SUP-1001-shopify-249" in json.dumps(x),x
assert "249.00" in json.dumps(x),x
PY
TALON_APPROVER_KEY="$DEMO_REVIEWER_KEY" "$BIN/talon" approvals approve "$approval_id" \
  --reason 'Independent synthetic test-order eligibility review' \
  --url "http://127.0.0.1:$TALON_PORT" >/dev/null
[[ "$(count_actions)" == 1 ]] || { echo 'Approval itself illegally dispatched action' >&2; exit 1; }
wait "$review_request_pid"
[[ "$(cat "$ACTION_DIR/review.status")" == 200 && "$(result_field "$ACTION_DIR/review.json")" == refunded && "$(count_actions)" == 2 ]] || { cat "$ACTION_DIR/review.json"; exit 1; }
verify_lifecycle refund-SUP-1001-shopify-249
echo 'PASS EUR249 separate reviewer, exact approved action and one post-claim effect'

curl -fsS "http://127.0.0.1:$SHOPIFY_PORT/count" >"$ACTION_DIR/ledger.json"
python3 - "$ACTION_DIR/ledger.json" <<'PY'
import json,sys
v=json.load(open(sys.argv[1]))
assert v["calls"]==2,v
assert [o["amount"] for o in v["operations"]]==["25.00","249.00"],v
assert all(o["ticket_id"]=="SUP-1001" and o["idempotency"] for o in v["operations"]),v
assert len({o["idempotency"] for o in v["operations"]})==2,v
PY
"$BIN/talon" agents show customer-support --effective >"$ACTION_DIR/effective.txt"
grep -F 'refund-too-large' "$ACTION_DIR/effective.txt" >/dev/null || { echo 'Company action rule absent from effective projection'; exit 1; }
echo 'PASS joined source-main Talon: one support identity, real n8n draft -> canonical action, signed proof, independent fake finance ledger'
echo 'NOT claimed: real Shopify write, paid model, released v1.17.0, exactly-once business effect'
