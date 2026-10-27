"""Persistent, deterministic DuckDB warehouse for synthetic People Analytics.

Only this module sees employee rows. All public analytics tool methods return
approved aggregates; do NOT expose SQL execution to AI agents.
"""
from __future__ import annotations

import os
import random
import tempfile
from pathlib import Path
from datetime import date, timedelta

import duckdb
import pandas as pd

from upstream_hr.data.generate_sample_data import build_employees

PERIOD = "2026-09"
AS_OF = date(2026, 9, 30)
MIN_COHORT = 10
DEFAULT_PATH = Path(__file__).resolve().parent / ".state" / "hr-warehouse.duckdb"


def database_path() -> Path:
    return Path(os.getenv("HR_DEMO_DB_PATH", str(DEFAULT_PATH))).expanduser().resolve()


def seed(force: bool = False) -> dict:
    """Create one local immutable fixture in an atomic rename; never embed real HR data."""
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return {"path": str(path), "seeded": False, "employees": row_count()}
    frame = build_employees(1200, PERIOD, random.Random(42))
    frame["hire_date"] = pd.to_datetime(frame["hire_date"]).dt.date
    frame["termination_date"] = pd.to_datetime(frame["termination_date"]).dt.date
    fd, staged = tempfile.mkstemp(dir=path.parent, prefix="hr-seed-", suffix=".duckdb")
    os.close(fd)
    os.unlink(staged)
    try:
        with duckdb.connect(staged) as conn:
            conn.register("seed_rows", frame)
            conn.execute("CREATE TABLE employees AS SELECT * FROM seed_rows")
            conn.execute("CREATE UNIQUE INDEX employees_id ON employees(employee_id)")
            conn.execute("CREATE INDEX employees_dept ON employees(department)")
            count = conn.execute("SELECT count(*) FROM employees").fetchone()[0]
            assert count == 1200
        os.replace(staged, path)
    finally:
        if os.path.exists(staged):
            os.unlink(staged)
    return {"path": str(path), "seeded": True, "employees": count}


def _connect():
    path = database_path()
    if not path.is_file():
        raise RuntimeError("Synthetic HR DuckDB not seeded. Run: python3 warehouse.py seed")
    return duckdb.connect(str(path), read_only=True)


def sql_rows(query: str, params: tuple = ()) -> list[dict]:
    with _connect() as conn:
        out = conn.execute(query, params)
        cols = [d[0] for d in out.description]
        return [dict(zip(cols, row)) for row in out.fetchall()]


"""Exactly two reviewed SQL statements; arbitrary SQL is never forwarded from the UI."""
SQL_PRESETS = {
    'all': 'SELECT department, COUNT(*) AS employees FROM employees GROUP BY department ORDER BY department',
    'active': 'SELECT department, COUNT(*) AS active_headcount FROM employees WHERE termination_date IS NULL GROUP BY department ORDER BY department',
}


def approved_sql(sql: str) -> dict:
    import re
    if not isinstance(sql, str) or len(sql) > 1200:
        raise ValueError('SQL must be a short aggregate SELECT')
    normalized = re.sub(r'\s+', ' ', sql.strip().rstrip(';')).casefold()
    matched = next((name for name, template in SQL_PRESETS.items()
                    if normalized == template.casefold()), None)
    if matched is None:
        raise ValueError('Only reviewed, department-grouped aggregate SELECTs are supported')
    statement = SQL_PRESETS[matched].replace(' ORDER BY department',
                                              ' HAVING COUNT(*) >= ? ORDER BY department')
    rows = sql_rows(statement, (MIN_COHORT,))
    return {'query_id':matched, 'columns':list(rows[0]) if rows else [],
            'rows':rows, 'minimum_cohort_size':MIN_COHORT, 'synthetic':True}


def row_count() -> int:
    return sql_rows("SELECT COUNT(*) AS n FROM employees")[0]["n"]


def departments() -> list[str]:
    return [r["department"] for r in sql_rows("SELECT DISTINCT department FROM employees ORDER BY department")]


def _valid(department: str):
    if not isinstance(department, str) or (department and department not in departments()):
        raise ValueError("Unknown department")


def _last_months(n: int):
    y, m = AS_OF.year, AS_OF.month
    out = []
    for offset in range(n - 1, -1, -1):
        idx = y * 12 + (m - 1) - offset
        year, month = divmod(idx, 12)
        start = date(year, month + 1, 1)
        next_month = date(year + 1, 1, 1) if month == 11 else date(year, month + 2, 1)
        out.append((start, next_month - timedelta(days=1)))
    return out


def _active_cond(start: str = "hire_date", end: str = "termination_date"):
    return f"({start} <= ? AND ({end} IS NULL OR {end} > ?))"


def _attrition_month(department: str, start: date, end: date) -> list[dict]:
    previous = start - timedelta(days=1)
    stmt = """
        SELECT department,
          COUNT(*) FILTER (WHERE hire_date <= ? AND
             (termination_date IS NULL OR termination_date > ?)) AS hc_start,
          COUNT(*) FILTER (WHERE hire_date <= ? AND
             (termination_date IS NULL OR termination_date > ?)) AS hc_end,
          COUNT(*) FILTER (WHERE termination_date BETWEEN ? AND ?) AS terminations
        FROM employees WHERE (? = '' OR department = ?)
        GROUP BY department ORDER BY department
    """
    return sql_rows(stmt, (previous, previous, end, end, start, end, department, department))


