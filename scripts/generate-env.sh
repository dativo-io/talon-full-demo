#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$ROOT/.env}"
[[ ! -e "$OUT" ]] || { echo "$OUT already exists; refusing to overwrite" >&2; exit 1; }

python3 - "$ROOT" "$OUT" <<'PYENV'
from pathlib import Path
import secrets
import shlex
import sys

root = Path(sys.argv[1])
out = Path(sys.argv[2])
values = {
    "TALON_GATEWAY": "http://127.0.0.1:8080",
    "TALON_MCP_GATEWAY": "http://127.0.0.1:8081",
    "TALON_CONFIG": str(root / "config/generated/talon.config.yaml"),
    "TALON_DATA_DIR": str(root / ".state/talon"),
    "TALON_SECRETS_KEY": secrets.token_hex(32),
    "TALON_SIGNING_KEY": secrets.token_hex(32),
    "TALON_ADMIN_KEY": secrets.token_hex(24),
    "OPENAI_API_KEY": "",
    "ANTHROPIC_API_KEY": "",
    "TALON_CUSTOMER_SUPPORT_KEY": secrets.token_hex(24),
    "TALON_CODING_ASSISTANT_KEY": secrets.token_hex(24),
    "TALON_DOCUMENT_SUMMARY_KEY": secrets.token_hex(24),
    "TALON_VENDOR_CONTRACT_REVIEW_KEY": secrets.token_hex(24),
    "TALON_CUSTOMER_SUPPORT_PROVIDER": "local-llama",
    "TALON_CUSTOMER_SUPPORT_MODEL": "llama3.2:1b",
    "TALON_COPILOT_SESSION_ID": "copilot-billing-demo",
    "TALON_N8N_SESSION_ID": "n8n-quarterly-demo",
    "TALON_N8N_VENDOR_REVIEW_SESSION_ID": "n8n-vendor-review-demo",
    "ZENDESK_ADAPTER_TOKEN": secrets.token_hex(32),
    "ZENDESK_ADAPTER_DOMAIN": "",
    "ZENDESK_ADAPTER_BIND": "127.0.0.1:8443",
    "COPILOT_SHIM_BIND": "127.0.0.1:8079",
    "RELEASE_MCP_BIND": "127.0.0.1:8090",
    "RELEASE_MCP_RECEIPTS": str(root / ".state/release-mcp-receipts.jsonl"),
    "N8N_ENCRYPTION_KEY": secrets.token_hex(32),
}
out.write_text("\n".join(f"export {key}={shlex.quote(value)}" for key, value in values.items()) + "\n")
out.chmod(0o600)
print(out)
PYENV
