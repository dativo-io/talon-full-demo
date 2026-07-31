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
SINCE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session) SESSION="$2"; shift 2 ;;
    --agent) AGENT="$2"; shift 2 ;;
    --min-denials) MIN_DENIALS="$2"; shift 2 ;;
    --deny-reason) DENY_REASON="$2"; shift 2 ;;
    # --since <rfc3339>: only records at/after this instant count, so a stale
    # record from an earlier run under the same session cannot satisfy the
    # assertion. Defaults to $TALON_RUN_START_RFC3339 (set in demo-run.env).
    --since) SINCE="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ -n "$SESSION" && -n "$AGENT" ]] || {
  echo 'usage: assert-evidence.sh --session ID --agent NAME [--min-denials N] [--deny-reason PREFIX] [--since RFC3339]' >&2
  exit 2
}
[[ -n "$SINCE" ]] || SINCE="${TALON_RUN_START_RFC3339:-}"

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

# When --since is set, restrict the working set to the current run's records.
# Talon timestamps may carry fractional seconds while a shell-captured run start
# may not. Raw string comparison is wrong in that case because '.' sorts before
# 'Z' (`...25.7Z` would appear older than `...25Z`). Normalize UTC timestamps to
# a fixed nine-digit fractional form before comparing, preserving lexical RFC3339
# ordering without discarding records created in the run's boundary second.
if [[ -n "$SINCE" ]]; then
  jq --arg t "$SINCE" '
    def fixed_rfc3339:
      if test("\\.[0-9]+Z$") then
        capture("^(?<base>.*\\.)(?<fraction>[0-9]+)Z$") as $m
        | $m.base + (($m.fraction + "000000000")[0:9]) + "Z"
      elif test("Z$") then
        sub("Z$"; ".000000000Z")
      else
        .
      end;
    ($t | fixed_rfc3339) as $start
    | {records: [.records[] | select((.timestamp | fixed_rfc3339) >= $start)]}
  ' "$EXPORT_FILE" > "$EXPORT_FILE.win" \
    && mv "$EXPORT_FILE.win" "$EXPORT_FILE"
fi

TOTAL="$(jq '.records | length' "$EXPORT_FILE")"
if [[ -n "$SINCE" ]]; then
  [[ "$TOTAL" -ge 1 ]] || { echo "no evidence records for session $SESSION since $SINCE (current run produced none — a stale record cannot satisfy this)" >&2; exit 1; }
else
  [[ "$TOTAL" -ge 1 ]] || { echo "no evidence records for session $SESSION" >&2; exit 1; }
fi

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
