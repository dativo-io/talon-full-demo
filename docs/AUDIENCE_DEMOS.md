# Audience-specific demo views

Every application case follows one rule:

```text
real application execution -> Talon evidence -> buyer projection / technical projection
```

The buyer and technical views never use separate fixtures or presenter-authored success data. Each presenter recreates a signed session export, verifies it, and then derives its output from that same evidence.

## Command matrix

| Application case | Buyer view | Technical view | Re-present completed run |
|---|---|---|---|
| Customer-support gateway | `make demo-support-buyer` | `make demo-support-tech` | `make present-support-all` |
| Zendesk adapter | `make demo-zendesk-buyer` | `make demo-zendesk-tech` | `make present-zendesk-all` |
| GitHub Copilot CLI | `make demo-copilot-buyer` | `make demo-copilot-tech` | `make present-copilot-all` |
| n8n workflow | external workflow run, then `make present-n8n` | external workflow run, then `make present-n8n-tech` | `make present-n8n-all` |

All real-provider cases require `make real-prepare`, `make real-start`, and a healthy `make real-status` first.

## 1. Customer-support gateway

### Buyer

```bash
make demo-support-buyer
```

The buyer receipt shows:

- the `customer-support` operational identity;
- that a reply was drafted;
- email and IBAN redaction before provider access;
- the failed local provider;
- the disallowed fallback candidate that was skipped;
- the approved OpenAI fallback;
- actual session cost;
- signed-evidence verification.

### Technical

```bash
make demo-support-tech
```

The technical view expands the same session into the native Talon session summary, chronological failover records, PII classification/redaction facts, route decisions, cost, and individual evidence commands.

The generated reply is an application output, not the proof. The evidence is the proof.

## 2. Zendesk adapter

### Buyer

```bash
make demo-zendesk-buyer
```

This sends one synthetic Zendesk-shaped ticket through the real local adapter and Talon. It shows the support outcome, PII handling, policy-valid failover, cost, and verified evidence.

### Technical

```bash
make demo-zendesk-tech
```

The technical view shows:

```text
synthetic ticket request
  -> loopback Zendesk adapter
  -> Talon gateway as customer-support
  -> policy-valid provider path
  -> governed draft response
  -> signed session evidence
```

It also verifies the adapter client attribution `zendesk-support-full-demo` and that the returned session ID matches the Talon evidence.

### Important external gate

This automated case proves the real **local adapter -> Talon -> provider** path. It does not prove:

- installation as a Zendesk private app;
- secure-setting substitution inside Zendesk;
- selection of the newest public requester comment;
- insertion into a real ticket editor.

Those claims require the installed private-app test described in [SETUP.md](SETUP.md#7-zendesk-private-app).

## 3. GitHub Copilot CLI

### Buyer

```bash
make demo-copilot-buyer
```

### Technical

```bash
make demo-copilot-tech
```

Both views use the same real Copilot session. See the main README and presenter runbook for the MCP and local-action truth boundaries.

## 4. n8n partial-output workflow

The repository does not yet contain a clean-imported n8n workflow export. The presenter therefore refuses to manufacture a result from the workflow specification alone.

After the pinned workflow has been built, exported without credentials, imported into a clean n8n `2.30.4` container, and run with `TALON_N8N_SESSION_ID`, present it with:

```bash
source .env
source .state/demo-run.env

TALON_PRESENT_N8N_SESSION_ID="$TALON_N8N_SESSION_ID" make present-n8n
TALON_PRESENT_N8N_SESSION_ID="$TALON_N8N_SESSION_ID" make present-n8n-tech
```

The presenter fails unless all of the following exist and agree:

- at least one completed `*.summary.md` section file;
- `.state/n8n-output/status.json` containing `session_budget_exceeded`;
- Talon evidence for the same session and `document-summary` identity;
- at least one allowed request followed by at least one budget denial;
- zero provider cost on every denied request;
- valid signatures for every exported record.

The buyer view shows the preserved partial business output, the budget stop, denied-request cost, session spend, and evidence verification. The technical view adds the native audit session, timeline, artifact paths, and soft-cap boundary.

## Presentation order

For most buyer meetings:

1. `make demo-support-buyer`
2. `make demo-copilot-buyer`
3. expand one of them with its technical presenter only when the audience asks how the proof works.

For a platform or security review:

1. `make demo-support-tech`
2. `make demo-copilot-tech`
3. `make live-check` for the separate adversarial MCP denial and real session-budget engine.

Use the Zendesk adapter case when the buyer owns customer-support operations. Add n8n only after its external workflow gate is complete.

## Truth boundaries

- Talon claims only the traffic and actions routed through its interception boundaries.
- Provider routes, redaction, cost, identity, denials, and signatures come from Talon evidence.
- Zendesk local-adapter proof is not private-app proof.
- n8n presenters require real imported-workflow artifacts; the specification alone is insufficient.
- Session budgets are soft caps: completed requests may consume budget before the next request is denied.
- HMAC evidence is tamper-evident and offline-verifiable, not immutable.
