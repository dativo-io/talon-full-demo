"""Prove a legacy direct privileged HR path, then the sealed agent boundary.

This is *synthetic* HR data. Baseline runs inside the privileged backend
container; governed proof runs inside the separated app container. Docker
network isolation and read-only volumes are deployment controls, NOT Talon.
"""
import json
import os
import socket
import sys
from urllib.request import Request, urlopen

from demo import META, governance, json_request, mcp_call

BACKEND = "http://127.0.0.1:9091"
MCP = "http://talon-mcp:8080"
DASHBOARD = "http://dashboard:9093"


def get(url):
    with urlopen(url, timeout=10) as response:
        return json.load(response)


def baseline():
    """Trusted HR backend can bypass Talon: the legacy risk is not imaginary."""
    status, out = json_request(BACKEND + "/mcp", {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"_meta": META, "name": "hr_employee_export",
                   "arguments": {"scope": "all"}},
    })
    assert status == 200 and "result" in out, (status, out)
    data = json.loads(out["result"]["content"][0]["text"])
    assert data.get("synthetic") is True and len(data["employees"]) > 0, data
    assert "monthly_salary_mxn" in data["employees"][0], data
    counts = get(BACKEND + "/debug/counters")
    assert counts["hr_employee_export"] >= 1, counts
    with urlopen(Request(BACKEND + "/debug/reset", method="POST", data=b""), timeout=10):
        pass
    print("BASELINE (privileged backend): direct employee export succeeded without Talon.")
    print("BASELINE: synthetic employee-level records were returned; counters reset.")
    print("BASELINE: this is the risk if a future agent retains equivalent direct credentials.")


def app():
    """App container has NO raw DuckDB filesystem or route to privileged HR."""
    assert not os.path.exists("/data/hr.duckdb"), "UI unexpectedly has the HR database volume"
    try:
        socket.create_connection(("hr-server", 9091), timeout=2)
    except (OSError, TimeoutError):
        print("PASS: UI/AI cannot reach the privileged HR server on the private network")
    else:
        raise AssertionError("UI can bypass Talon and reach HR server directly")

    # Assert the actual browser route works *without* mounting DuckDB into UI.
    browser_dashboard = get("http://127.0.0.1:8501/api/dashboard")
    assert browser_dashboard.get("warehouse") == "DuckDB", browser_dashboard
    with urlopen("http://127.0.0.1:8501/charts", timeout=10) as response:
        page = response.read().decode("utf-8")
    assert "12-month workforce attrition" in page, page[:500]
    print("PASS: browser proxy serves chart and dashboard from isolated aggregate API")
    dashboard = get(DASHBOARD + "/api/dashboard")
    assert dashboard.get("synthetic") and dashboard.get("warehouse") == "DuckDB", dashboard
    assert dashboard["headcount"] > 700, dashboard
    print("PASS: dashboard retrieves fixed, synthetic aggregates without HR DB credentials")

    session = "hr-demo-isolated-boundary"
    code, tools = mcp_call(MCP, "talon-hr-demo-key-0001", "tools/list", session=session)
    assert code == 200 and "result" in tools, tools
    assert {t["name"] for t in tools["result"]["tools"]} == {
        "hr_attrition_summary", "hr_headcount_summary", "hr_tenure_summary", "hr_aggregate_sql"
    }, tools
    code, permitted = mcp_call(MCP, "talon-hr-demo-key-0001", "tools/call",
                               "hr_attrition_summary", {"months": 6}, session)
    allowed = governance(permitted)
    assert code == 200 and allowed and allowed["decision"] == "allow" and \
        allowed["evidence"]["committed"] is True, permitted
    code, blocked = mcp_call(MCP, "talon-hr-demo-key-0001", "tools/call",
                             "hr_employee_export", {"scope": "all"}, session)
    denied = governance(blocked)
    assert code == 200 and "error" in blocked and denied and denied["decision"] == "deny" \
        and denied["provenance"] == "not_dispatched" \
        and denied["evidence"]["committed"] is True, blocked
    print("PASS: safe MCP HR aggregate permitted with committed Talon evidence")
    print("PASS: forced employee export denied before dispatch with committed Talon evidence")
    print("PASS: agent container has neither the HR database nor a network bypass")
    print("Evidence IDs:", allowed["evidence"]["id"], denied["evidence"]["id"])


def backend_counts():
    counts = get(BACKEND + "/debug/counters")
    assert counts["hr_employee_export"] == 0, counts
    assert counts["hr_attrition_summary"] >= 1, counts
    print("PASS: upstream independently counted zero employee exports:", counts)



# Granular integration checks. All run against actual service containers.
# The counter reset is explicit; it never means the baseline call was blocked.
CHECK_SESSION = "hr-demo-proof-checks"


