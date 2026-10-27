# People Analytics — 15-minute demonstration plan

## One-sentence story

**The HR warehouse is already governed. Talon governs which operations an AI use case may perform, and records verifiable evidence of what it actually did.**

The scenario uses 1,200 **fictional** employee records in DuckDB. The goal is to show useful aggregate analytics alongside preventive tool restrictions—not to replace warehouse access control.

## Before and after: two different workloads

~~~mermaid
flowchart LR
    subgraph BEFORE["BEFORE · privileged HR process"]
        P["Trusted HR operator"] -->|"Direct employee export"| H1["HR backend"]
        H1 -->|"Fictional salary rows"| P
    end
    subgraph AFTER["AFTER · isolated AI app"]
        A["AI app<br/>no HR database/route"] -->|"Approved tools"| T["Talon MCP"]
        T -->|"Aggregate only"| H2["Private HR backend"]
        A -. "Direct access blocked by Docker" .-> H2
        T -. "Employee export denied" .-> H2
    end
~~~

**Not a runtime switch:** we don't toggle Talon or migrate one running agent. The BEFORE call executes *directly* inside the privileged HR service and succeeds without Talon. We then **reset counters only**, and test a separate AI workload isolated by Docker networking and mounts. Talon enforces the permitted/denied operations routed through its proxy.

## Choose your presentation surface

- **[Browser-first](UI_PLAYBOOK.md):** workforce dashboard on 8501, authenticated operator proof console on 8502. Click through seven stages while showing actual command output.
- **[Terminal-first](PRESENTER_COMMANDS.md):** run the same seven stages as Docker/Talon commands, inspect original receipts and signatures.
- **[Quickstart and architecture](README.md):** shortest setup instructions and the full control-boundary diagram.

**Default mode: GUIDED · NO LLM.** Metrics and Talon calls are real; the assistant's wording is deterministic. A real provider is optional only after the [paid smoke test](ADVANCED_SETUP.md#optional-test-a-real-external-model) succeeds.

## Talk track

| Time | On screen | Explain |
|---|---|---|
| **0–2 min** | Workforce dashboard with department filter | Realistic, aggregate workforce analysis from fictional DuckDB data |
| **2–4 min** | **BEFORE** direct employee export and its backend counter | Broad service privileges are risky *if inherited by an AI workload*. Talon did not see this direct call |
| **4–6 min** | Explicit **RESET**, then Docker networks and mounts | Measurement starts from zero; the AI app cannot bypass the private HR service through its deployment |
| **6–9 min** | Talon discovery and permitted attrition analysis | Only three aggregate tools; the permitted operation returns a committed allow receipt |
| **9–11 min** | Forced `hr_employee_export` request and independent backend counter | Talon denies the request **before dispatch**; HR reports zero export executions **since reset** |
| **11–13 min** | Signed session export and CLI verification | Validate what Talon saw; no record exists for the earlier direct bypass |
| **13–15 min** | Architecture and boundaries | Identify one candidate AI use case whose direct warehouse access can be narrowed |

The operator export probe is **not** proof that a model spontaneously attempted an unsafe action. The demo also does not prove causal explanations for attrition trends.

## The two trust mechanisms

| Question | Real mechanism | Evidence |
|---|---|---|
| Can the AI app bypass the HR backend? | Docker private network + no DB mount | Network and mount inspection, failed direct connection |
| Can the AI agent invoke forbidden tools? | Talon MCP tool policy | Filtered discovery, committed denial, zero upstream export calls |
| Was permitted analytics actually executed? | HR aggregate service behind Talon | Returned DuckDB metrics and independent tool execution counter |
| Can the session be independently checked? | Talon signed audit | Exported session; signature verification by Talon CLI |

The fixed aggregate dashboard API is **separate from Talon**; ordinary chart reads aren't AI operations.

## Presentation checklist

- Use a trusted host with Docker Compose v2, OpenSSL and a compatible Talon build.
- Run `bash scripts/people-analytics-isolated.sh up`; rehearse with `verify`, but **don't run the combined verifier mid-presentation** because it includes a reset.
- If presenting in the browser, start `bash scripts/people-analytics-isolated.sh presenter` on the host, and use private SSH port forwarding. Never publish port 8502 or reveal its operator token.
- Explicitly reset instrumentation after the BEFORE export. Then run discovery, allow, deny, backend counters and signed audit in one presenter sequence.
- Only label an answer **LIVE AI** after the opt-in real-provider smoke succeeds; normal CI uses a fake upstream model for LLM protocol testing.

## What we are not claiming

No real employee data, no production HR platform integration, no production IAM/row-level authorization, no comprehensive PII/DLP protection, and no privacy-law certification. PII redaction is disabled in this scenario. The privileged HR backend retains access to its database; Docker isolates the AI workload from it. **Talon cannot control direct paths that bypass Talon.**

The demo is a basis for a scoped customer pilot, not a finished HR security architecture.
