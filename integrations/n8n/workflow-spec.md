# Quarterly Compliance Report Summarizer

```text
Manual Trigger → Build Manifest → Loop Over Items → Read File → Extract Text → HTTP Request to Talon → Switch
  200 → write one `<order>-<slug>.summary.md` → continue
  403 session_budget_exceeded → write `status.json` → stop
  other → Stop And Error
```

Call `http://host.docker.internal:8080/v1/proxy/anthropic/v1/messages` with Header Auth and `X-Talon-Session-ID: {{$env.TALON_N8N_SESSION_ID}}`. Enable Never Error, response status/headers, JSON response, and 90-second timeout. Inspect the pinned node's actual output envelope before writing the Switch expression.
