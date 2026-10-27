#!/usr/bin/env python3
"""People Analytics Copilot: fictional HR MCP server and a thin Talon-routed UI.
Guided UI is deterministic; live AI runs through Talon. HR analytics use DuckDB.
"""
import argparse
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse, urlencode
from web_ui import HTML
from agent_runtime import run_live_chat
from runtime_trace import trace, previews_enabled
from urllib.request import Request, urlopen

VERSION = '2026-07-28'
EXT = 'io.dativo.talon/governance'
META = {'io.modelcontextprotocol/protocolVersion': VERSION,
        'io.modelcontextprotocol/clientInfo': {'name': 'hr-demo', 'version': '1.0'},
        'io.modelcontextprotocol/clientCapabilities': {}}
TOOLS = [
 {'name':'hr_attrition_summary','description':'Aggregated monthly attrition by department; no individuals.',
  'inputSchema':{'type':'object','properties':{'months':{'type':'integer','minimum':1,'maximum':12},
                'department':{'type':'string'}},'required':['months'],'additionalProperties':False}},
 {'name':'hr_headcount_summary','description':'Aggregate active headcount by department.',
  'inputSchema':{'type':'object','properties':{'department':{'type':'string'}},'additionalProperties':False}},
 {'name':'hr_tenure_summary','description':'Aggregate tenure bands and average tenure.',
  'inputSchema':{'type':'object','properties':{'department':{'type':'string'}},'additionalProperties':False}},
 {'name':'hr_employee_export','description':'Privileged export of employee names and salaries; forbidden.',
  'inputSchema':{'type':'object','properties':{'scope':{'type':'string'}},'required':['scope'],'additionalProperties':False}},
]
COUNTS = {tool['name']:0 for tool in TOOLS}
LOCK = threading.Lock()


def json_request(url, data, headers=None):
    req = Request(url, data=json.dumps(data).encode(), method='POST',
                  headers={'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream', **(headers or {})})
    try:
        with urlopen(req, timeout=30) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.loads(exc.read())


