#!/usr/bin/env python3
"""Local presenter console: mirrors every granular CLI check in a browser.

SECURITY BOUNDARY: Runs on the Docker HOST, NEVER in the AI UI container.
The host operator can use Docker; the restricted AI workload cannot.
No generic shell or arbitrary container/command execution is exposed.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = Path(__file__).resolve().parent.parent
CASE = ROOT / "cases" / "people-analytics-copilot"
COMPOSE = CASE / "compose.isolated.yaml"
ENV_FILE = CASE / ".state" / "isolated.env"
SESSION = "hr-demo-presenter"
EVIDENCE_FILE = "/tmp/hr-presenter-evidence.json"

# Single source of truth for browser and command-line steps.
# Tuple: id, phase, descriptive name, command displayed as a shell instruction.
ACTIONS = (
    ("services", "Setup", "Inspect running services", "dc ps"),
    ("before", "1 · Direct access", "Privileged direct employee export (synthetic)",
     "dc exec -T hr-server python3 verify_isolation.py before"),
    ("counters", "1 · Direct access", "Read independent HR execution counters",
     "dc exec -T hr-server python3 verify_isolation.py counters"),
    ("reset", "2 · Measurement reset", "Explicitly reset synthetic HR counters",
     "dc exec -T hr-server python3 verify_isolation.py reset"),
    ("ui_networks", "3 · Deployment perimeter", "Inspect AI app networks",
     "docker inspect \"$(dc ps -q ui)\" --format '{{json .NetworkSettings.Networks}}'"),
    ("talon_networks", "3 · Deployment perimeter", "Inspect Talon proxy networks",
     "docker inspect \"$(dc ps -q talon-mcp)\" --format '{{json .NetworkSettings.Networks}}'"),
    ("hr_networks", "3 · Deployment perimeter", "Inspect HR backend networks",
     "docker inspect \"$(dc ps -q hr-server)\" --format '{{json .NetworkSettings.Networks}}'"),
    ("ui_mounts", "3 · Deployment perimeter", "Inspect AI app volume mounts",
     "docker inspect \"$(dc ps -q ui)\" --format '{{json .Mounts}}'"),
    ("boundary", "3 · Deployment perimeter", "Verify network isolation and working dashboard",
     "dc exec -T ui python3 verify_isolation.py boundary"),
    ("agent_policy", "4 · Effective boundaries", "Inspect agent allowlist",
     "dc exec -T talon-mcp cat /state/agent.talon.yaml"),
    ("proxy_policy", "4 · Effective boundaries", "Inspect MCP proxy allow/deny policy",
     "dc exec -T talon-mcp cat /case/proxy.isolated.talon.yaml"),
    ("discover", "4 · Effective boundaries", "Discover available tools through Talon",
     "dc exec -T ui python3 verify_isolation.py discover"),
    ("allow", "5 · Authorized analytics", "Execute approved aggregate tool; inspect receipt",
     "dc exec -T ui python3 verify_isolation.py allow"),
    ("deny", "6 · Forbidden operation", "Force employee export through Talon; inspect denial",
     "dc exec -T ui python3 verify_isolation.py deny"),
    ("backend_counts", "6 · Forbidden operation", "Verify backend export remained at zero",
     "dc exec -T hr-server python3 verify_isolation.py backend-counts"),
    ("evidence_export", "7 · Independent evidence", "Export signed presenter session",
     "dc exec -T talon-mcp talon audit export --format signed-json "
     "--session hr-demo-presenter --output /tmp/hr-presenter-evidence.json"),
    ("evidence_verify", "7 · Independent evidence", "Verify exported signatures",
     "dc exec -T talon-mcp talon audit verify --file /tmp/hr-presenter-evidence.json"),
)
CATALOG = {item[0]: item for item in ACTIONS}
RUN_LOCK = threading.Lock()


def _environment():
    if not COMPOSE.is_file() or not ENV_FILE.is_file():
        raise RuntimeError("Isolated demo is not initialized; first run 'bash scripts/people-analytics-isolated.sh up'")
    binary = os.environ.get("HR_DEMO_TALON_BIN") or shutil.which("talon")
    if not binary:
        raise RuntimeError("Cannot find Talon binary; set HR_DEMO_TALON_BIN")
    env = dict(os.environ)
    env["HR_DEMO_TALON_BIN"] = str(Path(binary).resolve())
    return env


def _dc_prefix():
    return ["docker", "compose", "-f", str(COMPOSE), "--env-file", str(ENV_FILE)]


def build_command(action, runner=None):
    """All arguments are fixed, with no user-supplied shell or tool inputs."""
    if action not in CATALOG:
        raise ValueError("Action is not in the presenter allowlist")
    if action == "services":
        return _dc_prefix() + ["ps"]
    if action in ("ui_networks", "talon_networks", "hr_networks", "ui_mounts"):
        service = {"ui_networks": "ui", "talon_networks": "talon-mcp",
                   "hr_networks": "hr-server", "ui_mounts": "ui"}[action]
        if not runner:
            raise RuntimeError("Inspect actions need a running Compose service ID")
        cid = runner(_dc_prefix() + ["ps", "-q", service])
        if not cid.strip():
            raise RuntimeError(service + " has no running container")
        format_arg = "{{json .Mounts}}" if action == "ui_mounts" else "{{json .NetworkSettings.Networks}}"
        return ["docker", "inspect", cid.strip(), "--format", format_arg]
    if action in ("agent_policy", "proxy_policy"):
        name = "/state/agent.talon.yaml" if action == "agent_policy" else "/case/proxy.isolated.talon.yaml"
        return _dc_prefix() + ["exec", "-T", "talon-mcp", "cat", name]
    if action in ("evidence_export", "evidence_verify"):
        verb = (["audit", "export", "--format", "signed-json",
                 "--session", SESSION, "--output", EVIDENCE_FILE]
                if action == "evidence_export"
                else ["audit", "verify", "--file", EVIDENCE_FILE])
        return _dc_prefix() + ["exec", "-T", "talon-mcp", "talon"] + verb
    service = ("hr-server" if action in ("before", "counters", "reset", "backend_counts")
               else "ui")
    return _dc_prefix() + ["exec", "-T", service, "python3",
                           "verify_isolation.py", action]


def perform(action):
    """One allowlisted step, returning actual output/return code, never a synthetic PASS."""
    env = _environment()
    if action not in CATALOG:
        raise ValueError("Unknown presenter action")
    def invoke(argv):
        out = subprocess.run(argv, capture_output=True, text=True, timeout=45, env=env,
                             cwd=ROOT, check=False)
        if out.returncode:
            raise RuntimeError("Container lookup failed: " + (out.stderr or out.stdout)[-1000:])
        return out.stdout
    with RUN_LOCK:
        command = build_command(action, runner=invoke)
        try:
            p = subprocess.run(command, capture_output=True, text=True, timeout=60,
                               env=env, cwd=ROOT, check=False)
            return {"action": action, "ok": p.returncode == 0,
                    "exit_code": p.returncode, "stdout": p.stdout[-24000:],
                    "stderr": p.stderr[-9000:], "command": CATALOG[action][3]}
        except subprocess.TimeoutExpired:
            return {"action": action, "ok": False, "exit_code": None, "stdout": "",
                    "stderr": "Timed out after 60 seconds", "command": CATALOG[action][3]}


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Talon · People Analytics Proof Console</title>
<style>
*{box-sizing:border-box}body{font:15px system-ui,Arial;background:#f3f6fa;color:#20324e;margin:0}
header{background:#142e53;color:white;padding:23px max(24px,calc((100vw - 1120px)/2))}
header h1{margin:0 0 7px;font-size:24px}a{color:inherit}
main{max-width:1120px;margin:auto;padding:22px}section{background:white;border:1px solid #dae4f0;border-radius:12px;padding:20px;margin-bottom:16px}
h2{font-size:19px;margin:0 0 6px}h3{font-size:15px;margin:0 0 5px}.muted{font-size:13px;color:#61748c}
button{border:0;background:#155db1;color:white;border-radius:7px;padding:9px 14px;cursor:pointer;font:inherit}
button:disabled{opacity:.5;cursor:wait}.secondary{background:#e5eefb;color:#165ba5}
input{padding:9px;border:1px solid #b5c5d8;border-radius:7px;max-width:400px;width:100%;font:inherit}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}@media(max-width:800px){.grid{grid-template-columns:1fr}}
.item{border:1px solid #dae4f0;border-radius:9px;padding:13px;min-width:0}
pre{white-space:pre-wrap;word-break:break-word;background:#f3f6fa;border:1px solid #e4e9f2;padding:11px;border-radius:8px;max-height:330px;overflow:auto;font:12px/1.6 ui-monospace,monospace}
.label{font-size:12px;color:#4f6988}.pass{color:#176646}.fail{color:#a12f32}.small{font-size:12px;color:#596b82}
.bar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
</style></head><body>
<header><h1>People Analytics · Proof Console</h1>
<p>Operator-only, localhost-bound · Same commands and source of truth as the terminal demo</p>
<nav><a href="http://127.0.0.1:8501/">Workforce dashboard</a> · <a href="#walkthrough">Walkthrough</a></nav>
</header><main>
<section><h2>Operator authentication</h2>
<p class="muted">This console runs on the Docker host, not inside the isolated AI application. Copy the access token printed by the console launcher. The token stays in this tab's memory.</p>
<div class="bar"><input type="password" id="token" placeholder="Paste operator token" autocomplete="off"><button onclick="connect()">Unlock presenter checks</button></div>
<p class="small" id="authStatus">Locked · the AI application cannot invoke these privileged commands.</p></section>
<section><h2>What the comparison proves</h2>
<p><strong>BEFORE:</strong> a privileged synthetic HR backend can export employee-level rows directly, without Talon. <strong>RESET:</strong> only execution counters reset; no permissions change. <strong>AFTER:</strong> the separate AI app lacks HR DB and network access; Talon allows approved aggregates and denies exports.</p>
<p class="muted">Docker isolation is not Talon policy. Operator commands do not travel through Talon unless they explicitly call its MCP endpoint. No real employee records are involved.</p></section>
<div id="walkthrough"></div>
</main><script>
var operatorToken='', catalog=[],busy=false;
function elem(name,text,cls){var e=document.createElement(name);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;}
async function connect(){
operatorToken=document.getElementById('token').value.trim();
try{
const response=await fetch('/api/actions',{headers:{'X-Presenter-Token':operatorToken}});
if(!response.ok)throw Error('Token rejected (HTTP '+response.status+')');
catalog=await response.json();document.getElementById('authStatus').textContent='Unlocked · run individual checks in any order. They operate on the real running services.';
document.getElementById('token').value='';
draw();
}catch(error){operatorToken='';document.getElementById('authStatus').textContent=error.message;}
}
function draw(){
const main=document.getElementById('walkthrough');main.replaceChildren();
const phases=[...new Set(catalog.map(a=>a.phase))];
for(const phase of phases){
const section=elem('section');section.append(elem('h2',phase));
const grid=elem('div',undefined,'grid');
for(const action of catalog.filter(a=>a.phase===phase)){
const card=elem('div',undefined,'item');card.append(elem('h3',action.title));
card.append(elem('div','Exact shell command (dc is Docker Compose alias):','label'));
const command=elem('pre',action.command);card.append(command);
const toolbar=elem('div',undefined,'bar');
const button=elem('button','Run actual check');
const copy=elem('button','Copy command','secondary');
copy.onclick=()=>navigator.clipboard.writeText(action.command);
const status=elem('span','Not run','small');
toolbar.append(button,copy,status);card.append(toolbar);
const output=elem('pre','No execution yet');card.append(output);
button.onclick=async()=>{
if(busy)return;busy=true;
for(const b of main.querySelectorAll('button'))b.disabled=true;
status.textContent='Executing...';
try{
const response=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json','X-Presenter-Token':operatorToken},
body:JSON.stringify({action:action.id})});
const result=await response.json();
if(!response.ok)throw Error(result.error||'Operator request failed');
status.textContent=result.ok?'PASS · exit 0':'FAILED · exit '+result.exit_code;
status.className=result.ok?'pass':'fail';
output.textContent=(result.stdout||'')+(result.stderr?'\nSTDERR:\n'+result.stderr:'')||'(no stdout)';
}catch(error){status.textContent='FAILED';status.className='fail';output.textContent=error.message;}
busy=false;for(const b of main.querySelectorAll('button'))b.disabled=false;
};
grid.append(card);
}section.append(grid);main.append(section);
}
}
</script></body></html>'''


def handler_factory(token):
    class PresenterHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass
        def _send(self, status, body, html=False):
            raw = (body if isinstance(body, str) else json.dumps(body)).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; connect-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(raw)
        def _authorized(self):
            supplied = self.headers.get("X-Presenter-Token", "")
            return bool(supplied and secrets.compare_digest(supplied, token))
        def _local_origin(self):
            origin = self.headers.get("Origin")
            return origin in (None, "http://127.0.0.1:8502", "http://localhost:8502")
        def do_GET(self):
            if self.path == "/":
                return self._send(200, PAGE, True)
            if self.path == "/api/actions":
                if not self._authorized():
                    return self._send(401, {"error": "Operator token required"})
                return self._send(200, [{"id": a, "phase": b, "title": c, "command": d}
                                        for a,b,c,d in ACTIONS])
            return self._send(404, {"error": "Not found"})
        def do_POST(self):
            if self.path != "/api/run":
                return self._send(404, {"error": "Not found"})
            if not self._authorized() or not self._local_origin():
                return self._send(403, {"error": "Operator token or same-origin browser context required"})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self._send(415, {"error": "JSON required"})
            size = int(self.headers.get("Content-Length", "0"))
            if size < 2 or size > 256:
                return self._send(400, {"error": "Bad request size"})
            try:
                payload = json.loads(self.rfile.read(size))
                action = payload.get("action") if isinstance(payload, dict) else None
                if action not in CATALOG:
                    return self._send(400, {"error": "Unrecognized action"})
                result = perform(action)
                return self._send(200, result)
            except (ValueError, RuntimeError, OSError) as exc:
                return self._send(503, {"error": str(exc)[:600]})
    return PresenterHandler


def main():
    parser = argparse.ArgumentParser(description="Synthetic People Analytics operator-only demo")
    opts = parser.add_mutually_exclusive_group(required=True)
    opts.add_argument("--serve", action="store_true", help="localhost-only protected UI on port 8502")
    opts.add_argument("--action", choices=tuple(CATALOG), help="Run exactly one checked Docker command")
    opts.add_argument("--list", action="store_true", help="Show mirrored UI/CLI actions")
    args = parser.parse_args()
    if args.list:
        for a,phase,title,cmd in ACTIONS:
            print(f"{phase}: {a}\n  {title}\n  {cmd}")
    elif args.action:
        result = perform(args.action)
        print(result["stdout"], end="")
        if result["stderr"]:
            print(result["stderr"], end="", file=__import__("sys").stderr)
        raise SystemExit(0 if result["ok"] else result["exit_code"] or 1)
    else:
        _environment()
        token = secrets.token_urlsafe(24)
        print("PRESENTER CONTROL CONSOLE: http://127.0.0.1:8502", flush=True)
        print("OPERATOR TOKEN (paste into console; never give to AI): " + token, flush=True)
        print("Host-local, token protected; privileged Docker actions are not exposed to the AI app.", flush=True)
        ThreadingHTTPServer(("127.0.0.1", 8502), handler_factory(token)).serve_forever()


if __name__ == "__main__":
    main()
