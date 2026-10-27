#!/usr/bin/env python3
"""Black-box acceptance against real Talon. Run with Talon and HR mock running."""
import argparse
import json
import subprocess
from urllib.request import Request, urlopen
from demo import governance, mcp_call


def get(url):
    with urlopen(url, timeout=5) as response:
        return json.load(response)


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
    def call(method, tool=None, arguments=None):
        return mcp_call(args.talon_url, args.agent_key, method, tool, arguments, 'hr-demo-acceptance')
    status, tools = call('tools/list')
    assert status == 200 and 'result' in tools, f'Failed discovery: {status} {tools}'
    names = [x['name'] for x in tools['result']['tools']]
    assert set(names) == {'hr_attrition_summary', 'hr_headcount_summary', 'hr_tenure_summary'}, names
    print('PASS: safe capability advertised; sensitive export hidden')
    status, allowed = call('tools/call', 'hr_attrition_summary', {'months': 6})
    a = governance(allowed)
    assert status == 200 and 'result' in allowed and a and a['decision'] == 'allow' and a['evidence']['committed'] is True, allowed
    counts = get(hr + '/debug/counters')
    assert counts['hr_attrition_summary'] == 1 and counts['hr_employee_export'] == 0, counts
    print('PASS: aggregate call executed exactly once with committed Talon receipt')
    allowed_ids = [a['evidence']['id']]
    for tool in ('hr_headcount_summary', 'hr_tenure_summary'):
        status, output = call('tools/call', tool, {})
        ext = governance(output)
        assert status == 200 and 'result' in output and ext and ext['decision'] == 'allow' and ext['evidence']['committed'] is True, output
        allowed_ids.append(ext['evidence']['id'])
        print('PASS: allowed workforce aggregate:', tool)
    counts = get(hr + '/debug/counters')
    assert counts['hr_headcount_summary'] == 1 and counts['hr_tenure_summary'] == 1 and counts['hr_employee_export'] == 0, counts
    status, denied = call('tools/call', 'hr_employee_export', {'scope': 'all'})
    d = governance(denied)
    assert status == 200 and 'error' in denied and d and d['code'] == 'policy_denied' and d['decision'] == 'deny' and d['retryable'] is False and d['provenance'] == 'not_dispatched' and d['evidence']['committed'] is True, denied
    counts = get(hr + '/debug/counters')
    assert counts['hr_attrition_summary'] == 1 and counts['hr_headcount_summary'] == 1 and counts['hr_tenure_summary'] == 1 and counts['hr_employee_export'] == 0, counts
    print('PASS: forbidden employee export rejected with zero upstream executions')
    for evidence_id in [*allowed_ids, d['evidence']['id']]:
        result = subprocess.run([args.talon_bin, 'audit', 'verify', evidence_id], capture_output=True, text=True)
        assert result.returncode == 0 and 'VALID' in result.stdout, f'Invalid signature {evidence_id}: {result.stdout} {result.stderr}'
        print('PASS: Talon signature verified:', evidence_id)
    print('PASS: People Analytics Copilot real-Talon acceptance')

if __name__ == '__main__':
    main()
