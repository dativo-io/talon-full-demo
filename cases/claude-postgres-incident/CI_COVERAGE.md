# OrderDesk Claude/Postgres incident — CI coverage and proof status

This case follows the same test classification as [People Analytics CI coverage](../people-analytics-copilot/CI_COVERAGE.md): **application first → actual Talon boundary → independent effects → signed verification → separate real-provider acceptance**. It is the incident's **Action Gateway**, not the HR case's MCP proxy, because the repair requires a human approval bound to exact action arguments.

| Layer | Command / CI | Real dependencies | Assertions | Explicit limitation |
|---|---|---|---|---|
| Contract | `make incident-contract-test` (routine CI) | Node 22; stub **Talon transport only** | Six closed schema shapes, no dangerous model tool advertised, stable mutation identity, HTTP routes, no sandbox secret injected by bridge, deny/pending do not claim; synthetic hook reachable-host positive control | Stub response is NOT Talon enforcement |
| Application | `make incident-fixture-validate` (Docker CI) | Real Postgres 16, OrderDesk Node app, protected executor, in-memory fake infrastructure, independent collector | Baseline staging `/health` and `/api/orders/summary` **503/28P01**; production rows=1000; independent collector reachable with zero hits; production observer lacks write grant; staging repair yields real `200` and orders count 2 / sum 4598; one executor mutation; no fake delete | Deliberate **direct executor** fixture call is NOT Talon authorization |
| Action governance | `make incident-talon-preflight` (separate Docker CI) | Exact **Talon v1.16.1** Go tag, real `talon validate`/`secrets`/`approver`/`serve`/`audit`, synthetic host bearer key | Company-source DENY; zero downstream volume effects; pending approval; no dispatch on approval; one later exact dispatch; replay/argument conflict; real app/business recovery; production invariant; `audit verify --operation` | This authenticated HOST-key preflight is not the OpenShell workload-hop C06–C09 proof; agent-key action evidence intentionally has no verified sandbox/session attribution |
| Delegated model + tool path | Full Demo #42 integration | Real pinned OpenShell and real Claude executable, Talon v1.16.1+ verified runtime | Same sandbox/use case/session for Anthropic and exact actions, real middleware, request-bound identity, no direct bypass, no key in sandbox | **Not implemented or passed here** |
| Hook containment | Full Demo #42 integration | Real Claude Code hook, OpenShell policy, independent collector | Hook executes and egress is blocked, collector receives zero despite reachable authorized-host positive control | **Not yet verified** |
| Signed customer claim | Full Demo #44 | Shared Talon data dir, real session, offline verifier, independently sourced run facts | Session-filtered signed export, verified operation lifecycle, models/usage, policy sources, exact payload digest, same sandbox, non-forged OpenShell provenance; buyer and technical views from same proof | **Not yet implemented** |
| Real Anthropic | Opt-in Full Demo #42 run | Actual Anthropic key in OpenShell provider store; real model traffic | Model-led diagnosis/reconciliation through delegated middleware, real token and cost evidence | **Not yet implemented**; not run in routine no-key CI |

## Why the case differs from People Analytics

People Analytics starts with an already useful DuckDB workforce app, introduces native Talon **MCP proxy** + model gateway, and proves policy changes with aggregate tool calls, independently constrained HR SQL, HR dispatch counters and Talon signatures. Its **GUIDED** mode is not a genuine LLM. The OrderDesk fixture likewise begins with a real business API and reproducible failure, but introduces Talon **Action Gateway** and an **OpenShell delegated** provider/model path to govern high-consequence operations. It uses fixed resource/revision schemas, an independent executor ledger and PostgreSQL business readout instead of an arbitrary SQL proxy. The correct operator interface is Claude Code terminal + external human review, **not** an invented workforce-style browser.

In both cases, a policy ALLOW **does not** mean the backend accepted arbitrary data/SQL and a Talon signature **does not** verify effects outside Talon's boundary. The trust proof is a composition of signed Talon decisions **and** independent backend/app observations. The evaluator must know which is which.

## Release provenance

The incident-specific [Talon release pin](TALON_RELEASE) is **v1.16.1**, separate from the People Analytics and other demos' pins. The published Talon **v1.16.1 release and annotated Git tag** point to commit `0cbcf96d1052e49fd020ac75b2f6ceccf02dda95`. Its changelog records real Claude/OpenShell Anthropic conformance and real Anthropic coverage in `make test-smoke`. GitHub lists v1.16.1 downloadable binaries and the OpenShell showcase manifest. **Independent checksum/manifest and clean-runner verification** remain separate #44 acceptance tests; do not infer they passed from publication.

Prior successful work (v1.16.0, before the current release pin) showed host-key API enforcement, approval, single dispatch and signed evidence in GitHub Actions. Do not report that historical result as though it used v1.16.1 or the delegated sandbox.

## Running

```bash
# from repo root — no keys, no containers
make incident-contract-test

# disposable real application + PostgreSQL, no LLM key
make incident-fixture-validate

# actual tagged Talon v1.16.1 CLI; no provider key or paid inference
go install github.com/dativo-io/talon/cmd/talon@v1.16.1
export PATH="$(go env GOPATH)/bin:$PATH"
make incident-talon-preflight
```

Routine CI runs all three, while #42/#44 remain blocking advanced integration work. `incident-fixture-validate` and `incident-talon-preflight` remove only their own Compose-created synthetic volumes and ephemeral Talon data after testing. Do not run these cleanup-oriented commands against production data.
