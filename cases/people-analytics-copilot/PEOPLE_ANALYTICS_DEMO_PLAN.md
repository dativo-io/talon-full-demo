# People Analytics — updated demonstration plan

**Purpose:** Show how an already-governed HR warehouse can be exposed to AI with narrower runtime permissions, verified execution and consistent use-case identity. Talon does not replace existing HR platform permissions, warehouse RBAC, or network segmentation.

**Buyer hypothesis:** the customer's People Analytics organization has governed HR data, but some AI use cases operate under service identities broader than they require. Leadership needs evidence that agents cannot freely retrieve employees' private records, and wants accountability for the models and operations they use. We have not connected to his real environment.

## Before and after

BEFORE — legacy-style broad privileges: a privileged HR process calls the synthetic backend directly and receives individual employee names and salary records. Talon does not see or stop this path.

AFTER — a separated browser and AI application has no DuckDB volume and no route to the private HR backend. It can request safe dashboard aggregates and talk to Talon's LLM/MCP processes. The MCP proxy alone bridges into the private HR network. Talon offers only three aggregate tools (attrition, headcount and tenure), refuses the employee export, and produces signed evidence.

The **container network / missing DuckDB mount** prevents the browser/agent from accessing raw HR data directly. That is a **deployment boundary, not Talon enforcement**. Talon governs routed model and tool requests. The HR backend enforces parameterized SQL and minimum reporting cohorts. The fixed aggregate dashboard service does not expose arbitrary SQL.

The "before" is an operator executing a direct call *inside the privileged HR container*. It illustrates what an agent with inherited broad credentials could do; it does not claim an actual Grab or Workday agent had those privileges.

## Presenter track: choose honestly

- **No provider key (fully CI-tested):** run the isolated GUIDED scenario. The seven granular commands demonstrate the actual backend, Docker isolation, Talon MCP allow/deny, counters and signatures. The assistant is **not** real AI inference. The credential-free *separate* LLM protocol test uses a fake upstream model.
- **Real AI track (opt-in):** **first** pass the external-provider smoke using an actual OpenAI credential; then start the isolated stack in LIVE mode. Real model-generated analysis is a valuable extra scene, but is **not an already-passed CI guarantee**. If any provider step fails, switch back to the guided track and explicitly label it.

Use [PRESENTER_COMMANDS.md](PRESENTER_COMMANDS.md) for the full command-by-command procedure. **BEFORE/AFTER is a comparison of two workloads, not a runtime switch or an agent migration.** Resetting the mock counters never changes privileges.

## Updated 12–15 minute customer walkthrough

| Time | What prospective customer sees | Why it matters |
|---|---|---|
| 0–2 min | Synthetic workforce dashboard with real DuckDB aggregate metrics | Existing HR analytics remains useful and governed, Talon is not a data platform replacement |
| 2–4 min | BEFORE: deliberate direct employee export from a privileged backend process (fictional names and salaries) | Shows the cost of broad service-account privileges when inherited by an AI runtime |
| 4–6 min | AFTER: prove AI app has no database file and cannot reach HR private service; dashboard aggregate still works | Revoked bypass is enforced by network and deployment isolation |
| 6–9 min | Ask: "Which department has highest attrition for September 2026? Compare six months, don't invent causes." In **LIVE** mode, use a real provider only after the smoke passes; otherwise use the transparently labelled GUIDED assistant | Real LLM path when enabled, or deterministic aggregate-tool demonstration without a provider |
| 9–11 min | User requests names/salaries; separately labelled operator forces forbidden employee-export call | Tool unavailable to model; forced MCP operation is denied pre-dispatch, upstream export counter stays zero |
| 11–13 min | Verify the signed Talon session for the allowed/denied MCP operations; in live mode, also inspect verified LLM records from the same use-case identity | Buyer can independently validate only what traversed Talon |
| 13–15 min | Map the boundary to the customer's service accounts, warehouse roles, tool infrastructure and use-case budgets | Opens a concrete scoped pilot conversation |

