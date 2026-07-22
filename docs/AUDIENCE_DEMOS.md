# Audience-specific demo views

Every application case follows one rule:

```text
real application execution -> Talon evidence -> buyer projection / technical projection
```

The buyer and technical views never use separate fixtures or presenter-authored success data. Each presenter recreates a signed session export, verifies it, and derives its output from the same evidence.

## Command matrix

| Application case | Buyer view | Technical view | Re-present completed run |
|---|---|---|---|
| Customer-support gateway | `make demo-support-buyer` | `make demo-support-tech` | `make present-support-all` |
| Zendesk adapter | `make demo-zendesk-buyer` | `make demo-zendesk-tech` | `make present-zendesk-all` |
| GitHub Copilot CLI | `make demo-copilot-buyer` | `make demo-copilot-tech` | `make present-copilot-all` |
| n8n workflow | `make demo-n8n-buyer` | `make demo-n8n-tech` | `make present-n8n-all` |

All real-provider cases require `make real-prepare`, `make real-start`, and a healthy `make real-status` first. The n8n case additionally requires Docker and an Anthropic key seeded by `real-prepare`.

## 1. Customer-support gateway

```bash
make demo-support-buyer
make demo-support-tech
```

The buyer receipt shows the `customer-support` identity, drafted reply, email and IBAN redaction, failed local provider, disallowed fallback skipped, approved OpenAI fallback, actual cost, and signed-evidence verification. The technical view expands the same session into native Talon audit records and the chronological failover path.

The generated prose is an application output, not the proof. The evidence is the proof.

## 2. Zendesk adapter and private app

```bash
make demo-zendesk-buyer
make demo-zendesk-tech
```

This proves:

```text
synthetic ticket request
  -> loopback Zendesk adapter
  -> Talon gateway as customer-support
  -> policy-valid provider path
  -> governed draft response
  -> signed session evidence
```

The technical view verifies `zendesk-support-full-demo` client attribution and that the returned session ID matches Talon evidence.

Package the actual private app with pinned ZCLI:

```bash
make zendesk-package
```

The resulting ZIP is content-checked, scanned for generated credentials, hashed, and uploaded as a hosted-CI artifact.

Installation inside Zendesk remains an account/browser operation. After observing private-app installation, secure-setting substitution, newest public requester-comment selection, and returned-draft insertion, record the final gate with:

```bash
export ZENDESK_INSTALLED_TICKET_ID='<ticket-id>'
export ZENDESK_INSTALLED_SESSION_ID='<session-id-shown-by-the-app>'
export ZENDESK_PRIVATE_APP_INSTALLED=yes
export ZENDESK_SECURE_SETTING_CONFIRMED=yes
export ZENDESK_NEWEST_REQUESTER_COMMENT_CONFIRMED=yes
export ZENDESK_DRAFT_INSERTED_CONFIRMED=yes
make verify-zendesk-installed
```

That command machine-verifies Talon evidence and records browser-only facts as operator-confirmed observations. It does not pretend Talon evidence proves DOM behavior inside Zendesk.

## 3. GitHub Copilot CLI

```bash
make demo-copilot-buyer
make demo-copilot-tech
```

Both views use the same real Copilot session. Talon proves the routed model and MCP surfaces, operational identity, cost, upstream receipts, and signatures. Local shell, filesystem, browser, and direct API actions remain outside this proof.

## 4. n8n partial-output workflow

The repository contains `integrations/n8n/quarterly-compliance-workflow.json`, a credential-free workflow export for pinned n8n `2.30.4`.

Validate the artifact without provider credentials:

```bash
make n8n-validate
```

The validation imports and executes the committed graph, exports it, proves the export contains no credential value, imports that export into a second clean runtime, and executes it again. Both runs must preserve one completed summary and stop the next request with a zero-cost budget denial.

Run the real application path:

```bash
make demo-n8n-buyer
make demo-n8n-tech
```

The workflow processes synthetic Markdown sections sequentially through Talon's `document-summary` identity. Completed sections are written under `.state/n8n-output`. When Talon returns `403 session_budget_exceeded`, n8n writes `status.json` and ends normally without processing another section.

The presenter fails unless all of the following agree:

- at least one completed `*.summary.md` section file;
- `.state/n8n-output/status.json` containing `session_budget_exceeded`;
- Talon evidence for the same session and `document-summary` identity;
- at least one allowed request followed by at least one budget denial;
- zero provider cost on every denied request;
- valid signatures for every exported record.

The buyer view shows preserved business output, the budget stop, denied-request cost, session spend, and evidence verification. The technical view adds native audit output, timeline, artifact paths, and the soft-cap boundary.

## Presentation order

For most buyer meetings:

1. `make demo-support-buyer`
2. `make demo-copilot-buyer`
3. `make demo-n8n-buyer` when workflow cost control is relevant
4. expand one scene with its technical presenter only when the audience asks how the proof works.

For a platform or security review:

1. `make demo-support-tech`
2. `make demo-copilot-tech`
3. `make demo-n8n-tech`
4. `make live-check` for the separate adversarial MCP denial and hermetic budget-engine proof.

Use the Zendesk scene when the buyer owns customer-support operations. Pair the adapter proof with the packaged private app; make the installed-app claim only after the explicit account/browser gate is recorded.

## Truth boundaries

- Talon claims only the traffic and actions routed through its interception boundaries.
- Provider routes, redaction, cost, identity, denials, and signatures come from Talon evidence.
- Zendesk UI behavior is operator-confirmed; the backend session is machine-verified.
- n8n results require real workflow artifacts and matching evidence, never the specification alone.
- Session budgets are soft caps: completed requests may consume budget before the next request is denied.
- HMAC evidence is tamper-evident and offline-verifiable, not immutable.
