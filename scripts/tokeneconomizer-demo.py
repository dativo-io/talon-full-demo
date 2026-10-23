#!/usr/bin/env python3
"""Live Claude Code / Talon / TokenEconomizer comparison. No mock model.

Run: python3 scripts/tokeneconomizer-demo.py validate|run|present
Secrets stay outside Git, in .state/tokeneconomizer-demo and Talon's vault.
"""
import html
import hashlib
import tempfile
import json
import os
import secrets
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from tokeneconomizer_proof import assess as assess_smoke, markdown as smoke_markdown, html_section as smoke_html
from tokeneconomizer_study_proof import assess as assess_study, markdown as study_markdown, html_section as study_html
from tokeneconomizer_workload import (write_repo as write_study_repo, digest as study_digest,
                                    grade as study_grade, order as study_order,
                                    validate as validate_study, WARMUP as STUDY_WARMUP,
                                    TASK_COUNT as STUDY_COUNT, DESIGN as STUDY_DESIGN)

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / ".state" / "tokeneconomizer-demo"
PORT = int(os.getenv("TE_DEMO_PORT", "18086"))
MODEL = os.getenv("TE_DEMO_MODEL", "claude-sonnet-5")
ARM_BUDGET = float(os.getenv("TE_DEMO_ARM_BUDGET", "5.0"))
PROFILE = os.getenv("TE_DEMO_PROFILE", "smoke")
SEED = int(os.getenv("TE_DEMO_SEED", "0"))
PRUNING_MODE = os.getenv("TE_DEMO_PRUNING_MODE", "default")
TALON_RELEASE = (ROOT / "config" / "tokeneconomizer-talon-release.txt").read_text().strip()
# Reviewed upstream revision; intentionally not a floating checkout.
TOKENECONOMIZER_COMMIT = "0ce0e067b42b1dd5a5f5984275d07f8c7686c44a"
# These model identifiers have entries in Talon's embedded USD pricing table.
# An unrecognized model might undermine cost-based admission and comparison.
SUPPORTED_PRICED_MODELS = {
    "claude-sonnet-5", "claude-sonnet-4-6", "claude-sonnet-4-5",
    "claude-haiku-4-5", "claude-opus-4-8", "claude-opus-4-7",
    "claude-opus-4-6", "claude-opus-4-5",
}
ARM_AGENTS = {"baseline": "te-baseline", "after": "te-after"}
# Deliberately allowlist subprocess environment so operator credentials never
# leak to the coding agent, plugin hooks, or Talon server process.
ENV_ALLOW = ("PATH", "HOME", "USER", "LOGNAME", "SHELL", "TERM", "TMPDIR",
             "TEMP", "TMP", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "NO_COLOR",
             "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "HTTP_PROXY", "HTTPS_PROXY",
             "NO_PROXY", "http_proxy", "https_proxy", "no_proxy",
             "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS",
             "SYSTEMROOT", "WINDIR")


def safe_env():
    return {key: os.environ[key] for key in ENV_ALLOW if key in os.environ}

# Five learning sessions and five measurement sessions per arm.
TASKS = [
    ("add", "def add(a,b):\n    return a+b+1\n", "add(2,3)", 5),
    ("double", "def double(n):\n    return n*3\n", "double(4)", 8),
    ("trim", "def trim(s):\n    return s.lower()\n", "trim('  Hi  ')", "hi"),
    ("clamp", "def clamp(x,lo,hi):\n    return max(lo,x)\n", "clamp(10,0,7)", 7),
    ("even", "def even(n):\n    return n%2==1\n", "even(6)", True),
    ("divide", "def divide(a,b):\n    return a/b\n", "divide(9,0)", 0),
    ("unique", "def unique(xs):\n    return xs\n", "unique([1,1,2,1])", [1, 2]),
    ("mean", "def mean(xs):\n    return sum(xs)/len(xs)\n", "mean([])", 0),
    ("slug", "def slug(s):\n    return s.lower().replace(' ','-')\n",
     "slug(' Hi   World ')", "hi-world"),
    ("negative", "def negative(n):\n    return n>0\n", "negative(-3)", True),
]


# These grading cases are absent from the agent's working repository.
TASK_CHECKS = [
    [("add(2,3)", 5), ("add(-2,5)", 3), ("add(0,0)", 0)],
    [("double(4)", 8), ("double(-3)", -6), ("double(0)", 0)],
    [("trim('  Hi  ')", "hi"), ("trim(' A B ')", "a b"),
     ("trim('  WOW  ')", "wow")],
    [("clamp(10,0,7)", 7), ("clamp(-2,0,7)", 0), ("clamp(3,0,7)", 3)],
    [("even(6)", True), ("even(7)", False), ("even(0)", True)],
    [("divide(9,0)", 0), ("divide(8,2)", 4), ("divide(-3,1)", -3)],
    [("unique([1,1,2,1])", [1, 2]), ("unique([])", []),
     ("unique(['b','a','b'])", ["b", "a"])],
    [("mean([])", 0), ("mean([2,4])", 3), ("mean([5])", 5)],
    [("slug(' Hi   World ')", "hi-world"),
     ("slug('Hello There')", "hello-there"), ("slug('  x ')", "x")],
    [("negative(-3)", True), ("negative(3)", False), ("negative(0)", False)],
]


def independent_grade(workspace, index):
    """Run multi-input hidden tests against only the agent's repaired module."""
    name = TASKS[index - 1][0]
    with tempfile.TemporaryDirectory(prefix="te-sealed-grader-") as directory:
        grade = Path(directory)
        (grade / "src").mkdir()
        (grade / "src" / "__init__.py").write_text("")
        shutil.copy2(workspace / "src" / f"case_{index}.py",
                     grade / "src" / f"case_{index}.py")
        cases = ["import unittest",
                 f"from src.case_{index} import {name}",
                 "class SealedGrade(unittest.TestCase):"]
        for test_id, (expression, expected) in enumerate(TASK_CHECKS[index - 1]):
            cases.extend([f"    def test_{test_id:02d}(self):",
                          f"        self.assertEqual({expression}, {repr(expected)})"])
        (grade / "test_grade.py").write_text("\n".join(cases) + "\n")
        graded = execute([sys.executable, "-m", "unittest", "-q",
                          "test_grade"], cwd=grade, timeout=20, check=False)
        return graded.returncode == 0


