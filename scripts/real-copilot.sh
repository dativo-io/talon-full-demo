#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
ENV_FILE="$ROOT/.env"
RUN_ENV="$STATE/demo-run.env"
OUTPUT_MODE="${COPILOT_DEMO_OUTPUT:-full}"

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

case "$OUTPUT_MODE" in
  full|quiet) ;;
  *) die "COPILOT_DEMO_OUTPUT must be full or quiet" ;;
esac

find_copilot() {
  if [[ -n "${COPILOT_BIN:-}" ]]; then
    [[ -x "$COPILOT_BIN" ]] || die "COPILOT_BIN is not executable: $COPILOT_BIN"
    printf '%s\n' "$COPILOT_BIN"
    return 0
  fi
  if [[ -x "$HOME/.local/bin/copilot" ]]; then
    printf '%s\n' "$HOME/.local/bin/copilot"
    return 0
  fi
  if command -v copilot >/dev/null 2>&1; then
    command -v copilot
    return 0
  fi
  return 1
}

COPILOT="$(find_copilot || true)"
if [[ -z "$COPILOT" ]]; then
  cat >&2 <<'MESSAGE'
ERROR: GitHub Copilot CLI is not installed or is not on PATH.

Install the official CLI with:
  make copilot-install

Then run:
  make real-copilot
MESSAGE
  exit 1
fi

version="$(bash "$ROOT/scripts/check-copilot-cli.sh" "$COPILOT")"

[[ -f "$ENV_FILE" ]] || die "missing .env; run make real-prepare"
# shellcheck disable=SC1090
source "$ENV_FILE"

curl --fail --silent --max-time 2 "$TALON_GATEWAY/health" >/dev/null \
  || die "Talon gateway is not running; run make real-start"
curl --fail --silent --max-time 2 "$TALON_MCP_GATEWAY/health" >/dev/null \
  || die "Talon MCP proxy is not running; run make real-start"

say "Using GitHub Copilot CLI: $version"
say "Binary: $COPILOT"

# Every attempt gets a fresh session, nonce, empty receipts file, freshly
# restarted shim, and empty Copilot state. Previous runs cannot satisfy the
# current run's assertions.
say "Minting a fresh bounded Copilot run..."
"$ROOT/scripts/preflight.sh"
"$ROOT/scripts/stop-components.sh" >/dev/null 2>&1 || true
"$ROOT/scripts/start-components.sh" >/dev/null
# shellcheck disable=SC1090
source "$RUN_ENV"
"$ROOT/scripts/render-copilot-mcp-config.sh" >/dev/null

nonce="$(cat "$STATE/run-nonce")"
timeout_seconds="${COPILOT_DEMO_TIMEOUT_SECONDS:-90}"
transcript="$STATE/copilot-$TALON_DEMO_RUN_ID.log"
rm -rf "$STATE/copilot-home"
mkdir -p "$STATE/copilot-home"

prompt="$(cat <<EOF_PROMPT
This is a bounded product integration proof. Do exactly this and nothing else:

1. Call release_status from the release-gateway MCP server with this exact run_nonce: $nonce
2. Call release_prepare from the release-gateway MCP server with the same exact run_nonce: $nonce
3. Stop immediately after those two calls and briefly report their outcomes.

Do not run shell commands, read or modify files, call release_publish, retry, delegate, use subagents, or inspect anything else.
EOF_PROMPT
)"

run_copilot() {
  (
    cd "$ROOT"
    export PATH="$(dirname "$COPILOT"):$PATH"
    export COPILOT_HOME="$STATE/copilot-home"
    export COPILOT_PROVIDER_TYPE=openai
    export COPILOT_PROVIDER_BASE_URL="http://127.0.0.1:8079/v1/proxy/openai/v1"
    export COPILOT_PROVIDER_API_KEY="$TALON_CODING_ASSISTANT_KEY"
    export COPILOT_MODEL="${COPILOT_MODEL:-gpt-4o-mini}"
    export COPILOT_OFFLINE=true
    export COPILOT_TASK_WAIT_TIMEOUT_SECONDS=30
    python3 "$ROOT/scripts/run-with-timeout.py" "$timeout_seconds" \
      "$COPILOT" \
        --prompt "$prompt" \
        --no-ask-user \
        --no-custom-instructions \
        --additional-mcp-config="@$STATE/copilot-mcp.json" \
        --disable-builtin-mcps \
        --allow-tool='release-gateway(release_status)' \
        --allow-tool='release-gateway(release_prepare)' \
        --deny-tool='shell' \
        --deny-tool='write'
  )
}

say
say "Running one bounded Copilot MCP prompt (hard limit: ${timeout_seconds}s)..."
say "Session: $TALON_COPILOT_SESSION_ID"
say "Transcript: $transcript"
say

set +e
if [[ "$OUTPUT_MODE" == "quiet" ]]; then
  run_copilot >"$transcript" 2>&1
  rc=$?
else
  run_copilot 2>&1 | tee "$transcript"
  rc="${PIPESTATUS[0]}"
fi
set -e

if [[ "$rc" -eq 124 ]]; then
  [[ "$OUTPUT_MODE" == "quiet" ]] && tail -n 80 "$transcript" >&2
  die "Copilot exceeded ${timeout_seconds}s. The run was terminated and does not count as a demo pass."
fi
if [[ "$rc" -eq 130 ]]; then
  [[ "$OUTPUT_MODE" == "quiet" ]] && tail -n 80 "$transcript" >&2
  die "Copilot run was cancelled. Child processes were terminated; rerun make real-copilot for a fresh attempt."
fi
if [[ "$rc" -ne 0 ]]; then
  [[ "$OUTPUT_MODE" == "quiet" ]] && tail -n 80 "$transcript" >&2
  die "Copilot exited with status $rc; inspect $transcript"
fi
[[ "$OUTPUT_MODE" == "quiet" ]] && say "Copilot completed; full client transcript retained at $transcript"

say
say "Verifying the result independently..."
"$ROOT/scripts/assert-release-blocked.sh"
"$ROOT/scripts/assert-evidence.sh" \
  --session "$TALON_COPILOT_SESSION_ID" \
  --agent coding-assistant \
  --since "$TALON_RUN_START_RFC3339"

say
say "REAL COPILOT CASE PASSED"
say "  Client: real GitHub Copilot CLI used Talon's OpenAI-compatible gateway"
say "  MCP: release_status + release_prepare reached the synthetic upstream"
say "  Boundary: no release_publish receipt reached the upstream"
say "  Evidence: current-run records are signed and attributed to coding-assistant"
say "  Scope: proves the real client, model, MCP, identity, and evidence path"
say "  Session: $TALON_COPILOT_SESSION_ID"
say "  Transcript: $transcript"
say
say "Present this same verified session with:"
say "  make present-copilot       # buyer view"
say "  make present-copilot-tech  # technical view"
