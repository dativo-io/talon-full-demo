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

Everything above except the real-Copilot-CLI driver was executed on 2026-07-20 against a live server built from `24046ca` (see `docs/VALIDATION.md`, "Executed live-server run"). In single-process gateway mode, v1.9.3 admin-gates `/mcp/proxy` (fail-closed, upstream #266); the rendered Copilot MCP config therefore carries `X-Talon-Admin-Key` alongside the agent bearer — decided 2026-07-20, tradeoff documented in `docs/SETUP.md` section 8, with a second non-gateway proxy process as the stricter alternative.

Until those checks run, label the scene **implemented and current-Talon-compatible, externally unverified**—not product-blocked.

## External integration gates

- install the Zendesk private app and prove secure-setting substitution;
- run real Copilot CLI BYOK against the session shim;
- boot the pinned n8n image;
- create, export, and clean-import the n8n workflow in that pinned version;
- calibrate the real provider session budget;
- run live provider evidence export, offline verification, and tamper-failure proof.