def execute(args, *, env=None, cwd=None, check=True, timeout=120, stdin=None):
    proc = subprocess.run(args, env=env if env is not None else safe_env(),
                          cwd=cwd, capture_output=True,
                          text=True, timeout=timeout, input=stdin)
    if check and proc.returncode:
        raise RuntimeError("Failed " + str(args[:3]) + ": " +
                           (proc.stderr or proc.stdout)[-700:])
    return proc


def private(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)
    path.chmod(0o600)


def fixture(path):
    if path.exists():
        shutil.rmtree(path)
    (path / "src").mkdir(parents=True)
    (path / "tests").mkdir()
    (path / "src" / "__init__.py").write_text("")
    for i, (name, body, expression, expected) in enumerate(TASKS, 1):
        (path / "src" / f"case_{i}.py").write_text(body)
        (path / "tests" / f"test_case_{i}.py").write_text(
            "import unittest\nfrom src.case_" + str(i) + " import " + name +
            "\nclass T(unittest.TestCase):\n    def test_case(self):\n"
            "        self.assertEqual(" + expression + "," + repr(expected) + ")\n")
    (path / "README.md").write_text(
        "Synthetic Python benchmark. Run python3 -m unittest discover -s tests "
        "-p test_case_N.py. No remotes or dependencies.\n")
    execute(["git", "init", "-q"], cwd=path)


def workload_fingerprint(workspace):
    """Hash the immutable benchmark starting point, not each agent's edits."""
    h = hashlib.sha256()
    for file in sorted([*workspace.glob("src/*.py"),
                        *workspace.glob("tests/*.py"), workspace / "README.md"]):
        rel = file.relative_to(workspace).as_posix()
        h.update(rel.encode() + b"\0")
        h.update(file.read_bytes())
    return h.hexdigest()


def validate():
    validate_study()
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "fixture"
        fixture(path)
        for i in range(1, 11):
            result = execute([sys.executable, "-m", "unittest", "discover",
                              "-s", "tests", "-p", f"test_case_{i}.py"],
                             cwd=path, check=False)
            assert result.returncode, f"fixture {i} unexpectedly passed"
            assert not independent_grade(path, i), (
                f"independent grade {i} unexpectedly passed")
    # Rewriting the visible test cannot fool the sealed grader.
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory) / "fixture"
        fixture(workspace)
        (workspace / "tests" / "test_case_1.py").write_text(
            "import unittest\nclass Fake(unittest.TestCase):\n"
            "    def test_cheat(self): self.assertTrue(True)\n")
        assert not independent_grade(workspace, 1)
    # Also exercise the terminal/HTML report without creating a fake live result.
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        before = total([{"tokens_in": 100, "tokens_out": 20, "cached": 10,
                         "cache_write": 4, "cost": 0.01, "calls": 1, "records": 1,
                         "denials": 0, "provider_errors": 0,
                         "duration_s": 2.0, "passed": True}])
        after = dict(before)
        after["cost"] = 0.008
        sample = {"baseline": before, "with_tokeneconomizer": after,
                  "run_id": "offline-format-test", "model": "test",
                  "tokeneconomizer_sha": "0" * 40}
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            rows = table(sample)
        html_path = Path(directory) / "comparison.html"
        html_report(sample, rows, html_path)
        assert "<table>" in html_path.read_text()
        assert "Talon-estimated provider cost (USD)" in html_path.read_text()
    # Unit contract: signed-export schema accounting, denied-budget evidence,
    # and attribution/pricing fail-closed cases; no Talon executable required.
    sample = {"session_id": "s1", "agent_id": ARM_AGENTS["baseline"],
              "tenant_id": "demo", "invocation_type": "gateway",
              "policy_decision": {"allowed": True},
              "execution": {"model_used": MODEL, "currency": "USD",
                            "pricing_basis": "table", "cost": 0.025,
                            "tokens": {"input": 10, "output": 4,
                                       "cache_read": 15, "cache_write": 3}}}
    denied = {"session_id": "s1", "agent_id": ARM_AGENTS["baseline"],
              "tenant_id": "demo", "invocation_type": "gateway",
              "policy_decision": {"allowed": False,
                                  "reasons": ["budget_exceeded: agent daily cost"]},
              "execution": {"cost": 0}}
    data = summarize_session_records([sample, denied], "s1", ARM_AGENTS["baseline"])
    assert data["cost"] == 0.025 and data["cache_write"] == 3
    assert data["calls"] == 1 and data["budget_denied"] and data["denials"] == 1
    assert summarize_session_records([denied], "s1",
                                     ARM_AGENTS["baseline"])["calls"] == 0
    for mutation in ({"agent_id": "someone-else"},
                     {"execution": dict(sample["execution"], pricing_basis="default_estimate")},
                     {"execution": dict(sample["execution"], currency="EUR")}):
        bad = dict(sample, **mutation)
        try:
            summarize_session_records([bad], "s1", ARM_AGENTS["baseline"])
        except RuntimeError:
            pass
        else:
            raise AssertionError("Untrusted/misattributed cost evidence accepted")
    for arm in ARM_AGENTS:
        policy = agent_policy(arm)
        assert "daily: 5.00" in policy and "monthly: 5.00" in policy
        assert "max_cost: 5.00" in policy
        assert 'allowed_providers: ["anthropic"]' in policy
        assert json.dumps(MODEL) in policy
    assert "ANTHROPIC_API_KEY" not in safe_env()
    assert "OPENAI_API_KEY" not in safe_env()
    assert "claude-sonnet-5" in SUPPORTED_PRICED_MODELS
    assert len(TOKENECONOMIZER_COMMIT) == 40
    print("PASS: 10 failing fixtures and independent sealed grading, two distinct $5.00 Talon policies, "
          "credential isolation, and comparison UX; zero API calls.")


