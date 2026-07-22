# Zendesk private app

The app runs in the Support ticket editor, selects the newest public requester comment, calls the private adapter through Zendesk's server-side request proxy, and inserts only the returned draft.

Configure:

- `adapter_domain` — authenticated HTTPS tunnel hostname only, with no scheme or path;
- `adapter_token` — secure, header-scoped setting.

## Build and inspect the credential-free ZIP

```bash
make zendesk-package
```

This account-independent command validates the repository contract, builds a deterministic ZIP, checks required Zendesk files including `icon_ticket_editor.svg`, scans for generated credential values, computes SHA-256, and writes:

```text
.state/zendesk-app/talon-reply-assistant.offline.zip
.state/zendesk-app/package.env
```

Hosted CI runs this command and uploads the inspected ZIP as a workflow artifact. This is a package-integrity gate, not Zendesk server-side validation.

## Run official authenticated ZCLI validation

Current ZCLI requires Zendesk authentication for both `apps:validate` and `apps:package`. Authenticate with a profile or OAuth environment variables, then run:

```bash
zcli login -i
make zendesk-zcli-package
```

Or in a headless shell:

```bash
export ZENDESK_SUBDOMAIN='<subdomain>'
export ZENDESK_OAUTH_TOKEN='<oauth-token>'
make zendesk-zcli-package
```

The command uses pinned `@zendesk/zcli` `1.1.4`, retains diagnostics, inspects the resulting ZIP, and writes `.state/zendesk-app/talon-reply-assistant.zcli.zip`. The hosted workflow also runs this step automatically when repository secrets `ZENDESK_SUBDOMAIN` and `ZENDESK_OAUTH_TOKEN` are configured.

## Install in a real Zendesk account

The local ZCLI server does not exercise secure settings. Install the authenticated ZCLI package privately using ZCLI or Admin Center, then configure the two settings above.

Use a synthetic ticket containing, in descending comment history:

1. an agent-authored public comment;
2. a private requester comment;
3. the newest public requester comment containing a synthetic email and IBAN;
4. an older public requester comment.

Click **Draft governed reply**. Confirm that:

- the newest public requester comment was selected;
- the returned draft, and nothing else, was inserted into the editor;
- the app displayed the returned `zendesk-ticket-...` session id.

## Record the final installed-app validation

```bash
export ZENDESK_INSTALLED_TICKET_ID='<ticket-id>'
export ZENDESK_INSTALLED_SESSION_ID='<session-id-shown-by-the-app>'
export ZENDESK_PRIVATE_APP_INSTALLED=yes
export ZENDESK_SECURE_SETTING_CONFIRMED=yes
export ZENDESK_NEWEST_REQUESTER_COMMENT_CONFIRMED=yes
export ZENDESK_DRAFT_INSERTED_CONFIRMED=yes
make verify-zendesk-installed
```

The command machine-verifies the matching Talon session: `customer-support` identity, `zendesk-support-full-demo` client attribution, email and IBAN redaction, local-provider failure, approved OpenAI fallback, session cost, and all HMAC signatures. It records the four browser-only observations as an explicit operator attestation linked to the package and evidence hashes.

The resulting attestation is not independent browser automation. It clearly distinguishes operator-confirmed UI facts from machine-verified Talon evidence.
