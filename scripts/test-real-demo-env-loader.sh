#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE="$ROOT/scripts/real-demo.sh"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/talon-env-loader.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/root/.state"
cat >"$WORK/root/.env" <<'EOF'
export TALON_GATEWAY=http://127.0.0.1:8080
export OPENAI_API_KEY=
export ANTHROPIC_API_KEY=
EOF

awk '
  /^load_env\(\) \{/ { capture=1 }
  capture { print }
  capture && /^}$/ { exit }
' "$SOURCE" >"$WORK/load-env-function.sh"

grep -Fq 'load_env() {' "$WORK/load-env-function.sh" \
  || { echo 'could not extract load_env from real-demo.sh' >&2; exit 1; }

(
  set -euo pipefail
  ROOT="$WORK/root"
  STATE="$ROOT/.state"
  ENV_FILE="$ROOT/.env"
  # shellcheck disable=SC1090
  source "$WORK/load-env-function.sh"

  unset OPENAI_API_KEY ANTHROPIC_API_KEY
  load_env
  [[ -z "${OPENAI_API_KEY:-}" ]] || { echo 'fresh-shell load unexpectedly invented an OpenAI key' >&2; exit 1; }
  [[ -z "${ANTHROPIC_API_KEY:-}" ]] || { echo 'fresh-shell load unexpectedly invented an Anthropic key' >&2; exit 1; }

  export OPENAI_API_KEY=external-openai
  export ANTHROPIC_API_KEY=external-anthropic
  load_env
  [[ "$OPENAI_API_KEY" == external-openai ]] || { echo 'OpenAI override was not preserved' >&2; exit 1; }
  [[ "$ANTHROPIC_API_KEY" == external-anthropic ]] || { echo 'Anthropic override was not preserved' >&2; exit 1; }
)

echo 'real-demo environment loader handles optional provider keys in a fresh shell'
bash "$ROOT/scripts/validate-completion-contracts.sh"
