"""Real model-driven chat through Talon's OpenAI-compatible LLM gateway and MCP proxy.

Every tool call travels through Talon. The model has no direct URL, DB credential
or access to the HR service. There is deliberately no ungoverned fallback path.
"""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def chat_completion(url, key, body, session):
    req = Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                  headers={"Content-Type": "application/json",
                           "Authorization": "Bearer " + key,
                           "X-Talon-Session-ID": session})
    try:
        with urlopen(req, timeout=90) as response:
            return json.load(response)
    except HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Talon LLM gateway returned HTTP {error.code}: {message[:350]}") from error


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
                    "Always call an available aggregate analytics tool before interpreting workforce data. "
                    "Never invent figures, individual employee details, explanations for attrition, or causal claims. "
                    "If asked for employee-level records, explain that you cannot access them; "
                    "offer a department/tenure aggregate instead. "
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
            status, out = call_tool(name, args, session)
            extension = out.get("result", {}).get("_meta", {}).get("io.dativo.talon/governance")
            if (status != 200 or "result" not in out or not extension
                    or extension.get("decision") != "allow"
                    or extension.get("evidence", {}).get("committed") is not True):
                raise RuntimeError("Talon did not authorize the MCP operation")
            evidence.append({"name": name, "governance": extension})
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": json.dumps(out["result"]["content"])})
    raise RuntimeError("AI exceeded the maximum governed tool-loop iterations")
