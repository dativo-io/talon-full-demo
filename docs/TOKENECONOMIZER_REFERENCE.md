# Original TokenEconomizer Web-Bench mini-pilot through Talon

**Status:** the operator's first paid Web-Bench pilot (2026-10-23; expressjs first six tasks, seed 0) produced complete signed Talon model evidence, but both arms stopped after task 1 failed twice. The **root cause was a host dependency**, not task correctness: Playwright's Chromium executable could not load `libatk-1.0.so.0` (exit 127). Five later task rows per arm were `unreached` placeholders. Optimizer effectiveness remains **unmeasured**; the local Talon v1.15.3 contract passed. The free `prepare`/`check` and paid `run` paths now require a local browser launch/close smoke test, preventing a repeat of this avoidable spend.

## Ubuntu host prerequisites

**Web-Bench requires Node.js 22 or newer.** Its pinned `rush.json` declares
`nodeSupportedVersionRange: ">=22.0.0"`. Run the version checks first:

```bash
node --version
npm --version
npx --version
```

If `node: command not found`, install Node.js **22** using
[nvm](https://github.com/nvm-sh/nvm) (a per-user installation, no `sudo`
needed). The commands below use a pinned nvm installer; review third-party
install scripts before running them on a server.

```bash
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
nvm install 22
nvm alias default 22
nvm use 22
node --version        # expect v22.x.x
npm --version
npx --version
```

If you reconnect over SSH and `node` is missing again, open a login shell
or source `"$HOME/.nvm/nvm.sh"` as shown above. **Do not use
`sudo make tokeneconomizer-reference-prepare`**: it would run as root,
bypassing your per-user nvm installation and creating root-owned files.

### Install the pinned GitHub Copilot CLI (separate from `gh`)

The **reference** run uses the standalone `copilot` executable, **not** `gh`
and not the old `gh copilot` extension. Microsoft's pinned
`experiments/README.md` uses **Copilot CLI `1.0.84-7`**. This specific
version avoids silently changing the benchmark runner across attempts.
Install it as your normal Ubuntu user, not with `sudo`:

```bash
curl -fsSL https://gh.io/copilot-install | VERSION=1.0.84-7 PREFIX="$HOME/.local" bash
export PATH="$HOME/.local/bin:$PATH"
command -v copilot             # expect $HOME/.local/bin/copilot
copilot --version             # no provider call
```

GitHub's [official installer](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli)
supports both `VERSION` and `PREFIX` and installs to
`$HOME/.local/bin` for non-root users. Review the installer before running
it on a production host. If the binary exists but is not found, run
`export PATH="$HOME/.local/bin:$PATH"` (and add that line to your shell's
startup configuration for future SSH sessions). No GitHub login is required
**for the benchmark's Anthropic BYOK routing**; the CLI still must install
and launch successfully.

**Required, free preflight:** after installation, run
`make tokeneconomizer-reference-check` again. It verifies the original
task definitions, built evaluator, Copilot executable and its version
without authentication or provider calls. The script prints a warning if
the detected CLI version differs from the one the paper pinned.

The benchmark also needs Git, Python 3.10+, a C/C++ build toolchain (for
native Node dependencies), and the system libraries required by Playwright
Chromium. On Ubuntu, install common build prerequisites if they are absent:

```bash
sudo apt-get update
sudo apt-get install -y git curl build-essential python3 pkg-config
```

### Required browser smoke test: do not pay for broken Chromium

The first paid attempt failed because Playwright downloaded Chromium but Ubuntu
could not start it: `libatk-1.0.so.0: cannot open shared object file` (exit
127). On both arms, **only task 1 was attempted (twice)**; the other five rows
were not real task executions. The original Web-Bench grader was unable to
launch its browser, so zero task successes are **not** evidence about the
agent's coding quality or TokenEconomizer's effectiveness.

The demo now runs an **actual local Chromium launch/close** through the exact
project's installed `@playwright/test` before considering a host ready.
Both `make tokeneconomizer-reference-prepare` and
`make tokeneconomizer-reference-check` validate the browser; so does the
paid runner **before starting Talon and before any model calls**.

If that smoke test reports missing **system libraries**, use the Playwright
system-dependency installer (review its package changes):

```bash
cd ~/src/talon-full-demo/.state/tokeneconomizer-demo/reference-web-bench/projects/expressjs
npx playwright install-deps chromium
cd ~/src/talon-full-demo
make tokeneconomizer-reference-check   # MUST print PASS: local Playwright browser launch
```

