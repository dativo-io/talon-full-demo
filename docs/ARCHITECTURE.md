# Architecture

Zendesk app → adapter → Talon OpenAI route; Copilot CLI → session shim → Talon OpenAI route; Copilot MCP → Talon MCP proxy → synthetic release server; n8n HTTP node → Talon Anthropic route. Adapters supply identity/session context but do not implement governance. Only the Zendesk adapter is publicly reachable through an HTTPS tunnel.
