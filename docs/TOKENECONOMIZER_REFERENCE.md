# Original TokenEconomizer full-project Web-Bench pilot through Talon

**State (2026-10-23):** The first six-task paid attempt is **invalid as an optimizer study**, for two independently verified reasons: the host lacked Chromium system libraries (`libatk-1.0.so.0`) and, more fundamentally, selecting only tasks 1–6 populated the evaluator workspace with the **fully developed reference code**. Both Copilot arms consequently said task 1 was already implemented. The browser has since passed its local launch test. This PR now forbids truncated runs and requires 20-task, `src-init`-based Web-Bench execution. No valid optimizer-effectiveness comparison has yet been produced.

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

The **prepare** target downloads Microsoft TokenEconomizer at the reviewed pinned revision, clones ByteDance Web-Bench at pinned commit `7b31ca2b786eef120dd49ce63dd03d0c0006046d`, runs Rush install/build **for only `@web-bench/eval` and `@web-bench/expressjs`**, installs the pinned Playwright Chromium browser, and exports all **20 original** Express.js tasks. The paid runner requires **the entire 20-task stream** and rejects any shorter `TE_REFERENCE_TASK_LIMIT`. Original source descriptions, task order, experiment controller, and evaluator stay unchanged. The export is a data-only projection of Microsoft's `workloads/webbench.json` + Web-Bench's `projects/expressjs/tasks.jsonl`; no tasks are invented or rewritten.

The default paths live in Git-ignored demo state, so **no `TE_REFERENCE_PROJECTS` or `TE_REFERENCE_TASKS` exports are needed**:

- Projects: `.state/tokeneconomizer-demo/reference-web-bench/projects`
- Export: `.state/tokeneconomizer-demo/reference-webbench-tasks.json`

If you already have a built Web-Bench checkout, set `TE_REFERENCE_PROJECTS` and `TE_REFERENCE_TASKS` to reuse it. `prepare` will not overwrite a checkout that is not a Git clone and skips rebuilding when the official evaluator is already built.

Ubuntu prerequisites: Python 3.10+, Git, Node.js/npm/npx, pinned Copilot CLI 1.0.84-7 and Talon v1.15.3. Preparing dependencies executes the normal external Rush installation/build scripts; review external packages as you would for any downloaded open-source project. On a 2-vCPU, 8-GB server, dependency installation and compilation may be resource-intensive. It does not charge the Anthropic provider.

## Forensic result: why the six-task run was invalid

This failure was **not a Talon policy denial or evidence that TokenEconomizer worsens coding**. Two unrelated defects invalidated the first operator run.

**1. Missing browser libraries (repaired):** The saved official evaluator log showed Playwright's Chromium exiting 127 because Ubuntu lacked `libatk-1.0.so.0`. Only task 1 was attempted (twice) in each arm; five later rows per arm were `unreached` placeholders. A keyless Chromium launch-and-close smoke test is now mandatory in `prepare`, `check`, and before paid execution.

**2. Gold/reference source contamination (methodology defect):** The original pinned ByteDance source `tools/evaluator/src/settings/bench.ts` explicitly contains:

```ts
if (startTask) {
  outputProjectDir.push(srcDir)
} else {
  outputProjectDir.push(initDir)
}
```

In this evaluator, `startTask` means **resume/calibration from the already developed `projects/expressjs/src/`**, not *start a new project at task 1*. The Microsoft harness set `startTask` when our caller passed a six-task subset. Consequently both agents were handed already-solved home/login routes and correctly said no file changes were needed. The reference `src/` contains the final Pug views/routes, while `src-init/` contains only the initial scaffold. The captured experimental agent trace confirms 22 `view` and three read-only Bash operations and zero changed-file submissions per attempt. The baseline likewise submitted no changed files.

**Full original 20-task stream:** When all 20 original tasks are selected in order, the Microsoft harness does not set `startTask`/`endTask`. Web-Bench starts from `src-init/` and uses the **production Playwright timeout of 30 seconds**, rather than the partial-run development timeout of 2 seconds. The new `initial_state_preflight` checks this upstream source behavior and confirms the initial and completed trees are distinct before authorization is used.

The old signed Talon receipts remain legitimate **governance/evidence artifacts**: all model/optimizer calls were attributed by isolated agent identity, but **cost and task-success deltas are unusable for optimizer-effectiveness claims**.

To examine the historical run locally with no API calls:

```bash
TE_REFERENCE_RUN_DIR=".state/tokeneconomizer-demo/reference-20261023T191741Z-01db0489" \
  make tokeneconomizer-reference-diagnose
```

The command reads saved official rows and tool-execution metadata, counts attempted versus unreached tasks, and prints original evaluator-log paths. It does not print prompts, tool arguments or model messages.

### How to advance the evidence

