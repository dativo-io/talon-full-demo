#!/usr/bin/env python3
"""Black-box acceptance against real Talon's governed MCP endpoint (/mcp).

Run with Talon (`talon serve`) and the HR MCP server running. Every claim is
checked against an independent observation: the HR server's own dispatch
counters, Talon's signed records (`talon audit verify`), the operation's
signed lifecycle (`talon audit verify --operation`) and the session timeline.
"""
import argparse
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from urllib.request import Request, urlopen
from demo import GOVERNED_TOOLS, governance, mcp_call

SESSION = 'hr-demo-acceptance'
AGENT = 'hr-analytics-assistant'
VALID_SQL = 'SELECT department, COUNT(*) AS employees FROM employees GROUP BY department ORDER BY department'
INVALID_SQL = 'SELECT employee_id, full_name, monthly_salary_mxn FROM employees'


def get(url):
    with urlopen(url, timeout=5) as response:
        return json.load(response)


def talon(bin_, *args):
    return subprocess.run([bin_, *args], capture_output=True, text=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--talon-url', default='http://127.0.0.1:8080')
    p.add_argument('--hr-url', default='http://127.0.0.1:9091')
    p.add_argument('--agent-key', default='talon-hr-demo-key-0001')
    p.add_argument('--talon-bin', required=True)
    args = p.parse_args()
    hr = args.hr_url.rstrip('/')
    with urlopen(Request(hr + '/debug/reset', data=b'', method='POST'), timeout=5):
        pass

    def call(method, tool=None, arguments=None, operation_id=None):
        return mcp_call(args.talon_url, args.agent_key, method, tool, arguments, SESSION,
                        operation_id=operation_id)

    def counts():
        return get(hr + '/debug/counters')

    status, tools = call('tools/list')
    assert status == 200 and 'result' in tools, f'Failed discovery: {status} {tools}'
    names = {x['name'] for x in tools['result']['tools']}
    assert names == GOVERNED_TOOLS, names
    print('PASS: governed discovery lists the four aggregates and talon_execute_operation; the export is hidden')

    # The admin key is not an identity on /mcp.
    admin = os.environ.get('TALON_ADMIN_KEY')
    if admin:
        status, refused = mcp_call(args.talon_url, admin, 'tools/list', session=SESSION)
        assert status == 401, (status, refused)
        print('PASS: the admin key is refused on /mcp (only the use case key is an identity)')

    operations = {}
    status, allowed = call('tools/call', 'hr_attrition_summary', {'months': 6})
    a = governance(allowed)
    assert status == 200 and 'result' in allowed and a, allowed
    assert a['code'] == 'allowed' and a['decision'] == 'allow' and a['provenance'] == 'observed' \
        and a['evidence']['committed'] is True and a['operationId'], a
    assert counts()['hr_attrition_summary'] == 1 and counts()['hr_employee_export'] == 0
    operations['hr_attrition_summary'] = a
    print('PASS: read-only aggregate executed in one call, exactly once at HR, with a committed receipt')
    for tool in ('hr_headcount_summary', 'hr_tenure_summary'):
        status, output = call('tools/call', tool, {})
        ext = governance(output)
        assert status == 200 and 'result' in output and ext and ext['decision'] == 'allow' \
            and ext['evidence']['committed'] is True, output
        operations[tool] = ext
        print('PASS: allowed workforce aggregate:', tool)
    c = counts()
    assert c['hr_headcount_summary'] == 1 and c['hr_tenure_summary'] == 1 and c['hr_employee_export'] == 0, c

    status, denied = call('tools/call', 'hr_employee_export', {'scope': 'all'})
    d = governance(denied)
    assert status == 200 and 'error' in denied and d and d['code'] == 'policy_denied' \
        and d['decision'] == 'deny' and d['retryable'] is False \
        and d['provenance'] == 'not_dispatched' and d['evidence']['committed'] is True, denied
    assert counts()['hr_employee_export'] == 0, counts()
    operations['hr_employee_export'] = d
    print('PASS: forbidden employee export called by name: policy_denied, zero HR executions')

    before_sql = counts()['hr_aggregate_sql']
    status, executed = call('tools/call', 'hr_aggregate_sql', {'sql': VALID_SQL})
    s = governance(executed)
    assert status == 200 and 'result' in executed and s and s['decision'] == 'allow', executed
    assert counts()['hr_aggregate_sql'] == before_sql + 1
    operations['hr_aggregate_sql (approved)'] = s
    print('PASS: approved aggregate SQL executed once at HR')

    # An allowed query the HR SQL validator rejects AFTER dispatch: the
    # backend may have done work, so the outcome is unknown, never a Talon
    # denial, and the vendor's text is not relayed.
    before_sql = counts()['hr_aggregate_sql']
    status, rejected = call('tools/call', 'hr_aggregate_sql', {'sql': INVALID_SQL})
    u = governance(rejected)
    assert status == 200 and 'error' in rejected and u, rejected
    assert u['code'] == 'upstream_outcome_unknown' and u['decision'] == 'unknown' \
        and u['provenance'] == 'unknown' and u['retryable'] is False \
        and u['evidence']['committed'] is True, u
    assert 'HR_SQL_REJECTED' not in json.dumps(rejected), 'vendor text relayed to the client'
    assert counts()['hr_aggregate_sql'] == before_sql + 1, 'the rejected query was not dispatched exactly once'
    operations['hr_aggregate_sql (rejected)'] = u
    print('PASS: HR validator rejection after dispatch is upstream_outcome_unknown (not a Talon denial); dispatched once')

    # With a client-chosen operation id, a retry resolves the SAME operation:
    # an unknown outcome is never sent to HR again.
    op_id = 'hr-demo-unknown-' + uuid.uuid4().hex[:12]
    before_sql = counts()['hr_aggregate_sql']
    status, first = call('tools/call', 'hr_aggregate_sql', {'sql': INVALID_SQL}, operation_id=op_id)
    assert governance(first)['code'] == 'upstream_outcome_unknown', first
    status, retry = call('tools/call', 'hr_aggregate_sql', {'sql': INVALID_SQL}, operation_id=op_id)
    r = governance(retry)
    assert r and r['code'] == 'operation_outcome_unknown' and r['retryable'] is False, retry
    assert counts()['hr_aggregate_sql'] == before_sql + 1, 'an unknown operation was dispatched again'
    status, changed = call('tools/call', 'hr_aggregate_sql', {'sql': VALID_SQL}, operation_id=op_id)
    assert governance(changed)['code'] == 'operation_conflict', changed
    assert counts()['hr_aggregate_sql'] == before_sql + 1, 'changed arguments under one operation id reached HR'
    print('PASS: retry of an unknown operation is refused (operation_outcome_unknown); changed arguments conflict; HR saw one call')

    for label, ext in operations.items():
        result = talon(args.talon_bin, 'audit', 'verify', ext['evidence']['id'])
        assert result.returncode == 0 and 'VALID' in result.stdout, \
            f'Invalid signature {label}: {result.stdout} {result.stderr}'
        lifecycle = talon(args.talon_bin, 'audit', 'verify', '--operation', ext['operationId'])
        assert lifecycle.returncode == 0 and 'Lifecycle: VALID' in lifecycle.stdout, \
            f'Lifecycle {label}: {lifecycle.stdout} {lifecycle.stderr}'
        print(f'PASS: signed record and lifecycle verified: {label} ({ext["operationId"]})')

    # Session attribution: the client-asserted X-Talon-Session-ID joins every
    # lifecycle record of these operations, all attributed to the use case.
    listed = talon(args.talon_bin, 'audit', 'list', '--session', SESSION, '--json')
    assert listed.returncode == 0, listed.stderr
    timeline = json.loads(listed.stdout)
    records = timeline['records']
    assert records, timeline
    agents = {r.get('agent_id') for r in records}
    assert agents == {AGENT}, agents
    # The signed-evidence rollup keeps outcomes apart (Talon #589): the export
    # Talon refused is a denied tool call; the aggregate the HR validator
    # rejected after dispatch is an unknown outcome, never a policy denial.
    summary = timeline['summary']
    outcomes = [r.get('outcome') or {} for r in records]
    denied = [o for o in outcomes if o.get('decision') == 'denied']
    unknown = [o for o in outcomes if o.get('dispatch') == 'unknown']
    assert unknown and all(o.get('decision') == 'allowed' for o in unknown), unknown
    assert summary.get('denied') == len(denied), (summary.get('denied'), len(denied))
    assert summary.get('tool_calls_denied', 0) >= 1, summary
    assert summary.get('tool_calls_unknown', 0) >= 1, summary
    print(f"PASS: session rollup: {summary.get('tool_calls', 0)} governed tool calls, "
          f"{summary['tool_calls_denied']} denied by Talon, {summary['tool_calls_unknown']} with an unknown outcome "
          f"(the HR rejection is never counted as a Talon denial)")
    seen_ops = {e['operationRef'] for e in operations.values()}
    with tempfile.TemporaryDirectory() as temp:
        out = str(Path(temp) / 'session.json')
        export = talon(args.talon_bin, 'audit', 'export', '--format', 'signed-json',
                       '--session', SESSION, '--output', out)
        assert export.returncode == 0, export.stderr
        body = Path(out).read_text()
        exported = json.loads(body)['records']
        refs = {r.get('correlation_id') for r in exported}
        assert seen_ops <= refs, (seen_ops - refs)
        # Credential isolation: no key material in the signed records.
        for secret in filter(None, [args.agent_key, os.environ.get('TALON_ADMIN_KEY'),
                                    os.environ.get('TALON_SECRETS_KEY'),
                                    os.environ.get('TALON_SIGNING_KEY')]):
            assert secret not in body, 'key material found in signed session records'
        verified = talon(args.talon_bin, 'audit', 'verify', '--file', out)
        assert verified.returncode == 0 and 'Invalid records: 0' in verified.stdout, verified.stdout
    print(f'PASS: {len(records)} session records, all attributed to {AGENT}; every operation joined the session; no key material in signed records')
    print('PASS: People Analytics Copilot real-Talon governed MCP acceptance')


if __name__ == '__main__':
    main()
