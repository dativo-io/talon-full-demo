"""Joins and People metrics.

The same LEFT JOIN is implemented twice on purpose:
  * join_pandas()  -> pandas.merge
  * join_sql()     -> SQL executed in an in-memory SQLite via pandas.read_sql
Both must return the same row count (asserted in tests) so the repo shows
SQL and Python side by side.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

JOIN_SQL = """
SELECT e.*,
       p.gross_pay_mxn, p.gross_pay_prev_mxn, p.base_salary_mxn, p.variable_pay_mxn,
       c.imss_status, c.infonavit_status, c.contract_end_date, c.last_audit
FROM employees e
LEFT JOIN payroll    p ON p.employee_id = e.employee_id
LEFT JOIN compliance c ON c.employee_id = e.employee_id
ORDER BY e.employee_id
"""


def period_bounds(period: str) -> tuple[date, date]:
    y, m = (int(x) for x in period.split("-"))
    start = date(y, m, 1)
    end = (date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)) - timedelta(days=1)
    return start, end


def join_pandas(employees: pd.DataFrame, payroll: pd.DataFrame, compliance: pd.DataFrame) -> pd.DataFrame:
    pay_cols = ["employee_id", "gross_pay_mxn", "gross_pay_prev_mxn", "base_salary_mxn", "variable_pay_mxn"]
    comp_cols = ["employee_id", "imss_status", "infonavit_status", "contract_end_date", "last_audit"]
    out = (employees
           .merge(payroll[pay_cols], on="employee_id", how="left", validate="one_to_one")
           .merge(compliance[comp_cols], on="employee_id", how="left", validate="one_to_one"))
    return out.sort_values("employee_id").reset_index(drop=True)


def join_sql(employees: pd.DataFrame, payroll: pd.DataFrame, compliance: pd.DataFrame) -> pd.DataFrame:
    with sqlite3.connect(":memory:") as con:
        employees.to_sql("employees", con, index=False)
        payroll.to_sql("payroll", con, index=False)
        compliance.to_sql("compliance", con, index=False)
        out = pd.read_sql(JOIN_SQL, con)
    for col in ("hire_date", "termination_date", "contract_end_date", "last_audit"):
        out[col] = pd.to_datetime(out[col], errors="coerce")
    out["imss_registered"] = out["imss_registered"].astype(bool)
    return out


@dataclass
class Metrics:
    master: pd.DataFrame
    summary: dict
    headcount: pd.DataFrame
    turnover: pd.DataFrame
    payroll_variance: pd.DataFrame
    compliance_gaps: pd.DataFrame
    unmatched_payroll: pd.DataFrame


def _active_at(df: pd.DataFrame, as_of: pd.Timestamp) -> pd.Series:
    return (df["hire_date"] <= as_of) & (df["termination_date"].isna() | (df["termination_date"] > as_of))


def headcount_table(master: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    active = master[_active_at(master, as_of)]
    hc = active.pivot_table(index="department", columns="site", values="employee_id",
                            aggfunc="count", fill_value=0)
    hc["Total"] = hc.sum(axis=1)
    hc.loc["Total"] = hc.sum()
    return hc.reset_index()


def turnover_trend(master: pd.DataFrame, period: str, months: int = 12) -> pd.DataFrame:
    """Monthly turnover = terminations / average headcount, trailing `months`."""
    _, end = period_bounds(period)
    rows = []
    end_ts = pd.Timestamp(end)
    for k in range(months - 1, -1, -1):
        m_end = (end_ts - pd.DateOffset(months=k)) + pd.offsets.MonthEnd(0)
        m_start = m_end.replace(day=1)
        hc_start = int(_active_at(master, m_start - pd.Timedelta(days=1)).sum())
        hc_end = int(_active_at(master, m_end).sum())
        terms = int(master["termination_date"].between(m_start, m_end).sum())
        hires = int(master["hire_date"].between(m_start, m_end).sum())
        avg_hc = (hc_start + hc_end) / 2 or 1
        rows.append({"month": m_end.strftime("%Y-%m"), "headcount_start": hc_start, "hires": hires,
                     "terminations": terms, "headcount_end": hc_end,
                     "turnover_rate_pct": round(100 * terms / avg_hc, 2)})
    return pd.DataFrame(rows)


def average_tenure_years(master: pd.DataFrame, as_of: pd.Timestamp) -> float:
    active = master[_active_at(master, as_of)]
    return round(float(((as_of - active["hire_date"]).dt.days / 365.25).mean()), 2)


def payroll_variance(master: pd.DataFrame, threshold_pct: float = 10.0) -> pd.DataFrame:
    paid = master.dropna(subset=["gross_pay_mxn", "gross_pay_prev_mxn"])
    g = paid.groupby("department").agg(employees_paid=("employee_id", "count"),
                                       gross_pay_mxn=("gross_pay_mxn", "sum"),
                                       gross_pay_prev_mxn=("gross_pay_prev_mxn", "sum")).reset_index()
    g["variance_mxn"] = (g["gross_pay_mxn"] - g["gross_pay_prev_mxn"]).round(2)
    g["variance_pct"] = (100 * g["variance_mxn"] / g["gross_pay_prev_mxn"]).round(2)
    g["flag"] = g["variance_pct"].abs().gt(threshold_pct).map({True: "REVIEW", False: ""})
    return g.sort_values("variance_pct", key=abs, ascending=False).reset_index(drop=True)


def compliance_gaps(master: pd.DataFrame, as_of: pd.Timestamp, horizon_days: int = 30) -> pd.DataFrame:
    active = _active_at(master, as_of)
    issues = []

    def flag(mask, issue, severity):
        for _, r in master[mask].iterrows():
            issues.append({"employee_id": r["employee_id"], "full_name": r["full_name"],
                           "department": r["department"], "site": r["site"],
                           "issue": issue, "severity": severity,
                           "detail": str(r.get("contract_end_date", ""))[:10] if "contract" in issue else r.get("imss_status")})

    flag(active & master["imss_status"].isna(), "Not found in compliance DB", "HIGH")
    flag(active & master["imss_status"].isin(["MISSING", "PENDING"]), "IMSS registration missing/pending", "HIGH")
    flag(active & (~master["imss_registered"]) & master["imss_status"].eq("ACTIVE"),
         "HRIS says not registered but IMSS active (data conflict)", "MEDIUM")
    flag((~active) & master["termination_date"].notna() & master["imss_status"].eq("ACTIVE"),
         "Terminated but IMSS still ACTIVE (baja pending)", "HIGH")
    flag(active & master["contract_end_date"].between(as_of, as_of + pd.Timedelta(days=horizon_days)),
         f"Contract expires within {horizon_days} days", "MEDIUM")
    flag(active & master["contract_end_date"].lt(as_of), "Contract already expired (renewal missing)", "HIGH")
    flag(active & master["infonavit_status"].eq("PENDING_DOCS"), "INFONAVIT documents pending", "LOW")
    cols = ["employee_id", "full_name", "department", "site", "issue", "severity", "detail"]
    out = pd.DataFrame(issues, columns=cols)
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    return out.sort_values(["severity", "employee_id"], key=lambda s: s.map(order) if s.name == "severity" else s).reset_index(drop=True)


def build_metrics(clean: dict[str, pd.DataFrame], period: str, engine: str = "pandas") -> Metrics:
    emp, pay, comp = clean["employees"], clean["payroll"], clean["compliance"]
    master = join_pandas(emp, pay, comp) if engine == "pandas" else join_sql(emp, pay, comp)
    _, end = period_bounds(period)
    as_of = pd.Timestamp(end)

    hc = headcount_table(master, as_of)
    to = turnover_trend(master, period)
    pv = payroll_variance(master)
    gaps = compliance_gaps(master, as_of)
    unmatched = pay[~pay["employee_id"].isin(emp["employee_id"])].reset_index(drop=True)

    active_n = int(_active_at(master, as_of).sum())
    start_ts = pd.Timestamp(period_bounds(period)[0])
    summary = {
        "period": period,
        "employees_in_hris": int(len(emp)),
        "active_headcount": active_n,
        "hires_in_period": int(master["hire_date"].between(start_ts, as_of).sum()),
        "terminations_in_period": int(master["termination_date"].between(start_ts, as_of).sum()),
        "monthly_turnover_pct": float(to.iloc[-1]["turnover_rate_pct"]),
        "trailing_12m_turnover_pct": round(float(to["terminations"].sum() / (to["headcount_end"].mean() or 1) * 100), 2),
        "average_tenure_years": average_tenure_years(master, as_of),
        "total_gross_payroll_mxn": round(float(pv["gross_pay_mxn"].sum()), 2),
        "payroll_variance_pct": round(float(100 * pv["variance_mxn"].sum() / (pv["gross_pay_prev_mxn"].sum() or 1)), 2),
        "active_without_payroll": int((_active_at(master, as_of) & master["gross_pay_mxn"].isna()).sum()),
        "payroll_rows_without_employee": int(len(unmatched)),
        "compliance_alerts": int(len(gaps)),
        "compliance_alerts_high": int((gaps["severity"] == "HIGH").sum()),
    }
    return Metrics(master, summary, hc, to, pv, gaps, unmatched)
