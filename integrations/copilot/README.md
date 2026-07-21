# GitHub Copilot CLI integration

GitHub Copilot CLI currently supports custom OpenAI-compatible providers through these environment variables:

```bash
export COPILOT_PROVIDER_TYPE=openai
export COPILOT_PROVIDER_BASE_URL=http://127.0.0.1:8079/v1/proxy/openai/v1
export COPILOT_PROVIDER_API_KEY="$TALON_CODING_ASSISTANT_KEY"
export COPILOT_MODEL=gpt-4o
export COPILOT_OFFLINE=true
```

The selected model must support streaming and tool calling. The local shim preserves the request path, query, body, authorization, and streaming response while injecting stable `X-Talon-Session-ID` and `X-Talon-Client` headers.

Render a session-only remote MCP configuration with:

```bash
scripts/render-copilot-mcp-config.sh
```

Then run Copilot from `cases/billing-demo` with `--additional-mcp-config=@../../.state/copilot-mcp.json`, `--disable-builtin-mcps`, `--allow-tool='release-gateway'`, and `--deny-tool='shell(git push)'`. The local fixture has no Git remote. Direct push prevention is a Copilot CLI permission, not a Talon claim.

Talon issues #346 and #350 are fixed on current `main`; the MCP scene is no longer product-blocked by those defects, but it remains externally unverified until run end-to-end against the current Talon binary and real Copilot CLI.
