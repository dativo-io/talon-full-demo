# Customer adoption friction — First Production Pilot

This report records actual observations, not assumed customer feedback. A source review is not a clean-install or runtime test. Append dated, reproducible results (artifact tag/checksum, platform, commands, evidence links; no credentials). Severity is the impact on adoption, not a claim about exploitability. Distinguish OSS product defects, Full Demo defects and presentation improvements. Report demonstrated product defects to [OSS #533](https://github.com/dativo-io/talon/issues/533) or [#561](https://github.com/dativo-io/talon/issues/561); customer activation is [Enterprise #32](https://github.com/dativo-io/talon-enterprise/issues/32).

| Attempted step / evidence | Expected experience | Actual observation | Workaround / next action | Severity and owner |
| --- | --- | --- | --- | --- |
| 2026-11-18: source review of PR #46 installation guide | Install a verified published artifact without Go/source build | Prior guide used floating @main. Runtime installation NOT RUN. | PR #46 now documents candidate/stable artifact gate; exact tested stable pin and command still required. | High — Full Demo #46; upstream release readiness #533/#561 |
| 2026-11-18: static Compose mount review of PR #46 | Console gets only required files/credentials | Prior console inherited whole case mount including secret-bearing .env; no runtime leak test performed. | PR #46 removes that mount and adds static regression guard; validate with actual paired console. SQLite WAL directory access retained. | High — Full Demo #46 |
| 2026-11-18: source review of PR #45 and #42–44 | Existing application recovery with verified agent and exact policy | Fixture/host-key preflight described; real shared-session C01–C12 not verified independently. | Keep buyer-ready false; run ratified integration contract with pinned published artifacts. | High for full showcase — Full Demo #42–44 |
| Published artifact install, first use-case registration and browser pairing | Supported clean install and observable real traffic | NOT RUN | Record exact commands, duration and results; no claims until observed. | Unassessed — #46/#48; OSS #561 if reproduced product defect |
| Argument-aware refund, exact approval/replay/unauthorized tests | Real released authorization and zero unauthorized downstream calls | NOT RUN | Use released #205/#433/#434 contract and independent finance ledger. | Unassessed — #34/#49; OSS #561 if product defect |
| Persistent restart/recovery and second inherited use case | State/keys/evidence preserved; policy inheritance proved | NOT RUN | Follow documented supported runbook; record backup/restore where practical. Reset is not recovery. | Unassessed — #48; OSS #561 if product defect |

At each rehearsal replace or append rows with actual evidence; keep failed and NOT RUN outcomes visible. Presentation polish never substitutes for customer acceptance.

## 2026-11-20 — real core-main integration findings

**Development-only validation, not a customer release.** [Full Demo #52 CI 44826296354](https://github.com/dativo-io/talon-full-demo/actions/runs/44826296354) ran a pinned Talon `main` source build (commit `5912dc1215cc`) with real n8n 2.48.5, synthetic Shopify lookup/provider and independent synthetic refund ledger. The support draft and canonical n8n refund were governed by **one native customer-support key and one running Talon process**. Native company PII deny blocked upstream traffic, €750 company DENY produced zero finance dispatches, €25 ALLOW one call, €249 independent reviewer approval zero-before-claim / one-after-claim, replay/conflict zero extra; signed action lifecycle valid. The source reference's separate broader tampering/UNKNOWN test also passed in that CI job.

| Friction or concern | What is actually known | Owner / exit gate |
| --- | --- | --- |
| n8n version fragmentation | Existing released Stage A tested on n8n 2.30.4; core canonical action reference verified on 2.48.5. The joined core-main lane therefore uses 2.48.5. | #49/#52: select supported and pinned consumer version; run both workflows and real webhook against that same version; no silent assumptions |
| Two n8n workflow imports | The Stage A standalone template is read/draft only; joined CI imports an additional upstream canonical action graph. The harness performs the trusted synthetic request handoff. No single standalone full template exists. | #34/#35/#50: document trusted operator decision and reference workflow install with native credentials; only advertise completed one-import automation if shipped and tested |
| Source build vs published artifact | Main-native path and action ref are proved in CI, but v1.17.0 has not been published and a stable artifact did not execute this joined path. | OSS #561 / #48 / #52: replay joined acceptance on the verified final stable digest with native persistent installation |
| Buyer-proof boundary | Independent synthetic ledger makes the action decision real; no Shopify payment, real model, external reviewer device, recovery or second ACME use case in this particular run. | #48–50: actual customer-app adoption evidence, second inherited use case, real provider and supported recovery; fail closed on missing proof |
| Operator-key separation | Native registration mints a use-case key, reviewer has a separate credential, exported stock workflow contains no raw secret; source-main CI covers these. | #52: preserve per-tenant scoped vault secret ACLs, supported pairing and post-restart credential behavior in stable acceptance |
| Review timing | We have automated CI durations, not measured external customer onboarding timing. | #50: measure prepared install+pair, first/second integration, investigation; report prefetch/exclusions |

The successful joined source-main fixture is useful technical proof but not evidence that an external engineer can independently adopt Talon in under 15 minutes, nor a substitute for complete pilot/ACME acceptance.

## Buyer-win adoption and competitor benchmark gaps (2026-11-20)

The reviewed alternatives are **Bifrost, LiteLLM, Portkey, Solo.io agentgateway and TrueFoundry**; see the [competitive scorecard](COMPETITOR_PROOF_SCORECARD.md) and [buyer-win strategy](TALON_BUYER_WIN_STRATEGY.md). No head-to-head implementation trial has been performed against any competitor. Do **not** interpret the current candidate-only or deterministic CI as proof of lower adoption cost.

| Customer question / experiment | Current observation | Measured counterfactual needed | Gate / owner |
| --- | --- | --- | --- |
| "Could we do the same with existing gateway?" | LiteLLM/Bifrost/Portkey offer routing/budgets/MCP; Portkey/TrueFoundry have agent-management stories; Solo enterprise can apply guardrails and ext-auth | Two existing apps integrated on Talon and rival stack, same baseline and same action outcome, operator hours and duplicated services counted | Product discovery, #47/#50 |
| "Do native reviewers really remove engineering code?" | Joined source-main n8n test uses **two imported real n8n graphs** and a trusted synthetic handoff runner; not one customer-installable package | User independently imports/installs official reference, creates separate approver creds, completes same refund without bespoke approval store | #34/#49/#52 |
| "Can I prove what happened after a crash?" | Signed action lifecycle and replay/changed args passed for synthetic operation; real persistent restore + `UNKNOWN` **in Shopify case** not accepted | Kill/restore Talon during specific synthetic operation; reconcile downstream ledger; verify no blind redispatch and preserved approvals/IDs/evidence | #48/#49 and core native ops |
| "Are these real data/PII and spend controls?" | Shopify passes app-side minimization and separate Talon PII **block**; this is not wire-level redaction. Document cost test is synthetic. | PII redaction proved by captured upstream request; actual provider fallback attempts, cost basis and first useful n8n document outcome | #49/#50 |
| "Does onboarding actually get faster?" | Targets <3 min install, <5 first, <2 second, <1 denial diagnosis are **not measured** | Timed external unassisted session; record prefetch, keys, deployment environment, troubleshooting, baseline competitor | #48/#50 |
| "Is this the requested release?" | Official RC2 artifact was **published on November 21** with immutable Linux/amd64 SHA256 `5ba2021a7da0ad704a4c3b21e319e05b96fa0347d7d43318ed30bead357ba47c`; the Full Demo's published-binary consumer job must independently PASS. The latest stable v1.16.1 does not include complete new action contract. | Published exact tag/digest, consumer job actually ran, business receipts and verifier trace reference that digest | #47/#48/#52; core release |
| "Is each PR actually green?" | On Nov 20, #52 latest checks had a shell-harness duplicated tail syntax error despite completed earlier actual action tests. Fix committed separately; do not assume the latest CI is green without checking it. | New-head Actions check pass for released-artifact lane and candidate lane, plus exact artifact evidence | #52 |

A skeptical buyer's request to compare *actual implementation cost* with an existing rival is valid. Record **"Not measured"**, not `Talon faster`, until the same app, operator constraints and failure scenario have been executed against both stacks.

## Native v1.17.0 consumer acceptance — pending

The complete stable release (core #562–569 and #572) is required for integrated pilot/ACME. RC.1 is not complete. Core #563's no-clone quickstart is a separate disposable proof (no actual provider or console); follow the supported persistent profile for adoption. Do not mark the quickstart as an enduring shared installation. No new runtime tests were performed in this product-alignment update.

| Measure | Target on prepared host | Actual / evidence |
| --- | --- | --- |
| Native install + console pair | <3 min | NOT RUN |
| First use case registered through governed traffic | <5 min | NOT RUN |
| Second use case with inherited applicable mandatory control and first still working | <2 min | NOT RUN |
| Denied-action explanation and evidence verification | <1 min | NOT RUN |
| New application-specific governance infrastructure | None | NOT RUN |

For each use case record independent registered, loaded, connected and governed verdicts with exact artifact digest, runtime/effective policy, request/session/evidence references and downstream outcomes. Measure elapsed time from each first native operation to verified outcome; show excluded prebuild/download time separately. Keep actual failures visible. Verify company policy cannot be weakened by a use-case override according to the released contract. Do not count a config file alone as a governed application.
