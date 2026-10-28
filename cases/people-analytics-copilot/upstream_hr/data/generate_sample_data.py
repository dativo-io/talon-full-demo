"""Generate SYNTHETIC HR data for the pipeline demo.

Everything produced here is fake: names are "Empleado NNN", IDs are
sequential "EMP-NNNN", and no real CURP/RFC/NSS-like identifiers are created.
Three heterogeneous sources are written so the pipeline can demonstrate
extraction, cleaning and joining across systems:

  data/raw/employees.xlsx        -> HRIS export (clean, canonical keys)
  data/raw/payroll_<period>.csv  -> payroll system (different key names, dirty)
  data/raw/compliance.sqlite     -> compliance DB (IMSS / INFONAVIT / contracts)

Run directly:  python3 data/generate_sample_data.py --period 2026-07
"""
from __future__ import annotations

import argparse
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent / "raw"

DEPARTMENTS = ["Engineering", "Product", "Risk", "Operations", "Finance",
               "People", "Sales", "Customer Support", "Compliance"]
SITES = ["CDMX", "Querétaro", "Guadalajara", "Remote"]
SITE_WEIGHTS = [0.45, 0.2, 0.2, 0.15]
JOB_LEVELS = ["Analyst", "Senior Analyst", "Specialist", "Manager", "Director"]
LEVEL_WEIGHTS = [0.35, 0.25, 0.2, 0.15, 0.05]
SALARY_BANDS_MXN = {  # monthly gross, synthetic
    "Analyst": (22000, 38000),
    "Senior Analyst": (35000, 55000),
    "Specialist": (45000, 70000),
    "Manager": (70000, 120000),
    "Director": (120000, 220000),
}
CONTRACT_TYPES = ["Indefinido", "Temporal", "Por obra"]


def _period_bounds(period: str) -> tuple[date, date]:
    year, month = (int(x) for x in period.split("-"))
    start = date(year, month, 1)
    end = (date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)) - timedelta(days=1)
    return start, end


def build_employees(n: int, period: str, rng: random.Random) -> pd.DataFrame:
    _, period_end = _period_bounds(period)
    rows = []
    for i in range(1, n + 1):
        level = rng.choices(JOB_LEVELS, LEVEL_WEIGHTS)[0]
        lo, hi = SALARY_BANDS_MXN[level]
        hire = period_end - timedelta(days=rng.randint(15, 365 * 7))
        # ~12% of employees have terminated at some point in the last 18 months
        term = None
        if rng.random() < 0.12:
            earliest = max(hire + timedelta(days=30), period_end - timedelta(days=540))
            if earliest < period_end:
                term = earliest + timedelta(days=rng.randint(0, (period_end - earliest).days))
        rows.append({
            "employee_id": f"EMP-{i:04d}",
            "full_name": f"Empleado {i:03d}",
            "department": rng.choice(DEPARTMENTS),
            "site": rng.choices(SITES, SITE_WEIGHTS)[0],
            "job_level": level,
            "hire_date": hire,
            "termination_date": term,
            "monthly_salary_mxn": round(rng.uniform(lo, hi), -2),
            "imss_registered": rng.random() > 0.04,
            "contract_type": rng.choices(CONTRACT_TYPES, [0.8, 0.15, 0.05])[0],
        })
    return pd.DataFrame(rows)


def _messy_id(emp_id: str, rng: random.Random) -> str:
    """Return the payroll system's rendering of an ID (lowercase, padded, etc.)."""
    styles = [
        lambda s: s,
        lambda s: s.lower(),
        lambda s: f"  {s} ",
        lambda s: s.replace("-", ""),
        lambda s: f"{s}\t",
    ]
    return rng.choice(styles)(emp_id)


