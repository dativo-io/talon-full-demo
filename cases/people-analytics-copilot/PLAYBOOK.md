# People Analytics — run the complete demo

This is the **operator playbook** for the synthetic Workforce app + Talon.
Follow it top to bottom on a **Linux host**. It always builds **current
[dativo-io/talon main](https://github.com/dativo-io/talon/tree/main)** when
you prepare the demo, records the resolved revision, and tests the real
governed MCP route. There is **no fixed commit to check out**.

Requirements: Git, Go compatible with Talon's current `go.mod`, Docker
with Compose v2, OpenSSL, and a free Docker host. Python 3 is needed only
for the optional automated tests. No OpenAI key is required for the default
GUIDED demo. All HR employee records are fictional.

## 1. Get the demo and Talon

From an Ubuntu terminal:

```bash
mkdir -p ~/src
cd ~/src
if [ ! -d talon-full-demo/.git ]; then
  git clone https://github.com/dativo-io/talon-full-demo.git
fi
cd talon-full-demo
git pull --ff-only origin main
cd cases/people-analytics-copilot
bash ../../scripts/prepare-people-analytics-talon.sh
export HR_DEMO_TALON_BIN="$(realpath ../../.state/talon-bin/talon)"
```

**Already cloned?** The clone step is skipped automatically.
**Already running the demo?** Keep `.env` and `.state/talon/` untouched.
The build helper fetches Talon `main`, compiles it and confirms the executable
matches that checkout. Run it again when you want to update Talon. The
specific SHA is printed for troubleshooting, not baked into this playbook.

Every command below runs from `cases/people-analytics-copilot`.
In a **new terminal**, export `HR_DEMO_TALON_BIN` again before using Compose.

## 2. Prepare local state once

```bash
# Use the original keys if reusing an existing installation.
if [ ! -f .env ]; then
  if [ -e .state/talon/secrets.db ] || [ -e .state/talon/evidence.db ]; then
    echo "Existing Talon state found: recover its original .env first." >&2
    exit 1
  fi
  umask 077
  printf 'HR_DEMO_SECRETS_KEY=%s\nHR_DEMO_SIGNING_KEY=%s\nHR_DEMO_ADMIN_KEY=%s\nHR_DEMO_UID=%s\nHR_DEMO_GID=%s\n' \
    "$(openssl rand -hex 32)" "$(openssl rand -hex 32)" \
    "$(openssl rand -hex 24)" "$(id -u)" "$(id -g)" > .env
fi

mkdir -p .state/talon .state/policy
if [ ! -f .state/policy/gateway.talon.yaml ]; then
  cp gateway.talon.yaml .state/policy/gateway.talon.yaml
fi
docker compose -f compose.isolated.yaml up --build -d seed hr-server dashboard
```

Initialize Talon **only if this installation has no agent policy**:

```bash
if [ ! -f .state/talon/agent.talon.yaml ]; then
  docker compose -f compose.isolated.yaml run --rm talon-cli \
    talon init --scaffold --name hr-analytics-assistant
  cp agent.talon.yaml .state/talon/agent.talon.yaml
fi

# Disposable synthetic demo key; not a production tenant credential.
docker compose -f compose.isolated.yaml run --rm talon-cli \
  talon secrets set hr-analytics-assistant-talon-key talon-hr-demo-key-0001
docker compose -f compose.isolated.yaml run --rm talon-cli talon validate
```

Validation must succeed. Do **not** delete `read_only`, regenerate vault
keys, rerun `init --force`, or remove persistent state to resolve a binary
compatibility error.

## 3. Start GUIDED mode — no paid model

```bash
# If an old LIVE gateway is crash-looping, stop just that process.
docker compose -f compose.isolated.yaml stop talon-gateway || true
docker compose -f compose.isolated.yaml --profile operator up --build -d \
  talon-mcp ui talon-ui

docker compose -f compose.isolated.yaml --profile operator ps
docker compose -f compose.isolated.yaml logs --tail=30 talon-mcp ui
```

Open the **Workforce app** at `http://127.0.0.1:8501/` on the server.
If Ubuntu is remote, create a local SSH tunnel from your **laptop**:

```bash
ssh -L 8501:127.0.0.1:8501 -L 8787:127.0.0.1:8787 USER@SERVER_IP
```

Then visit `http://127.0.0.1:8501/` on your laptop. The chart data and
governed MCP policy are real; GUIDED assistant wording is deterministic and
**does not invoke a paid LLM**.

## 4. Exercise the three governance outcomes

In the Workforce app, keep the same displayed session ID as you:

1. Run **All employees / department distribution** from the SQL workspace:
   a reviewed aggregate succeeds via `hr_aggregate_sql`.
2. Click **Request individual employee records**: Talon denies the
   forbidden `hr_employee_export` tool **before HR dispatch**.
3. Enter an employee-level SQL request using the allowed SQL tool: the
   **HR validator rejects it after Talon allows dispatch**. Talon's recorded
   upstream outcome is **unknown**, not a Talon policy denial.

The fixed workforce charts use a separate read-only data path; don't claim
Talon governs those chart requests. Compare signed Talon receipts with
independent HR counters:

```bash
docker compose -f compose.isolated.yaml exec -T hr-server \
  python3 verify_isolation.py counters
docker compose -f compose.isolated.yaml run --rm talon-cli talon audit list
```

Copy the actual `hr-demo-...` session ID from the Workforce app:

```bash
SESSION_ID='hr-demo-PASTE-YOUR-ID'
docker compose -f compose.isolated.yaml run --rm talon-cli \
  talon audit list --session "$SESSION_ID"
docker compose -f compose.isolated.yaml run --rm talon-cli \
  talon audit verify --session "$SESSION_ID"
docker compose -f compose.isolated.yaml run --rm talon-cli \
  talon costs --session "$SESSION_ID" --json
```

GUIDED mode has no model spend. A signed denial plus no HR dispatch is the
tool-governance proof; the SQL rejection proves **defense in depth**.

## 5. Pair the read-only Talon Operations Console

```bash
docker compose -f compose.isolated.yaml --profile operator ps talon-ui
docker compose -f compose.isolated.yaml --profile operator exec -T \
  talon-ui talon ui pair
docker compose -f compose.isolated.yaml --profile operator \
  logs --no-color --tail=30 talon-ui
```

The **last command** contains the actual
`Talon console pairing code: XXXXX-XXXXX-XXXXX-XXXXX`.
`talon ui pair` itself prints only an acknowledgement. Codes are single-use,
expire within 10 minutes and must not be pasted into tickets or screenshots.
Open `http://127.0.0.1:8787/` (through the SSH tunnel for remote hosts),
enter the real code, and explore **AI Use Cases → hr-analytics-assistant**,
**Sessions → your session**, **Evidence** and **System**.

The Console is read-only; it doesn't authorize or execute HR operations.

## 6. Optional LIVE mode with an actual model

Only do this when you want real model calls and have a disposable provider key.
Store an OpenAI key in Talon's encrypted vault using the operator CLI (the
command-line argument may be visible to Docker administrators/process viewers;
avoid using production credentials here):

