# Talon operator UI screenshots for People Analytics

**Automated real native UI gate (current main):** `python scripts/test-people-analytics-operator-console.py` now runs the actual `talon-ui` Compose service over the SAME live HR/Talon data store, pairs Chromium using a one-time code from the process's private container log, visits all seven Console areas, checks HR's observed session and effective policy in the read-only API, and confirms no privileged console route. This gate is distinct from `scripts/test-people-analytics-browser.py` (the Workforce app). CI must PASS before claiming operator-browser acceptance; screenshot placeholders below remain placeholders and must not be presented as real captures.

The [People Analytics walkthrough](../README.md) includes five **screenshot slots**. They are intentionally text placeholders until a maintainer captures the real running installation; this PR does **not** ship mocked or generated UI screenshots.

Capture these in a browser at `http://127.0.0.1:8787/`, after pairing with the code from `docker compose -f compose.isolated.yaml --profile operator logs talon-ui`. Save the images in this directory using the filenames below, then replace the corresponding `> **Screenshot slot ...**` text in the case README with a Markdown image:

```markdown
![Descriptive screenshot caption](screenshots/01-talon-system.png)
```

| File to add | Capture | What the caption must not overclaim |
|---|---|---|
| `01-talon-system.png` | System: MCP endpoint running, gateway state, runtime freshness and evidence-store availability | In GUIDED mode the gateway is not started; evidence-store health does not imply data-plane liveness |
| `02-talon-effective-policy.png` | AI Use Cases → hr-analytics-assistant → Effective policy, with the forbidden `hr_employee_export` action and the Action Gateway policy's proof state | Loaded agent and gateway inputs are independent; a file edit without activation proves nothing |
| `03-talon-session-timeline.png` | Sessions → actual `hr-demo-...` session after an aggregate, forbidden export and HR SQL rejection | Talon-denied/not-dispatched and outcome-unknown/after-dispatch are distinct; do not synthesize absent records |
| `04-talon-evidence-verification.png` | Evidence record showing actual HMAC verification and an intercepted outcome | “Signature valid” is tamper evidence on read, not immutable storage or independent HR execution proof |
| `05-talon-costs-live.png` *(optional)* | Costs with genuine priced model traffic in LIVE mode; include currency and UTC window | GUIDED mode has no LLM spend; fleet UTC totals are not the per-session `talon costs --session` rollup |

### Seventh current-main area: Approvals (read only)

Core main now includes **Approvals** alongside Overview, AI Use Cases, Sessions, Costs, Configuration and System. Every governed MCP call in the People Analytics scenario is an Action Gateway operation, but none requires approval (aggregates allowed, export forbidden): the Approvals page can be honestly **empty**. A future optional real capture `06-talon-approvals-empty.png` must label it `No action approval requests in this HR run`, not claim approval enforcement or present a synthetic pending row. To demonstrate native human approval, use the Customer Support Action Gateway acceptance, which has an independent reviewer CLI/API, actual operation, signature and counting business adapter. Never add approve/reject buttons inside this read-only console. The seven-page browser acceptance has not been run against an official stable v1.17.0 artifact.

Use only synthetic case data. **Never include the one-time pairing code, `.env` values, admin/agent/provider/vault keys, browser cookie, or sensitive log text.** Crop browser chrome and any personal information. The screenshots are illustrations; the signed evidence, CLI verification and the independent HR counters remain the proof.

The operator console is separate from the workforce web app on port 8501. Do not confuse these images with the application dashboards or with the retired Talon dashboards.
