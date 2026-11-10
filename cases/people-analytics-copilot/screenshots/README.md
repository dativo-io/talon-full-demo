# Talon operator UI screenshots for People Analytics

The [People Analytics walkthrough](../README.md) includes five **screenshot slots**. They are intentionally text placeholders until a maintainer captures the real running installation; this PR does **not** ship mocked or generated UI screenshots.

Capture these in a browser at `http://127.0.0.1:8787/`, after pairing with the code from `docker compose -f compose.isolated.yaml logs talon-ui`. Save the images in this directory using the filenames below, then replace the corresponding `> **Screenshot slot ...**` text in the case README with a Markdown image:

```markdown
![Descriptive screenshot caption](screenshots/01-talon-system.png)
```

| File to add | Capture | What the caption must not overclaim |
|---|---|---|
| `01-talon-system.png` | System: MCP proxy running, gateway state, runtime freshness and evidence-store availability | In GUIDED mode the gateway is not started; evidence-store health does not imply data-plane liveness |
| `02-talon-effective-policy.png` | AI Use Cases → hr-analytics-assistant → Effective policy, with `hr_employee_export` rule and MCP boundary proof | Loaded agent/gateway/MCP inputs are independent; a file edit without activation proves nothing |
| `03-talon-session-timeline.png` | Sessions → actual `hr-demo-...` session after an aggregate, forbidden export and HR SQL rejection | Talon-denied/not-dispatched and HR-rejected/after-dispatch are distinct; do not synthesize absent records |
| `04-talon-evidence-verification.png` | Evidence record showing actual HMAC verification and an intercepted outcome | “Signature valid” is tamper evidence on read, not immutable storage or independent HR execution proof |
| `05-talon-costs-live.png` *(optional)* | Costs with genuine priced model traffic in LIVE mode; include currency and UTC window | GUIDED mode has no LLM spend; fleet UTC totals are not the per-session `talon costs --session` rollup |

Use only synthetic case data. **Never include the one-time pairing code, `.env` values, admin/agent/provider/vault keys, browser cookie, or sensitive log text.** Crop browser chrome and any personal information. The screenshots are illustrations; the signed evidence, CLI verification and the independent HR counters remain the proof.

The operator console is separate from the workforce web app on port 8501. Do not confuse these images with the application dashboards or with the retired Talon dashboards.
