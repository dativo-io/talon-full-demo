# Architecture

This document is for an engineer evaluating adoption, not just running the demo.
It states the trust boundaries, who owns which credential, how data flows, what
happens when Talon is unavailable, and which identity claims are *authenticated*
versus merely *attributed*. Scope: what this repository actually implements and
what remains an external gate (see `docs/BLOCKERS.md`).

## Components and data flow

```
Zendesk ticket editor (browser app, server-side request proxy)
  --HTTPS tunnel--> zendesk-adapter :8443
  --Talon agent key--> Talon gateway :8080  /v1/proxy/<provider>/...

GitHub Copilot CLI (model traffic)
  --> copilot-session-shim :8079 (injects X-Talon-Session-ID)
  --Talon agent key--> Talon gateway :8080  /v1/proxy/openai/...

GitHub Copilot CLI (MCP tools)
  --Talon agent key--> Talon MCP proxy :8081  /mcp/proxy
  --> synthetic release MCP server :8090  (no external publish path)

n8n HTTP node
  --Talon agent key--> Talon gateway :8080  /v1/proxy/anthropic/...
```

The gateway (`:8080`) and the MCP proxy (`:8081`) are two `talon serve`
processes sharing one `talon.config.yaml` + `agents_dir` and one
`TALON_DATA_DIR`. See "Two-process topology" below for why.

## Trust boundaries

- **Only the Zendesk adapter is reachable outside loopback**, and only through an
  authenticated HTTPS tunnel. Everything else binds to `127.0.0.1`.
- The **browser is untrusted**: it supplies ticket/requester JSON, not governance.
  The adapter validates and bounds that input; policy runs in Talon.
- **Talon is the only governance boundary.** Adapters and shims carry identity and
  session context; they do not implement policy, redaction, budgets, or evidence.
- Talon governs **only traffic routed through it.** Copilot's local shell, file
  edits, and test execution are outside Talon — the demo never claims otherwise.

## Credential ownership

| Credential | Held by | Never seen by |
|---|---|---|
| Provider API keys (OpenAI/Anthropic) | Talon vault only | adapters, shims, browser, Copilot |
| Talon agent keys (per use case) | the adapter/shim/n8n making the call | the browser; the provider |
| Zendesk adapter token | the Zendesk app secure setting + adapter | the browser DOM |
| Talon admin key | operator/CI only | **the Copilot process** (MCP is agent-key authed) |
| Evidence signing key | Talon only | everything else |

Provider keys stay in Talon's vault and are attached server-side; a compromised
adapter or shim cannot exfiltrate a provider credential.

## Identity: authenticated vs attributed

- **Authenticated** (proven by a key Talon verifies): the acting agent identity —
  e.g. the `coding-assistant` bearer authenticates both its gateway LLM traffic
  and, via the proxy-only process, its `/mcp/proxy` calls. MCP and LLM evidence
  therefore share `agent_id = coding-assistant`.
- **Attributed** (client-asserted, recorded as provenance, never a policy input):
  `X-Talon-Session-ID`, correlation IDs, and any client identity headers.
- **Policy profile vs acting identity (MCP):** the MCP tool decision is evaluated
  against the proxy profile `coding-assistant-release-tools` (the `agent.name` in
  `mcp-proxy.example.yaml`), while the authenticated acting identity in evidence
  is `coding-assistant`. These are distinct objects; evidence should be read with
  that distinction in mind (the tool denial is the proxy profile's policy, not
  `coding-assistant`'s ordinary effective policy).
- **Known coarseness (external gate):** the Zendesk adapter authenticates as the
  single `customer-support` use case and derives a session from the ticket ID. It
  does **not** today carry a verified human support-agent identity, Zendesk
  account/installation, or source comment ID. Adding those requires a *verified*
  platform assertion (not more trusted browser JSON) — tracked as adoption work.

## Two-process topology (and why)

In v1.9.3 a single `--gateway` process that also serves `--proxy-config` puts
`/mcp/proxy` behind admin-only middleware (fail-closed native-execution route,
upstream #266): the client would need the operator admin key, and Talon — seeing
no authenticated agent — would attribute MCP evidence to the proxy config's name.
Running the MCP proxy as its own **non-gateway** process authenticates
`/mcp/proxy` with agent keys, so the acting identity owns the evidence and the
client holds no admin key.

Caveats, stated honestly:

- The two processes share one **SQLite** `TALON_DATA_DIR`. Evidence writes are
  direct SQLite writes with no application-level retry around a locked database.
  Treat this as a **low-concurrency demo topology** (the demo issues requests
  sequentially), not a supported concurrent-production arrangement.
- Each process owns its own runtime generation (config-reload loop, compiled
  policy, identity registry). During a config change the two can briefly serve
  different generations.
- The gateway dashboard's metrics collector receives live events only from its own
  evidence store and reconciles from the shared DB periodically (default ~30s), so
  MCP evidence produced by the other process can appear in the dashboard with a
  short lag. Verify via the signed export, which is immediate and authoritative.

The proper long-term fix belongs in Talon (a gateway-mode `/mcp/proxy` that
requires operator authorization for config access while resolving a scoped agent
bearer for invocation identity, or a lightweight MCP-only proxy mode). Until then,
this repository labels the split as a demo workaround, not a recommended
production topology.

## Failure modes

| Condition | Behavior |
|---|---|
| Preferred provider down | Gateway walks the policy-valid fallback chain; skips healthy-but-disallowed destinations; PII still redacted before the chosen provider |
| Session budget projected to exceed cap | Denied **before** provider execution (soft cap; prior output remains); `403 session_budget_exceeded` |
| Forbidden tool invoked | Denied with `TALON_TOOL_FORBIDDEN`; never reaches upstream; recorded in signed evidence |
| Talon gateway 4xx (adapter path) | 403 → policy denial; 401 → integration misconfiguration; 429 → rate limited; other → generic unavailable — upstream body never forwarded |
| Talon unavailable / transport error | Adapter returns a safe "governed draft unavailable" (502); the ticket stays with a human. No ungoverned fallback path exists |
| MCP proxy process down | MCP tools unavailable; gateway LLM traffic unaffected (separate process) |

## Operational notes for a real deployment (not implemented here)

- **Key rotation:** provider keys rotate in Talon's vault; agent keys rotate per
  adapter/shim; the adapter token rotates in the Zendesk secure setting. No
  rotation automation ships in this demo.
- **HA / backup:** SQLite evidence suits single-instance; a real deployment needs
  Talon's supported store and a backup policy for the evidence DB.
- **Latency:** Talon adds one hop plus policy evaluation; measure it in the pilot
  rather than assuming.
- **Idempotency / rate limiting on the adapter:** not implemented (see
  `docs/BLOCKERS.md`); a production adapter should key requests by
  installation+ticket+source-comment+generation and rate-limit per token.

These are deliberately out of scope for a technical preview; they are listed so an
adopter's design review starts from an honest map rather than a happy path.
