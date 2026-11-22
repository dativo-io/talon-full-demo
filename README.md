# Dativo Talon · Full Demo

**One company. Four existing AI use cases. One operating layer.**

This repository contains *customer-facing reference applications and independently executable proof* for [Dativo Talon](https://github.com/dativo-io/talon). The applications remain separate. Talon supplies shared company policy, operational identity, model/MCP/action controls, independent approvals, cost admission, read-only Operations Console and verifiable signed evidence **only for requests routed through it**.

**Start here:** [Demo catalog](docs/DEMO_CATALOG.md) · [Guided ACME journey](docs/DEMO_EXPERIENCE_INDEX.md) · [Test and release matrix](docs/TEST_MATRIX.md) · [Documentation index](docs/README.md)

## The four ACME use cases

| Existing application | Useful application result | Talon intervention | Implementation |
| --- | --- | --- | --- |
| **Customer Support** | Shopify-style **read-only** synthetic order lookup, governed draft and internal refund handoff | Company amount thresholds, independent approval, exact single dispatch, PII block | [Shopify/n8n support](integrations/n8n/shopify-support/README.md) |
| **People Analytics** | DuckDB workforce aggregate and existing browser | Governed `POST /mcp`, employee-export deny, SQL UNKNOWN handling, shared Console | [People Analytics](cases/people-analytics-copilot/README.md) |
| **OrderDesk / Engineering** | Real local PostgreSQL staging outage repaired; production preserved | HTTP Action Gateway company DENY, separate on-call reviewer, durable operation | [OrderDesk incident](cases/claude-postgres-incident/README.md) |
| **Document Processing** | Useful synthetic document responses before budget exhaustion | Real Talon per-session cost admission; next provider call denied | [Document/n8n reference](integrations/n8n/README.md) |

**n8n is an orchestrator inside Support and Documents, not a fifth AI use case.** Use one use-case identity/key each and configure the organization baseline once. HR uses canonical governed MCP; OrderDesk's HTTP Action Gateway is intentional. New adopters must **not** use the removed `/mcp/proxy` or `--proxy-config` interfaces.

## What we have actually proven

The [source-pinned four-use-case acceptance](https://github.com/dativo-io/talon-full-demo/actions/runs/45014911307) PASSED against exact Talon main `156188dea65cb6feab01aa92093a00e7717a6dd6` (source-built; **not a published stable release**). One running Talon process, company policy, data directory and signing store governed four distinct native keys. The run independently counted real local DuckDB/PostgreSQL and synthetic Shopify/document effects; produced **41 signed records, eight valid action lifecycles**, and showed all four in the paired native read-only Console (Overview, AI Use Cases, Approvals, Sessions, Costs, Configuration, System).

Additional consumer CI executes real n8n **2.48.5** and a synthetic merchant refund adapter. It proves €25 allow, €249 review-then-claim, €750 deny and replay refusal. Approval itself causes zero effects. The independent HR browser/Compose gate also passed. Consult the [test matrix](docs/TEST_MATRIX.md) for sources and precise claims.

**Not proven / not customer-live:** four complete application UIs simultaneously in one persistent **published v1.17.0 stable** installation; genuine Claude Code × OpenShell same-hop C01–C12; live Shopify payments; paid model/provider calls; Zendesk installation; or recovery of that full customer fleet. A historical published **v1.17.0-rc.2** consumer test is separately recorded in [RC2 acceptance](docs/RC2_CONSUMER_ACCEPTANCE.md). Do not substitute source-built results for released-artifact acceptance.

## Run the supported, credential-free proofs

From a fresh checkout, with Go, Python 3, Docker/Compose, Node and `jq` installed:

```bash
python3 -m pip install -r cases/people-analytics-copilot/requirements.txt
make validate-local            # offline app contracts, source tests and native fixtures
make live-check                # real source-built Talon MCP denial + session budget
```

To reproduce the **single-installation four-use-case control-plane test**, build the exact reviewed Talon main and run:

```bash
git clone https://github.com/dativo-io/talon.git ../talon
git -C ../talon checkout 156188dea65cb6feab01aa92093a00e7717a6dd6
mkdir -p .state
go -C ../talon build -o "$PWD/.state/talon" ./cmd/talon
TALON_FLEET_BIN="$PWD/.state/talon" \
TALON_CORE_DIR="$(cd ../talon && pwd)" \
TALON_CORE_SHA=156188dea65cb6feab01aa92093a00e7717a6dd6 \
python3 scripts/test-acme-one-fleet.py
```

The runner creates a disposable local installation, starts the HR/merchant/document fixtures plus actual PostgreSQL containers, verifies company policy and backend counters, pairs the native Console and tears down. **No paid provider keys or real merchant access are needed.** Docker and fixed fixture ports must be available. For the official current CI, see [ACME cross-consumer workflow](.github/workflows/acme-governed-main-acceptance.yml).

## Repository map

| Directory | Purpose |
| --- | --- |
| [`cases/`](cases/) | Existing standalone business-app fixtures: People Analytics, OrderDesk and additional historical cases |
| [`integrations/`](integrations/) | n8n workflows, Shopify support, Zendesk packaging and legacy Copilot integration |
| [`scripts/`](scripts/) | Executable proofs, environment tooling and signed-evidence checks |
| [`docs/`](docs/README.md) | Canonical guided journey, proof catalog, test/release claims, competitive evidence and runbooks |
| [`.github/workflows/`](docs/TEST_MATRIX.md) | Current-main acceptance, consumer compatibility and historical release checks |

The previous long-form standalone walkthrough is preserved verbatim as [**README_LEGACY.md**](README_LEGACY.md); historical scripts and n8n **2.30.4** flows remain available but are **not** equivalent to the current-main ACME acceptance. The older bespoke support approval gate is not Talon's canonical Action Gateway.

For technical scope and claims use the [ACME journey](docs/SHOWCASE_LIVE_WALKTHROUGH.md), [buyer-win strategy](docs/TALON_BUYER_WIN_STRATEGY.md), and [competitive proof scorecard](docs/COMPETITOR_PROOF_SCORECARD.md). Runtime **Approvals** are independent reviewer API/CLI actions; the native seven-area Console is read-only. Signed at-most-once authorization does **not** guarantee exactly-once external business effects.
