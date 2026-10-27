# People Analytics — CI acceptance matrix

This document describes what is **actually exercised on pull requests**, not what the demo intends to support eventually. All mandatory jobs require no employee data or commercial LLM credentials. The external-provider path is deliberately opt-in.

## Mandatory pull-request gates

| Gate | What runs | Independent acceptance conditions |
|---|---|---|
| Unit and offline HTTP tests | `validate` job, `make people-analytics-validate` | Deterministic seeded DuckDB; persistent SQL aggregates; cohort restrictions; parameterized filters; guided/AI tool-loop fail-closed behavior; HTTP routes; documentation links; operator authentication and command allowlist; JavaScript syntax for both applications |
| Real MCP and model protocol | `people-analytics-talon-contract` | Two **real Talon processes** (LLM gateway and MCP proxy), a **fake** OpenAI-compatible upstream, a real synthetic HR service and DuckDB. Three approved aggregate tools discovered; forbidden export denied before dispatch; no upstream export; fake model consumes returned aggregate; signed LLM/MCP session verified |
| Docker non-bypass | `people-analytics-isolation-contract` | Privileged synthetic HR backend's **BEFORE** direct export works; counters reset explicitly; separated UI has no HR volume or private network route; approved aggregate through Talon succeeds; forbidden export reaches neither HR nor DuckDB; signed evidence verifies |
| Terminal-first presenter parity | Same Docker isolation job, granular commands | Individual BEFORE, counters, RESET, boundary, discover, allow, deny, backend count and signed session export/verify commands run against **real** services |
| Browser-first application | Same Docker isolation job, Playwright + headless Chromium | Business dashboard loads and filters; mode explicitly says GUIDED; assistant retrieves and displays a real Talon-approved aggregate; forbidden probe produces a committed denial; independent HR counter is not exposed to unprivileged UI |
| Browser-first operator console | Same Docker isolation job, real authenticated console + headless Chromium | Unauthenticated/cross-origin requests rejected; operator token required; every displayed allowlisted action clicked in order; actual exit codes and stdout verified; BEFORE, explicit RESET, allow/deny, independent backend counter and Talon signature verification all executed |
| Broader repo contracts | `validate`, `talon-release-contract` and existing other workflows | Existing Go/JS demos and released Talon contracts continue to pass; People Analytics changes must not break the surrounding repo |

Browser test: `python scripts/test-people-analytics-browser.py`. It uses **real Chrome-compatible browser interactions** and a localhost operator HTTP server against the running Docker stack; it is **not** a mock frontend or a screenshot-only comparison.

On a CI browser failure, the job uploads an optional short-lived screenshot under `people-analytics-browser-failure`. It contains **fictional** employee data; do not reuse this mechanism with production HR records.

## Reproduce locally

~~~bash
# Offline tests (Python dependencies already installed)
make people-analytics-validate

# Real released Talon LLM+MCP with a deterministic fake model
bash scripts/test-people-analytics-talon.sh

# Docker-isolated UI, backend, Talon, and repeatable proof
bash scripts/people-analytics-isolated.sh up
bash scripts/people-analytics-isolated.sh verify

# Optional browser regression on the started Docker environment
python -m pip install playwright==1.55.0
python -m playwright install chromium
python scripts/test-people-analytics-browser.py

bash scripts/people-analytics-isolated.sh down
~~~

The browser acceptance uses loopback ports 8501 and 8502. It starts a separate token-protected local operator process for the test and automatically shuts it down. Ensure an interactive presenter console is **not already occupying port 8502** when running the browser test.

## Explicitly NOT proven by mandatory CI

- **Real external OpenAI performance, output quality, model prices or latency.** The LLM provider in mandatory CI is fake; the Talon gateway is real. A human can run the separate, billable opt-in `bash scripts/test-people-analytics-real-provider.sh` in a trusted environment.
- **Production IAM or warehouse row-level authorization.** The demo uses synthetic DuckDB and a Docker network/mount perimeter. Talon cannot govern a direct database/HTTP path that bypasses it.
- **Universal PII/DLP compliance.** The agent scenario disables PII redaction and does not prove cross-cohort inference attacks are impossible.
- **A migration of one privileged running agent.** BEFORE and AFTER are different process identities; the reset measures backend calls after the baseline, not a change of permissions.
- **A complete usability study.** Browser E2E checks interactive correctness and trust evidence, not human comprehension, accessibility conformance or visual polish on every platform.

Do not describe the guided default UI or deterministic mock-provider outputs as actual model-generated answers. No customer-identifying information or real HR data belongs in these fixtures or logs.
