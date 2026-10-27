"""Render charts from already aggregated People Analytics metrics.

The chart renderer never imports DuckDB or receives raw employee rows.
"""
from __future__ import annotations

from html import escape
import plotly.graph_objects as go

from upstream_hr.hr_pipeline.dashboard import _fig_html, _kpi

def charts_html(stat: dict) -> str:
    history = stat["attrition_12m"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[x["month"] for x in history],
                             y=[x["attrition_rate_pct"] for x in history],
                             mode="lines+markers", name="Monthly attrition %"))
    fig.update_layout(title="12-month workforce attrition", yaxis_title="Attrition (%)",
                      height=300, margin=dict(l=55, r=15, t=65, b=45))
    department_counts = stat["headcount_by_department"]
    head = go.Figure(go.Bar(x=[x["department"] for x in department_counts],
                            y=[x["active_headcount"] for x in department_counts]))
    head.update_layout(title="Active headcount", height=300,
                       margin=dict(l=55, r=15, t=65, b=50))
    tiles = "".join([_kpi("Active headcount", stat["headcount"]),
                     _kpi("Latest monthly attrition", stat["latest_attrition_pct"], "%"),
                     _kpi("Average tenure", stat["average_tenure_years"], " years")])
    plot1 = _fig_html(fig, True)
    plot2 = _fig_html(head, False)
    return (
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        'body{font:14px system-ui;margin:0;background:white;color:#1b2c42}'
        '.kpis{display:flex;flex-wrap:wrap;gap:10px}.kpi{flex:1;min-width:110px;background:#f4f7fc;'
        'border-radius:9px;padding:12px}.kpi-value{font-size:24px;font-weight:700}'
        '.kpi-label{font-size:12px;color:#607080} .chart{margin-top:6px}</style></head><body>'
        '<div class="kpis">' + tiles + '</div><div class="chart">' + plot1 + '</div>'
        + '<div class="chart">' + plot2 + '</div>'
        + '<small>Fictional employees. Data period: ' + escape(stat["data_period"])
        + '. No causal inference.</small></body></html>'
    )
