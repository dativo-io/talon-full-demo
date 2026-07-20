# Talon Full Demo

A standalone, early-adopter-oriented demonstration of three recognizable applications governed through [Dativo Talon](https://github.com/dativo-io/talon):

- **Zendesk Support** — a human support agent requests a governed reply draft.
- **GitHub Copilot CLI** — Copilot fixes a real test through Talon's OpenAI-compatible gateway and attempts a release capability through Talon's MCP proxy.
- **n8n** — a document workflow preserves partial business output when Talon prevents the next request on projected session cost.

The intended experience is a **10–15 minute narrated interactive walkthrough**, not a long terminal GIF.

## Status

This repository deliberately separates what is implemented and locally testable from what remains gated on live services or Talon product work.

| Area | Status |
|---|---|
| Copilot model session shim | Implemented and tested |
| Zendesk adapter | Implemented and tested against a mock Talon endpoint |
| Zendesk ticket-editor app | Implemented; requires a Zendesk private-app installation test |
| Synthetic release MCP server | Implemented and tested |
| Billing repository fixture | Implemented; fails before the expected patch |
| n8n Compose and workflow specification | Implemented; exported workflow must be produced from the pinned n8n UI |
| Talon configuration | Bootstrapped from the canonical `talon/examples/product-demo` source |
| MCP policy-denial proof | Talon #346/#350 are fixed; implementation is compatible with current `main`, but end-to-end Copilot/Talon evidence proof remains external |
| Real-provider evidence choreography | Requires provider keys and a real Talon gateway |

## Why this repository exists

The short Talon hero proves the product outcome. This repository is the adopter-facing artifact: copyable applications, integration seams, test fixtures, and an evidence-gated presenter runbook.

## Quick local validation

No provider keys, Zendesk account, Copilot installation, Docker, or Talon binary are required:

```bash
make validate-local
```

This builds the Go services, runs unit tests, exercises the Zendesk adapter and Copilot shim against a mock Talon gateway, exercises the synthetic MCP server, and verifies the billing fixture.

## Real setup

1. Clone `dativo-io/talon` next to this repository.
2. Generate `.env`:

   ```bash
   make env
   ```

3. Copy the canonical three-agent demo baseline:

   ```bash
   TALON_REPO=../talon make bootstrap-config
   ```

4. Follow [docs/SETUP.md](docs/SETUP.md).
5. Use [docs/PRESENTER_RUNBOOK.md](docs/PRESENTER_RUNBOOK.md) only after every evidence gate passes.

## Core truth rules

- Application output is produced by the real application path, not by the presenter.
- Provider routes, redaction, costs, policy decisions, and signatures are displayed only after Talon evidence confirms them.
- Talon is credited only for model traffic and tool calls routed through Talon.
- One coding-tool denial does not create a fictional `needs-attention` fleet state.
- Session limits are soft caps.
- HMAC evidence is tamper-evident and offline-verifiable, not immutable.
- The existing short hero is out of scope and remains unchanged.

## Repository map

```text
cmd/                  runnable adapters and helper services
internal/             tested implementation packages
integrations/         Zendesk, Copilot, and n8n integration assets
cases/                synthetic business fixtures
config/               generated Talon config location and MCP templates
mock/                  no-key local Talon-compatible test endpoint
scripts/               setup, validation, orchestration, and assertions
docs/                  architecture, setup, presenter, and blocker guides
```

## Security

Only synthetic data belongs in this repository. Never commit provider keys, Talon keys, Zendesk settings, generated evidence, n8n credentials, or real customer content.
