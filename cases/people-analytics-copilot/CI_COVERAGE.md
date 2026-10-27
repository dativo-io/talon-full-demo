# People Analytics · CI acceptance

| Check | Verified behavior |
|---|---|
| Python unit + docs | Fictional DuckDB metrics, two exact approved SQL queries, unsafe SQL refusal, HTTP path, backend counters, model tool-loop fail-closed, JavaScript syntax and documentation links |
| Talon MCP integration | Released Talon proxy, allowed aggregate tools, denied privileged export, verified signed receipts |
| Credential-free model integration | Real Talon LLM+MCP, fake provider model tool selection, session traces and signatures—not paid OpenAI |
| Docker isolation | Workforce app has no DB volume or private backend route; privileged BEFORE is intentionally separate |
| Chromium | **One** workforce dashboard (8501), actual allowed SQL, HR SQL-validator rejection, guided MCP aggregate and export denial |
| Policy flip | Edit writable runtime Talon MCP policy; restart Talon; same SQL changes allow→deny; HR dispatch counter unchanged; restore allow; export/verify signed evidence |

## Run

```bash
make people-analytics-validate
bash scripts/test-people-analytics-talon.sh
bash scripts/people-analytics-isolated.sh up
bash scripts/people-analytics-isolated.sh verify
python scripts/test-people-analytics-browser.py
python scripts/test-people-analytics-policy-change.py
bash scripts/people-analytics-isolated.sh down
```

Playwright Chromium must be installed for browser E2E. CI uses a hosted Chromium-compatible browser and saves a fictional-data-only screenshot on failure. The automated policy-change test restores the original editable policy in a `finally` block.

**Not proved by mandatory CI:** a real OpenAI provider, model quality or latency, production employee IAM, arbitrary SQL safety, production DLP, legal compliance, or universal control over direct calls bypassing Talon.

See [quickstart](README.md), [terminal playbook](PRESENTER_COMMANDS.md) and [external provider smoke](ADVANCED_SETUP.md).
