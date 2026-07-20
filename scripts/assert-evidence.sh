#!/usr/bin/env bash
set -euo pipefail

# Asserts the signed Talon evidence for one session: offline signature
# verification plus agent attribution, and optionally a minimum number of
# denials whose machine reason starts with a given prefix. A denied request
# must never carry cost. This scripts the runbook's manual evidence
# inspection and is used by scripts/test-live-talon.sh.
#
# Usage:
#   assert-evidence.sh --session ID --agent NAME [--min-denials N] [--deny-reason PREFIX]
#
# Environment: TALON_BIN (default: `talon` on PATH); the TALON_DATA_DIR and
# signing-key environment of the store under test must already be exported.

TALON_BIN="${TALON_BIN:-talon}"
SESSION=""
AGENT=""
MIN_DENIALS=0
DENY_REASON=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) SESSION="$2"; shift 2 ;;
    --agent) AGENT="$2"; shift 2 ;;
    --min-denials) MIN_DENIALS="$2"; shift 2 ;;
    --deny-reason) DENY_REASON="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$SESSION" && -n "$AGENT" ]] || {
  echo 'usage: assert-evidence.sh --session ID --agent NAME [--min-denials N] [--deny-reason PREFIX]' >&2
  exit 2
}

EXPORT_FILE="$(mktemp)"
VERIFY_OUT="$(mktemp)"
trap 'rm -f "$EXPORT_FILE" "$VERIFY_OUT"' EXIT

"$TALON_BIN" audit export --format signed-json --session "$SESSION" --output "$EXPORT_FILE" >/dev/null
"$TALON_BIN" audit verify --file "$EXPORT_FILE" > "$VERIFY_OUT"

for line in 'Invalid records: 0' 'Missing signature: 0' 'Could not parse: 0'; do
  grep -q "$line" "$VERIFY_OUT" || {
    echo "signed evidence verification failed for session $SESSION (missing '$line'):" >&2
    cat "$VERIFY_OUT" >&2
    exit 1
  }
done

TOTAL="$(jq '.records | length' "$EXPORT_FILE")"
[[ "$TOTAL" -ge 1 ]] || { echo "no evidence records for session $SESSION" >&2; exit 1; }

jq -e --arg s "$SESSION" 'all(.records[]; .session_id == $s)' "$EXPORT_FILE" >/dev/null \
  || { echo "export contains records outside session $SESSION" >&2; exit 1; }
jq -e --arg a "$AGENT" 'all(.records[]; .agent_id == $a)' "$EXPORT_FILE" >/dev/null \
  || { echo "evidence not attributed to agent $AGENT" >&2; exit 1; }

if [[ "$MIN_DENIALS" -gt 0 ]]; then
  DENIALS="$(jq --arg p "$DENY_REASON" \
    '[.records[] | select(.policy_decision.allowed == false)
      | select(($p == "") or (any(.policy_decision.reasons[]?; startswith($p))))] | length' \
    "$EXPORT_FILE")"
  [[ "$DENIALS" -ge "$MIN_DENIALS" ]] || {
    echo "expected >= $MIN_DENIALS denial(s) with reason prefix '$DENY_REASON', found $DENIALS" >&2
    exit 1
  }
  jq -e '[.records[] | select(.policy_decision.allowed == false) | (.execution.cost // 0)] | all(. == 0)' \
    "$EXPORT_FILE" >/dev/null \
    || { echo 'a denied request carries non-zero cost in evidence' >&2; exit 1; }
fi

echo "evidence OK: session=$SESSION agent=$AGENT records=$TOTAL (signatures valid)"
