#!/usr/bin/env python3
"""Small ORIGINAL Web-Bench experiment through Talon, not the installable TE plugin.

The Microsoft experiments/trimech-web controller and official Web-Bench grader
are used UNMODIFIED. GitHub Copilot CLI BYOK sends Anthropic wire requests to
Talon; a separate authenticated agent with an explicitly approved budget protects each arm.

No provider calls without an explicit TE_REFERENCE_PAID_CONFIRM=YES.
"""
import importlib.util
import json
import os
import signal
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "tokeneconomizer_demo_reference_helpers", ROOT / "scripts" / "tokeneconomizer-demo.py")
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)

MODEL = "claude-sonnet-5"
FULL_PROJECT_TASKS = 20
MAX_ARM_BUDGET_USD = 25.0
DEFAULT_ARM_TIMEOUT_S = 14400   # full 20-task stream
# Reviewed original Web-Bench source revision, not a moving main branch.
WEBBENCH_SHA = "7b31ca2b786eef120dd49ce63dd03d0c0006046d"
COPILOT_REFERENCE_VERSION = "1.0.84-7"
ARMS = (("baseline", "baseline"), ("after", "trimech-web"))
# The Web-Bench checkout is kept under the demo's already git-ignored state.
# No dependency is downloaded by 'plan' or the offline validator.
DEFAULT_WEBBENCH = demo.STATE / "reference-web-bench"
DEFAULT_EXPORT = demo.STATE / "reference-webbench-tasks.json"


def reference_paths():
    projects = Path(os.getenv("TE_REFERENCE_PROJECTS", str(DEFAULT_WEBBENCH / "projects"))).expanduser()
    tasks = Path(os.getenv("TE_REFERENCE_TASKS", str(DEFAULT_EXPORT))).expanduser()
    return projects, tasks


def export_expressjs_tasks(projects, tasks, experiments):
    """Original task texts and exact original upstream order; one project only.

    The upstream exporter requires tasks.jsonl for ALL benchmark projects.
    Instead restrict its data-only projection to the expressjs project while
    leaving the controller, original task IDs and official grader unchanged.
    """
    manifest = json.loads((experiments / "workloads" / "webbench.json").read_text())
    canonical_ids = manifest["groups"]["expressjs"]
    task_source = projects / "expressjs" / "tasks.jsonl"
    if not task_source.is_file():
        raise RuntimeError("Original Web-Bench task definitions missing: " + str(task_source))
    originals = {}
    for line in task_source.read_text().splitlines():
        if line.strip():
            item = json.loads(line)
            if item["id"] in originals:
                raise RuntimeError("Duplicate original Web-Bench task ID: " + item["id"])
            originals[item["id"]] = item
    missing = [identity for identity in canonical_ids if identity not in originals]
    if missing or len(canonical_ids) != 20:
        raise RuntimeError("expressjs source differs from official Microsoft workload: " + str(missing))
    rows = [{"instance_id": identity, "problem_statement": originals[identity].get("description", ""),
             "repo": "expressjs"} for identity in canonical_ids]
    if any(not row["problem_statement"].strip() for row in rows):
        raise RuntimeError("Official Web-Bench task description is missing")
    tasks.parent.mkdir(parents=True, exist_ok=True)
    tasks.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    return rows


