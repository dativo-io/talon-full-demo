#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="$ROOT/config/generated"
SOURCE_POLICY="$ROOT/config/agent-overlays/customer-support/agent.talon.yaml"
TARGET_DIR="$CONFIG_DIR/agents/customer-support"
TARGET_POLICY="$TARGET_DIR/agent.talon.yaml"

command -v talon >/dev/null 2>&1 || { echo 'missing command: talon' >&2; exit 1; }
[[ -f "$CONFIG_DIR/talon.config.yaml" ]] || { echo 'missing generated Talon config; run make real-prepare' >&2; exit 1; }
[[ -s "$SOURCE_POLICY" ]] || { echo "missing customer-support overlay: $SOURCE_POLICY" >&2; exit 1; }

install -d -m 0700 "$TARGET_DIR"
cp "$SOURCE_POLICY" "$TARGET_POLICY"
chmod 0600 "$TARGET_POLICY"

# The base prepare path already seeded customer-support-talon-key and both
# provider secrets. This step changes policy only, then validates the complete
# generated fleet so an incompatible or ignored action boundary cannot start.
talon validate --dir "$CONFIG_DIR/agents" >/dev/null

echo 'Applied the customer-support refund action boundary to the generated Talon fleet.'
