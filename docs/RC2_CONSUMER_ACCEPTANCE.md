# Talon v1.17.0-rc.2 — Full Demo consumer acceptance evidence

*2026-11-21. Internal release-compatibility record, not complete Full ACME LIVE acceptance. The core release itself has passed; Full Demo uses its own consumer fixture and independent downstream checks.*

## Immutable provenance

| Item | Verified value |
| --- | --- |
| Core release | [Talon `v1.17.0-rc.2`](https://github.com/dativo-io/talon/releases/tag/v1.17.0-rc.2) — published prerelease 2026-11-21T07:52:07Z, **not stable v1.17.0** |
| Annotated tag object | `3e10f674b62cf1abfd5527a16c891810115b1f18` |
| Tagged core commit | `3f3f20dff910dc2416c8d82467de2d4e2dd8acc5` (contains merged #562–#569/#572) |
| Linux/amd64 release archive | `talon_1.17.0-rc.2_linux_amd64.tar.gz` |
| Release archive SHA256 | `5ba2021a7da0ad704a4c3b21e319e05b96fa0347d7d43318ed30bead357ba47c` |
| Full Demo published-binary consumer run | **PASS** [#52 workflow 44882306751](https://github.com/dativo-io/talon-full-demo/actions/runs/44882306751), with explicit GitHub release digest match, archive sha256 check, binary-version and build-information checks |
| Talon core published-artifact release checks | **PASS** [release run 44881314831](https://github.com/dativo-io/talon/actions/runs/44881314831), including official first/second app pilot, console, cold backup/restore, OpenShell showcase packaging, reviewer/action and signed evidence |
| Tagged-source regression compatibility | **PASS** [Full Demo 44881660657](https://github.com/dativo-io/talon-full-demo/actions/runs/44881660657): exact RC2 commit and pre-RC2 regression. This is secondary evidence, not release-artifact acceptance. |
| Cross-PR merge rehearsal | **PASS** [combined tree 44882124040](https://github.com/dativo-io/talon-full-demo/actions/runs/44882124040) on #45/#46/#52/#51 versions at that run; rerun on latest tips before final merge |

## What Full Demo ACTUALLY executed on the published RC2 binary

| Buyer-visible case | Independent action and result | Evidence | Verdict |
| --- | --- | --- | --- |
| **Shopify-style Customer Support / read & draft** | Real n8n **2.48.5** imported/executed order status, EUR249 refund review request, wrong sender negative, EUR25 and EUR750 draft outputs; initial three acceptance cases had 3 read-only Shopify-shaped fixture requests and 2 minimized deterministic-provider calls; two additional refund proposals ran later under the same key (5 reads and 4 upstream drafts in total), no financial mutation; native use-case registration and company PII **block** with zero provider dispatch | Same-use-case signed model/session records 2 valid, no leaked raw credential in export | **PASS — deterministic synthetic** |
| **Support canonical refund operations** | Official stock-node action graph imported separately into real n8n on the **same Talon instance and `customer-support` key**. Saved actual Stage A terminal output supplies amount to trusted request caller. EUR750 company DENY → 0 synthetic downstream calls; EUR25 allow → 1; EUR249 independent reviewer approval → zero until a separate authorized claim → 1. Same-operation replay / changed args no second call. | Signed valid operation lifecycles for all three; independent two-call fake finance ledger, distinct idempotency keys, no refund URL in n8n workflow | **PASS — deterministic synthetic, not Shopify refund** |
| **People Analytics** | Real Talon LLM gateway+MCP tool loop with isolated synthetic model and DuckDB backed HR service; allowed bounded aggregates, refused employee export with zero upstream executions, independent HR/SQL safeguard | Multiple signed model/MCP proxy records, same session and actual ID correlation | **PASS — isolated HR fixture** |
| **Document Processing cost boundary** | Two separately budgeted $5 synthetic agents, Anthropic-shaped requests, priced usage and two preventive admission denials with zero dispatch | Signed valid Talon budget/denial evidence; **not** paid Anthropic or customer invoice | **PASS — synthetic budget contract** |
| **OrderDesk/Engineering** | Real PostgreSQL synthetic staging drift (SQLSTATE `28P01`), business recovery; protected synthetic production row count 1,000. Real RC2 HOST-key Talon company delete DENY/zero effect, reviewer approval has no effect until claim; one dispatch, no replay | Signed Talon operation lifecycle and independent PostgreSQL/infra counters | **PASS — host-key preflight only** |
| **Native operator Console** | `talon ui serve --help` checked from official RC2 binary. Separately the **core release pilot** verified native Console/operations including first/second use case, signed evidence and restore | Full Demo did **not** pair browser against four apps or check all seven native pages on same ACME runtime | **PARTIAL; Full Demo UI browser NOT RUN** |

**Honest claim:** Each *tested* consumer application path works against published RC2, and its independent synthetic effects match Talon's signed enforcement. A green availability probe was not used as a substitute; the actual published-binary consumer job ran and passed.

## Missing Full Demo acceptance — do not conflate with above

- **Unified First Production Pilot / Full ACME:** four existing apps have NOT all connected to **one persistent company deployment** in one run; cross-application mandatory company policy inherited with real observed traffic and separate keys is still the next Full Demo consumer gate. The core official native two-use-case pilot *has* passed; that is product capability, not proof of the specific ACME app wiring.
- **Actual external integrations:** no paid-provider LIVE failover/PII-redaction wire capture in joined Support; Shopify read/order and refunds are synthetic, not a test store or settlement. Email sender verification is operator-attested in fixture.
- **OrderDesk:** real Claude Code/OpenShell delegated same-hop C01–C12 and sandbox egress denial/production invariants as one coherent manifest have not passed. HOST-key action and PostgreSQL are not equivalent.
- **Operations UI / recovery in ACME:** no Full Demo paired seven-area browser journey, backup/restore with the same multi-app state, or full buyer+technical same-run projections.
- **Packaging:** Shopify Stage A read/draft and official canonical action still require **two actual n8n workflow imports** and a trusted synthetic handoff. Not a published single-import n8n marketplace refund template; no alternative approval engine.
- **Semantics:** approval authorizes without dispatch; Talon at-most-once **dispatch within a durable boundary** is not exactly-once external business effects. `UNKNOWN` requires business reconciliation. Budget admission is estimate-based and signed HMAC evidence is tamper-evident, not immutable.

## Merge and product-level acceptance checklist

- [x] Exact RC2 tag and official immutable Linux archive digest verified
- [x] Release-core pilot and operations gate passed (separately)
- [x] Full Demo published-RC2 Shopify, HR, budget and HOST-key OrderDesk synthetic consumer tests passed
- [x] Combined four-PR tree merge + local static tests passed at [rehearsal 44882124040](https://github.com/dativo-io/talon-full-demo/actions/runs/44882124040)
- [ ] Re-run merged-tree checks against **the final tips** of #45/#46/#52/#51 immediately before actual merges
- [ ] Shared persistent ACME two-app first pilot with real registered→loaded→connected→governed proof (Full Demo apps)
- [ ] Full ACME four-app same-run session, native Console and backup/restore
- [ ] Actual LIVE provider/test-store where separately authorized, if presented as such
- [ ] Real Claude/OpenShell C01–C12 integrated safety proof

Do not merge the four draft PRs merely because the published RC2 **component** acceptance passed. Keep the buyer-facing [ACME demo index](DEMO_EXPERIENCE_INDEX.md), [walkthrough](SHOWCASE_LIVE_WALKTHROUGH.md), [scorecard](COMPETITOR_PROOF_SCORECARD.md) and [limitations](CUSTOMER_ADOPTION_FRICTION.md) consistent with this evidence.

### Source of truth
- [Published RC2 binary acceptance / job](https://github.com/dativo-io/talon-full-demo/actions/runs/44882306751)
- [Talon official prerelease and assets](https://github.com/dativo-io/talon/releases/tag/v1.17.0-rc.2)
- [Core release acceptance](https://github.com/dativo-io/talon/actions/runs/44881314831)
- [Joined tagged-source CI](https://github.com/dativo-io/talon-full-demo/actions/runs/44881660657)
- [Combined PR merge rehearsal](https://github.com/dativo-io/talon-full-demo/actions/runs/44882124040)
