# People Analytics — transparent presenter commands

For a conversation with prospective customer, **do not hide the demonstration behind a single
success message.** These commands call the actual running containers and print
the original Talon governance decisions and the independent HR execution counters.

This is a comparison between two workloads **already running with different
privileges**, not a before/after policy flip, rollout, or identity migration.

- BEFORE: a test executed INSIDE the privileged synthetic HR service sends an
  employee-level export directly to its local MCP endpoint; Talon does not see it.
- RESET: the presenter explicitly clears the HR mock service's *execution
  counters*. It does NOT undo that earlier execution or revoke HR permissions.
- AFTER: the separate AI container has no HR DuckDB mount or private backend
  network route; allowed analytics flows through Talon. Talon prevents even an
  intentionally forced employee-export MCP request.

## Choose your interface: browser or shell

**Both interfaces run exactly the same allowlisted commands against the same
Docker containers, DuckDB dataset, independent backend counters and signed
Talon evidence.** The browser does not simulate or replay successful results.
Each button displays its exact shell command, real stdout/stderr and exit code.

The main People Analytics dashboard (port 8501) is deliberately **unprivileged**.
The operator proof console is a **separate host process** bound to loopback
(port 8502), because its BEFORE action deliberately has Docker authority to
access the privileged synthetic HR backend. The AI container does not have
Docker access and cannot connect to the host console via its private namespace.

Start the isolated services first as explained below, then **in a second Ubuntu
terminal** start the operator console:

~~~bash
cd ~/demos/talon-full-demo-hr
bash scripts/people-analytics-isolated.sh presenter
~~~

The host terminal prints a one-time operator token. Paste it into the console's
password field. It is kept in that browser tab's memory and is never placed
in the URL, the AI prompt, or the source repository. Do not show the token
during a public screen share.

If Ubuntu is on a remote host, forward **both** services through SSH from
your laptop:

~~~bash
ssh -N -L 8501:127.0.0.1:8501 -L 8502:127.0.0.1:8502 sergey@178.62.232.131
~~~

Open the app at http://127.0.0.1:8501 and choose **Open the 7-stage presenter
proof console**, or navigate directly to http://127.0.0.1:8502. You can
use the dashboard, the operator console or the terminal interchangeably.

To run the **exact same** presenter action from your host shell without a
browser (instead of the explicit Docker Compose commands in this document):

~~~bash
python3 scripts/people_analytics_presenter.py --list
python3 scripts/people_analytics_presenter.py --action before
python3 scripts/people_analytics_presenter.py --action counters
python3 scripts/people_analytics_presenter.py --action reset
python3 scripts/people_analytics_presenter.py --action boundary
python3 scripts/people_analytics_presenter.py --action discover
python3 scripts/people_analytics_presenter.py --action allow
python3 scripts/people_analytics_presenter.py --action deny
python3 scripts/people_analytics_presenter.py --action backend_counts
python3 scripts/people_analytics_presenter.py --action evidence_export
python3 scripts/people_analytics_presenter.py --action evidence_verify
~~~

The operator console is **synthetic-demo-only**: a fixed whitelist, random
one-time token, no generic command interpreter, and localhost binding. Docker
operator privileges remain powerful; never expose port 8502 publicly, do not
forward it to people you do not trust, and never run it against real HR data.
The console is not a Talon feature or a production admin interface.

## Preparation (Ubuntu, at repository root)

~~~bash
cd ~/demos/talon-full-demo-hr
git switch feat/people-analytics-copilot-v1
git pull --ff-only
export CASE="$PWD/cases/people-analytics-copilot"
export HR_DEMO_TALON_BIN="$(readlink -f "$(command -v talon)")"

# Starts synthetic data seed, separate HR and dashboard services, real Talon
# MCP process, and a restricted browser/AI app. No external provider key needed.
bash scripts/people-analytics-isolated.sh up

# Use this transparent shortcut to see the *exact* Docker Compose calls:
dc() {
  docker compose -f "$CASE/compose.isolated.yaml" \
    --env-file "$CASE/.state/isolated.env" "$@"
}

dc ps
~~~

Expected: hr-server, dashboard, talon-mcp and ui are running; seed and talon-init are successful one-shot containers. If anything is restarting, inspect the logs before presenting.

