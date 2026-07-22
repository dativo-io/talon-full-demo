#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.state"
ENV_FILE="$ROOT/.env"
SESSION="${ZENDESK_INSTALLED_SESSION_ID:-}"
TICKET="${ZENDESK_INSTALLED_TICKET_ID:-}"

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }
confirm_yes() { [[ "${!1:-}" == yes ]] || die "$1=yes is required after observing that step in the installed Zendesk app"; }

for cmd in talon jq sha256sum date; do need "$cmd"; done
[[ -f "$ENV_FILE" ]] || die 'missing .env; run make real-prepare'
# shellcheck disable=SC1090
source "$ENV_FILE"
[[ -n "$SESSION" ]] || die 'set ZENDESK_INSTALLED_SESSION_ID to the session displayed by the installed app'
[[ -n "$TICKET" ]] || die 'set ZENDESK_INSTALLED_TICKET_ID to the synthetic Zendesk ticket id'
[[ "$SESSION" == "zendesk-ticket-$TICKET-"* ]] \
  || die 'installed session id does not match the supplied synthetic ticket id'

confirm_yes ZENDESK_PRIVATE_APP_INSTALLED
confirm_yes ZENDESK_SECURE_SETTING_CONFIRMED
confirm_yes ZENDESK_NEWEST_REQUESTER_COMMENT_CONFIRMED
confirm_yes ZENDESK_DRAFT_INSERTED_CONFIRMED

install -d -m 0700 "$STATE/zendesk-installed"
evidence="$STATE/zendesk-installed/$SESSION.signed.json"
verify="$STATE/zendesk-installed/$SESSION.verify.txt"
talon audit export --format signed-json --session "$SESSION" --output "$evidence" >/dev/null
talon audit verify --file "$evidence" >"$verify"
for expected in 'Invalid records: 0' 'Missing signature: 0' 'Could not parse: 0' 'Unsupported: 0'; do
  grep -Fq "$expected" "$verify" || { cat "$verify" >&2; die "evidence verification failed: $expected"; }
done

total="$(jq '.records | length' "$evidence")"
valid="$(awk -F': ' '/^Valid records:/ {print $2}' "$verify")"
[[ "$total" -ge 1 && "$valid" == "$total" ]] || die 'not every installed-app evidence record verified'
jq -e --arg s "$SESSION" 'all(.records[]; .session_id == $s and .agent_id == "customer-support")' "$evidence" >/dev/null \
  || die 'installed-app records do not share the customer-support operational identity'
jq -e 'any(.records[]; .orchestration.client == "zendesk-support-full-demo")' "$evidence" >/dev/null \
  || die 'installed-app evidence lacks Zendesk adapter client attribution'
jq -e 'any(.records[]; ((.classification.input_pii_redacted // false) == true or (.classification.pii_redacted // false) == true)
  and (.classification.pii_detected | index("email"))
  and (.classification.pii_detected | index("iban")))' "$evidence" >/dev/null \
  || die 'installed-app evidence does not prove email + IBAN redaction'
jq -e 'any(.records[]; .failover.role == "failed_attempt" and .failover.provider == "local-llama")' "$evidence" >/dev/null \
  || die 'installed-app evidence lacks the local-provider failure'
jq -e 'any(.records[]; .failover.role == "fallback_decision" and .failover.provider == "openai")' "$evidence" >/dev/null \
  || die 'installed-app evidence lacks the approved OpenAI fallback'

package_sha="not-recorded"
package_file="not-recorded"
if [[ -f "$STATE/zendesk-app/package.env" ]]; then
  # shellcheck disable=SC1090
  source "$STATE/zendesk-app/package.env"
  package_sha="${ZENDESK_APP_PACKAGE_SHA256:-not-recorded}"
  package_file="${ZENDESK_APP_PACKAGE:-not-recorded}"
fi

attestation="$STATE/zendesk-installed/$SESSION.operator-attestation.json"
umask 077
jq -n \
  --arg observed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg ticket_id "$TICKET" \
  --arg session_id "$SESSION" \
  --arg package "$package_file" \
  --arg package_sha256 "$package_sha" \
  --arg evidence "$evidence" \
  --arg evidence_sha256 "$(sha256sum "$evidence" | awk '{print $1}')" \
  --argjson records "$total" \
  '{
    proof_type: "operator-confirmed-ui-plus-talon-evidence",
    observed_at: $observed_at,
    ticket_id: $ticket_id,
    session_id: $session_id,
    observations: {
      private_app_installed: true,
      secure_setting_substitution_observed: true,
      newest_public_requester_comment_selected: true,
      returned_draft_only_inserted: true
    },
    package: {path: $package, sha256: $package_sha256},
    talon_evidence: {path: $evidence, sha256: $evidence_sha256, records: $records, signatures_valid: true}
  }' >"$attestation"
chmod 0600 "$attestation"

say
say 'ZENDESK INSTALLED APP VALIDATION RECORDED'
say "  Ticket:       $TICKET"
say "  Session:      $SESSION"
say "  Talon records:$total valid / 0 invalid"
say "  Attestation:  $attestation"
say
say 'UI observations are operator-confirmed; Talon identity, routing, redaction, cost, and signatures are machine-verified.'