`npx playwright install-deps chromium` may use `sudo` internally to install
Ubuntu packages. It installs operating-system libraries, **not** model or
provider packages, and makes no Anthropic API calls. Do not rerun the paid
experiment until the local launch passes. If problems persist, inspect missing
shared libraries with `ldd "$HOME/.cache/ms-playwright/chromium_headless_shell-1200/chrome-headless-shell-linux64/chrome-headless-shell" | grep 'not found'`
(the path is for the pinned Playwright browser from the operator log).
The setup runs upstream build scripts and downloads binaries but **never
uses the Anthropic model API**.

## Quick setup on Ubuntu

On the `feature/tokeneconomizer-claude-comparison` branch of `talon-full-demo`:

```bash
git pull --ff-only
make tokeneconomizer-reference-plan         # free, explains the experiment
make tokeneconomizer-reference-prepare      # no model calls, but clones/builds open-source code and downloads browser binaries
make tokeneconomizer-reference-check        # free, validates original Web-Bench project, evaluator and task order
make tokeneconomizer-validate               # free, local regression tests
make tokeneconomizer-contract               # free, live Talon gateway against a local mock
```

The **prepare** target downloads Microsoft TokenEconomizer at the reviewed pinned revision, clones ByteDance Web-Bench at pinned commit `7b31ca2b786eef120dd49ce63dd03d0c0006046d`, runs Rush install/build **for only `@web-bench/eval` and `@web-bench/expressjs`**, installs the Playwright Chromium browser for the project's pinned version, and exports all **20 original** expressjs tasks into a single-project task list. The paid runner uses only the first six by default (one to eight supported). Original source descriptions, task order, experiment controller and evaluator stay unchanged. The export is a data-only projection of Microsoft's `workloads/webbench.json` + Web-Bench's `projects/expressjs/tasks.jsonl`; no tasks are invented or rewritten.

The default paths live in Git-ignored demo state, so **no `TE_REFERENCE_PROJECTS` or `TE_REFERENCE_TASKS` exports are needed**:

- Projects: `.state/tokeneconomizer-demo/reference-web-bench/projects`
- Export: `.state/tokeneconomizer-demo/reference-webbench-tasks.json`

If you already have a built Web-Bench checkout, set `TE_REFERENCE_PROJECTS` and `TE_REFERENCE_TASKS` to reuse it. `prepare` will not overwrite a checkout that is not a Git clone and skips rebuilding when the official evaluator is already built.

Ubuntu prerequisites: Python 3.10+, Git, Node.js/npm/npx, pinned Copilot CLI 1.0.84-7 and Talon v1.15.3. Preparing dependencies executes the normal external Rush installation/build scripts; review external packages as you would for any downloaded open-source project. On a 2-vCPU, 8-GB server, dependency installation and compilation may be resource-intensive. It does not charge the Anthropic provider.

## Diagnose a saved reference run BEFORE paying for another one

The first local experiment returned six row files for each arm, but the
upstream comparison script printed `resolved=0/0` and crashed on division
by a zero baseline median. **Do not treat all six rows as six attempted
tasks.** When a Web-Bench task fails both tries, the original evaluator
stops the sequential project and the harness writes `unreached=True`
placeholder rows for all remaining tasks with zero cost. These placeholders
bias token averages and make the upstream `compare_arms.py` median zero.

Run the demo's **read-only, zero-cost** diagnostic on the previously saved
experiment (it does not rerun the agent or require a key):

```bash
git pull --ff-only
TE_REFERENCE_RUN_DIR=".state/tokeneconomizer-demo/reference-20261023T191741Z-01db0489" \
  make tokeneconomizer-reference-diagnose
```

Or use `make tokeneconomizer-reference-diagnose` for the newest saved
reference-proof.json. The report prints **per-arm actual attempted tasks,
actual pass/fail per attempt, unreached placeholders, model turns, usage
source, and exact evaluator/agent log paths** for failing tasks. It does
not dump raw prompts, API keys, or logs. Inspect the failing task's
`evaluator.log`, `row.json`, `run_config.json` and agent transcript
before sharing logs publicly; these may contain workspace code/prompts.

The first failure is now **explained** by the evaluator log:
Chromium could not load `libatk-1.0.so.0`. The experimental
`webbench_answered_files` field was also `[[], []]` on task 1; after fixing
Chromium, check whether the agent produces and submits changed files, rather
than attributing that observation to the browser error. The partial-stream
Playwright 2-second timeout limitation remains and should not be conflated
with the missing-library failure.

### Next experiment: preserve the paper's evaluation unit

