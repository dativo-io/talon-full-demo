#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -f "$ROOT/.env" ]] || { echo "missing $ROOT/.env; run make env" >&2; exit 1; }
# shellcheck disable=SC1091
source "$ROOT/.env"
OUT="${1:-$ROOT/.state/copilot-mcp.json}"
mkdir -p "$(dirname "$OUT")"

python3 - "$ROOT/integrations/copilot/copilot-mcp.example.json" "$OUT" <<'PYMCP'
from pathlib import Path
import json
import os
import sys

source = Path(sys.argv[1])
out = Path(sys.argv[2])
text = source.read_text()
for key in ('TALON_CODING_ASSISTANT_KEY', 'TALON_ADMIN_KEY', 'TALON_COPILOT_SESSION_ID'):
    value = os.environ.get(key)
    if not value:
        raise SystemExit(f'{key} is required')
    text = text.replace('${' + key + '}', value)
parsed = json.loads(text)
out.write_text(json.dumps(parsed, indent=2) + '\n')
out.chmod(0o600)
print(out)
PYMCP