def prepare():
    """Explicit, keyless dependency setup; builds only expressjs and evaluator."""
    projects, tasks = reference_paths()
    checkout = projects.parent
    if projects.is_symlink() or checkout.is_symlink() or tasks.is_symlink():
        raise RuntimeError("Web-Bench checkout and export must not use symlinks")
    if not shutil.which("node"):
        raise RuntimeError(
            "Node.js 22+ is required by Web-Bench but 'node' is missing from PATH. "
            "On Ubuntu: install nvm, run 'nvm install 22', then 'nvm use 22'. "
            "See docs/TOKENECONOMIZER_REFERENCE.md (Ubuntu host prerequisites).")
    raw_version = subprocess.run(
        ["node", "--version"], capture_output=True, text=True,
        env=demo.safe_env(), check=True, timeout=15).stdout.strip()
    try:
        node_major = int(raw_version.lstrip("v").split(".")[0])
    except (ValueError, IndexError):
        raise RuntimeError("Cannot identify Node.js version: " + repr(raw_version))
    if node_major < 22:
        raise RuntimeError(
            f"Web-Bench requires Node.js 22+; detected {raw_version}. "
            "Run 'nvm install 22 && nvm use 22' before preparation.")
    for executable in ("git", "npm", "npx", "python3"):
        if not shutil.which(executable):
            raise RuntimeError("Missing " + executable + ". Install prerequisites and retry. "
                               "See docs/TOKENECONOMIZER_REFERENCE.md.")
    plugin, commit = demo.install_plugin()
    experiments = plugin.parent / "experiments"
    build_env = demo.safe_env()  # never expose Anthropic/OpenAI keys to third-party build scripts
    print("Pinned Microsoft experiment code:", commit, flush=True)
    if not (checkout / ".git").is_dir():
        if checkout.exists():
            raise RuntimeError("Path exists but is not a Web-Bench checkout: " + str(checkout))
        checkout.parent.mkdir(parents=True, exist_ok=True)
        print("Cloning original Web-Bench into", checkout, flush=True)
        subprocess.run(["git", "clone", "https://github.com/bytedance/web-bench.git",
                        str(checkout)], env=build_env, check=True)
    head = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                          capture_output=True, text=True, env=build_env, check=True).stdout.strip()
    if head != WEBBENCH_SHA:
        dirty = subprocess.run(["git", "-C", str(checkout), "status", "--porcelain"],
                               capture_output=True, text=True, env=build_env, check=True).stdout
        if dirty.strip():
            raise RuntimeError("Original Web-Bench checkout has local edits; refusing checkout " +
                               str(checkout))
        subprocess.run(["git", "-C", str(checkout), "fetch", "--depth", "1",
                        "origin", WEBBENCH_SHA], env=build_env, check=True)
        subprocess.run(["git", "-C", str(checkout), "checkout", "--detach", WEBBENCH_SHA],
                       env=build_env, check=True)
    print("Preparing only original expressjs project and official evaluator", flush=True)
    # A built evaluator can be reused. Always regenerate the task export from
    # original tasks.jsonl + Microsoft's committed workload identity manifest.
    evaluator = checkout / "apps" / "eval" / "dist" / "index.js"
    if not evaluator.is_file():
        # 'rush install' uses the project's rush.json and pnpm lockfile.
        # npx avoids assuming global npm install permissions on the host.
        for args in (["npx", "--yes", "@microsoft/rush", "install"],
                     ["npx", "--yes", "@microsoft/rush", "build",
                      "--to", "@web-bench/eval", "--to", "@web-bench/expressjs"]):
            print(">", " ".join(args), flush=True)
            subprocess.run(args, cwd=checkout, env=build_env, check=True)
    # Idempotent: a pre-existing evaluator build does not imply that this
    # machine has the project's pinned browser binary installed.
    args = ["npx", "playwright", "install", "chromium", "chromium-headless-shell"]
    print(">", " ".join(args), flush=True)
    subprocess.run(args, cwd=projects / "expressjs", env=build_env, check=True)
    rows = export_expressjs_tasks(projects, tasks, experiments)
    playwright_preflight(projects)
    revision = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                              capture_output=True, text=True, env=build_env, check=True).stdout.strip()
    print("Original Web-Bench source:", revision)
    print("Original", len(rows), "expressjs tasks exported:", tasks)
    print("Evaluator:", evaluator)
    print("No model calls were made. Next: make tokeneconomizer-reference-check", flush=True)


def playwright_preflight(projects):
    """Run a LOCAL Playwright Chromium launch/close smoke test with zero API traffic.

    Merely downloading the Chromium executable is not enough on minimal Ubuntu
    servers: the browser can still exit 127 when libatk and other Linux
    system libraries are absent. Check this before any billable model call.
    """
    target = projects / "expressjs"
    if not target.is_dir():
        raise RuntimeError("Web-Bench expressjs project not found: " + str(target))
    smoke = (
        "const {chromium}=require('@playwright/test');"
        "(async()=>{const b=await chromium.launch({headless:true});"
        "console.log('Chromium ' + b.version());await b.close();})()"
        ".catch(e=>{console.error(e.message);process.exit(1);});"
    )
    proc = demo.execute(["node", "-e", smoke], cwd=target, env=demo.safe_env(),
                        check=False, timeout=90)
    if proc.returncode:
        error = (proc.stderr or proc.stdout or "").strip()[-1500:]
        raise RuntimeError(
            "LOCAL Playwright Chromium launch failed (no model calls made). "
            "The Oct 23 first paid experiment failed because Chromium could not "
            "load libatk-1.0.so.0. On Ubuntu, run:\n"
            "  cd " + str(target) + "\n"
            "  npx playwright install-deps chromium\n"
            "Then retry 'make tokeneconomizer-reference-check' BEFORE any paid run. "
            "Playwright diagnostic: " + error)
    print("PASS: local Playwright browser launch:", proc.stdout.strip(), flush=True)


def copilot_preflight():
    """Fail early and keylessly when the original agent executable is missing."""
    binary = shutil.which("copilot")
    if not binary:
        local = Path.home() / ".local" / "bin" / "copilot"
        message = ("GitHub Copilot CLI is missing from PATH; install the original "
                   f"version {COPILOT_REFERENCE_VERSION} with:\n"
                   "  curl -fsSL https://gh.io/copilot-install | "
                   f"VERSION={COPILOT_REFERENCE_VERSION} PREFIX=\"$HOME/.local\" bash\n"
                   "  export PATH=\"$HOME/.local/bin:$PATH\"\n"
                   "Then run 'copilot --version' and 'make tokeneconomizer-reference-check'. "
                   "See docs/TOKENECONOMIZER_REFERENCE.md.")
        if local.is_file():
            message = ("Copilot exists at " + str(local) +
                       " but is not on PATH. Run 'export PATH=\"$HOME/.local/bin:$PATH\"' "
                       "and retry 'make tokeneconomizer-reference-check'.")
        raise RuntimeError(message)
    # A local CLI --version lookup does not require Copilot authentication or
    # Anthropic credentials. Use a scrubbed env to avoid leaking real keys.
    info = subprocess.run([binary, "--version"], capture_output=True, text=True,
                          env=demo.safe_env(), timeout=30, check=False)
    if info.returncode:
        raise RuntimeError("Copilot CLI could not start locally (exit " +
                           str(info.returncode) + "). Verify " + str(binary))
    version = (info.stdout or info.stderr).strip().splitlines()
    if not version:
        raise RuntimeError("Copilot CLI did not report its version")
    return {"binary": binary, "version": version[0]}


