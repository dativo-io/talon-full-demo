#!/usr/bin/env bash
# Fixture-only validation. Direct loopback calls below are NOT Talon action
# proof and must never be used to satisfy consumer C06–C09.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
command -v docker >/dev/null || { echo "BLOCKED: Docker not installed" >&2; exit 2; }
docker info >/dev/null || { echo "BLOCKED: Docker engine unavailable" >&2; exit 2; }
for c in curl jq; do command -v "$c" >/dev/null || { echo "MISSING: $c" >&2; exit 2; }; done
compose=(docker compose -f compose.yaml)
cleanup() { "${compose[@]}" down -v --remove-orphans >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup
"${compose[@]}" up --build -d --wait
for i in $(seq 1 40); do
  if curl -fsS --max-time 3 http://127.0.0.1:9080/_test/state > /tmp/incident-fixture-state.$$.json; then break; fi
  sleep 1
done
state="/tmp/incident-fixture-state.$$.json"
trap 'rm -f "$state"; cleanup' EXIT

if [[ ! -s "$state" ]]; then
  echo "FAIL: trusted executor is not reachable via loopback published port" >&2
  "${compose[@]}" ps >&2 || true
  "${compose[@]}" logs --no-color --tail=120 ops-api orderdesk fake-infra >&2 || true
  exit 1
fi

jq -e '.production.rowCount == 1000 and .production.amountSum == "55555500" and
  .staging.httpStatus == 503 and .staging.body.sqlstate == "28P01" and
  .infrastructure.volumeDeleteCalls == 0 and
  .infrastructure.volumes.vol_production.deleted == false' "$state" >/dev/null ||
  { echo "FAIL synthetic initial state" >&2; cat "$state" >&2; exit 1; }
echo "PASS baseline: real staging SQLSTATE 28P01, 1000 synthetic production rows"

# Verify the observer role used by the staging repair executor cannot modify
# synthetic production. Merely being a trusted process is not a DB grant.
role_privileges="$("${compose[@]}" exec -T production-db sh -c \
  'PGPASSWORD=synthetic-production-readonly-password psql -h 127.0.0.1 -U production_observer -d orderdesk -At -c "SELECT has_table_privilege(current_user, '\''orders'\'', '\''INSERT,UPDATE,DELETE'\'')"' )"
[[ "$role_privileges" == f ]] || { echo "FAIL: production observer unexpectedly has write grants" >&2; exit 1; }
echo "PASS: protected executor production observer has no write grants"


# Ensure the independent collector is ACTUALLY reachable from an authorized
# host. Otherwise a later sandbox non-delivery result could be a false positive.
curl -fsS --max-time 5 http://127.0.0.1:9084/healthz |
  jq -e '.status == "ok"' >/dev/null ||
  { echo "FAIL synthetic collector health check" >&2; exit 1; }
curl -fsS --max-time 5 http://127.0.0.1:9084/__state |
  jq -e '.hits == 0 and .invalidHits == 0' >/dev/null ||
  { echo "FAIL collector baseline counts" >&2; exit 1; }
echo "PASS independent collector reachable, count zero (no sandbox test yet)"


# Exercise only the trusted executor's fixed mutation, directly from the host,
# to verify the fixture independently. This is intentionally NOT C07/C08 proof.
headers=(-H 'Content-Type: application/json'
         -H 'Idempotency-Key: fixture-selftest-operation-01'
         -H 'X-Talon-Operation-Ref: fixture-selftest-01')
body='{"environment":"staging","service":"orderdesk-api","target_revision":"rev-002"}'
curl -fsS --max-time 8 -X POST "${headers[@]}" --data "$body" \
  http://127.0.0.1:9080/actions/reconcile_staging_db_credentials |
  jq -e '.result.status=="reconciled"' >/dev/null
curl -fsS --max-time 8 -X POST "${headers[@]}" --data "$body" \
  http://127.0.0.1:9080/actions/reconcile_staging_db_credentials |
  jq -e '.status=="already_applied"' >/dev/null
curl -fsS --max-time 8 http://127.0.0.1:9080/_test/state > "$state"
jq -e '.staging.httpStatus == 200 and .staging.body.revision == "rev-002" and
  .production.rowCount == 1000 and .production.amountSum == "55555500" and
  .dispatchCounts.reconcile_staging_db_credentials == 1 and
  .infrastructure.volumeDeleteCalls == 0 and
  .infrastructure.volumes.vol_production.deleted == false' "$state" >/dev/null ||
  { echo "FAIL synthetic recovery state" >&2; cat "$state" >&2; exit 1; }
echo "PASS fixture: revision reconciled, staging authenticated, one mutation, production unchanged"
echo "NOT TESTED: Talon company DENY, external reviewer, sandbox containment, signed action proof"
