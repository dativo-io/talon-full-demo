# One-browser workforce walkthrough

**Synthetic data only.** Docker isolates the workforce app from the private HR service and DuckDB file. Talon governs only model and MCP calls routed through it. The HR backend, not Talon, validates SQL query shapes. Signed evidence is tamper-evident, not immutable.

Open only **http://127.0.0.1:8501** after the [terminal startup](README.md). If remote, use `ssh -N -L 8501:127.0.0.1:8501 user@demo-host`.

1. Filter the **Workforce overview** by department. Chart reads use the separate fixed aggregate service—not Talon.
2. Run the first preset in **SQL workspace**. The actual `hr_aggregate_sql` MCP request goes through Talon; inspect its signed allow receipt and returned cohort-safe DuckDB result.
3. Replace SQL with `SELECT employee_id, full_name, monthly_salary_mxn FROM employees`. This is **HR_SQL_REJECTED**, an HR backend SQL validator decision, *not* a Talon policy denial. The tool-call receipt can still be `allow`.
4. Restore the first SQL. In the presenter terminal, remove `hr_aggregate_sql` from the editable **proxy** allowlist and run `reapply`. Repeat unchanged SQL in the browser. **Talon** must now deny pre-dispatch, with a committed evidence ID and unchanged backend counter. Restore the allowlist and `reapply` to confirm recovery.
5. Ask the AI for attrition trends. In **LIVE** mode, the model calls Talon's LLM gateway and selects an allowed MCP tool. GUIDED mode is explicitly marked **NO LLM**; it is only the offline rehearsal path.
6. Press **Attempt employee export through Talon**. This is a forced operator probe. Talon denies it before the HR backend.
7. Copy the session ID displayed on the page. In the terminal correlate `HR_AI_TRACE` events (`mcp.request`, `mcp.response`, and LIVE `llm.gateway.*`), the HR dispatch count, and the signed Talon audit records.

```bash
bash scripts/people-analytics-isolated.sh logs
# Exact terminal evidence inspection:
# docker compose -f ... --env-file ... exec -T talon-mcp talon audit list
```

By default traces contain **metadata**, not prompt/response bodies. An application-observed gateway response is not an HTTPS packet capture of OpenAI. Real external inference needs a paid provider smoke. No production HR data, IAM, SQL RBAC, DLP, or legal compliance claim is made.
