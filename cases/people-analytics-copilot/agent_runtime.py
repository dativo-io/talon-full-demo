"""Real model-driven chat through Talon's OpenAI-compatible LLM gateway and MCP proxy.

Every tool call travels through Talon. The model has no direct URL, DB credential
or access to the HR service. There is deliberately no ungoverned fallback path.
"""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from runtime_trace import trace, previews_enabled


def chat_completion(url, key, body, session):
    trace("llm.gateway.request", session, provider_mode=os.getenv("HR_DEMO_PROVIDER_KIND", "unverified upstream; inspect Talon gateway config"),
          gateway="Talon LLM", model=body.get("model"),
          offered_tools=[x["function"]["name"] for x in body.get("tools", [])],
          message_roles=[m.get("role") for m in body.get("messages", [])],
          tool_choice=body.get("tool_choice"),
          request_payload=body if previews_enabled() else "[metadata only; enable HR_DEMO_TRACE_PAYLOADS=1 for synthetic fixtures]")
    req = Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                  headers={"Content-Type": "application/json",
                           "Authorization": "Bearer " + key,
                           "X-Talon-Session-ID": session})
    try:
        with urlopen(req, timeout=90) as response:
            try:
                result = json.load(response)
                if (not isinstance(result, dict) or
                        not isinstance(result.get("choices"), list) or
                        not result["choices"]):
                    raise ValueError("Missing OpenAI-compatible choices")
            except (ValueError, UnicodeDecodeError) as error:
                trace("llm.gateway.error", session, failure="invalid_json_response")
                raise RuntimeError(
                    "Talon LLM gateway returned an empty or invalid JSON response; "
                    "inspect talon-gateway logs for the upstream failure"
                ) from error
            choice = (result.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            trace("llm.gateway.response", session, model=result.get("model"),
                  provider_response_id=result.get("id"),
                  finish_reason=choice.get("finish_reason"),
                  usage=result.get("usage"),
                  tool_calls=[x.get("function", {}).get("name") for x in msg.get("tool_calls") or []],
                  response_payload=result if previews_enabled() else "[metadata only]")
            return result
    except HTTPError as error:
        # Do not forward upstream error bodies: they may contain sensitive headers
        # or prompt fragments, and may not be JSON.
        error.read()
        trace("llm.gateway.error", session, http_status=error.code)
        hint = ("; check upstream HTTPS trust/connection in talon-gateway logs"
                if error.code in (502, 503, 504) else "; inspect talon-gateway logs")
        raise RuntimeError(f"Talon LLM gateway returned HTTP {error.code}{hint}") from error
    except URLError as error:
        trace("llm.gateway.error", session, failure="transport")
        raise RuntimeError("Talon LLM gateway is unreachable; check talon-gateway container logs") from error


def run_live_chat(prompt, tools, session, model, llm_url, llm_key, call_tool):
    """call_tool(name, args, session) -> (HTTP status, JSON-RPC response).

    Never assume a tool ran just because the model asked for it. Require a
    committed Talon allow receipt before accepting results as authorized.
    """
    if not llm_key or not llm_url:
        raise RuntimeError("Live AI mode needs TALON_LLM_URL and TALON_LLM_KEY")
    advertised = {t["name"]: t for t in tools}
    if not advertised:
        raise RuntimeError("No tools advertised by Talon")
    messages = [
        {"role": "system",
         "content": "You are an HR analytics assistant working only with synthetic demo data. "
                    "Use only tools discovered through Talon. "
                    "Call an appropriate tool before answering questions about workforce data. "
                    "Never invent figures, employee details, explanations for attrition, or causal claims. "
                    "If a requested tool is unavailable, explain that you cannot retrieve that data. "
                    "Describe trends and associations, not causes."},
        {"role": "user", "content": prompt},
    ]
    definitions = [{"type": "function", "function": {
        "name": t["name"], "description": t.get("description", ""),
        "parameters": t["inputSchema"],
    }} for t in tools]
    evidence = []
    for turn in range(3):
        resp = chat_completion(llm_url, llm_key, {
            "model": model, "messages": messages, "tools": definitions,
            # First turn must fetch facts rather than invent analysis.
            "tool_choice": "required" if turn == 0 else "auto",
            "max_tokens": 600,
            "temperature": 0,
        }, session)
        message = resp["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        if not calls:
            if not evidence:
                raise RuntimeError('Model answered without fetching governed HR data')
            answer = message.get("content")
            if not isinstance(answer, str):
                raise RuntimeError("No text answer from model")
            return {"answer": answer, "calls": evidence,
                    "mode": "live AI through Talon LLM and MCP"}
        messages.append(message)
        for call in calls:
            if call.get("type") != "function" or not isinstance(call.get("function"), dict):
                raise RuntimeError("Unsupported model tool call")
            name = call["function"].get("name")
            if name not in advertised:
                raise RuntimeError("Model requested an undiscovered tool: " + str(name))
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except json.JSONDecodeError as error:
                raise RuntimeError("Invalid model tool arguments") from error
            if not isinstance(args, dict):
                raise RuntimeError("Tool arguments must be an object")
            trace("llm.tool.request", session, tool=name,
                  arguments=args if previews_enabled() else "[metadata only]")
            status, out = call_tool(name, args, session)
            extension = out.get("result", {}).get("_meta", {}).get("io.dativo.talon/governance")
            if (status != 200 or "result" not in out or not extension
                    or extension.get("decision") != "allow"
                    or extension.get("evidence", {}).get("committed") is not True):
                raise RuntimeError("Talon did not authorize the MCP operation")
            trace("llm.tool.response", session, tool=name, http_status=status,
                  decision=extension.get("decision"),
                  evidence_id=extension.get("evidence", {}).get("id"),
                  evidence_committed=extension.get("evidence", {}).get("committed"))
            evidence.append({"name": name, "governance": extension})
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": json.dumps(out["result"]["content"])})
    raise RuntimeError("AI exceeded the maximum governed tool-loop iterations")
