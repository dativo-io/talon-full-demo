"""Structured, bounded, opt-in demo tracing of real routed request/response events.

App-observed LLM response ≠ packet capture of provider HTTPS. Never log API keys.
Verbose payload previews must ONLY be used with the synthetic HR fixture.
"""
import json
import os
import re
import time

_BLOCKED = re.compile(r"(authorization|api[_-]?key|password|secret|credential|token)$", re.I)

def _scrub(value, level=0):
    if level > 6:
        return "[truncated depth]"
    if isinstance(value, dict):
        return {str(k): ("[redacted]" if _BLOCKED.search(str(k)) else _scrub(v, level + 1))
                for k, v in list(value.items())[:30]}
    if isinstance(value, list):
        return [_scrub(x, level + 1) for x in value[:15]]
    if isinstance(value, str):
        value = re.sub(r"sk-[A-Za-z0-9_-]{8,}", "[redacted key]", value)
        value = re.sub(r"Bearer\\s+\\S+", "Bearer [redacted]", value, flags=re.I)
        return value[:1600] + ("…[truncated]" if len(value) > 1600 else "")
    return value

def trace(kind, session, **fields):
    if os.getenv("HR_DEMO_TRACE", "1") != "1":
        return
    record = {"event": kind, "session": session, "ts_unix_ms": int(time.time() * 1000),
              "observer": "demo-application (not provider wire capture)"}
    record.update(_scrub(fields))
    print("HR_AI_TRACE " + json.dumps(record, ensure_ascii=False, separators=(",", ":")),
          flush=True)

def previews_enabled():
    return os.getenv("HR_DEMO_TRACE_PAYLOADS", "0") == "1"