```bash
read -rsp 'Disposable OpenAI key: ' OPENAI_API_KEY; echo
docker compose -f compose.isolated.yaml run --rm talon-cli \
  talon secrets set openai-api-key "$OPENAI_API_KEY"
unset OPENAI_API_KEY

# Preserve state; start the existing policy's model gateway and recreate the app.
docker compose -f compose.isolated.yaml --profile live up -d talon-gateway
HR_DEMO_AI_MODE=live docker compose -f compose.isolated.yaml \
  --profile live up --force-recreate -d ui
docker compose -f compose.isolated.yaml --profile live \
  logs --tail=30 talon-gateway
```

The Workforce app now routes model requests through the Talon LLM gateway
subject to its configured policy and provider availability. A successful
gateway start is **not proof of successful provider inference**: confirm an
actual response and usage/cost evidence for that session.

To return to GUIDED mode:

```bash
docker compose -f compose.isolated.yaml stop talon-gateway
HR_DEMO_AI_MODE=guided docker compose -f compose.isolated.yaml \
  up --no-deps --force-recreate -d ui
```

## 7. Shut down safely

```bash
docker compose -f compose.isolated.yaml --profile live --profile operator down
```

This stops containers while keeping `.env`, `.state/talon`, and the
synthetic DuckDB volume. **Do not use `down -v` or delete `.state`** unless
you explicitly want a reset and have backed up the demo state.

