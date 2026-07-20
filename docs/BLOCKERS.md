# Current release gates

Compatibility was source-audited against `dativo-io/talon/main` commit `3f373e19f2a97722db7450e51461862911188ecb` on 2026-07-20.

## Resolved Talon defects

Talon issues `#346` and `#350` are closed as completed. Current `main` now:

- defaults an omitted `proxy.mode` to `intercept`;
- rejects unknown proxy modes;
- blocks explicitly forbidden tools in every mode except explicitly selected `passthrough`;
- records passthrough policy violations truthfully as shadow violations rather than fake blocks;
- preserves authenticated tenant and agent identity in MCP evidence;
- validates and propagates client-asserted session metadata and request correlation IDs with attribution provenance.

The demo still uses explicit `proxy.mode: intercept`; it does not depend on the default.

## Remaining MCP end-to-end gate

The product defects are fixed, but the full scene must still be executed against the current Talon binary before it becomes a demonstrated result. Required proof:

- `release_status` reaches the synthetic upstream;
- `release_prepare` reaches the synthetic upstream;
- forbidden `release_publish` returns a Talon policy denial and is absent from upstream receipts;
- evidence carries the authenticated `coding-assistant` identity;
- evidence preserves the asserted Copilot session and request correlation identifier;
- the emitted native explanation includes the current deterministic tool-denial code/reason;
- the signed session export verifies offline.

Until those checks run, label the scene **implemented and current-Talon-compatible, externally unverified**—not product-blocked.

## External integration gates

- install the Zendesk private app and prove secure-setting substitution;
- run real Copilot CLI BYOK against the session shim;
- boot the pinned n8n image;
- create, export, and clean-import the n8n workflow in that pinned version;
- calibrate the real provider session budget;
- run live provider evidence export, offline verification, and tamper-failure proof.
