#!/usr/bin/env python3
"""Verify SQL and employee-query allow/deny policy flips through the real Talon MCP service."""
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parent.parent
POLICY=ROOT/"cases/people-analytics-copilot/.state/policy/proxy.isolated.talon.yaml"
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
def post_employee_question():
    # Identical model-free UI request on every run; Talon, not the app,
    # determines whether the employee export capability can execute.
    request=Request("http://127.0.0.1:8501/api/query",method="POST",
                    data=json.dumps({"session":SESSION,
                                     "query":"Show an individual employee name and salary"}).encode(),
                    headers={"Content-Type":"application/json"})
    for attempt in range(30):
        try:
            with urlopen(request,timeout=6) as resp:return json.load(resp)
        except Exception:
            if attempt==29:raise
            time.sleep(1)

def dc(*args):
    return subprocess.check_output(["docker","compose","-f","compose.isolated.yaml",*args],cwd=CASE,text=True)
def count():
    code="import json;from urllib.request import urlopen;print(json.load(urlopen('http://127.0.0.1:9091/debug/counters'))['hr_aggregate_sql'])"
    return int(dc("exec","-T","hr-server","python3","-c",code).strip())
def export_count():
    code="import json;from urllib.request import urlopen;print(json.load(urlopen('http://127.0.0.1:9091/debug/counters'))['hr_employee_export'])"
    return int(dc("exec","-T","hr-server","python3","-c",code).strip())

def reload():
    # Use the same native Talon CLI and Compose command documented in README.
    subprocess.run(["docker","compose","-f","compose.isolated.yaml","run","--rm",
                    "talon-cli","talon","validate"],check=True,cwd=CASE)
    subprocess.run(["docker","compose","-f","compose.isolated.yaml","up","--no-deps",
                    "-d","--force-recreate","talon-mcp"],check=True,cwd=CASE)
def assert_receipt(r,decision):
    receipt=r.get("receipt") or {}
    assert receipt.get("decision")==decision and receipt.get("evidence",{}).get("committed") is True,r
    assert receipt.get("evidence",{}).get("id"),r
def check_export_flip():
    original=POLICY.read_text()
    forbidden="  forbidden_tools:\n    - hr_employee_export\n"
    allowed_anchor="    - name: hr_aggregate_sql\n"
    assert original.count(forbidden)==1 and original.count(allowed_anchor)==1,original
    before=export_count()
    denied=post_employee_question()
    assert denied.get("status")=="talon_denied" and denied["tool"]["governance"]["decision"]=="deny",denied
    assert denied["tool"]["governance"]["provenance"]=="not_dispatched",denied
    assert denied["tool"]["governance"]["evidence"]["committed"] is True,denied
    assert export_count()==before,"Denied guided export reached HR backend"
    modified=(original.replace(allowed_anchor,allowed_anchor+"    - name: hr_employee_export\n",1)
              .replace(forbidden,"  forbidden_tools: []\n",1))
    try:
        POLICY.write_text(modified)
        reload()
        allowed=post_employee_question()
        assert allowed["tool"]["governance"]["decision"]=="allow",allowed
        assert allowed["tool"]["governance"]["evidence"]["committed"] is True,allowed
        assert "hr_employee_export" in allowed["tools"],allowed
        assert "Fictional employee records:" in allowed["answer"],allowed
        assert "full_name" in allowed["answer"] and "monthly_salary_mxn" in allowed["answer"],allowed
        assert export_count()==before+1,"Allowed guided export did not reach HR backend"
        print("PASS: identical employee query, policy-only change: deny -> allow; synthetic HR rows returned")
    finally:
        POLICY.write_text(original)
        reload()
    restored=post_employee_question()
    assert restored["status"]=="talon_denied",restored
    assert restored["tool"]["governance"]["evidence"]["committed"] is True,restored
    assert export_count()==before+1,"Re-denied export reached HR backend"
    print("PASS: employee export restored to deny; no new HR dispatch")


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
    check_export_flip()
    dc("exec","-T","talon-mcp","talon","audit","export","--format","signed-json","--session",SESSION,
       "--output","/tmp/hr-policy-change.json")
    output=dc("exec","-T","talon-mcp","talon","audit","verify","--file","/tmp/hr-policy-change.json")
    assert "Invalid records: 0" in output,output
    print("PASS: restored permission; all allow/deny evidence signatures verify")

if __name__=="__main__":main()
