"""Opt-in live OpenAI smoke through REAL Talon LLM + MCP gateways and DuckDB.

Requires a real OpenAI API key placed in Talon's vault by the launcher. Makes
bounded billable model requests. Never runs in routine PR CI or synthetic CI.
"""
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen

from demo import mcp_call
from agent_runtime import run_live_chat


def get(url):
    with urlopen(url, timeout=10) as res:
        return json.load(res)


def main():
    model = os.getenv("HR_REAL_MODEL", "gpt-4o-mini")
    key = os.getenv("HR_TALON_AGENT_KEY", "talon-hr-demo-key-0001")
    talon_bin = os.getenv("TALON_BIN", "talon")
    mcp = os.getenv("TALON_URL", "http://127.0.0.1:8080")
    gateway = os.getenv("TALON_LLM_URL",
                        "http://127.0.0.1:8082/v1/proxy/openai/v1/chat/completions")
    session = "hr-demo-live-provider-smoke"
    status, listing = mcp_call(mcp, key, "tools/list", session=session)
    assert status == 200 and "result" in listing, listing
    tools = listing["result"]["tools"]
    safe = {"hr_attrition_summary", "hr_headcount_summary", "hr_tenure_summary", "hr_aggregate_sql"}
    assert {t["name"] for t in tools} == safe, tools
    before = get("http://127.0.0.1:9091/debug/counters")
    result = run_live_chat(
        "Which department has the highest monthly attrition for September 2026? "
        "Use the available six-month attrition metrics. Cite figures and avoid causal claims.",
        tools, session, model, gateway, key,
        lambda tool, args, sid: mcp_call(mcp, key, "tools/call", tool, args, sid),
    )
    assert result["calls"], "Model failed to select an approved data tool"
    assert all(c["name"] in safe for c in result["calls"]), result
    assert result["answer"] and len(result["answer"]) >= 30, result
    after = get("http://127.0.0.1:9091/debug/counters")
    assert after["hr_employee_export"] == before["hr_employee_export"] == 0, after
    assert sum(after[t] - before[t] for t in safe) == len(result["calls"]), after

    with tempfile.TemporaryDirectory() as temp:
        file = str(Path(temp) / "signed-session.json")
        exported = subprocess.run(
            [talon_bin, "audit", "export", "--format", "signed-json",
             "--session", session, "--output", file], capture_output=True, text=True)
        assert exported.returncode == 0, exported.stderr
        evidence = json.loads(Path(file).read_text())["records"]
        assert len(evidence) >= len(result["calls"]) + 2, evidence
        assert {r.get("agent_id") for r in evidence} == {"hr-analytics-assistant"}, evidence
        verify = subprocess.run([talon_bin, "audit", "verify", "--file", file],
                                capture_output=True, text=True)
        assert verify.returncode == 0, (verify.stdout, verify.stderr)
        for expected in ("Invalid records: 0", "Missing signature: 0", "Could not parse: 0"):
            assert expected in verify.stdout, verify.stdout
        print(f"PASS: real provider via Talon: {len(evidence)} signed records, one agent/session")
    print("PASS: LLM selected approved tools; no privileged export; model answer returned")
    print("PASS: actual provider-backed People Analytics smoke")
    print("Model:", model)
    print("Answer:", result["answer"])


if __name__ == "__main__":
    main()
