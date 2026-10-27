# People Analytics tests

The normal integration path is documented in [README](README.md): Docker Compose for the existing infrastructure and the **real Talon CLI** for initialization, secrets, policy and evidence. There is no custom Talon lifecycle wrapper.

| Test | What it checks |
|---|---|
| Python + docs | DuckDB fixture, aggregate SQL allowlist, bounded department LIKE filter, bad SQL rejection, HTTP contracts, live tool-loop limits, docs and UI script syntax |
| MCP contract | Released Talon binary, allowed aggregate tools, export denied pre-dispatch, signed evidence |
| Model contract | Actual Talon LLM and MCP processes using a **fake OpenAI-compatible model**, not external inference |
| Talon gateway TLS | Debian runtime installs standard CA certificates; external OpenAI handshake still requires an opt-in real-provider test |
| Docker + Chromium | Only one browser (:8501), existing charts, real SQL MCP request, HR-level SQL rejection and Talon denial |
| Business observability | Native `audit list --session`, `costs --session --json`, and `audit verify --session` on the signed tool decisions; visible per-request allow/deny history in the same browser. The example agent also has a session cost limit. |
| Policy change | Same SQL allow → edit the Talon proxy YAML → restart only Talon → deny with zero HR dispatch → restore allow and verify signatures |

CI prepares its own isolated `.env` and uses `docker compose run --rm talon-cli talon init`, `talon validate`, `talon secrets set` and `talon serve`. It does not rely on a custom application-specific launcher. The policy-flip test edits/restores only the example MCP policy.

From the demo repository root:

```bash
make people-analytics-validate
bash scripts/test-people-analytics-talon.sh
```

Chromium and the policy-flip check run in CI with a locally started Docker stack; see `.github/workflows/ci.yml`. The **separate real-provider smoke** needs a disposable `OPENAI_API_KEY` and may incur charges:

```bash
bash scripts/test-people-analytics-real-provider.sh
```

Not proven by no-key CI: real OpenAI model selection, production IAM/row security, legal compliance, arbitrary SQL safety or interception of direct bypass paths. Application-observed gateway traces are not OpenAI wire captures.
