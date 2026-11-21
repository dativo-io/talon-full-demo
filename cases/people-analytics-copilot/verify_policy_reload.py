#!/usr/bin/env python3
"""Policy reload on Talon's governed MCP endpoint, proven at the HR backend.

Run by scripts/test-people-analytics-talon.sh between Talon restarts; the
script edits only the use case's agent.talon.yaml (capabilities.forbidden_tools).
Each phase checks Talon's committed receipt AND the HR server's own counter.
"""
import argparse
import json
import sys
from urllib.request import urlopen
from demo import governance, governed_call, mcp_call

SESSION = 'hr-demo-policy-reload'
SQL = 'SELECT department, COUNT(*) AS employees FROM employees GROUP BY department ORDER BY department'


def counts(hr):
    with urlopen(hr + '/debug/counters', timeout=5) as response:
        return json.load(response)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=['sql-denied', 'export-allowed', 'restored'])
    p.add_argument('--talon-url', default='http://127.0.0.1:8080')
    p.add_argument('--hr-url', default='http://127.0.0.1:9091')
    p.add_argument('--agent-key', default='talon-hr-demo-key-0001')
    args = p.parse_args()
    hr = args.hr_url.rstrip('/')

    def listed():
        status, out = mcp_call(args.talon_url, args.agent_key, 'tools/list', session=SESSION)
        assert status == 200 and 'result' in out, out
        return {t['name'] for t in out['result']['tools']}

    if args.phase == 'sql-denied':
        assert 'hr_aggregate_sql' not in listed(), 'a forbidden action is still discoverable'
        before = counts(hr)['hr_aggregate_sql']
        status, out = mcp_call(args.talon_url, args.agent_key, 'tools/call',
                               'hr_aggregate_sql', {'sql': SQL}, SESSION)
        g = governance(out)
        assert g and g['code'] == 'policy_denied' and g['provenance'] == 'not_dispatched' \
            and g['evidence']['committed'] is True, out
        assert counts(hr)['hr_aggregate_sql'] == before, 'denied SQL reached HR'
        print('PASS: after the policy edit and a Talon restart, identical SQL is policy_denied with zero HR dispatch')
    elif args.phase == 'export-allowed':
        assert 'hr_employee_export' in listed(), 'the export is not discoverable after lifting the prohibition'
        before = counts(hr)['hr_employee_export']
        status, prep = mcp_call(args.talon_url, args.agent_key, 'tools/call',
                                'hr_employee_export', {'scope': 'all'}, SESSION)
        g = governance(prep)
        assert g and g['code'] == 'operation_prepared' and g['provenance'] == 'not_dispatched' \
            and g['evidence']['committed'] is True and g['operationId'], prep
        assert counts(hr)['hr_employee_export'] == before, 'preparing the export reached HR'
        status, out = mcp_call(args.talon_url, args.agent_key, 'tools/call', 'talon_execute_operation',
                               {'operation_id': g['operationId']}, SESSION)
        e = governance(out)
        assert e and e['code'] == 'allowed' and e['operationId'] == g['operationId'], out
        assert counts(hr)['hr_employee_export'] == before + 1, 'the executed export did not reach HR exactly once'
        status, again = mcp_call(args.talon_url, args.agent_key, 'tools/call', 'talon_execute_operation',
                                 {'operation_id': g['operationId']}, SESSION)
        assert governance(again)['code'] == 'operation_already_succeeded', again
        assert counts(hr)['hr_employee_export'] == before + 1, 'a duplicate execute reached HR'
        # The app's own helper does the same two calls.
        status, out2, receipts = governed_call(args.talon_url, args.agent_key,
                                               'hr_employee_export', {'scope': 'all'}, SESSION)
        assert [r['code'] for r in receipts] == ['operation_prepared', 'allowed'], receipts
        assert counts(hr)['hr_employee_export'] == before + 2
        data = json.loads(out['result']['content'][0]['text'])
        assert data.get('synthetic') is True and data.get('employees'), data
        print('PASS: export allowed by policy edit: prepared (zero HR calls), executed once by operation id, duplicate execute refused (operation_already_succeeded)')
    else:
        names = listed()
        assert 'hr_aggregate_sql' in names and 'hr_employee_export' not in names, names
        before = counts(hr)
        status, out = mcp_call(args.talon_url, args.agent_key, 'tools/call',
                               'hr_aggregate_sql', {'sql': SQL}, SESSION)
        assert governance(out)['decision'] == 'allow', out
        status, denied = mcp_call(args.talon_url, args.agent_key, 'tools/call',
                                  'hr_employee_export', {'scope': 'all'}, SESSION)
        assert governance(denied)['code'] == 'policy_denied', denied
        after = counts(hr)
        assert after['hr_aggregate_sql'] == before['hr_aggregate_sql'] + 1, (before, after)
        assert after['hr_employee_export'] == before['hr_employee_export'], (before, after)
        print('PASS: restored policy: SQL allowed (one HR call), export denied again (no HR call)')


if __name__ == '__main__':
    sys.exit(main())
