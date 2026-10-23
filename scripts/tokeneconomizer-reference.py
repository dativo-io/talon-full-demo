#!/usr/bin/env python3
"""Small ORIGINAL Web-Bench experiment through Talon, not the installable TE plugin.

The Microsoft experiments/trimech-web controller and official Web-Bench grader
are used UNMODIFIED. GitHub Copilot CLI BYOK sends Anthropic wire requests to
Talon; a separate authenticated agent and $5 admission limit protects each arm.

No provider calls without an explicit TE_REFERENCE_PAID_CONFIRM=YES.
"""
import importlib.util
import json
import os
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
MAX_TASKS = 8
DEFAULT_TASKS = 6
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
    for executable in ("git", "node", "npm", "npx", "python3"):
        if not shutil.which(executable):
            raise RuntimeError("Missing " + executable + ". Install prerequisites and retry.")
    plugin, commit = demo.install_plugin()
    experiments = plugin.parent / "experiments"
    print("Pinned Microsoft experiment code:", commit, flush=True)
    if not (checkout / ".git").is_dir():
        if checkout.exists():
            raise RuntimeError("Path exists but is not a Web-Bench checkout: " + str(checkout))
        checkout.parent.mkdir(parents=True, exist_ok=True)
        print("Cloning original Web-Bench into", checkout, flush=True)
        subprocess.run(["git", "clone", "https://github.com/bytedance/web-bench.git",
                        str(checkout)], check=True)
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
            subprocess.run(args, cwd=checkout, check=True)
    # Idempotent: a pre-existing evaluator build does not imply that this
    # machine has the project's pinned browser binary installed.
    args = ["npx", "playwright", "install", "chromium", "chromium-headless-shell"]
    print(">", " ".join(args), flush=True)
    subprocess.run(args, cwd=projects / "expressjs", check=True)
    rows = export_expressjs_tasks(projects, tasks, experiments)
    revision = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    print("Original Web-Bench source:", revision)
    print("Original", len(rows), "expressjs tasks exported:", tasks)
    print("Evaluator:", evaluator)
    print("No model calls were made. Next: make tokeneconomizer-reference-check", flush=True)


def check():
    projects, tasks, selected = inputs()
    _, commit = demo.install_plugin()
    print("PASS: original Web-Bench evaluator, source task order and", len(selected),
          "selected tasks verified; Microsoft harness pinned to", commit)
    print("Projects:", projects)
    print("Export:", tasks)
    print("No model calls were made.")



def task_limit():
    value = int(os.getenv("TE_REFERENCE_TASK_LIMIT", str(DEFAULT_TASKS)))
    if not 1 <= value <= MAX_TASKS:
        raise RuntimeError("Reference pilot requires between 1 and 8 original Web-Bench tasks/arm")
    return value


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
    print("TokenEconomizer ORIGINAL Web-Bench mini pilot (NOT production plugin)")
    print("Source: microsoft/TokenEconomizer @" , demo.TOKENECONOMIZER_COMMIT)
    print("Official evaluator: expressjs | first", task_limit(), "sequential tasks | seed 0")
    print("Arms: baseline vs trimech-web | Copilot CLI BYOK -> Talon -> Anthropic")
    print("Each arm: independent $5.00 admission cap; up to $10.00 combined.")
    print("Pilot subset switches official Web-Bench evaluator to stricter development timeouts.")
    print("Only 1 seed: no statistical, causal or paper-replication claim.")
    print("No API calls performed. One-command benchmark setup:")
    print("  make tokeneconomizer-reference-prepare   # source/dependency downloads; NO paid calls")
    print("  make tokeneconomizer-reference-check     # original evaluator/task order; NO paid calls")
    print("Then export ANTHROPIC_API_KEY (used only in Talon's vault) and run:")
    print("  TE_REFERENCE_PAID_CONFIRM=YES make tokeneconomizer-reference-run")
    print("Default paths:", reference_paths())
    print("Billing may exceed Talon's estimate-based admission limits: set a provider-side limit.")


def run():
    if os.getenv("TE_REFERENCE_PAID_CONFIRM") != "YES":
        raise RuntimeError("No paid execution without TE_REFERENCE_PAID_CONFIRM=YES")
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is required only for Talon's vault setup")
    if demo.ARM_BUDGET != 5.0 or demo.MODEL != MODEL:
        raise RuntimeError("Reference study requires the $5/arm policy and claude-sonnet-5")
    projects, tasks, expected = inputs()
    for name in ("copilot", "talon", "git", "node", "bash"):
        if not shutil.which(name):
            raise RuntimeError("Missing " + name + "; no model calls made")
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
            print("START", name, "|", len(expected), "official tasks | $5 Talon policy", flush=True)
            process = demo.execute(["bash", "scripts/launch/main_sweep.sh"],
                                   env=env, cwd=experiments, check=False,
                                   timeout=3600)
            demo.private(output / "harness.log", process.stdout + "\n" + process.stderr)
            observations[arm] = {"official_arm": name,
                                 "exit_code": process.returncode,
                                 "tasks": official_rows(results, name)}
            try:
                observations[arm]["talon"] = audit_agent(values, run_id, arm, output)
            except Exception as e:
                observations[arm]["audit_error"] = str(e)
                errors.append(arm + " audit: " + str(e))
            if process.returncode:
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
    report = {
        "run_id": run_id, "workload": "original Web-Bench expressjs first tasks",
        "origin": "microsoft/TokenEconomizer", "upstream_sha": commit,
        "model": MODEL, "agent": "copilot CLI BYOK", "seed": 0,
        "task_ids": expected, "budget_admission_per_arm_usd": 5.0,
        "strict_provider_invoice_ceiling": False,
        "grading_caveat": "Original Web-Bench partial stream uses development-mode Playwright timeouts",
        "arms": {arm: {
            "official_arm": x["official_arm"], "exit_code": x["exit_code"],
            "tasks": [{"id": k, "resolved": v.get("resolved"),
                       "resolved_p2": v.get("resolved_p2"),
                       "eff_tokens": v.get("cost_effective_tokens")}
                      for k, v in x["tasks"].items()],
            "talon": x.get("talon"), "audit_error": x.get("audit_error"),
        } for arm, x in arms.items()},
        "errors": errors,
        "verdict": "ONE_SEED_OBSERVATIONAL_ONLY" if comparable else "INCONCLUSIVE",
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
        elif action == "run":
            run()
        else:
            raise RuntimeError("Use plan, prepare, check, or run")
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
