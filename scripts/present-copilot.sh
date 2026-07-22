#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
ENV_FILE="$ROOT/.env"
RUN_ENV="$STATE/demo-run.env"
MODE="${1:-buyer}"

usage() {
  cat <<'EOF'
Usage: bash scripts/present-copilot.sh [buyer|technical|all]

buyer      Show one concise, business-readable receipt from the latest real Copilot run.
technical  Show the Talon session, evidence timeline, MCP boundary, and signature verification.
all        Show the buyer receipt followed by the technical proof.

The command does not rerun Copilot. It exports and verifies the latest session recorded in
.state/demo-run.env, so both views are projections of the same Talon evidence.
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
[[ -f "$RUN_ENV" ]] || { echo 'ERROR: no demo run identity; run make real-copilot' >&2; exit 1; }

# shellcheck disable=SC1090
source "$ENV_FILE"
# shellcheck disable=SC1090
source "$RUN_ENV"

SESSION="${TALON_COPILOT_SESSION_ID:-}"
[[ -n "$SESSION" ]] || { echo 'ERROR: TALON_COPILOT_SESSION_ID is empty; rerun make real-copilot' >&2; exit 1; }

EVIDENCE_FILE="${TALON_PRESENT_EVIDENCE_FILE:-$STATE/$SESSION.signed.json}"
VERIFY_FILE="$STATE/$SESSION.verify.txt"

# Every presentation starts by recreating and cryptographically checking the receipt.
talon audit export \
  --format signed-json \
  --session "$SESSION" \
  --output "$EVIDENCE_FILE" >/dev/null

talon audit verify --file "$EVIDENCE_FILE" > "$VERIFY_FILE"
for expected in 'Invalid records: 0' 'Missing signature: 0' 'Could not parse: 0' 'Unsupported: 0'; do
  grep -Fq "$expected" "$VERIFY_FILE" || {
    echo "ERROR: evidence verification failed; missing '$expected'" >&2
    cat "$VERIFY_FILE" >&2
    exit 1
  }
done

# Prove the current nonce produced both allowed upstream receipts and no publish receipt.
"$ROOT/scripts/assert-release-blocked.sh" >/dev/null

TOTAL="$(jq '.records | length' "$EVIDENCE_FILE")"
VALID="$(awk -F': ' '/^Valid records:/ {print $2}' "$VERIFY_FILE")"
INVALID="$(awk -F': ' '/^Invalid records:/ {print $2}' "$VERIFY_FILE")"
AGENT="$(jq -r '[.records[].agent_id] | unique | if length == 1 then .[0] else join(", ") end' "$EVIDENCE_FILE")"
SOURCE="$(jq -r '[.records[].orchestration.client? | select(type == "string" and length > 0)] | unique | first // "github-copilot-cli-full-demo"' "$EVIDENCE_FILE")"
PROVENANCE="$(jq -r '[.records[].orchestration.provenance? | select(type == "string" and length > 0)] | unique | first // "client_asserted"' "$EVIDENCE_FILE")"
MODELS="$(jq -r '[.records[].execution.model_used? | select(type == "string" and length > 0)] | unique | join(", ")' "$EVIDENCE_FILE")"
TOOLS="$(jq -r '[.records[] | select(.invocation_type == "proxy_tool_call") | .execution.tools_called[]?] | unique | sort | join(", ")' "$EVIDENCE_FILE")"
COST="$(jq -r '[.records[].execution.cost // 0] | add // 0' "$EVIDENCE_FILE")"
COST_FMT="$(printf '%.6f' "$COST")"
PII="$(jq -r '[.records[].classification.pii_detected[]?] | unique | sort | join(", ")' "$EVIDENCE_FILE")"
REDACTED_RECORDS="$(jq '[.records[] | select(.classification.pii_redacted == true)] | length' "$EVIDENCE_FILE")"
GATEWAY_RECORDS="$(jq '[.records[] | select(.invocation_type == "gateway")] | length' "$EVIDENCE_FILE")"
MCP_RECORDS="$(jq '[.records[] | select(.invocation_type == "proxy_tool_call")] | length' "$EVIDENCE_FILE")"
ALLOWED="$(jq '[.records[] | select(.policy_decision.allowed == true)] | length' "$EVIDENCE_FILE")"
DENIED="$(jq '[.records[] | select(.policy_decision.allowed == false)] | length' "$EVIDENCE_FILE")"

[[ "$TOTAL" -ge 1 ]] || { echo "ERROR: no evidence records for $SESSION" >&2; exit 1; }
[[ "$VALID" == "$TOTAL" && "$INVALID" == "0" ]] || { echo 'ERROR: not every record verified' >&2; exit 1; }
jq -e --arg s "$SESSION" 'all(.records[]; .session_id == $s)' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: exported records do not all belong to the current session' >&2; exit 1; }
jq -e '([.records[] | select(.invocation_type == "proxy_tool_call") | .execution.tools_called[]?] | sort) == ["release_prepare", "release_status"]' "$EVIDENCE_FILE" >/dev/null \
  || { echo 'ERROR: MCP evidence does not contain exactly release_status and release_prepare' >&2; exit 1; }

show_buyer() {
  local data_line
  if [[ -n "$PII" && "$REDACTED_RECORDS" -gt 0 ]]; then
    data_line="$PII detected; input redaction recorded"
  elif [[ -n "$PII" ]]; then
    data_line="$PII detected; no input-redaction fact in this session"
  else
    data_line="No classified personal data detected"
  fi

  cat <<EOF

TALON VERIFIED AI USE CASE
────────────────────────────────────────────────────────────
Use case          GitHub Copilot CLI
Operational ID    $AGENT
Business outcome  Release status checked; release prepared
Action boundary   release_publish did not reach the upstream
Data handling     $data_line
Model path        ${MODELS:-not recorded} through Talon
Session cost      \$$COST_FMT
Evidence          $VALID valid / $INVALID invalid records
Result            VERIFIED
────────────────────────────────────────────────────────────
What this means: one company AI use case has an identity, controlled
intercepted actions, attributable spend, and a verifiable session record.
EOF
}

show_technical() {
  cat <<EOF

TALON TECHNICAL PROOF
────────────────────────────────────────────────────────────
Session:     $SESSION
Agent:       $AGENT
Client:      $SOURCE
Provenance:  $PROVENANCE
Surfaces:    $GATEWAY_RECORDS gateway records + $MCP_RECORDS MCP records
Decisions:   $ALLOWED allowed / $DENIED denied
Evidence:    $EVIDENCE_FILE
EOF

  echo
  talon audit list --session "$SESSION"

  cat <<'EOF'

Evidence timeline (oldest first)
TIME                              SURFACE          OPERATION                 DECISION  COST
EOF
  jq -r '
    .records
    | sort_by(.timestamp)
    | .[]
    | [
        .timestamp,
        .invocation_type,
        (if .invocation_type == "proxy_tool_call"
         then (.execution.tools_called // [] | join(","))
         else (.execution.model_used // "-") end),
        (if .policy_decision.allowed then "allow" else "deny" end),
        ((.execution.cost // 0) | tostring)
      ]
    | @tsv
  ' "$EVIDENCE_FILE"

  cat <<EOF

MCP boundary
  Allowed and executed: $TOOLS
  Did not reach upstream: release_publish

Cryptographic verification
EOF
  sed -n '/^Total records:/,/^Unsupported:/p' "$VERIFY_FILE"

  cat <<EOF

Inspect individual MCP receipts with:
EOF
  jq -r '.records[] | select(.invocation_type == "proxy_tool_call") | "  talon audit show " + .id' "$EVIDENCE_FILE"

  cat <<'EOF'

Scope boundary
  Talon proves model traffic and MCP calls routed through Talon.
  Local shell commands, file edits, browser actions, and direct APIs that bypass
  Talon are outside this proof. Client/session provenance is attribution, not
  independent process attestation.
EOF
}

case "$MODE" in
  buyer) show_buyer ;;
  technical) show_technical ;;
  all) show_buyer; show_technical ;;
esac