**Why separate commands?** Each step deliberately displays the state of an actual process, using either the backend, the restricted app, Docker metadata, or Talon's CLI. None of the presenter results rely on the browser's green status label. The shell shortcut dc is defined **only in this terminal**; define it again in a new shell.

From your laptop, open the UI with SSH forwarding (keep the tunnel open):

~~~bash
ssh -N -L 8501:127.0.0.1:8501 user@demo-host
~~~

Then browse to http://127.0.0.1:8501. This does not expose the app's port publicly.

**Do not run the combined verify script during the individual sequence**: it includes its own baseline+reset, and would change the execution counters you are explaining.

## Phase 1 — BEFORE: privileged backend can bypass Talon

~~~bash
# This runs in the privileged HR SERVICE, not in the AI app.
# It prints ONE fictional employee example and deliberately does NOT reset counters.
dc exec -T hr-server python3 verify_isolation.py before

# Observe an HR export recorded directly by the independent backend.
dc exec -T hr-server python3 verify_isolation.py counters
~~~

Expected: a synthetic employee name/salary is returned, and
hr_employee_export is greater than zero. This is not a Talon failure: the
request **never traversed Talon**. The baseline demonstrates the risk of an
agent inheriting comparable privileges.

## Phase 2 — Explicit reset of *mock* counters (no policy change!)

~~~bash
dc exec -T hr-server python3 verify_isolation.py reset
dc exec -T hr-server python3 verify_isolation.py counters
~~~

Expected: all execution counters zero. Explain why:
"Now I'll start measuring operations for the separate, isolated AI workload.
We haven't changed the backend's privileged identity, tool code, database or
Talon policy. We only reset synthetic instrumentation."

## Phase 3 — Show the enforcement topology, not a green checkbox

~~~bash
# Names of networks joined by each running container:
docker inspect "$(dc ps -q ui)" --format '{{range $n, $_ := .NetworkSettings.Networks}}{{println $n}}{{end}}'
docker inspect "$(dc ps -q talon-mcp)" --format '{{range $n, $_ := .NetworkSettings.Networks}}{{println $n}}{{end}}'
docker inspect "$(dc ps -q hr-server)" --format '{{range $n, $_ := .NetworkSettings.Networks}}{{println $n}}{{end}}'

# The UI/AI service has no mounted HR database:
docker inspect "$(dc ps -q ui)" --format '{{range .Mounts}}{{println .Destination}}{{end}}'

# Independent test: no database mount or private HR network access; safe
# browser dashboard still loads from its fixed aggregate-only API.
dc exec -T ui python3 verify_isolation.py boundary
~~~

Expected:
- UI joins app_net only, HR service joins private_hr only.
- Talon MCP proxy joins **both** networks and is the only approved HR bridge.
- UI mounts no raw HR DuckDB data volume.
- The direct private HR connection fails; the dashboard aggregate route succeeds.

**Important:** Docker networking and volume isolation prevent bypass here.
Talon itself does not revoke already-issued database credentials. In a real
deployment, warehouse RBAC and service IAM must provide further protections.

## Phase 4 — Show precisely what the AI can discover

~~~bash
# Calls tools/list over real Talon MCP using a fixed session "hr-demo-presenter".
dc exec -T ui python3 verify_isolation.py discover
~~~

Expected ONLY:
- hr_attrition_summary
- hr_headcount_summary
- hr_tenure_summary

The forbidden hr_employee_export tool does not appear. Unlike prompting an
LLM to "behave", this is enforced at the tool-discovery boundary.

## Phase 5 — A permitted operation and its actual Talon receipt

~~~bash
dc exec -T ui python3 verify_isolation.py allow
~~~

This executes hr_attrition_summary via the Talon MCP proxy, reads an aggregate
calculated by DuckDB and prints the unmodified governance extension. Show:
decision=allow, evidence.committed=true, evidence.id present. No named employee
rows are returned.

## Phase 6 — Force a prohibited operation; verify pre-dispatch deny

~~~bash
# This bypasses the model's normal tool selection, NOT Talon's MCP proxy.
# It tests preventive enforcement, not the model's willingness to refuse.
dc exec -T ui python3 verify_isolation.py deny

# Independent HR service counter; must show zero employee exports since reset.
dc exec -T hr-server python3 verify_isolation.py backend-counts
dc exec -T hr-server python3 verify_isolation.py counters
~~~

