#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POLICY="$ROOT/config/agent-overlays/vendor-contract-review/agent.talon.yaml"

[[ -s "$POLICY" ]] || { echo "missing vendor-review policy: $POLICY" >&2; exit 1; }

# The full demo documents Talon v1.9.3+ as its released runtime floor. That CLI
# rejects the newer agent.use_case operating-record block as an unknown key for a
# gateway agent. Keep this overlay on the released schema until the demo raises
# its minimum Talon version and validates that migration explicitly.
if grep -Eq '^  use_case:' "$POLICY"; then
  echo 'vendor-review policy uses agent.use_case, which released Talon v1.9.3 rejects' >&2
  exit 1
fi

for required in \
  'name: vendor-contract-review' \
  'secret_name: vendor-contract-review-talon-key' \
  'allowed_providers: ["openai", "anthropic"]' \
  'default_action: deny' \
  'tier: confidential' \
  'allowed_providers: ["anthropic"]' \
  'input_scan: true' \
  'redact_input: true'; do
  grep -Fq -- "$required" "$POLICY" \
    || { echo "vendor-review policy lost required control: $required" >&2; exit 1; }
done

echo 'vendor-review overlay is compatible with the released Talon demo schema'