## Recover safely after a Docker/network restart

**Use this only for an already-initialized demo.** In this Compose topology,
`hr-mcp-net` owns the network namespace used by `hr-server`, `talon-mcp`,
and optional `talon-gateway`. Rebuilding or recreating only the network owner
while Talon is running can leave the Talon containers referencing a removed
namespace. A subsequent `docker compose restart talon-mcp` can fail with
`joining network namespace of container: No such container` even though
individual containers previously appeared healthy.

From `cases/people-analytics-copilot` on the **Linux Docker host**:

```bash
# Use the previously built, source-verified Talon executable.
export HR_DEMO_TALON_BIN="$(realpath ../../.state/talon-bin/talon)"
export HR_DEMO_AI_MODE=guided
test -x "$HR_DEMO_TALON_BIN"

# Stop the whole topology together; no -v (keep named DuckDB volume).
docker compose -f compose.isolated.yaml \
  --profile live --profile operator down

# Restore GUIDED mode from the existing images, with one coherent network.
docker compose -f compose.isolated.yaml \
  --profile operator up --no-build -d \
  hr-mcp-net hr-server dashboard talon-mcp ui talon-ui

# Wait for dependencies and verify the private HR listener from its namespace.
docker compose -f compose.isolated.yaml --profile operator ps
docker compose -f compose.isolated.yaml exec -T hr-server \
  python3 -c "from urllib.request import urlopen; print(urlopen('http://127.0.0.1:9091/debug/counters', timeout=5).status)"

# This uses GET. The Workforce example does not promise to implement HEAD.
curl --fail --silent --show-error --output /dev/null \
  --write-out 'Workforce HTTP %{http_code}\n' http://127.0.0.1:8501/
```

Expected: HR returns `200`, Workforce returns `200`, and the relevant
containers stay up. `down` without `-v` interrupts running requests but keeps
the persisted `.env`, `.state/talon` vault/evidence and named DuckDB volume.
Never run `down -v`, `init --force` or regenerate signing/vault keys to repair
a container network. Do **not** repeatedly `up --build` only `hr-mcp-net` or
`hr-server` while the dependent Talon containers are running. If an image
has not yet been built, first stop the full topology as above, then build
and start **all** its dependent services together instead of a subset.

**Verify both HTTP paths, not just the Workforce home page:**

```bash
# From the UI container: can the Workforce app reach its separate chart service?
docker compose -f compose.isolated.yaml exec -T ui \
  python3 -c "from urllib.request import urlopen; print('Dashboard HTTP', urlopen('http://dashboard:9093/api/dashboard', timeout=5).status)"

# From the Docker host: what mode was actually loaded, and do charts render?
curl --fail --silent --show-error http://127.0.0.1:8501/api/mode
curl --fail --silent --show-error --output /dev/null \
  --write-out 'Charts HTTP %{http_code}\n' http://127.0.0.1:8501/charts
```

GUIDED mode should report `"mode": "guided"`, with both dashboard and
charts reporting HTTP `200`. Click **Ask assistant** and confirm a
deterministic aggregate result with a committed Talon MCP receipt; a
separate employee-export request must still be denied before dispatch.
If the dashboard is down, inspect `docker compose -f compose.isolated.yaml
logs --tail=80 dashboard ui`; the browser UI being reachable on `8501`
does not demonstrate that its chart dependency on `dashboard:9093` is
reachable. Do not claim the demo is healthy because only Talon's MCP path
works.

**Recover LIVE mode instead (optional):** use this only when you already
have a disposable provider key saved under `openai-api-key` in this
installation's encrypted vault; otherwise follow step 6 to set it.
Recreate the whole namespace rather than starting a stale gateway alone:

