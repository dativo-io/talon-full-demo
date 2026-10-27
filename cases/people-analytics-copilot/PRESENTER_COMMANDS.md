# Presenter terminal commands

## Bootstrapping one real governed application

```bash
git switch feat/people-analytics-governed-demo
bash scripts/people-analytics-isolated.sh infra
bash scripts/people-analytics-isolated.sh config
${EDITOR:-vi} cases/people-analytics-copilot/.state/policy/agent.talon.yaml
${EDITOR:-vi} cases/people-analytics-copilot/.state/policy/proxy.isolated.talon.yaml
${EDITOR:-vi} cases/people-analytics-copilot/.state/policy/gateway.talon.yaml
read -rs -p "OpenAI key: " OPENAI_API_KEY; echo; export OPENAI_API_KEY
bash scripts/people-analytics-isolated.sh talon
unset OPENAI_API_KEY
bash scripts/people-analytics-isolated.sh app
```

Observe in a second terminal:

```bash
bash scripts/people-analytics-isolated.sh logs
```

The files in `.state/policy` are writable, untracked, and mounted read-only into the Talon containers. Policy reload is **explicit** and requires revalidation/restart:

```bash
# Delete/restore "- name: hr_aggregate_sql" in proxy.isolated.talon.yaml.
bash scripts/people-analytics-isolated.sh reapply
```

## Exact backend and evidence checks

Set the temporary shell helper below **from the repo root**:

```bash
CASE="$PWD/cases/people-analytics-copilot"
dc() {
  docker compose -f "$CASE/compose.isolated.yaml" --env-file "$CASE/.state/isolated.env" "$@"
}
dc exec -T hr-server python3 verify_isolation.py warehouse-info
dc exec -T ui python3 verify_isolation.py boundary
dc exec -T ui python3 verify_isolation.py discover
dc exec -T ui python3 verify_isolation.py allow
dc exec -T ui python3 verify_isolation.py deny
dc exec -T hr-server python3 verify_isolation.py counters
dc exec -T talon-mcp talon audit list
```

**Optional BEFORE experiment**, not part of the policy-toggle proof: run `dc exec -T hr-server python3 verify_isolation.py before`. This privileged process can directly export fictional records without Talon. `dc exec -T hr-server python3 verify_isolation.py reset` resets **only counters**, not privileges. Docker (not Talon) prevents the workforce application from reaching that private backend directly. Never call this a live agent migration.

For an independently signed session:

```bash
dc exec -T talon-mcp talon audit export --format signed-json \
  --session hr-demo-presenter --output /tmp/hr-presenter-evidence.json
dc exec -T talon-mcp talon audit verify --file /tmp/hr-presenter-evidence.json
```

Stop: `bash scripts/people-analytics-isolated.sh down`. To **delete the fictional DuckDB and demo Talon evidence volumes**, use `reset` (destructive).
