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

cat >"$WORK/fake-talon" <<'EOF'
#!/usr/bin/env bash
[[ "${1:-}" == --probe ]] || exit 2
echo 'resolved Talon CLI'
EOF
chmod +x "$WORK/fake-talon"
TALON_BIN="$WORK/fake-talon" \
  bash "$ROOT/scripts/with-talon.sh" talon --probe \
  | grep -Fq 'resolved Talon CLI' \
  || { echo 'Talon-aware wrapper did not expose the resolved runtime CLI as talon' >&2; exit 1; }

echo 'Talon runtime CLI resolver works without inheriting the preparation shell PATH'

cat >"$WORK/old-audit-talon" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == audit && "${2:-}" == export && "${3:-}" == --help ]]; then
  echo 'Output format: csv, json, or ndjson'
  exit 0
fi
if [[ "${1:-}" == audit && "${2:-}" == verify && "${3:-}" == --help ]]; then
  echo 'verify one evidence id'
  exit 0
fi
[[ "${1:-}" == --probe ]] && { echo 'old audit CLI selected'; exit 0; }
exit 2
EOF
cat >"$WORK/compatible-audit-talon" <<'EOF'
#!/usr/bin/env bash
if [[ "${1:-}" == audit && "${2:-}" == export && "${3:-}" == --help ]]; then
  echo '--session SESSION --format signed-json'
  exit 0
fi
if [[ "${1:-}" == audit && "${2:-}" == verify && "${3:-}" == --help ]]; then
  echo '--file FILE'
  exit 0
fi
[[ "${1:-}" == --probe ]] && { echo 'compatible audit CLI selected'; exit 0; }
exit 2
EOF
chmod +x "$WORK/old-audit-talon" "$WORK/compatible-audit-talon"
TALON_CLI_PROFILE=audit \
TALON_BIN="$WORK/old-audit-talon" \
TALON_AUDIT_BIN="$WORK/compatible-audit-talon" \
  bash "$ROOT/scripts/with-talon.sh" talon --probe \
  | grep -Fq 'compatible audit CLI selected' \
  || { echo 'audit profile did not reject the released CLI lacking signed session export' >&2; exit 1; }

echo 'Talon audit CLI profile requires session-filtered signed export and file verification'

mkdir -p "$WORK/fake-bin"
cat >"$WORK/fake-bin/talon" <<EOF
#!/usr/bin/env bash
if [[ "\${1:-}" == validate && "\${2:-}" == --file && -f "\${3:-}" && "\$#" -eq 3 ]]; then
  printf '%s\n' "\$*" >"$WORK/validate-args.txt"
  exit 0
fi
printf 'unsupported fake Talon invocation: %s\n' "\$*" >&2
exit 2
EOF
chmod +x "$WORK/fake-bin/talon"
printf 'agent: {}\n' >"$WORK/agent.talon.yaml"
PATH="$WORK/fake-bin:$PATH" \
  bash "$ROOT/scripts/validate-agent-policy.sh" "$WORK/agent.talon.yaml" >/dev/null
[[ "$(cat "$WORK/validate-args.txt")" == "validate --file $WORK/agent.talon.yaml" ]] \
  || { echo 'single-agent validation did not use the released Talon --file contract' >&2; exit 1; }
if grep -Fq -- 'talon validate --dir' "$ROOT/scripts/n8n-workflow.sh"; then
  echo 'n8n runner still depends on the newer Talon --dir flag' >&2
  exit 1
fi

echo 'n8n policy staging uses the released Talon single-file validation contract'
bash "$ROOT/scripts/validate-completion-contracts.sh"
