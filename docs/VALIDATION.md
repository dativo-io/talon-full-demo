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
- `talon serve --host ... --port ... --gateway --proxy-config ...`, run from the generated-config directory (`agents_dir` is working-directory-relative in v1.9.3; from the repository root the server fails at boot);
- MCP endpoint `POST /mcp/proxy`: admin-gated when one process serves `--gateway` (upstream #266 fail-closed); agent-key authenticated (attributing to the acting agent) when run as a proxy-only process — the demo uses the latter on `:8081`;
- strict proxy YAML with object-form `allowed_tools` and top-level `pii_handling`;
- issue #346 fail-closed/default-mode behavior;
- issue #350 authenticated agent plus session/correlation evidence attribution;
- v1.9.3 #367 local MCP `initialize` handshake on `/mcp/proxy` (required by spec-conformant clients);
- v1.9.3 #369 stable denial machine codes in `error.data.talon_code`;
- v1.9.3 #368 `talon serve --gateway-mode` runtime override (used instead of a generated shadow config);
- `talon agents --url` runtime fleet verification, binary-verified against a build of `24046ca` (implemented in `internal/cmd/agents_queue.go` since v1.9.0; QUICKSTART's snippet is accurate).

## Executed live-server run (2026-07-20)

This is reproducible as a script — `make live-check` (`scripts/test-live-talon.sh`) — a rerunnable, mock-independent gate distinct from the source audit above, not a one-time transcript. It needs a `dativo-io/talon` checkout (`TALON_REPO`, default `../talon`; a mismatch with `TALON_PINNED_COMMIT` warns) and builds the Talon binary itself. Two hermetic phases run in a temp dir (the repo's `.env`/`.state`/`config/generated` are untouched):

**Phase 1 — MCP release boundary and the identity story, in the demo's real two-process topology.** A gateway process (`:GW`) and a proxy-only process (`:MCP`) share one `TALON_DATA_DIR`. Then:

- the fleet view (`talon agents --url`, #370/v1.9.0) lists 3 agents;
- an LLM call through the gateway as the `coding-assistant` bearer succeeds (against a synthetic OpenAI-compatible provider, no real key);
- the MCP scene runs through the proxy-only process with the **agent bearer only, no admin key** — proving agent-key auth on `/mcp/proxy`: `initialize` answered locally as `talon-mcp-proxy v1.9.3` (#367), `tools/list` advertises exactly the two allowed tools **each with `run_nonce` required**, nonce-tagged `release_status`/`release_prepare` succeed, and `release_publish` is denied with `error.data.talon_code == "TALON_TOOL_FORBIDDEN"` (#369) with no publish receipt;
- `scripts/assert-release-blocked.sh` passes for the run nonce and rejects a stale nonce;
- `scripts/assert-evidence.sh` verifies the signed export offline and asserts that **every record in the session — the LLM call and all MCP calls — carries `agent_id = coding-assistant`** (4/4 valid, 1 forbidden-tool denial). This is the identity proof: LLM and MCP actions share one operational identity, and the client holds no operator credential.

**Phase 2 — the session-budget engine itself** (#198/#283, not the mock's imitation): a synthetic OpenAI-compatible provider returns large usage so one request's real cost dwarfs the pre-request estimate; the cap is measured at runtime (1.5× one request's actual signed-evidence cost, robust to pricing-table changes) and Talon denies request 3 with a real `403 session_budget_exceeded` at zero cost. Executed 2026-07-20: measured cost 1.6, cap 2.4, allow/allow/deny, evidence 3/3 valid.

This closes the gap between "matches the 403 contract read in Talon's `session_budget_test.go`" and "Talon's real budget path produced the denial." The remaining external gate is a **real Copilot CLI binary** driving Phase 1's scene (the live check drives `tools/call` over HTTP, but the tool schema now advertises `run_nonce` as required, so a conforming client is exercised through the same contract); real-*provider* budget calibration (actual LLM spend and latency) also remains external.

Still external: driving the same scene from a real Copilot CLI binary, the Zendesk private-app installation, the n8n UI workflow export, and real-provider routes (LLM and budget calibration used no real provider keys in this run).

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
