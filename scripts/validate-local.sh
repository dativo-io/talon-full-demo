#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for cmd in go node npm jq curl python3 git; do
  command -v "$cmd" >/dev/null || { echo "missing validation command: $cmd" >&2; exit 1; }
done

"$ROOT/scripts/test-integration-local.sh"

"$ROOT/scripts/reset-billing-fixture.sh"
(
  cd "$ROOT/cases/billing-demo"
  if npm test >/dev/null 2>&1; then
    echo 'billing fixture unexpectedly passed before the expected fix' >&2
    exit 1
  fi
  git apply --check expected-fix.patch
  git apply expected-fix.patch
  npm test
  git reset --hard -q HEAD
  [[ -z "$(git status --porcelain)" ]] || { echo 'billing fixture reset left changes' >&2; exit 1; }
)
rm -rf "$ROOT/cases/billing-demo/.git"

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  N8N_ENCRYPTION_KEY=local-validation TALON_N8N_SESSION_ID=n8n-quarterly-demo \
    docker compose -f "$ROOT/integrations/n8n/compose.yaml" config --quiet
else
  python3 - "$ROOT/integrations/n8n/compose.yaml" <<'PYCOMPOSE'
from pathlib import Path
import sys

text = Path(sys.argv[1]).read_text()
required = [
    'docker.n8n.io/n8nio/n8n:2.30.4',
    '127.0.0.1:5678:5678',
    'N8N_ENCRYPTION_KEY: ${N8N_ENCRYPTION_KEY:?set N8N_ENCRYPTION_KEY}',
    '../../cases/quarterly-report:/demo/input:ro',
]
missing = [item for item in required if item not in text]
if missing:
    raise SystemExit(f'n8n static contract missing: {missing}')
PYCOMPOSE
fi

echo 'ALL LOCALLY EXECUTABLE VALIDATIONS PASSED'
