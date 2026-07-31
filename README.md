# Talon Full Demo

A standalone, early-adopter-oriented demonstration of recognizable applications governed through [Dativo Talon](https://github.com/dativo-io/talon):

- **n8n customer-support resolution** — a duplicate-charge workflow drafts a reply through a policy-valid provider path, protects customer PII, and cannot expose the forbidden refund action upstream.
- **n8n vendor-contract review** — a confidential synthetic contract package is blocked from one destination, redacted, and reviewed through the approved provider with both decisions in one signed session.
- **Customer support / Zendesk** — a support workflow requests a governed reply draft through direct and adapter paths.
- **GitHub Copilot CLI** — a real Copilot client sends model traffic through Talon and reaches a synthetic release boundary through Talon's MCP proxy.
- **n8n cost boundary** — an imported document workflow preserves partial business output when Talon prevents the next request on projected session cost.

The intended experience is a **10–15 minute narrated walkthrough**. Every completed application case has two projections of the same Talon evidence:

- a concise buyer/product view;
- a technical/security view.

See [Audience-specific demo views](docs/AUDIENCE_DEMOS.md) for the full command matrix and truth boundaries.

## Start here

### 1. Validate the repository without keys

```bash
make validate-local
```

With Docker available, validate the real pinned n8n artifacts separately:

```bash
make n8n-support-resolution-validate
make n8n-vendor-review-validate
make n8n-validate
```

The support-resolution gate proves reply-then-tool-denial workflow behavior. The vendor-review gate reproduces a zero-cost OpenAI egress denial followed by an approved Anthropic review. The quarterly gate reproduces useful output followed by a session-budget denial. Each workflow imports, executes, exports without credential values, clean-imports, and executes again in n8n `2.30.4`.

### 2. Prepare and start the real stack

Clone `dativo-io/talon` next to this repository, put Talon v1.9.3+ on `PATH`, then:

```bash
export OPENAI_API_KEY='sk-...'
export ANTHROPIC_API_KEY='sk-ant-...'
make real-prepare
make real-start
make real-status
```

OpenAI is required for support, Copilot, Zendesk, and the customer-support resolution. Anthropic is required for the quarterly and vendor-review n8n cases. `real-prepare` installs the full-demo-owned vendor-review and customer-support action-boundary overlays into the generated Talon fleet and seeds their vault bindings.

## Choose a case and audience

### n8n customer-support resolution

The input is a synthetic duplicate-charge ticket, account context, and refund policy. n8n produces a useful reply draft despite the preferred local provider being unavailable, while Talon redacts the customer's email and IBAN, keeps failover inside the approved provider list, and blocks a later request that exposes `issue_refund`.

Buyer/product/executive:

```bash
make demo-n8n-support-resolution-buyer
```

Platform/security/engineering:

```bash
make demo-n8n-support-resolution-tech
```

Re-present the same completed session:

```bash
make present-n8n-support-resolution
make present-n8n-support-resolution-tech
make present-n8n-support-resolution-all
```

The presenter fails closed unless the resolution and status artifacts, `customer-support` identity, confidential-tier email/IBAN redaction, local-provider failure, skipped disallowed fallback, approved OpenAI selection, later zero-cost `issue_refund` tool denial, and every evidence signature agree.

Talon does not execute, approve, or decline the EUR 249 refund. The workflow preserves the reply and records that human support and finance approval remain required.

### n8n vendor-contract review

The input is a synthetic vendor profile, proposed DPA, and internal review policy. The workflow first probes OpenAI with the confidential package; Talon's agent-level egress rule denies it before provider access. The same package then goes to the approved Anthropic destination after email and IBAN redaction.

Buyer/product/executive:

```bash
make demo-n8n-vendor-review-buyer
```

Platform/security/engineering:

```bash
make demo-n8n-vendor-review-tech
```

Re-present the same completed session:

```bash
make present-n8n-vendor-review
make present-n8n-vendor-review-tech
make present-n8n-vendor-review-all
```

The presenter fails closed unless the review and status artifacts, `vendor-contract-review` identity, zero-cost OpenAI egress denial, later allowed Anthropic decision, confidential-tier email/IBAN redaction, and every evidence signature agree. The generated review is advisory and synthetic; human legal, privacy, security, and procurement review remains required.

### Customer-support gateway

```bash
make demo-support-buyer
make demo-support-tech

make present-support
make present-support-tech
make present-support-all
```

The direct support case proves email and IBAN redaction, a failed local provider, a disallowed fallback candidate skipped by policy, an approved OpenAI fallback, actual cost, and verified signed evidence. It is a lower-level gateway proof than the n8n support-resolution business workflow.

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

### n8n session-budget workflow

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

The workflow reads synthetic quarterly sections sequentially, writes each completed summary, then preserves partial output and writes `status.json` when Talon denies the next request with `session_budget_exceeded`. The presenter fails closed unless output artifacts, `document-summary` identity, allowed work followed by a zero-cost denial, and valid signatures all agree.

## Existing low-level commands

```bash
make real-smoke                    # direct support smoke path
make real-support                  # fresh support gateway run
make real-zendesk                  # fresh local Zendesk-adapter run
make real-copilot                  # fresh bounded Copilot run
make real-n8n-support-resolution   # fresh customer-support resolution workflow
make real-n8n-vendor-review        # fresh vendor-contract review workflow
make real-n8n                      # fresh quarterly-report workflow
make live-check                    # separate real-Talon MCP denial + budget-engine proof
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
| n8n customer-support resolution | Implemented; pinned clean-import gate + real OpenAI/fallback path |
| n8n vendor-contract review | Implemented; pinned egress-deny/allow clean-import gate + real Anthropic path |
| n8n session-budget workflow | Implemented; pinned import/execute/export/clean-import gate + real Anthropic path |
| Real support gateway path | Implemented; buyer + technical views |
| Real local Zendesk adapter path | Implemented; buyer + technical views |
| Zendesk offline private-app ZIP | Implemented; deterministic package + secret scan + CI artifact |
| Zendesk server-side ZCLI validation/package | Implemented command; Zendesk authentication required |
| Zendesk installed private app | Account/browser gate; `make verify-zendesk-installed` records completion |
| Real GitHub Copilot CLI path | Implemented; buyer + technical views |
| Talon configuration | Canonical product-demo source plus full-demo-owned vendor-review and customer-support overlays |

## Validation levels

| Command | External account needed? | Meaning |
|---|---:|---|
| `make validate-local` | No | Repository code, adapters, mock integration, presenter contracts, MCP contract, and billing fixture work locally. |
| `make n8n-support-resolution-validate` | No provider account; Docker | Support workflow creates a reply, blocks `issue_refund`, exports without credentials, clean-imports, and executes again. |
| `make n8n-vendor-review-validate` | No provider account; Docker | Vendor-review workflow proves egress-deny then allow behavior twice with credential-free exports. |
| `make n8n-validate` | No provider account; Docker | Quarterly workflow imports, executes, exports without credentials, clean-imports, and executes again. |
| `make live-check` | No provider account | A real Talon binary enforces MCP policy, signs evidence, and applies the real session-budget engine. |
| `make demo-n8n-support-resolution-buyer` / `-tech` | OpenAI + Docker | Real imported support workflow, PII redaction, policy-valid fallback, forbidden refund tool, cost, and evidence. |
| `make demo-n8n-vendor-review-buyer` / `-tech` | OpenAI + Anthropic + Docker | Real imported workflow, egress denial, PII redaction, approved review, cost, and evidence. |
| `make demo-n8n-buyer` / `-tech` | Anthropic + Docker | Real imported workflow, partial output, budget stop, and evidence. |
| `make demo-support-buyer` / `-tech` | OpenAI | Direct support PII, fallback, cost, and evidence. |
| `make demo-zendesk-buyer` / `-tech` | OpenAI | Real local adapter path and evidence. |
| `make zendesk-package` | No Zendesk account | Build and inspect a credential-free ZIP; no Zendesk server validation claim. |
| `make zendesk-zcli-package` | Authenticated Zendesk account | Official ZCLI validation and package, then local ZIP inspection. |
| `make verify-zendesk-installed` | Zendesk account | Machine-verified Talon session plus explicit operator-confirmed UI observations. |
| `make demo-copilot-buyer` / `-tech` | OpenAI + Copilot CLI | Real Copilot model/MCP path and evidence. |

## Core truth rules

- Application output is produced by the real application path, not by the presenter.
- Buyer and technical summaries are computed from newly exported and verified signed Talon sessions, never hard-coded.
- Provider routes, redaction, costs, policy decisions, and signatures are displayed only after Talon evidence confirms them.
- Talon is credited only for model traffic and tool schemas or calls routed through Talon.
- A blocked `issue_refund` schema proves it was not offered through that governed request; Talon does not execute, approve, or decline refunds.
- An offline Zendesk ZIP is not described as Zendesk server-validated.
- Zendesk browser-only observations are operator-confirmed, not misrepresented as Talon evidence.
- Talon does not govern Copilot's local shell commands, filesystem changes, browser actions, or direct API calls.
- Session limits are soft caps.
- Vendor-contract review output is advisory, synthetic, and requires human review.
- HMAC evidence is tamper-evident and offline-verifiable, not immutable.
- Only synthetic data belongs in this repository and demo.

## Repository map

```text
cmd/                  runnable adapters and helper services
internal/             tested implementation packages
integrations/         Zendesk, Copilot, and n8n integration assets
cases/                synthetic business fixtures
config/               generated Talon config, integration overlays, and MCP templates
mock/                  no-key local Talon-compatible test endpoint
scripts/               setup, validation, orchestration, and presenters
docs/                  quickstarts, architecture, setup, presenter, and blockers
```

## Security

Never commit provider keys, Talon keys, Zendesk settings, generated evidence, n8n credentials, or real customer content. Real provider keys should be exported only for `make real-prepare`; the helper stores them in Talon's encrypted local vault and does not write them into `.env`.