The denied Talon receipt must show decision=deny,
provenance=not_dispatched and evidence.committed=true. Crucially, the
**independent backend counter** must show hr_employee_export=0,
whereas hr_attrition_summary must have increased. The baseline from Phase 1
may have executed an export; zero is **since the explicit Phase 2 reset**.

## Proof matrix — who independently confirms what?

| Customer question | Independent observation | What it does **not** prove |
|---|---|---|
| Could a privileged path retrieve employee records? | BEFORE direct tool call in hr-server and its export counter | Talon blocked it (Talon was bypassed) |
| Can the AI app open HR data directly? | Docker network membership, absence of DB volume, failed direct connect | Every possible attack is prevented or IAM is production-ready |
| Which tools does the AI use case see? | Talon tools/list response, backed by actual agent/proxy configs | SQL access outside the controlled deployment is impossible |
| Did analytics execute? | Allowed Talon receipt plus increased backend aggregate counter | The LLM's answer is correct or causally explanatory |
| Did the forbidden export execute? | Denied not_dispatched receipt **and** zero export counter since reset | That an export never happened before reset |
| Can we check the record later? | Talon CLI signed export and verification | Events outside Talon or immutable storage |

## Phase 7 — Independently verify signed evidence

All presenter commands in Phases 4–6 use the *same* session:
hr-demo-presenter. Export that session from the Talon process:

~~~bash
dc exec -T talon-mcp talon audit export \
  --format signed-json \
  --session hr-demo-presenter \
  --output /tmp/hr-presenter-evidence.json

dc exec -T talon-mcp talon audit verify \
  --file /tmp/hr-presenter-evidence.json
~~~

The CLI must report zero invalid records, zero missing signatures and zero
parse errors. The direct BEFORE call is absent from this Talon evidence by
design; Talon didn't see it. Never claim it was blocked.

## Inspect the active policies before or after the request

~~~bash
# These files are consumed by the live Talon container.
dc exec -T talon-mcp cat /state/agent.talon.yaml
dc exec -T talon-mcp cat /case/proxy.isolated.talon.yaml
~~~

The first lists the three permitted HR tools for the AI agent. The second
exposes the MCP upstream, its tool allowlist and forbidden export. **Do not
describe a tool as blocked based only on reading YAML**: the separate discovery,
denial, backend-counter and evidence commands above establish runtime behavior.

## Show actual AI generation (separate, optional)

The above seven phases are a fully working **governed tool** demonstration
without an LLM key. The Docker UI starts in GUIDED mode.

To switch **GUIDED → LIVE AI** (different switch from the BEFORE/AFTER
security comparison!), obtain a real provider key and enable the separately
configured Talon LLM gateway:

~~~bash
read -rs -p "OpenAI API key: " OPENAI_API_KEY; echo
export OPENAI_API_KEY
bash scripts/people-analytics-isolated.sh live
~~~

This can incur OpenAI costs; the real-provider path is not automatically
validated in CI. The isolated LIVE launcher passes the key through the initialization container's environment into Talon's encrypted vault; privileged Docker operators may inspect process/container environment. Use only on a trusted demo machine with fictional HR records. After checking it on the target host, ask the AI for six-month
department attrition and inspect Talon model/tool session evidence. Model
output is advisory; the DuckDB aggregates are authoritative. The live
provider path has a separate opt-in smoke test:

~~~bash
# Uses separate loopback services; stop any conflicting demo processes first.
bash scripts/test-people-analytics-real-provider.sh
~~~

That smoke requires a real key and is NOT part of the default fake-provider
acceptance. Do not claim a successful live provider call until it passes.

## What to say while presenting

"First you see what the privileged backend could do if an AI service account
inherited its permissions. Next we keep the HR backend unchanged but run the
AI use case with no database credentials or route to that private HR service.
Talon exposes only approved aggregate capabilities. Even when I force a
forbidden tool request through Talon, it is denied before reaching the
backend. Here is the backend's counter, and here are the independently
verified signed records."

For the complete customer story, see PEOPLE_ANALYTICS_DEMO_PLAN.md.

## Cleanup

~~~bash
bash scripts/people-analytics-isolated.sh down
# Optional destructive reset of *synthetic* volume and Talon demo state:
# bash scripts/people-analytics-isolated.sh reset
~~~
