# Architecture and trust boundaries

## One control plane, four application paths

```text
Zendesk Support
  browser app
    → Zendesk server-side request proxy
    → HTTPS tunnel
    → zendesk-adapter (Talon key remains here)
    → Talon LLM gateway
    → selected provider

GitHub Copilot CLI model traffic
  Copilot CLI
    → copilot-session-shim (adds stable session/client headers only)
    → Talon LLM gateway
    → OpenAI-compatible provider

GitHub Copilot CLI tool traffic
  Copilot remote HTTP MCP client
    → Talon MCP proxy
    → release-mcp-server (synthetic, no external publication capability)

n8n
  HTTP Request node
    → Talon Anthropic-compatible gateway
    → Anthropic-compatible provider
```

## What each component owns

| Component | Owns | Does not own |
|---|---|---|
| Zendesk app | Selecting newest public requester comment; human-facing failure state | Talon/provider keys, provider-route claims, governance |
| Zendesk adapter | Authentication, request shaping, stable session ID, Talon agent key | Policy decisions, provider selection claims |
| Copilot shim | Transparent forwarding and stable session/client headers | Governance, command permissions, result fabrication |
| Release MCP server | Safe synthetic status/prepare/publish methods and upstream execution receipts | Real GitHub releases, deployments, registries, or network publication |
| n8n workflow | Business orchestration and partial-output preservation | Talon policy, cost decision, evidence signing |
| Talon | Controls and evidence for traffic/actions actually routed through its gateway or MCP proxy | Local shell/file/browser/direct API actions that bypass it |

## Evidence gates

Application output proves the application path. Talon signed evidence must independently prove model/provider path, policy decision, cost, session attribution, and offline signature verification before those claims are presented.

MCP upstream receipts prove only whether a synthetic tool reached the upstream server. The release scene requires both Talon denial evidence and the receipt assertion:

```text
release_status   present
release_prepare  present
release_publish  absent
```

Current Talon cannot yet provide the required authenticated MCP agent/session attribution, so this scene remains blocked for release claims.