**Do not just increase seed count on the six-task pilot.** The paper's
Web-Bench experiment uses **full 20-task project streams**. A partial
stream switches the evaluator from 30-second to 2-second Playwright
timeouts and cannot reproduce the paper's grading. Additionally, later
tasks only run when earlier tasks pass; even a 20-task limit can end
after the first task if it fails both attempts.

1. Investigate the saved failed task and validate baseline grader health
   independently, without modifying the original Microsoft grader or
   optimizer.
2. Once healthy, explicitly fund a **full 20-task, one-seed, paired
   baseline/trimech-web pilot** on a predeclared project, with native
   production-mode evaluator settings; no claims from a one-seed result.
3. Only if that completes successfully, run **three predeclared seeds**
   across several original projects, with a cost budget approved before
   adding more traffic. Preserve the original model, Copilot CLI version,
   retry count, project order and signed Talon per-arm isolation.
4. Publish **both** Web-Bench's pass@1 and pass@2, attempted/reached task
   counts, paired cache-aware effective token costs, actual Talon-estimated
   provider spend (including optimization calls), and mechanism activation.

The current runner intentionally caps pilot tasks at eight and budgets at
$5 estimated admission per arm. **Full-20 support and its cost ceiling
must be deliberately designed and approved before a paid scale-up.**

We should tell a Talon governance and evidence story: Talon attributes
all agent and optimizer model calls, enforces independent budgets and
emits verifiable signed records. Whether the optimizer saves tokens on
this workload remains a separate, falsifiable empirical question.

## Deliberately paid experiment

Only after the keyless preparation and contract pass:

```bash
export ANTHROPIC_API_KEY='...'
TE_REFERENCE_PAID_CONFIRM=YES make tokeneconomizer-reference-run
```

The real Anthropic key is sent to Talon's encrypted vault through stdin, not to the Copilot CLI. Copilot CLI uses two isolated BYOK identities to talk to Talon, which enforces independent **$5 estimated admission caps** for baseline and experimental arms. No provider calls happen unless the `TE_REFERENCE_PAID_CONFIRM=YES` environment variable is explicitly present.

**These are admission-estimate budgets, not hard provider invoice ceilings.** Set an account-side Anthropic usage limit if you need a hard spending control. The reference harness may make billed preflight calls, which count in Talon's signed cost ledger and the $5 admission budgets.

## What this measures

| Dimension | Choice |
|---|---|
| Microsoft revision | `0ce0e067b42b1dd5a5f5984275d07f8c7686c44a` |
| Workload | Original Web-Bench expressjs tasks 1–6; sequential |
| Arms | Original `baseline` vs experimental `trimech-web` |
| Agent/model | Copilot CLI BYOK, `claude-sonnet-5`, high effort |
| Network path | Copilot BYOK → Talon v1.15.3 → Anthropic |
| Budgets | $5 admission per arm, signed record export of ALL agent sessions |
| Scope | One seed; observational only |

The original Claude Code experiment runner hardcodes Anthropic routing and ignores `ANTHROPIC_BASE_URL`, so this experiment deliberately uses Copilot's BYOK transport rather than bypassing Talon.

**Important limitation:** When the original Web-Bench evaluator is asked to grade fewer than its full 20-task project, it switches to development mode with Playwright timeouts of 2 seconds instead of 30 seconds. We preserve the upstream evaluator behavior and disclose this limitation. Correctness numbers cannot be compared directly with the full published benchmark.

The benchmark writes results to a new, ignored `.state/tokeneconomizer-demo/reference-<timestamp>-<nonce>/` directory:

- `reference-proof.json`: summary, task identities, verified evidence, result status
- `official-results/`: original Microsoft graded rows/transcripts
- `baseline/signed.json` and `after/signed.json`: Talon signed evidence for every agent session
- `baseline/harness.log`, `after/harness.log`: upstream logs

The result is `INCONCLUSIVE` if task grading or signed evidence is incomplete, if the stream contains unattempted/unreached tasks or no successful tasks, or if model/pricing facts cannot be verified. Even a completed one-seed run is only `ONE_SEED_OBSERVATIONAL_ONLY`. We must inspect the original intervention telemetry before making an optimizer-effect claim.

**Boundaries:** this is the research **experimental controller**, not the installable TokenEconomizer plugin; do not pool results with the existing synthetic 24-ticket pilot. The demo makes no Talon OSS changes and does not govern local file or shell operations. The original controller and evaluator are unmodified.

See Microsoft's [official experimental setup](https://github.com/microsoft/TokenEconomizer/blob/main/experiments/README.md) for more details.