def check():
    projects, tasks, selected = inputs()
    # Keep all prerequisites in the FREE gate, so a paid run is not used
    # for discovering missing host executables.
    for name in ("git", "node", "bash"):
        if not shutil.which(name):
            raise RuntimeError("Missing " + name + "; no model calls made")
    cli = copilot_preflight()
    playwright_preflight(projects)
    initial_state_preflight(projects, selected)
    _, commit = demo.install_plugin()
    print("PASS: original Web-Bench evaluator, source task order and", len(selected),
          "selected tasks verified; Microsoft harness pinned to", commit)
    print("Copilot CLI:", cli["binary"], "|", cli["version"])
    if COPILOT_REFERENCE_VERSION not in cli["version"]:
        print("WARNING: upstream paper used Copilot CLI", COPILOT_REFERENCE_VERSION,
              "but found", cli["version"], "- comparability may differ")
    print("Projects:", projects)
    print("Export:", tasks)
    print("No model calls were made.")



def task_limit():
    """Full project only: startTask on ANY partial run seeds the gold src/."""
    value = int(os.getenv("TE_REFERENCE_TASK_LIMIT", str(FULL_PROJECT_TASKS)))
    if value != FULL_PROJECT_TASKS:
        raise RuntimeError(
            "INVALID BENCHMARK: Web-Bench partial streams set startTask and "
            "initialize from the completed reference src/ instead of src-init/. "
            "This contaminates the benchmark and changes test timeouts. "
            "Only the complete original 20-task project is supported; "
            "unset TE_REFERENCE_TASK_LIMIT or set it to 20. No paid calls made.")
    return value


def reference_budget():
    """Explicit, capped Talon estimate-admission budget for both arms."""
    from math import isfinite
    raw = os.getenv("TE_REFERENCE_ARM_BUDGET_USD", "5.00")
    try:
        usd = float(raw)
    except ValueError:
        raise RuntimeError("Invalid TE_REFERENCE_ARM_BUDGET_USD: " + repr(raw))
    if not isfinite(usd) or not 0 < usd <= MAX_ARM_BUDGET_USD:
        raise RuntimeError("TE_REFERENCE_ARM_BUDGET_USD must be > 0 and <= USD 25/arm")
    if usd > 5.0 and os.getenv("TE_REFERENCE_HIGHER_BUDGET_CONFIRM") != "YES":
        raise RuntimeError(
            "Higher budget requires TE_REFERENCE_HIGHER_BUDGET_CONFIRM=YES "
            "as well as the existing paid confirmation. No paid calls made.")
    return round(usd, 2)


def arm_timeout_seconds():
    """Bounded per-arm wall-clock limit; not a provider spending cap."""
    raw = os.getenv("TE_REFERENCE_ARM_TIMEOUT_S", str(DEFAULT_ARM_TIMEOUT_S))
    try:
        seconds = int(raw)
    except ValueError:
        raise RuntimeError("Invalid TE_REFERENCE_ARM_TIMEOUT_S: " + repr(raw))
    if not 3600 <= seconds <= DEFAULT_ARM_TIMEOUT_S:
        raise RuntimeError("TE_REFERENCE_ARM_TIMEOUT_S must be 3600..14400 seconds")
    return seconds


def execute_official_arm(env, experiments, log_path):
    """Live log + group-aware timeout (never orphan billable agent children)."""
    demo.private(log_path, "")
    limit = arm_timeout_seconds()
    print("Original harness live log:", log_path, "| timeout", limit, "s", flush=True)
    with log_path.open("w") as logfile:
        proc = subprocess.Popen(
            ["bash", "scripts/launch/main_sweep.sh"],
            cwd=experiments, env=env, stdout=logfile,
            stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return proc.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=15)
            raise RuntimeError(
                f"Full-project benchmark exceeded {limit}s per-arm deadline. "
                f"Terminated process group to stop further spending; log: {log_path}")