def keys(run_id):
    # Fresh credentials and data store every run, so previous runs do not
    # consume either arm's $5.00 daily/monthly budget.
    values = {name: secrets.token_hex(32) for name in
              ("vault", "signing", "admin", "agent_baseline", "agent_after")}
    private(STATE / run_id / "keys.json", json.dumps(values))
    return values


def tenv(values, run_id):
    env = safe_env()
    config = STATE / run_id / "config"
    env.update(TALON_DATA_DIR=str(STATE / run_id / "talon-store"),
               TALON_SECRETS_KEY=values["vault"],
               TALON_SIGNING_KEY=values["signing"],
               TALON_ADMIN_KEY=values["admin"],
               TALON_GATEWAY_CONFIG=str(config / "talon.config.yaml"))
    return env


def agent_policy(arm):
    agent = ARM_AGENTS[arm]
    # Both warmup and measured requests consume this arm's Talon daily and
    # monthly budget. Session limits are supplementary (one per CLI task).
    # cost_limits.per_request is native-run-only, not a gateway budget.
    return f"""agent:
  name: {agent}
  tenant_id: demo
  version: "1.0.0"
  key:
    secret_name: {agent}-agent-secret
policies:
  allowed_providers: ["anthropic"]
  models:
    allowed: [{json.dumps(MODEL)}]
  cost_limits:
    daily: {ARM_BUDGET:.2f}
    monthly: {ARM_BUDGET:.2f}
  session_limits:
    max_cost: {ARM_BUDGET:.2f}
  data_classification:
    input_scan: true
    output_scan: true
"""


def setup(values, run_id):
    config = STATE / run_id / "config"
    for arm in ARM_AGENTS:
        private(config / "agents" / arm / "agent.talon.yaml", agent_policy(arm))
    # Fleet mode: two separate authenticated agents/budget ledgers.
    # Warn-only PII scans observe synthetic repair prompts without altering
    # them or blocking legitimate code/text in model responses.
    private(config / "talon.config.yaml", f"""data_dir: {json.dumps(str(STATE / run_id / 'talon-store'))}
agents_dir: "agents"
gateway:
  enabled: true
  providers:
    anthropic:
      enabled: true
      api_family: anthropic
      base_url: "https://api.anthropic.com"
      secret_name: te-provider-secret
  organization_policy:
    defaults:
      pii_action: warn
      response_pii_action: warn
    constraints:
      allowed_providers: ["anthropic"]
    log_prompts: false
    log_responses: false
    scan_tool_content: evidence_only
""")
    env = tenv(values, run_id)
    # Secret via stdin, never argv. ACL allows only the two benchmark agents.
    execute(["talon", "secrets", "set", "te-provider-secret",
             "--tenant", "demo", "--agent", ARM_AGENTS["baseline"],
             "--agent", ARM_AGENTS["after"]],
            env=env, stdin=os.environ["ANTHROPIC_API_KEY"], cwd=config)
    for arm, agent in ARM_AGENTS.items():
        execute(["talon", "secrets", "set", f"{agent}-agent-secret",
                 "--tenant", "demo", "--agent", agent],
                env=env, stdin=values["agent_" + arm], cwd=config)
    execute(["talon", "validate", "--dir", "agents"], env=env, cwd=config)

def health():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1) as reply:
            return reply.headers.get("X-Talon-Service", "").lower() == "talon"
    except Exception:
        return False


def start_gateway(values, run_id):
    if health():
        raise RuntimeError(f"Port {PORT} already hosts Talon; refusing to reuse it")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1):
            raise RuntimeError(f"Port {PORT} is already occupied")
    except (urllib.error.URLError, TimeoutError):
        pass
    log = (STATE / run_id / "gateway.log").open("w")
    process = subprocess.Popen(
        ["talon", "serve", "--host", "127.0.0.1", "--port", str(PORT),
         "--gateway", "--gateway-config", str(STATE / run_id / "config" / "talon.config.yaml")],
        cwd=STATE / run_id / "config", env=tenv(values, run_id),
        stdout=log, stderr=subprocess.STDOUT)
    for _ in range(100):
        if process.poll() is not None:
            log.close()
            raise RuntimeError("Talon startup failed: see " + str(STATE / run_id / "gateway.log"))
        if health():
            return process, log
        time.sleep(0.1)
    process.terminate()
    log.close()
    raise RuntimeError("Talon health check failed")


def install_plugin():
    directory = STATE / "TokenEconomizer"
    if not directory.exists():
        execute(["git", "clone", "--depth", "1",
                 "https://github.com/microsoft/TokenEconomizer.git", str(directory)],
                timeout=180)
    dirty = execute(["git", "-C", str(directory), "status", "--porcelain"]).stdout
    if dirty.strip():
        raise RuntimeError("TokenEconomizer checkout has local modifications: " + str(directory))
    commit = execute(["git", "-C", str(directory), "rev-parse", "HEAD"]).stdout.strip()
    if commit != TOKENECONOMIZER_COMMIT:
        execute(["git", "-C", str(directory), "fetch", "--depth", "1", "origin",
                 TOKENECONOMIZER_COMMIT], timeout=180)
        execute(["git", "-C", str(directory), "checkout", "--detach",
                 TOKENECONOMIZER_COMMIT])
        commit = execute(["git", "-C", str(directory), "rev-parse", "HEAD"]).stdout.strip()
    if commit != TOKENECONOMIZER_COMMIT:
        raise RuntimeError("TokenEconomizer revision did not match pinned SHA")
    plugin = directory / "plugin"
    if not (plugin / "scripts" / "te-hook").exists():
        raise RuntimeError("Pinned TokenEconomizer checkout missing hook launcher")
    return plugin, commit

