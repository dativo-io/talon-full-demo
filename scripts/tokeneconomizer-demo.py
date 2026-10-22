#!/usr/bin/env python3
"""Live Claude Code / Talon / TokenEconomizer comparison. No mock model.

Run: python3 scripts/tokeneconomizer-demo.py validate|run|present
Secrets stay outside Git, in .state/tokeneconomizer-demo and Talon's vault.
"""
import html
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

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / ".state" / "tokeneconomizer-demo"
PORT = int(os.getenv("TE_DEMO_PORT", "18086"))
MODEL = os.getenv("TE_DEMO_MODEL", "claude-sonnet-5")
AGENT = "te-claude-code"

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


def execute(args, *, env=None, cwd=None, check=True, timeout=120):
    proc = subprocess.run(args, env=env, cwd=cwd, capture_output=True,
                          text=True, timeout=timeout)
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


def validate():
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "fixture"
        fixture(path)
        for i in range(1, 11):
            result = execute([sys.executable, "-m", "unittest", "discover",
                              "-s", "tests", "-p", f"test_case_{i}.py"],
                             cwd=path, check=False)
            assert result.returncode, f"fixture {i} unexpectedly passed"
    print("PASS: 10 independent initially failing fixtures; zero API calls.")


def keys():
    file = STATE / "keys.json"
    if file.exists():
        if file.stat().st_mode & 0o077:
            raise RuntimeError("Unsafe key permissions: chmod 600 " + str(file))
        return json.loads(file.read_text())
    values = {name: secrets.token_hex(32) for name in ("vault", "signing", "admin", "agent")}
    private(file, json.dumps(values))
    return values


def tenv(values):
    env = os.environ.copy()
    env.update(TALON_DATA_DIR=str(STATE / "talon-store"),
               TALON_SECRETS_KEY=values["vault"],
               TALON_SIGNING_KEY=values["signing"],
               TALON_ADMIN_KEY=values["admin"],
               TALON_DEFAULT_POLICY=str(STATE / "config" / "agent.talon.yaml"),
               TALON_GATEWAY_CONFIG=str(STATE / "config" / "talon.config.yaml"))
    return env


def setup(values):
    config = STATE / "config"
    private(config / "agent.talon.yaml", """agent:
  name: te-claude-code
  tenant_id: demo
  version: "1.0.0"
  key:
    secret_name: te-agent-secret
policies:
  allowed_providers: ["anthropic"]
  cost_limits:
    per_request: 5.0
    daily: 20.0
    monthly: 100.0
  session_limits:
    max_cost: 5.0
  data_classification:
    input_scan: true
""")
    private(config / "talon.config.yaml", """gateway:
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
""")
    env = tenv(values)
    execute(["talon", "secrets", "set", "te-provider-secret",
             os.environ["ANTHROPIC_API_KEY"], "--tenant", "demo", "--agent", AGENT],
            env=env)
    execute(["talon", "secrets", "set", "te-agent-secret",
             values["agent"], "--tenant", "demo", "--agent", AGENT], env=env)
    execute(["talon", "validate", "--file",
             str(config / "agent.talon.yaml")], env=env)


def health():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1) as reply:
            return reply.headers.get("X-Talon-Service", "").lower() == "talon"
    except Exception:
        return False


def start_gateway(values):
    if health():
        raise RuntimeError(f"Port {PORT} already hosts Talon; refusing to reuse it")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1):
            raise RuntimeError(f"Port {PORT} is already occupied")
    except (urllib.error.URLError, TimeoutError):
        pass
    log = (STATE / "gateway.log").open("w")
    process = subprocess.Popen(
        ["talon", "serve", "--host", "127.0.0.1", "--port", str(PORT),
         "--gateway", "--gateway-config", str(STATE / "config" / "talon.config.yaml")],
        cwd=STATE / "config", env=tenv(values),
        stdout=log, stderr=subprocess.STDOUT)
    for _ in range(100):
        if process.poll() is not None:
            log.close()
            raise RuntimeError("Talon startup failed: see " + str(STATE / "gateway.log"))
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
    commit = execute(["git", "-C", str(directory), "rev-parse", "HEAD"]).stdout.strip()
    plugin = directory / "plugin"
    if not (plugin / "scripts" / "te-hook").exists():
        raise RuntimeError("TokenEconomizer checkout missing hook launcher")
    return plugin, commit


