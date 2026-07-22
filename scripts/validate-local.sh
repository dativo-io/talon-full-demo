#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for cmd in go node npm jq curl python3 git; do
  command -v "$cmd" >/dev/null || { echo "missing validation command: $cmd" >&2; exit 1; }
done

"$ROOT/scripts/test-integration-local.sh"

# Regression: a previous Copilot run may leave the working fixture in any state.
# Poison it deliberately and prove reset reconstructs the committed baseline.
printf 'poisoned by prior run\n' > "$ROOT/cases/billing-demo/src/invoice.mjs"
"$ROOT/scripts/reset-billing-fixture.sh"
grep -Fq 'return sum + Math.round(taxed * 100) / 100;' \
  "$ROOT/cases/billing-demo/src/invoice.mjs" \
  || { echo 'billing fixture was not restored from committed baseline' >&2; exit 1; }
(
  cd "$ROOT/cases/billing-demo"
  if npm test >/dev/null 2>&1; then
    echo 'billing fixture unexpectedly passed before the expected fix' >&2
    exit 1
  fi
  git apply --check expected-fix.patch
  npm run fix-demo
  npm test
  [[ "$(git diff --name-only)" == "src/invoice.mjs" ]] \
    || { echo 'deterministic fix changed unexpected files' >&2; exit 1; }
  grep -Fqx '    return sum + taxed;' src/invoice.mjs \
    || { echo 'deterministic fix did not apply the expected one-line correction' >&2; exit 1; }
  git diff --check
  git reset --hard -q HEAD
  [[ -z "$(git status --porcelain)" ]] || { echo 'billing fixture reset left changes' >&2; exit 1; }
)
rm -rf "$ROOT/cases/billing-demo/.git"

# Regression: the bounded real-Copilot driver must terminate a runaway process
# and report the stable timeout status expected by the shell wrapper.
python3 "$ROOT/scripts/run-with-timeout.py" 2 true
set +e
python3 "$ROOT/scripts/run-with-timeout.py" 1 \
  python3 -c 'import time; time.sleep(30)' >/dev/null 2>&1
timeout_rc=$?
set -e
[[ "$timeout_rc" -eq 124 ]] \
  || { echo "timeout runner returned $timeout_rc, expected 124" >&2; exit 1; }

# Regression: stable Copilot 1.0.73 can expose the complete programmatic surface
# through `copilot help` while abbreviated `copilot --help` and cosmetic flags
# differ from newer documentation. Functional compatibility must still pass.
copilot_test_dir="$(mktemp -d)"
cat > "$copilot_test_dir/copilot" <<'FAKE_COPILOT'
#!/usr/bin/env bash
case "${1:-}" in
  --version)
    echo 'GitHub Copilot CLI 1.0.73.'
    ;;
  help)
    cat <<'HELP'
--prompt
--no-ask-user
--additional-mcp-config
--disable-builtin-mcps
--allow-tool
--deny-tool
--no-custom-instructions
HELP
    ;;
  --help)
    echo 'abbreviated help without the complete option list'
    ;;
  *)
    exit 2
    ;;
esac
FAKE_COPILOT
chmod +x "$copilot_test_dir/copilot"
bash "$ROOT/scripts/check-copilot-cli.sh" "$copilot_test_dir/copilot" \
  | grep -Fq 'GitHub Copilot CLI 1.0.73.' \
  || { rm -rf "$copilot_test_dir"; echo 'Copilot functional capability probe rejected compatible 1.0.73 interface' >&2; exit 1; }
rm -rf "$copilot_test_dir"

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
