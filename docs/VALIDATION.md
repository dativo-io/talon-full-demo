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
7. a local HTTP integration test using the explicitly labelled mock gateway;
8. billing fixture fail-before / pass-after proof;
9. n8n Compose validation when Docker is available, otherwise a bounded static contract check;
10. `git diff --check`.

The local mock proves adapter and transport behavior only. It does not produce Talon evidence and is never presented as a live Talon result.

## Current Talon compatibility

Source-audited on 2026-07-20 against `dativo-io/talon/main` commit `3f373e19f2a97722db7450e51461862911188ecb`:

- gateway route `/v1/proxy/{provider}/v1/...`;
- `talon serve --host ... --port ... --gateway --gateway-config ... --proxy-config ...`;
- MCP endpoint `POST /mcp/proxy`;
- strict proxy YAML with object-form `allowed_tools` and top-level `pii_handling`;
- issue #346 fail-closed/default-mode behavior;
- issue #350 authenticated agent plus session/correlation evidence attribution.

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