def capture_tool_catalog(workspace, plugin, values, run_id):
    """Upstream-required Claude tool catalog; stops before a model call.

    TokenEconomizer says its auto-pruning evidence omits always-loaded
    Claude tools unless this one-time catalog is recorded first.
    """
    env = safe_env()
    env.update(ANTHROPIC_AUTH_TOKEN=values["agent_after"],
               ANTHROPIC_BASE_URL=f"http://127.0.0.1:{PORT}/v1/proxy/anthropic",
               CLAUDE_CONFIG_DIR=str(STATE / run_id / "claude-after"),
               TOKENECONOMIZER_HOME=str(STATE / run_id / "plugin-after"),
               CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1",
               TE_PAID="false", TE_SIDECALL="1")
    result = execute([str(plugin / "scripts" / "te"), "--host", "claude",
                      "--cwd", str(workspace), "toolprune", "refresh-catalog"],
                     cwd=workspace, env=env, check=False, timeout=90)
    if result.returncode:
        raise RuntimeError("TokenEconomizer Claude tool catalog not captured: " +
                           (result.stderr or result.stdout)[-600:])
    if "tools recorded" not in result.stdout:
        raise RuntimeError("TokenEconomizer tool catalog capture was not confirmed: " +
                           result.stdout[-600:])
    return {"status": "recorded", "details": result.stdout.strip()[:600]}


def summarize_session_records(records, session, agent):
    """Extract comparable accounting ONLY from verified, correctly attributed records."""
    if not records or any(item.get("session_id") != session or
                          item.get("agent_id") != agent or
                          item.get("tenant_id") != "demo" for item in records):
        raise RuntimeError("Missing/misattributed Talon evidence: " + session)
    model_calls = [item for item in records if item.get("invocation_type") == "gateway"
                   and item.get("policy_decision", {}).get("allowed", False)
                   and item.get("execution", {}).get("model_used")]
    budget_denied = any(
        not item.get("policy_decision", {}).get("allowed", True)
        and any("budget_exceeded" in str(reason) for reason in
                (item.get("policy_decision", {}).get("reasons") or []))
        for item in records)
    if not model_calls and not budget_denied:
        raise RuntimeError("No routed calls or budget denial found: " + session)
    for row in model_calls:
        execution = row["execution"]
        if execution.get("model_used") != MODEL:
            raise RuntimeError("Unexpected model in signed evidence: " + session)
        if execution.get("currency") != "USD" or execution.get("pricing_basis") != "table":
            raise RuntimeError("No verified USD table pricing; savings cannot be claimed: " +
                               session)

    def tokens(field):
        return sum(r.get("execution", {}).get("tokens", {}).get(field, 0) or 0
                   for r in model_calls)

    return {"tokens_in": tokens("input"), "tokens_out": tokens("output"),
            "cached": tokens("cache_read"), "cache_write": tokens("cache_write"),
            "cost": sum(r.get("execution", {}).get("cost", 0) or 0 for r in model_calls),
            "calls": len(model_calls), "records": len(records),
            "budget_denied": budget_denied,
            "provider_errors": sum(bool(r.get("execution", {}).get("error"))
                                   for r in model_calls),
            "denials": sum(not r.get("policy_decision", {}).get("allowed", True)
                           for r in records)}


def verified(session, agent, env, destination):
    destination.mkdir(parents=True, exist_ok=True)
    signed = destination / "signed.json"
    execute(["talon", "audit", "export", "--session", session, "--tenant",
             "demo", "--agent", agent,
             "--format", "signed-json", "--output", str(signed)], env=env)
    check = execute(["talon", "audit", "verify", "--file", str(signed)], env=env).stdout
    if not all(value in check for value in
               ("Invalid records: 0", "Missing signature: 0",
                "Could not parse: 0", "Unsupported: 0")):
        raise RuntimeError("Signed evidence failed verification: " + session)
    return summarize_session_records(json.loads(signed.read_text()).get("records", []),
                                     session, agent)

def plugin_pruned_tools(workspace, state):
    """Only count rules the plugin recorded AND Claude will actually read."""
    settings = workspace / ".claude" / "settings.local.json"
    try:
        if not settings.is_file():
            return []
        denied = set(json.loads(settings.read_text()).get("permissions", {}).get("deny") or [])
        if not denied:
            return []
        for file in state.rglob("untool_applied.json"):
            doc = json.loads(file.read_text())
            mine = (doc.get("by_path") or {}).get(str(settings.resolve())) or []
            actual = denied.intersection(mine)
            if actual:
                return sorted(actual)
    except (ValueError, OSError, TypeError):
        pass
    return []


def plugin_session_signals(state, answer):
    """Read what an actual Claude session received; not a pending proposal."""
    result = {"plugin_injected_facts": 0, "plugin_nudges": 0,
              "plugin_session_recorded": False}
    if answer is None:
        return result
    try:
        sid = json.loads(answer.stdout).get("session_id")
        if not isinstance(sid, str) or not sid or len(sid) > 128:
            return result
        for file in state.rglob("sessions/*.json"):
            if file.stem != sid:
                continue
            doc = json.loads(file.read_text())
            result["plugin_session_recorded"] = True
            if int(doc.get("injected_chars") or 0) > 0:
                result["plugin_injected_facts"] = len(doc.get("injected_ids") or [])
            result["plugin_nudges"] = int(doc.get("nudges") or 0)
            return result
    except (ValueError, OSError, TypeError):
        pass
    return result


