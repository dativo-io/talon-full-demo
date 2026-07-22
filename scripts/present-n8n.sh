#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
OUT="$STATE/n8n-output"
ENV_FILE="$ROOT/.env"
RUN_ENV="$STATE/demo-run.env"
LATEST_ENV="$STATE/latest-n8n-session.env"
MODE="${1:-buyer}"

usage() {
  cat <<'EOF'
Usage: TALON_PRESENT_N8N_SESSION_ID=<session> bash scripts/present-n8n.sh [buyer|technical|all]

buyer      Show a concise workflow outcome derived from output artifacts and Talon evidence.
technical  Show the session timeline, budget denial, partial files, and signatures.
all        Show buyer view followed by technical proof.

This command does not run n8n. It fails closed unless a real imported workflow already
produced section files, status.json with session_budget_exceeded, and matching Talon evidence.
EOF
}

case "$MODE" in
  buyer|technical|all) ;;
  -h|--help|help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac

for cmd in talon jq; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: missing command: $cmd" >&2; exit 1; }
done
[[ -f "$ENV_FILE" ]] || { echo 'ERROR: missing .env; run make real-prepare' >&2; exit 1; }
# shellcheck disable=SC1090
source "$ENV_FILE"

SESSION="${TALON_PRESENT_N8N_SESSION_ID:-}"
if [[ -z "$SESSION" && -f "$LATEST_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$LATEST_ENV"
  SESSION="${TALON_N8N_PRESENTED_SESSION_ID:-}"
fi
if [[ -z "$SESSION" && -f "$RUN_ENV" ]]; then
  # shellcheck disable=SC1090
  source "$RUN_ENV"
  SESSION="${TALON_N8N_SESSION_ID:-}"
fi
[[ -n "$SESSION" ]] || { echo 'ERROR: no n8n session; set TALON_PRESENT_N8N_SESSION_ID to the session used by the imported workflow' >&2; exit 1; }

[[ -d "$OUT" ]] || { echo "ERROR: missing n8n output directory: $OUT" >&2; exit 1; }
STATUS_FILE="$OUT/status.json"
[[ -s "$STATUS_FILE" ]] || { echo "ERROR: missing $STATUS_FILE; the budget-denial branch has not been proven" >&2; exit 1; }
grep -Fq 'session_budget_exceeded' "$STATUS_FILE" \
  || { echo 'ERROR: status.json does not contain session_budget_exceeded' >&2; exit 1; }

mapfile -d '' SUMMARY_FILES < <(find "$OUT" -maxdepth 1 -type f -name '*.summary.md' -print0 | sort -z)
(( ${#SUMMARY_FILES[@]} > 0 )) || { echo 'ERROR: no completed n8n section files; partial-output preservation is unproven' >&2; exit 1; }
REPORT_FILE="$OUT/quarterly-summary.partial.$SESSION.md"
{
  printf '# Quarterly compliance summary\n\n_Synthetic demonstration data._\n\n'
  for file in "${SUMMARY_FILES[@]}"; do
    cat "$file"
    printf '\n'
  done
} >"$REPORT_FILE"

EVIDENCE_FILE="${TALON_PRESENT_EVIDENCE_FILE:-$STATE/$SESSION.signed.json}"
VERIFY_FILE="$STATE/$SESSION.verify.txt"
talon audit export --format signed-json --session "$SESSION" --output "$EVIDENCE_FILE" >/dev/null
talon audit verify --file "$EVIDENCE_FILE" >"$VERIFY_FILE"
for expected in 'Invalid records: 0' 'Missing signature: 0' 'Could not parse: 0' 'Unsupported: 0'; do
  grep -Fq "$expected" "$VERIFY_FILE" || {
    echo "ERROR: evidence verification failed; missing '$expected'" >&2
    cat "$VERIFY_FILE" >&2
    exit 1
  }
done

TOTAL="$(jq '.records | length' "$EVIDENCE_FILE")"
VALID="$(awk -F': ' '/^Valid records:/ {print $2}' "$VERIFY_FILE")"
INVALID="$(awk -F': ' '/^Invalid records:/ {print $2}' "$VERIFY_FILE")"
AGENT="$(jq -r '[.records[].agent_id] | unique | if length == 1 then .[0] else join(", ") end' "$EVIDENCE_FILE")"
MODELS="$(jq -r '[.records[].execution.model_used? | select(type == "string" and length > 0)] | unique | join(", ")' "$EVIDENCE_FILE")"
PROVIDERS="$(jq -r '[.records[].execution.provider? | select(type == "string" and length > 0)] | unique | join(", ")' "$EVIDENCE_FILE")"
ALLOWED="$(jq '[.records[] | select(.policy_decision.allowed == true)] | length' "$EVIDENCE_FILE")"
DENIED="$(jq '[.records[] | select(.policy_decision.allowed == false)] | length' "$EVIDENCE_FILE")"
COST="$(jq -r '[.records[].execution.cost // 0] | add // 0' "$EVIDENCE_FILE")"
COST_FMT="$(printf '%.6f' "$COST")"
DENIED_COST="$(jq -r '[.records[] | select(.policy_decision.allowed == false) | (.execution.cost // 0)] | add // 0' "$EVIDENCE_FILE")"
DENIED_COST_FMT="$(printf '%.6f' "$DENIED_COST")"
SECTIONS="${#SUMMARY_FILES[@]}"

[[ "$TOTAL" -ge 2 ]] || { echo "ERROR: expected multiple n8n records for $SESSION" >&2; exit 1; }
[[ "$VALID" == "$TOTAL" && "$INVALID" == "0" ]] || { echo 'ERROR: not every n8n record verified' >&2; exit 1; }
[[ "$AGENT" == "document-summary" ]] || { echo "ERROR: expected document-summary evidence, found $AGENT" >&2; exit 1; }
[[ "$ALLOWED" -ge 1 && "$DENIED" -ge 1 ]] || { echo "ERROR: expected allowed work followed by a denial; found $ALLOWED allowed / $DENIED denied" >&2; exit 1; }
jq -e --arg s "$SESSION" 'all(.records[]; .session_id == $s)' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: exported records do not all belong to the n8n session' >&2; exit 1; }
jq -e 'any(.records[]; .policy_decision.allowed == false
    and any(.policy_decision.reasons[]?; startswith("session_budget_exceeded")))' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: Talon evidence does not contain a session_budget_exceeded denial' >&2; exit 1; }
jq -e '[.records[] | select(.policy_decision.allowed == false) | (.execution.cost // 0)] | all(. == 0)' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: a denied n8n request carries non-zero cost' >&2; exit 1; }

umask 077
cat >"$LATEST_ENV" <<EOF
export TALON_N8N_PRESENTED_SESSION_ID=$SESSION
export TALON_N8N_EVIDENCE_FILE=$EVIDENCE_FILE
export TALON_N8N_STATUS_FILE=$STATUS_FILE
export TALON_N8N_REPORT_FILE=$REPORT_FILE
EOF
chmod 0600 "$LATEST_ENV"

show_buyer() {
  cat <<EOF

TALON VERIFIED AI USE CASE
────────────────────────────────────────────────────────────
Use case          n8n quarterly report workflow
Operational ID    $AGENT
Business outcome  $SECTIONS section(s) completed; partial report preserved
Cost boundary     Next request stopped on the session budget
Denied request    \$$DENIED_COST_FMT provider cost
Model path        ${MODELS:-not recorded} through Talon
Session spend     \$$COST_FMT
Evidence          $VALID valid / $INVALID invalid records
Result            VERIFIED PARTIAL OUTPUT
────────────────────────────────────────────────────────────
What this means: useful work survives a later budget stop, while the denied
request adds no provider cost and remains visible in the same session record.
EOF
}

show_technical() {
  cat <<EOF

TALON TECHNICAL PROOF — N8N WORKFLOW
────────────────────────────────────────────────────────────
Session:       $SESSION
Agent:         $AGENT
Providers:     ${PROVIDERS:-not recorded}
Models:        ${MODELS:-not recorded}
Decisions:     $ALLOWED allowed / $DENIED denied
Sections:      $SECTIONS completed
Session cost:  \$$COST_FMT
Denied cost:   \$$DENIED_COST_FMT
Evidence:      $EVIDENCE_FILE
Status:        $STATUS_FILE
Partial report:$REPORT_FILE
EOF

  echo
  talon audit list --session "$SESSION"

  cat <<'EOF'

Evidence timeline (oldest first)
TIME                              MODEL                     DECISION  REASON                         COST
EOF
  jq -r '
    .records
    | sort_by(.timestamp)
    | .[]
    | [
        .timestamp,
        (.execution.model_used // "-"),
        (if .policy_decision.allowed then "allow" else "deny" end),
        (.policy_decision.reasons[0] // "-"),
        ((.execution.cost // 0) | tostring)
      ]
    | @tsv
  ' "$EVIDENCE_FILE"

  cat <<EOF

Workflow artifacts
EOF
  for file in "${SUMMARY_FILES[@]}"; do
    printf '  completed: %s\n' "$file"
  done
  printf '  denial:    %s\n' "$STATUS_FILE"
  printf '  assembled: %s\n' "$REPORT_FILE"

  cat <<'EOF'

Cryptographic verification
EOF
  sed -n '/^Total records:/,/^Unsupported:/p' "$VERIFY_FILE"

  cat <<'EOF'

Inspect records with:
EOF
  jq -r '.records[] | "  talon audit show " + .id' "$EVIDENCE_FILE"

  cat <<'EOF'

Scope boundary
  The session cap is a soft cap: completed requests may consume budget before
  the next request is denied. This proof requires a real imported n8n workflow;
  the repository's workflow specification alone cannot satisfy it.
EOF
}

case "$MODE" in
  buyer) show_buyer ;;
  technical) show_technical ;;
  all) show_buyer; show_technical ;;
esac
