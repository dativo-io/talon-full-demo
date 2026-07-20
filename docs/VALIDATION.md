# Validation status

This file distinguishes checks that run entirely inside this repository from external integration gates.

## Repository-local contract

Run:

```bash
make ci
```

The command performs:

1. Go formatting check;
2. `go vet ./...`;
3. builds all three Go services;
4. `go test ./...`;
5. Zendesk browser-logic tests with Node;
6. shell syntax validation;
7. a local HTTP integration test using the explicitly labelled mock gateway, including a nonce-correlated forbidden-tool proof (stale receipts from an earlier run cannot satisfy the assertion) and the session-budget scenario -- request 1 allowed, request 2 allowed, request 3 denied 403 `session_budget_exceeded` with zero simulated cost, matching the n8n workflow-spec branch;
8. billing fixture fail-before / pass-after proof;
9. n8n Compose validation when Docker is available, otherwise a bounded static contract check;
10. `git diff --check`.

The local mock proves adapter and transport behavior only. It does not produce Talon evidence and is never presented as a live Talon result.

## Current Talon compatibility

Source-audited on 2026-07-20 against `dativo-io/talon/main` commit `24046ca690a616c2710c3084d59857839364bcf3`:

- gateway route `/v1/proxy/{provider}/v1/...`;
- `talon serve --host ... --port ... --gateway --gateway-config ... --proxy-config ...`;
- MCP endpoint `POST /mcp/proxy`;
- strict proxy YAML with object-form `allowed_tools` and top-level `pii_handling`;
- issue #346 fail-closed/default-mode behavior;
- issue #350 authenticated agent plus session/correlation evidence attribution;
- v1.9.3 #367 local MCP `initialize` handshake on `/mcp/proxy` (required by spec-conformant clients);
- v1.9.3 #369 stable denial machine codes in `error.data.talon_code`;
- v1.9.3 #368 `talon serve --gateway-mode` runtime override (used instead of a generated shadow config);
- `talon agents --url` runtime fleet verification, binary-verified against a build of `24046ca` (implemented in `internal/cmd/agents_queue.go` since v1.9.0; QUICKSTART's snippet is accurate).

Source compatibility is not an executed live integration result.

## External validation still required

- build and run the current Talon checkout with the generated config;
- seed the vault-backed agent keys and provider keys;
- install the Zendesk private app and prove secure-setting substitution;
- run real Copilot CLI BYOK and the remote MCP server;
- prove `release_publish` is absent from upstream receipts and present as a signed Talon denial;
- pull and boot the pinned n8n image;
- create/export/clean-import the n8n workflow from the pinned UI;
- run real provider traffic and calibrate the soft session budget;
- export signed evidence, verify it offline, tamper a copy, and prove verification fails.
