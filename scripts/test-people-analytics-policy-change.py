#!/usr/bin/env python3
"""Verify identical SQL request changes from allow to deny solely through Talon MCP policy."""
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parent.parent
POLICY=ROOT/"cases/people-analytics-copilot/.state/policy/proxy.isolated.talon.yaml"
LAUNCHER=ROOT/"scripts/people-analytics-isolated.sh"
CASE=ROOT/"cases/people-analytics-copilot"
SQL="SELECT department, COUNT(*) AS employees FROM employees GROUP BY department ORDER BY department"
SESSION="hr-demo-policy-change"
def post():
    request=Request("http://127.0.0.1:8501/api/sql",method="POST",
                    data=json.dumps({"session":SESSION,"sql":SQL}).encode(),
                    headers={"Content-Type":"application/json"})
    for attempt in range(30):
        try:
            with urlopen(request,timeout=6) as resp:return json.load(resp)
        except Exception:
            if attempt==29:raise
            time.sleep(1)
def dc(*args):
    return subprocess.check_output(["docker","compose","-f",str(CASE/"compose.isolated.yaml"),
        "--env-file",str(CASE/".state/isolated.env"),*args],text=True)
def count():
    code="import json;from urllib.request import urlopen;print(json.load(urlopen('http://127.0.0.1:9091/debug/counters'))['hr_aggregate_sql'])"
    return int(dc("exec","-T","hr-server","python3","-c",code).strip())
def reload():
    subprocess.run(["bash",str(LAUNCHER),"reapply"],check=True,cwd=str(ROOT))
def assert_receipt(r,decision):
    receipt=r.get("receipt") or {}
    assert receipt.get("decision")==decision and receipt.get("evidence",{}).get("committed") is True,r
    assert receipt.get("evidence",{}).get("id"),r
def main():
    original=POLICY.read_text()
    entry="    - name: hr_aggregate_sql\n"
    assert original.count(entry)==1,"Expected exactly one MCP SQL allowance"
    before=count()
    allowed=post()
    assert allowed.get("status")=="executed",allowed
    assert_receipt(allowed,"allow")
    assert count()==before+1,"First SQL was not executed"
    try:
        POLICY.write_text(original.replace(entry,"",1))
        reload()
        after=count()
        denied=post()
        assert denied.get("status")=="talon_denied",denied
        assert_receipt(denied,"deny")
        assert (denied["receipt"].get("provenance")=="not_dispatched"),denied
        assert count()==after,"Denied SQL reached HR backend"
        print("PASS: identical SQL, same app, only Talon MCP policy changed: allow -> deny; no upstream dispatch")
    finally:
        POLICY.write_text(original)
        reload()
    restored=post()
    assert restored.get("status")=="executed",restored
    assert_receipt(restored,"allow")
    dc("exec","-T","talon-mcp","talon","audit","export","--format","signed-json","--session",SESSION,
       "--output","/tmp/hr-policy-change.json")
    output=dc("exec","-T","talon-mcp","talon","audit","verify","--file","/tmp/hr-policy-change.json")
    assert "Invalid records: 0" in output,output
    print("PASS: restored permission; all allow/deny evidence signatures verify")

if __name__=="__main__":main()