Key line: "You've already governed who can read the data. Talon governs which actions a particular AI use case can execute, and gives you verifiable evidence. The existing HR permissions and deployment perimeter prevent bypass."

## Two interchangeable demonstration interfaces

The business dashboard on localhost:8501 offers an explicit link to the
**Presenter Proof Console** on localhost:8502. This is a separate, token-gated
host operator service with Docker privileges; it is **not available to the
restricted AI process**. Every UI proof action displays the exact corresponding
command and real process output, so the presenter can switch freely between
browser and terminal. The privileged BEFORE call and the explicit counter
RESET stay visible as separate actions. No "before/after Talon enable switch"
exists. [Detailed UI and CLI steps](PRESENTER_COMMANDS.md).

## Release and presentation gates

1. **Local:** Run make people-analytics-validate. Verify deterministic DuckDB metrics, read-only SQL reporting, browser routes and model loop fail-closed tests.
2. **Real Talon with fake model:** Run bash scripts/test-people-analytics-talon.sh. Uses real Talon LLM/MCP gateways, a deterministic fake OpenAI-compatible upstream, synthetic DuckDB and verified signed evidence. This does *not* prove real OpenAI inference.
3. **Before/after with network isolation:** Run bash scripts/people-analytics-isolated.sh up and then bash scripts/people-analytics-isolated.sh verify. Docker Compose proves the AI app has no database mount and no path to the private HR service, while Talon's aggregate call succeeds and the employee export is denied. This is also exercised in CI.
4. **Real external model (explicit opt-in):** Export a real OPENAI_API_KEY in the operator shell and run bash scripts/test-people-analytics-real-provider.sh. This invokes a real provider through Talon, requires a model-selected data tool, independently checks dispatch counts, and verifies the signed session. It incurs provider cost. This gate cannot be claimed to have passed until run in the intended environment.

Use mock-provider mode only when visibly labelled; don't call scripted text a real AI answer. Attrition metrics are descriptive, never evidence of causation. Never present this synthetic data as a real HR dataset.

## Presenter prep

- Checkout the PR branch, verify Talon and Docker Compose v2, and confirm the synthetic DuckDB seed process has succeeded. The Docker launcher seeds the DB automatically; manual multi-terminal mode requires explicit seeding.
- Stop stale services before starting the isolated deployment (UI exposed only on 127.0.0.1:8501); SSH tunnel from your laptop.
- Rehearse with the combined before/after verifier, then use the [granular presenter commands](PRESENTER_COMMANDS.md) in the meeting. The BEFORE baseline prints fictional employee information; the reset is explicit, visible and mandatory before post-denial counters.
- For genuine AI, first validate the external-provider smoke (paid, opt-in) and then launch isolated LIVE mode with the same Talon agent identity; this may restart demo services. Otherwise do not describe guided or mock-provider output as model-generated.
- After denial, show an independently checked backend counter and the Talon evidence export. Use exactly what was verified.
- Ask which current agents retain direct warehouse credentials and whether those can be removed; identify one approved HR analytics pilot.

## Boundaries

- No official Workday/Grab integration, real employees, SSO or production IAM.
- A compromised privileged HR service could still extract synthetic rows; the isolation keeps that privileged component off the AI application's network.
- No arbitrary query authorization, formal GDPR compliance claim or broad DLP guarantee. The demo's PII redaction is disabled.
- The ordinary dashboard read is intentionally a separate fixed aggregate API; it does not pass through Talon.
- The static demo agent key is suitable only for synthetic loopback/container testing. The isolated LIVE launcher passes a real provider key via environment variables to the Talon initialization container before storing it in Talon's vault. Environment variables may be visible to privileged Docker operators: never use this convenience workflow for production HR data or shared infrastructure.
- Signed evidence covers traffic that traverses Talon, not direct bypass traffic; the latter requires independent deployment checks.
