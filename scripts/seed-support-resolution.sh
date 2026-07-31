#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
CONFIG_DIR="$ROOT/config/generated"
SOURCE_POLICY="$ROOT/config/agent-overlays/customer-support/agent.talon.yaml"
TARGET_DIR="$CONFIG_DIR/agents/customer-support"
TARGET_POLICY="$TARGET_DIR/agent.talon.yaml"

command -v talon >/dev/null 2>&1 || { echo 'missing command: talon' >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || { echo 'missing .env; run make real-prepare' >&2; exit 1; }
[[ -f "$CONFIG_DIR/talon.config.yaml" ]] || { echo 'missing generated Talon config; run make real-prepare' >&2; exit 1; }
[[ -s "$SOURCE_POLICY" ]] || { echo "missing customer-support overlay: $SOURCE_POLICY" >&2; exit 1; }

# Existing demo hosts may have an .env created before this n8n case existed.
# Add only the non-secret default session value; per-run preflight replaces it
# with a fresh identity before executing the workflow.
# shellcheck disable=SC1090
source "$ENV_FILE"
if [[ -z "${TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID:-}" ]]; then
  TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID=n8n-support-resolution-demo
  printf 'export TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID=%q\n' \
    "$TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID" >>"$ENV_FILE"
  chmod 0600 "$ENV_FILE"
fi

install -d -m 0700 "$TARGET_DIR"
cp "$SOURCE_POLICY" "$TARGET_POLICY"
chmod 0600 "$TARGET_POLICY"

# The base prepare path already seeded customer-support-talon-key and both
# provider secrets. This step changes policy only, then validates the complete
# generated fleet so an incompatible or ignored action boundary cannot start.
talon validate --dir "$CONFIG_DIR/agents" >/dev/null

echo 'Applied the customer-support refund action boundary to the generated Talon fleet.'
