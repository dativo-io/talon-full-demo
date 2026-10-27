# People Analytics Copilot · Talon full demo

A customer-facing, synthetic **Workforce Intelligence** dashboard. A persistent DuckDB HR warehouse backs parameterized SQL. The browser/AI application now reads the dashboard through a **separate aggregate-only HTTP service**, not through a mounted HR database. AI model traffic and tool calls travel through Dativo Talon.

**Buyer story:** The People Analytics team already operates a governed HR warehouse. Business users need an AI assistant to analyze attrition, headcount and tenure. Talon adds **use-case-specific AI runtime permissions** and signed evidence, without replacing the HR warehouse's access controls.

## Start here: choose the correct demo mode

| Mode | What you see | External LLM key? | Main proof |
|---|---|---|---|
| **Isolated guided** — best starting point for prospective customer | Real DuckDB, Docker separation, real Talon MCP and deterministic (non-LLM) assistant | No | Restricted data path, allow/deny, signed evidence |
| **Credential-free model integration** | Real Talon LLM + MCP processes, real DuckDB; fake upstream model emits a deterministic tool call | No | Gateway and tool-call mechanics; **not real AI quality** |
| **External-model live** — opt-in | Actual OpenAI model through Talon gateway, authorized tools executed via MCP | Yes; billable | Natural-language AI interaction after provider smoke passes |

**Two different transitions:** "BEFORE → AFTER" compares a privileged HR backend with a **separately deployed, restricted AI application**. It is *not* a Talon on/off switch, runtime policy change, or migration of one agent. "GUIDED → LIVE" changes the response mode, *not* employee-data access permissions.

**Presenting the demo?** Choose the [browser-first playbook](UI_PLAYBOOK.md) or [terminal-first playbook](PRESENTER_COMMANDS.md) to show direct HR access, explicitly reset counters, inspect network boundaries, display Talon allow/deny responses and verify signed evidence. Follow the [12–15 minute plan](PEOPLE_ANALYTICS_DEMO_PLAN.md) for the narrative.

### Fastest customer setup (Docker)

Requires Docker with the **Compose v2 plugin**, OpenSSL and a compatible Talon binary on the host. From the checked-out repository root:

~~~bash
git switch feat/people-analytics-copilot-v1
git pull --ff-only
talon version
docker compose version
bash scripts/people-analytics-isolated.sh up
bash scripts/people-analytics-isolated.sh verify
~~~

This starts in **GUIDED** mode, with fictional employees and no LLM provider key. For customer presentation, use the guided browser steps in [UI_PLAYBOOK.md](UI_PLAYBOOK.md) or the individual commands in [PRESENTER_COMMANDS.md](PRESENTER_COMMANDS.md), not just the combined test. Open **http://127.0.0.1:8501**; from a remote VM forward that port using SSH, for example:

~~~bash
ssh -N -L 8501:127.0.0.1:8501 user@demo-host
~~~

Finish with bash scripts/people-analytics-isolated.sh down (preserves synthetic data); reset also **deletes** the synthetic HR and Talon state volumes.

**Verification status:** Offline application tests, real Talon with a simulated LLM, Docker isolation, and command-by-command presenter checks have passed CI. The optional **real OpenAI provider smoke has not been executed**; that remains a separate presentation gate.

## Source and licensing

The synthetic HR data generator, reference workforce metric calculations and Plotly HTML helper were incorporated **unchanged** from:

- Upstream: https://github.com/franciscomorenosys/hr-data-pipeline
- Pinned source commit: f0edfe24f2e29d02b4145e9e806c3ad0826b7f5b
- License: MIT; retained at upstream_hr/LICENSE
- Used modules: upstream_hr/data/generate_sample_data.py, upstream_hr/hr_pipeline/transform.py, upstream_hr/hr_pipeline/dashboard.py

The original project demonstrates HRIS/payroll/compliance joins and reports. This case reuses its **synthetic employee generator** and Plotly helpers; the vendored reference Pandas calculations remain available, but **DuckDB SQL now computes the authoritative demo metrics**. No payroll/IMSS compliance reporting is claimed. The SQL queries, UI and Talon integration are original code in this repository.

