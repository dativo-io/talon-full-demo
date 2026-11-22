# ACME First Production Pilot — two existing use cases on governed Talon

**Status:** a source-built, single-process **four-use-case technical governance test PASSED** ([real one-installation ACME acceptance (all three CI jobs passed)](https://github.com/dativo-io/talon-full-demo/actions/runs/45014911307)) with independent downstream counters, 41 signed records, eight verified operation lifecycles and a paired native Console. The installation was **ephemeral CI**, not a published-release persistent production pilot or a simultaneous end-to-end four-application UI demonstration. See the [live execution index](DEMO_EXPERIENCE_INDEX.md). No paid model keys are required; neither real Shopify payment nor real Claude/OpenShell C01–C12 was exercised.

## 1. Use exactly the validated Talon producer

These instructions target the **source-built** merged MCP Action Gateway main, not the published historical RC2. Do not use a moving `main` checkout in a demo.

```bash
git clone https://github.com/dativo-io/talon.git
git -C talon checkout 156188dea65cb6feab01aa92093a00e7717a6dd6
test "$(git -C talon rev-parse HEAD)" = "156188dea65cb6feab01aa92093a00e7717a6dd6"
mkdir -p bin
(cd talon && go build -o ../bin/talon ./cmd/talon)
bin/talon version
sha256sum bin/talon   # save alongside every generated proof pack
```

For a released installation instead, verify a published archive and image at the **same** pinned version/digest first, using the official [release verification and production pilot runbook](https://github.com/dativo-io/talon/blob/156188dea65cb6feab01aa92093a00e7717a6dd6/docs/guides/production-pilot.md). Do not pass off the above binary as an official release artifact.

## 2. One organization policy, two distinct use cases

- **ACME Support** uses the existing Shopify-style n8n 2.48.5 workflow for customer lookup/draft plus the canonical HTTP Action Gateway for the synthetic EUR 25/249/750 refund scenario; the company policy controls its action limits and independent reviewer. The finance system is **synthetic**, and two imported workflows are required. [Actual PR #52](https://github.com/dativo-io/talon-full-demo/pull/52).
- **ACME People Analytics** uses `actions.sources.hr` in its use-case `agent.talon.yaml`, with real HR Docker/DuckDB behind Talon's governed `POST /mcp`; `hr_aggregate_sql` is dispatched when allowed, `hr_employee_export` is denied with zero backend calls, and an HR rejection after dispatch is `UNKNOWN`. [Actual PR #46](https://github.com/dativo-io/talon-full-demo/pull/46).

Load the shared company defaults and forbidden/approval constraints under **`gateway.organization_policy` in `talon.config.yaml`**, once. Register each use case with a **distinct use-case key**; one company's constraints cannot be weakened by an agent override. Use only the existing Talon configuration and native registration surfaces:

```bash
talon agents add support-assistant --tenant acme --owner support-ops@acme.example
talon agents add hr-analytics-assistant --tenant acme --owner people-ops@acme.example
talon validate
talon doctor
talon agents show support-assistant --effective
talon agents show hr-analytics-assistant --effective
```

This presumes a configured Talon data directory/agents directory and company baseline; complete setup and secure key handling are in the [official pilot runbook](https://github.com/dativo-io/talon/blob/156188dea65cb6feab01aa92093a00e7717a6dd6/docs/guides/production-pilot.md). `agents add` shows keys **once**: store in the application's secret manager, not shell history, screenshots, a repository or the n8n workflow JSON. Add the HR source token to Talon's vault scoped to the HR use case; do not give that token to an agent client.

## 3. Connect, exercise, observe

1. Start the trusted HR MCP backend, then `talon serve --host 127.0.0.1 --port 8080` with the shared data store and company configuration. **There is no `--proxy-config` and no `/mcp/proxy`.** When needed, start `talon ui serve` against the same store: Console access uses a one-time log-printed pairing code, not the admin key in a browser.
2. Give the HR application's **MCP client** the endpoint `http://127.0.0.1:8080/mcp`, `Authorization: Bearer <HR use-case key>` and standard MCP `2026-07-28`. Give Support its separate key and Talon's model/HTTP-action endpoints; the two applications must genuinely connect and transmit governed traffic. The `X-Talon-Session-ID` is merely attribution.
3. Run one allowed HR aggregate, the denied export and the HR-validator UNKNOWN; compare Talon's signed outcomes against **independent HR dispatch counters**. Run the n8n customer-support inquiry and €25 allowed, €249 independently reviewed, €750 forbidden synthetic refund; inspect finance counters (0 before decision, exactly 1 after a claim, 0 denied). Approval **does not** execute. Replay must not add effects; changed arguments conflict; UNKNOWN is never blindly retried. The consequential MCP path is prepare → `talon_execute_operation` and receives an operation ID **from Talon**, not from the model.
4. Verify an actual operation: `talon audit verify --operation <operation_id>`. Then inspect Console Overview, AI Use Cases/effective policy, Approvals (read-only), Sessions/evidence, Costs, Configuration and System. The Console proves **observed readiness**, not connection merely because an agent was registered. A browser session cannot approve an operation; use a separately authenticated reviewer CLI/API.

## 4. Gates before calling this a live ACME demo

**Two distinct acceptance levels:** (1) the new `one-installation-fleet` job in [ACME's current-main workflow](../.github/workflows/acme-governed-main-acceptance.yml) **PASSED** with four native use cases in one live ephemeral Talon installation, common loaded baseline, independently measured outcomes, one signed proof and paired Console; (2) a **persistent official-artifact buyer deployment** with all four actual client UIs, safe restart/restore and one narrated end-to-end presentation remains **NOT RUN**. Component CI on separate stores alone does not establish (1). Other current limits: no real Shopify payment, no anonymous external MCP access, no implicit shell/file/browser containment, no native Console write/reviewer UI, no corporate SSO reviewer authentication and no paid-provider claim unless explicitly run. For the engineering incident, OrderDesk still correctly uses its existing **HTTP** Action Gateway, and Claude Code × OpenShell C01–C12 remain a separate nontrivial gate.

**Executable fixtures:** `make incident-bridge-intents` for OrderDesk, `bash scripts/test-people-analytics-talon.sh` for HR, `bash integrations/n8n/shopify-support/test-n8n.sh` for Shopify (n8n 2.48.5), and `make live-check` on the correct pinned Talon source for synthetic MCP. The [merged-main four-PR CI](../.github/workflows/acme-governed-main-acceptance.yml) exercises these component paths but must not be mistaken for the final shared-fleet buyer run.
