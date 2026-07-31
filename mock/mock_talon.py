#!/usr/bin/env python3
import json, os, sys, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT=int(os.environ.get('MOCK_TALON_PORT','18080'))
LOG=Path(os.environ.get('MOCK_TALON_LOG','/tmp/mock-talon.jsonl'))
# Optional session-budget simulation. When MOCK_TALON_SESSION_BUDGET_REQUESTS
# is set to a positive integer N, requests N+1 onward for the same
# X-Talon-Session-ID are denied with HTTP 403 and error.type set to
# "session_budget_exceeded" -- matching real Talon's gateway contract.
# The denied request is logged with cost_usd 0 and denied=true: a budget
# denial never incurs simulated provider cost. Unset (default) = no budgets,
# preserving the original always-allow behavior.
BUDGET=int(os.environ.get('MOCK_TALON_SESSION_BUDGET_REQUESTS','0') or '0')
# Optional destination-policy simulation used by the vendor-contract review.
# A matching provider path is denied before the mock provider response, with the
# same egress machine code real Talon exposes. Existing mock modes are unchanged.
DENY_PROVIDER=os.environ.get('MOCK_TALON_DENY_PROVIDER','').strip().lower()
# Optional gateway tool-schema denial used by the support-resolution workflow.
# A request declaring the named OpenAI/Anthropic tool is rejected before the
# mock provider response and carries zero simulated provider cost.
DENY_TOOL=os.environ.get('MOCK_TALON_DENY_TOOL','').strip()
_sessions={}
_lock=threading.Lock()

def tool_names(body):
    if not isinstance(body, dict):
        return []
    names=[]
    for tool in body.get('tools') or []:
        if not isinstance(tool, dict):
            continue
        name=tool.get('name')
        fn=tool.get('function')
        if not name and isinstance(fn, dict):
            name=fn.get('name')
        if isinstance(name, str) and name:
            names.append(name)
    return names

class H(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def log_message(self,*args): pass
    def _write(self,status,body,ctype='application/json'):
        data=body if isinstance(body,bytes) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type',ctype)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('X-Talon-Service','talon')
        self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if self.path=='/health': self._write(200,{'service':'talon'}); return
        self._write(404,{'error':'not found'})
    def do_POST(self):
        length=int(self.headers.get('content-length','0'))
        raw=self.rfile.read(length)
        rec={'path':self.path,'headers':{k.lower():v for k,v in self.headers.items()},'body_raw':raw.decode(errors='replace')}
        try: rec['body']=json.loads(raw or b'{}')
        except Exception: rec['body']=None
        rec['tool_names']=tool_names(rec['body'])
        denied=False
        denial_code=''
        if DENY_TOOL and DENY_TOOL in rec['tool_names']:
            denied=True
            denial_code='tool_governance_block'
        elif DENY_PROVIDER and f'/{DENY_PROVIDER}/' in self.path.lower():
            denied=True
            denial_code='egress_tier_destination_disallowed'
        elif BUDGET>0:
            session=rec['headers'].get('x-talon-session-id','')
            with _lock:
                count=_sessions.get(session,0)+1
                _sessions[session]=count
            denied=count>BUDGET
            if denied:
                denial_code='session_budget_exceeded'
        rec['denied']=denied
        rec['denial_code']=denial_code
        rec['cost_usd']=0.0 if denied else 0.0001
        LOG.parent.mkdir(parents=True,exist_ok=True)
        with LOG.open('a') as f: f.write(json.dumps(rec)+'\n')
        if denied and denial_code=='tool_governance_block':
            self._write(403,{'error':{'message':f'Request contains forbidden tools: [{DENY_TOOL}]','type':'policy_denied'}})
            return
        if denied and denial_code.startswith('egress_'):
            self._write(403,{'error':{'message':f'{denial_code}: confidential data may not egress to provider {DENY_PROVIDER}','type':denial_code,'code':denial_code}})
            return
        if denied:
            self._write(403,{'error':{'message':'session spend plus estimate exceeds limit','type':'session_budget_exceeded'}})
            return
        if '/anthropic/' in self.path:
            prompt=''
            try:
                prompt=str(rec.get('body',{}).get('messages',[{}])[0].get('content',''))
            except Exception:
                pass
            text='Synthetic vendor contract review. Material gaps: transfer mechanism, subprocessor notice, breach SLA, deletion periods, and unnamed model provider. Human review required.' if 'vendor contract' in prompt.lower() else 'Synthetic compliance summary.'
            self._write(200,{'id':'msg_demo','type':'message','role':'assistant','content':[{'type':'text','text':text}],'model':'claude-demo','stop_reason':'end_turn','usage':{'input_tokens':20,'output_tokens':8}})
        else:
            self._write(200,{'id':'chatcmpl-demo','object':'chat.completion','model':'gpt-demo','choices':[{'index':0,'message':{'role':'assistant','content':'We received your synthetic refund request and are reviewing it.'},'finish_reason':'stop'}],'usage':{'prompt_tokens':20,'completion_tokens':12,'total_tokens':32}})

if __name__=='__main__':
    print(f'mock talon listening on {PORT}', flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),H).serve_forever()
