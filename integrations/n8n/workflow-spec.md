# Quarterly Compliance Report Summarizer

The executable source of truth is `quarterly-compliance-workflow.json`, imported and executed by `scripts/n8n-workflow.sh` in pinned n8n `2.30.4`.

```text
Manual Trigger
  → Read `/demo/input/*.md`
  → Extract UTF-8 text and preserve filename metadata
  → Validate `<order>-<slug>.md`
  → Loop Over Sections (batch size 1)
  → POST through Talon as `document-summary`
  → inspect full HTTP response without throwing on non-2xx

    200
      → extract Anthropic text
      → write `/demo/output/<order>-<slug>.summary.md`
      → continue the loop

    403 + error.code=session_budget_exceeded
      → write `/demo/output/status.json`
      → stop without dispatching another section

    anything else
      → Stop And Error
```

## Request contract

- URL: `{{$env.TALON_N8N_GATEWAY_URL}}/v1/proxy/anthropic/v1/messages`
- authentication: generated `httpHeaderAuth` credential named `Talon document-summary`
- session: `X-Talon-Session-ID: {{$env.TALON_N8N_SESSION_ID}}`
- client: `X-Talon-Client: n8n-quarterly-report-full-demo`
- model: `claude-haiku-4-5`
- timeout: 90 seconds
- response: JSON, full status and headers, Never Error enabled

The credential JSON is rendered under `.state/` and imported separately. The committed workflow contains only the credential id/name reference, never a Talon key.

## Execution contract

The loop processes one section at a time. This is essential: completed output must exist before the next request encounters the session-budget boundary. The denial branch ends the workflow normally after writing `status.json`; unexpected provider or integration responses fail the workflow.

## Validation contract

`make n8n-validate` proves import, execution, credential-free export, clean re-import, and second execution against the mock allow-then-deny contract. `make demo-n8n-buyer` and `make demo-n8n-tech` run the same committed graph through real Talon and Anthropic, then project buyer and technical views from the same signed Talon session.

Session limits are soft caps. The workflow claims only that Talon denied the next request before provider dispatch after completed requests consumed the session budget.
