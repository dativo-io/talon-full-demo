"""Single workforce application: SQL is tool-routed; AI is clearly labeled live or guided."""
HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Workforce Intelligence · Dativo Talon</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f3f6fa;color:#1b2a3f;font:15px system-ui,Arial}
header{background:#142e53;color:white;padding:22px max(calc((100vw - 1350px)/2),24px)}
h1{font-size:25px;margin:0 0 5px}header p{margin:0;color:#c3d5ea}
.shell{max-width:1350px;margin:auto;padding:20px;display:grid;grid-template-columns:minmax(0,1.4fr) minmax(340px,1fr);gap:18px}
.panel{background:white;border:1px solid #dce5ee;border-radius:12px;padding:20px;margin-bottom:18px}
h2{font-size:18px;margin:0 0 8px}.muted{color:#586c82;font-size:13px}
textarea{width:100%;min-height:110px;border:1px solid #aebfd1;border-radius:8px;padding:10px;font:13px/1.5 ui-monospace,monospace}
button{padding:9px 14px;background:#155db1;color:white;border:0;border-radius:7px;cursor:pointer;margin:7px 5px 7px 0}
button:disabled{opacity:.6}.secondary{background:#e8f1fb;color:#174b81}.danger{background:#963c3c}
pre{background:#f4f7fb;border:1px solid #e1e8f0;border-radius:7px;padding:12px;white-space:pre-wrap;overflow-wrap:anywhere;font:12px/1.5 ui-monospace,monospace}
iframe{border:0;width:100%;height:800px}select{padding:8px}
.pill{background:#dcebea;color:#246451;padding:4px 9px;border-radius:10px;font-size:12px}
footer{padding:10px 22px;color:#63768e;font-size:12px;max-width:1350px;margin:auto}
@media(max-width:900px){.shell{grid-template-columns:1fr}iframe{height:800px}}
</style></head><body>
<header><h1>Workforce Intelligence</h1><p>Fictional DuckDB workforce · Talon governs routed model and MCP actions</p></header>
<div class="shell">
<section class="panel"><h2>Workforce overview</h2>
<label class="muted">Department <select id="department" onchange="loadDashboard()"><option value="">All departments</option></select></label>
<p class="muted">Charts use a separate fixed aggregate dashboard API—not Talon.</p>
<iframe id="charts" title="Workforce analytics charts" src="/charts"></iframe></section>
<div>
<section class="panel"><h2>SQL workspace</h2>
<p class="muted">Submit SQL through the <code>hr_aggregate_sql</code> MCP tool. The HR backend accepts exactly two reviewed department aggregates, not arbitrary SQL.</p>
<button class="secondary" onclick="preset('all')">All employees</button><button class="secondary" onclick="preset('active')">Active employees</button>
<textarea id="sql" aria-label="SQL query">SELECT department, COUNT(*) AS employees
FROM employees
GROUP BY department
ORDER BY department;</textarea>
<button id="runSQL" onclick="runSQL()">Run SQL through Talon</button>
<pre id="sqlResult">No SQL executed yet.</pre></section>
<section class="panel"><h2>Workforce AI <span class="pill" id="mode">Connecting…</span></h2>
<p class="muted">Model inference runs only in LIVE mode. Guided mode executes MCP aggregates without a model.</p>
<textarea id="query" aria-label="AI question">Which departments have the highest attrition over the last six months?</textarea>
<button id="askbutton" onclick="ask()">Ask assistant</button>
<pre id="answer">No question asked.</pre></section>
<section class="panel"><h2>Policy boundary</h2>
<p class="muted">This is a deliberate operator probe, not an autonomous model request.</p>
<button class="danger" onclick="probe()">Attempt employee export through Talon</button>
<pre id="probe">No export attempted.</pre>
<p id="sessionLabel" class="muted"></p>
<pre id="receipt">No Talon receipt yet.</pre></section>
</div></div>
<footer>Fictional data only. Docker prevents direct HR access from this application. Talon controls intercepted calls; the HR backend validates SQL. Verify receipts with the Talon CLI.</footer>
<script>
const el=id=>document.getElementById(id);
const session='hr-demo-'+Math.random().toString(36).slice(2);
el('sessionLabel').textContent='Session: '+session;
const queries={
 all:'SELECT department, COUNT(*) AS employees\nFROM employees\nGROUP BY department\nORDER BY department;',
 active:'SELECT department, COUNT(*) AS active_headcount\nFROM employees\nWHERE termination_date IS NULL\nGROUP BY department\nORDER BY department;'
};
function preset(id){el('sql').value=queries[id]}
async function api(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify({session,...body})});const j=await r.json();if(!r.ok)throw Error(j.error||('HTTP '+r.status));return j}
function receipt(g){if(!g)return;const e=g.evidence||{};
el('receipt').textContent='Decision: '+(g.decision||'unknown')+'\nProvenance: '+(g.provenance||'unknown')+
'\nEvidence ID: '+(e.id||'none')+'\nCommitted: '+String(e.committed===true)}
async function runSQL(){el('runSQL').disabled=true;el('sqlResult').textContent='Submitting through Talon…';
try{const r=await api('/api/sql',{sql:el('sql').value});receipt(r.receipt);
el('sqlResult').textContent=(r.status==='executed'?'EXECUTED · HR-approved aggregate\n':
r.status==='talon_denied'?'DENIED · Talon blocked before dispatch\n':
'REJECTED · HR SQL validator (Talon allowed tool dispatch)\n')+
(r.data?JSON.stringify(r.data,null,2):(r.message||''));}
catch(e){el('sqlResult').textContent='Error: '+e.message}finally{el('runSQL').disabled=false}}
async function ask(){el('askbutton').disabled=true;el('answer').textContent='Requesting…';
try{const r=await api('/api/query',{query:el('query').value});el('answer').textContent=r.answer;
if(r.calls&&r.calls.length)receipt(r.calls[r.calls.length-1].governance);
else if(r.tool)receipt(r.tool.governance)}
catch(e){el('answer').textContent='Error: '+e.message}finally{el('askbutton').disabled=false}}
async function probe(){el('probe').textContent='Checking real Talon policy…';
try{const r=await api('/api/probe',{});el('probe').textContent=r.denied?'DENIED · not dispatched':'FAILED TO PROVE DENIAL';receipt(r.tool.governance)}
catch(e){el('probe').textContent='Error: '+e.message}}
async function loadDashboard(){const d=el('department').value;el('charts').src='/charts'+(d?'?department='+encodeURIComponent(d):'')}
async function init(){try{const r=await fetch('/api/dashboard');if(!r.ok)throw Error('Dashboard API unavailable');
const info=await r.json();info.departments.forEach(d=>{const o=document.createElement('option');o.value=d;o.textContent=d;el('department').append(o)});
const m=await (await fetch('/api/mode')).json();el('mode').textContent=m.mode==='live'?'LIVE · OPENAI VIA TALON':'GUIDED · NO LLM'}
catch(e){el('mode').textContent='SETUP REQUIRED';el('answer').textContent=e.message}}
init();
</script></body></html>'''
