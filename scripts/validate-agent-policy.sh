#!/usr/bin/env bash
set -euo pipefail

POLICY_FILE="${1:-}"
[[ -n "$POLICY_FILE" ]] || {
  echo 'Usage: validate-agent-policy.sh <agent.talon.yaml>' >&2
  exit 2
}
command -v talon >/dev/null 2>&1 || {
  echo 'ERROR: missing command: talon' >&2
  exit 1
}
[[ -f "$POLICY_FILE" ]] || {
  echo "ERROR: policy file does not exist: $POLICY_FILE" >&2
  exit 1
}

# Validate only the policy the n8n demo stages. --file is supported by the
# released Talon CLI used on the demo host; directory validation was added later
# and cannot be assumed for an installed v1.9.x binary.
talon validate --file "$POLICY_FILE"
