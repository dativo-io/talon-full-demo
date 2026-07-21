# n8n integration

The Compose environment is pinned to `n8n:2.30.4`, binds only to `127.0.0.1:5678`, requires an operator-supplied encryption key, and commits no credentials.

The repository intentionally contains a workflow specification rather than an untested hand-authored export. Build and run the workflow in the pinned n8n UI, export it without credentials, import it into a clean container running the same version, reconnect the Header Auth credential, and rerun before committing any workflow JSON. Until that sequence is completed, n8n is a tested deployment contract and implementation specification—not a finished workflow artifact.

## Budget-branch contract, tested locally

The workflow-spec's denial branch (`403 session_budget_exceeded` → write
`status.json` → stop) is exercisable without Docker or a provider:
`mock/mock_talon.py` with `MOCK_TALON_SESSION_BUDGET_REQUESTS=2` denies the
third request on the same `X-Talon-Session-ID` with HTTP 403, a body
containing `session_budget_exceeded`, and zero simulated cost — the exact
contract the workflow's Switch node must branch on.
`scripts/test-integration-local.sh` asserts this sequence in CI. Real
Talon session budgets are soft caps (see Talon `LIMITATIONS.md`);
real-provider budget calibration remains an external validation gate.