def one(arm, index, run_id, workspace, values, plugin, issue_id=None, previously_passing=()):
    session = f"te-{run_id}-{arm}-{index}"
    env = safe_env()  # exclude operator API, OAuth and cloud credentials
    env.update(
        ANTHROPIC_AUTH_TOKEN=values["agent_" + arm],
        ANTHROPIC_BASE_URL=f"http://127.0.0.1:{PORT}/v1/proxy/anthropic",
        ANTHROPIC_CUSTOM_HEADERS=("X-Talon-Session-ID: " + session +
                                  "\nX-Talon-Client: te-demo-claude"),
        CLAUDE_CONFIG_DIR=str(STATE / run_id / ("claude-" + arm)),
        TOKENECONOMIZER_HOME=str(STATE / run_id / ("plugin-" + arm)),
        CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1",
        TE_PAID="false")
    if PRUNING_MODE == "accelerated" and plugin:
        # Deliberate diagnostic ablation, NEVER a production-default claim.
        env["TE_TOOLPRUNE_QUIET_MINUTES"] = "0"
    if PROFILE == "study":
        prompt = (
            f"Implement issue {issue_id} in issues/{issue_id}.md in this existing "
            "service repository. Read the repository README and test conventions, "
            "find the relevant rule and API wiring, and run the issue test. "
            "Preserve solutions from earlier tickets. Do not change issues, tests, "
            "or install packages; no network calls. Summarize what you changed.")
        turns, timeout = "24", 900
    else:
        prompt = (f"Fix ONLY src/case_{index}.py so the test passes. Run "
                  f"python3 -m unittest discover -s tests -p test_case_{index}.py. "
                  "Do not use network, install software, or modify any other files. "
                  "Conclude with a one-sentence summary.")
        turns, timeout = "8", 240
    args = ["claude", "-p", prompt, "--model", MODEL, "--output-format", "json",
            "--effort", "high", "--max-turns", turns,
            "--permission-mode", "acceptEdits",
            "--allowedTools", "Read", "Edit", "Write", "Bash(python3 *)"]
    if plugin:
        args += ["--plugin-dir", str(plugin)]
    plugin_state = STATE / run_id / "plugin-after"
    applied_tools = plugin_pruned_tools(workspace, plugin_state) if plugin else []
    started = time.monotonic()
    try:
        answer = execute(args, cwd=workspace, env=env, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        answer = None
    duration = round(time.monotonic() - started, 2)
    grade_passed = (study_grade(workspace, issue_id) if PROFILE == "study"
                    else independent_grade(workspace, index))
    # The last task passing is not sufficient: a later edit must not destroy
    # previously resolved functionality in this persistent repository.
    regression_free = (all(study_grade(workspace, old_id) for old_id in previously_passing)
                       if PROFILE == "study" else True)
    destination = STATE / run_id / arm / f"task-{index:02d}"
    metrics = verified(session, ARM_AGENTS[arm], tenv(values, run_id), destination)
    signed = destination / "signed.json"
    session_signals = plugin_session_signals(plugin_state, answer) if plugin else {}
    metrics.update(task=index, issue_id=issue_id, warmup=index <= (STUDY_WARMUP if PROFILE == "study" else 5),
                   passed=grade_passed, regression_free=regression_free,
                   plugin_pruned_tools=applied_tools,
                   **session_signals,
                   cli_success=answer is not None and answer.returncode == 0,
                   duration_s=duration, session=session,
                   signed_evidence_verified=True,
                   receipt=f"{arm}/task-{index:02d}/signed.json",
                   receipt_sha256=hashlib.sha256(signed.read_bytes()).hexdigest())
    private(destination / "metrics.json", json.dumps(metrics, indent=2))
    if answer:
        private(destination / "claude.json", answer.stdout)
    print(f"{arm:>8} {index:02d} {'learn' if metrics['warmup'] else 'measure':7} "
          f"{'PASS' if metrics['passed'] else 'FAIL'}  "
          f"USD {metrics['cost']:.4f}  {metrics['tokens_in']} input  {duration:.1f}s",
          flush=True)
    return metrics


def total(rows):
    fields = ("tokens_in", "tokens_out", "cached", "cache_write", "cost",
              "calls", "records", "denials", "duration_s", "provider_errors")
    result = {key: sum(item[key] for item in rows) for key in fields}
    result.update(passed=sum(int(item["passed"]) for item in rows),
                  tasks=len(rows))
    return result


def table(report):
    before, after = report["baseline"], report["with_tokeneconomizer"]
    fields = [("Talon-estimated provider cost (USD)", "cost", "USD {:.4f}"),
              ("Uncached input tokens", "tokens_in", "{:,.0f}"),
              ("Output tokens", "tokens_out", "{:,.0f}"),
              ("Cache read tokens", "cached", "{:,.0f}"),
              ("Cache write tokens", "cache_write", "{:,.0f}"),
              ("Runtime (seconds)", "duration_s", "{:.1f}"),
              ("Passing tests", "passed", "{:,.0f}"),
              ("Provider calls", "calls", "{:,.0f}"),
              ("Provider errors", "provider_errors", "{:,.0f}"),
              ("Signed evidence", "records", "{:,.0f}")]
    proof = report.get("proof") or {}
    complete = bool(proof.get("comparison_valid"))
    intervened = bool(proof.get("plugin_activation_observed"))
    budget = float(report.get("budget_cap_usd_per_arm") or ARM_BUDGET)
    # Print raw observed amounts in every run, but a percentage needs
    # comparable signed evidence AND an applied optimization. Otherwise it
    # looks like a causal claim on an unverified warmup fluctuation.
    delta_unproven = "not proven" if complete else "incomplete"
    rows = []
    for label, key, display in fields:
        x, y = before[key], after[key]
        delta = delta_unproven if not complete or not intervened else (
            "n/a" if not x else f"{(y / x - 1) * 100:+.1f}%")
        rows.append((label, display.format(x), display.format(y), delta))
    spent = report.get("arm_total_including_warmups") or {}
    if "baseline" in spent and "after" in spent:
        x, y = spent["baseline"]["cost"], spent["after"]["cost"]
        delta = delta_unproven if not complete or not intervened else (
            "n/a" if not x else f"{(y / x - 1) * 100:+.1f}%")
        rows.insert(1, ("Full-arm cost incl. warmups (USD)",
                        f"USD {x:.4f}", f"USD {y:.4f}", delta))
        rows.insert(2, ("Talon budget utilization",
                        f"{100*x/budget:.1f}%",
                        f"{100*y/budget:.1f}%", delta_unproven if not complete or not intervened else "—"))
    widths = [max(map(lambda line: len(str(line[i])),
                  [("Metric", "Before", "After", "Change")] + rows)) for i in range(4)]
    layout = lambda line: " | ".join(str(line[i]).ljust(widths[i]) for i in range(4))
    print("\n" + layout(("Metric", "Before", "After", "Change")))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(layout(row))
    print(f"Talon budget: USD {report.get('budget_cap_usd_per_arm', ARM_BUDGET):.2f} "
          "daily/monthly per arm, warmup INCLUDED in budget. "
          "Admission estimates may differ from final billed costs.")
    if report.get("arm_status"):
        print("Arm completion:", report["arm_status"])
    for arm, summary in report.get("arm_total_including_warmups", {}).items():
        print(f"{arm}: USD {summary['cost']:.4f} estimated total "
              f"(warmups and measured, limit USD {budget:.2f})")
    if not complete:
        print("INCONCLUSIVE: one or both arms failed to complete successfully "
              "or the optimizer effect was not observed. Do not claim savings.")
    if report.get("profile") == "study":
        print("Headline study metric is WHOLE-STREAM cost and graded success rate, "
              "including eight learning tickets. Last 16 are diagnostic only.")
    else:
        print("Five warmup tasks per arm excluded from measured comparison. "
              "Costs are Talon pricing estimates from real provider usage.")
    return rows


def html_report(report, rows, path):
    row_html = "\n".join("<tr>" + "".join("<td>" + html.escape(str(x)) +
                                              "</td>" for x in row) + "</tr>"
                         for row in rows)
    document = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TokenEconomizer × Talon</title>
<style>body{background:#f6f7f9;color:#1f2937;font:15px/1.6 system-ui;margin:0}
.wrap{max-width:940px;margin:56px auto;padding:0 20px}h1{font-size:34px;letter-spacing:-1.3px}
.label{text-transform:uppercase;letter-spacing:2px;font-size:12px;color:#64748b}
.card{background:white;border:1px solid #e2e8f0;border-radius:16px;padding:25px;margin:22px 0;
box-shadow:0 3px 14px #00000008}table{width:100%;border-collapse:collapse}
td,th{padding:13px;border-bottom:1px solid #e2e8f0;text-align:right}
td:first-child,th:first-child{text-align:left}th{color:#64748b;font-size:12px}
p{color:#475569}.ok{color:#166534;font-weight:650}</style>
<div class="wrap"><div class="label">Dativo Talon · Live integration study</div>
<h1>Before / after TokenEconomizer</h1>
<p>Real Claude Code calls routed through Talon. Provider usage and cost are derived from signed,
independently verified Talon evidence. Tasks are independently graded by Python tests.</p>
PROOF_SECTION
<div class="card"><h2>Measured comparison</h2><table><thead>
<tr><th>Metric</th><th>Without plugin</th><th>With TokenEconomizer</th><th>Change</th>
</tr></thead><tbody>ROWS</tbody></table></div>
<div class="card"><h2>Method and boundaries</h2>
<p>Each arm has its own authenticated Talon agent with a USD BUDGET daily and monthly
budget, covering warmup AND measured tasks. The Talon ledger is new for every run.
The local agent policy allows only the selected Anthropic model, and warn-only
input/response PII scans observe without changing synthetic code.</p>
<p>WORKLOAD_DESC. Independent Claude profiles,
Git workspaces and plugin state. The operator's Anthropic key is stored only in the local
Talon encrypted vault, not passed to Claude Code. All model calls must have Talon evidence.</p>
<p>Execution status: STATUS. Optimizer effect: ACTIVATION.</p>
<p class="ok">Included calls have signed evidence.</p>
<p>Small sample; not a statistical significance claim. Warmups incur real spend
and are excluded only from measured comparison. Costs are Talon estimates based
on provider usage, not final invoice totals. Policy admission estimates may
understate one request's actual cost, so USD BUDGET is a preventive budget, not
an absolute provider-billing ceiling. Budget exhaustion produces an incomplete
comparison, not a savings claim. Local file edits and test subprocesses are
not Talon-governed actions.</p>
</div><div class="card"><h2>What TokenEconomizer actually did</h2>
<p>Learned facts: FACTS · Proposed tool exclusions: PROPOSALS · Applied exclusions: PRUNED · Loop nudges: NUDGES.</p>
<p>These are observed plugin events, not assumed feature activation. Zero means none observed.</p>
</div><p class="label">Run RUNID · model MODEL · TokenEconomizer REV</p></div></html>"""
    section = (study_html(report.get("proof") or assess_study(report))
               if report.get("profile") == "study"
               else smoke_html(report.get("proof") or assess_smoke(report)))
    path.write_text(document.replace("BUDGET", f"{report.get('budget_cap_usd_per_arm', ARM_BUDGET):.2f}")
                    .replace("WORKLOAD_DESC", ("Eight learning and 16 measured repository tickets per arm" if report.get("profile") == "study" else "Five warmup sessions and five measured repairs per arm"))
                    .replace("PROOF_SECTION", section)
                    .replace("ROWS", row_html)
                    .replace("RUNID", report["run_id"])
                    .replace("MODEL", html.escape(report["model"]))
                    .replace("REV", report["tokeneconomizer_sha"][:12])
                    .replace("STATUS", html.escape(str(report.get("arm_status", {}))))
                    .replace("ACTIVATION", "observed" if
                             report.get("optimizer_effect_observed", False)
                             else "not proven — comparison inconclusive")
                    .replace("FACTS", str(report.get("plugin_mechanisms_observed", {}).get("learned_facts", 0)))
                    .replace("PROPOSALS", str(report.get("plugin_mechanisms_observed", {}).get("proposed_tools", 0)))
                    .replace("PRUNED", str(report.get("plugin_mechanisms_observed", {}).get("pruned_tools", 0)))
                    .replace("NUDGES", str(report.get("plugin_mechanisms_observed", {}).get("nudges", 0))))


def observed_optimizations(directory):
    """Read local plugin observations, without inventing any optimizations."""
    result = {"learned_facts": 0, "session_injections": 0,
              "proposed_tools": 0, "pruned_tools": 0, "nudges": 0}
    # Unlike injection.json's rendered_ids (facts prepared for a future
    # session), an actual session's injected_ids means the facts were sent
    # to its context at SessionStart. This is the claim-worthy mechanism.
    for f in directory.rglob("sessions/*.json"):
        try:
            session = json.loads(f.read_text())
            if session.get("injected_chars", 0) > 0 and session.get("injected_ids"):
                result["session_injections"] += 1
        except (OSError, ValueError, TypeError):
            pass
    for f in directory.rglob("injection.json"):
        try:
            result["learned_facts"] += len(json.loads(f.read_text()).get("rendered_ids") or [])
        except (OSError, ValueError):
            pass
    for f in directory.rglob("untool.json"):
        try:
            result["proposed_tools"] += len(json.loads(f.read_text()).get("proposal") or [])
        except (OSError, ValueError):
            pass
    for f in directory.rglob("untool_applied.json"):
        try:
            d = json.loads(f.read_text())
            result["pruned_tools"] += sum(len(v) for v in (d.get("by_path") or {}).values())
        except (OSError, ValueError):
            pass
    for f in directory.rglob("events.jsonl"):
        try:
            for line in f.read_text().splitlines():
                try:
                    result["nudges"] += json.loads(line).get("kind") == "nudge"
                except ValueError:
                    pass
        except OSError:
            pass
    return result


def run():
    if PROFILE not in ("smoke", "study"):
        raise RuntimeError("TE_DEMO_PROFILE must be smoke or study")
    if PRUNING_MODE not in ("default", "accelerated"):
        raise RuntimeError("TE_DEMO_PRUNING_MODE must be default or accelerated")
    # This is a deliberately low-cost PRODUCT demo, not a paid research
    # sweep. Never let a direct Python invocation override the agreed $5.00
    # admission budget per arm. Three-seed Make target splits it further.
    if not (0 < ARM_BUDGET <= 5.0):
        raise RuntimeError("TE_DEMO_ARM_BUDGET must be > 0 and <= USD 5.00 per arm")
    if PROFILE == "study" and SEED not in (0,1,2):
        raise RuntimeError("TE_DEMO_SEED must be 0, 1 or 2")
    if MODEL not in SUPPORTED_PRICED_MODELS:
        raise RuntimeError(f"Model {MODEL!r} is not in the verified Talon USD "
                           "pricing allowlist; refusing unpriced budget experiment.")
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("Export ANTHROPIC_API_KEY before make demo-tokeneconomizer")
    for tool in ("talon", "claude", "git"):
        if not shutil.which(tool):
            raise RuntimeError(tool + " not installed")
    # Direct Python entry must enforce the same version guard as the Make
    # contract, even when the operator bypasses Make (no paid calls yet).
    release_result = execute(["talon", "version"], check=False, timeout=15)
    installed = (release_result.stdout or "").splitlines()
    if release_result.returncode != 0 or not installed or installed[0].strip() != "Talon " + TALON_RELEASE:
        raise RuntimeError(
            "TokenEconomizer requires Talon " + TALON_RELEASE +
            "; installed binary reports " + repr((release_result.stdout or
             release_result.stderr).strip()[:160]) +
            ". Install: go install github.com/dativo-io/talon/cmd/talon@" +
            TALON_RELEASE + " and put $(go env GOPATH)/bin on PATH.")
    if "--plugin-dir" not in execute(["claude", "--help"], timeout=30).stdout:
        raise RuntimeError("Claude Code version does not advertise --plugin-dir")
    task_limit = int(os.getenv("TE_DEMO_TASK_LIMIT",
                               str(STUDY_COUNT if PROFILE == "study" else 10)))
    if task_limit not in ((STUDY_COUNT,) if PROFILE == "study" else (1, 10)):
        raise RuntimeError("Study requires all 24 tickets; smoke allows 1 or 10")
    stream = study_order(SEED) if PROFILE == "study" else []
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    print(f"TokenEconomizer {PROFILE}: seed={SEED}, {task_limit} tasks/arm, "
          f"USD {ARM_BUDGET:.2f} per-arm Talon admission budgets; "
          "learning counts against both budgets.", flush=True)
    print("NOTE: Talon limits request admission by estimates; provider billing "
          "can exceed these amounts. An interrupted study is INCONCLUSIVE.", flush=True)
    print("Preparing isolated identities, provider vault and gateway...", flush=True)
    values = keys(run_id)
    setup(values, run_id)
    print("Preparing reviewed TokenEconomizer checkout...", flush=True)
    plugin, commit = install_plugin()
    versions = {}
    for command, label in ((["claude", "--version"], "claude_cli"),
                           (["talon", "version"], "talon_cli"),
                           (["git", "--version"], "git")):
        version = execute(command, check=False, timeout=15)
        versions[label] = (version.stdout or version.stderr).strip()[:200]
    print("Starting isolated Talon gateway...", flush=True)
    server, log = start_gateway(values, run_id)
    print("Gateway healthy; starting billable Claude Code experiment.", flush=True)
    arms = {arm: [] for arm in ARM_AGENTS}
    workload_digests = {}
    catalog = {"status": "not_attempted"}
    run_error = ""
    try:
        arms_order = ("baseline", "after") if PROFILE == "smoke" or SEED % 2 == 0 else ("after", "baseline")
        for arm in arms_order:
            print(f"START ARM {arm}: up to {task_limit} tasks, budget USD {ARM_BUDGET:.2f}; "
                  "tool and model costs count toward this arm.", flush=True)
            workspace = STATE / run_id / ("workspace-" + arm)
            if PROFILE == "study":
                write_study_repo(workspace)
                workload_digests[arm] = study_digest(workspace)
            else:
                fixture(workspace)
                workload_digests[arm] = workload_fingerprint(workspace)
            if arm == "after":
                try:
                    catalog = capture_tool_catalog(workspace, plugin, values, run_id)
                    print("TokenEconomizer catalog:", catalog["status"], flush=True)
                except Exception as exc:
                    catalog = {"status": "failed", "details": str(exc)}
                    run_error = "TokenEconomizer catalog: " + str(exc)
                    print("RUN ERROR:", run_error, file=sys.stderr, flush=True)
                    break
            for index in range(1, task_limit + 1):
                try:
                    issue_id = stream[index-1]["id"] if PROFILE == "study" else None
                    previously_passing = [r["issue_id"] for r in arms[arm] if
                                          r.get("passed") and r.get("regression_free")]
                    result = one(arm, index, run_id, workspace, values,
                                 plugin if arm == "after" else None,
                                 issue_id, previously_passing)
                except Exception as exc:
                    # Preserve all completed task receipts and report the
                    # interrupted/failed experiment instead of losing the run.
                    run_error = f"{arm} task {index}: {exc}"
                    print("RUN ERROR:", run_error, file=sys.stderr, flush=True)
                    break
                arms[arm].append(result)
                if result["budget_denied"]:
                    print(f"{arm}: Talon denied a request due to budget; "
                          "stopping arm (no bypass).", flush=True)
                    break
            if run_error:
                break
    finally:
        server.terminate()
        try:
            server.wait(timeout=8)
        except subprocess.TimeoutExpired:
            server.kill()
        log.close()
    # Distinguish plugin installation, hook execution and an observed optimization.
    # A hook that fired but did nothing must NOT be marketed as a saving.
    plugin_state = STATE / run_id / "plugin-after"
    observed_hooks = list(plugin_state.rglob("sessions/*.json"))
    mechanisms = observed_optimizations(plugin_state)
    effect_observed = (len(observed_hooks) >= 5 and
                       any(mechanisms[k] for k in
                           ("session_injections", "pruned_tools", "nudges")))
    report = {
        "run_id": run_id, "model": MODEL, "tokeneconomizer_sha": commit,
        "demo_revision": execute(["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip(),
        "profile": PROFILE, "seed": SEED, "task_order": [t["id"] for t in stream],
        "workload_design": STUDY_DESIGN if PROFILE == "study" else "single-function-smoke",
        "warmup_count": STUDY_WARMUP if PROFILE == "study" else 5,
        "reasoning_effort": "high",
        "pruning_mode": PRUNING_MODE,
        "token_economizer_config": "defaults-no-paid-helpers" if PRUNING_MODE == "default" else "accelerated-pruning-ablation",
        "talon_release": TALON_RELEASE,
        "workload_sha256": workload_digests,
        "tokeneconomizer_catalog": catalog,
        "task_limit": task_limit, "run_error": run_error,
        "tool_versions": versions, "comparison_policy": ("separate governed Talon agents" if PROFILE == "study"
                              else "separate $5.00 Talon agents"),
        "token_economizer_hook_sessions": len(observed_hooks),
        "plugin_mechanisms_observed": mechanisms,
        "optimizer_effect_observed": effect_observed,
        "budget_cap_usd_per_arm": ARM_BUDGET,
        "arm_total_including_warmups": {a: total(rows) for a, rows in arms.items()},
        "arm_status": {a: ("budget_exhausted" if any(r["budget_denied"] for r in rows)
                           else "smoke_only" if task_limit == 1 and len(rows) == 1
                           else "completed" if len(rows) == task_limit and
                             all(r["cli_success"] and r["provider_errors"] == 0 for r in rows)
                           else "completed_with_failures" if len(rows) == task_limit
                           else "incomplete")
                       for a, rows in arms.items()},
        "baseline": total(arms["baseline"][STUDY_WARMUP if PROFILE == "study" else 5:]),
        "with_tokeneconomizer": total(arms["after"][STUDY_WARMUP if PROFILE == "study" else 5:]),
        "baseline_warmup": total(arms["baseline"][:STUDY_WARMUP if PROFILE == "study" else 5]),
        "tokeneconomizer_warmup": total(arms["after"][:STUDY_WARMUP if PROFILE == "study" else 5]),
        "tasks": arms, "source": "Live Anthropic through Talon signed evidence",
    }
    destination = STATE / run_id
    report["proof"] = assess_study(report) if PROFILE == "study" else assess_smoke(report)
    private(destination / "comparison.json", json.dumps(report, indent=2))
    private(destination / "proof.json", json.dumps(report["proof"], indent=2))
    private(destination / "proof.md",
            study_markdown(report["proof"], report) if PROFILE == "study"
            else smoke_markdown(report["proof"], report))
    private(STATE / "latest.txt", run_id)
    rows = table(report)
    html_report(report, rows, destination / "comparison.html")
    print("\nPROOF VERDICT:", report["proof"]["verdict"])
    print(report["proof"]["headline"])
    print("Proof report:", destination / "proof.md")
    print("Observed TokenEconomizer hook session files:", len(observed_hooks))
    print("Plugin mechanisms:", report["plugin_mechanisms_observed"])
    print("Optimizer effect observed:", effect_observed)
    print("HTML report:", destination / "comparison.html")
    print("Raw signed receipts:", destination)
    if run_error:
        raise RuntimeError("Incomplete experiment; partial report saved: " +
                           str(destination / "comparison.html") + " — " + run_error)


def main():
    try:
        action = sys.argv[1] if len(sys.argv) > 1 else "run"
        if action == "validate":
            validate()
        elif action == "run":
            run()
        elif action == "present":
            run_id = (STATE / "latest.txt").read_text().strip()
            report = json.loads((STATE / run_id / "comparison.json").read_text())
            if not report.get("proof"):
                raise RuntimeError("Stored report has no proof assessment; "
                                   "rerun the benchmark with the updated demo.")
            table(report)
            print("\nPROOF VERDICT:", report["proof"]["verdict"])
            print(report["proof"]["headline"])
            print("Proof report:", STATE / run_id / "proof.md")
            print("HTML report:", STATE / run_id / "comparison.html")
        else:
            raise RuntimeError("Use validate, run, or present")
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
