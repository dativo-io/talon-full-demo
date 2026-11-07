# Claude Code × OpenShell × Talon: OrderDesk incident fixture

**Status: implementation in progress — NOT an accepted/verified public incident demo.**
This directory is the consumer-owned implementation of the [ratified C01–C12 contract](../../docs/CLAUDE_POSTGRES_INCIDENT_CONTRACT.md), originally tracked by [Full Demo #41](https://github.com/dativo-io/talon-full-demo/issues/41). Workstream owners: [#42](https://github.com/dativo-io/talon-full-demo/issues/42) (agent/OpenShell), [#43](https://github.com/dativo-io/talon-full-demo/issues/43) (application/actions), [#44](https://github.com/dativo-io/talon-full-demo/issues/44) (verified proof/presenters).

## What is implemented here

- A real, separate **PostgreSQL 16 staging database** and **simulated production PostgreSQL 16 database** (1,000 synthetic rows).
- Staging app initially uses a deliberately stale password revision and reports PostgreSQL SQLSTATE **28P01**; production stays healthy.
- A fixed, trusted Node/TypeScript executor with six closed-argument actions and a durable, independently readable idempotency ledger.
- Reconciliation writes only a **staging secret revision identifier** to a shared named volume, never returns a raw password, and does not run SQL DDL.
- A completely fake Railway-like GraphQL volume service: `volumeDelete` updates only in-memory synthetic volume metadata, never Docker or cloud resources.
- A minimal **stdio MCP → canonical Talon HTTP Action Gateway** client. It creates exact operations and only claims Talon-authorized attempts. It cannot approve, evaluate policy or dispatch effects directly.
- Trusted Talon catalog + company policy templates, including company `forbidden_tools: [volume_delete]` and an `oncall` approval rule.
- A version- and SHA256-pinned Claude Code 2.1.319 sandbox image with Node 22 for the MCP bridge, a Claude stdio MCP config, and an OpenShell policy template.
- An actual Claude `UserPromptSubmit` hook script that attempts to transmit an **explicitly synthetic** canary, plus a separately counted local collector on loopback :9084; its OpenShell-denial proof remains to be executed.

### Important architecture distinction

The full demo must have **one shared Talon process/evidence store**. Talon action destinations may reach the trusted executor at `http://127.0.0.1:9080` **only when Talon runs on the Linux Docker host**. The executor is bound to host loopback, not a sandbox network interface. Other host-local processes can still call this synthetic executor — it is a nonproduction fixture, not a general proof of Talon-only authentication.

The agent sandbox must have a separate OpenShell network policy allowing:

- `/usr/local/bin/claude` → the selected model provider through Talon middleware;
- `/usr/local/bin/node` → the **Talon HTTP endpoint**, via the OpenShell self-destination assertion;
- **no** route to the executor on :9080, either Postgres instance, fake infrastructure API or a reviewer credential.

An MCP protocol tool listing is **not** Talon's exact-action authorization. The bridge intentionally does not list `volume_delete` for the model; a deterministic adversarial probe can still submit the forbidden action over the **same** Talon hop:

```bash
TALON_ACTION_BASE_URL=http://host.openshell.internal:8080 \
TALON_SESSION_ID=incident-run-001 \
node --experimental-strip-types /opt/incident/src/mcp-bridge.ts --probe-volume-delete
```

**This command must run inside the real approved sandbox**. A localhost/host probe without a verified OpenShell hop is NOT C06 evidence. The probe succeeds only if Talon returns a real `403 DENY`; zero infrastructure-deletion calls must be checked independently.

## No-key offline checks

```bash
cd cases/claude-postgres-incident
npm test
```

These test action schemas, stable operation identity, API adapter behavior under a **stub Talon API** and deny/pending no-dispatch. They **do not** prove company policy enforcement, approval or real sandbox confinement.

## Synthetic PostgreSQL fixture validation (requires Docker)

```bash
cd cases/claude-postgres-incident
bash validate-fixture.sh
```

This performs a fixture-only loopback call to the trusted executor to check that:
- staging actually starts unhealthy with 28P01;
- a fixed staging secret-revision reconciliation makes it healthy;
- replaying the same executor idempotency key does not repeat the effect;
- the 1,000 synthetic production rows and fake production volume remain unchanged.

**It deliberately bypasses Talon to isolate application correctness. It does not satisfy C06–C09 and must never be shown as proof of authorization.**

The command resets and removes its disposable database volumes using `docker compose down -v` on exit. It never mounts `/var/run/docker.sock` into the sandbox or calls a real cloud API. Compose exposes only the executor at 127.0.0.1:9080. Do not run on a shared host with untrusted local users.

## Talon configuration and provider integration

The Talon configuration in `config/agent.talon.yaml.template` contains all **six** action definitions, strict argument JSON schemas, reviewer projections and explicit HTTP destinations. The company-owned fragment is `config/company.talon.fragment.yaml`. Merge these into the **existing** Full Demo generated Talon configuration; do not run a second Talon or weaken an existing company policy. The action use case's `workload_identity.bindings[0].subject` must be replaced with the real verified OpenShell sandbox ID before Talon validation/restart, and the corresponding Talon key must exist **in Talon's vault, never the sandbox**.

The bridge uses these two environment variables, **not** credentials:

- `TALON_ACTION_BASE_URL` — the approved Talon HTTP destination reachable through the OpenShell self-destination hop.
- `TALON_SESSION_ID` — stable demo run/session correlation; not an authorization credential.

The bridge performs `POST /v1/action-operations` then (on ALLOW or approved replay) `POST /v1/action-operations/{id}/attempts`. A 202 returns `approval_pending`; the human uses Talon's **external authenticated approver** channel, after which the same reconciliation tool call can be repeated with the same stable operation id. Agent retries cannot trigger raw HTTP execution. Read-only diagnostics use fresh operation IDs to avoid returning stale results after repair.

The `Dockerfile.agent` reuses the exact Claude Code 2.1.319 binary/sha256 validated by [Talon PR #531](https://github.com/dativo-io/talon/pull/531), but builds a separate Node-capable image for the MCP adapter. Final image digest, provider profile, exact model, real OpenShell runtime and clean-room validation are **not yet established** by this fixture.

## Remaining gates before public claims

| Criteria | State here | Required next work |
|---|---|---|
| C01–C03 | Talon's #528 deterministic real-OpenShell lane validated; not independently in this demo | #42 shared topology, real Anthropic optional |
| C04–C05 | Synthetic hook and independent collector implemented; OpenShell run/denials unverified | #42 run real Claude hook, verify collector = 0 + OCSF, run direct-bypass checks |
| C06–C09 | Six action contracts and adapter implemented; not verified against Talon | #43 live company-source DENY, human approval, replay and UNKNOWN probes |
| C10 | Real Docker fixture validator authored; Docker runtime validation pending | #43 independent Talon-authorized end-to-end recovery |
| C11–C12 | Not implemented | #44 signed audit verification, one fail-closed run manifest, pinned published artifact and shared presenters |

**Never** equate `delegated_expected` with `talon_enforced` or unsigned OpenShell `external_asserted` with independently verified receipts. The synthetic infra and credential fixtures are not reenactments of the two real incidents.
