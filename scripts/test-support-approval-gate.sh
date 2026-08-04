#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
PID=""
cleanup() {
  [[ -n "$PID" ]] && kill -TERM "$PID" 2>/dev/null || true
  [[ -n "$PID" ]] && wait "$PID" 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

PORT="$(python3 - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    print(sock.getsockname()[1])
PY
)"
KEY="$WORK/key"
STATE="$WORK/state"
URL="http://127.0.0.1:$PORT"
openssl rand -hex 32 >"$KEY"
chmod 0600 "$KEY"
python3 "$ROOT/scripts/support-approval-server.py" \
  --host 127.0.0.1 --port "$PORT" --state-dir "$STATE" --signing-key-file "$KEY" \
  >"$WORK/server.log" 2>&1 &
PID="$!"
for _ in $(seq 1 100); do
  curl -fsS "$URL/health" >/dev/null 2>&1 && break
  sleep 0.05
done
curl -fsS "$URL/health" >/dev/null || { cat "$WORK/server.log" >&2; exit 1; }

create_request() {
  local id="$1" session="$2" nonce="$3"
  curl -fsS -H 'Content-Type: application/json' \
    -d "{\"approval_id\":\"$id\",\"session_id\":\"$session\",\"run_nonce\":\"$nonce\",\"ticket_id\":\"SUP-1042\",\"amount_eur\":249,\"requested_action\":\"issue_refund\"}" \
    "$URL/requests" >/dev/null
}

ID1=apr_gate_test_approved
SESSION1=session-approved
NONCE1=nonce-approved
create_request "$ID1" "$SESSION1" "$NONCE1"
curl -fsS "$URL/wait/$ID1?timeout=10" >"$WORK/wait-approved.json" &
WAIT_PID="$!"
sleep 0.4
kill -0 "$WAIT_PID" 2>/dev/null || { echo 'approval wait returned before an explicit decision' >&2; exit 1; }
[[ ! -e "$STATE/$ID1.receipt.json" ]] || { echo 'approval receipt existed before a decision' >&2; exit 1; }

BAD_CODE="$(curl --silent --output "$WORK/bad.json" --write-out '%{http_code}' \
  -H 'Accept: application/json' -H 'Content-Type: application/json' -d '{}' \
  "$URL/approval/apr_wrong_session/approve")"
[[ "$BAD_CODE" == 404 ]] || { echo "mismatched approval unexpectedly returned HTTP $BAD_CODE" >&2; exit 1; }
kill -0 "$WAIT_PID" 2>/dev/null || { echo 'mismatched approval released the wait' >&2; exit 1; }

curl -fsS -H 'Accept: application/json' -H 'Content-Type: application/json' \
  -d '{"operator":"gate-test"}' "$URL/approval/$ID1/approve" >/dev/null
wait "$WAIT_PID"
python3 "$ROOT/scripts/verify-support-approval.py" \
  --receipt "$WORK/wait-approved.json" --key "$KEY" --session "$SESSION1" \
  --run-nonce "$NONCE1" --ticket SUP-1042 --amount 249 --action issue_refund \
  --decision approved >/dev/null

ID2=apr_gate_test_rejected
SESSION2=session-rejected
NONCE2=nonce-rejected
create_request "$ID2" "$SESSION2" "$NONCE2"
curl -fsS "$URL/wait/$ID2?timeout=10" >"$WORK/wait-rejected.json" &
WAIT_PID="$!"
sleep 0.4
kill -0 "$WAIT_PID" 2>/dev/null || { echo 'rejection wait returned before the decision' >&2; exit 1; }
curl -fsS -H 'Accept: application/json' -H 'Content-Type: application/json' \
  -d '{"operator":"gate-test"}' "$URL/approval/$ID2/reject" >/dev/null
wait "$WAIT_PID"
python3 "$ROOT/scripts/verify-support-approval.py" \
  --receipt "$WORK/wait-rejected.json" --key "$KEY" --session "$SESSION2" \
  --run-nonce "$NONCE2" --ticket SUP-1042 --amount 249 --action issue_refund \
  --decision rejected >/dev/null

echo 'SUPPORT OPERATOR APPROVAL GATE PASSED'
