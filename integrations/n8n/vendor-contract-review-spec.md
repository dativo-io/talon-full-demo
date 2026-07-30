# Vendor Contract Review — n8n workflow contract

The executable source of truth is `vendor-contract-review-workflow.json`, imported and executed by `scripts/n8n-vendor-review.sh` in pinned n8n `2.30.4`.

## Business flow

```text
Manual Trigger
  → read `/demo/input/*.md`
  → extract and combine the synthetic vendor package
  → POST the confidential package toward OpenAI through Talon
  → require `403 egress_*_destination_disallowed`
  → POST the same package toward the approved Anthropic destination
  → write `/demo/output/vendor-contract-review.md`
  → write `/demo/output/status.json`
```

The workflow deliberately makes a negative destination probe before the useful review. OpenAI and Anthropic are both configured for the agent; the agent-level egress rule, not provider availability or a missing secret, denies confidential-tier traffic to OpenAI. Talon evaluates the destination before retrieving the upstream secret or sending request bytes.

The approved Anthropic request uses the same input. The organization baseline plus this agent's input-scanning override detect and redact the synthetic email and IBAN. Classification remains confidential; redaction does not silently downgrade the tier.

## Request contract

Both requests use:

- authentication: generated `httpHeaderAuth` credential named `Talon vendor-contract-review`;
- session: `X-Talon-Session-ID: {{$env.TALON_N8N_VENDOR_REVIEW_SESSION_ID}}`;
- client: `X-Talon-Client: n8n-vendor-contract-review-full-demo`;
- timeout: 90 seconds;
- response: JSON, full status and headers, Never Error enabled.

Destinations:

- negative probe: `/v1/proxy/openai/v1/chat/completions`, model `gpt-4o-mini`;
- approved review: `/v1/proxy/anthropic/v1/messages`, model `claude-haiku-4-5`.

The committed workflow contains only the credential id/name reference. The credential JSON is generated under `.state/` and must never be committed or exported with its secret value.

## Application artifacts

A successful run must create:

- `vendor-contract-review.md` — model-generated advisory review with an explicit human-review warning;
- `status.json` — machine-readable result linking the denied and approved destinations to one Talon session.

`status.json` is an application artifact, not proof of enforcement. The presenter exports and verifies signed Talon evidence and fails closed unless it independently confirms:

- one `vendor-contract-review` session;
- a zero-cost OpenAI egress denial;
- an allowed Anthropic egress decision;
- confidential-tier email and IBAN detection with input redaction on the allowed request;
- valid signatures for every record;
- matching workflow artifacts and session id.

## Validation modes

`make n8n-vendor-review-validate` imports, executes, exports, clean-imports, and executes again against a deterministic mock that denies OpenAI with the real egress error schema and allows Anthropic.

`make demo-n8n-vendor-review-buyer` runs the same committed graph through real Talon and Anthropic. `make present-n8n-vendor-review-all` re-presents the completed session without making another model call.

## Truth boundary

The review is advisory and synthetic. Talon proves that the configured traffic boundary, redaction policy, attribution, and signed evidence operated on requests routed through it. It does not determine whether the vendor contract is legally sufficient, and it does not control document copies or provider calls that bypass Talon.