def verified(session, env, destination):
    destination.mkdir(parents=True, exist_ok=True)
    signed = destination / "signed.json"
    execute(["talon", "audit", "export", "--session", session,
             "--format", "signed-json", "--output", str(signed)], env=env)
    check = execute(["talon", "audit", "verify", "--file", str(signed)], env=env).stdout
    if not all(value in check for value in
               ("Invalid records: 0", "Missing signature: 0", "Could not parse: 0")):
        raise RuntimeError("Signed evidence failed verification: " + session)
    records = json.loads(signed.read_text()).get("records", [])
    if not records or any(item.get("session_id") != session or
                          item.get("agent_id") != AGENT for item in records):
        raise RuntimeError("Missing/misattributed evidence: " + session)
    model_calls = [item for item in records if item.get("invocation_type") == "gateway"
                   and item.get("execution", {}).get("model_used")]
    if not model_calls:
        raise RuntimeError("No routed provider calls found: " + session)

    def tokens(field):
        return sum(item.get("execution", {}).get("tokens", {}).get(field, 0) or 0
                   for item in model_calls)

    return {"tokens_in": tokens("input"), "tokens_out": tokens("output"),
            "cached": tokens("cache_read"),
            "cost": sum(item.get("execution", {}).get("cost", 0) or 0
                        for item in model_calls),
            "calls": len(model_calls), "records": len(records),
            "denials": sum(not item.get("policy_decision", {}).get("allowed", True)
                           for item in records)}


def one(arm, index, run_id, workspace, values, plugin):
    session = f"te-{run_id}-{arm}-{index}"
    env = os.environ.copy()
    # Never pass the actual upstream key to Claude: only Talon has the vaulted key.
    for key in ("ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN",
                "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX"):
        env.pop(key, None)
    env.update(
        ANTHROPIC_AUTH_TOKEN=values["agent"],
        ANTHROPIC_BASE_URL=f"http://127.0.0.1:{PORT}/v1/proxy/anthropic",
        ANTHROPIC_CUSTOM_HEADERS=("X-Talon-Session-ID: " + session +
                                  "\nX-Talon-Client: te-demo-claude"),
        CLAUDE_CONFIG_DIR=str(STATE / run_id / ("claude-" + arm)),
        TOKENECONOMIZER_HOME=str(STATE / run_id / ("plugin-" + arm)),
        CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1",
        TE_PAID="false", TE_TOOLPRUNE="auto", TE_TOOLPRUNE_EVIDENCE="5",
        TE_TOOLPRUNE_QUIET_MINUTES="0")
    prompt = (f"Fix ONLY src/case_{index}.py so the test passes. Run "
              f"python3 -m unittest discover -s tests -p test_case_{index}.py. "
              "Do not use network, install software, or modify any other files. "
              "Conclude with a one-sentence summary.")
    args = ["claude", "-p", prompt, "--model", MODEL, "--output-format", "json",
            "--max-turns", "8", "--permission-mode", "acceptEdits",
            "--allowedTools", "Read", "Edit", "Write", "Bash(python3 *)"]
    if plugin:
        args += ["--plugin-dir", str(plugin)]
    started = time.monotonic()
    try:
        answer = execute(args, cwd=workspace, env=env, timeout=240, check=False)
    except subprocess.TimeoutExpired:
        answer = None
    duration = round(time.monotonic() - started, 2)
    grade = execute([sys.executable, "-m", "unittest", "discover",
                     "-s", "tests", "-p", f"test_case_{index}.py"],
                    cwd=workspace, timeout=15, check=False)
    destination = STATE / run_id / arm / f"task-{index:02d}"
    metrics = verified(session, tenv(values), destination)
    metrics.update(task=index, warmup=index <= 5, passed=grade.returncode == 0,
                   cli_success=answer is not None and answer.returncode == 0,
                   duration_s=duration, session=session)
    private(destination / "metrics.json", json.dumps(metrics, indent=2))
    if answer:
        private(destination / "claude.json", answer.stdout)
    print(f"{arm:>8} {index:02d} {'warmup' if index<=5 else 'measure':7} "
          f"{'PASS' if metrics['passed'] else 'FAIL'}  "
          f"USD {metrics['cost']:.4f}  {metrics['tokens_in']} input  {duration:.1f}s",
          flush=True)
    return metrics


