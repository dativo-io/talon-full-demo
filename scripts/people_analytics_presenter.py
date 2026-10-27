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
import re
from urllib.parse import urlparse, parse_qs
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
    ("warehouse_info", "Setup", "Inspect embedded DuckDB schema and synthetic row count",
     "dc exec -T hr-server python3 verify_isolation.py warehouse-info"),
    ("compose_spec", "Setup", "View actual Docker Compose services and network mounts",
     "cat cases/people-analytics-copilot/compose.isolated.yaml"),
    ("bootstrap_logs", "Setup", "Show Talon scaffold, validation and key setup log",
     "dc logs --tail 70 talon-init"),
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
    ("gateway_policy", "4 · Effective boundaries", "Inspect LIVE gateway provider configuration",
     "dc exec -T talon-mcp cat /case/gateway.talon.yaml"),
    ("validate_policy", "4 · Effective boundaries", "Validate active Talon config",
     "dc exec -T talon-mcp talon validate"),
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

# Host-only log readers: no generic Docker exec, shell or arbitrary service names.
LOG_SOURCES = {
    "talon-mcp": "Talon MCP proxy — live process output",
    "talon-gateway": "Talon LLM gateway — LIVE profile only",
    "talon-init": "Talon scaffold / validation / vault initialization",
    "ui": "AI app — structured MCP + model gateway exchanges",
    "trace": "AI request/response trace — app-observed, not provider wire capture",
    "hr-server": "Private HR backend — actual dispatched operations",
    "dashboard": "Aggregate dashboard API",
}
_REDACTIONS = (
    (re.compile(r"\bBearer\s+\S+", re.I), "Bearer [redacted]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"), "[redacted-api-key]"),
    (re.compile(r"(?i)(?:TALON_SECRETS_KEY|TALON_SIGNING_KEY|TALON_ADMIN_KEY|HR_DEMO_OPENAI_KEY|OPENAI_API_KEY)\s*[:=]\s*\S+"),
     "[redacted-environment-secret]"),
)

