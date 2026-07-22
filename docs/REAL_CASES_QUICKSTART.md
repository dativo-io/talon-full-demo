# Real cases: the short path

This is the recommended path for testing and presenting the demo against real providers. [SETUP.md](SETUP.md) remains the manual reference.

## What each level proves

| Command | External dependency | What it proves |
|---|---|---|
| `make validate-local` | None | Repository code, adapters, mock paths, presenter contracts, MCP contract, and billing fixture. |
| `make n8n-validate` | Docker | The committed workflow imports, executes, exports without credentials, clean-imports, and executes again in pinned n8n `2.30.4`. |
| `make live-check` | Talon checkout | A real Talon binary enforces MCP policy, signs evidence, and applies the real session-budget engine. |
| `make demo-support-buyer` / `-tech` | OpenAI | Real support redaction, policy-valid failover, cost, and evidence. |
| `make demo-zendesk-buyer` / `-tech` | OpenAI | Real local Zendesk adapter → Talon → provider path and evidence. |
| `make zendesk-package` | None | Credential-free ZIP structure, icon, manifest, secret scan, and SHA-256. |
| `make zendesk-zcli-package` | Authenticated Zendesk | Official ZCLI server-side validation and package. |
| `make demo-copilot-buyer` / `-tech` | OpenAI + Copilot CLI | Real Copilot model/MCP path, identity, cost, receipts, and evidence. |
| `make demo-n8n-buyer` / `-tech` | Anthropic + Docker | Real imported n8n workflow, preserved partial output, budget stop, and evidence. |

## 1. Prepare once

```bash
cd ~/talon-full-demo
export OPENAI_API_KEY='sk-...'
export ANTHROPIC_API_KEY='sk-ant-...'
make real-prepare
make real-start
make real-status
```

Anthropic is required only for the n8n/document-summary case. `real-prepare` stores provider keys in Talon's encrypted local vault, not in `.env`.

## 2. Validate repository-owned artifacts

```bash
make validate-local
make n8n-validate
make live-check
make zendesk-package
```

`n8n-validate` performs two clean imports and executions. `zendesk-package` builds an offline-inspected ZIP; it is not Zendesk server validation.

## 3. Customer-support case

Buyer view:

```bash
make demo-support-buyer
```

Technical view:

```bash
make demo-support-tech
```

Re-present the same session:

```bash
make present-support-all
```

Expected path:

```text
email + IBAN detected and redacted
  → preferred local-llama route fails
  → disallowed openai-batch is skipped
  → OpenAI is selected
  → reply is produced
  → cost and signed evidence are verified
```

## 4. Zendesk adapter and private app

Run the real local adapter path:

```bash
make demo-zendesk-buyer
make demo-zendesk-tech
```

Build the account-independent ZIP:

```bash
make zendesk-package
```

Authenticate ZCLI and run official Zendesk validation/package:

```bash
zcli login -i
make zendesk-zcli-package
```

Expose only `127.0.0.1:8443` through an authenticated HTTPS tunnel. Install `.state/zendesk-app/talon-reply-assistant.zcli.zip` privately and configure:

- `adapter_domain`: tunnel hostname only;
- `adapter_token`: `ZENDESK_ADAPTER_TOKEN` from `.env`, as the secure header-scoped setting.

Use a synthetic ticket with requester public comments plus agent/private comments. Confirm the app selects the newest public requester comment and inserts only the returned draft. Then record the installed-app gate:

```bash
export ZENDESK_INSTALLED_TICKET_ID='<ticket-id>'
export ZENDESK_INSTALLED_SESSION_ID='<session-id-shown-by-the-app>'
export ZENDESK_PRIVATE_APP_INSTALLED=yes
export ZENDESK_SECURE_SETTING_CONFIRMED=yes
export ZENDESK_NEWEST_REQUESTER_COMMENT_CONFIRMED=yes
export ZENDESK_DRAFT_INSERTED_CONFIRMED=yes
make verify-zendesk-installed
```

Browser behavior is operator-confirmed. Talon identity, provider path, redaction, cost, and signatures are machine-verified.

## 5. GitHub Copilot CLI

Install once:

```bash
make copilot-install
```

Choose one audience flow:

```bash
make demo-copilot-buyer
make demo-copilot-tech
```

Re-present the same session:

```bash
make present-copilot-all
```

The driver mints a fresh session and nonce, routes model traffic through Talon, permits only `release_status` and `release_prepare`, denies shell/write operations in the client, enforces a 90-second limit, and independently verifies upstream receipts and signed Talon evidence.

Talon proves only model and MCP traffic routed through its boundaries. This scene does not claim control over local shell, filesystem, browser, or direct API actions.

## 6. n8n partial-output workflow

The committed source of truth is:

```text
integrations/n8n/quarterly-compliance-workflow.json
```

Run for a buyer:

```bash
make demo-n8n-buyer
```

Run for a technical reviewer:

```bash
make demo-n8n-tech
```

Re-present the same session:

```bash
make present-n8n-all
```

The workflow reads synthetic Markdown sections sequentially through Talon's `document-summary` identity. Each completed summary is written before the next request. When Talon returns `403 session_budget_exceeded`, n8n writes `status.json` and ends normally. The denied request must have zero provider cost, and the presenter verifies the complete signed session.

Session limits are soft caps: completed requests may consume budget before the next request is denied.

## Stop and restart

```bash
make real-stop
```

A later `make real-start` mints a new run identity. Run `make real-prepare` again only when provider keys, generated local keys, or canonical Talon configuration change.

## Common failures

### Provider authentication, quota, or billing errors

Correct the provider account/key, then rerun:

```bash
make real-prepare
make real-start
```

### Authenticated ZCLI reports authorization failure

Current ZCLI requires Zendesk authentication for validation and packaging:

```bash
zcli login -i
# or export ZENDESK_SUBDOMAIN and ZENDESK_OAUTH_TOKEN
make zendesk-zcli-package
```

### Ollama is running

Stop it before the support/Zendesk cases. Those scenes intentionally require the preferred local provider to fail.

### Port 8080 or 8081 is already in use

```bash
make real-stop || true
sudo ss -ltnp 'sport = :8081'
```

Stop only the stale process you recognize, then rerun `make real-start`.

### `.env` is missing but `.state/talon` exists

The encrypted state is tied to the original `TALON_SECRETS_KEY`. Restore the matching `.env`, or deliberately reset:

```bash
make real-stop || true
rm -rf .state config/generated .env
make real-prepare
```
