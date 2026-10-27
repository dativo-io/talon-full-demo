"""Standalone web interface for the synthetic People Analytics Copilot."""
HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Workforce Intelligence · Talon</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f3f6fa;color:#1b2a3f;font:15px system-ui,-apple-system,Segoe UI,Arial}
header{background:#142e53;color:white;padding:22px max(calc((100vw - 1460px)/2),24px)}
header h1{font-size:24px;margin:0 0 5px}header p{color:#b5cae7;font-size:13px;margin:0}
.shell{max-width:1460px;margin:auto;padding:22px;display:grid;grid-template-columns:minmax(0,1.5fr) minmax(340px,0.9fr);gap:20px}
.panel{background:white;border:1px solid #dce5ee;border-radius:14px;box-shadow:0 2px 6px #15274306;padding:22px}
.panel h2{margin:0 0 8px;font-size:18px}.muted{color:#63768e;font-size:13px}
aside{display:flex;flex-direction:column;gap:18px}button{padding:11px 15px;border:0;border-radius:8px;color:white;background:#155db1;cursor:pointer;font:inherit}
button:disabled{opacity:.6;cursor:wait}.danger{background:#9d3737}.secondary{color:#155db1;background:#e7f0fc}
textarea{width:100%;min-height:92px;border:1px solid #bccbe0;border-radius:9px;padding:12px;margin:10px 0 6px;font:inherit}
select{padding:8px;border:1px solid #bfccdb;border-radius:7px;font:inherit}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px ui-monospace,SFMono-Regular,monospace;line-height:1.5}
.answer{padding:14px;background:#f1f6fd;border-radius:10px;min-height:110px}
.details{background:#f9fafc;padding:12px;border:1px solid #e4e9ef;border-radius:8px}
.pill{display:inline-block;padding:5px 9px;border-radius:12px;background:#dcebea;color:#1c6356;font-size:12px}
iframe{border:0;width:100%;height:830px;display:block;margin-top:12px}
.smallbuttons{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0 4px}
footer{max-width:1460px;margin:auto;padding:8px 22px 26px;color:#6a7c90;font-size:12px}
@media(max-width:900px){.shell{grid-template-columns:1fr}header{padding:20px}iframe{height:850px}}
</style></head>
<body><header><h1>Workforce Intelligence</h1><p>People Analytics · Synthetic HR warehouse · Governed AI with Dativo Talon</p>
<p style="margin-top:12px"><a href="http://127.0.0.1:8502/" target="_blank" rel="noopener noreferrer"
style="display:inline-block;background:#dceafb;color:#163b68;padding:10px 14px;border-radius:8px;text-decoration:none;font-weight:600">
Open the 7-stage presenter proof console</a>
<span style="font-size:12px;color:#c9d9eb">Operator-only, separately authenticated on localhost:8502 · Or run the equivalent shell commands</span></p></header>
<div style="max-width:1460px;margin:14px auto 0;padding:0 22px"><div class="panel" style="padding:14px 18px">
<strong>Explore this demonstration:</strong> <span class="muted">1. Filter workforce charts · 2. Ask an approved analytics question · 3. Force an export denial · 4. Open the <a href="http://127.0.0.1:8502/" target="_blank" rel="noopener noreferrer">independent operator proof console</a> to inspect backend counters and signed evidence.</span>
<div class="muted" style="margin-top:7px">The dashboard is an unprivileged business application. The operator console runs separately, requires authentication, and executes the exact same checks available by CLI. No actual employee data is used.</div>
</div></div>
<div class="shell"><section class="panel"><div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap">
<div><h2>Workforce overview</h2><span class="muted">12-month workforce and attrition trends — derived from fictional employee histories</span></div>
<label class="muted">Department <select id="department" onchange="loadDashboard()"><option value="">All departments</option></select></label></div>
<iframe id="charts" title="Workforce analytics charts" src="/charts"></iframe></section>
<aside><section class="panel"><div style="display:flex;justify-content:space-between;gap:8px;align-items:center">
<h2>Ask Workforce AI</h2><span class="pill" id="mode">Connecting...</span></div>
<p class="muted">Ask questions about attrition, workforce size, and tenure. Only governed MCP tools are available.</p>
<div class="smallbuttons"><button class="secondary" onclick="suggest('Compare department attrition trends over the last six months')">Attrition</button>
<button class="secondary" onclick="suggest('Summarize headcount by department')">Headcount</button>
<button class="secondary" onclick="suggest('Compare tenure bands across departments')">Tenure</button></div>
<textarea id="query">Which departments have the highest attrition over the last six months?</textarea>
<button id="askbutton" onclick="ask()">Ask assistant</button>
<p class="muted" id="respondmode"></p><p class="muted" id="sessionLabel">Session: initializing...</p><pre id="answer" class="answer">Ask a question to start.</pre>
</section><section class="panel"><h2>Talon governance</h2>
<p class="muted">For the complete before/after trust demonstration, use the
<a href="http://127.0.0.1:8502/" target="_blank" rel="noopener noreferrer">operator proof console</a>
or its exact Docker Compose terminal commands. The isolated AI app cannot execute privileged baseline tests itself.</p>
<p class="muted">Tools discovered through Talon; evidence shown from actual routed calls, not fabricated UI events.</p>
<pre id="tools" class="details">No tools discovered yet</pre>
<pre id="receipt" class="details">No receipt yet</pre>
<p class="muted">Operator-only negative test — not an AI-selected action:</p>
<button class="danger" onclick="probe()">Force a forbidden export through Talon</button>
<pre id="probe"></pre><button id="countsButton" class="secondary" onclick="counts()">Refresh upstream execution counts</button>
<pre id="counters" class="details">Not loaded</pre></section></aside></div>
<footer>Fictional HR records only · No prediction of individual attrition risk · Direct database access outside Talon is not covered · Signed evidence must be verified with Talon CLI.</footer>
<script>
const el=x=>document.getElementById(x), session='hr-demo-'+Math.random().toString(36).slice(2);
el('sessionLabel').textContent='AI app session: '+session+' (different from operator proof session)';
function suggest(q){el('query').value=q}
function receipt(v){if(!v||!v.governance)return;let g=v.governance,e=g.evidence||{};
el('receipt').textContent='Decision: '+(g.decision||'unknown')+'\nCode: '+(g.code||'unknown')+'\nEvidence ID: '+(e.id||'none')+'\nCommitted: '+(e.committed===true);
}
async function api(path,body){let r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({session,...body})});let j=await r.json();if(!r.ok)throw Error(j.error||('HTTP '+r.status));return j}
async function loadDashboard(){
let d=el('department').value;
el('charts').src='/charts'+(d?'?department='+encodeURIComponent(d):'');
}
async function init(){try{
let info=await (await fetch('/api/dashboard')).json();
info.departments.forEach(d=>{let opt=document.createElement('option');opt.value=d;opt.textContent=d;el('department').append(opt)});
let mode=await (await fetch('/api/mode')).json();el('mode').textContent=mode.mode==='live'?'LIVE AI · TALON':'GUIDED · NO LLM';
await counts();
}catch(e){el('mode').textContent='SETUP REQUIRED';el('answer').textContent=e.message}}
async function ask(){el('askbutton').disabled=true;el('answer').textContent='Requesting governed analysis...';
el('receipt').textContent='No signed tool receipt from this request yet.';
try{let r=await api('/api/query',{query:el('query').value});el('answer').textContent=r.answer;
el('tools').textContent=r.tools.join('\n');el('respondmode').textContent=r.mode||'';
if(r.calls&&r.calls.length){el('receipt').textContent='Governed calls: '+r.calls.length;receipt(r.calls[r.calls.length-1])}
else receipt(r.tool)}catch(e){el('answer').textContent='Error: '+e.message}
el('askbutton').disabled=false;await counts()}
async function probe(){el('probe').textContent='Checking real Talon decision...';
el('receipt').textContent='Awaiting Talon denial receipt...';
try{let r=await api('/api/probe',{});el('probe').textContent=r.denied?'DENIED — not dispatched':'FAILED TO PROVE DENIAL';
receipt(r.tool)}catch(e){el('probe').textContent='Error: '+e.message}
await counts()}
async function counts(){try{let r=await fetch('/api/counters');el('counters').textContent=
JSON.stringify(await r.json(),null,2);
let data=JSON.parse(el('counters').textContent);
if(data.available===false){el('countsButton').hidden=true;
el('counters').textContent='Not available from this isolated app. Inspect independent execution counters in the authenticated operator proof console (port 8502).';}
}catch(e){el('counters').textContent='Counters unavailable: '+e.message}}

init();
</script></body></html>'''
