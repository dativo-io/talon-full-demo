#!/usr/bin/env bash
# Real-Talon, credential-free People Analytics governance acceptance.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CASE="$ROOT/cases/people-analytics-copilot"
TALON_BIN="$(command -v talon)"
[[ -x "$TALON_BIN" ]] || { echo "Talon binary required" >&2; exit 1; }
TEMP="$(mktemp -d)"
HR_PID=""
DASH_PID=""
TALON_PID=""
GW_PID=""
LLM_PID=""
cleanup() {
  if [[ -n "$TALON_PID" ]]; then kill "$TALON_PID" 2>/dev/null || true; wait "$TALON_PID" 2>/dev/null || true; fi
  if [[ -n "$GW_PID" ]]; then kill "$GW_PID" 2>/dev/null || true; wait "$GW_PID" 2>/dev/null || true; fi
  if [[ -n "$LLM_PID" ]]; then kill "$LLM_PID" 2>/dev/null || true; wait "$LLM_PID" 2>/dev/null || true; fi
  if [[ -n "$DASH_PID" ]]; then kill "$DASH_PID" 2>/dev/null || true; wait "$DASH_PID" 2>/dev/null || true; fi
  if [[ -n "$HR_PID" ]]; then kill "$HR_PID" 2>/dev/null || true; wait "$HR_PID" 2>/dev/null || true; fi
  if [[ "$KEEP_HR_DEMO_ARTIFACTS" != "1" ]]; then rm -rf "$TEMP"; else echo "Logs: $TEMP"; fi
}
KEEP_HR_DEMO_ARTIFACTS="0"
trap cleanup EXIT
trap 'echo "People Analytics Talon gate failed. Logs:" >&2; tail -80 "$TEMP/talon.log" "$TEMP/dashboard.log" "$TEMP/hr.log" "$TEMP/gateway.log" "$TEMP/llm.log" >&2 2>/dev/null || true' ERR
export HR_DEMO_DB_PATH="$TEMP/hr.duckdb"
(cd "$CASE" && python3 warehouse.py seed)
export TALON_DATA_DIR="$TEMP/state"
mkdir -p "$TALON_DATA_DIR"
export TALON_SECRETS_KEY="$(openssl rand -hex 32)"
export TALON_SIGNING_KEY="$(openssl rand -hex 32)"
export TALON_ADMIN_KEY="$(openssl rand -hex 24)"

(cd "$CASE" && exec python3 demo.py hr >"$TEMP/hr.log" 2>&1) &
HR_PID=$!
for n in {1..60}; do
  if curl --silent --fail http://127.0.0.1:9091/debug/counters >/dev/null 2>&1; then break; fi
  sleep .5
done
curl --silent --fail http://127.0.0.1:9091/debug/counters >/dev/null

(cd "$CASE" && exec python3 demo.py dashboard >"$TEMP/dashboard.log" 2>&1) &
DASH_PID=$!
for n in {1..60}; do
  if curl --silent --fail http://127.0.0.1:9093/api/dashboard >/dev/null 2>&1; then break; fi
  sleep .5
done
curl --silent --fail http://127.0.0.1:9093/api/dashboard >/dev/null

# Model emulation is the upstream OF A REAL TALON LLM GATEWAY. Never fake Talon.
(cd "$CASE" && exec python3 mock_llm.py >"$TEMP/llm.log" 2>&1) &
LLM_PID=$!
for n in {1..60}; do
  if curl --silent --fail http://127.0.0.1:9092/health >/dev/null 2>&1; then break; fi
  sleep .5
done
curl --silent --fail http://127.0.0.1:9092/health >/dev/null

sed 's|https://api.openai.com|http://127.0.0.1:9092|' \
  "$CASE/gateway.talon.yaml" > "$TEMP/gateway.talon.yaml"

(
  cd "$TALON_DATA_DIR"
  "$TALON_BIN" init --scaffold --name hr-analytics-assistant
  cp "$CASE/agent.talon.yaml" "$TALON_DATA_DIR/agent.talon.yaml"
  "$TALON_BIN" validate
  "$TALON_BIN" secrets set hr-analytics-assistant-talon-key talon-hr-demo-key-0001
  "$TALON_BIN" secrets set openai-api-key sk-demo-mock-provider-not-a-real-api-key
  exec "$TALON_BIN" serve --host 127.0.0.1 --port 8080 --proxy-config "$CASE/proxy.talon.yaml"
) >"$TEMP/talon.log" 2>&1 &
TALON_PID=$!
for n in {1..60}; do
  if curl --silent --fail http://127.0.0.1:8080/health >/dev/null 2>&1; then break; fi
  sleep .5
done
curl --silent --fail http://127.0.0.1:8080/health >/dev/null


# Same data directory, signing vault and agent identity as the MCP proxy.
(
  cd "$TALON_DATA_DIR"
  exec "$TALON_BIN" serve --host 127.0.0.1 --port 8082 --gateway \
    --gateway-config "$TEMP/gateway.talon.yaml"
) >"$TEMP/gateway.log" 2>&1 &
GW_PID=$!
for n in {1..60}; do
  if curl --silent --fail http://127.0.0.1:8082/health >/dev/null 2>&1; then break; fi
  sleep .5
done
curl --silent --fail http://127.0.0.1:8082/health >/dev/null

(cd "$CASE" && python3 verify.py --talon-bin "$TALON_BIN")
(cd "$CASE" && python3 verify_live.py --talon-bin "$TALON_BIN")
echo "PASS: Real Talon People Analytics MCP + model-to-tool governance contract"