1. Run `make tokeneconomizer-reference-prepare`, `make tokeneconomizer-reference-check`, and `make tokeneconomizer-reference-plan` **without provider spend**. The check must print both `PASS: local Playwright browser launch` and `PASS: 20-task production stream starts from src-init`.
2. Review and explicitly approve the expected costs of **one full 20-task Express.js stream**, with one seed in each arm. The two-arm Talon estimate-admission default remains **$5 per arm**, which may interrupt a 20-task study; any increase is an explicit, separately confirmed opt-in.
3. Evaluate the official per-task `resolved_p1` and `resolved_p2`, including genuinely reached tasks, total provider spend and cache-aware effective tokens, and actually active TokenEconomizer mechanisms. End early or declare the run inconclusive if the original evaluator stops or the Talon budget denies model calls.
4. Only if this stream yields meaningful outcomes, predeclare multiple original projects and at least three seeds; do not make a causal or replication claim from one seed.

**Do not change or patch the original ByteDance grader, Microsoft controller, or gold/reference source to improve results.** This wrapper changes only benchmark selection, preflight checks, Talon routing, and evidence packaging.

## Deliberately paid experiment

Only after the keyless preflight passes **and the full-stream costs have been approved**:

```bash
# No API calls:
make tokeneconomizer-reference-check
make tokeneconomizer-reference-plan
make tokeneconomizer-contract

# Explicitly paid, a *full* 20-task project per arm:
export ANTHROPIC_API_KEY='...'
TE_REFERENCE_PAID_CONFIRM=YES TE_REFERENCE_FULL_STREAM_CONFIRM=YES \
  make tokeneconomizer-reference-run
```

If you explicitly approve a larger estimated admission budget for this stream, set
`TE_REFERENCE_ARM_BUDGET_USD` (maximum 25 per arm) together with
`TE_REFERENCE_HIGHER_BUDGET_CONFIRM=YES`. For example, `TE_REFERENCE_ARM_BUDGET_USD=10`
would authorize **up to $10 estimated admission per arm, $20 combined**; this is not a
hard provider invoice ceiling. These flags are **not required for the default $5 per arm**.
Changing the budget does not modify Talon OSS or the original research controller.

The real Anthropic key is sent to Talon's encrypted vault through stdin, not to Copilot CLI. Copilot uses two isolated BYOK identities to talk to Talon, which enforces the individually approved **estimated admission caps** per arm (default **$5**). Model calls require BOTH `TE_REFERENCE_PAID_CONFIRM=YES` and `TE_REFERENCE_FULL_STREAM_CONFIRM=YES`; higher budgets require an additional explicit confirmation.

**These are admission-estimate budgets, not hard provider invoice ceilings.** Set an account-side Anthropic usage limit if you need a hard spending control. The reference harness may make billed preflight calls, which count in Talon's signed cost ledger and the $5 admission budgets.

## What this measures

| Dimension | Choice |
|---|---|
| Microsoft revision | `0ce0e067b42b1dd5a5f5984275d07f8c7686c44a` |
| Workload | **All original 20 Web-Bench Express.js tasks, sequential** |
| Arms | Original `baseline` vs experimental `trimech-web` |
| Agent/model | Copilot CLI BYOK, `claude-sonnet-5`, high effort |
| Network path | Copilot BYOK → Talon v1.15.3 → Anthropic |
| Budgets | $5 estimated admission per arm by default; optional explicitly approved increase ≤$25/arm |
| Scope | One seed; observational only |

The original Claude Code experiment runner hardcodes Anthropic routing and ignores `ANTHROPIC_BASE_URL`, so this experiment deliberately uses Copilot's BYOK transport rather than bypassing Talon.

**Integrity invariant:** This runner will not use fewer than 20 tasks: restricted streams set Web-Bench's `startTask`, unexpectedly loading pre-solved reference `src/` and tightening Playwright timeout from 30s to 2s. The full-project grader preserves the original 30s production behavior. One seed is observational only and not equivalent to the published multi-project, multi-seed benchmark.

The benchmark writes results to a new, ignored `.state/tokeneconomizer-demo/reference-<timestamp>-<nonce>/` directory:

- `reference-proof.json`: summary, task identities, verified evidence, result status
- `official-results/`: original Microsoft graded rows/transcripts
- `baseline/signed.json` and `after/signed.json`: Talon signed evidence for every agent session
- `baseline/harness.log`, `after/harness.log`: upstream logs

The result is `INCONCLUSIVE` if task grading or signed evidence is incomplete, if the stream contains unattempted/unreached tasks or no successful tasks, or if model/pricing facts cannot be verified. Even a completed one-seed run is only `ONE_SEED_OBSERVATIONAL_ONLY`. We must inspect the original intervention telemetry before making an optimizer-effect claim.

**Boundaries:** this is the research **experimental controller**, not the installable TokenEconomizer plugin; do not pool results with the existing synthetic 24-ticket pilot. The demo makes no Talon OSS changes and does not govern local file or shell operations. The original controller and evaluator are unmodified.

See Microsoft's [official experimental setup](https://github.com/microsoft/TokenEconomizer/blob/main/experiments/README.md) for more details.
