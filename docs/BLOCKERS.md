# Current blockers

Compatibility was source-audited against `dativo-io/talon/main` commit `631695d8713337cee3bef79e65225e40ba03c923` on 2026-07-19.

## MCP blocker 1 — unset mode can fail open

Open Talon issue: `#346`.

`internal/mcp/proxy_config.go` still does not default or validate `proxy.mode`. In `internal/mcp/proxy.go`, an explicitly forbidden tool is returned as blocked only for `intercept` and `shadow`; an empty mode falls through toward upstream forwarding after writing blocked-looking evidence.

This repository always sets:

```yaml
proxy:
  mode: intercept
```

That reduces configuration risk but does not close the product defect. A current-Talon regression test must prove a forbidden call never reaches upstream, including the omitted-mode case, before the scene is release-ready.

## MCP blocker 2 — evidence attribution

Open Talon issue: `#350`.

Current `recordEvidence` still writes:

```text
agent_id = mcp-proxy
correlation_id = newly generated mcp_proxy_* value
```

It does not preserve the authenticated coding-assistant identity or the incoming session/correlation metadata required to join the MCP decision to the Copilot session. The demo therefore cannot truthfully claim one session-level trail across Copilot model traffic and its MCP tool call.

## Required product exit criteria

- unset or unknown mode fails closed or is rejected;
- explicit intercept mode is regression-tested;
- forbidden `release_publish` never reaches the synthetic upstream;
- evidence contains the authenticated tenant and agent;
- session and correlation IDs are preserved under documented provenance;
- native reason/explanation values are displayed as emitted, not rewritten by the demo.

## Non-blocking external work

- install the Zendesk private app and prove secure-setting substitution;
- run real Copilot CLI BYOK and session-scoped MCP configuration;
- create/export/clean-import the n8n workflow in the pinned version;
- calibrate the real provider session budget;
- run evidence export, offline verification, and tamper-failure proof.

Until all MCP exit criteria are met, keep the PR and the MCP scene marked draft/blocked.