def build_payroll(emp: pd.DataFrame, period: str, rng: random.Random) -> pd.DataFrame:
    """Payroll export: different column names, dirty values, duplicates, orphans."""
    _, period_end = _period_bounds(period)
    active = emp[emp["termination_date"].isna() | (emp["termination_date"] >= period_end.replace(day=1))]
    rows = []
    for _, e in active.iterrows():
        base = float(e["monthly_salary_mxn"])
        # payroll = base + variable pay - deductions, with a bit of noise
        variable = round(base * rng.choice([0, 0, 0, 0.05, 0.1]), 2)
        gross = round(base + variable, 2)
        dept = e["department"]
        dept = rng.choice([dept, dept.upper(), dept.lower(), f" {dept} "])
        rows.append({
            "EmpID": _messy_id(e["employee_id"], rng),
            "Nombre": e["full_name"],
            "Depto": dept,
            "Sede": e["site"],
            "SalarioBase": base,
            "Variable": variable,
            "Bruto": gross,
            "Periodo": period,
        })
    df = pd.DataFrame(rows)

    # Previous-month column to allow variance analysis (noise +-8 %, a few spikes)
    prev = []
    for g in df["Bruto"]:
        factor = rng.uniform(0.92, 1.08) if rng.random() > 0.05 else rng.uniform(0.6, 1.5)
        prev.append(round(float(g) * factor, 2))
    df["BrutoMesAnterior"] = prev

    # --- deliberately dirty rows ---
    dup = df.sample(6, random_state=1)                      # exact duplicates
    df = pd.concat([df, dup], ignore_index=True)
    missing = df.sample(3, random_state=2).copy()           # missing IDs
    missing["EmpID"] = None
    df = pd.concat([df, missing], ignore_index=True)
    orphans = pd.DataFrame([{                               # IDs not in HRIS
        "EmpID": f"EMP-{9000 + k:04d}", "Nombre": f"Empleado Temporal {k}",
        "Depto": "Operations", "Sede": "CDMX", "SalarioBase": 25000.0,
        "Variable": 0.0, "Bruto": 25000.0, "Periodo": period, "BrutoMesAnterior": 25000.0,
    } for k in range(1, 4)])
    df = pd.concat([df, orphans], ignore_index=True)
    # one negative salary and one salary stored as text with thousands separator
    df.loc[df.index[5], "Bruto"] = -1500.0
    df["Bruto"] = df["Bruto"].astype(object)
    df.loc[df.index[7], "Bruto"] = "48,500.00"
    return df.sample(frac=1, random_state=3).reset_index(drop=True)


def build_compliance(emp: pd.DataFrame, period: str, rng: random.Random) -> pd.DataFrame:
    _, period_end = _period_bounds(period)
    rows = []
    for _, e in emp.iterrows():
        if e["contract_type"] == "Indefinido":
            contract_end = None
        else:
            contract_end = period_end + timedelta(days=rng.randint(-20, 180))
        imss_status = "ACTIVE" if e["imss_registered"] else rng.choice(["PENDING", "MISSING"])
        if pd.notna(e["termination_date"]):
            imss_status = rng.choice(["DEREGISTERED", "ACTIVE"])  # ACTIVE here = a gap to flag
        rows.append({
            "emp_id": e["employee_id"],
            "imss_status": imss_status,
            "infonavit_status": rng.choices(["NONE", "ACTIVE_CREDIT", "PENDING_DOCS"], [0.6, 0.3, 0.1])[0],
            "contract_end_date": contract_end.isoformat() if contract_end else None,
            "last_audit": (period_end - timedelta(days=rng.randint(0, 400))).isoformat(),
        })
    comp = pd.DataFrame(rows)
    # a few employees never made it into the compliance DB (coverage gap)
    return comp.drop(comp.sample(5, random_state=4).index).reset_index(drop=True)


def generate(period: str = "2026-07", n_employees: int = 300, seed: int = 42,
             raw_dir: Path = RAW_DIR) -> dict[str, Path]:
    rng = random.Random(seed)
    raw_dir.mkdir(parents=True, exist_ok=True)

    emp = build_employees(n_employees, period, rng)
    payroll = build_payroll(emp, period, rng)
    comp = build_compliance(emp, period, rng)

    xlsx_path = raw_dir / "employees.xlsx"
    csv_path = raw_dir / f"payroll_{period.replace('-', '_')}.csv"
    db_path = raw_dir / "compliance.sqlite"

    emp_out = emp.copy()
    for col in ("hire_date", "termination_date"):
        emp_out[col] = pd.to_datetime(emp_out[col])
    emp_out.to_excel(xlsx_path, sheet_name="Employees", index=False)
    payroll.to_csv(csv_path, index=False)

    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as con:
        comp.to_sql("compliance", con, index=False)
        con.execute("CREATE INDEX idx_compliance_emp ON compliance(emp_id)")

    return {"employees": xlsx_path, "payroll": csv_path, "compliance": db_path}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate synthetic HR sources")
    ap.add_argument("--period", default="2026-07", help="YYYY-MM")
    ap.add_argument("--employees", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    paths = generate(args.period, args.employees, args.seed)
    for name, p in paths.items():
        print(f"{name:<11} -> {p}")
