# Audience-specific demo views

Every application case follows one rule:

```text
real application execution -> Talon evidence -> buyer projection / technical projection
```

The buyer and technical views never use separate fixtures or presenter-authored success data. Each presenter recreates a signed session export, verifies it, and derives its output from the same evidence. The customer-support resolution additionally verifies a separate signed operator-decision receipt before presenting a completed result.

## Command matrix

| Application case | Buyer view | Technical view | Re-present completed run |
|---|---|---|---|
| Customer-support gateway | `make demo-support-buyer` | `make demo-support-tech` | `make present-support-all` |
| Zendesk adapter | `make demo-zendesk-buyer` | `make demo-zendesk-tech` | `make present-zendesk-all` |
| GitHub Copilot CLI | `make demo-copilot-buyer` | `make demo-copilot-tech` | `make present-copilot-all` |
| n8n quarterly workflow | `make demo-n8n-buyer` | `make demo-n8n-tech` | `make present-n8n-all` |
| n8n vendor-contract review | `make demo-n8n-vendor-review-buyer` | `make demo-n8n-vendor-review-tech` | `make present-n8n-vendor-review-all` |
| n8n customer-support resolution | `make demo-n8n-support-resolution-buyer` + explicit approval/rejection in shell 2 | `make demo-n8n-support-resolution-tech` + explicit approval/rejection in shell 2 | `make present-n8n-support-resolution-all` |

All real-provider cases require `make real-prepare`, `make real-start`, and a healthy `make real-status` first. Every n8n case additionally requires Docker. The quarterly and vendor-review cases require Anthropic; the support-resolution case requires OpenAI and a literal operator decision before it can complete.

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

Build and inspect the private-app ZIP without an account:

```bash
make zendesk-package
```

This hosted-CI gate proves required files, manifest shape, ticket-editor icon, deterministic packaging, and absence of generated credential values. It does not claim Zendesk server-side validation.

Authenticate ZCLI and run the official validation/package gate:

```bash
zcli login -i
make zendesk-zcli-package
```

Current ZCLI requires Zendesk authentication for `apps:validate` and `apps:package`. The hosted workflow runs this step automatically only when Zendesk OAuth repository secrets are configured.

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

## 5. n8n vendor-contract review

The repository contains `integrations/n8n/vendor-contract-review-workflow.json` and three synthetic input documents under `cases/vendor-contract-review`.

Validate the artifact without provider credentials:

```bash
make n8n-vendor-review-validate
```

The clean-import gate uses a deterministic mock with the real egress error shape. It must deny the OpenAI destination at zero provider cost, allow the Anthropic review, export no credential value, clean-import, and reproduce the same result.

Run the real application path:

```bash
make demo-n8n-vendor-review-buyer
make demo-n8n-vendor-review-tech
```

The workflow combines a synthetic vendor profile, proposed DPA, and internal review criteria. It first sends the confidential package toward OpenAI as a negative probe. Talon's `vendor-contract-review` egress rule denies that destination before upstream access. The workflow then sends the same package to the approved Anthropic destination; Talon redacts the synthetic email and IBAN and records the allowed decision in the same session.

n8n writes:

- `.state/n8n-vendor-review-output/vendor-contract-review.md` — the advisory review packet;
- `.state/n8n-vendor-review-output/status.json` — the application result linking denied and approved destinations.

The presenter fails unless all of the following agree:

- the review and status artifacts exist and reference the requested session;
- every record belongs to `vendor-contract-review`;
- signed evidence contains a zero-cost OpenAI `egress_*_destination_disallowed` decision;
- signed evidence later contains an allowed Anthropic egress decision;
- the allowed request is confidential tier and proves email + IBAN redaction;
- every exported signature verifies.

The model output is an advisory first pass. Talon does not decide whether the vendor terms are legally sufficient, and the demo does not claim compliance.

## 6. n8n customer-support resolution

The repository contains a credential-free base workflow at `integrations/n8n/customer-support-resolution-workflow.json`, a deterministic operator-gate renderer, and three synthetic inputs under `cases/customer-support-resolution`:

- duplicate-charge ticket `SUP-1042` with a customer email and IBAN;
- account context showing two matching EUR 249 charges;
- refund policy requiring human support and finance approval.

Validate the complete rendered workflow without provider credentials:

```bash
make n8n-support-resolution-validate
```

The gate:

1. renders the blocking operator nodes into the base graph;
2. imports and executes it against mock Talon;
3. proves no final artifacts exist while approval is pending;
4. explicitly approves the first run;
5. exports without credential values;
6. clean-imports and approves the exported graph in a second n8n `2.30.4` runtime;
7. runs a rejection branch and proves no finance handoff is created;
8. verifies the HMAC-signed operator receipts.

The mock does not claim to prove real failover, PII handling, provider cost, or Talon signatures.

### Run the interactive real path

In shell 1:

```bash
make demo-n8n-support-resolution-buyer
```

The first model request goes through the preferred local provider. With Ollama intentionally offline, Talon records the failed route, skips `openai-batch` because the use case may not reach it, selects OpenAI, redacts email and IBAN, and returns a body-only customer-reply draft.

A later request in the same session declares and forces the `issue_refund` function. The customer-support overlay forbids that tool, while the organization policy uses block mode. Talon rejects the request before provider dispatch at zero provider cost.

