# Talon Full Demo

A standalone, early-adopter-oriented demonstration of recognizable applications governed through [Dativo Talon](https://github.com/dativo-io/talon):

- **Customer support / Zendesk** — a support workflow requests a governed reply draft.
- **GitHub Copilot CLI** — a real Copilot client sends model traffic through Talon and reaches a synthetic release boundary through Talon's MCP proxy.
- **n8n** — a document workflow preserves partial business output when Talon prevents the next request on projected session cost.

The intended experience is a **10–15 minute narrated walkthrough**, not a long terminal GIF. Every completed application case has two projections of the same Talon evidence:

- a concise buyer/product view;
- a technical/security view.

See [Audience-specific demo views](docs/AUDIENCE_DEMOS.md) for the full command matrix and truth boundaries.

## Start here

### 1. Validate the repository without keys

```bash
make validate-local
```

### 2. Prepare and start the real stack

Clone `dativo-io/talon` next to this repository, put Talon v1.9.3+ on `PATH`, then:

```bash
export OPENAI_API_KEY='sk-...'
make real-prepare
make real-start
make real-status
```

Add `ANTHROPIC_API_KEY` and rerun `make real-prepare` only when preparing the n8n/document-summary case.

## Choose a case and audience

### Customer-support gateway

Buyer/product/executive:

```bash
make demo-support-buyer
```

Platform/security/engineering:

```bash
make demo-support-tech
```

Re-present the completed session without a provider call:

```bash
make present-support
make present-support-tech
make present-support-all
```

The real support case proves email and IBAN redaction, a failed local provider, a disallowed fallback candidate skipped by policy, an approved OpenAI fallback, actual cost, and verified signed evidence.

### Zendesk adapter

Buyer/product/executive:

```bash
make demo-zendesk-buyer
```

Platform/security/engineering:

```bash
make demo-zendesk-tech
```

Re-present the completed session:

```bash
make present-zendesk
make present-zendesk-tech
make present-zendesk-all
```

This sends a synthetic Zendesk-shaped ticket through the real local adapter and Talon. It proves the adapter-to-Talon path, client attribution, PII handling, policy-valid failover, cost, and signed evidence. It does **not** prove private-app installation, secure-setting substitution, or comment selection inside a real Zendesk account; those remain separate external gates.

### GitHub Copilot CLI

Install the CLI once:

```bash
make copilot-install
```

Buyer/product/executive:

```bash
make demo-copilot-buyer
```

Platform/security/engineering:

```bash
make demo-copilot-tech
```

Re-present the same completed session:

```bash
make present-copilot
make present-copilot-tech
make present-copilot-all
```

The demo uses GitHub Copilot CLI in BYOK offline mode, pointed at Talon's local session shim. The bounded run permits only `release_status` and `release_prepare`, independently verifies upstream receipts and signed evidence, and explicitly stays within Talon's real boundary: model traffic and MCP calls routed through Talon. It is not a benchmark of Copilot code editing.

### n8n workflow

The repository intentionally does not claim a completed n8n workflow until a workflow built in the pinned UI has been exported without credentials and clean-imported into a fresh n8n `2.30.4` container.

After that real workflow run, present the resulting session with:

```bash
TALON_PRESENT_N8N_SESSION_ID=<session-id> make present-n8n
TALON_PRESENT_N8N_SESSION_ID=<session-id> make present-n8n-tech
TALON_PRESENT_N8N_SESSION_ID=<session-id> make present-n8n-all
```

These commands fail closed unless partial section files, `status.json`, a `session_budget_exceeded` denial, zero denied-request cost, matching `document-summary` evidence, and valid signatures all exist.

## Existing low-level commands

The original commands remain available for troubleshooting and manual validation:

```bash
make real-smoke       # direct support smoke path
make real-support     # fresh support run, full output
make real-zendesk     # fresh local Zendesk-adapter run, full output
make real-copilot     # fresh bounded Copilot run, full output
make live-check       # separate real-Talon MCP denial + session-budget engine proof
```

Stop repository-managed services with:

```bash
make real-stop
```

## Status

This repository deliberately separates what is executable from what remains gated on external accounts or UI setup.

| Area | Status |
|---|---|
| Local repository validation | Implemented and tested |
| Real Talon MCP + session-budget check | Implemented; `make live-check` |
| Real support gateway path | Implemented; buyer + technical views |
| Real local Zendesk adapter path | Implemented; buyer + technical views |
| Zendesk installed private app | External gate: installation + secure-setting verification |
| Real GitHub Copilot CLI path | Implemented; buyer + technical views |
| Synthetic release MCP server | Implemented and tested |
| Billing repository fixture | Implemented and tested locally; separate from the Copilot integration proof |
| n8n Compose + workflow specification | Implemented |
| n8n imported workflow execution | External gate; presenters fail closed until real artifacts/evidence exist |
| Talon configuration | Bootstrapped from canonical `talon/examples/product-demo` source |

## Why this repository exists

The short Talon hero proves the product outcome. This repository is the adopter-facing artifact: copyable applications, integration seams, test fixtures, and evidence-gated presenter flows.

## Quick local validation

No provider keys, Zendesk account, Copilot installation, Docker, or Talon binary are required.

Local prerequisites: `go` (1.23.0+), `node` and `npm` (Node 20+), `python3`, `jq`, `curl`, `git`.

```bash
make validate-local
```

`make validate-local` builds the Go services, runs unit tests, exercises the Zendesk adapter and Copilot shim against a mock Talon gateway, exercises the synthetic MCP server, asserts the session-budget contract, verifies the deterministic billing fixture, and checks that every buyer/technical presenter remains evidence-backed and free of hard-coded run results.

## Validation levels

| Command | External account needed? | Meaning |
|---|---:|---|
| `make validate-local` | No | Repository code, adapters, mock integration, presenter contracts, MCP contract, and billing fixture work locally. |
| `make live-check` | No provider account | A real Talon binary enforces MCP policy, attributes identity, signs evidence, and applies the real session-budget engine. |
| `make demo-support-buyer` | OpenAI | Run the real support path and finish with a concise evidence-derived receipt. |
| `make demo-support-tech` | OpenAI | Run the same path and expand PII, fallback, cost, and signatures. |
| `make demo-zendesk-buyer` | OpenAI | Run the real local Zendesk adapter path and finish with a buyer receipt. |
| `make demo-zendesk-tech` | OpenAI | Expand the adapter session, attribution, fallback, and evidence. |
| `make demo-copilot-buyer` | OpenAI + Copilot CLI | Run real Copilot and finish with a buyer receipt. |
| `make demo-copilot-tech` | OpenAI + Copilot CLI | Expand model/MCP traffic, boundary, cost, attribution, and signatures. |
| `make present-n8n` | Anthropic + imported n8n workflow | Project a completed real workflow into a buyer view. |
| `make present-n8n-tech` | Anthropic + imported n8n workflow | Expand the same workflow session and partial-output artifacts. |

## Core truth rules

- Application output is produced by the real application path, not by the presenter.
- Buyer and technical summaries are computed from newly exported and verified signed Talon sessions, never hard-coded.
- Provider routes, redaction, costs, policy decisions, and signatures are displayed only after Talon evidence confirms them.
- Talon is credited only for model traffic and tool calls routed through Talon.
- The local Zendesk adapter proof is not a claim that the private Zendesk app has been installed or validated.
- The n8n workflow specification cannot satisfy the n8n presenter without real output artifacts and evidence.
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

Never commit provider keys, Talon keys, Zendesk settings, generated evidence, n8n credentials, or real customer content. Real provider keys should be exported in the current shell for `make real-prepare`; the helper stores them in Talon's local encrypted vault and does not write them into `.env`.
