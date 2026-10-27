# Terminal playbook

**Best for:** engineers, security reviewers and anyone who wants to see unmodified commands, execution counters and signed evidence. The [browser playbook](UI_PLAYBOOK.md) invokes the **same allowlisted actions** through a separate authenticated operator interface.

> **Not a before/after policy flip.** BEFORE uses a privileged HR process with direct access; AFTER uses a *different, already-isolated AI process*. Only test counters reset. Talon does not revoke an existing warehouse credential.

## 1. Prepare the demo

On your trusted Linux demo host, from the repository root:

~~~bash
git fetch origin
git switch feat/people-analytics-governed-demo
git pull --ff-only
export CASE="$PWD/cases/people-analytics-copilot"
export HR_DEMO_TALON_BIN="$(readlink -f "$(command -v talon)")"

bash scripts/people-analytics-isolated.sh up
~~~

Set up a local shortcut for inspectable Docker Compose commands in this shell:

~~~bash
dc() {
  docker compose -f "$CASE/compose.isolated.yaml" \
    --env-file "$CASE/.state/isolated.env" "$@"
}
dc ps
~~~

The HR service, aggregate dashboard, Talon MCP proxy and AI app should be running; seed and Talon initialization are one-shot services. **No real LLM provider is required**. Do not run the combined `verify` script during the steps below; it performs its own baseline and counter reset.

## 2. Run seven proof stages

### Stage 1 — BEFORE: direct privileged access

~~~bash
dc exec -T hr-server python3 verify_isolation.py before
dc exec -T hr-server python3 verify_isolation.py counters
~~~

One **fictional** employee's name/salary appears and `hr_employee_export` increases. The request goes **directly** to the HR backend; it **bypasses Talon** and is therefore absent from Talon evidence.

### Stage 2 — RESET only the counters

~~~bash
dc exec -T hr-server python3 verify_isolation.py reset
dc exec -T hr-server python3 verify_isolation.py counters
~~~

All counters are now zero. This **does not** reverse the prior export or change permissions. The remaining tests measure actions **since reset**.

### Stage 3 — Prove Docker isolation

~~~bash
# Where each container is connected:
docker inspect "$(dc ps -q ui)" --format '{{json .NetworkSettings.Networks}}'
docker inspect "$(dc ps -q talon-mcp)" --format '{{json .NetworkSettings.Networks}}'
docker inspect "$(dc ps -q hr-server)" --format '{{json .NetworkSettings.Networks}}'

# What filesystem mounts the AI app has:
docker inspect "$(dc ps -q ui)" --format '{{json .Mounts}}'

# Assert the direct HR network/DB bypass fails, yet charts still work:
dc exec -T ui python3 verify_isolation.py boundary
~~~

The UI is on `app_net` only; HR is on `private_hr`; Talon MCP bridges both. The UI has **no DuckDB volume**. **Docker**, not Talon, makes the direct path unavailable.

### Stage 4 — Show actual policies and discovery

~~~bash
dc exec -T talon-mcp cat /state/agent.talon.yaml
dc exec -T talon-mcp cat /case/proxy.isolated.talon.yaml

dc exec -T ui python3 verify_isolation.py discover
~~~

The model/tool boundary exposes exactly three tools:

~~~text
hr_attrition_summary
hr_headcount_summary
hr_tenure_summary
~~~

The privileged `hr_employee_export` tool is absent from discovery. Reading the policy file alone is not proof of enforcement; the next two calls are.

### Stage 5 — Execute an allowed aggregate

~~~bash
dc exec -T ui python3 verify_isolation.py allow
~~~

The returned data comes from DuckDB, with a **Talon allow receipt** containing `decision=allow`, `evidence.committed=true` and an evidence ID.

### Stage 6 — Force a denied operation, then check HR

~~~bash
dc exec -T ui python3 verify_isolation.py deny
dc exec -T hr-server python3 verify_isolation.py backend-counts
dc exec -T hr-server python3 verify_isolation.py counters
~~~

The Talon receipt shows `decision=deny`, `provenance=not_dispatched`, and a committed evidence ID. The **independent** HR backend must report `hr_employee_export=0` **since reset**, while the aggregate-tool counter has increased.

This operator probe **forces** a disallowed MCP call; it does not claim the guided assistant or LLM attempted the export.

### Stage 7 — Independently verify evidence

All allowed/denied presenter calls share the `hr-demo-presenter` session.

~~~bash
dc exec -T talon-mcp talon audit export \
  --format signed-json --session hr-demo-presenter \
  --output /tmp/hr-presenter-evidence.json

dc exec -T talon-mcp talon audit verify \
  --file /tmp/hr-presenter-evidence.json
~~~

Expected: zero invalid records, zero missing signatures and zero parse errors. **The direct BEFORE export is intentionally missing**, because it never crossed Talon.

## 3. Switch to UI for the same proof (optional)

Start the host-only operator console in a **second host terminal**:

~~~bash
bash scripts/people-analytics-isolated.sh presenter
~~~

Use its one-time token to unlock **http://127.0.0.1:8502**. The customer-facing dashboard is at **http://127.0.0.1:8501**. If remote, tunnel both ports:

~~~bash
ssh -N -L 8501:127.0.0.1:8501 -L 8502:127.0.0.1:8502 user@demo-host
~~~

The console offers **Copy command** and prints actual stdout/stderr for each action. It has Docker operator privileges and must **never** be exposed on a public network or embedded in the AI workload.

Alternatively, run individual actions through the same fixed command catalog used by the UI:

~~~bash
python3 scripts/people_analytics_presenter.py --list
python3 scripts/people_analytics_presenter.py --action discover
~~~

Run the catalog's full sequence from the [browser playbook](UI_PLAYBOOK.md) or use the direct commands in Stage 1–7. **Do not repeat BEFORE after RESET** if you intend to assert zero exports.

## 4. Wrap up

**What this proves:** the isolated workload cannot reach privileged HR directly; Talon permits approved aggregate MCP tools and denies the export before dispatch; independent counters and signatures corroborate execution.

**What it doesn't:** Talon controlling traffic outside its gateway, a live migration of agent permissions, full HR IAM/DLP, or real provider inference in default **GUIDED · NO LLM** mode.

For billable LIVE-provider setup or debugging individual processes, see [Advanced setup](ADVANCED_SETUP.md).

~~~bash
bash scripts/people-analytics-isolated.sh down
~~~

`reset` additionally **deletes the synthetic HR and Talon state volumes**.
