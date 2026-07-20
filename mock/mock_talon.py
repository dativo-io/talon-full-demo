#!/usr/bin/env python3
import json, os, sys, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

PORT=int(os.environ.get('MOCK_TALON_PORT','18080'))
LOG=Path(os.environ.get('MOCK_TALON_LOG','/tmp/mock-talon.jsonl'))

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
        LOG.parent.mkdir(parents=True,exist_ok=True)
        with LOG.open('a') as f: f.write(json.dumps(rec)+'\n')
        if '/anthropic/' in self.path:
            self._write(200,{'id':'msg_demo','type':'message','role':'assistant','content':[{'type':'text','text':'Synthetic compliance summary.'}],'model':'claude-demo','stop_reason':'end_turn','usage':{'input_tokens':20,'output_tokens':8}})
        else:
            self._write(200,{'id':'chatcmpl-demo','object':'chat.completion','model':'gpt-demo','choices':[{'index':0,'message':{'role':'assistant','content':'We received your synthetic refund request and are reviewing it.'},'finish_reason':'stop'}],'usage':{'prompt_tokens':20,'completion_tokens':12,'total_tokens':32}})

if __name__=='__main__':
    print(f'mock talon listening on {PORT}', flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),H).serve_forever()
