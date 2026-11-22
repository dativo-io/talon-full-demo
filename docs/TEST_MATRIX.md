# Test matrix and CI contract

*Last audited: November 22, 2026. Current tested producer: `dativo-io/talon@156188dea65cb6feab01aa92093a00e7717a6dd6` (source-built main, **not an official stable v1.17.0 binary**). The validation workflows for old unmerged PR combinations are being replaced by checks of the **actual checked-out branch/main**.*

## Proof levels

| Result type | Allowed claim | Not allowed |
| --- | --- | --- |
| **Offline contract / import** | Source, JSON, docs, mock protocol, clean import and local unit tests passed | A real Talon dispatch, actual model, merchant transaction or approved action |
| **Real Talon + synthetic downstream** | The real Talon executable enforced policy, generated native operations, stored signed evidence; real local PostgreSQL/DuckDB or independently counted synthetic effect | External Shopify refund, paid LLM output, sandbox containment outside the intercept path |
| **Shared-installation governance** | One live source-pinned Talon `serve`, company config, four native keys, same signer/evidence store and Console, distinct business outcomes | Four full application clients concurrently operated in a persistent official-release customer environment |
| **Published-release consumer** | Exact SHA256-verified published prerelease or stable executable passed the specific tests | Claiming current-main features or untested clients work on that older artifact |
| **Customer-live end-to-end** | Only after a verified release, actual four client UIs, persistent restart/recovery, identities, same-run evidence and operator walkthrough | Current status — **NOT RUN** |

## Canonical current-main acceptance

| Workflow / script | What actually runs | Status / direct evidence |
| --- | --- | --- |
| [`acme-governed-main-acceptance.yml`](../.github/workflows/acme-governed-main-acceptance.yml) | Source-builds exact Talon SHA; runs actual HR trusted MCP, real n8n 2.48.5/synthetic merchant refund, actual PostgreSQL staging and OrderDesk HTTP actions, real model budget, core SDK, and **one independent same-process four-use-case fleet job** | [PASS in the merged four-PR tree](https://github.com/dativo-io/talon-full-demo/actions/runs/45014911307) (three jobs) |
| [`scripts/test-acme-one-fleet.py`](../scripts/test-acme-one-fleet.py) | One native policy/store/process, four registered keys, HR export zero, synthetic refund €25/€249/€750, documents 2→deny, real staging repair, **41 signed records / 8 operation lifecycles**, Console seven areas | PASS as above; CLI/API pairing, **not** all four full client UIs or an end-to-end browser fleet |
| [`ci.yml`](../.github/workflows/ci.yml) | Normal Go/Python/Node validation, HR Compose+browser, Action Gateway preflight, and standalone release-contract tests | [PASS at consolidated ACME branch](https://github.com/dativo-io/talon-full-demo/actions/runs/45015580376) |
| [`orderdesk-main-action-gateway.yml`](../.github/workflows/orderdesk-main-action-gateway.yml) | Talon source-pinned HTTP Action Gateway, actual PostgreSQL local fixture, replay/bridge | [PR #45 review](https://github.com/dativo-io/talon-full-demo/pull/45); genuine OpenShell/Claude NOT RUN |
| [`people-analytics-governed-mcp-source.yml`](../.github/workflows/people-analytics-governed-mcp-source.yml) | Real Talon native governed `POST /mcp` with HR backend and signatures | [PR #46 review](https://github.com/dativo-io/talon-full-demo/pull/46) |
| [`shopify-core-main.yml`](../.github/workflows/shopify-core-main.yml) | Actual n8n import and source-main vs historical RC2 tagged-source compatibility | [PR #52 review](https://github.com/dativo-io/talon-full-demo/pull/52) |
| [`n8n-check.yml`](../.github/workflows/n8n-check.yml) | Historical n8n 2.30.4 clean imports; mock outcomes | Not Talon current-main external provider proof |
| [`zendesk-package.yml`](../.github/workflows/zendesk-package.yml) | ZIP packaging, manifest and secret absence | Not installed Zendesk account proof |

**Historical release/compatibility controls:** [`talon-rc2-compat.yml`](../.github/workflows/talon-rc2-compat.yml) downloads/verifies **published** prerelease `v1.17.0-rc.2` by its SHA256; [`orderdesk-rc2-source.yml`](../.github/workflows/orderdesk-rc2-source.yml) is tagged-source-only. Source-built RC2 is not a published-binary test. Their results are recorded in [RC2 consumer acceptance](RC2_CONSUMER_ACCEPTANCE.md).

## Commands — tested boundaries

Install local dependencies as shown in [the top-level README](../README.md). Minimal checks:

```bash
python3 scripts/check-repo-navigation.py
make validate-local
make live-check
```

To run the stronger, real ACME one-installation test, build the exact producer source and export `TALON_FLEET_BIN`, `TALON_CORE_DIR` and `TALON_CORE_SHA` according to the [root README](../README.md), then:

```bash
python3 scripts/test-acme-one-fleet.py
```

It requires Docker/Compose, Python DuckDB dependencies and available local fixture ports. It cleans up its own temporary store and Docker test volumes; **do not run it against customer data**. For actual consumer/transaction evidence, inspect workflow logs and downstream counters; a static PASS label or generated Markdown report is insufficient.

## Outstanding gates

- Full released, persistent **v1.17.0 stable** Four ACME client UIs working together and same-session Console/browser, restart/backup/restore: **NOT RUN**.
- Real Claude Code + OpenShell **C01–C12** same-hop verified identity, containment and tool choice: **NOT RUN**; OrderDesk host-key Action Gateway evidence is not this gate.
- Paid upstream model and actual Shopify payment mutation: **NOT RUN**; synthetic fixtures purposely perform no actual financial operation.
- Actual installed Zendesk private app and current-main GitHub Copilot compatibility: **NOT RUN**.
- Benchmark superiority vs Bifrost/LiteLLM/Portkey/Solo/TrueFoundry: **NOT RUN**; [buyer scorecard](COMPETITOR_PROOF_SCORECARD.md) is an adversarial methodology, not results.
