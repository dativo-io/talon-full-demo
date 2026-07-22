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

The real runner transparently stages `document-summary.policies.session_limits.max_cost` from the pinned canonical `$0.01` to `$0.00301` for the run. This sits just above the pinned `$0.003` pre-request estimate for 500 input and 500 output tokens on `claude-haiku-4-5`: one request can execute, then completed spend makes a later estimate cross the boundary. The runner refuses to alter an unpinned or operator-modified agent config and restores the canonical file on every exit.

## Validation contract

`make n8n-validate` proves import, execution, credential-free export, clean re-import, and second execution against the mock allow-then-deny contract. `make demo-n8n-buyer` and `make demo-n8n-tech` run the same committed graph through real Talon and Anthropic, then project buyer and technical views from the same signed Talon session.

The technical presenter reads `{limit, spent, estimate}` from the signed denial record. Staging metadata is not accepted as proof.

Session limits are soft caps. The workflow claims only that Talon denied the next request before provider dispatch after completed requests consumed the session budget.
