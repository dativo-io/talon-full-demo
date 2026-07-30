#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env"
CONFIG_DIR="$ROOT/config/generated"
SOURCE_POLICY="$ROOT/config/agent-overlays/vendor-contract-review/agent.talon.yaml"
TARGET_DIR="$CONFIG_DIR/agents/vendor-contract-review"
TARGET_POLICY="$TARGET_DIR/agent.talon.yaml"

command -v talon >/dev/null 2>&1 || { echo 'missing command: talon' >&2; exit 1; }
[[ -f "$ENV_FILE" ]] || { echo 'missing .env; run make real-prepare' >&2; exit 1; }
[[ -f "$CONFIG_DIR/talon.config.yaml" ]] || { echo 'missing generated Talon config; run make real-prepare' >&2; exit 1; }
[[ -s "$SOURCE_POLICY" ]] || { echo "missing vendor-review policy overlay: $SOURCE_POLICY" >&2; exit 1; }

external_openai="${OPENAI_API_KEY:-}"
external_anthropic="${ANTHROPIC_API_KEY:-}"
# shellcheck disable=SC1090
source "$ENV_FILE"
[[ -n "$external_openai" ]] && OPENAI_API_KEY="$external_openai"
[[ -n "$external_anthropic" ]] && ANTHROPIC_API_KEY="$external_anthropic"
[[ -n "${OPENAI_API_KEY:-}" ]] || { echo 'OPENAI_API_KEY is required by the full demo prepare path' >&2; exit 1; }

# Existing demo hosts may have an .env created before this use case existed. Add
# only the new local identity values; never rewrite existing keys or provider data.
if [[ -z "${TALON_VENDOR_CONTRACT_REVIEW_KEY:-}" ]]; then
  TALON_VENDOR_CONTRACT_REVIEW_KEY="$(openssl rand -hex 24)"
  printf 'export TALON_VENDOR_CONTRACT_REVIEW_KEY=%q\n' "$TALON_VENDOR_CONTRACT_REVIEW_KEY" >>"$ENV_FILE"
fi
if [[ -z "${TALON_N8N_VENDOR_REVIEW_SESSION_ID:-}" ]]; then
  TALON_N8N_VENDOR_REVIEW_SESSION_ID=n8n-vendor-review-demo
  printf 'export TALON_N8N_VENDOR_REVIEW_SESSION_ID=%q\n' "$TALON_N8N_VENDOR_REVIEW_SESSION_ID" >>"$ENV_FILE"
fi
chmod 0600 "$ENV_FILE"

install -d -m 0700 "$TARGET_DIR"
cp "$SOURCE_POLICY" "$TARGET_POLICY"
chmod 0600 "$TARGET_POLICY"

# Re-set the shared provider secrets with the complete ACL so adding the overlay
# cannot remove access already granted to the canonical product-demo agents.
talon secrets set openai-api-key "$OPENAI_API_KEY" \
  --tenant acme --agent customer-support --agent coding-assistant --agent vendor-contract-review >/dev/null

anthropic_value="${ANTHROPIC_API_KEY:-not-configured-anthropic-demo-key}"
talon secrets set anthropic-api-key "$anthropic_value" \
  --tenant acme --agent document-summary --agent vendor-contract-review >/dev/null

talon secrets set vendor-contract-review-talon-key "$TALON_VENDOR_CONTRACT_REVIEW_KEY" \
  --tenant acme --agent vendor-contract-review >/dev/null

# Validate the full generated fleet after the overlay and key binding are present.
talon validate --dir "$CONFIG_DIR/agents" >/dev/null
TALON_GATEWAY_CONFIG="$TALON_CONFIG" talon doctor >/dev/null

echo 'Added vendor-contract-review to the generated Talon fleet and seeded its vault bindings.'
