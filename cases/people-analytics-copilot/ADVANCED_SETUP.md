# Advanced setup and LIVE model

Most presenters should use the **[Docker quickstart](README.md#get-started)** followed by the [browser](UI_PLAYBOOK.md) or [terminal](PRESENTER_COMMANDS.md) playbook. This page is for debugging Talon services and testing external model inference. It is **not required** for the default guided demonstration.

## Automated tests

From the repository root, with Python dependencies installed:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r cases/people-analytics-copilot/requirements.txt

make people-analytics-validate
bash scripts/test-people-analytics-talon.sh
~~~

The second command starts real Talon LLM/MCP processes but uses a **fake OpenAI-compatible provider**. It proves protocol routing and signed evidence, **not real model quality**. It uses loopback ports 8080, 8082, 9091, 9092 and 9093; stop conflicting services first.

## Standalone services without Docker

This method shares one Linux host's filesystem/network context and **does not prove that the AI app cannot bypass the HR service**. Use the Docker topology for isolation claims.

From the repository root, seed the synthetic warehouse first:

~~~bash
source .venv/bin/activate
make people-analytics-seed
export DEMO_DIR="$PWD/cases/people-analytics-copilot"
~~~

Open **four terminal sessions** on that host:

**Terminal 1 — private HR MCP service**

~~~bash
cd ~/demos/talon-full-demo-hr
source .venv/bin/activate
cd cases/people-analytics-copilot
python demo.py hr
# port 9091
~~~

**Terminal 2 — Talon MCP proxy and evidence state**

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
"$TALON_BIN" serve --host 127.0.0.1 --port 8080 \
  --proxy-config "$DEMO_DIR/proxy.talon.yaml" > "$TALON_DATA_DIR/talon.log" 2>&1 &
TALON_PID=$!
~~~

**Terminal 3 — aggregate-only dashboard service**

~~~bash
cd ~/demos/talon-full-demo-hr
source .venv/bin/activate
cd cases/people-analytics-copilot
python demo.py dashboard
# port 9093
~~~

**Terminal 4 — business UI in GUIDED mode**

~~~bash
cd ~/demos/talon-full-demo-hr
source .venv/bin/activate
cd cases/people-analytics-copilot
python demo.py ui
# port 8501
~~~

To validate the **Talon MCP** contract, return to **Terminal 2**, which still has the signing and data-directory environment:

~~~bash
cd ~/demos/talon-full-demo-hr
source .venv/bin/activate
cd cases/people-analytics-copilot
python verify.py --talon-bin "$TALON_BIN"
~~~

Do not open a fresh SSH shell for the audit command without also restoring the **same** Talon environment. When finished, stop the HR/dashboard/UI foreground processes with Ctrl+C; in Terminal 2 run `kill "$TALON_PID"`.

## Technical tracing and live logs

The operator console on `127.0.0.1:8502` has an authenticated, **allowlisted** log viewer (Talon MCP, optional Talon LLM gateway, init, UI, HR service and dashboard). It polls bounded Docker log snapshots; it cannot run arbitrary Docker commands. The UI's request/response trace comes from the **actual app boundary**, not a packet capture of provider HTTPS and not a simulated provider.

In LIVE mode, the `ui` service logs `HR_AI_TRACE` metadata for each outbound Talon LLM gateway request and returned response, including the session, model, provider response ID, usage, tool calls and signed MCP decision. The Talon LLM gateway's own logs are shown separately.

For a synthetic fixture **only**, start LIVE with explicit, redacted body previews:

~~~bash
HR_DEMO_TRACE_PAYLOADS=1 bash scripts/people-analytics-isolated.sh live
~~~

Default `HR_DEMO_TRACE_PAYLOADS=0` logs only safe metadata. Never enable body previews for production HR, credentials, private prompts or customer datasets. API authorization headers are not traced. Docker operators may still read container logs.

## Optional: test a real external model

**Provider calls can incur charges.** The following path has a separately configured Talon LLM gateway and requires a working OpenAI API credential. It is **opt-in**, not part of regular PR CI. Use a disposable provider key on a trusted host with fictional HR data only.

### Independent paid smoke (recommended first)

Stop any conflicting loopback demo services on ports 8080, 8082, 9091, 9092 or 9093. From the repository root:

~~~bash
read -rs -p "OpenAI API key: " OPENAI_API_KEY; echo
export OPENAI_API_KEY
bash scripts/test-people-analytics-real-provider.sh
unset OPENAI_API_KEY
~~~

This runs real Talon gateways and tests whether the external model selects an approved tool, receives the DuckDB aggregate, returns an answer, and produces verifiable signed evidence. **Do not claim the live path works until this test passes in the intended environment.**

### Enable LIVE in the Docker dashboard

Start the isolated stack first, then:

~~~bash
read -rs -p "OpenAI API key: " OPENAI_API_KEY; echo
export OPENAI_API_KEY
bash scripts/people-analytics-isolated.sh live
unset OPENAI_API_KEY
~~~

Reload the business UI on port 8501. The mode should display **LIVE AI · TALON**. The operator console and the Docker privacy boundary remain separate.

The launcher temporarily passes the provider credential in an environment variable to Talon's initialization container before storing it in Talon's vault. This is acceptable only on a trusted synthetic demo host: privileged Docker users can potentially inspect container environments. Never use the convenience setup with production HR data.

### LIVE with the four-terminal setup

In **Terminal 2**, while its original Talon environment is still present:

~~~bash
read -rs -p "OpenAI API key: " OPENAI_API_KEY; echo
"$TALON_BIN" secrets set openai-api-key "$OPENAI_API_KEY"
unset OPENAI_API_KEY
cd "$TALON_DATA_DIR"
"$TALON_BIN" serve --host 127.0.0.1 --port 8082 --gateway \
  --gateway-config "$DEMO_DIR/gateway.talon.yaml" > "$TALON_DATA_DIR/gateway.log" 2>&1 &
GATEWAY_PID=$!
~~~

Restart **Terminal 4** with the following environment:

~~~bash
export TALON_AI_MODE=live
export TALON_LLM_URL=http://127.0.0.1:8082/v1/proxy/openai/v1/chat/completions
export TALON_LLM_KEY=talon-hr-demo-key-0001
export TALON_LLM_MODEL=gpt-4o-mini
python demo.py ui
~~~

If the gateway fails, the app does **not** fall back to direct provider access. To stop the gateway, return to Terminal 2 and run `kill "$GATEWAY_PID"`.

## Troubleshooting

| Problem | Check |
|---|---|
| `talon` or Docker Compose missing | `talon version` and `docker compose version`; Talon CI is pinned to its reviewed released version |
| Ports already in use | Stop stale demo services before launching. Don't kill unrelated services |
| Browser reports missing counters | Expected under Docker isolation; counters are available **inside hr-server** or through the authenticated operator console |
| Export counter is nonzero | In a step-by-step demo, run the explicit **RESET** stage; zero means zero **since reset** |
| Guided assistant doesn't generate freeform AI text | Expected: GUIDED means **no LLM** |
| Missing audit records | Use the correct `hr-demo-presenter` session and the same Talon state/signing environment |
| Live-provider failure | Check gateway/provider logs and credentials without displaying secrets; do not substitute mock output |

For exactly what the automated checks cover, see the [CI acceptance matrix](CI_COVERAGE.md).