**Everything shown is fictional:** 1,200 generated employee records, seeded deterministically, and aggregate calculations over fictional employment histories. A synthetic, privileged employee-export tool exists as the negative test.

## What the demo actually proves

1. A separate aggregate-only dashboard HTTP service calculates historical attrition, headcount and tenure from parameterized SQL; the browser/AI workload needs **no DuckDB file access**.
2. A Talon MCP proxy advertises **three aggregate tools**: hr_attrition_summary, hr_headcount_summary, hr_tenure_summary. It hides the privileged hr_employee_export capability from discovery.
3. In guided mode, the app calls the aggregate tools **through Talon** and uses their real results to produce a deterministic (non-LLM) answer.
4. In live mode, the model gets aggregate tool definitions via Talon's MCP discovery; model requests go **through Talon's LLM gateway**, and every executed tool call goes through its **MCP proxy**, requiring a committed allow receipt. No DB SQL interface is offered to the model. The same Talon agent key is used by default for LLM and MCP requests.
5. An explicit **operator-only** negative probe attempts the privileged export through Talon. The upstream execution count must stay at zero and Talon's evidence must report a non-retryable, pre-dispatch denial.
6. The real Talon acceptance gate verifies tool discovery, allowed tool invocations, denied export, zero export dispatch, and signed evidence. A second phase sends a model-selected tool call through a **real Talon LLM gateway** using a deliberately fake OpenAI-compatible provider (no external model fees).

This is **not** an official Workday integration, a causal HR predictor, row-level database authorization, comprehensive PII/DLP for arbitrary SQL, or a GDPR compliance certificate. If the assistant bypasses the MCP proxy, Talon cannot govern those direct calls. Cohort suppression belongs in the HR backend; it is not delegated to the LLM.

## Structure

- demo.py — three process modes: privileged synthetic HR MCP, fixed aggregate-only dashboard API, and separate browser/AI app (no DB mount required).
- warehouse.py — deterministic seed into a persistent local DuckDB file; parameterized SQL analytics and deliberately privileged detail query.
- analytics.py — chart rendering over DuckDB-returned aggregate results.
- web_ui.py — HTML dashboard, inline Plotly charts, live/guide chat interface and operator probe.
- agent_runtime.py — model-driven chat-completions tool loop: Talon LLM gateway -> tool discovery -> Talon MCP calls.
- agent.talon.yaml — **explicit shared agent tool allowlist** for both Talon LLM and MCP surfaces; replaces scaffold defaults.
- gateway.talon.yaml — separate real-provider gateway configuration (OpenAI-compatible).
- mock_llm.py / verify_live.py — no-key test using a real Talon gateway and deterministic synthetic LLM upstream; never represented as a real OpenAI call.
- proxy.talon.yaml — three approved read-only aggregate tools, employee export explicitly forbidden.
- verify.py — mandatory **real Talon** integration acceptance and cryptographic signature verification.
- verify_real_provider.py — provider-backed model/tool/evidence smoke, only run with a real API key.
- compose.isolated.yaml + verify_isolation.py — separate backend network and DB volume, plus a BEFORE privileged direct export / AFTER isolated AI access proof.
- PEOPLE_ANALYTICS_DEMO_PLAN.md — customer-facing presentation timeline, proof requirements and limitations.
- test_demo.py / test_agent_runtime.py / test_warehouse.py — isolated DuckDB, HTTP and agent-loop tests.
- upstream_hr/ — source-pinned MIT code, with retained license.

## Setup — synthetic workforce dashboard and Talon MCP

Requirements: Python 3.10+, Talon supporting MCP 2026-07-28, curl, openssl and free loopback ports 8080 / 8501 / 9091 / 9093. The temporary model integration test additionally uses 8082 / 9092. A provider key is **not** required to validate Talon or run guided mode.

From repository root:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r cases/people-analytics-copilot/requirements.txt
make people-analytics-validate
make people-analytics-seed  # creates cases/people-analytics-copilot/.state/hr-warehouse.duckdb
export DEMO_DIR="$PWD/cases/people-analytics-copilot"
export TALON_BIN="$(command -v talon)"
~~~

Keep the absolute DEMO_DIR and TALON_BIN values available to your terminals. **Only the HR service and the separate aggregate dashboard service open DuckDB in read-only mode. The browser/AI service never opens the employee database.**

