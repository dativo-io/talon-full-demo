# Talon Full Demo

A standalone, early-adopter-oriented demonstration of recognizable applications governed through [Dativo Talon](https://github.com/dativo-io/talon):

- **Customer support / Zendesk** — a support workflow requests a governed reply draft.
- **GitHub Copilot CLI** — a real Copilot client sends model traffic through Talon and reaches a synthetic release boundary through Talon's MCP proxy.
- **n8n** — an imported document workflow preserves partial business output when Talon prevents the next request on projected session cost.

The intended experience is a **10–15 minute narrated walkthrough**. Every completed application case has two projections of the same Talon evidence:

- a concise buyer/product view;
- a technical/security view.

See [Audience-specific demo views](docs/AUDIENCE_DEMOS.md) for the full command matrix and truth boundaries.

## Start here

### 1. Validate the repository without keys

```bash
make validate-local
```

With Docker available, validate the real pinned n8n artifact separately:

```bash
make n8n-validate
```

This imports, executes, exports, clean-imports, and executes the credential-free workflow again in n8n `2.30.4` against the mock allow-then-budget-deny contract.

### 2. Prepare and start the real stack

Clone `dativo-io/talon` next to this repository, put Talon v1.9.3+ on `PATH`, then:

```bash
export OPENAI_API_KEY='sk-...'
export ANTHROPIC_API_KEY='sk-ant-...'
make real-prepare
make real-start
make real-status
```

Anthropic is required only for the n8n/document-summary scene.

## Choose a case and audience

### Customer-support gateway

```bash
make demo-support-buyer
make demo-support-tech

make present-support
make present-support-tech
make present-support-all
```

The real support case proves email and IBAN redaction, a failed local provider, a disallowed fallback candidate skipped by policy, an approved OpenAI fallback, actual cost, and verified signed evidence.

### Zendesk adapter

```bash
make demo-zendesk-buyer
make demo-zendesk-tech

make present-zendesk
make present-zendesk-tech
make present-zendesk-all
```

This proves the real local adapter-to-Talon path, client attribution, PII handling, policy-valid failover, cost, and signed evidence.

Build and inspect a credential-free private-app ZIP without an account:

```bash
make zendesk-package
```

Run official Zendesk server-side validation and packaging after authenticating ZCLI:

```bash
zcli login -i
make zendesk-zcli-package
```

The hosted workflow always builds and scans the offline ZIP. It also runs authenticated ZCLI automatically when repository secrets `ZENDESK_SUBDOMAIN` and `ZENDESK_OAUTH_TOKEN` exist.

After installing the authenticated package in a real Zendesk account and observing the UI flow, machine-verify the matching Talon session and record the UI observations:

```bash
export ZENDESK_INSTALLED_TICKET_ID='<ticket-id>'
export ZENDESK_INSTALLED_SESSION_ID='<session-id-shown-by-the-app>'
export ZENDESK_PRIVATE_APP_INSTALLED=yes
export ZENDESK_SECURE_SETTING_CONFIRMED=yes
export ZENDESK_NEWEST_REQUESTER_COMMENT_CONFIRMED=yes
export ZENDESK_DRAFT_INSERTED_CONFIRMED=yes
make verify-zendesk-installed
```

UI observations remain explicitly operator-confirmed; Talon identity, routing, redaction, cost, and signatures are machine-verified.

### GitHub Copilot CLI

Install once:

```bash
make copilot-install
```

Run and present:

```bash
make demo-copilot-buyer
make demo-copilot-tech

make present-copilot
make present-copilot-tech
make present-copilot-all
```

The bounded run permits only `release_status` and `release_prepare`, independently verifies upstream receipts and signed evidence, and stays within Talon's real boundary: model traffic and MCP calls routed through Talon. It is not a benchmark of Copilot code editing.

### n8n workflow

The repository contains a real, credential-free workflow export and a pinned clean-import gate.

Buyer/product/executive:

```bash
make demo-n8n-buyer
```

Platform/security/engineering:

```bash
make demo-n8n-tech
```

Re-present the same completed session:

```bash
make present-n8n
make present-n8n-tech
make present-n8n-all
```

The workflow reads synthetic compliance sections sequentially, writes each completed summary, then preserves partial output and writes `status.json` when Talon denies the next request with `session_budget_exceeded`. The presenter fails closed unless output artifacts, `document-summary` identity, allowed work followed by a zero-cost denial, and valid signatures all agree.

## Existing low-level commands

```bash
make real-smoke       # direct support smoke path
make real-support     # fresh support run, full output
make real-zendesk     # fresh local Zendesk-adapter run, full output
make real-copilot     # fresh bounded Copilot run, full output
make real-n8n         # fresh imported n8n workflow, full output
make live-check       # separate real-Talon MCP denial + budget-engine proof
```

Stop repository-managed services with:

```bash
make real-stop
```

## Status

| Area | Status |
|---|---|
| Local repository validation | Implemented and tested |
| Real Talon MCP + session-budget check | Implemented; `make live-check` |
| Real support gateway path | Implemented; buyer + technical views |
| Real local Zendesk adapter path | Implemented; buyer + technical views |
| Zendesk offline private-app ZIP | Implemented; deterministic package + secret scan + CI artifact |
| Zendesk server-side ZCLI validation/package | Implemented command; Zendesk authentication required |
| Zendesk installed private app | Account/browser gate; `make verify-zendesk-installed` records completion |
| Real GitHub Copilot CLI path | Implemented; buyer + technical views |
| n8n workflow artifact | Implemented; pinned import/execute/export/clean-import CI gate |
| Real n8n + Anthropic path | Implemented command; host execution remains the provider credential gate |
| Talon configuration | Bootstrapped from canonical `talon/examples/product-demo` source |

## Validation levels

| Command | External account needed? | Meaning |
|---|---:|---|
| `make validate-local` | No | Repository code, adapters, mock integration, presenter contracts, MCP contract, and billing fixture work locally. |
| `make n8n-validate` | No provider account; Docker | The committed workflow imports, executes, exports without credentials, clean-imports, and executes again. |
| `make live-check` | No provider account | A real Talon binary enforces MCP policy, signs evidence, and applies the real session-budget engine. |
| `make demo-support-buyer` / `-tech` | OpenAI | Real support, PII, fallback, cost, and evidence. |
| `make demo-zendesk-buyer` / `-tech` | OpenAI | Real local adapter path and evidence. |
| `make zendesk-package` | No Zendesk account | Build and inspect a credential-free ZIP; no Zendesk server validation claim. |
| `make zendesk-zcli-package` | Authenticated Zendesk account | Official ZCLI validation and package, then local ZIP inspection. |
| `make verify-zendesk-installed` | Zendesk account | Machine-verified Talon session plus explicit operator-confirmed UI observations. |
| `make demo-copilot-buyer` / `-tech` | OpenAI + Copilot CLI | Real Copilot model/MCP path and evidence. |
| `make demo-n8n-buyer` / `-tech` | Anthropic + Docker | Real imported n8n workflow, partial output, budget stop, and evidence. |

## Core truth rules

- Application output is produced by the real application path, not by the presenter.
- Buyer and technical summaries are computed from newly exported and verified signed Talon sessions, never hard-coded.
- Provider routes, redaction, costs, policy decisions, and signatures are displayed only after Talon evidence confirms them.
- Talon is credited only for model traffic and tool calls routed through Talon.
- An offline Zendesk ZIP is not described as Zendesk server-validated.
- Zendesk browser-only observations are operator-confirmed, not misrepresented as Talon evidence.
- Talon does not govern Copilot's local shell commands, filesystem changes, browser actions, or direct API calls.
- Session limits are soft caps.
- HMAC evidence is tamper-evident and offline-verifiable, not immutable.
- Only synthetic data belongs in this repository and demo.

## Repository map

```text
cmd/                  runnable adapters and helper services
internal/             tested implementation packages
integrations/         Zendesk, Copilot, and n8n integration assets
cases/                synthetic business fixtures
config/               generated Talon config location and MCP templates
mock/                  no-key local Talon-compatible test endpoint
scripts/               setup, validation, orchestration, and presenters
docs/                  quickstarts, architecture, setup, presenter, and blockers
```

## Security

Never commit provider keys, Talon keys, Zendesk settings, generated evidence, n8n credentials, or real customer content. Real provider keys should be exported only for `make real-prepare`; the helper stores them in Talon's encrypted local vault and does not write them into `.env`.
