"""Self-contained Plotly HTML dashboard (no external assets at runtime)."""
from __future__ import annotations

from html import escape
from pathlib import Path

import plotly.graph_objects as go
import plotly.io as pio

from .transform import Metrics

NAVY, BLUE, GRAY, RED, AMBER = "#1F3C6E", "#4A6FA5", "#5A6472", "#C0392B", "#D68910"
LAYOUT = dict(font=dict(family="Arial, sans-serif", size=13, color="#1A1A1A"),
              paper_bgcolor="white", plot_bgcolor="white", margin=dict(l=50, r=20, t=50, b=50))


def _kpi(label: str, value, suffix: str = "") -> str:
    return (f'<div class="kpi"><div class="kpi-value">{value}{suffix}</div>'
            f'<div class="kpi-label">{escape(label)}</div></div>')


def _fig_html(fig: go.Figure, include_js: bool) -> str:
    fig.update_layout(**LAYOUT)
    return pio.to_html(fig, full_html=False, include_plotlyjs="inline" if include_js else False,
                       config={"displayModeBar": False})


def build_dashboard(metrics: Metrics, out_dir: Path | str, period: str) -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    s = metrics.summary

    # 1. Headcount by site (stacked by department)
    hc = metrics.headcount[metrics.headcount["department"] != "Total"].set_index("department")
    sites = [c for c in hc.columns if c != "Total"]
    fig_hc = go.Figure([go.Bar(name=dept, x=sites, y=hc.loc[dept, sites].values) for dept in hc.index])
    fig_hc.update_layout(barmode="stack", title="Active headcount by site and department",
                         legend=dict(orientation="h", y=-0.25), colorway=[NAVY, BLUE, "#7F9CC9", GRAY, "#9AA5B1",
                                                                           "#C5D0DE", "#2E5A9C", "#8EA9D6", "#B0BCCB"])

    # 2. Turnover trend
    to = metrics.turnover
    fig_to = go.Figure()
    fig_to.add_bar(x=to["month"], y=to["terminations"], name="Terminations", marker_color="#C5D0DE", yaxis="y2")
    fig_to.add_scatter(x=to["month"], y=to["turnover_rate_pct"], name="Turnover %", mode="lines+markers",
                       line=dict(color=NAVY, width=3))
    fig_to.update_layout(title="Monthly turnover, trailing 12 months",
                         yaxis=dict(title="Turnover %"), yaxis2=dict(title="Terminations", overlaying="y", side="right"),
                         legend=dict(orientation="h", y=-0.25))

    # 3. Payroll variance by department
    pv = metrics.payroll_variance.sort_values("variance_pct")
    colors = [RED if f == "REVIEW" else BLUE for f in pv["flag"]]
    fig_pv = go.Figure(go.Bar(x=pv["variance_pct"], y=pv["department"], orientation="h", marker_color=colors,
                              text=[f"{v:+.1f}%" for v in pv["variance_pct"]], textposition="outside"))
    fig_pv.update_layout(title="Gross payroll variance vs previous month (by department)",
                         xaxis=dict(title="% change", zeroline=True, zerolinecolor=GRAY))

    # 4. Compliance alerts table
    gaps = metrics.compliance_gaps
    sev_color = {"HIGH": "#F8D7DA", "MEDIUM": "#FFF3CD", "LOW": "#E2E3E5"}
    fig_tbl = go.Figure(go.Table(
        header=dict(values=[c.replace("_", " ").title() for c in gaps.columns], fill_color=NAVY,
                    font=dict(color="white", size=12), align="left"),
        cells=dict(values=[gaps[c].astype(str) for c in gaps.columns], align="left",
                   fill_color=[[sev_color.get(v, "white") for v in gaps["severity"]]] * len(gaps.columns))))
    fig_tbl.update_layout(title=f"Compliance alerts ({len(gaps)})", height=min(900, 120 + 26 * max(len(gaps), 1)))

    kpis = "".join([
        _kpi("Active headcount", s["active_headcount"]),
        _kpi("Monthly turnover", s["monthly_turnover_pct"], "%"),
        _kpi("Trailing 12m turnover", s["trailing_12m_turnover_pct"], "%"),
        _kpi("Average tenure", s["average_tenure_years"], " yrs"),
        _kpi("Gross payroll (MXN)", f"{s['total_gross_payroll_mxn']:,.0f}"),
        _kpi("Payroll variance", f"{s['payroll_variance_pct']:+.1f}", "%"),
        _kpi("Compliance alerts (high)", f"{s['compliance_alerts']} ({s['compliance_alerts_high']})"),
        _kpi("Payroll rows w/o employee", s["payroll_rows_without_employee"]),
    ])

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>People Dashboard {escape(period)}</title>
<style>
 body{{font-family:Arial,sans-serif;margin:0;background:#F4F6F9;color:#1A1A1A}}
 header{{background:{NAVY};color:#fff;padding:18px 32px}} header h1{{margin:0;font-size:22px}}
 header p{{margin:4px 0 0;opacity:.8;font-size:13px}}
 .wrap{{max-width:1280px;margin:0 auto;padding:24px 32px}}
 .kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-bottom:24px}}
 .kpi{{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
 .kpi-value{{font-size:26px;font-weight:bold;color:{NAVY}}} .kpi-label{{font-size:12px;color:{GRAY};margin-top:4px}}
 .grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}} .card{{background:#fff;border-radius:10px;padding:8px;box-shadow:0 1px 3px rgba(0,0,0,.08)}}
 .full{{grid-column:1/-1}} footer{{font-size:12px;color:{GRAY};padding:24px 32px;text-align:center}}
 @media(max-width:900px){{.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<header><h1>People Operations Dashboard — {escape(period)}</h1>
<p>Synthetic data · generated by hr-data-pipeline · {s['employees_in_hris']} employee records in HRIS</p></header>
<div class="wrap">
 <div class="kpis">{kpis}</div>
 <div class="grid">
  <div class="card">{_fig_html(fig_hc, True)}</div>
  <div class="card">{_fig_html(fig_to, False)}</div>
  <div class="card full">{_fig_html(fig_pv, False)}</div>
  <div class="card full">{_fig_html(fig_tbl, False)}</div>
 </div>
</div>
<footer>hr-data-pipeline · Francisco Moreno · all data in this page is synthetic</footer>
</body></html>"""
    path = out_dir / "dashboard.html"
    path.write_text(html, encoding="utf-8")
    return path