**Limitation of the manual setup:** all processes share the same Linux host/user and networking context. It demonstrates Talon's routed MCP enforcement, **not** proof of an isolated AI workload. For the no-bypass claim, use the Docker scenario above. Seed once before starting the HR and aggregate services. To regenerate, run `python warehouse.py seed --force` while both services are stopped. Override the database location with `HR_DEMO_DB_PATH` in all processes, if necessary.

**Manual-mode warning:** These are separate shell sessions. Environment variables and a Python virtual environment activated in Terminal 1 **do not automatically propagate** to Terminals 2–4. The setup below repeats the relevant exports. For a prospective customer meeting, the Docker runbook is strongly preferred because it tests the non-bypass perimeter.

**Terminal 1 — synthetic HR MCP source**

~~~bash
cd ~/demos/talon-full-demo-hr
source .venv/bin/activate
cd cases/people-analytics-copilot
python demo.py hr
# listening on 127.0.0.1:9091
~~~

**Terminal 2 — real Talon MCP (leave the shell open for verification)**

~~~bash
export DEMO_DIR="$HOME/demos/talon-full-demo-hr/cases/people-analytics-copilot"
export TALON_BIN="$(command -v talon)"
export TALON_DATA_DIR="$(mktemp -d)"
export TALON_SECRETS_KEY="$(openssl rand -hex 32)"
export TALON_SIGNING_KEY="$(openssl rand -hex 32)"
export TALON_ADMIN_KEY="$(openssl rand -hex 24)"

cd "$TALON_DATA_DIR"
"$TALON_BIN" init --scaffold --name hr-analytics-assistant
cp "$DEMO_DIR/agent.talon.yaml" "$TALON_DATA_DIR/agent.talon.yaml"
"$TALON_BIN" validate
"$TALON_BIN" secrets set hr-analytics-assistant-talon-key talon-hr-demo-key-0001

# Background process leaves this same shell free to run audit verification.
"$TALON_BIN" serve --host 127.0.0.1 --port 8080 \
  --proxy-config "$DEMO_DIR/proxy.talon.yaml" > "$TALON_DATA_DIR/talon.log" 2>&1 &
TALON_PID=$!
# Inspect errors without printing provider credentials.
tail -n 15 "$TALON_DATA_DIR/talon.log"
~~~

The scaffold initially permits sql_query and file_read; **agent.talon.yaml** replaces these with exactly three HR aggregate tools. Never skip this step. The static demo key is for isolated fictional data only. The init command may warn about no configured model provider; GUIDED MCP use does not require one.

**Terminal 3 — aggregate-only dashboard API**

~~~bash
cd ~/demos/talon-full-demo-hr
source .venv/bin/activate
cd cases/people-analytics-copilot
python demo.py dashboard
# listening on 127.0.0.1:9093
~~~

**Terminal 4 — browser application (GUIDED mode)**

~~~bash
cd ~/demos/talon-full-demo-hr
source .venv/bin/activate
cd cases/people-analytics-copilot
python demo.py ui
# listening on 127.0.0.1:8501
~~~

Open http://127.0.0.1:8501/ (use an SSH port-forward from a remote demo host, never a publicly exposed service).

**Verification — return to Terminal 2 (same Talon environment)**

~~~bash
cd ~/demos/talon-full-demo-hr
source .venv/bin/activate
cd cases/people-analytics-copilot
python verify.py --talon-bin "$TALON_BIN"
~~~

This script checks tool discovery, permitted aggregates, forbidden export, zero upstream export calls and Talon evidence signatures. It requires the *original* TALON_DATA_DIR, TALON_SECRETS_KEY and TALON_SIGNING_KEY from Terminal 2; a new SSH session will not have them automatically. When finished, stop the Talon subprocess with kill "$TALON_PID" **in Terminal 2**. Other terminal services stop using Ctrl+C.

## Real AI assistant — provider-backed mode

**Opt-in:** run the separately configured LLM gateway with an OpenAI credential. Before a customer presentation, use the self-contained paid real-provider smoke below rather than assuming a provider call will work. The Docker launcher also supports LIVE mode.

