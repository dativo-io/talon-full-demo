# Talon Full Demo

A standalone, early-adopter-oriented demonstration of three recognizable applications governed through [Dativo Talon](https://github.com/dativo-io/talon):

- **Zendesk Support** — a human support agent requests a governed reply draft.
- **GitHub Copilot CLI** — Copilot fixes a real test through Talon's OpenAI-compatible gateway and reaches a synthetic release boundary through Talon's MCP proxy.
- **n8n** — a document workflow preserves partial business output when Talon prevents the next request on projected session cost.

The intended experience is a **10–15 minute narrated interactive walkthrough**, not a long terminal GIF.

## Start here

### 1. Validate the repository without keys

```bash
make validate-local
```

### 2. Run one real provider-backed case

Clone `dativo-io/talon` next to this repository, put Talon v1.9.3+ on `PATH`, then:

```bash
export OPENAI_API_KEY='sk-...'
make real-prepare
make real-start
make real-smoke
```

A successful smoke test proves a real support request was PII-redacted, the unavailable local provider failed, a disallowed fallback candidate was skipped, OpenAI was selected, and the resulting signed evidence verified offline.

Optional real Copilot case:

```bash
make copilot-install   # one-time; explicit opt-in installation
make real-copilot
```

The demo uses GitHub Copilot CLI in BYOK offline mode, pointed at Talon's local session shim. GitHub authentication is not required for this model/MCP path. `make real-copilot` verifies that the installed CLI supports the exact provider, MCP, and permission flags used by the demo before launching it.

See [Real cases: the short path](docs/REAL_CASES_QUICKSTART.md) for the complete staged flow. Use [SETUP.md](docs/SETUP.md) as the manual reference and [PRESENTER_RUNBOOK.md](docs/PRESENTER_RUNBOOK.md) only after every relevant gate passes.

Stop repository-managed services with:

```bash
make real-stop
```

## Status

This repository deliberately separates what is implemented and locally testable from what remains gated on live services or external account setup.

| Area | Status |
|---|---|
| Local repository validation | Implemented and tested |
| Real Talon MCP + session-budget check | Implemented; `make live-check` |
| Real OpenAI support smoke test | Implemented; `make real-prepare real-start real-smoke` |
| Copilot model session shim | Implemented and tested; real Copilot CLI driver requires the CLI binary (`make copilot-install`) |
| Zendesk adapter | Implemented and tested against a mock Talon endpoint |
| Zendesk ticket-editor app | Implemented; requires private-app installation and secure-setting verification |
| Synthetic release MCP server | Implemented and tested |
| Billing repository fixture | Implemented; fails before the expected patch |
| n8n Compose and workflow specification | Compose implemented; workflow export and clean-import from pinned n8n UI remain external |
| Talon configuration | Bootstrapped from canonical `talon/examples/product-demo` source |

## Why this repository exists

The short Talon hero proves the product outcome. This repository is the adopter-facing artifact: copyable applications, integration seams, test fixtures, and an evidence-gated presenter runbook.

## Quick local validation

No provider keys, Zendesk account, Copilot installation, Docker, or Talon binary are required.

Local prerequisites: `go` (1.23.0+), `node` and `npm` (Node 20+), `python3`, `jq`, `curl`, `git`.

```bash
make validate-local
```

If Go prints `download go1.23 ... toolchain not available`, pull the latest repository changes. To inspect the Go binary installed on the host without triggering module toolchain selection, run:

```bash
GOTOOLCHAIN=local go version
```

Install a current Go release from [go.dev/dl](https://go.dev/dl/) when the local version is older than 1.23.0 or automatic toolchain downloads are blocked.

`make validate-local` builds the Go services, runs unit tests, exercises the Zendesk adapter and Copilot shim against a mock Talon gateway, exercises the synthetic MCP server with a nonce-correlated forbidden-tool proof, asserts the session-budget scenario, and verifies the billing fixture.

## Validation levels

| Command | External account needed? | Meaning |
|---|---:|---|
| `make validate-local` | No | Repository and local mock paths work. |
| `make live-check` | No provider account | A real Talon binary enforces MCP and session-budget behavior. |
| `make real-smoke` | OpenAI | One real provider-backed support path and signed evidence work end to end. |
| `make real-copilot` | OpenAI + Copilot CLI | The real Copilot client uses Talon for model and MCP traffic. |
| Zendesk private app | Zendesk + tunnel | Installed app secure settings and ticket-editor flow work. |
| n8n scene | Anthropic + Docker | Pinned imported workflow and budget scene work. |

## Core truth rules

- Application output is produced by the real application path, not by the presenter.
- Provider routes, redaction, costs, policy decisions, and signatures are displayed only after Talon evidence confirms them.
- Talon is credited only for model traffic and tool calls routed through Talon.
- Talon does not govern Copilot's local shell commands, filesystem changes, browser actions, or direct API calls.
- One coding-tool denial does not create a fictional `needs-attention` fleet state.
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
scripts/               setup, validation, orchestration, and assertions
docs/                  quickstarts, architecture, setup, presenter, and blockers
```

## Security

Never commit provider keys, Talon keys, Zendesk settings, generated evidence, n8n credentials, or real customer content. Real provider keys should be exported in the current shell for `make real-prepare`; the helper stores them in Talon's local encrypted vault and does not write them into `.env`.