def initial_state_preflight(projects, task_ids):
    """Keyless guard for the original Web-Bench source/calibration trap."""
    if task_ids != [f"task-{i}" for i in range(1, FULL_PROJECT_TASKS + 1)]:
        raise RuntimeError("Initial-state safeguard requires all 20 original tasks in order")
    project = projects / "expressjs"
    init = project / "src-init" / "index.js"
    gold = project / "src" / "index.js"
    settings = projects.parent / "tools" / "evaluator" / "src" / "settings" / "bench.ts"
    if not all(f.is_file() for f in (init, gold, settings)):
        raise RuntimeError("Official Web-Bench src-init, reference src and settings are missing")
    source = settings.read_text()
    if not all(x in source for x in (
        "if (startTask)", "outputProjectDir.push(srcDir)",
        "outputProjectDir.push(initDir)",
        "fullTasks.length !== tasks.length")):
        raise RuntimeError(
            "Web-Bench starting-state logic changed; audit official source before paying.")
    # Unlike the completed reference, the starting scaffold must not already
    # contain the first task's implementation. Do not mutate either folder.
    if (project / "src-init" / "routes" / "home" / "api.js").exists():
        raise RuntimeError("Web-Bench src-init contains completed home routes")
    if init.read_bytes() == gold.read_bytes():
        raise RuntimeError("Web-Bench initial and reference entrypoints are identical")
    print("PASS: 20-task production stream starts from src-init (not solved src/)", flush=True)