For the manual setup, in **Terminal 2**, while its Talon environment is still present:

~~~bash
# Read the key privately rather than putting it in shell command history.
read -rs -p "OpenAI API key: " OPENAI_API_KEY; echo
"$TALON_BIN" secrets set openai-api-key "$OPENAI_API_KEY"
unset OPENAI_API_KEY

cd "$TALON_DATA_DIR"
"$TALON_BIN" serve --host 127.0.0.1 --port 8082 --gateway \
  --gateway-config "$DEMO_DIR/gateway.talon.yaml" \
  > "$TALON_DATA_DIR/gateway.log" 2>&1 &
GATEWAY_PID=$!
~~~

Restart **Terminal 4** (Ctrl+C the current UI process first) with:

~~~bash
cd ~/demos/talon-full-demo-hr
source .venv/bin/activate
cd cases/people-analytics-copilot
export TALON_AI_MODE=live
export TALON_LLM_URL=http://127.0.0.1:8082/v1/proxy/openai/v1/chat/completions
export TALON_LLM_KEY=talon-hr-demo-key-0001
export TALON_LLM_MODEL=gpt-4o-mini
python demo.py ui
~~~

The gateway and MCP proxy share the same local Talon signing/vault state and agent bearer. If provider inference fails, the app **does not** bypass Talon to call OpenAI directly. To stop the manual gateway, return to Terminal 2 and run kill "$GATEWAY_PID". A provider key stored in Talon's vault must not be committed to the repository.

### Automated integration without paid LLM calls

~~~bash
# From the repository root; needs free loopback ports 8080, 8082, 9091, 9092.
bash scripts/test-people-analytics-talon.sh
~~~

This starts real Talon MCP + LLM gateways with a **deterministic fake upstream model**. It verifies the model-selected aggregate tool executes against DuckDB only through Talon, verifies the denied employee export never reaches upstream, and checks signed MCP evidence. **It does not prove that OpenAI/Anthropic's live model generated a good answer**; that requires a real provider key and a manual evaluation.

## Stronger before/after proof: isolated services (recommended for prospective customer)

The simple loopback run above demonstrates Talon governance, **not protection from direct backend bypass on the same Unix identity/network**. To prove isolation, use the optional Docker Compose topology instead. It starts separate HR, aggregate dashboard, AI UI, and Talon MCP services. Only Talon's MCP proxy joins the private HR network; the UI container has no DuckDB volume or backend network route.

From repository root (Docker Compose v2 and a compatible local Talon binary required):

~~~bash
bash scripts/people-analytics-isolated.sh up
bash scripts/people-analytics-isolated.sh verify
# Open http://127.0.0.1:8501 in a browser / SSH tunnel
bash scripts/people-analytics-isolated.sh down
~~~

The verifier deliberately performs a direct **privileged baseline call inside the HR service**, resets the counters, then executes the same unauthorized export through Talon from the isolated AI workload. It also checks that the UI has no DuckDB volume or route to the privileged backend. The backend must report zero post-reset export executions, and the session evidence must verify.

An explicitly separate aggregate-only HTTP endpoint serves charts; it never exposes raw SQL or employee records. **Network isolation is Docker's responsibility, not Talon's**. Neither the isolated topology nor the single-host topology constitutes production-grade HR IAM.

### Run against a real OpenAI provider

First stop any already running local demo processes using 8080, 8082, 9091, 9093 and 8501. Export your provider credential in a shell, without writing it into Git:

~~~bash
export OPENAI_API_KEY="your-real-provider-key"
bash scripts/test-people-analytics-real-provider.sh
~~~

This opt-in smoke starts real Talon LLM+MCP processes, exercises actual OpenAI tool calling using a bounded response, verifies backend operations and a single signed session. **It incurs provider fees** and has not been executed without an API key. Run it before presenting "real AI" to prospective customer. For live AI inside the isolated Docker topology, run the secure launcher with an exported key and the "live" action; the provider credential is passed into the Talon vault, not into the UI image.

Full 12–15 minute customer-facing script: [PEOPLE_ANALYTICS_DEMO_PLAN.md](PEOPLE_ANALYTICS_DEMO_PLAN.md).

## Two interfaces, one real seven-stage proof