def read_service_logs(source):
    """Bounded log snapshots, live via short UI polling. Never follow indefinitely."""
    if source not in LOG_SOURCES:
        raise ValueError("Unrecognized log source")
    _environment()
    service = "ui" if source == "trace" else source
    command = _dc_prefix() + ["logs", "--no-color", "--timestamps", "--tail", "110", service]
    out = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=8,
                         env=_environment(), check=False)
    if out.returncode:
        # Gateway profile may not be started yet.
        return {"source": source, "available": False, "lines": "",
                "explanation": "Service is not running or logs unavailable. Start LIVE mode for talon-gateway."}
    log = out.stdout
    if source == "trace":
        log = "\n".join(line for line in log.splitlines() if "HR_AI_TRACE " in line)
    for pattern, replacement in _REDACTIONS:
        log = pattern.sub(replacement, log)
    log = log[-28000:]
    return {"source": source, "available": True, "lines": log,
            "explanation": ("Application-observed request/response summaries through Talon. "
                            "These are NOT a packet capture of OpenAI HTTPS; provider is real ONLY in LIVE mode."
                            if source == "trace" else LOG_SOURCES[source])}


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
    if action == "compose_spec":
        return ["cat", str(COMPOSE)]
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
    if action == "bootstrap_logs":
        return _dc_prefix() + ["logs", "--tail", "70", "talon-init"]
    if action == "validate_policy":
        return _dc_prefix() + ["exec", "-T", "talon-mcp", "talon", "validate"]
    if action in ("agent_policy", "proxy_policy", "gateway_policy"):
        name = {"agent_policy": "/state/agent.talon.yaml",
                "proxy_policy": "/case/proxy.isolated.talon.yaml",
                "gateway_policy": "/case/gateway.talon.yaml"}[action]
        return _dc_prefix() + ["exec", "-T", "talon-mcp", "cat", name]
    if action in ("evidence_export", "evidence_verify"):
        verb = (["audit", "export", "--format", "signed-json",
                 "--session", SESSION, "--output", EVIDENCE_FILE]
                if action == "evidence_export"
                else ["audit", "verify", "--file", EVIDENCE_FILE])
        return _dc_prefix() + ["exec", "-T", "talon-mcp", "talon"] + verb
    service = ("hr-server" if action in ("before", "counters", "reset", "backend_counts", "warehouse_info")
               else "ui")
    cli_action = {"backend_counts": "backend-counts", "warehouse_info": "warehouse-info"}.get(action, action)
    return _dc_prefix() + ["exec", "-T", service, "python3",
                           "verify_isolation.py", cli_action]


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
<title>People Analytics · Operator Proof Console</title>
<style>
*{box-sizing:border-box}body{font:15px/1.5 system-ui,-apple-system,Segoe UI,Arial;background:#f4f7fb;color:#213249;margin:0}
header{background:#142e53;color:white;padding:22px max(24px,calc((100vw - 1120px)/2))}
header h1{font-size:25px;margin:0 0 4px}header p{margin:4px 0;color:#d3e0ef}
header a{color:#d8e9ff}main{max-width:1120px;margin:auto;padding:24px}
section{background:white;border:1px solid #d9e4ef;border-radius:14px;padding:22px;margin-bottom:18px}
h2{font-size:20px;margin:0 0 8px}h3{font-size:16px;margin:0 0 6px}
p{margin:7px 0 14px}.muted{font-size:13px;color:#63738a}
button{border:0;background:#155db1;color:white;border-radius:8px;padding:10px 15px;cursor:pointer;font:inherit}
button:focus-visible,input:focus-visible,summary:focus-visible{outline:3px solid #e5a32d;outline-offset:2px}
button:disabled{opacity:.5;cursor:wait}
select{padding:9px;border:1px solid #b5c5d8;border-radius:7px;max-width:100%;background:white;color:inherit}.secondary{background:#e8f0fb;color:#144e96}
input{padding:10px;border:1px solid #b5c5d8;border-radius:8px;max-width:400px;width:100%;font:inherit}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:12px}
.action{border:1px solid #dce6f0;border-radius:10px;padding:15px;min-width:0}
.action h3{margin-top:0}.action header{background:none;color:inherit;padding:0}
.line{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.small{font-size:12px;color:#5a6c85}.tag{font-size:12px;display:inline-block;border-radius:20px;background:#e7eef9;padding:4px 9px}
.ok{color:#176344;font-weight:600}.bad{color:#a62d35;font-weight:600}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;border:1px solid #e4e9f1;border-radius:9px;padding:12px;font:12px/1.6 ui-monospace,SFMono-Regular,monospace;max-height:400px;overflow:auto}
details{margin-top:11px}summary{cursor:pointer;color:#165a9d;font-weight:600}
#progress{background:#e9eff7;height:10px;border-radius:9px;overflow:hidden;margin:12px 0}
#progressFill{background:#17866f;height:100%;width:0;transition:width .25s}
.phase{border-left:5px solid #ccdbed}.phase[data-complete="true"]{border-left-color:#17866f}
.phaseTitle{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.phaseNote{background:#f3f7fc;border-radius:8px;padding:12px;color:#445c77;font-size:14px}
.warning{border-left:4px solid #bd7340;background:#fff6eb;padding:11px 13px;margin:12px 0}
#walkthrough[hidden],#overview[hidden]{display:none}
@media(max-width:650px){main{padding:12px}section{padding:16px}.cards{grid-template-columns:1fr}}
</style></head><body>
<header><h1>People Analytics · Operator Proof Console</h1>
<p>Seven-stage evidence walkthrough · Synthetic HR data · Real Docker, DuckDB and Talon</p>
<nav><a href="http://127.0.0.1:8501/">Open workforce dashboard</a> · <a href="#guide">What this proves</a></nav></header>
<main>
<section id="auth"><h2>1. Unlock operator checks</h2>
<p class="muted">Runs separately on the trusted Docker host, never inside the AI app. Use the one-time token printed by the console launcher. The token stays only in this browser tab's memory.</p>
<div class="line"><label for="token">Operator token</label><input type="password" id="token" placeholder="Paste token" autocomplete="off"><button id="connect" onclick="connect()">Unlock</button></div>
<p id="authStatus" role="status" aria-live="polite" class="small">Locked. No privileged actions are available until authentication.</p>
</section>
<section id="guide"><h2>2. Understand the claim</h2>
<p><strong>Before:</strong> a privileged HR process calls employee export directly without Talon. <strong>Reset:</strong> only synthetic execution counters reset. <strong>After:</strong> a separate AI app has no HR data volume or direct backend network path; Talon allows safe aggregates and blocks export through its MCP endpoint.</p>
<div class="warning"><strong>No runtime switch:</strong> this compares two workloads with different access, not a live agent migration. Docker enforces network/volume separation; Talon enforces routed model/tool policy. Guided mode is not a real LLM.</div>
<p class="muted">Each check reveals the corresponding shell command, its actual exit code and stdout/stderr. The console never fabricates approval receipts, HR counts or evidence validation.</p></section>
<section id="overview" hidden>
<h2>3. Run the seven proof stages</h2>
<p class="muted">Follow the stages in order for an auditable story. Nothing runs automatically. Individual diagnostics can be repeated; rerunning the privileged BEFORE export increases its counter. Reset is a deliberate separate action.</p>
<div id="progress" role="progressbar" aria-label="Checks completed" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><div id="progressFill"></div></div>
<p id="progressText" class="small" aria-live="polite">No checks run yet</p>
<div class="line"><button class="secondary" onclick="goNext()">Go to next incomplete check</button><button class="secondary" onclick="copySetup()">Copy shell setup</button></div>
<details><summary>Terminal equivalent: initialize the dc shortcut</summary>
<pre id="shellSetup"># Run from the demo repository root:
export CASE="$PWD/cases/people-analytics-copilot"
dc() {
  docker compose -f "$CASE/compose.isolated.yaml" \
    --env-file "$CASE/.state/isolated.env" "$@"
}</pre>
<p class="small">The shell alias is needed for commands displayed below. The browser uses an explicit allowlist and does not execute shell strings supplied by the user.</p>
</details>
</section>
<section id="technicalLab" hidden>
<h2>4. Technical inspection — see the system working</h2>
<p>Inspect <strong>actual Docker services</strong>, Talon configuration, bootstrap logs and real request/response traces. This does not create mock answers or turn on unrestricted logging. Use this panel while performing a step in the workforce UI or proof console.</p>
<div class="warning"><strong>Provider truth:</strong> the default GUIDED mode has no LLM request. The LIVE gateway sends calls to an external provider, but requires a real API key and an independently passed smoke test. Traces marked <code>llm.gateway.*</code> are observed by the application at Talon's gateway boundary—not HTTPS packets captured inside OpenAI. Model content is hidden unless synthetic-only payload previews were explicitly enabled when starting LIVE.</div>
<details open><summary>Declared runtime topology (verify with the live commands below)</summary>
<pre>Workforce UI / AI container [app_net, no HR data mount]
  |-- charts ----------> Aggregate API ------> DuckDB volume (read-only)
  |-- guided MCP ------> Talon MCP proxy ------> HR service [private_hr]
  |-- LIVE model ------> Talon LLM gateway ---> OpenAI (external, only with key)
                             |
                        tool selected by model
                             |
                        Talon MCP proxy ------> HR service --> DuckDB

Talon init creates/validates shared state; both Talon processes use it.
Only Talon MCP bridges app_net to private_hr. Tool policy is enforced by Talon.
</pre>
<p class="small">This is the declared topology, not proof by itself. Check Compose config, live Docker networks, volumes and tool receipts using the actions below.</p>
</details>
<div class="line">
<label for="logSource">Running service / event source</label>
<select id="logSource" aria-label="Running service logs">
<option value="talon-init">Talon bootstrap / configuration creation</option>
<option value="talon-mcp">Talon MCP live logs</option>
<option value="talon-gateway">Talon LLM gateway (LIVE only)</option>
<option value="trace">AI request / response exchanges (structured trace)</option>
<option value="ui">AI application raw logs</option>
<option value="hr-server">Private HR backend execution logs</option>
<option value="dashboard">DuckDB aggregate dashboard logs</option>
</select>
<button id="refreshLogs" class="secondary" onclick="refreshLogs()">Refresh logs</button>
<label class="small"><input id="autoRefresh" type="checkbox" onchange="toggleAutoRefresh(this.checked)"> Auto-refresh ~2s</label>
</div>
<p id="logStatus" class="small" role="status" aria-live="polite">Unlock to inspect real process logs.</p>
<pre id="liveLogs" style="min-height:180px">Select a source and click Refresh logs.</pre>
<details><summary>Where Talon configuration actually comes from</summary>
<p>The <strong>talon-init</strong> container runs Talon scaffold, copies the reviewed <code>agent.talon.yaml</code>, validates it, and writes demo keys to Talon's encrypted vault. The Talon MCP and optional LLM gateway containers use the same mounted Talon state. These are real files/processes, not a policy simulated in this page.</p>
<p>Select the fixed actions <strong>Inspect agent allowlist</strong>, <strong>Inspect MCP proxy allow/deny policy</strong>, <strong>Inspect LIVE gateway provider configuration</strong>, and <strong>Validate active Talon config</strong> in Stage 4. Each action shows the exact command and its stdout. The policy is Git-managed: editing it is a separate, explicit redeploy, not a secret UI toggle.</p>
</details>
</section>
<div id="walkthrough" hidden></div>
</main>
<script>
let operatorToken='',catalog=[],busy=false,results={};
const notes={
'Setup':{why:'Inspect actual containers and Talon scaffold/validation logs before trusting any outcome.',expect:'HR, dashboard, Talon and AI app containers are running.'},
'1 · Direct access':{why:'Demonstrate the problem: a trusted HR process has more authority than a reporting AI use case should inherit.',expect:'An actual synthetic employee export returns a name and salary; the HR backend counter rises.'},
'2 · Measurement reset':{why:'Start the AFTER measurement at zero, without claiming that privileges were changed.',expect:'All synthetic HR counters reset. The prior direct call still happened.'},
'3 · Deployment perimeter':{why:'Prove the restricted AI workload cannot directly reach raw HR data, while the dashboard still works.',expect:'UI network and mounts exclude the private HR backend and DuckDB file; the live boundary check succeeds.'},
'4 · Effective boundaries':{why:'Inspect actual configured agent/proxy permissions and the tools offered at runtime.',expect:'Only three aggregate HR tools appear. Sensitive export is absent from discovery.'},
'5 · Authorized analytics':{why:'Execute an approved aggregate through Talon and show the committed allow receipt.',expect:'DuckDB results and a real signed evidence ID; no individual employee rows.'},
'6 · Forbidden operation':{why:'Deliberately force an employee export through Talon, then independently check the backend.',expect:'A pre-dispatch Talon denial and zero export executions since the reset.'},
'7 · Independent evidence':{why:'Export the actual Talon session and independently validate signatures.',expect:'No invalid or unsigned records. The BEFORE direct call is intentionally absent.'}
};
const risks={before:'This actually executes a direct synthetic employee export outside Talon. It will increase the BEFORE export counter.',reset:'This clears demonstration counters only. It does not undo the BEFORE execution or change access privileges.'};
function el(tag,text,cls){const v=document.createElement(tag);if(text!==undefined)v.textContent=text;if(cls)v.className=cls;return v;}
function announce(s,ok){const n=document.getElementById('authStatus');n.textContent=s;n.className=ok?'ok':'bad';}
async function connect(){
const candidate=document.getElementById('token').value.trim();
if(!candidate){announce('Enter the operator token from the host terminal.',false);return;}
try{const response=await fetch('/api/actions',{headers:{'X-Presenter-Token':candidate}});
 if(!response.ok)throw Error('Authentication failed (HTTP '+response.status+').');
 catalog=await response.json();operatorToken=candidate;results={};
 document.getElementById('token').value='';document.getElementById('overview').hidden=false;
 document.getElementById('walkthrough').hidden=false;
 document.getElementById('technicalLab').hidden=false;announce('Unlocked. Commands run only when you select Run.',true);draw();
}catch(error){operatorToken='';announce(error.message,false);}
}
function copyText(s){
 if(navigator.clipboard && navigator.clipboard.writeText){return navigator.clipboard.writeText(s);}
 const input=document.createElement('textarea');input.value=s;document.body.append(input);input.select();
 document.execCommand('copy');input.remove();return Promise.resolve();
}
function copySetup(){copyText(document.getElementById('shellSetup').textContent);}
let logTimer=null,logBusy=false;
async function refreshLogs(){
 if(!operatorToken || logBusy) return;
 logBusy=true;
 const source=document.getElementById('logSource').value;
 const state=document.getElementById('logStatus');
 try {
   const r=await fetch('/api/logs?source='+encodeURIComponent(source),{
     headers:{'X-Presenter-Token':operatorToken}
   });
   const info=await r.json();
   if(!r.ok)throw Error(info.error||'Log request failed');
   state.textContent=info.explanation+(info.available?' · live snapshot':' · not running');
   document.getElementById('liveLogs').textContent=
     info.lines || (info.available?'No matching events yet. Trigger a real UI action.':'Service not started.');
 } catch(error){
   state.textContent='Log inspection failed: '+error.message;
 }
 logBusy=false;
}
function toggleAutoRefresh(enabled){
 if(logTimer){clearInterval(logTimer);logTimer=null;}
 if(enabled){refreshLogs();logTimer=setInterval(()=>{
   if(document.visibilityState==='visible')refreshLogs();
 },2200);}
}

function updateProgress(){
const complete=Object.keys(results).filter(k=>results[k]===true).length;
const pct=catalog.length?Math.round(100*complete/catalog.length):0;
document.getElementById('progressFill').style.width=pct+'%';
document.getElementById('progress').setAttribute('aria-valuenow',pct);
document.getElementById('progressText').textContent=complete+' / '+catalog.length+' checks succeeded in this browser tab; failures remain visible. This is UI progress, not signed evidence.';
for(const section of document.querySelectorAll('.phase')) {
const ids=(section.dataset.actions||'').split(',');
section.dataset.complete=ids.every(id=>results[id]===true)?'true':'false';
}
}
function goNext(){
const next=catalog.find(x=>results[x.id]!==true);
if(next){const target=document.getElementById('action-'+next.id);if(target)target.scrollIntoView({behavior:'smooth',block:'center'});}
}
function draw(){
const dest=document.getElementById('walkthrough');dest.replaceChildren();
const phases=[...new Set(catalog.map(a=>a.phase))];
for(const phase of phases){
 const group=catalog.filter(a=>a.phase===phase),note=notes[phase]||{};
 const section=el('section',undefined,'phase');section.dataset.actions=group.map(a=>a.id).join(',');
 const top=el('div',undefined,'phaseTitle');top.append(el('h2',phase));
 top.append(el('span',group.length+' individual checks','tag'));section.append(top);
 section.append(el('p',note.why||'Run the real check.','muted'));
 section.append(el('p','Expected: '+(note.expect||'See command output.'),'phaseNote'));
 const cards=el('div',undefined,'cards');
 for(const a of group){
  const card=el('article',undefined,'action');card.id='action-'+a.id;
  card.append(el('h3',a.title));
  if(risks[a.id])card.append(el('p',risks[a.id],'warning'));
  const commands=el('details');commands.append(el('summary','View exact terminal command'));
  commands.append(el('pre',a.command));card.append(commands);
  const controls=el('div',undefined,'line');
  const run=el('button','Run check');run.type='button';
  const copy=el('button','Copy command','secondary');copy.type='button';
  copy.onclick=()=>copyText(a.command).then(()=>{copy.textContent='Copied';setTimeout(()=>copy.textContent='Copy command',1400);}).catch(()=>{copy.textContent='Copy manually from above';commands.open=true;});
  const state=el('span','Not run','small');state.setAttribute('role','status');
  controls.append(run,copy,state);card.append(controls);
  const outputWrap=el('details');outputWrap.open=true;outputWrap.append(el('summary','Actual process output (not run yet)'));
  const output=el('pre','No execution yet');output.setAttribute('aria-live','polite');outputWrap.append(output);
  card.append(outputWrap);
  run.onclick=async()=>{
   if(busy)return;
   if(risks[a.id]&&!window.confirm(risks[a.id]+' Continue?'))return;
   busy=true;for(const b of dest.querySelectorAll('button'))b.disabled=true;
   state.textContent='Executing…';state.className='small';
   try{
    const response=await fetch('/api/run',{method:'POST',headers:{'Content-Type':'application/json','X-Presenter-Token':operatorToken},body:JSON.stringify({action:a.id})});
    const result=await response.json();
    if(!response.ok)throw Error(result.error||'Operator request failed');
    results[a.id]=result.ok===true;updateProgress();
    state.textContent=result.ok?'Exit 0 · command succeeded':'Exit '+result.exit_code+' · failed';
    state.className=result.ok?'ok':'bad';
    output.textContent=('Exit code: '+result.exit_code+'\n'+(result.stdout||'')+(result.stderr?'\nSTDERR:\n'+result.stderr:''))||'No output';
   }catch(error){results[a.id]=false;updateProgress();state.textContent='Request failed';state.className='bad';output.textContent=error.message;}
   busy=false;for(const b of dest.querySelectorAll('button'))b.disabled=false;
  };
  cards.append(card);
 }
 section.append(cards);dest.append(section);
}
updateProgress();
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
            route = urlparse(self.path)
            if route.path == "/api/logs":
                if not self._authorized() or not self._local_origin():
                    return self._send(401, {"error": "Operator token required"})
                args = parse_qs(route.query)
                source = args.get("source", [""])[0]
                if source not in LOG_SOURCES:
                    return self._send(400, {"error": "Unknown fixed log source"})
                try:
                    return self._send(200, read_service_logs(source))
                except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
                    return self._send(503, {"error": str(exc)[:200]})
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
