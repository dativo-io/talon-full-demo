# Presenter runbook — 10–15 minutes

Use synthetic data only. Abort a scene when the application result or Talon evidence does not match the expected claim.

## Preflight

- `make validate-local` is green.
- Current Talon config was freshly bootstrapped and its source commit recorded.
- Talon runs on loopback with the expected three agents.
- OpenAI/Anthropic accounts are valid for the live cut.
- Zendesk installed private app was tested, not only ZCLI local mode.
- Copilot real BYOK path was tested.
- n8n workflow passed export/clean-import/rerun.
- MCP scene is skipped unless both blockers in `BLOCKERS.md` are fixed and regression-tested.

## 0:00 — Set the frame

Show the three real application surfaces and say:

> These are three separate AI use cases. Each keeps its own user experience, but their model traffic runs through one Talon control plane. We will show application output first, then the exact Talon record behind it.

Do not lead with compliance or evidence as the category.

## 1:00 — Zendesk Support

1. Open a synthetic refund ticket.
2. Point out the newest public requester comment; include synthetic email/IBAN data.
3. Click **Draft with Talon**.
4. Show the inserted draft and session ID returned by the adapter.
5. Inspect the corresponding Talon session/evidence before claiming PII handling or provider failover.

Boundary statement:

> The Zendesk app selected the message and inserted the reply. Talon controlled only the LLM request routed through its gateway. The adapter does not decide policy or report a provider path.

## 4:00 — GitHub Copilot CLI

1. Show `npm test` failing in the isolated billing fixture.
2. Start Copilot through the session shim.
3. Ask for the smallest correct patch.
4. Show the diff and passing test.
5. State that the shim injected session metadata only.
6. State that the fixture has no real remote and direct `git push` is denied by Copilot CLI.

### Optional MCP scene — currently blocked

Run only after Talon product exit criteria are complete:

1. Clear the synthetic receipt file.
2. Call `release_status` and `release_prepare`; show their upstream receipts.
3. Attempt `release_publish` through Talon MCP.
4. Show Talon's native denial reason and authenticated agent/session evidence.
5. Run `scripts/assert-release-blocked.sh` to prove `release_publish` is absent upstream.

Do not substitute the direct safe MCP server for a Talon policy proof.

## 8:00 — n8n

1. Open the imported workflow built in the pinned UI.
2. Run against the three synthetic quarterly-report sections.
3. Show section files created after successful requests.
4. Show the real third HTTP response and Talon evidence before describing a session-budget denial.
5. Assemble the deterministic partial report with `scripts/assemble-n8n-report.sh`.

Say explicitly that session limits are soft caps and the denied new request had zero provider cost only when the evidence confirms no dispatch.

## 11:00 — Operator view

Show the real running gateway:

```bash
talon agents --url "$TALON_GATEWAY"
talon agents show document-summary --url "$TALON_GATEWAY"
talon audit list --session "$TALON_N8N_SESSION_ID"
```

The truthful expected normal final state is:

```text
customer-support   healthy
coding-assistant   healthy
document-summary   blocked
```

`document-summary` becomes blocked only from a real persistent period-cap/policy condition. A single coding denial does not create `needs-attention`.

## 13:00 — Offline verification

```bash
talon audit export --format signed-json --session "$TALON_N8N_SESSION_ID" --output .state/n8n.signed.json
talon audit verify --file .state/n8n.signed.json
```

Optionally alter one field in a copy and show verification fail. Describe the records as HMAC-signed, tamper-evident, and offline-verifiable—not immutable.

## 14:00 — Close

> The adoption path is one real AI use case first: route it through Talon in shadow mode, observe what policy would do, then enable one control. This repository makes the seams and the remaining limitations inspectable.
