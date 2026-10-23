# Talon Full Demo

A standalone, early-adopter-oriented demonstration of recognizable applications governed through [Dativo Talon](https://github.com/dativo-io/talon):

- **n8n customer-support resolution** — a duplicate-charge workflow drafts a reply through a policy-valid provider path, protects customer PII, blocks the refund action, and then literally waits for a demo operator to approve or reject the synthetic finance handoff.
- **n8n vendor-contract review** — a confidential synthetic contract package is blocked from one destination, redacted, and reviewed through the approved provider with both decisions in one signed session.
- **Customer support / Zendesk** — a support workflow requests a governed reply draft through direct and adapter paths.
- **GitHub Copilot CLI** — a real Copilot client sends model traffic through Talon and reaches a synthetic release boundary through Talon's MCP proxy.
- **n8n cost boundary** — an imported document workflow preserves partial business output when Talon prevents the next request on projected session cost.

The intended experience is a **10–15 minute narrated walkthrough**. Every completed application case has two projections of the same Talon evidence:

- a concise buyer/product view;
- a technical/security view.

See [Audience-specific demo views](docs/AUDIENCE_DEMOS.md) for the full command matrix and truth boundaries.

## Start here

### 1. Validate the repository without keys

```bash
make validate-local
```

With Docker available, validate the real pinned n8n artifacts separately:

```bash
make n8n-support-resolution-validate
make n8n-vendor-review-validate
make n8n-validate
```

The support-resolution gate proves reply generation, zero-cost `issue_refund` denial, a blocking session-bound operator decision, approved and rejected branches, signed operator receipts, and credential-free clean import. The vendor-review gate reproduces a zero-cost OpenAI egress denial followed by an approved Anthropic review. The quarterly gate reproduces useful output followed by a session-budget denial. Each workflow executes in pinned n8n `2.30.4`.

### 2. Prepare and start the real stack

Clone `dativo-io/talon` next to this repository, put Talon v1.9.3+ on `PATH`, then:

```bash
export OPENAI_API_KEY='sk-...'
export ANTHROPIC_API_KEY='sk-ant-...'
make real-prepare
make real-start
make real-status
```

OpenAI is required for support, Copilot, Zendesk, and the customer-support resolution. Anthropic is required for the quarterly and vendor-review n8n cases. `real-prepare` installs the full-demo-owned vendor-review and customer-support action-boundary overlays into the generated Talon fleet and seeds their vault bindings.

## OpenShell sandboxed support agent (advanced, opt-in)

The OpenShell case uses the same prepared Talon fleet and signed evidence as the other demos. Enable it before preparation, on a supported Linux/Docker host with a compatible Talon build:

    export TALON_OPENSHELL_ENABLED=1
    make real-prepare
    make real-start
    make real-status
    make demo-openshell-buyer

In another terminal during the human gate: `make status-openshell-approval`, then `make approve-openshell` (or `make reject-openshell`). To re-present the same run: `make present-openshell-all`. Technical view: `make demo-openshell-tech`.

**Integration status:** Talon PR #501 is merged but the latest published release predates it. The canonical main-Talon OpenShell showcase runner must be delivered and verified before this is a self-service demo. See [OpenShell demo contract](docs/OPENSHELL_DEMO.md). The option is off by default and does not affect existing cases.

## Choose a case and audience

### n8n customer-support resolution

The input is a synthetic duplicate-charge ticket, account context, and refund policy. n8n produces a useful reply draft despite the preferred local provider being unavailable, while Talon redacts the customer's email and IBAN, keeps failover inside the approved provider list, and blocks a later request that exposes `issue_refund`.

The real demo then enters a literal human gate. The n8n execution remains blocked and no final status or synthetic finance handoff exists until the operator approves or rejects the exact EUR 249 request.

Start the buyer demo in shell 1:

```bash
make demo-n8n-support-resolution-buyer
```

It will stop at:

```text
HUMAN APPROVAL REQUIRED
...
The workflow is blocked. No final status or finance handoff exists yet.
```

In shell 2, inspect or decide:

```bash
make status-n8n-support-resolution-approval
make approve-n8n-support-resolution
# or:
make reject-n8n-support-resolution
```

The approval page shown by shell 1 is bound to loopback. On a remote demo host, use the terminal command or an SSH tunnel to open the page locally.

The approved path creates a signed operator receipt plus `finance-refund-request.json`. The rejected path creates a signed rejection receipt and no finance handoff. Neither path executes a refund.

Platform/security/engineering uses the same interaction:

```bash
make demo-n8n-support-resolution-tech
```

Re-present the same completed session without another model call:

```bash
make present-n8n-support-resolution
make present-n8n-support-resolution-tech
make present-n8n-support-resolution-all
```

The presenter fails closed unless all of the following agree:

- final customer reply and status artifacts;
- `customer-support` identity;
- confidential-tier email and IBAN redaction;
- failed local route and policy-valid OpenAI fallback;
- zero-cost `issue_refund` denial before provider dispatch;
- separately signed operator approval or rejection bound to the exact session, run nonce, ticket, amount, and action;
- approved finance handoff created after approval, or no handoff after rejection;
- every Talon evidence signature and the operator-receipt HMAC.

Talon does not execute, approve, or decline the EUR 249 refund. Talon blocks AI authority. The separate demo operator gate controls only whether the workflow may create a synthetic finance handoff.

### n8n vendor-contract review

The input is a synthetic vendor profile, proposed DPA, and internal review policy. The workflow first probes OpenAI with the confidential package; Talon's agent-level egress rule denies it before provider access. The same package then goes to the approved Anthropic destination after email and IBAN redaction.

Buyer/product/executive:

```bash
make demo-n8n-vendor-review-buyer
```

Platform/security/engineering:

```bash
make demo-n8n-vendor-review-tech
```

Re-present the same completed session:

```bash
make present-n8n-vendor-review
make present-n8n-vendor-review-tech
make present-n8n-vendor-review-all
```

The presenter fails closed unless the review and status artifacts, `vendor-contract-review` identity, zero-cost OpenAI egress denial, later allowed Anthropic decision, confidential-tier email/IBAN redaction, and every evidence signature agree. The generated review is advisory and synthetic; human legal, privacy, security, and procurement review remains required.

### Customer-support gateway

```bash
make demo-support-buyer
make demo-support-tech

make present-support
make present-support-tech
make present-support-all
```

The direct support case proves email and IBAN redaction, a failed local provider, a disallowed fallback candidate skipped by policy, an approved OpenAI fallback, actual cost, and verified signed evidence. It is a lower-level gateway proof than the n8n support-resolution business workflow.

### Zendesk adapter

```bash
make demo-zendesk-buyer
make demo-zendesk-tech

make present-zendesk
make present-zendesk-tech
make present-zendesk-all
```

This proves the real local adapter-to-Talon path, client attribution, PII handling, policy-valid failover, cost, and signed evidence.

Build and inspect a credential-free private-app ZIP without an account:

```bash
make zendesk-package
```

Run official Zendesk server-side validation and packaging after authenticating ZCLI:

```bash
zcli login -i
make zendesk-zcli-package
```

The hosted workflow always builds and scans the offline ZIP. It also runs authenticated ZCLI automatically when repository secrets `ZENDESK_SUBDOMAIN` and `ZENDESK_OAUTH_TOKEN` exist.

After installing the authenticated package in a real Zendesk account and observing the UI flow, machine-verify the matching Talon session and record the UI observations:

```bash
export ZENDESK_INSTALLED_TICKET_ID='<ticket-id>'
export ZENDESK_INSTALLED_SESSION_ID='<session-id-shown-by-the-app>'
export ZENDESK_PRIVATE_APP_INSTALLED=yes
export ZENDESK_SECURE_SETTING_CONFIRMED=yes
export ZENDESK_NEWEST_REQUESTER_COMMENT_CONFIRMED=yes
export ZENDESK_DRAFT_INSERTED_CONFIRMED=yes
make verify-zendesk-installed
```

UI observations remain explicitly operator-confirmed; Talon identity, routing, redaction, cost, and signatures are machine-verified.

### GitHub Copilot CLI

Install once:

```bash
make copilot-install
```

Run and present:

```bash
make demo-copilot-buyer
make demo-copilot-tech

make present-copilot
make present-copilot-tech
make present-copilot-all
```

The bounded run permits only `release_status` and `release_prepare`, independently verifies upstream receipts and signed evidence, and stays within Talon's real boundary: model traffic and MCP calls routed through Talon. It is not a benchmark of Copilot code editing.

### n8n session-budget workflow

Buyer/product/executive:

```bash
make demo-n8n-buyer
```

Platform/security/engineering:

```bash
make demo-n8n-tech
```

Re-present the same completed session:

```bash
make present-n8n
make present-n8n-tech
make present-n8n-all
```

The workflow reads synthetic quarterly sections sequentially, writes each completed summary, then preserves partial output and writes `status.json` when Talon denies the next request with `session_budget_exceeded`. The presenter fails closed unless output artifacts, `document-summary` identity, allowed work followed by a zero-cost denial, and valid signatures all agree.

## Existing low-level commands

```bash
make real-smoke                    # direct support smoke path
make real-support                  # fresh support gateway run
make real-zendesk                  # fresh local Zendesk-adapter run
make real-copilot                  # fresh bounded Copilot run
make real-n8n-support-resolution   # fresh support workflow; blocks at operator gate
make real-n8n-vendor-review        # fresh vendor-contract review workflow
make real-n8n                      # fresh quarterly-report workflow
make live-check                    # separate real-Talon MCP denial + budget-engine proof
```

Stop repository-managed services with:

```bash
make real-stop
```

## Status

| Area | Status |
|---|---|
| Local repository validation | Implemented and tested |
| Real Talon MCP + session-budget check | Implemented; `make live-check` |
| n8n customer-support resolution | Implemented; clean-import gate + real OpenAI/fallback path + blocking operator approval/rejection |
| n8n vendor-contract review | Implemented; pinned egress-deny/allow clean-import gate + real Anthropic path |
| n8n session-budget workflow | Implemented; pinned import/execute/export/clean-import gate + real Anthropic path |
| Real support gateway path | Implemented; buyer + technical views |
| Real local Zendesk adapter path | Implemented; buyer + technical views |
| Zendesk offline private-app ZIP | Implemented; deterministic package + secret scan + CI artifact |
| Zendesk server-side ZCLI validation/package | Implemented command; Zendesk authentication required |
| Zendesk installed private app | Account/browser gate; `make verify-zendesk-installed` records completion |
| Real GitHub Copilot CLI path | Implemented; buyer + technical views |
| Talon configuration | Canonical product-demo source plus full-demo-owned vendor-review and customer-support overlays |

## Validation levels

| Command | External account needed? | Meaning |
|---|---:|---|
| `make validate-local` | No | Repository code, adapters, mock integration, presenter contracts, MCP contract, and billing fixture work locally. |
| `make n8n-support-resolution-validate` | No provider account; Docker | Renders the operator-gated workflow, clean-imports it twice with explicit approval, exercises rejection, verifies signed operator receipts, and proves no finance handoff follows rejection. |
| `make n8n-vendor-review-validate` | No provider account; Docker | Vendor-review workflow proves egress-deny then allow behavior twice with credential-free exports. |
| `make n8n-validate` | No provider account; Docker | Quarterly workflow imports, executes, exports without credentials, clean-imports, and executes again. |
| `make live-check` | No provider account | A real Talon binary enforces MCP policy, signs evidence, and applies the real session-budget engine. |
| `make demo-n8n-support-resolution-buyer` / `-tech` | OpenAI + Docker + explicit operator decision | Real imported support workflow, PII redaction, policy-valid fallback, forbidden refund tool, blocking human gate, branch-specific artifacts, cost, and evidence. |
| `make demo-n8n-vendor-review-buyer` / `-tech` | OpenAI + Anthropic + Docker | Real imported workflow, egress denial, PII redaction, approved review, cost, and evidence. |
| `make demo-n8n-buyer` / `-tech` | Anthropic + Docker | Real imported workflow, partial output, budget stop, and evidence. |
| `make demo-support-buyer` / `-tech` | OpenAI | Direct support PII, fallback, cost, and evidence. |
| `make demo-zendesk-buyer` / `-tech` | OpenAI | Real local adapter path and evidence. |
| `make zendesk-package` | No Zendesk account | Build and inspect a credential-free ZIP; no Zendesk server validation claim. |
| `make zendesk-zcli-package` | Authenticated Zendesk account | Official ZCLI validation and package, then local ZIP inspection. |
| `make verify-zendesk-installed` | Zendesk account | Machine-verified Talon session plus explicit operator-confirmed UI observations. |
| `make demo-copilot-buyer` / `-tech` | OpenAI + Copilot CLI | Real Copilot model/MCP path and evidence. |

## Core truth rules

- Application output is produced by the real application path, not by the presenter.
- Buyer and technical summaries are computed from newly exported and verified signed Talon sessions, never hard-coded.
- Provider routes, redaction, costs, policy decisions, and signatures are displayed only after Talon evidence confirms them.
- Talon is credited only for model traffic and tool schemas or calls routed through Talon.
- A blocked `issue_refund` schema proves it was not offered through that governed request; Talon does not execute, approve, or decline refunds.
- The support demo's operator receipt is separate from Talon evidence: it proves only who released workflow continuation for that synthetic request.
- Operator approval creates only a synthetic finance handoff; no refund or payment-system call occurs.
- An offline Zendesk ZIP is not described as Zendesk server-validated.
- Zendesk browser-only observations are operator-confirmed, not misrepresented as Talon evidence.
- Talon does not govern Copilot's local shell commands, filesystem changes, browser actions, or direct API calls.
- Session limits are soft caps.
- Vendor-contract review output is advisory, synthetic, and requires human review.
- HMAC evidence is tamper-evident and offline-verifiable, not immutable.
- Only synthetic data belongs in this repository and demo.

## Repository map

```text
cmd/                  runnable adapters and helper services
internal/             tested implementation packages
integrations/         Zendesk, Copilot, and n8n integration assets
cases/                synthetic business fixtures
config/               generated Talon config, integration overlays, and MCP templates
mock/                  no-key local Talon-compatible test endpoint
scripts/               setup, validation, orchestration, approval service, and presenters
docs/                  quickstarts, architecture, setup, presenter, and blockers
```

## Security

Never commit provider keys, Talon keys, Zendesk settings, generated evidence, n8n credentials, operator-approval keys, or real customer content. Real provider keys should be exported only for `make real-prepare`; the helper stores them in Talon's encrypted local vault and does not write them into `.env`.


## TokenEconomizer x Talon — real Claude Code before/after demo

This optional case is **isolated** from the other Full Demo workflows. It does
not modify the Talon source checkout or the existing generated fleet. It starts
a loopback Talon gateway on port 18086 with **two isolated Talon agent identities**
(te-baseline and te-after), separate cost ledgers, and an encrypted vault under
the Git-ignored .state/tokeneconomizer-demo directory. Each invocation uses a
fresh data store so earlier experiments cannot consume its budget.

It drives the **real Claude Code CLI** on two equivalent synthetic Python
repositories: five learning sessions and five measured repair sessions without
TokenEconomizer, then five learning and five measured sessions with Microsoft's
TokenEconomizer plugin loaded through the Claude Code --plugin-dir flag.

### Requirements

- Talon CLI built from the **merged budget-governance main** (PR #508), not an
  older binary/release. For an explicitly reviewed source revision, use
  `cef6313c42a44ab9ab64de0e879147bf50370ea3` (Go 1.26.10).
- Official Claude Code CLI on PATH, with non-interactive print mode and --plugin-dir.
- Python 3.10+, Git and connectivity to the Anthropic API.
- An Anthropic API key with active API billing, not only a Claude subscription.

### Compatibility and run

The **credential-free real-Talon contract** is a separate CI job, not a mock
replacement for Talon. It builds the above merged `main` revision, starts
the real Talon gateway with a local Anthropic-wire mock (no external key or
Claude CLI), reuses the two exact demo agent policies, confirms pricing of
`claude-sonnet-5`, verifies cross-session agent budget denials before
provider dispatch, and verifies the signed receipt exports. The mock
deliberately bills one huge response above $5 to demonstrate **estimate
overshoot**: Talon prevents further admission, but cannot stop billing
within an already-admitted request.

Locally run `make tokeneconomizer-contract` with a Talon binary built from
that same main revision on PATH. This validates the gateway/CLI boundary
without spending money. CI's fixed commit is a reproducibility fixture;
when upgrading to a newer Talon main, update the fixture SHA and rerun it
before claiming compatibility. The real Claude Code/TokenEconomizer plugin
integration **still needs the paid smoke**.

    make tokeneconomizer-validate       # offline fixture and report invariants
    make tokeneconomizer-contract       # real Talon gateway / mock Anthropic / $5 denial / signed evidence
    export ANTHROPIC_API_KEY='sk-ant-...'
    make tokeneconomizer-smoke          # one real task per arm, checks integration
    make demo-tokeneconomizer           # full real comparison, subject to $5/arm policies
    make present-tokeneconomizer        # replay the latest table without new API calls

The run prints a before/after table for **Talon-estimated USD cost from real
Anthropic usage**, input and output tokens, cached-input tokens, runtime,
independently graded **sealed Python tests** (three input cases per function,
executed outside Claude's editable workspace), provider calls, and signed
Talon evidence. It also saves an audience-friendly
HTML comparison under .state/tokeneconomizer-demo/<RUN_ID>/comparison.html,
JSON data, and signed per-session Talon receipts under the same run directory.
The report also separates cache-read and cache-write tokens and records
the CLI versions used to reproduce it.

**Talon cost policy: USD $5 per arm (USD $10 across the experiment).** Each arm
uses its own Talon agent with `cost_limits.daily: 5.00` and
`cost_limits.monthly: 5.00` plus a `session_limits.max_cost: 5.00` safeguard.
Talon enforces each agent's **aggregate** daily/monthly limit across all its
Claude CLI task sessions. Both the baseline and the TokenEconomizer arm include
all warmup and measured requests in their budget. Policy is limited to the
configured, Talon-priced Anthropic model (default: `claude-sonnet-5`).
Synthetic Python prompts and responses are PII-scanned in **warn** mode so
benchmark content is not silently rewritten or blocked. Local file/test tools
remain Claude Code permissions, not Talon-controlled actions.

The $5 values are **pre-request admission budgets, not a guaranteed invoice
hard ceiling**: Talon checks the model cost estimate before forwarding requests,
but a request costing more than estimated can overshoot. This is why the report
shows the total including warmups for each agent and marks a budget-stopped arm
**incomplete**, with no before/after savings percentage. Actual billed provider
cost can differ from Talon's pricing-table estimates. The user must still monitor
their Anthropic billing limits.

Five warmups per arm are excluded from the headline comparison, but their
spend is recorded separately in the JSON and counted against the $5 arm cap.
The sampled task count is small (five measured repairs per arm),
so results are not a statistically powered measure of product savings.
Runs that fail grading, contain a model/provider error, exhaust a budget, or
fail to show actual TokenEconomizer hook/mechanism activity are
**INCONCLUSIVE**: the report does not print a numeric savings percentage.
The one-task smoke intentionally reports INCONCLUSIVE by design; it is a
connectivity check, not a savings experiment. Partial reports remain available
when an individual task errors after the gateway starts. The
result can be a negative cost reduction; none is assumed in advance.

Each model call must have session-correlated, agent-attributed signed evidence
that passes Talon's offline signature verification. The independent Python
test outcome determines task correctness, not Claude's self-assessment.

Tool pruning may modify only the synthetic repository's local Claude settings;
the plugin is given isolated state and a five-session threshold. The upstream
TokenEconomizer revision is pinned to
`0ce0e067b42b1dd5a5f5984275d07f8c7686c44a` so changes to its main
branch cannot silently alter the experiment. Upstream notes that a recorded
Claude Code tool catalog is important to make pruning effective; this pilot
does **not** guarantee a measurable improvement on tiny synthetic tasks. The operator's
real upstream API key is stored in a local Talon encrypted vault, never passed
to Claude Code, written to reports or committed to Git. It is passed to Talon
vault setup by stdin (not process arguments), and both Claude Code and Talon
receive an allowlisted environment with unrelated host credentials removed.
The provider secret is accessible only to the two benchmark agent identities.
The demonstration uses small bounded coding tasks and eight maximum agent turns
per task.

This demo governs only the model traffic that actually crosses Talon. File
edits, local shell/test execution and bypass traffic remain outside the Talon
enforcement boundary.
