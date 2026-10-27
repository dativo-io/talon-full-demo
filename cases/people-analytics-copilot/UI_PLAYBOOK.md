# Browser playbook

**Best for:** business stakeholders and anyone who prefers a visual walkthrough. This guide and the [terminal playbook](PRESENTER_COMMANDS.md) operate on the **same synthetic data, Talon policy, and signed evidence**.

## 1. Start the two web apps

From the checked-out demo repository on your trusted Ubuntu host:

~~~bash
bash scripts/people-analytics-isolated.sh up
~~~

In a **second host terminal**, start the separately authenticated operator console:

~~~bash
bash scripts/people-analytics-isolated.sh presenter
~~~

It prints a **one-time token**. Keep the token private; the operator console has Docker privileges and must never be exposed publicly.

Open two browser tabs:

| URL | What you use it for |
|---|---|
| **http://127.0.0.1:8501** | Workforce Intelligence dashboard + guided assistant |
| **http://127.0.0.1:8502** | Operator Proof Console: privileged BEFORE, isolation checks, Talon evidence |

On a remote host, forward both loopback ports from your laptop:

~~~bash
ssh -N -L 8501:127.0.0.1:8501 -L 8502:127.0.0.1:8502 user@demo-host
~~~

## 2. Show useful analytics first

In the **Workforce Intelligence** tab:

1. Filter by department; watch the headcount, attrition and tenure charts change. Charts use a **fixed aggregate API**, not Talon.
2. Ask: *Which departments have the highest attrition over the last six months?*
3. Show the actual **Talon allow receipt** for the aggregate tool call.
4. Point out the mode: **GUIDED · NO LLM**. The statistics are calculated by DuckDB; the answer wording is deterministic.

The browser app has **no raw HR database mount or direct private HR connection**. Its counter panel therefore cannot independently read the HR backend—use the operator console for that proof.

## 3. Unlock the operator console

In the **Operator Proof Console** tab, paste the one-time token from the trusted host terminal and select **Unlock**.

The screen guides you through seven stages. Each check has **Run check**, **View exact terminal command**, **Copy command**, and the **actual exit code/stdout/stderr**. Nothing runs automatically. BEFORE and RESET require confirmation.

Work through the stages **in order**:

| Stage | Click and show | Expected result |
|---|---|---|
| **1. Direct access** | Execute privileged synthetic employee export; inspect independent HR counter | An employee name/salary appears; export counter rises. The request **bypasses Talon** |
| **2. Reset measurement** | Explicitly reset HR counters | Counters return to zero. **Permissions did not change** |
| **3. Deployment isolation** | View UI/Talon/HR networks and UI mounts; test restricted app connectivity | AI UI has **no DuckDB mount or direct HR route**. Dashboard still works |
| **4. Tool policy** | Inspect agent and proxy policy; discover tools | Only headcount, attrition and tenure aggregate tools are offered |
| **5. Allow** | Execute aggregate HR tool | DuckDB summary returned; `decision=allow` and committed evidence |
| **6. Deny** | Force employee export through Talon; inspect independent HR counter | `decision=deny`, `not_dispatched`; backend export counter is **zero since reset** |
| **7. Verify** | Export signed presenter session; verify signatures | No invalid or unsigned evidence records |

The UI progress indicator counts successful command exits in **this browser tab**. It is not a security audit result; Stage 7 verifies the actual signed records.

**Do not mix** the seven-stage sequence with `bash scripts/people-analytics-isolated.sh verify`; that command performs another baseline and reset.

## 4. Close with the proof, not a green badge

Show three independent observations:

- **Network/volume evidence:** the AI app cannot bypass the private HR service. **Docker** enforces this.
- **Policy and MCP receipts:** Talon offers three aggregate tools, permits an approved call and denies employee export **before dispatch**.
- **Backend counter + signed session:** the HR service reports zero export executions **since Stage 2**; Talon's evidence verifies.

A separate operator **forced** the forbidden call. A real LLM did not attempt it autonomously. The successful BEFORE direct call is **not** in Talon evidence—it never traversed Talon.

## 5. Optional LIVE model

For genuine model-generated analysis, first run the **billable external-provider smoke test** and enable LIVE mode using [Advanced setup](ADVANCED_SETUP.md#optional-test-a-real-external-model). The UI should then say **LIVE AI · TALON**. The default GUIDED mode and the fake-provider integration test are **not real LLM inference**.

## Troubleshooting and shutdown

| If… | Do this |
|---|---|
| Operator console says **Locked** | Paste the token from its host terminal; verify the SSH tunnel includes port 8502 |
| A check fails | Expand raw stderr; copy the exact command and retry via the [terminal playbook](PRESENTER_COMMANDS.md) |
| Backend counter is already nonzero | Do the deliberate Stage 2 reset, then rerun only the AFTER stages |
| Dashboard is unavailable | Run `bash scripts/people-analytics-isolated.sh logs` on the host |
| The progress indicator resets | Expected after refreshing; Talon's signed records remain on the demo state volume |

Stop the operator console with **Ctrl+C** in its terminal. Stop containers:

~~~bash
bash scripts/people-analytics-isolated.sh down
~~~

The `reset` action is different: it **deletes synthetic DuckDB and Talon demo volumes**.

For the timed story, use the [15-minute presentation plan](PEOPLE_ANALYTICS_DEMO_PLAN.md). For direct access to every command, use the [terminal playbook](PRESENTER_COMMANDS.md).
