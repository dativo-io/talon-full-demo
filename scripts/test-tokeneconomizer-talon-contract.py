#!/usr/bin/env python3
"""Keyless stable Talon release gateway contract for Claude Code × TokenEconomizer.

Uses the SAME two agent policies and signed-receipt parser as the paid demo,
but a counted local Anthropic-wire fixture instead of Claude Code / Anthropic.
Tests Talon's real startup, secret ACLs, fleet identities, table pricing,
cross-session $7.50 agent budget, zero-dispatch denial and signed audit export.
No real model calls, provider credentials or TokenEconomizer plugin required.
"""
import contextlib
import http.server
import json
import os
import runpy
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = runpy.run_path(str(ROOT / "scripts" / "tokeneconomizer-demo.py"))
MODEL = DEMO["MODEL"]
AGENTS = DEMO["ARM_AGENTS"]
LIMIT = DEMO["ARM_BUDGET"]
RELEASE = (ROOT / "config" / "tokeneconomizer-talon-release.txt").read_text().strip()


def run(command, *, cwd, env, stdin=None):
    result = subprocess.run(command, cwd=cwd, env=env, input=stdin, text=True,
                            capture_output=True, timeout=60, check=False)
    if result.returncode:
        raise RuntimeError(f"{' '.join(command[:3])} failed:\n"
                           f"{(result.stdout + result.stderr)[-1500:]}")
    return result.stdout


class Provider(http.server.BaseHTTPRequestHandler):
    calls = 0
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if not self.path.endswith("/v1/messages") or payload.get("model") != MODEL:
            self.send_error(400, "wrong provider route or model")
            return
        type(self).calls += 1
        # Deliberately >$7.50 at published table price, proving that the
        # budget is an admission cap, not an exact provider-invoice ceiling.
        response = {"id": "msg_talon_contract", "type": "message",
                    "role": "assistant", "model": MODEL,
                    "content": [{"type": "text", "text": "ok"}],
                    "stop_reason": "end_turn", "stop_sequence": None,
                    "usage": {"input_tokens": 3000000, "output_tokens": 100}}
        data = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_):
        pass


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def request(port, token, session, model=MODEL):
    data = json.dumps({"model": model, "max_tokens": 128,
                       "messages": [{"role": "user", "content": "hello"}]}).encode()
    headers = {"Authorization": "Bearer " + token,
               "Content-Type": "application/json",
               "Anthropic-Version": "2023-06-01",
               "X-Talon-Session-ID": session,
               "X-Talon-Client": "te-demo-contract"}
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/v1/proxy/anthropic/v1/messages",
        data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


def signed_records(cwd, env, session, agent, dest):
    run(["talon", "audit", "export", "--tenant", "demo",
         "--agent", agent, "--session", session,
         "--format", "signed-json", "--output", str(dest)], cwd=cwd, env=env)
    report = run(["talon", "audit", "verify", "--file", str(dest)], cwd=cwd, env=env)
    for marker in ("Invalid records: 0", "Missing signature: 0",
                   "Could not parse: 0", "Unsupported: 0"):
        if marker not in report:
            raise RuntimeError(f"invalid Talon signature report for {session}: {report}")
    records = json.loads(dest.read_text())["records"]
    return DEMO["summarize_session_records"](records, session, agent)


