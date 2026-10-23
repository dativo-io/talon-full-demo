# Original TokenEconomizer Web-Bench mini-pilot through Talon

**Implementation status:** opt-in runner added. No paid benchmark execution or live signed evidence has been produced by this change.

## Experiment design

This is separate from the 24-ticket synthetic/production-plugin study. It invokes the original Microsoft experimental harness and Web-Bench grader without patching either.

| Dimension | Choice |
|---|---|
| Microsoft revision | 0ce0e067b42b1dd5a5f5984275d07f8c7686c44a |
| Workload | Official Web-Bench, expressjs, first 6 sequential tasks (1–8 supported) |
| Arms | baseline vs trimech-web experimental controller |
| Agent | Copilot CLI with Anthropic BYOK, claude-sonnet-5, high effort |
| Model path | Copilot BYOK -> Talon v1.15.3 -> Anthropic |
| Admission budget | $5 baseline + $5 experimental; all calls included |
| Proof | Original graded tasks and full signed Talon export for both agents |
| Statistical strength | One seed, descriptive pilot only |

The original Claude Code experiment runner **hardcodes direct Anthropic
routing** and deliberately ignores ANTHROPIC_BASE_URL. The original Copilot
runner supports BYOK, so its base URL and generated Talon agent token can be
set without modifying Microsoft's experimental source.

The optimizer can issue its own Anthropic Messages requests. Those use the
same configured BYOK base URL and agent token; evidence is exported by **Talon
agent**, not a single Copilot session, so sidecalls are not excluded from costs.

**Grading caveat:** the original Web-Bench evaluator automatically switches to
development mode when the task range is truncated. This tightens Playwright
timeouts from 30 seconds to 2 seconds. Keep that upstream behavior unchanged,
but do **not** compare mini-pilot pass rates directly with full paper results.

## Free preparation

From the talon-full-demo checkout:

    make tokeneconomizer-reference-plan
    make tokeneconomizer-validate
    make tokeneconomizer-contract

The plan and tests perform zero provider calls.

## Web-Bench prerequisites

Prepare the Microsoft harness at the revision above in
.state/tokeneconomizer-demo/TokenEconomizer (the paid runner can clone and pin
it automatically), plus the official bytedance/web-bench repository. Follow
the upstream documentation at:

https://github.com/microsoft/TokenEconomizer/blob/main/experiments/README.md

That guide explains the Node/rush Web-Bench build, pinned Playwright browser,
and task export. The necessary exported paths are:

- TE_REFERENCE_PROJECTS: absolute canonical path to web-bench/projects
- TE_REFERENCE_TASKS: path to the exported webbench_tasks.json

The runner checks that the expressjs project exists, the official evaluator
has been built, and the first task IDs exactly match the frozen benchmark
task order. Missing prerequisites are reported **before** any model call.

## Explicitly paid run

Set the variables below in your terminal (replace paths and provide your own
provider credential):

    export TE_REFERENCE_PROJECTS="$HOME/te_data/web-bench/projects"
    export TE_REFERENCE_TASKS="$HOME/te_data/webbench_tasks.json"
    export TE_REFERENCE_TASK_LIMIT=6
    export ANTHROPIC_API_KEY='...'
    TE_REFERENCE_PAID_CONFIRM=YES make tokeneconomizer-reference-run

No external model call is made without the confirmation variable. The actual
Anthropic key is installed into Talon's encrypted vault through stdin and is
not forwarded to the Copilot process. The Copilot process receives only the
generated Talon identity and the local Talon BYOK URL.

The official harness performs billable preflight model checks before tasks;
they count toward the **same Talon $5 admission budgets** and signed exports.
The $5 figures are estimate-based admission ceilings, **not guaranteed
provider-invoice limits**. Set a provider-account usage limit if required.

Each run uses a fresh Talon data store and saves artifacts under Git-ignored
.state/tokeneconomizer-demo/reference-<timestamp>-<nonce>/:

- reference-proof.json: workload, original rows, signed costs and caveats
- official-results/: original Microsoft per-task rows and transcripts
- baseline/signed.json and after/signed.json: verifiable Talon evidence
- baseline/harness.log and after/harness.log: reference execution logs

A run is INCONCLUSIVE on missing or invalid signed evidence, incomplete task
execution, unexpected provider model/pricing, missing original task identities
or official harness errors. When both arms complete, the verdict is still
ONE_SEED_OBSERVATIONAL_ONLY. A savings or causality claim additionally
requires the original controller's mechanism traces, per-task correctness
and multiple independent seeds.

## Boundaries

- No modifications to Talon OSS or the released Talon gateway.
- No modifications to Microsoft's experimental controller, task definitions
  or grader.
- Not a test of the installable TokenEconomizer plugin.
- Never pool these costs or correctness metrics with the synthetic pilot.
- Talon governs model traffic, not local agent file/shell execution.
