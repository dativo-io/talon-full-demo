#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Contract regression: the OpenShell case is OPTIONAL and absent dependencies
# must fail rather than producing a fake successful demo.
bash -n scripts/real-openshell.sh scripts/present-openshell.sh
for target in openshell-validate real-openshell demo-openshell-buyer \
  demo-openshell-tech present-openshell-all status-openshell-approval \
  approve-openshell reject-openshell; do
  make --no-print-directory -n "$target" >/dev/null
done

msg="$(TALON_OPENSHELL_ENABLED=0 bash scripts/real-openshell.sh status 2>&1)"
grep -Fq 'disabled' <<<"$msg" || { echo 'disabled OpenShell status did not declare absence' >&2; exit 1; }
if TALON_OPENSHELL_ENABLED=0 bash scripts/real-openshell.sh run >/tmp/talon-openshell-negative.log 2>&1; then
  echo 'disabled OpenShell case executed unexpectedly' >&2; exit 1
fi
grep -Fq 'opt-in' /tmp/talon-openshell-negative.log \
  || { echo 'disabled OpenShell run did not report the expected gate' >&2; exit 1; }
rm -f /tmp/talon-openshell-negative.log

# Static wiring safety: the public Full Demo adapter must NEVER call the
# separate source-build live smoke, fabricate success or start a second Talon.
if grep -Eq 'openshell-live\.sh|talon serve|ALL PASS openshell' scripts/real-openshell.sh; then
  echo 'OpenShell adapter bypasses shared-stack/real-runner boundary' >&2; exit 1
fi
grep -Fq 'audit verify --operation' scripts/present-openshell.sh \
  || { echo 'presenter is not verifying the canonical refund lifecycle' >&2; exit 1; }
grep -Fq 'audit export --format signed-json --session' scripts/present-openshell.sh \
  || { echo 'presenter is not exporting the fresh signed session' >&2; exit 1; }
echo 'OpenShell Full Demo adapter contract: PASS (does not claim live readiness)'