def check_before():
    """Execute and SHOW a direct privileged export; intentionally no counter reset."""
    code, result = json_request(BACKEND + "/mcp", {
        "jsonrpc": "2.0", "id": 101, "method": "tools/call",
        "params": {"_meta": META, "name": "hr_employee_export",
                   "arguments": {"scope": "all"}},
    })
    assert code == 200 and "result" in result, (code, result)
    data = json.loads(result["result"]["content"][0]["text"])
    assert data.get("synthetic") is True and data.get("employees"), data
    person = data["employees"][0]
    assert "monthly_salary_mxn" in person, person
    print("BEFORE: direct call to HR backend, NO Talon in the request path")
    print("Synthetic employee example:", json.dumps({
        "name": person["full_name"], "monthly_salary_mxn": person["monthly_salary_mxn"]
    }, indent=2))
    print("Direct backend call succeeded; not governed by Talon.")
    check_counters()


def check_counters():
    counts = get(BACKEND + "/debug/counters")
    print("BACKEND EXECUTION COUNTERS:", json.dumps(counts, indent=2))


def check_reset():
    with urlopen(Request(BACKEND + "/debug/reset", method="POST", data=b""),
                 timeout=10):
        pass
    counts = get(BACKEND + "/debug/counters")
    assert counts and all(value == 0 for value in counts.values()), counts
    print("RESET: all backend counters explicitly reset to zero for AFTER test.")
    print("This does not undo the BEFORE call or revoke the backend's privileges.")
    check_counters()


def check_boundary():
    assert not os.path.exists("/data/hr.duckdb"), "Unexpected HR DB in AI container"
    print("NO DATABASE FILE: AI workload does not mount /data/hr.duckdb")
    try:
        socket.create_connection(("hr-server", 9091), timeout=2)
    except OSError as exc:
        print("NO DIRECT NETWORK PATH to private HR service:", type(exc).__name__)
    else:
        raise AssertionError("AI could bypass Talon via private HR network")
    stats = get("http://127.0.0.1:8501/api/dashboard")
    assert stats.get("synthetic") and stats.get("warehouse") == "DuckDB", stats
    print("APP STILL WORKS: fixed aggregate-only dashboard reports",
          stats["headcount"], "synthetic active employees.")


def check_discover():
    code, out = mcp_call(MCP, "talon-hr-demo-key-0001", "tools/list",
                         session=CHECK_SESSION)
    assert code == 200 and "result" in out, out
    offered = [tool["name"] for tool in out["result"]["tools"]]
    assert set(offered) == {
        "hr_attrition_summary", "hr_headcount_summary", "hr_tenure_summary", "hr_aggregate_sql"
    }, offered
    print("TALON TOOL DISCOVERY (same agent/session):")
    print(json.dumps(offered, indent=2))
    print("Employee-level export is absent from discovery.")


def check_allow():
    code, out = mcp_call(MCP, "talon-hr-demo-key-0001", "tools/call",
                         "hr_attrition_summary", {"months": 6},
                         session=CHECK_SESSION)
    detail = governance(out)
    assert code == 200 and "result" in out and detail, out
    assert detail["decision"] == "allow" and detail["evidence"]["committed"] is True, out
    result = json.loads(out["result"]["content"][0]["text"])
    assert result["cohorts"], result
    first = result["cohorts"][0]
    print("ALLOWED: aggregated DuckDB attrition for", first["department"])
    print("Example:", first["months"][-1])
    print("TALON GOVERNANCE RECEIPT:", json.dumps(detail, indent=2))


def check_deny():
    code, out = mcp_call(MCP, "talon-hr-demo-key-0001", "tools/call",
                         "hr_employee_export", {"scope": "all"},
                         session=CHECK_SESSION)
    detail = governance(out)
    assert code == 200 and "error" in out and detail, out
    assert detail["decision"] == "deny" \
        and detail["provenance"] == "not_dispatched" \
        and detail["evidence"]["committed"] is True, out
    print("DENIED: attempted employee export through Talon MCP")
    print("TALON GOVERNANCE RECEIPT:", json.dumps(detail, indent=2))



def warehouse_info():
    """Inspectable DuckDB metadata from private HR service; no employee rows."""
    import duckdb
    import warehouse
    path = warehouse.database_path()
    with duckdb.connect(str(path), read_only=True) as conn:
        tables = [row[0] for row in conn.execute("SHOW TABLES").fetchall()]
        fields = [row[1] for row in conn.execute("PRAGMA table_info('employees')").fetchall()]
        count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
    print(json.dumps({"engine": "embedded DuckDB (not a separate database server)",
                      "path": str(path), "read_only_inspection": True,
                      "tables": tables, "employee_columns": fields,
                      "synthetic_employee_rows": count,
                      "note": "Metadata only; UI SQL permits two reviewed aggregate shapes through Talon MCP."},
                     indent=2))
    assert count == 1200


if __name__ == "__main__":
    actions = {
        "baseline": baseline, "app": app, "backend-counts": backend_counts,
        "warehouse-info": warehouse_info,
        "before": check_before, "counters": check_counters,
        "reset": check_reset, "boundary": check_boundary,
        "discover": check_discover, "allow": check_allow, "deny": check_deny,
    }
    if len(sys.argv) != 2 or sys.argv[1] not in actions:
        raise SystemExit("Usage: python verify_isolation.py " + "|".join(actions))
    actions[sys.argv[1]]()
