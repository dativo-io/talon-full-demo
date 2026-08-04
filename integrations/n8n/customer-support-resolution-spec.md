# Customer-support resolution workflow contract

## Business input

The case reads three synthetic Markdown files from `cases/customer-support-resolution`:

1. duplicate-charge ticket `SUP-1042` with a synthetic customer email and IBAN;
2. account and charge context showing two matching EUR 249 charges;
3. a refund policy requiring support and finance approval.

The files are combined into one case package. n8n, not Talon, reads the local files.

## Rendered workflow

`integrations/n8n/customer-support-resolution-workflow.json` is the credential-free base graph. `scripts/render-support-resolution-workflow.py` deterministically adds the operator gate and publish-safe output rules before import.

```text
Manual Trigger
  → read and assemble ticket + account context + refund policy
  → POST through Talon as `customer-support` to local-llama
      → real path: local connection failure
      → openai-batch skipped by provider policy
      → OpenAI fallback returns a body-only reply draft
  → POST a second governed request declaring `issue_refund`
      → Talon returns HTTP 403 before provider dispatch
  → create approval request bound to session + run nonce + ticket + amount + action
  → wait for explicit operator decision
      → approve: create signed approval receipt + synthetic finance handoff
      → reject: create signed rejection receipt and no finance handoff
  → write final reply and status only after the decision
```

The main real-demo command remains blocked while the operator gate is pending. Before a decision, the workflow must not create:

- `customer-support-resolution.md`;
- `status.json`;
- `operator-approval-receipt.json`;
- `finance-refund-request.json`.

## Talon request contract

Both governed model requests use:

- operational identity: `customer-support`;
- session: `TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID`;
- client attribution: `n8n-customer-support-resolution-full-demo`;
- ephemeral n8n Header Auth credential generated under `.state`;
- the OpenAI-compatible gateway surface.

The first request uses the configured `local-llama` route and Talon's policy-valid fallback chain. The second request goes directly to the allowed OpenAI destination so the denial is caused by tool policy, not provider availability.

The action request intentionally declares only `issue_refund` and forces that tool choice. With `tool_policy_action: block` and the customer-support overlay, Talon rejects the whole request before an upstream provider sees it.

## Operator gate contract

The loopback approval service binds only to `127.0.0.1`. The request contains:

```json
{
  "approval_id": "apr_...",
  "session_id": "n8n-support-resolution-...",
  "run_nonce": "...",
  "ticket_id": "SUP-1042",
  "amount_eur": 249,
  "requested_action": "issue_refund",
  "refund_executed": false,
  "status": "pending"
}
```

The operator must either use the rendered approval page or run one of these commands in a second shell:

```bash
make approve-n8n-support-resolution
make reject-n8n-support-resolution
```

A decision for a different approval ID, session, nonce, ticket, amount, or action cannot release the waiting execution.

The operator receipt is HMAC-SHA256 signed with a fresh demo-run key. It is a proof source separate from Talon's signed evidence:

- Talon evidence proves AI identity, data handling, route selection, model cost, and tool denial;
- the operator receipt proves the exact human decision that released workflow continuation.

Approval does not expose `issue_refund` to the model and does not execute a refund. It authorizes only creation of a synthetic finance handoff.

## Output contract

The model is asked for a body-only reply. n8n owns the final closing:

```text
Best regards,
ACME Support Team
```

The workflow fails closed if the model output contains a redaction placeholder, the raw synthetic email or IBAN, or a claim that the refund was already executed.

Every completed branch writes:

- `customer-support-resolution.md`;
- `operator-approval-receipt.json`;
- `status.json`.

The approved branch additionally writes `finance-refund-request.json`. The rejected branch must not create that file.

Approved status includes:

```json
{
  "result": "governed_support_resolution",
  "operator_decision": "approved",
  "action_status": "approved_for_finance_processing",
  "finance_handoff_file": "finance-refund-request.json",
  "refund_executed": false
}
```

Rejected status includes:

```json
{
  "result": "governed_support_resolution_rejected",
  "operator_decision": "rejected",
  "action_status": "human_rejected",
  "finance_handoff_file": null,
  "refund_executed": false
}
```

Both statuses also preserve the session, run nonce, approval ID, requested model, provider-reported model, zero denied-request cost, and the `issue_refund` denial.

## Required real proof

The presenter must verify one matching session that proves:

- email and IBAN detected and redacted at confidential tier;
- failed `local-llama` attempt with `connection_error`;
- `openai-batch` skipped by `agent_provider_allowlist`;
- OpenAI selected as the policy-valid fallback;
- a later denied record whose requested and filtered tools include `issue_refund`;
- zero provider cost for the denied tool-schema request;
- every Talon HMAC signature validates;
- the separate operator receipt signature validates;
- approval/rejection fields match the application status exactly;
- an approved finance handoff was created after the human decision;
- a rejected request produced no finance handoff.

## Validation

`make n8n-support-resolution-validate`:

1. renders the operator-gated workflow;
2. executes it against mock Talon with explicit auto-approval;
3. exports it without credential values;
4. imports and executes the export in a second clean n8n `2.30.4` runtime;
5. executes the rejection branch;
6. verifies signed operator receipts and branch-specific artifacts.

`scripts/test-support-approval-gate.sh` separately proves that the long-poll remains blocked before a decision, a mismatched approval cannot release it, and explicit approval or rejection releases the correct request.

The mock path proves workflow branching, approval gating, and credential hygiene. It does not prove real provider fallback, PII redaction, Talon cost accounting, or Talon evidence signatures; those claims require the real presenter.

## Truth boundaries

- All ticket, account, policy, approval, and finance data are synthetic.
- The generated response is a draft, not proof of correctness.
- Talon does not execute, approve, or decline the refund.
- The operator gate controls workflow continuation, not payment execution.
- The action proof covers the tool schema in the routed request. Direct payment-system calls or provider requests bypassing Talon remain outside the proof.
- Talon evidence and the operator receipt are tamper-evident and independently verifiable, not immutable.