```bash
export HR_DEMO_TALON_BIN="$(realpath ../../.state/talon-bin/talon)"
export HR_DEMO_AI_MODE=live

docker compose -f compose.isolated.yaml \
  --profile live --profile operator down
docker compose -f compose.isolated.yaml \
  --profile live --profile operator up --no-build -d \
  hr-mcp-net hr-server dashboard talon-mcp talon-gateway ui talon-ui

docker compose -f compose.isolated.yaml exec -T ui \
  python3 -c "from urllib.request import urlopen; print('Gateway HTTP', urlopen('http://talon-gateway:8082/health', timeout=5).status)"
curl --fail --silent --show-error http://127.0.0.1:8501/api/mode
docker compose -f compose.isolated.yaml --profile live logs --tail=60 \
  hr-server dashboard talon-mcp talon-gateway ui
```

Expect a gateway HTTP `200` and `"mode": "live"`. **Neither establishes
a successful provider request**: test **Ask assistant** and verify actual
provider response and signed cost/usage for that session. If it reports
`Talon LLM gateway is unreachable`, distinguish network failure from
provider/authentication failure using the `ui` and `talon-gateway` logs.
A later `agent_config_reload_rejected_keeping_last_known_good` with
`127.0.0.1:9091: connect refused` means the HR action source was
unavailable to the gateway at reload time. Check
`hr-server` health and its shared network namespace; do not loosen
agent policy or reset the vault to clear the warning.

See [operational readiness issue #62](https://github.com/dativo-io/talon-full-demo/issues/62)
for the remaining fail-visible UI/startup improvements. The recipes above
repair a running demo; they are not proof of a persistent published-release
customer deployment.

**Remote laptop:** the Workforce app is bound to the **Docker host's**
`127.0.0.1:8501`; the Console is bound to `127.0.0.1:8787`.
HTTP `200` when curling on the host does not imply the URL is reachable
from your laptop. From the **laptop**, tunnel both:

```bash
ssh -N -L 8501:127.0.0.1:8501 -L 8787:127.0.0.1:8787 USER@SERVER_IP
```

Then open `http://127.0.0.1:8501/` and `http://127.0.0.1:8787/` on
the laptop. If the Console works but the Workforce app does not, check that
port `8501` is included in the tunnel and that no local process owns it.

**Console readiness:** GUIDED mode intentionally does **not** start the
optional LIVE LLM gateway. A prior graceful shutdown may remain visible as
an `LLM gateway is offline` runtime fact in the Console; do not mistake this
for a fresh model call failure or claim that LIVE inference works. If
**Configuration activation** is still degraded, inspect the current finding
and `docker compose ... logs hr-server talon-mcp`; an old rejected
configuration is not evidence that the current active policy is healthy.
Verify the MCP route and three outcomes in step 4 before presenting.
For a LIVE run, follow step 6 and separately verify actual provider traffic.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| `scripts/prepare-people-analytics-talon.sh: No such file` | You are in the case directory. Use `../../scripts/prepare-people-analytics-talon.sh`. |
| `read_only: Additional property ...` | Wrong Talon binary: rebuild current main with step 1, export `HR_DEMO_TALON_BIN`, recreate affected Talon containers. Do not edit the policy. |
| `talon-gateway ... 127.0.0.1:9091 connect refused` | Update Full Demo `main` and recreate gateway; the gateway must share the HR network namespace. Confirm `hr-server` is healthy. |
| `talon-ui` displays no pairing code | Read `docker compose ... logs talon-ui`; `up -d` never displays the code. If needed, run `talon ui pair` **inside** `talon-ui`, then read the logs again. |
| `llm_keys: No LLM provider configured` | Expected in GUIDED mode; LIVE mode needs a provider key. |
| `cipher: message authentication failed` | The current vault and `.env` don't match. Recover the original keys; do not regenerate over existing evidence. |

## Automated verification (optional)

From the **Full Demo root**, after stopping the demo in step 7 and installing the case's Python requirements:

```bash
python3 -m pip install -r cases/people-analytics-copilot/requirements.txt
PATH="$PWD/.state/talon-bin:$PATH" bash scripts/test-people-analytics-talon.sh
```

The test uses disposable synthetic state; it does not validate a published
Talon release. CI checks out current core `main` separately and runs
the isolated Compose and paired-browser tests. The resolved core source SHA
is recorded on each CI run so a regression can be reproduced.

For architecture, detailed security boundaries, and historical compatibility
evidence, see [the technical notes](README.md). For the shared four-use-case
fleet see the [repository overview](../../README.md).
