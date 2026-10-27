"""End-to-end LIVE AI contract: real Talon LLM gateway + real Talon MCP proxy.

The provider is an explicitly labelled synthetic OpenAI-compatible model
fixture. No external vendor key or paid model is used by this acceptance test.
"""
import argparse
import contextlib
import io
import json
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen

from agent_runtime import run_live_chat
from demo import mcp_call


def get(url):
    with urlopen(url, timeout=5) as r:
        return json.load(r)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--talon-bin", required=True)
    parser.add_argument("--mcp", default="http://127.0.0.1:8080")
    parser.add_argument("--gateway", default="http://127.0.0.1:8082")
    parser.add_argument("--hr", default="http://127.0.0.1:9091")
    parser.add_argument("--model-upstream", default="http://127.0.0.1:9092")
    parser.add_argument("--agent-key", default="talon-hr-demo-key-0001")
    args = parser.parse_args()
    session = "hr-demo-real-gateway-model-tool-loop"
    before = get(args.hr + "/debug/counters")
    http_code, listed = mcp_call(args.mcp, args.agent_key, "tools/list", session=session)
    assert http_code == 200 and "result" in listed, listed
    offered = listed["result"]["tools"]
    assert {t["name"] for t in offered} == {
        "hr_attrition_summary", "hr_headcount_summary", "hr_tenure_summary"
    }, offered

    def tool_call(name, arguments, session_id):
        return mcp_call(args.mcp, args.agent_key, "tools/call",
                        name, arguments, session=session_id)

    # Observe real routed exchanges through Talon's released LLM gateway.
    # The upstream provider is explicitly a synthetic OpenAI-compatible fixture.
    trace_stream = io.StringIO()
    with contextlib.redirect_stdout(trace_stream):
        outcome = run_live_chat(
            "Compare the last six months of department attrition based on available metrics.",
            offered, session, "gpt-4o-mini",
            args.gateway.rstrip("/") + "/v1/proxy/openai/v1/chat/completions",
            args.agent_key, tool_call
        )
    print(trace_stream.getvalue(), end="")
    events = [json.loads(line.split("HR_AI_TRACE ", 1)[1])
              for line in trace_stream.getvalue().splitlines()
              if line.startswith("HR_AI_TRACE ")]
    by_event = lambda name: [e for e in events if e.get("event") == name]
    assert len(by_event("llm.gateway.request")) == 2, events
    assert len(by_event("llm.gateway.response")) == 2, events
    assert len(by_event("llm.tool.request")) == 1, events
    assert len(by_event("llm.tool.response")) == 1, events
    assert {e["session"] for e in events} == {session}, events
    assert {e.get("provider_mode") for e in by_event("llm.gateway.request")} == {
        "simulated-openai-compatible-provider"}, events
    assert all(e["provider_response_id"] == "chatcmpl-hr-mock"
               for e in by_event("llm.gateway.response")), events
    assert all(e["usage"]["total_tokens"] == 50
               for e in by_event("llm.gateway.response")), events
    assert by_event("llm.tool.response")[0]["evidence_committed"] is True, events
    assert by_event("llm.tool.response")[0]["evidence_id"], events
    assert all(e.get("request_payload", "").startswith("[metadata only")
               for e in by_event("llm.gateway.request")), events
    assert all(e.get("response_payload") == "[metadata only]"
               for e in by_event("llm.gateway.response")), events
    assert "sk-demo-mock-provider" not in trace_stream.getvalue(), "Credential leaked in trace"
    print("PASS: observed 2 actual Talon LLM gateway requests/responses, one allowed tool, "
          "session/evidence correlation, simulated provider labeled and prompts not logged")
    assert outcome["mode"].startswith("live AI through Talon"), outcome
    assert len(outcome["calls"]) == 1, outcome
    called = outcome["calls"][0]
    assert called["name"] == "hr_attrition_summary", outcome
    receipt = called["governance"]
    assert receipt["decision"] == "allow" and receipt["evidence"]["committed"] is True, receipt
    assert "descriptive aggregate" in outcome["answer"], outcome["answer"]

    after = get(args.hr + "/debug/counters")
    assert after["hr_attrition_summary"] == before["hr_attrition_summary"] + 1, (before, after)
    assert after["hr_employee_export"] == before["hr_employee_export"] == 0, (before, after)
    model = get(args.model_upstream + "/debug/status")
    assert model["completions"] == 2 and model["with_tool_result"] == 1, model

    evidence_id = receipt["evidence"]["id"]
    audit = subprocess.run([args.talon_bin, "audit", "verify", evidence_id],
                           capture_output=True, text=True)
    assert audit.returncode == 0 and "VALID" in audit.stdout, (audit.stdout, audit.stderr)
    # Stronger cross-surface identity proof: independently export and verify the
    # complete current LLM+MCP session rather than trusting a UI counter.
    with tempfile.TemporaryDirectory() as temp:
        exported = str(Path(temp) / "signed.json")
        export = subprocess.run([
            args.talon_bin, "audit", "export", "--format", "signed-json",
            "--session", session, "--output", exported,
        ], capture_output=True, text=True)
        assert export.returncode == 0, (export.stdout, export.stderr)
        records = json.loads(Path(exported).read_text())["records"]
        assert len(records) >= 3, records  # two LLM model calls + one MCP tool call
        observed_agents = {record.get("agent_id") for record in records}
        assert observed_agents == {"hr-analytics-assistant"}, observed_agents
        verification = subprocess.run([args.talon_bin, "audit", "verify", "--file", exported],
                                      capture_output=True, text=True)
        assert verification.returncode == 0, verification.stderr
        for expected in ("Invalid records: 0", "Missing signature: 0", "Could not parse: 0"):
            assert expected in verification.stdout, verification.stdout
        print(f"PASS: {len(records)} signed LLM/MCP records tied to one agent + session")

    print("PASS: real Talon LLM gateway forwarded two turns to isolated synthetic provider")
    print("PASS: synthetic model selected Talon-advertised aggregate tool")
    print("PASS: real Talon MCP proxy executed one permitted DuckDB aggregate")
    print("PASS: no privileged employee export dispatched to upstream")
    print("PASS: same session on LLM and MCP client paths:", session)
    print("PASS: Talon MCP evidence verified:", evidence_id)
    print("PASS: credential-free real Talon model-to-MCP integration")


if __name__ == "__main__":
    main()
