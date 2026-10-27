# CI coverage: what is actually tested

Mandatory PR checks use **fictional data** and **no paid LLM provider**. The browser and terminal paths exercise the same real Docker/Talon stack.

| CI job | Real acceptance checks |
|---|---|
| **validate** | DuckDB seed and SQL aggregates; cohort and input safeguards; UI/backend HTTP contracts; agent-loop fail-closed behavior; operator API authentication; both browser scripts' syntax; documentation links |
| **people-analytics-talon-contract** | Real Talon LLM gateway + MCP proxy, deterministic **fake** model provider, aggregate tool execution, blocked export, linked signed LLM/MCP session |
| **people-analytics-isolation-contract** | Docker private HR network and DB mounts; privileged BEFORE succeeds; explicit RESET; isolated AFTER aggregate allowed/export denied; independent HR counters and signature verification |
| **Browser acceptance** (inside isolation job) | Real Chromium opens both UI applications, filters dashboard, runs GUIDED analytics and forbidden-tool probe, authenticates to the operator console and clicks through all its real checks |
| **talon-release-contract / other repo jobs** | Regression coverage for reviewed Talon release and the broader demo repository |

Browser regression script: [scripts/test-people-analytics-browser.py](../../scripts/test-people-analytics-browser.py). Browser failures save a temporary screenshot artifact named `people-analytics-browser-failure` (fictional data only).

## Run locally

~~~bash
# From repo root; install the HR Python dependencies first:
make people-analytics-validate

# Real Talon gateway and MCP, fake provider, signed session:
bash scripts/test-people-analytics-talon.sh

# Real Docker services and isolation proof:
bash scripts/people-analytics-isolated.sh up
bash scripts/people-analytics-isolated.sh verify

# Optional real browser regression:
python -m pip install playwright==1.55.0
python -m playwright install chromium
python scripts/test-people-analytics-browser.py

bash scripts/people-analytics-isolated.sh down
~~~

The browser test starts a temporary, token-authenticated operator server on localhost:8502. Stop any interactive operator console using that port before running it.

## Not proven by mandatory CI

- **Real model generation:** regular CI uses a fake provider. Real OpenAI requires the explicit, billable [smoke test](ADVANCED_SETUP.md#optional-test-a-real-external-model).
- **Production HR controls:** no real employee data, IAM, row-level policy, GDPR compliance or comprehensive PII protection.
- **All possible bypasses:** Talon covers routed calls; Docker protects the demo's direct HR network/file boundary.
- **A live privilege migration:** BEFORE and AFTER are different workloads; the counter reset changes no permissions.
- **Human usability:** the browser test checks functional navigation and actual output, not a full UX/accessibility study.

See [README](README.md) for the architecture and [demo plan](PEOPLE_ANALYTICS_DEMO_PLAN.md) for the customer-facing proof story.
