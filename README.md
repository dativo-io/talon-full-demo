# Talon Full Demo

A standalone 10–15 minute interactive demonstration of three recognizable applications routed through one [Dativo Talon](https://github.com/dativo-io/talon) control plane:

1. **Zendesk Support** — a private ticket-editor app requests a governed reply draft.
2. **GitHub Copilot CLI** — Copilot fixes a real failing fixture through Talon's OpenAI-compatible gateway and connects to a synthetic release MCP service through Talon's MCP proxy.
3. **n8n** — a document workflow preserves partial output when a session-budget denial stops the next model request.

The story is operational, not a longer hero animation: applications do useful work, Talon changes the behavior of traffic routed through it, the operator inspects the outcome, and signed evidence can be exported and verified offline.

## Honest status

| Area | Status |
|---|---|
| Go session shim, Zendesk adapter, synthetic release MCP server | Locally built, unit-tested, and exercised over real local HTTP |
| Zendesk private app | Manifest and browser logic tested locally; real private-app install and secure-setting substitution remain external |
| Copilot billing fixture | Dependency-free; proven failing before the expected patch and passing after it |
| Copilot BYOK/model path | Configuration reconciled with current Copilot CLI docs; not executed here against the real CLI |
| n8n | Loopback-only Compose and implementation specification present; no fabricated workflow export |
| Talon gateway configuration | Bootstrapped from `dativo-io/talon/examples/product-demo`, not copied as a stale permanent fork |
| Current Talon compatibility | Source-audited against `main` commit `631695d8713337cee3bef79e65225e40ba03c923`; current Talon was not built or run in this validation environment |
| MCP release-denial scene | **Blocked for release claims**: current Talon still has the unset-mode fail-open defect ([#346](https://github.com/dativo-io/talon/issues/346)) and hardcoded MCP evidence attribution ([#350](https://github.com/dativo-io/talon/issues/350)) |
| Real provider/evidence choreography | Not executed; requires provider keys and a live Talon runtime |

See [docs/VALIDATION.md](docs/VALIDATION.md) and [docs/BLOCKERS.md](docs/BLOCKERS.md).

## Local no-key validation

```bash
make validate-local
```

This runs Go formatting checks, unit tests and vet, Zendesk JavaScript tests, shell syntax checks, a local HTTP integration harness, the billing fixture before/after proof, and a Docker Compose check when Docker is available. The local gateway is an explicitly labelled mock; it does not produce Talon evidence.

## Standalone setup

```bash
# Repositories should be siblings.
git clone https://github.com/dativo-io/talon.git ../talon

make env
TALON_REPO=../talon make bootstrap-config
```

Then follow [docs/SETUP.md](docs/SETUP.md). Use [docs/PRESENTER_RUNBOOK.md](docs/PRESENTER_RUNBOOK.md) only after its evidence and external-service gates pass.

## Integration boundaries

```text
Zendesk ticket editor
  → Zendesk server-side request proxy
  → public HTTPS adapter
  → Talon /v1/proxy/local-llama/v1/chat/completions

GitHub Copilot CLI
  → transparent session-header shim
  → Talon OpenAI-compatible endpoint

Copilot remote HTTP MCP
  → Talon /mcp/proxy
  → synthetic release MCP server

n8n HTTP Request node
  → Talon /v1/proxy/anthropic/v1/messages
```

The adapters provide transport, stable session metadata, and credential isolation. They do **not** perform governance.

## Truth rules

- Every successful-looking receipt shown during the live demo must come from application output, Talon evidence, or an unmistakably labelled mock.
- Real mode uses synthetic data only.
- HMAC evidence is **tamper-evident and offline-verifiable**, not immutable.
- Session limits are **soft caps**.
- Talon controls only model traffic and actions routed through an interception boundary it actually owns.
- A single coding-tool denial does not manufacture `needs-attention`; the truthful normal final fleet is `customer-support healthy`, `coding-assistant healthy`, `document-summary blocked` only after real period-cap exhaustion.
- Gateway shadow mode is process-wide and restart-bound, not a per-agent live switch.
- Direct `git push` prevention in the Copilot command is a Copilot CLI safety setting, not a Talon feature.

## Repository map

```text
cmd/          runnable adapters and safe helper services
internal/     tested Go implementation packages
integrations/ Zendesk, Copilot, and n8n assets
cases/        synthetic fixtures
config/       generated Talon config target and current MCP template
mock/         labelled no-key local test gateway
scripts/      setup, validation, orchestration, and assertions
docs/         architecture, setup, validation, blockers, and presenter guide
```

## Security

Only synthetic data belongs here. Do not commit `.env`, provider or Talon keys, Zendesk settings, n8n credentials, generated evidence, local state, or real customer content. Services bind to loopback by default; only the Zendesk adapter should be exposed, through an authenticated HTTPS tunnel for the installed private-app test.

Licensed under Apache-2.0.
