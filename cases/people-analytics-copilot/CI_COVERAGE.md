# People Analytics tests

The normal integration path is documented in [README](README.md): Docker Compose for the existing infrastructure and the **real Talon CLI** for initialization, secrets, policy and evidence. There is no custom Talon lifecycle wrapper.

| Test | What it checks |
|---|---|
| Python + docs | DuckDB fixture, aggregate SQL allowlist, bounded department LIKE filter, bad SQL rejection, HTTP contracts, live tool-loop limits, docs and UI script syntax |
| Governed MCP contract | Talon built from current [core `main`](https://github.com/dativo-io/talon/tree/main) on every CI run; its resolved source SHA is recorded (governed MCP, talon#431; source-built acceptance, not released-artifact proof). Discovery hides the forbidden export; the admin key is refused; read-only aggregates execute once at HR; the forbidden export called by name is `policy_denied` with zero HR calls; an approved SQL executes once; an SQL the HR validator rejects after dispatch is `upstream_outcome_unknown` (dispatched once, vendor text not relayed); a retry of that operation (same client operation id) is refused and changed arguments conflict, with no new HR call; every operation's signed record and lifecycle verify (`talon audit verify --operation`); every record joins the asserted session and carries no key material |
| Model contract | Actual Talon LLM gateway and governed MCP endpoint using a **fake OpenAI-compatible model**, not external inference |
| Talon gateway TLS | Debian runtime installs standard CA certificates; external OpenAI handshake still requires an opt-in real-provider test |
| Docker + Chromium | Only one browser (:8501), existing charts, real SQL MCP request, HR-level SQL rejection after dispatch shown as **outcome unknown**, and Talon denial. HR listens on loopback inside the namespace it shares only with `talon-mcp`; the app has no route to it |
| Business observability | Native `audit list --session`, `costs --session --json`, and `audit verify --session` on the signed tool decisions; visible per-request allow/deny history in the same browser. The example agent also has a session cost limit. |
| Policy change | Same SQL allow → forbid `hr_aggregate_sql` in the use case's `agent.talon.yaml` → restart only Talon → deny with zero HR dispatch → lift the export prohibition → the export is prepared (zero HR calls), executed once by operation id, and a duplicate execute is refused → restore and verify signatures. Runs locally in `test-people-analytics-talon.sh` (processes) and in Docker in CI (`test-people-analytics-policy-change.py`) |
| Read-only Talon operator UI | `test_docs.py` guards the opt-in, loopback-only `talon-ui` Compose service (profile `operator`), shared data/policy sources, no private-HR network and no admin/vault key. The paired console is an **operator walkthrough**, not an additional policy engine. Actual browser screenshots are intentionally left for manual capture; this repo's Chromium gate validates the **Workforce app**, not the new Talon console. |

CI prepares its own isolated `.env` and uses `docker compose run --rm talon-cli talon init`, `talon validate`, `talon secrets set` and `talon serve`. It does not rely on a custom application-specific launcher. The policy-flip test edits/restores only the use case's `agent.talon.yaml` in Talon's state.

From the demo repository root:

```bash
make people-analytics-validate
bash scripts/test-people-analytics-talon.sh
```

Chromium and the policy-flip check run in CI with a locally started Docker stack; see `.github/workflows/ci.yml`. The **separate real-provider smoke** needs a disposable `OPENAI_API_KEY` and may incur charges:

```bash
bash scripts/test-people-analytics-real-provider.sh
```

Not proven by no-key CI: real OpenAI model selection, production IAM/row security, legal compliance, arbitrary SQL safety or interception of direct bypass paths. Application-observed gateway traces are not OpenAI wire captures. No automated check covers the Talon Operations Console for this case (the screenshots are manual captures).

## Complete v1.17.0 consumer acceptance (not run)

The governed-MCP workflows build an unreleased Talon candidate from source, not a published artifact. Do not use them as evidence of native v1.17.0 registration or paired Console acceptance. Once complete stable v1.17.0 is verified (RC.1 is incomplete), run the supported artifact deployment and actual operator browser across **seven** read-only areas including **Approvals** (native reviewer CLI/API for decisions), independently prove registered/loaded/connected/governed, record exact artifact digests and actual timings, and confirm policy/CLI/API/Console/evidence and independent HR counter parity. Keep native deployment and registration steps visible. Company-policy inheritance across applications belongs to integrated #48/#50; no alternate policy engine. This consumer test does not gate OSS release.
