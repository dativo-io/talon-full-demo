#!/usr/bin/env python3
import json, os, sys, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT=int(os.environ.get('MOCK_TALON_PORT','18080'))
LOG=Path(os.environ.get('MOCK_TALON_LOG','/tmp/mock-talon.jsonl'))
# Optional session-budget simulation. When MOCK_TALON_SESSION_BUDGET_REQUESTS
# is set to a positive integer N, requests N+1 onward for the same
# X-Talon-Session-ID are denied with HTTP 403 and a body containing
# "session_budget_exceeded" -- mirroring real Talon's contract
# (internal/gateway/session_budget_test.go: 403 + session_budget_exceeded).
# The denied request is logged with cost_usd 0 and denied=true: a budget
# denial never incurs simulated provider cost. Unset (default) = no budgets,
# preserving the original always-allow behavior.
BUDGET=int(os.environ.get('MOCK_TALON_SESSION_BUDGET_REQUESTS','0') or '0')
_sessions={}
_lock=threading.Lock()

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
        denied=False
        if BUDGET>0:
            session=rec['headers'].get('x-talon-session-id','')
            with _lock:
                count=_sessions.get(session,0)+1
                _sessions[session]=count
            denied=count>BUDGET
        rec['denied']=denied
        rec['cost_usd']=0.0 if denied else 0.0001
        LOG.parent.mkdir(parents=True,exist_ok=True)
        with LOG.open('a') as f: f.write(json.dumps(rec)+'\n')
        if denied:
            self._write(403,{'error':{'message':'denied: session_budget_exceeded: accrued session spend plus the pre-request estimate exceeds max_session_cost (soft cap; see Talon LIMITATIONS.md)','type':'session_budget_exceeded','code':'session_budget_exceeded'}})
            return
        if '/anthropic/' in self.path:
            self._write(200,{'id':'msg_demo','type':'message','role':'assistant','content':[{'type':'text','text':'Synthetic compliance summary.'}],'model':'claude-demo','stop_reason':'end_turn','usage':{'input_tokens':20,'output_tokens':8}})
        else:
            self._write(200,{'id':'chatcmpl-demo','object':'chat.completion','model':'gpt-demo','choices':[{'index':0,'message':{'role':'assistant','content':'We received your synthetic refund request and are reviewing it.'},'finish_reason':'stop'}],'usage':{'prompt_tokens':20,'completion_tokens':12,'total_tokens':32}})

if __name__=='__main__':
    print(f'mock talon listening on {PORT}', flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),H).serve_forever()