def attrition_summary(department: str = "", months: int = 6) -> dict:
    _valid(department)
    if type(months) is not int or not 1 <= months <= 12:
        raise ValueError("months must be 1–12")
    grouped = {}
    for start, end in _last_months(months):
        for r in _attrition_month(department, start, end):
            avg = (r["hc_start"] + r["hc_end"]) / 2
            if avg < MIN_COHORT:
                continue
            rate = round(100 * r["terminations"] / avg, 2)
            grouped.setdefault(r["department"], []).append({
                "month": end.strftime("%Y-%m"),
                "attrition_rate_pct": rate, "terminations": int(r["terminations"]),
                "headcount_end": int(r["hc_end"])
            })
    cohorts = []
    for dept, rows in sorted(grouped.items()):
        if len(rows) == months:
            cohorts.append({"department": dept, "months": rows,
                            "change_pp": round(rows[-1]["attrition_rate_pct"] -
                                               rows[0]["attrition_rate_pct"], 2)})
    return {"metric": "monthly terminations / average headcount, %", "period": PERIOD,
            "source": "DuckDB synthetic employee lifecycle warehouse", "cohorts": cohorts,
            "interpretation": "descriptive trend only; no causal inference",
            "minimum_cohort_size": MIN_COHORT}


def headcount_summary(department: str = "") -> dict:
    _valid(department)
    rows = sql_rows("""
      SELECT department, COUNT(*) AS active_headcount FROM employees
      WHERE hire_date <= ? AND (termination_date IS NULL OR termination_date > ?)
        AND (? = '' OR department = ?)
      GROUP BY department HAVING COUNT(*) >= ? ORDER BY department
    """, (AS_OF, AS_OF, department, department, MIN_COHORT))
    return {"as_of": AS_OF.isoformat(), "departments": rows, "minimum_cohort_size": MIN_COHORT}


def tenure_summary(department: str = "") -> dict:
    _valid(department)
    base = """
        FROM employees WHERE hire_date <= ?
        AND (termination_date IS NULL OR termination_date > ?)
        AND (? = '' OR department = ?)
    """
    params = (AS_OF, AS_OF, department, department)
    avg = sql_rows("SELECT ROUND(AVG(date_diff('day', hire_date, ?)/365.25), 2) AS years " +
                   base, (AS_OF,) + params)[0]["years"]
    rows = sql_rows("""
      SELECT CASE WHEN date_diff('day', hire_date, ?)/365.25 < 1 THEN '<1 year'
                  WHEN date_diff('day', hire_date, ?)/365.25 < 3 THEN '1–3 years'
                  WHEN date_diff('day', hire_date, ?)/365.25 < 5 THEN '3–5 years'
                  ELSE '5+ years' END AS tenure_band,
             COUNT(*) AS headcount
    """ + base + " GROUP BY tenure_band HAVING COUNT(*) >= ?",
         (AS_OF, AS_OF, AS_OF) + params + (MIN_COHORT,))
    ordered = ["<1 year", "1–3 years", "3–5 years", "5+ years"]
    rows.sort(key=lambda r: ordered.index(r["tenure_band"]))
    return {"department": department or "all", "as_of": AS_OF.isoformat(),
            "average_tenure_years": float(avg) if avg is not None else None,
            "bands": rows, "minimum_cohort_size": MIN_COHORT}


def privileged_employee_detail() -> dict:
    """Unsafe demo-only tool. Talon policy MUST block before dispatch."""
    return {"synthetic": True, "employees": sql_rows("""
      SELECT employee_id, full_name, department, monthly_salary_mxn
      FROM employees ORDER BY employee_id LIMIT 8
    """)}


def dashboard_summary(department: str = "") -> dict:
    _valid(department)
    counts = headcount_summary(department)["departments"]
    hc = sum(r["active_headcount"] for r in counts)
    if hc < MIN_COHORT:
        raise ValueError("Cohort too small")
    months = _last_months(12)
    timeline = []
    for start, end in months:
        rows = _attrition_month(department, start, end)
        start_n = sum(r["hc_start"] for r in rows)
        end_n = sum(r["hc_end"] for r in rows)
        terms = sum(r["terminations"] for r in rows)
        avg = (start_n + end_n) / 2
        if avg >= MIN_COHORT:
            timeline.append({"month": end.strftime("%Y-%m"),
                             "attrition_rate_pct": round(100 * terms / avg, 2),
                             "terminations": terms, "headcount_end": end_n})
    tenure = tenure_summary(department)["average_tenure_years"]
    return {"department": department or "All departments", "departments": departments(),
            "headcount": hc, "headcount_by_department": counts, "average_tenure_years": tenure,
            "latest_attrition_pct": timeline[-1]["attrition_rate_pct"] if timeline else 0,
            "attrition_12m": timeline, "data_period": PERIOD, "synthetic": True,
            "warehouse": "DuckDB"}


def cli():
    import argparse
    parser = argparse.ArgumentParser(description="Fictional People Analytics DuckDB seed")
    parser.add_argument("command", choices=["seed", "status"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    import json
    print(json.dumps(seed(force=args.force) if args.command == "seed" else {
        "path": str(database_path()), "employees": row_count()}, indent=2))


if __name__ == "__main__":
    cli()
