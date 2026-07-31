# n8n integrations

This directory contains real, credential-free workflow exports for the pinned `n8n:2.30.4` runtime:

- `quarterly-compliance-workflow.json` — sequential document summaries with a session-budget stop;
- `vendor-contract-review-workflow.json` — confidential vendor-package review with an egress denial before an approved provider call;
- `customer-support-resolution-workflow.json` — duplicate-charge reply drafting with PII redaction, policy-valid fallback, and a blocked refund action;
- `compose.yaml` — loopback-only UI runtime for Ubuntu/Linux rehearsals;
- the accompanying `*-spec.md` files — human-readable behavior and truth contracts.

## Quarterly-report workflow

The workflow reads the three synthetic Markdown sections under `cases/quarterly-report`, processes them sequentially through Talon's `document-summary` identity, writes each completed summary, and stops cleanly when Talon returns `403 session_budget_exceeded`. Completed files remain available and `status.json` records which next section was not sent.

### Credential-free clean-import validation

```bash
make n8n-validate
```

This command uses pinned n8n `2.30.4` and mock Talon's allow-then-budget-deny contract to:

1. render an ephemeral Header Auth credential outside the repository;
2. import the committed workflow into a clean n8n runtime;
3. execute it sequentially;
4. verify one completed summary and a zero-cost budget denial;
5. export the workflow and assert that no credential value was included;
6. import that export into a second clean runtime;
7. execute and verify the same contract again.

No provider key is needed.

### Real Talon + Anthropic demo

Prepare the real stack with both provider keys once:

```bash
export OPENAI_API_KEY='sk-...'
export ANTHROPIC_API_KEY='sk-ant-...'
make real-prepare
make real-start
```

Run and present:

```bash
make demo-n8n-buyer
make present-n8n-all
```

The real runner stages the pinned `document-summary` session cap from its canonical `$0.01` value to `$0.00301` for this one run. Talon's pinned pre-request estimate for `claude-haiku-4-5` is `$0.003`, so the first section can run and completed spend makes a later request cross the staged boundary. The runner validates the pinned source and canonical value before editing and restores the original agent file on exit.

The presenter fails closed unless completed `*.summary.md` files, `status.json`, `document-summary` attribution, allowed work followed by `session_budget_exceeded`, zero provider cost on the denied request, valid Talon signatures, and the signed denial's `{limit, spent, estimate}` arithmetic all agree.

## Vendor-contract review workflow

The workflow reads three synthetic documents under `cases/vendor-contract-review`:

- a vendor profile containing a synthetic contact email and billing IBAN;
- a proposed data-processing addendum;
- ACME's synthetic vendor-review criteria.

It combines them into one confidential review package and runs two requests in the same Talon session:

```text
OpenAI destination probe
  → Talon denies confidential-tier egress before provider access
  → zero provider cost

Approved Anthropic review
  → Talon redacts email + IBAN
  → Anthropic creates an advisory review packet
  → n8n writes vendor-contract-review.md + status.json
```

OpenAI and Anthropic are both configured for the `vendor-contract-review` identity. The negative request is denied by the agent's egress rule, not by missing credentials or provider availability. The allowed request stays confidential-tier after redaction and is recorded in the same signed session.

### Credential-free clean-import validation

```bash
make n8n-vendor-review-validate
```

The gate imports, executes, exports without credential values, clean-imports, and executes again against a mock matching Talon's egress error contract.

### Real Talon + Anthropic demo

```bash
make demo-n8n-vendor-review-buyer
make present-n8n-vendor-review-all
```

The buyer and technical views fail closed unless application artifacts and signed evidence agree on:

- `vendor-contract-review` attribution;
- a zero-cost OpenAI egress denial;
- a later allowed Anthropic decision;
- confidential-tier email and IBAN redaction;
- matching session identity and valid signatures.

The model output is an advisory first pass, not legal advice or a compliance determination.

## Customer-support resolution workflow

The workflow reads three synthetic inputs under `cases/customer-support-resolution`:

- a duplicate-charge ticket containing an email and IBAN;
- account and charge context;
- a refund policy requiring human support and finance approval.

It produces one reply draft and then exercises the financial-action boundary in the same Talon session:

```text
Draft request through preferred local provider
  → local provider is unavailable
  → disallowed openai-batch candidate is skipped
  → approved OpenAI fallback receives redacted input
  → reply draft completes

Autonomous refund-action branch
  → request declares the issue_refund tool
  → Talon blocks the request before provider dispatch
  → denied provider cost is zero
  → n8n preserves the draft and writes human-approval status
```

Talon does not execute or approve the refund. The proof is that the governed model request could not expose `issue_refund` upstream; n8n then converted the structured denial into an explicit business state.

### Credential-free clean-import validation

```bash
make n8n-support-resolution-validate
```

The gate imports, executes, exports without credential values, clean-imports, and executes again against a mock reply-then-tool-denial contract. The mock does not prove real provider fallback; the real signed session does.

### Real Talon + OpenAI demo

```bash
make demo-n8n-support-resolution-buyer
make present-n8n-support-resolution-all
```

The presenters fail closed unless application artifacts and signed evidence agree on:

- `customer-support` attribution;
- confidential-tier email and IBAN redaction;
- local provider failure, skipped disallowed fallback, and approved OpenAI selection;
- a later `issue_refund` tool-schema denial;
- zero provider cost on the denied action request;
- matching session identity and valid signatures.

## Audit-capable presentation CLI

The already-running Talon service may use a released binary whose `audit export` command predates session-filtered signed exports. Runtime execution continues to use that service unchanged. Presentation commands select a compatible installed CLI or build and cache the repository-pinned CLI under `.state/talon-audit-cli/`. This does not restart or replace the running gateway.

## Optional UI import

The automated CLI runners are the canonical demo paths. To inspect one of the workflows in the n8n UI, render its Header Auth credential into `.state`, copy the selected committed workflow to `.state/n8n-config/workflow.json`, and start `integrations/n8n/compose.yaml`.

The Compose runtime uses Linux host networking because Talon deliberately binds only to host loopback. `N8N_LISTEN_ADDRESS=127.0.0.1` keeps the n8n UI loopback-only as well. Never commit generated credential files.

## Truth boundaries

- Session budgets are soft caps. Completed requests may consume budget before the next request is denied.
- The quarterly staged cap is a transparent demo policy change, not a hidden product claim.
- The vendor-review contract and data are synthetic; human legal, privacy, security, and procurement review remains required.
- The support-resolution ticket and account data are synthetic. Talon does not execute, approve, or decline the refund.
- A blocked tool schema proves that the tool was not offered through that governed provider request; it is not proof about actions outside Talon.
- Talon proves only controls applied to traffic routed through it. Direct model calls, document copies, or payment actions that bypass Talon are outside the proof.
- HMAC evidence is tamper-evident and offline-verifiable, not immutable.