def total(rows):
    fields = ("tokens_in", "tokens_out", "cached", "cost", "calls",
              "records", "denials", "duration_s")
    result = {key: sum(item[key] for item in rows) for key in fields}
    result.update(passed=sum(int(item["passed"]) for item in rows),
                  tasks=len(rows))
    return result


def table(report):
    before, after = report["baseline"], report["with_tokeneconomizer"]
    fields = [("Provider cost (USD)", "cost", "USD {:.4f}"),
              ("Input tokens", "tokens_in", "{:,.0f}"),
              ("Output tokens", "tokens_out", "{:,.0f}"),
              ("Cache read tokens", "cached", "{:,.0f}"),
              ("Runtime (seconds)", "duration_s", "{:.1f}"),
              ("Passing tests", "passed", "{:,.0f}"),
              ("Provider calls", "calls", "{:,.0f}"),
              ("Signed evidence", "records", "{:,.0f}")]
    rows = []
    for label, key, display in fields:
        x, y = before[key], after[key]
        delta = "n/a" if not x else f"{(y / x - 1) * 100:+.1f}%"
        rows.append((label, display.format(x), display.format(y), delta))
    widths = [max(map(lambda line: len(str(line[i])),
                  [("Metric", "Before", "After", "Change")] + rows)) for i in range(4)]
    layout = lambda line: " | ".join(str(line[i]).ljust(widths[i]) for i in range(4))
    print("\n" + layout(("Metric", "Before", "After", "Change")))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(layout(row))
    print("Five warmup tasks per arm excluded. Real API spend; no mock.")
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
<div class="card"><h2>Measured comparison</h2><table><thead>
<tr><th>Metric</th><th>Without plugin</th><th>With TokenEconomizer</th><th>Change</th>
</tr></thead><tbody>ROWS</tbody></table></div>
<div class="card"><h2>Method and boundaries</h2>
<p>Five warmup sessions and five measured repairs per arm. Independent Claude profiles,
Git workspaces and plugin state. The operator's Anthropic key is stored only in the local
Talon encrypted vault, not passed to Claude Code. All model calls must have Talon evidence.</p>
<p class="ok">Included calls have signed evidence.</p>
<p>Small sample; not a statistical significance claim. Warmups incur real spend.
Savings may be negative. Local file edits and test subprocesses are not Talon-governed actions.</p>
</div><p class="label">Run RUNID · model MODEL · TokenEconomizer REV</p></div></html>"""
    path.write_text(document.replace("ROWS", row_html)
                    .replace("RUNID", report["run_id"])
                    .replace("MODEL", html.escape(report["model"]))
                    .replace("REV", report["tokeneconomizer_sha"][:12]))


def run():
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("Export ANTHROPIC_API_KEY before make demo-tokeneconomizer")
    for tool in ("talon", "claude", "git"):
        if not shutil.which(tool):
            raise RuntimeError(tool + " not installed")
    if "--plugin-dir" not in execute(["claude", "--help"], timeout=30).stdout:
        raise RuntimeError("Claude Code version does not advertise --plugin-dir")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    values = keys()
    setup(values)
    plugin, commit = install_plugin()
    server, log = start_gateway(values)
    arms = {}
    try:
        for arm in ("baseline", "after"):
            workspace = STATE / run_id / ("workspace-" + arm)
            fixture(workspace)
            arms[arm] = []
            for index in range(1, 11):
                arms[arm].append(one(arm, index, run_id, workspace, values,
                                     plugin if arm == "after" else None))
    finally:
        server.terminate()
        try:
            server.wait(timeout=8)
        except subprocess.TimeoutExpired:
            server.kill()
        log.close()
    report = {
        "run_id": run_id, "model": MODEL, "tokeneconomizer_sha": commit,
        "baseline": total(arms["baseline"][5:]),
        "with_tokeneconomizer": total(arms["after"][5:]),
        "baseline_warmup": total(arms["baseline"][:5]),
        "tokeneconomizer_warmup": total(arms["after"][:5]),
        "tasks": arms, "source": "Live Anthropic through Talon signed evidence",
    }
    destination = STATE / run_id
    private(destination / "comparison.json", json.dumps(report, indent=2))
    private(STATE / "latest.txt", run_id)
    rows = table(report)
    html_report(report, rows, destination / "comparison.html")
    print("HTML report:", destination / "comparison.html")
    print("Raw signed receipts:", destination)


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
            table(report)
            print("HTML report:", STATE / run_id / "comparison.html")
        else:
            raise RuntimeError("Use validate, run, or present")
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
