# Customer-support resolution workflow contract

## Business input

The committed workflow reads three synthetic Markdown files from `cases/customer-support-resolution`:

1. duplicate-charge ticket `SUP-1042` with a synthetic customer email and IBAN;
2. account and charge context showing two matching EUR 249 charges;
3. a refund policy that requires human support and finance approval.

The files are combined into one case package. n8n, not Talon, reads the local files.

## Workflow

```text
Manual Trigger
  → Read `/demo/input/*.md`
  → Extract UTF-8 text
  → Assemble one support case
  → POST through Talon as `customer-support` to local-llama
      → real path: local connection failure
      → openai-batch skipped by provider policy
      → OpenAI fallback returns the reply draft
  → POST a second governed request declaring `issue_refund`
      → Talon returns HTTP 403 before provider dispatch
  → write `/demo/output/customer-support-resolution.md`
  → write `/demo/output/status.json`
```

The refund-action request intentionally declares only the forbidden `issue_refund` function and forces that tool choice. With the product-demo organization default `tool_policy_action: block` and the full-demo customer-support overlay, Talon rejects the whole request before an upstream provider sees it.

## Talon request contract

Both requests use:

- operational identity: `customer-support`;
- session: `TALON_N8N_SUPPORT_RESOLUTION_SESSION_ID`;
- client attribution: `n8n-customer-support-resolution-full-demo`;
- ephemeral n8n Header Auth credential generated under `.state`;
- the OpenAI-compatible gateway surface.

The first request uses the configured `local-llama` route and relies on Talon's policy-valid fallback chain. The second request goes directly to the allowed OpenAI destination so the observed denial is caused by tool policy, not provider availability.

## Required application artifacts

`customer-support-resolution.md` must contain:

- the customer reply draft;
- an explicit statement that no refund was executed;
- the human support and finance approval requirement.

`status.json` must contain:

```json
{
  "result": "governed_support_resolution",
  "operational_id": "customer-support",
  "ticket_id": "SUP-1042",
  "refund_amount_eur": 249,
  "reply_draft_created": true,
  "blocked_tool": "issue_refund",
  "denial_code": "tool_governance_block",
  "denied_provider_cost_usd": 0,
  "action_status": "human_approval_required",
  "human_approval_required": true
}
```

## Required real evidence

The presenter must verify one matching session that proves:

- email and IBAN detected and redacted at confidential tier;
- failed `local-llama` attempt with `connection_error`;
- `openai-batch` skipped by `agent_provider_allowlist`;
- OpenAI selected as the policy-valid fallback;
- a later denied record whose requested and filtered tools include `issue_refund`;
- zero provider cost for the denied tool-schema request;
- all exported HMAC signatures validate.

## Clean-import validation

`make n8n-support-resolution-validate` executes the committed graph against mock Talon, exports it without credential values, imports the export into a second clean pinned n8n `2.30.4` runtime, and executes it again.

The mock gate proves workflow behavior and credential hygiene. It does not claim to prove real fallback, PII redaction, cost accounting, or signatures; those claims require the real Talon presenter.

## Truth boundaries

- All input is synthetic.
- The generated response is a draft, not proof of correctness.
- Talon does not execute, approve, or decline the refund.
- The action proof covers the tool schema in the routed request. Direct payment-system calls or provider requests bypassing Talon remain outside the proof.
- HMAC evidence is tamper-evident and offline-verifiable, not immutable.
