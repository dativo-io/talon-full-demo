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


## TokenEconomizer × Talon — real coding-agent cost study

### NEW: original Microsoft benchmark mini-pilot

A separate, opt-in mode invokes Microsoft's **unmodified experimental Web-Bench
harness** (baseline vs `trimech-web`, real `expressjs` tasks) using Copilot CLI
Anthropic BYOK routed **through Talon**. Both arms have separate $5 admission
limits and verified signed cost exports. This is **not** the installable
TokenEconomizer plugin, and it does not replace the 24-ticket synthetic study.

- **Prerequisite:** Web-Bench requires **Node.js 22+**, plus npm/npx. On Ubuntu, install Node 22 with [nvm](https://github.com/nvm-sh/nvm) if `node --version` fails, then run `nvm use 22`. The [setup guide](docs/TOKENECONOMIZER_REFERENCE.md#ubuntu-host-prerequisites) provides exact commands and Playwright troubleshooting.
- **No spend:** `make tokeneconomizer-reference-plan`
- **Pinned CLI prerequisite:** install standalone `copilot` v`1.0.84-7` (`curl -fsSL https://gh.io/copilot-install | VERSION=1.0.84-7 PREFIX="$HOME/.local" bash`) and ensure `$HOME/.local/bin` is on `PATH`. `gh` alone does not satisfy this requirement.
- **Keyless data setup:** `make tokeneconomizer-reference-prepare` (downloads/builds upstream benchmark, but no provider calls)
- **No-spend readiness:** `make tokeneconomizer-reference-check`
- **No-spend diagnosis of existing runs:** `make tokeneconomizer-reference-diagnose` (or set `TE_REFERENCE_RUN_DIR=...`)
- **No-spend valid task-pair comparison:** `make tokeneconomizer-reference-analyze` (also supports `TE_REFERENCE_RUN_DIR=...`), excluding unreached tasks and incomplete usage, even when the wrapper proof is absent.
- **Paid full 20-task stream only:** `TE_REFERENCE_PAID_CONFIRM=YES TE_REFERENCE_FULL_STREAM_CONFIRM=YES make tokeneconomizer-reference-run` — default $5 estimated admission/arm, may terminate before the final task. Higher budgets require separately confirmed opt-in (see the guide).
- **Long-run safety:** the full-project harness has a 4-hour timeout **per arm**, private live harness logs, and kills its process group on timeout; run from `tmux` if using SSH.
- **Full setup and methodology:** [Original Web-Bench pilot](docs/TOKENECONOMIZER_REFERENCE.md).

**The 2026-10-23 six-task pilot is invalid for optimizer conclusions.** Its shortened range made the official Web-Bench evaluator set `startTask`, which starts from the fully implemented reference `src/` rather than the intended `src-init/`. Both agents consequently found task 1 already complete and submitted no file edits. Chromium also lacked an Ubuntu shared library (`libatk-1.0.so.0`), now repaired and guarded with a local smoke test. The runner now **fails closed on partial streams**, checks initial-vs-gold source provenance, and requires an extra explicit confirmation for the real full-20-task study. Talon's signed cost evidence is valid, but the pilot does not establish TokenEconomizer savings. See the [benchmark root-cause analysis](docs/TOKENECONOMIZER_REFERENCE.md#forensic-result-why-the-six-task-run-was-invalid).



This optional demo uses **real Claude Code → Talon v1.15.3 → Anthropic
requests**, separate governed agent identities, a Talon vault, per-session
signed receipts and independent correctness grading. All state lives in the
Git-ignored `.state/tokeneconomizer-demo/` directory. This is a **production
TokenEconomizer plugin** study, NOT a reproduction of the paper's experimental
controller or its 277-task SWE-Bench results.

### Two modes with different goals

| Command | Goal | Workload | Billable? |
|---|---|---|---|
| `make tokeneconomizer-validate` | Check fixtures, proof gates, seed handling, grading and report code | 24-ticket fixture + negative tests | No |
| `make tokeneconomizer-contract` | Verify released Talon gateway, budgets, Anthropic wire and signed evidence against local mock | Gateway mock | No |
| `make tokeneconomizer-smoke` | Ensure Claude Code, plugin and Talon can complete one real coding task in each arm | Original simple fixture | **Yes** |
| `make demo-tokeneconomizer` | Study actual plugin effectiveness across a persistent repository stream | **24 linked tickets per arm**, seed 0 | **Yes** |
| `make tokeneconomizer-study-3` | Three independently seeded 24-ticket streams with **USD 1.66/arm per seed**; may stop before all tickets | Up to 144 paid task attempts, **never guaranteed to finish** | **Yes** |
| `make present-tokeneconomizer` | Read the most recent report without paying again | Existing saved evidence | No |

The original one-task smoke remains a connectivity check. Do not use its
cost delta as an optimization result.

### Prerequisites and Ubuntu setup

Talon **v1.15.3** is pinned in
[`config/tokeneconomizer-talon-release.txt`](config/tokeneconomizer-talon-release.txt),
which CI installs by published tag. The keyless contract and both paid modes
refuse a different binary. Requires a supported Claude Code CLI (`--plugin-dir`,
`--effort high`), Python 3.10+, git, Anthropic API billing and an API key.
Go 1.26.10 is needed only to build Talon from source/module.

```bash
go install github.com/dativo-io/talon/cmd/talon@v1.15.3
export PATH="$(go env GOPATH)/bin:$PATH"
talon version                 # use 'talon version', NOT '--version'
cd ~/src/talon-full-demo
git pull --ff-only
make tokeneconomizer-validate
make tokeneconomizer-contract
export ANTHROPIC_API_KEY='sk-ant-...'
make tokeneconomizer-smoke
make demo-tokeneconomizer        # $5.00 per arm; billable; may end early at budget limit
make present-tokeneconomizer     # free; replays latest saved evidence
```

If Talon is not on PATH, set `TALON_BIN=/absolute/path/to/talon`
for the Make targets. `scripts/with-talon.sh` also resolves common local
install locations.

If your terminal prints only `PASS: Talon stable release v1.15.3
compatibility`, that confirms **only the keyless contract**. The paid
runner starts *after* that; it prints its mode, task count, per-arm
budget, setup milestones and task-level cost as it progresses. If the
shell prompt has not returned, the paid run may still be executing.
`make present-tokeneconomizer` opens the latest saved run, not an
in-progress run. To run these commands conditionally, use
`make demo-tokeneconomizer && make present-tokeneconomizer` rather
than assuming a passed contract proves the paid benchmark completed.

### Why the study changed

Our first real v1.15.3 10-task pilot on 2026-10-23 verified its
signed evidence and grading but **did not demonstrate savings**:
measured provider cost went from USD 0.3022 to USD 0.3495
(**+15.6%**); cache reads fell **20.8%**, cache writes rose
**88.4%**. Both arms passed five measured repairs. This is a genuine
observation, but one tiny task dominated the result, the plugin's
tool-pruning quiet-time delay had been forced to zero, and almost no
micro-skill or loop-guard learning was possible. **Do not market
those numbers as representative of the original research.**

### Latest operator run: 24-ticket study (2026-10-23)

The operator's completed seed-0 run `20261023T133101Z` is a **negative,
non-activating production-plugin observation**, not evidence of paper
replication. From the terminal log and its local `proof.md`:

- Independently graded success: **24/24 baseline, 24/24 plugin**; zero
  cumulative hidden regressions.
- **Whole-stream** Talon-estimated cost: **USD 3.2904 baseline vs USD
  3.3560 plugin** (**+1.99%**). The last 16 tickets alone cost USD
  2.1674 vs USD 2.1083, but that excludes the expensive learning phase.
- **119 vs 113** provider calls, with matching verified Talon signed
  evidence counts, according to the saved local proof.
- The plugin recorded **24 hook sessions, 11 proposed tool removals,
  zero applied removals, zero injected micro-skills and zero nudges**.
  Hook execution and proposals are not optimizer actions. The short
  study did not establish that the production quiet-time pruning
  mechanism had an opportunity to activate.

**Important budget exception:** This historical run was configured with
**USD 7.50 per arm**, conflicting with the agreed USD 5.00 admission
ceiling. Its *actual Talon-estimated spend* was below USD 5.00 per arm,
but that does not retroactively fix the configured prevention rule.
The runner, Make targets, tests and proof evaluator now enforce the
correct USD 5.00-per-arm ceiling. Old local evidence is preserved as
recorded, not relabeled as a compliant run. The logs and signed receipts
remain local to the operator; the terminal summary alone is not an
independently published evidence package.

**Why activation was unlikely:** The upstream plugin defaults to an
**hour of repository inactivity before applying an automatic tool-pruning
deny list**, while this study issued successive short tasks. Its free
micro-skills require recurring environment failures across sessions,
and the failure-loop guard needs repeated failing attempts inside a turn.
The all-green 24-ticket result supplies little evidence for either.
These are eligibility limitations, **not evidence that the plugin is
broken**. See [upstream plugin settings](https://github.com/microsoft/TokenEconomizer/blob/main/plugin/README.md).

**Next experiment gate:** First establish an observable mechanism
(injection, applied tool pruning or loop nudge) in a genuinely eligible
workload. Repeating short default-plugin runs with zero interventions
would only measure sampling variation, not TokenEconomizer effectiveness.
Do not automatically start the three-seed paid run before this gate.

The revised default study uses a persistent Python service repository
with **24 incremental tickets** spanning normalization, routing, data
policy and usage billing. Each ticket requires navigating issue
descriptions and test conventions and modifying the shared domain
implementation **and** public service registry. Visible tests are
available in the checkout; hidden acceptance tests run in a fresh,
separate grader directory so editing visible tests cannot fake success.
After every ticket, the grader **also re-runs all previously successful
hidden ticket checks** to detect regressions of existing features.
Fixes accumulate in each arm's repository over the entire stream.
Three seeded orders keep task pairs aligned while varying experience
and alternating which arm executes first.

Eight tickets form the learning phase, and the remaining 16 show the
later trajectory. **The headline cost always includes ALL 24 paid
tickets per arm**, including learning. The late-phase figure is
diagnostic, not a cherry-picked replacement for acquisition costs.
The report shows correctness (resolved tickets), full-stream USD,
USD/resolved ticket, cache reads/writes, the **pricing decomposition**
of cache reads versus expensive cache writes, per-ticket signed evidence,
and cumulative break-even. Explicit **high** reasoning effort,
up to **24 turns** and bounded **900-second** task execution are used,
not the prior eight-turn quick-fix configuration.

### Plugin defaults matter

The official production plugin's normal idle-time tool-pruning delay
is preserved. No `TE_TOOLPRUNE_QUIET_MINUTES=0` override is used in
the default study. We perform the plugin's documented **no-model tool
catalog capture** before the plugin arm starts, and record whether it
succeeded. Paid LLM-assisted plugin helpers remain disabled
(`TE_PAID=false`), matching the shipped no-paid-helper baseline.
Micro-skill injections, actual pruning applications, and loop nudges
are recorded when they occur; a hook's mere existence does not prove
intervention. When none occurs, **we report that honestly**.

To investigate cache-prefix invalidation explicitly, a separately
labeled accelerated ablation is available via
`TE_DEMO_PRUNING_MODE=accelerated make demo-tokeneconomizer`. That
is **not** the default and the production-default evaluator does not
accept its result as a normal-configuration savings claim.

### Study budgets and costs

**All paid demo modes honor the agreed USD 5.00 baseline / USD 5.00 plugin
Talon admission-policy ceiling.** Both the one-task smoke and the
24-ticket comparison use a fresh Talon store with **USD 5.00 daily/monthly
per agent**, and all learning and measured sessions consume that same
arm's allowance. The runner **rejects a budget greater than USD 5.00**
even when invoked directly rather than through Make.

The optional three-seed study uses **USD 1.66 per arm per seed**
(three fresh Talon stores × USD 1.66 = **USD 4.98 per arm across
the entire three-seed invocation**, USD 9.96 combined). It does not
give each seed a new USD 5.00 allowance. It cannot guarantee completing
24 issues in each seed under this budget. The study preserves partial
task evidence and reports **INCONCLUSIVE** if a limit prevents a
comparable full run; do not interpret a truncated comparison as
TokenEconomizer succeeding or failing.

**These are Talon estimation-based admission-policy ceilings, not
guaranteed hard limits on Anthropic invoices.** A permitted request can
cost more than its admission estimate, so actual provider billing may
overshoot. Keep an Anthropic account-side usage limit or billing alert
if a strict externally billed amount is required. The keyless contract
and offline proof checks make no billable provider calls.

Talon enforces model/provider and agent budget rules on gateway traffic;
Claude Code's local file and shell actions are not governed by Talon.
The operator Anthropic key is stored through stdin in Talon's encrypted
vault, never supplied directly to the coding agent or plugin.

### Proof standards and reports

Every run saves:
- `comparison.html`: first-screen proof verdict, signed-vs-graded
  metrics, and a cumulative savings table by ticket
- `proof.md` and `proof.json`: reasoned conclusion, passing/failing
  gates, resolved counts, per-task receipts and whole-stream economics
- `comparison.json`: raw experiment metadata and cost summaries
- `baseline/task-NN/signed.json`, `after/task-NN/signed.json` and
  corresponding `metrics.json`: individually verified, agent-attributed
  signed Talon evidence

The study yields **INCONCLUSIVE** when paired task identities,
identical initial repo hashes, high effort, CLI/provider/model metadata,
signature verification, spent-cost reconciliation, or completion fail.
**QUALITY_REGRESSION** means outcomes or previously working tickets got worse;
**NO_OPTIMIZER_INTERVENTION** means no mechanism acted and cost was not
lower; **NOT_DEMONSTRATED** means an intervention occurred but the
whole stream was not cheaper;
**LOWER_COST_UNATTRIBUTED** means lower spending without a demonstrated
plugin intervention; **PRELIMINARY_SAVINGS** means one observed run was cheaper,
the plugin acted, and graded completions were preserved.
None of these constitutes paper replication or causal evidence.

The optional three-seed aggregate compares independently initialized
runs without dropping losing seeds. It also rejects a cumulative
admission allocation greater than USD 5.00 **per arm across all three
seeds**, and requires the **same demo git revision,
Claude Code version and plugin/model config** for all three seeds. It produces
`.state/tokeneconomizer-demo/study-aggregate.md` and
`study-aggregate.json`. A repeated direction across three seeds
still supports only a **bounded, synthetic, observational claim**,
not a generalizable ROI prediction.

```bash
make present-tokeneconomizer
cat ".state/tokeneconomizer-demo/$(cat .state/tokeneconomizer-demo/latest.txt)/proof.md"
# Only when ready for three separate billable runs:
make tokeneconomizer-study-3
cat .state/tokeneconomizer-demo/study-aggregate.md
```

### Relationship to the original research

The original [TokenEconomizer paper](https://arxiv.org/abs/2610.22732),
[project page](https://tokeneconomizer.github.io/) and
[reference experiments](https://github.com/microsoft/TokenEconomizer/tree/main/experiments)
use a **different experimental controller** with independently isolated
real SWE-Bench tasks, official grading, long repository streams, and
three seeds. The paper's `trimech` activation, cost model and failure-loop
actions are **not interchangeable** with the published production plugin.
To reproduce the paper, use its reference experiment harness, official
tasks/images and graders. Our 24-ticket scenario is an affordable
production-plugin effectiveness **pilot** with Talon observability and
signed evidence. It has deliberately narrower external validity.
Read [the upstream plugin methodology](https://github.com/microsoft/TokenEconomizer/blob/main/docs/PLUGIN.md)
before using these pilot outcomes as research evidence.
