# Current release gates

Compatibility was source-audited against `dativo-io/talon/main` commit `24046ca690a616c2710c3084d59857839364bcf3` on 2026-07-20.

## Resolved Talon defects

Talon issues `#346` and `#350` are closed as completed. Current `main` now:

- defaults an omitted `proxy.mode` to `intercept`;
- rejects unknown proxy modes;
- blocks explicitly forbidden tools in every mode except explicitly selected `passthrough`;
- records passthrough policy violations truthfully as shadow violations rather than fake blocks;
- preserves authenticated tenant and agent identity in MCP evidence;
- validates and propagates client-asserted session metadata and request correlation IDs with attribution provenance.

Talon v1.9.3 additionally resolved three gaps this demo's review surfaced:

- `#367`: `/mcp/proxy` (and `/mcp`) answer the mandatory MCP `initialize` handshake locally (tools capability only, never forwarded upstream) and accept `notifications/initialized`; spec-conformant MCP clients such as Copilot CLI can now connect through the proxy. The prior `-32601` on `initialize` would have broken the Copilot MCP scene.
- `#369`: denials carry a stable machine code in JSON-RPC `error.data.talon_code` (`TALON_TOOL_FORBIDDEN` for the forbidden-tool case), so the denial gate below asserts on a code, not on prose.
- `#368`: `talon serve --gateway-mode shadow|enforce|log_only` overrides `gateway.mode` at runtime; the demo no longer generates an edited shadow config file.

The demo still uses explicit `proxy.mode: intercept`; it does not depend on the default.

## Remaining MCP end-to-end gate

The product defects are fixed, but the full scene must still be executed against the current Talon binary before it becomes a demonstrated result. Required proof:

- `release_status` reaches the synthetic upstream;
- `release_prepare` reaches the synthetic upstream;
- forbidden `release_publish` returns a Talon policy denial and is absent from upstream receipts;
- evidence carries the authenticated `coding-assistant` identity;
- evidence preserves the asserted Copilot session and request correlation identifier;
- the JSON-RPC denial carries `error.data.talon_code == "TALON_TOOL_FORBIDDEN"` (stable since v1.9.3, #369);
- the signed session export verifies offline.

Everything above except the real-Copilot-CLI driver was executed on 2026-07-20 against a live server built from `24046ca` (see `docs/VALIDATION.md`, "Executed live-server run") and is now re-run by `make live-check`.

Topology decision (identity + least privilege): the MCP proxy runs as its own **non-gateway** `talon serve` on `:8081`, sharing `TALON_DATA_DIR` with the gateway. A proxy-only process authenticates `/mcp/proxy` with **agent keys** (`TenantKeyMiddleware`), so the `coding-assistant` bearer both authenticates and owns the evidence — MCP records and the agent's LLM records share `agent_id = coding-assistant` — and the Copilot process holds no admin key. (The earlier single-process option required the operator admin key on the client and attributed MCP evidence to the proxy config's name `coding-assistant-release-tools`, breaking the "one identity" story; it was rejected.) `make live-check` asserts the shared-identity result.

The synthetic release server advertises `run_nonce` as a **required** input-schema property and rejects a missing/malformed nonce server-side, so a schema-driven MCP client (Copilot) actually sends it — the `tools/call` curl in the live check is not a more permissive path than the real client.

Until the real-Copilot-CLI driver runs, label the scene **implemented, executed against real Talon via `make live-check`, real-client driver externally unverified**—not product-blocked.

## External integration gates

- install the Zendesk private app and prove secure-setting substitution;
- run real Copilot CLI BYOK against the session shim;
- boot the pinned n8n image;
- create, export, and clean-import the n8n workflow in that pinned version;
- calibrate the real provider session budget;
- run live provider evidence export, offline verification, and tamper-failure proof.