def main():
    # Fail before fixture setup or subprocess calls if run without the
    # repository's with-talon.sh resolver or an installed binary.
    import shutil
    if not shutil.which("talon"):
        raise SystemExit(
            "ERROR: Talon CLI not found. Run this check through "
            "'make tokeneconomizer-contract' (uses scripts/with-talon.sh), "
            "or install the supported Talon stable release and put it on PATH. "
            "You can also set TALON_BIN=/absolute/path/to/talon for Make.")
    # Compatibility alone is insufficient: do not silently accept old Talon
    # binaries merely because a local mock can exercise their budget subset.
    if not RELEASE.startswith("v") or not RELEASE[1:].replace(".", "").isdigit():
        raise RuntimeError("Invalid pinned Talon release tag: " + RELEASE)
    installed = run(["talon", "version"], cwd=ROOT, env=DEMO["safe_env"]())
    version_line = installed.splitlines()[0].strip() if installed.strip() else ""
    if version_line != "Talon " + RELEASE:
        raise RuntimeError(
            "TokenEconomizer requires the reviewed Talon stable release "
            + RELEASE + "; installed binary reports " + repr(version_line)
            + ". Install with: go install "
            "github.com/dativo-io/talon/cmd/talon@" + RELEASE
            + " ; export PATH=\"$(go env GOPATH)/bin:$PATH\" "
            "or set TALON_BIN to that release's binary.")
    Provider.calls = 0
    with tempfile.TemporaryDirectory(prefix="talon-token-contract-") as tmp:
        root = Path(tmp)
        cfg = root / "config"
        cfg.mkdir()
        with http.server.ThreadingHTTPServer(("127.0.0.1", 0), Provider) as mock:
            thread = threading.Thread(target=mock.serve_forever, daemon=True)
            thread.start()
            for arm, agent in AGENTS.items():
                policy = cfg / "agents" / arm / "agent.talon.yaml"
                policy.parent.mkdir(parents=True)
                policy.write_text(DEMO["agent_policy"](arm))

            (cfg / "talon.config.yaml").write_text(
                f"""data_dir: "{root / 'store'}"
agents_dir: "agents"
gateway:
  enabled: true
  providers:
    anthropic:
      enabled: true
      api_family: anthropic
      base_url: "http://127.0.0.1:{mock.server_port}"
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
            env = DEMO["safe_env"]()
            env.update(TALON_DATA_DIR=str(root / "store"),
                       TALON_SECRETS_KEY="76" * 32,
                       TALON_SIGNING_KEY="73" * 32,
                       TALON_ADMIN_KEY="61" * 32,
                       TALON_GATEWAY_CONFIG=str(cfg / "talon.config.yaml"))
            tokens = {"baseline": "talon-demo-contract-baseline-001",
                      "after": "talon-demo-contract-after-002"}
            run(["talon", "secrets", "set", "te-provider-secret",
                 "--tenant", "demo", "--agent", AGENTS["baseline"],
                 "--agent", AGENTS["after"]],
                cwd=cfg, env=env, stdin="sk-local-fixture-not-a-real-provider-key")
            for arm, agent in AGENTS.items():
                run(["talon", "secrets", "set", f"{agent}-agent-secret",
                     "--tenant", "demo", "--agent", agent],
                    cwd=cfg, env=env, stdin=tokens[arm])
            run(["talon", "validate", "--dir", "agents"], cwd=cfg, env=env)

            port = free_port()
            log_path = root / "gateway.log"
            with log_path.open("w") as logs:
                process = subprocess.Popen(
                    ["talon", "serve", "--gateway", "--host", "127.0.0.1",
                     "--port", str(port), "--gateway-config",
                     str(cfg / "talon.config.yaml")],
                    cwd=cfg, env=env, stdout=logs, stderr=subprocess.STDOUT)
                try:
                    for _ in range(120):
                        if process.poll() is not None:
                            raise RuntimeError("gateway exited at startup")
                        try:
                            with urllib.request.urlopen(
                                f"http://127.0.0.1:{port}/health", timeout=1
                            ) as response:
                                if response.status == 200:
                                    break
                        except (OSError, urllib.error.URLError):
                            pass
                        time.sleep(0.1)
                    else:
                        raise RuntimeError("gateway did not become ready")

                    for arm, agent in AGENTS.items():
                        first = f"contract-{arm}-1"
                        second = f"contract-{arm}-2"
                        code, body = request(port, tokens[arm], first)
                        if code != 200:
                            raise AssertionError(f"{arm} allowed: HTTP {code} {body}")
                        code, body = request(port, tokens[arm], second)
                        if code != 403 or "budget_exceeded" not in json.dumps(body):
                            raise AssertionError(f"{arm} budget: HTTP {code} {body}")
                        allowed = signed_records(cfg, env, first, agent,
                                                 root / f"{arm}-allowed.json")
                        denied = signed_records(cfg, env, second, agent,
                                                root / f"{arm}-denied.json")
                        if allowed["calls"] != 1 or allowed["cost"] <= LIMIT:
                            raise AssertionError(f"{arm} cost not priced/attributed: {allowed}")
                        if denied["calls"] != 0 or not denied["budget_denied"]:
                            raise AssertionError(f"{arm} denial not evidenced: {denied}")
                    if Provider.calls != 2:
                        raise AssertionError(f"denials reached mock provider: {Provider.calls}")
                    print("PASS: Talon stable release " + RELEASE + " compatibility — two separately budgeted "
                          "$7.50 agents; Anthropic-wire requests, priced usage, two preventive "
                          "denials (zero dispatch), verified signed evidence; no paid calls")
                except Exception:
                    print(log_path.read_text()[-5000:], file=sys.stderr)
                    raise
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=6)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=6)
            mock.shutdown()
            thread.join(timeout=4)


if __name__ == "__main__":
    main()