def inputs():
    """Full path validation before creating credentials or starting Talon."""
    projects, tasks = reference_paths()
    if not projects.is_dir():
        raise RuntimeError("Web-Bench projects are missing: " + str(projects) +
                           ". Run make tokeneconomizer-reference-prepare (no API calls).")
    if not tasks.is_file():
        raise RuntimeError("Original Web-Bench task export is missing: " + str(tasks) +
                           ". Run make tokeneconomizer-reference-prepare (no API calls).")
    if not (projects / "expressjs").is_dir():
        raise RuntimeError("Web-Bench expressjs project missing from TE_REFERENCE_PROJECTS")
    # Do not accept a different moving Web-Bench revision as the same benchmark.
    if (projects.parent / ".git").is_dir():
        actual = subprocess.run(["git", "-C", str(projects.parent), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
        if actual != WEBBENCH_SHA:
            raise RuntimeError("Original Web-Bench revision mismatch: " + actual +
                               ". Run make tokeneconomizer-reference-prepare.")
    evaluator = projects.parent / "apps" / "eval" / "dist" / "index.js"
    if not evaluator.is_file():
        raise RuntimeError("Official Web-Bench evaluator is not built: " + str(evaluator))
    if projects.is_symlink() or tasks.is_symlink() or projects.parent.is_symlink():
        raise RuntimeError("Use canonical, non-symlinked Web-Bench paths (upstream requirement)")
    data = json.loads(tasks.read_text())
    if not isinstance(data, list):
        raise RuntimeError("Official exported Web-Bench task file must be a JSON list")
    matching = [t for t in data if t.get("repo", "").split("/")[-1] == "expressjs"]
    ids = [t.get("instance_id") for t in matching]
    expected = [f"task-{i}" for i in range(1, task_limit() + 1)]
    if ids[:len(expected)] != expected:
        raise RuntimeError("Original expressjs task order is missing or altered: " + repr(ids[:8]))
    return projects.resolve(), tasks.resolve(), expected


def provider_env(values, run_id, arm, projects, tasks, results, env_file):
    """Explicit allowlist: NEVER inherit operator's actual Anthropic API key."""
    env = demo.safe_env()
    env.update(
        AGENT="copilot", MODEL=MODEL, DOMAIN="webbench",
        RUNNER="te_harness.webbench:make_runner", REPOS="expressjs",
        ARMS="baseline" if arm == "baseline" else "trimech-web",
        SEEDS="0", LIMIT=str(task_limit()), DETACH="0", SKIP_DONE="0",
        TOKENECONOMIZER_ENV_FILE=str(env_file),
        TOKENECONOMIZER_WEBBENCH_PROJECTS=str(projects),
        TOKENECONOMIZER_WEBBENCH_TASKS=str(tasks),
        TOKENECONOMIZER_RESULTS=str(results),
        COPILOT_PROVIDER_BASE_URL=f"http://127.0.0.1:{demo.PORT}/v1/proxy/anthropic",
        COPILOT_PROVIDER_TYPE="anthropic",
        COPILOT_PROVIDER_API_KEY=values["agent_" + arm],
        COPILOT_MODEL=MODEL,
        COPILOT_AUTO_UPDATE="false",
        COPILOT_OFFLINE="true",
        COPILOT_PROVIDER_HEADERS=(
            "X-Talon-Session-ID: ref-" + run_id + "-" + arm +
            "\nX-Talon-Client: tokeneconomizer-reference-copilot"),
        TE_EFFORT_LEVEL="high",
        TE_STRICT_MODEL_ID="1",
        TE_OPTIMIZER_PREFLIGHT="1",
        COPILOT_HOME=str(results / ("copilot-home-" + arm)),
    )
    # The paper's optimizer sometimes makes a direct Messages API call, which
    # uses this *same* BYOK base URL and agent key, but not Copilot's custom
    # headers. Audit all sessions by agent, never only the CLI's session ID.
    assert "ANTHROPIC_API_KEY" not in env and "ANTHROPIC_AUTH_TOKEN" not in env
    assert env["COPILOT_PROVIDER_BASE_URL"].startswith("http://127.0.0.1:")
    return env


def official_rows(results, arm):
    root = results / "copilot_webbench_sonnet5" / arm / "expressjs_s0"
    files = sorted(root.glob("20*/row.json"))
    found = {}
    for file in files:
        row = json.loads(file.read_text())
        identifier = row.get("instance") or row.get("instance_id")
        if identifier:
            found[identifier] = row
    return found


def transcript_activity(path):
    """Count ACTUAL executed tools (not streamed tool-call deltas), without payloads.

    Do not print prompts, tool arguments, responses, commands, filenames, or keys.
    A 'bash' execution can still write files; its effect cannot be determined
    from tool names alone. Transcript activity is not evaluator evidence.
    """
    from collections import Counter
    counts, executions = Counter(), Counter()
    completion_fields, explicit_failures = set(), Counter()
    tool_update_fields, tool_catalog_exposed = set(), False
    agent_messages_with_content = 0
    if not path.is_file():
        return None
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                event = json.loads(line)
            except (ValueError, TypeError):
                continue
            if not isinstance(event, dict):
                continue
            kind = event.get("type")
            counts[kind] += 1
            data = event.get("data")
            if not isinstance(data, dict):
                data = {}
            if kind == "session.tools_updated":
                tool_update_fields.update(k for k in data.keys() if isinstance(k, str))
                # An event carrying only {'model': ...} is NOT evidence the
                # CLI had zero tools. It exposes no catalog at all.
                if isinstance(data.get("tools"), list):
                    tool_catalog_exposed = True
            if kind == "assistant.message" and data.get("content"):
                agent_messages_with_content += 1
            if kind == "tool.execution_start":
                name = data.get("toolName") or data.get("tool") or data.get("name")
                if not isinstance(name, str):
                    name = "unknown"
                # Keep tool names to bounded, predictable metadata. No raw
                # data/arguments/results are copied into the displayed output.
                name = name[:60]
                executions[name] += 1
            if kind == "tool.execution_complete":
                completion_fields.update(k for k in data.keys() if isinstance(k, str))
                # Count only explicit structured failure indicators. Never
                # regex-match arbitrary result text: a successful tool can
                # quote "permission denied" or "no such file".
                if data.get("isError") is True or data.get("is_error") is True:
                    explicit_failures["is_error"] += 1
                elif data.get("success") is False:
                    explicit_failures["success_false"] += 1
                elif isinstance(data.get("exitCode"), int) and data["exitCode"] != 0:
                    explicit_failures["exit_code_nonzero"] += 1
                elif data.get("status") in ("error", "failed", "failure"):
                    explicit_failures["status_failed"] += 1
    return {"model_calls": counts["model.call_start"],
            "tool_execution_started": counts["tool.execution_start"],
            "tool_execution_completed": counts["tool.execution_complete"],
            "executed_tools": dict(sorted(executions.items())),
            "tool_update_fields": sorted(tool_update_fields),
            "tool_catalog_exposed": tool_catalog_exposed,
            "tool_completion_fields": sorted(completion_fields),
            "explicit_tool_failures": dict(sorted(explicit_failures.items())),
            "assistant_messages_with_content": agent_messages_with_content}


def diagnose(run_location=None):
    """Offline postmortem of saved *original* Web-Bench rows. Never makes model calls."""
    if run_location:
        root = Path(run_location).expanduser().resolve()
    else:
        candidates = sorted(p for p in demo.STATE.glob("reference-*")
                            if (p / "reference-proof.json").is_file())
        if not candidates:
            raise RuntimeError("No Web-Bench reference-proof.json found; provide a run path")
        root = candidates[-1]
    proof_file = root / "reference-proof.json"
    if not proof_file.is_file():
        raise RuntimeError("Missing completed reference proof: " + str(proof_file))
    proof = json.loads(proof_file.read_text())
    results = root / "official-results"
    rows = {arm: official_rows(results, name) for arm, name in ARMS}
    expected = proof.get("task_ids", [])
    if not expected or any(not rows[arm] for arm in rows):
        raise RuntimeError("Missing original graded rows in " + str(results))
    print("ORIGINAL WEB-BENCH OFFLINE DIAGNOSIS")
    print("Run:", root)
    print("Paper controller: ", proof.get("upstream_sha"))
    print("No API calls made; only local saved artifacts read.")
    print("NOTE: a stored row is NOT necessarily an attempted or resolved task.")
    print("task       arm         attempts outcomes   resolved unreached turns  usage")
    totals = {}
    for arm, name in ARMS:
        current = rows[arm]
        counts = {"rows": len(current), "attempted": 0, "resolved": 0,
                  "unreached": 0, "usage_incomplete": 0}
        for identity in expected:
            row = current.get(identity)
            if not row:
                print(f"{identity:<10} {name:<11} MISSING ROW")
                continue
            attempts = int(row.get("webbench_attempts") or 0)
            if attempts:
                counts["attempted"] += 1
            if row.get("resolved") is True:
                counts["resolved"] += 1
            if row.get("unreached"):
                counts["unreached"] += 1
            if row.get("usage_incomplete"):
                counts["usage_incomplete"] += 1
            outcomes = "".join("Y" if status else "N"
                               for status in row.get("webbench_attempt_results", [])) or "-"
            print(f"{identity:<10} {name:<11} {attempts:<8} {outcomes:<10} "
                  f"{str(row.get('resolved')):<8} {str(bool(row.get('unreached'))):<9} "
                  f"{str(row.get('num_turns', '-')):<6} "
                  f"{str(row.get('tokens_source', '-'))}")
            if attempts and row.get("resolved") is not True:
                location = Path(row.get("run_dir") or "")
                config = location / "run_config.json"
                if config.is_file():
                    cfg = json.loads(config.read_text())
                    evaluator_log = ((cfg.get("webbench") or {}).get("evaluator_log"))
                    if evaluator_log:
                        print("  Failed task evaluator log:", evaluator_log)
                print("  Failed task row:", location / "row.json")
                transcript = location / "transcript.jsonl"
                print("  Failed task agent transcript:", transcript)
                activity = transcript_activity(transcript)
                if activity is not None:
                    print("  Agent execution summary (no prompts/commands):", activity)
                submissions = row.get("webbench_answered_files")
                if isinstance(submissions, list):
                    print("  Submitted changed-file counts per attempt:",
                          [len(items) if isinstance(items, list) else "unknown"
                           for items in submissions])
                    if submissions and all(isinstance(x, list) and not x for x in submissions):
                        print("  NOTE: no eligible file changes were submitted. 'bash' may")
                        print("  edit files; inspect local bash tool commands/results and")
                        print("  workspace paths to distinguish no edits vs collection.")
                print("  Agent-side error:", bool(row.get("is_error")),
                      "stream_broken:", bool(row.get("stream_broken")),
                      "timed_out:", bool(row.get("timed_out")))
        totals[arm] = counts
        print(f"{arm}: {counts}")
    if any(t["unreached"] for t in totals.values()):
        print("DIAGNOSIS: STREAM CENSORED. After a Web-Bench task fails both attempts,")
        print("the evaluator stops; later 'unreached' rows are not additional tasks.")
        print("DO NOT infer success rate or benchmark savings from this truncated stream.")
    elif any(t["resolved"] == 0 for t in totals.values()):
        print("DIAGNOSIS: NO SUCCESSFUL TASKS in at least one arm.")
        print("Investigate official grader and agent logs before spending more.")
    else:
        print("Both arms resolved at least one task; inspect per-task differences and mechanisms.")
    print("Raw run files and evaluator logs may contain prompts and code; review before sharing.")


def audit_agent(values, run_id, arm, out):
    """Verify ALL signed records, including direct controller side calls."""
    out.mkdir(parents=True, exist_ok=True)
    signed = out / "signed.json"
    env = demo.tenv(values, run_id)
    agent = demo.ARM_AGENTS[arm]
    demo.execute(["talon", "audit", "export", "--tenant", "demo", "--agent", agent,
                  "--format", "signed-json", "--output", str(signed)], env=env)
    check = demo.execute(["talon", "audit", "verify", "--file", str(signed)], env=env).stdout
    for marker in ("Invalid records: 0", "Missing signature: 0",
                   "Could not parse: 0", "Unsupported: 0"):
        if marker not in check:
            raise RuntimeError("Signed Talon evidence verification failed for " + arm)
    records = json.loads(signed.read_text()).get("records") or []
    if not records:
        raise RuntimeError("No signed Talon records for " + arm + " (possible bypass)")
    if any(r.get("agent_id") != agent or r.get("tenant_id") != "demo" for r in records):
        raise RuntimeError("Talon receipt includes a different agent or tenant")
    sent = [r for r in records if r.get("invocation_type") == "gateway"
            and r.get("policy_decision", {}).get("allowed")
            and r.get("execution", {}).get("model_used")]
    if not sent:
        raise RuntimeError("No authenticated model calls through Talon")
    for r in sent:
        e = r["execution"]
        if e.get("model_used") != MODEL or e.get("currency") != "USD" or \
                e.get("pricing_basis") != "table" or e.get("error"):
            raise RuntimeError("Unverifiable price/model/provider error in Talon receipts")
    denials = [r for r in records if not r.get("policy_decision", {}).get("allowed", True)]
    return {"signed_records": len(records), "provider_calls": len(sent),
            "talon_estimated_usd": round(sum(float(r["execution"].get("cost") or 0)
                                              for r in sent), 8),
            "denials": len(denials),
            "sessions": sorted({r.get("session_id") for r in records if r.get("session_id")}),
            "signed_receipt": str(signed.relative_to(out.parent))}


def plan():
    print("TokenEconomizer ORIGINAL Web-Bench full-project pilot (NOT production plugin)")
    print("Source: microsoft/TokenEconomizer @", demo.TOKENECONOMIZER_COMMIT)
    print("Official evaluator: expressjs | ALL", task_limit(), "tasks | production grader | seed 0")
    print("Arms: baseline vs trimech-web | Copilot CLI BYOK -> Talon -> Anthropic")
    print("Each arm: independent USD 5.00 default estimated admission budget;")
    print("Per-arm runtime max:", arm_timeout_seconds(), "s (not a provider spending cap)")
    print("explicitly opt into a higher amount (max USD 25/arm), if needed.")
    print("Partial benchmark forbidden: Web-Bench treats startTask as GOLD src/ calibration.")
    print("Only 1 seed: no statistical, causal or paper-replication claim.")
    print("No API calls performed. One-command benchmark setup:")
    print("  make tokeneconomizer-reference-prepare   # source/dependency downloads; NO paid calls")
    print("  make tokeneconomizer-reference-check     # original evaluator/task order; NO paid calls")
    print("Then export ANTHROPIC_API_KEY (used only in Talon's vault) and run:")
    print("  TE_REFERENCE_PAID_CONFIRM=YES TE_REFERENCE_FULL_STREAM_CONFIRM=YES")
    print("    make tokeneconomizer-reference-run")
    print("Optional budget only if explicitly approved: TE_REFERENCE_ARM_BUDGET_USD=<amount>")
    print("  and TE_REFERENCE_HIGHER_BUDGET_CONFIRM=YES when amount exceeds 5.")
    print("Default paths:", reference_paths())
    print("Host prerequisite: Copilot CLI", COPILOT_REFERENCE_VERSION,
          "and Node.js 22+. See docs/TOKENECONOMIZER_REFERENCE.md")
    print("Billing may exceed Talon's estimate-based admission limits: set a provider-side limit.")


def run():
    if os.getenv("TE_REFERENCE_PAID_CONFIRM") != "YES":
        raise RuntimeError("No paid execution without TE_REFERENCE_PAID_CONFIRM=YES")
    if os.getenv("TE_REFERENCE_FULL_STREAM_CONFIRM") != "YES":
        raise RuntimeError(
            "The invalid six-task experiment is retired. Full 20-task Web-Bench "
            "run requires TE_REFERENCE_FULL_STREAM_CONFIRM=YES and explicit "
            "TE_REFERENCE_PAID_CONFIRM=YES. No paid calls made.")
    budget = reference_budget()
    arm_timeout_seconds()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is required only for Talon's vault setup")
    if demo.MODEL != MODEL:
        raise RuntimeError("Reference study requires claude-sonnet-5")
    # The budget is only consumed inside this benchmark subprocess; no
    # modification to Talon OSS or to the synthetic fixture study.
    demo.ARM_BUDGET = budget
    # Reject invalid partial streams before touching filesystem, binaries,
    # gateway credentials or API traffic. This is a methodology fail-closed gate.
    task_limit()
    projects, tasks, expected = inputs()
    playwright_preflight(projects)
    initial_state_preflight(projects, expected)
    copilot = copilot_preflight()
    for name in ("talon", "git", "node", "bash"):
        if not shutil.which(name):
            raise RuntimeError("Missing " + name + "; no model calls made")
    print("Copilot CLI preflight:", copilot["binary"], "|", copilot["version"], flush=True)
    version = demo.execute(["talon", "version"], check=False)
    if version.returncode or version.stdout.strip().splitlines()[0] != "Talon " + demo.TALON_RELEASE:
        raise RuntimeError("Expected released Talon " + demo.TALON_RELEASE)
    # Download only reviewed upstream source; never copy Microsoft harness files
    # into Talon or silently patch their benchmark/grading/controller logic.
    plugin, commit = demo.install_plugin()
    experiments = plugin.parent / "experiments"
    if not (experiments / "scripts" / "launch" / "main_sweep.sh").is_file():
        raise RuntimeError("Pinned upstream experiment harness missing")
    run_id = "reference-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    root = demo.STATE / run_id
    root.mkdir(parents=True)
    env_file = root / "empty-upstream-env"
    demo.private(env_file, "# Empty on purpose: no upstream .env credential injection.\n")
    results = root / "official-results"
    values = demo.keys(run_id)
    demo.setup(values, run_id)
    server, log = demo.start_gateway(values, run_id)
    observations, errors = {}, []
    try:
        for arm, name in ARMS:
            output = root / arm
            output.mkdir(exist_ok=True)
            env = provider_env(values, run_id, arm, projects, tasks, results, env_file)
            (results / ("copilot-home-" + arm)).mkdir(parents=True, exist_ok=True)
            # The official launcher checks its own arms/instance selection for FREE.
            pre = demo.execute(["bash", "scripts/launch/main_sweep.sh"],
                               env=dict(env, DRYRUN="1"), cwd=experiments,
                               check=False, timeout=180)
            demo.private(output / "plan.log", pre.stdout + "\n" + pre.stderr)
            if pre.returncode or "cells=1" not in pre.stdout or \
                    "task-runs=" not in pre.stdout:
                raise RuntimeError("Reference arm planning failed; see " + str(output / "plan.log"))
            print("START", name, "|", len(expected), "official tasks | $",
                  f"{budget:.2f}", " Talon estimated admission policy", flush=True)
            arm_exit = execute_official_arm(env, experiments, output / "harness.log")
            observations[arm] = {"official_arm": name,
                                 "exit_code": arm_exit,
                                 "tasks": official_rows(results, name)}
            try:
                observations[arm]["talon"] = audit_agent(values, run_id, arm, output)
            except Exception as e:
                observations[arm]["audit_error"] = str(e)
                errors.append(arm + " audit: " + str(e))
            if arm_exit:
                errors.append(arm + " official harness nonzero exit")
                break
            if list(observations[arm]["tasks"]) != expected:
                errors.append(arm + " missing, reordered or extra official task results")
                break
    except Exception as exc:
        errors.append(str(exc))
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        log.close()
    arms = observations
    comparable = len(arms) == 2 and not errors and all(
        "talon" in x and len(x["tasks"]) == len(expected)
        for x in arms.values())
    # An official Web-Bench cell can contain rows for UNREACHED tasks. Once a
    # task fails both attempts, the project stream ends. Do not present a
    # successfully exported but unattempted cell as an informative comparison.
    success_per_arm = {
        arm: sum(row.get("resolved") is True for row in x["tasks"].values())
        for arm, x in arms.items()
    }
    unreachable_per_arm = {
        arm: sum(bool(row.get("unreached")) for row in x["tasks"].values())
        for arm, x in arms.items()
    }
    attempted_per_arm = {
        arm: sum(int(row.get("webbench_attempts") or 0) > 0
                 for row in x["tasks"].values())
        for arm, x in arms.items()
    }
    informative = comparable and all(
        unreachable_per_arm.get(arm, len(expected)) == 0
        and attempted_per_arm.get(arm, 0) == len(expected)
        and success_per_arm.get(arm, 0) > 0
        for arm in ("baseline", "after"))
    if comparable and not informative:
        errors.append("Official Web-Bench stream non-informative: "
                      "unreached tasks or zero resolved; use offline diagnose "
                      "before planning another paid experiment")
    report = {
        "run_id": run_id, "workload": "original Web-Bench expressjs full 20-task stream",
        "origin": "microsoft/TokenEconomizer", "upstream_sha": commit,
        "webbench_sha": WEBBENCH_SHA,
        "model": MODEL, "agent": "copilot CLI BYOK", "seed": 0,
        "task_ids": expected, "budget_admission_per_arm_usd": budget,
        "source_state": "src-init", "original_project_complete": True,
        "strict_provider_invoice_ceiling": False,
        "grading_caveat": "Original Web-Bench full project, production Playwright grader",
        "arms": {arm: {
            "official_arm": x["official_arm"], "exit_code": x["exit_code"],
            "tasks": [{"id": k, "resolved": v.get("resolved"),
                       "resolved_p1": v.get("resolved_p1"),
                       "resolved_p2": v.get("resolved_p2"),
                       "attempts": v.get("webbench_attempts"),
                       "attempt_results": v.get("webbench_attempt_results"),
                       "unreached": bool(v.get("unreached")),
                       "stream_broken": bool(v.get("stream_broken")),
                       "num_turns": v.get("num_turns"),
                       "usage_incomplete": v.get("usage_incomplete"),
                       "eff_tokens": v.get("cost_effective_tokens")}
                      for k, v in x["tasks"].items()],
            "talon": x.get("talon"), "audit_error": x.get("audit_error"),
        } for arm, x in arms.items()},
        "errors": errors,
        "attempted_tasks_per_arm": attempted_per_arm,
        "resolved_tasks_per_arm": success_per_arm,
        "unreached_tasks_per_arm": unreachable_per_arm,
        "verdict": "ONE_SEED_OBSERVATIONAL_ONLY" if informative else "INCONCLUSIVE",
        "limits": [
            "No statistical or causal inference from one short seed",
            "Experimental trimech-web controller, NOT the production plugin",
            "Partial Web-Bench uses stricter grader timeouts",
            "Talon costs are verified pricing-table estimates, not provider invoices",
            "Talon audits cover ALL agent sessions including optimizer sidecalls",
            "No optimizer activation asserted without inspecting the upstream traces",
        ]}
    demo.private(root / "reference-proof.json", json.dumps(report, indent=2))
    print("Reference result:", report["verdict"])
    print("Evidence:", root / "reference-proof.json")
    if errors:
        raise RuntimeError("; ".join(errors))
    for arm in arms:
        obs = arms[arm]
        print(f"{arm}: {len(obs['tasks'])}/{len(expected)} original tasks; "
              f"Talon estimated USD {obs['talon']['talon_estimated_usd']:.4f}; "
              f"signed calls {obs['talon']['provider_calls']}")
    print("Compare resolved_p2, cache-aware cost and original traces before making claims.")


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "plan"
    try:
        if action == "plan":
            plan()
        elif action == "prepare":
            prepare()
        elif action == "check":
            check()
        elif action == "diagnose":
            diagnose(sys.argv[2] if len(sys.argv) > 2 else os.getenv("TE_REFERENCE_RUN_DIR"))
        elif action == "run":
            run()
        else:
            raise RuntimeError("Use plan, prepare, check, diagnose, or run")
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