The **Workforce dashboard** (http://127.0.0.1:8501) is the business application
and remains isolated from raw HR data. The **Presenter Proof Console**
(http://127.0.0.1:8502) is a separate operator-only web UI running on the
Docker host. It offers every granular BEFORE / RESET / topology / policy /
tool-discovery / allow / deny / counter / signature command as a clickable
action with **actual stdout, stderr and exit code**, plus a copyable terminal
equivalent. It does not fabricate receipts or run commands inside the agent.

~~~bash
# On Ubuntu after starting the isolated environment, in a separate shell:
bash scripts/people-analytics-isolated.sh presenter
# Copy the generated operator token from the host shell into the presenter UI.
~~~

To connect from a remote laptop, tunnel both ports:

~~~bash
ssh -N -L 8501:127.0.0.1:8501 -L 8502:127.0.0.1:8502 user@demo-host
~~~

You can switch between the UI and documented shell commands at any point.
The operator console has Docker authority, unlike the AI application; it
must remain localhost-only and is protected by a one-time access token.
**Never expose port 8502 publicly or give its token to the AI workload.**

See [PRESENTER_COMMANDS.md](PRESENTER_COMMANDS.md) for both interfaces and
the complete trust-building sequence.

For a trust-building **command-by-command** version showing raw HR backend output, an explicit instrumentation reset, Docker networks, separate authorized/denied MCP operations, independent backend counters and signed evidence, use [PRESENTER_COMMANDS.md](PRESENTER_COMMANDS.md). The CI job executes the same granular sequence.

## Troubleshooting and proof boundaries

| Symptom | What to inspect |
|---|---|
| Talon missing or incompatible | Check talon version. The CI tests use a pinned v1.15.3 release with MCP 2026-07-28 support |
| Docker Compose not found | Install Docker with the **Compose v2 plugin**, and check docker compose version |
| Ports occupied | Check the running containers and old host processes before launching the isolated stack; do not terminate unrelated processes |
| Assistant or dashboard unavailable | Run bash scripts/people-analytics-isolated.sh logs and docker compose ps; check the separate dashboard and Talon MCP service |
| UI shows GUIDED | Expected. The default assistant is deterministic, not an LLM; live mode requires a separately configured Talon LLM gateway and real provider key |
| Browser cannot display backend counters | Expected under Docker isolation: the browser does **not** have a direct route to the HR service. Inspect counters using the operator commands inside hr-server |
| Export count remains nonzero | Run the **explicit RESET step** after the privileged BEFORE call. Zero after the Talon deny means zero **since reset**, not zero over all time |
| No signed records | Verify the same session ID and Talon state/signing keys were used. A direct HR BEFORE request is **absent** from Talon evidence because it bypasses Talon |
| Configuration changed, but demo looks unchanged | Check the checkout branch and restart/rebuild the containers |
| Starting from scratch | The reset action removes the synthetic HR and Talon persistent volumes. This is destructive; use only for disposable demo state |
| Real-provider smoke fails | Confirm the correct OpenAI API key is supplied to Talon's vault, the gateway is running on the documented port and the model supports tool calling; check the gateway logs without exposing secrets |

**Do not overclaim:** Docker networks and mounts—not Talon—prevent direct HR bypass in the isolated topology. The HR backend enforces SQL parameterization and the cohort threshold. The operator-initiated denied export is not evidence that a real model attempted it. Signed Talon evidence only covers traffic Talon saw and is tamper-evident, not immutable. PII redaction is **disabled** in this scenario. No Workday integration, actual a customer access, production IAM, GDPR compliance or universal DLP guarantee is demonstrated.

**Follow-up work (not v1 claims):** More comprehensive PII/data-classification controls, provider egress/budget proof, production authentication and warehouse-scoped identities, and an optional Workday integration.

For the customer narrative, use [PEOPLE_ANALYTICS_DEMO_PLAN.md](PEOPLE_ANALYTICS_DEMO_PLAN.md). Choose [UI_PLAYBOOK.md](UI_PLAYBOOK.md) for a browser-led journey or [PRESENTER_COMMANDS.md](PRESENTER_COMMANDS.md) for terminal-led checks. Both produce the same real Talon evidence.