The same n8n execution then creates an approval request bound to:

```text
approval ID
Talon session ID
run nonce
ticket SUP-1042
EUR 249 amount
issue_refund action
```

At that point shell 1 prints:

```text
HUMAN APPROVAL REQUIRED
...
The workflow is blocked. No final status or finance handoff exists yet.
```

The command remains running. In shell 2, inspect the pending request and choose exactly one outcome:

```bash
make status-n8n-support-resolution-approval

make approve-n8n-support-resolution
# or:
make reject-n8n-support-resolution
```

The loopback approval page shown by shell 1 provides the same Approve and Reject controls. On a remote Ubuntu host, use the terminal target or forward the printed loopback port through SSH.

### Approved branch

Only after explicit approval does n8n write:

- `.state/n8n-support-resolution-output/customer-support-resolution.md` — clean reply with application-owned `ACME Support Team` sign-off;
- `.state/n8n-support-resolution-output/operator-approval-receipt.json` — HMAC-signed exact-request approval;
- `.state/n8n-support-resolution-output/finance-refund-request.json` — synthetic finance handoff created after approval;
- `.state/n8n-support-resolution-output/status.json` — completed application state.

The refund remains unexecuted. Approval authorizes only the synthetic finance handoff, not the AI tool and not a payment call.

### Rejected branch

After explicit rejection, n8n writes the clean reply, signed rejection receipt, and rejection status. It does not create `finance-refund-request.json`.

### Output safety

The governed model is asked for reply body only. n8n appends the deterministic closing. The workflow fails closed when the body contains:

- a redaction placeholder such as `[[PERSON]]`;
- the raw synthetic email or IBAN;
- a claim that the refund has already been issued, completed, processed, or returned.

### Presentation proof

After shell 1 resumes, it presents the buyer or technical receipt. Re-present the same run without another provider call with:

```bash
make present-n8n-support-resolution
make present-n8n-support-resolution-tech
make present-n8n-support-resolution-all
```

The presenter fails unless all of the following agree:

- final application artifacts match the requested session and ticket;
- every Talon record belongs to `customer-support`;
- signed Talon evidence proves confidential-tier email and IBAN redaction;
- signed Talon evidence proves local-provider failure, skipped disallowed candidate, and approved OpenAI fallback;
- a later signed Talon record shows `issue_refund` requested and filtered under a denied policy decision;
- the denied request has zero provider cost;
- every exported Talon signature verifies;
- the separate operator receipt HMAC verifies;
- the receipt matches the session, nonce, ticket, amount, action, and application status;
- an approved finance handoff is timestamped after the operator decision;
- rejection produced no finance handoff.

The presenter distinguishes the proof sources:

```text
Talon evidence
  -> AI identity, data handling, route selection, cost, and tool denial

Operator receipt
  -> exact human decision that released workflow continuation
```

Talon does not execute, approve, or decline the refund. The operator gate does not change Talon's tool policy. It controls only whether the workflow may create a synthetic finance handoff after Talon has denied AI authority.

## Presentation order

For most buyer meetings:

1. `make demo-n8n-support-resolution-buyer`, then approve or reject in shell 2 — broadest story: useful output, PII handling, reliability, financial-action control, and literal human control
2. `make demo-n8n-vendor-review-buyer` when confidential documents or approved-provider boundaries matter
3. `make demo-copilot-buyer` when coding-agent governance matters
4. `make demo-n8n-buyer` when workflow cost control is relevant
5. expand one scene with its technical presenter only when the audience asks how the proof works.

For a platform or security review:

1. `make demo-n8n-support-resolution-tech`, then make the explicit decision in shell 2
2. `make demo-n8n-vendor-review-tech`
3. `make demo-copilot-tech`
4. `make demo-n8n-tech`
5. `make live-check` for the separate adversarial MCP denial and hermetic budget-engine proof.

Use the direct support and Zendesk scenes when the buyer specifically owns customer-support operations or wants to inspect an adapter/private-app path. Pair the Zendesk adapter proof with the offline-inspected package, but make the Zendesk-validated or installed-app claim only after the authenticated ZCLI and account/browser gates are complete.

## Truth boundaries

- Talon claims only the traffic and actions routed through its interception boundaries.
- Provider routes, redaction, cost, identity, denials, and Talon signatures come from Talon evidence.
- A blocked tool schema proves the tool was not offered through that governed provider request; it is not proof about payment actions outside Talon.
- Talon does not execute, approve, or decline refunds.
- The support operator gate is a separate synthetic workflow-continuation control, not a Talon product claim or payment-system integration.
- The HMAC operator receipt proves the explicit decision for the exact synthetic request; it does not prove a real organizational approver identity.
- Approval creates only a synthetic finance handoff. Rejection creates no handoff. Neither branch executes a refund.
- An offline Zendesk ZIP is not described as Zendesk server-validated.
- Zendesk UI behavior is operator-confirmed; the backend session is machine-verified.
- n8n results require real workflow artifacts and matching evidence, never the specification alone.
- Session budgets are soft caps: completed requests may consume budget before the next request is denied.
- Vendor-review outputs are advisory and synthetic; human legal, privacy, security, and procurement review remains required.
- All customer-support ticket, account, approval, and finance data in this repository are synthetic.
- HMAC evidence and receipts are tamper-evident and offline-verifiable, not immutable.