def mcp_call(base, key, method, tool=None, args=None, session='hr-demo-v1'):
    params = {'_meta': META}
    if tool is not None:
        params.update(name=tool, arguments=args or {})
    headers = {'MCP-Protocol-Version': VERSION, 'Mcp-Method': method, 'X-Talon-Session-ID': session}
    if tool is not None:
        headers['Mcp-Name'] = tool
    if key:
        headers['Authorization'] = 'Bearer ' + key
    trace("mcp.request", session, target="Talon MCP proxy", method=method, tool=tool,
          arguments=args if previews_enabled() else "[metadata only]")
    status, response = json_request(base.rstrip('/') + '/mcp/proxy',
                        {'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}, headers)
    g = governance(response)
    trace("mcp.response", session, method=method, tool=tool, http_status=status,
          decision=g.get("decision") if g else None,
          provenance=g.get("provenance") if g else None,
          evidence_id=g.get("evidence", {}).get("id") if g else None,
          discovered_tools=[t.get("name") for t in response.get("result", {}).get("tools", [])]
          if method == "tools/list" else None)
    return status, response


def governance(out):
    return (out.get('result', {}).get('_meta', {}).get(EXT) or
            out.get('error', {}).get('data', {}).get(EXT))


class HTTPBase(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass
    def reply(self, status, obj, content_type='application/json'):
        body = (obj if isinstance(obj, str) else json.dumps(obj)).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def payload(self):
        size = int(self.headers.get('Content-Length', '0'))
        if size < 1 or size > 8192:
            raise ValueError('invalid request size')
        return json.loads(self.rfile.read(size))


class HRService(HTTPBase):
    def do_GET(self):
        if self.path == '/debug/counters':
            with LOCK:
                return self.reply(200, dict(COUNTS))
        return self.reply(404, {'error': 'not_found'})
    def do_POST(self):
        if self.path == '/debug/reset':
            with LOCK:
                for key in COUNTS:
                    COUNTS[key] = 0
            return self.reply(200, {'reset': True})
        if self.path != '/mcp':
            return self.reply(404, {'error': 'not_found'})
        try:
            request = self.payload()
            method = request.get('method')
            rid = request.get('id')
            if method == 'tools/list':
                result = {'resultType': 'complete', 'tools': TOOLS, 'ttlMs': 30000, 'cacheScope': 'public'}
            elif method == 'tools/call':
                name = request.get('params', {}).get('name')
                if name not in COUNTS:
                    return self.reply(200, {'jsonrpc': '2.0', 'id': rid, 'error': {'code': -32602, 'message': 'Unknown tool'}})
                with LOCK:
                    COUNTS[name] += 1
                # HR service independently observes every actual upstream dispatch.
                trace("hr.upstream.dispatched", "hr-backend", tool=name,
                      execution_count=COUNTS[name])
                arguments = request.get('params', {}).get('arguments') or {}
                if not isinstance(arguments, dict):
                    raise ValueError('Tool arguments must be a map')
                import warehouse  # employee-level storage belongs to HR service only
                if name == 'hr_attrition_summary':
                    value = warehouse.attrition_summary(arguments.get('department', ''), arguments.get('months', 6))
                elif name == 'hr_headcount_summary':
                    value = warehouse.headcount_summary(arguments.get('department', ''))
                elif name == 'hr_tenure_summary':
                    value = warehouse.tenure_summary(arguments.get('department', ''))
                else:
                    value = warehouse.privileged_employee_detail()
                result = {'resultType': 'complete', 'content': [{'type': 'text', 'text': json.dumps(value)}]}
            else:
                return self.reply(200, {'jsonrpc': '2.0', 'id': rid, 'error': {'code': -32601, 'message': 'Method not found'}})
            return self.reply(200, {'jsonrpc': '2.0', 'id': rid, 'result': result})
        except (ValueError, TypeError):
            return self.reply(400, {'error': 'Invalid JSON'})



class DashboardService(HTTPBase):
    """Fixed aggregate-only HTTP API: no MCP endpoint, SQL input or employee rows."""
    def do_GET(self):
        import warehouse  # Only dashboard/HR backend processes have a mounted HR DB.
        from analytics import charts_html
        route = urlparse(self.path)
        qs = parse_qs(route.query)
        department = qs.get("department", [""])[0]
        if route.path not in ("/api/dashboard", "/charts"):
            return self.reply(404, {"error": "not_found"})
        try:
            stats = warehouse.dashboard_summary(department)
            if route.path == "/api/dashboard":
                return self.reply(200, stats)
            return self.reply(200, charts_html(stats), "text/html; charset=utf-8")
        except ValueError as exc:
            return self.reply(400, {"error": str(exc)})




class Browser(HTTPBase):
    talon = 'http://127.0.0.1:8080'
    mock = 'http://127.0.0.1:9091'
    dashboard = 'http://127.0.0.1:9093'
    key = 'talon-hr-demo-key-0001'
    live_mode = False
    llm_url = ''
    llm_key = ''
    llm_model = 'gpt-4o-mini'
    def do_GET(self):
        route = urlparse(self.path)
        query = parse_qs(route.query)
        if route.path == '/':
            return self.reply(200, HTML, 'text/html; charset=utf-8')
        if route.path in ('/api/dashboard', '/charts'):
            # The web/agent process has NO database file or HR-backend credentials.
            # It only reaches the separate aggregate-only dashboard service.
            query_string = urlencode({'department': query.get('department', [''])[0]})
            endpoint = self.dashboard.rstrip('/') + route.path + '?' + query_string
            try:
                with urlopen(endpoint, timeout=10) as response:
                    return self.reply(200, response.read().decode('utf-8'),
                                      'text/html; charset=utf-8' if route.path == '/charts'
                                      else 'application/json')
            except HTTPError as exc:
                return self.reply(exc.code, {'error': 'Unknown or disallowed dashboard filter'})
            except Exception:
                return self.reply(502, {'error': 'Aggregate dashboard service unavailable'})
        if route.path == '/api/mode':
            return self.reply(200, {'mode': 'live' if self.live_mode else 'guided'})
        if route.path == '/api/counters':
            if not self.mock:
                return self.reply(200, {'available': False, 'reason': 'Isolated app cannot reach HR backend; verify counts from operator backend.'})
            try:
                with urlopen(self.mock + '/debug/counters', timeout=3) as resp:
                    return self.reply(200, json.load(resp))
            except Exception:
                return self.reply(502, {'error': 'HR mock not running'})
        return self.reply(404, {'error': 'not_found'})
    def do_POST(self):
        try:
            if self.path not in ('/api/query', '/api/probe'):
                return self.reply(404, {'error': 'not_found'})
            payload = self.payload()
            session = payload.get('session')
            if not isinstance(session, str) or not session.startswith('hr-demo-') or len(session) > 80:
                raise ValueError('invalid session')
            code, listing = mcp_call(self.talon, self.key, 'tools/list', session=session)
            if code != 200 or 'result' not in listing:
                raise RuntimeError('Talon MCP discovery failed')
            names = [x['name'] for x in listing['result']['tools']]
            if 'hr_employee_export' in names:
                raise RuntimeError('Unsafe proxy policy: employee export was advertised')
            if self.path == '/api/probe':
                code, result = mcp_call(self.talon, self.key, 'tools/call', 'hr_employee_export', {'scope': 'all'}, session)
                g = governance(result)
                denied = bool(code == 200 and 'error' in result and g and g.get('decision') == 'deny'
                              and g.get('provenance') == 'not_dispatched' and g.get('retryable') is False
                              and g.get('evidence', {}).get('committed') is True)
                return self.reply(200, {'denied': denied, 'tool': {'governance': g}})
            query = payload.get('query', '')
            if not isinstance(query, str) or len(query) > 1000 or not query:
                raise ValueError('invalid query')
            if 'hr_attrition_summary' not in names:
                raise RuntimeError('Allowed HR aggregate tool was not advertised')
            if self.live_mode:
                data = run_live_chat(
                    query, listing['result']['tools'], session, self.llm_model,
                    self.llm_url, self.llm_key,
                    lambda name, arguments, sess: mcp_call(
                        self.talon, self.key, 'tools/call', name, arguments, sess))
                return self.reply(200, {'answer': data['answer'], 'tools': names,
                                         'calls': data['calls'], 'mode': data['mode'],
                                         'tool': {'governance': data['calls'][-1]['governance']}
                                         if data['calls'] else None})
            if any(word in query.lower() for word in ('name', 'salary', 'salaries', 'export', 'individual')):
                return self.reply(200, {'answer': 'Employee-level details are not authorized. You can ask for aggregate headcount, attrition or tenure trends.',
                                        'tools': names, 'tool': None, 'mode': 'guided'})
            if 'tenure' in query.lower():
                name, arguments = 'hr_tenure_summary', {}
            elif 'headcount' in query.lower() or 'workforce size' in query.lower():
                name, arguments = 'hr_headcount_summary', {}
            else:
                name, arguments = 'hr_attrition_summary', {'months': 6}
            code, result = mcp_call(self.talon, self.key, 'tools/call', name, arguments, session)
            g = governance(result)
            if code != 200 or 'result' not in result or not g or g.get('decision') != 'allow' or g.get('evidence', {}).get('committed') is not True:
                raise RuntimeError('No committed Talon authorization for aggregate HR data')
            data = json.loads(result['result']['content'][0]['text'])
            if name == 'hr_attrition_summary':
                rows = sorted(data['cohorts'], key=lambda r: r['months'][-1]['attrition_rate_pct'], reverse=True)
                answer = 'Latest monthly attrition by department:\n' + '\n'.join(
                    f"{r['department']}: {r['months'][-1]['attrition_rate_pct']:.2f}% "
                    f"(6-month change {r['change_pp']:+.2f} pp)" for r in rows)
            elif name == 'hr_headcount_summary':
                answer = 'Active headcount by department:\n' + '\n'.join(
                    f"{r['department']}: {r['active_headcount']}" for r in data['departments'])
            else:
                answer = 'Average tenure: ' + str(data['average_tenure_years']) + ' years\n' + '\n'.join(
                    f"{r['tenure_band']}: {r['headcount']} people" for r in data['bands'])
            answer += '\n\nGuided deterministic analysis, NOT a model-generated answer. Observed correlations are not causes.'
            return self.reply(200, {'answer': answer, 'tools': names, 'mode': 'guided', 'tool': {'governance': g}})
        except (ValueError, TypeError) as exc:
            return self.reply(400, {'error': str(exc)})
        except Exception as exc:
            return self.reply(502, {'error': f'Governed demo failed: {str(exc)[:250]}' })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('service', choices=['hr', 'dashboard', 'ui'])
    parser.add_argument('--port', type=int)
    args = parser.parse_args()
    if args.service == 'hr':
        handler, port = HRService, (args.port or 9091)
    elif args.service == 'dashboard':
        handler, port = DashboardService, (args.port or 9093)
    else:
        handler, port = Browser, (args.port or 8501)
        Browser.talon = os.getenv('TALON_URL', Browser.talon)
        Browser.mock = os.getenv('HR_MOCK_URL', Browser.mock)
        Browser.dashboard = os.getenv('HR_DASHBOARD_URL', Browser.dashboard)
        Browser.key = os.getenv('TALON_AGENT_KEY', Browser.key)
        Browser.live_mode = os.getenv('TALON_AI_MODE', 'guided') == 'live'
        Browser.llm_url = os.getenv('TALON_LLM_URL', '')
        Browser.llm_key = os.getenv('TALON_LLM_KEY', Browser.key)
        Browser.llm_model = os.getenv('TALON_LLM_MODEL', 'gpt-4o-mini')
    if args.service in ('hr', 'dashboard'):
        import warehouse
        count = warehouse.row_count()
    else:
        count = 'isolated/no DB'
    if args.service == 'ui' and Browser.live_mode and not Browser.llm_url:
        raise RuntimeError('LIVE AI requires TALON_LLM_URL pointing to a real Talon gateway')
    bind_host = os.getenv("DEMO_BIND_HOST", "127.0.0.1")
    print(f"{args.service} on {bind_host}:{port}, DB access={count}", flush=True)
    ThreadingHTTPServer((bind_host, port), handler).serve_forever()

if __name__ == '__main__':
    main()
