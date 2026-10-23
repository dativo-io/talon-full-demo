"""Evidence-backed verdict for the TokenEconomizer Claude Code pilot.

A DEMONSTRATED result means observed lower *Talon-estimated* measured spend
on identical synthetic tasks, preserved sealed-grader correctness and real
plugin intervention. It does not establish causal attribution or general ROI.
"""
import html

ARM_NAMES = ("baseline", "after")
MEASURED = tuple(range(6, 11))


def assess(report):
    arms = report.get("tasks") or {}
    before, after = (arms.get(name) or [] for name in ARM_NAMES)
    measured = (report.get("baseline") or {}, report.get("with_tokeneconomizer") or {})
    spent = report.get("arm_total_including_warmups") or {}
    statuses = report.get("arm_status") or {}
    interventions = report.get("plugin_mechanisms_observed") or {}
    signals = {k: int(interventions.get(k) or 0) for k in
               ("learned_facts", "session_injections", "proposed_tools", "pruned_tools", "nudges")}
    pairs = []
    for index in MEASURED:
        a = next((r for r in before if r.get("task") == index), None)
        b = next((r for r in after if r.get("task") == index), None)
        pairs.append({
            "task": index, "baseline_usd": round(a["cost"], 7) if a else None,
            "after_usd": round(b["cost"], 7) if b else None,
            "baseline_passed": bool(a and a.get("passed")),
            "after_passed": bool(b and b.get("passed")),
            "baseline_receipt": a.get("receipt") if a else None,
            "after_receipt": b.get("receipt") if b else None,
        })
    all_tasks = before + after
    complete = (report.get("task_limit") == 10
                and len(before) == len(after) == 10
                and all(statuses.get(a) == "completed" for a in ARM_NAMES)
                and not report.get("run_error"))
    signed = (bool(all_tasks) and
              all(r.get("signed_evidence_verified") is True and
                  r.get("receipt", "").endswith("/signed.json") and
                  r.get("receipt_sha256") and r.get("calls", 0) >= 1 and
                  r.get("records", 0) >= r.get("calls", 0)
                  for r in all_tasks))
    passing = (bool(all_tasks) and all(
        r.get("passed") and r.get("cli_success") and
        r.get("provider_errors", 1) == 0 and not r.get("budget_denied") and
        r.get("denials", 1) == 0 for r in all_tasks))
    paired = all(p["baseline_usd"] is not None and
                 p["after_usd"] is not None and
                 p["baseline_passed"] and p["after_passed"] for p in pairs)
    # Published totals must reconcile to the *same per-task signed receipts*.
    # Never trust a prettier aggregation that silently omits expensive work.
    calculated_measured = (
        sum(float(r.get("cost") or 0) for r in before if r.get("task") in MEASURED),
        sum(float(r.get("cost") or 0) for r in after if r.get("task") in MEASURED))
    reported_measured = (
        float((report.get("baseline") or {}).get("cost") or 0),
        float((report.get("with_tokeneconomizer") or {}).get("cost") or 0))
    full_actual = (
        sum(float(r.get("cost") or 0) for r in before),
        sum(float(r.get("cost") or 0) for r in after))
    full_reported = (
        float((spent.get("baseline") or {}).get("cost") or 0),
        float((spent.get("after") or {}).get("cost") or 0))
    reconciliation = (
        all(abs(a - b) < 1e-6 for a, b in zip(calculated_measured, reported_measured))
        and all(abs(a - b) < 1e-6 for a, b in zip(full_actual, full_reported)))
    comparable = complete and signed and passing and paired and reconciliation
    model = report.get("model") or ""
    release = (report.get("tool_versions") or {}).get("talon_cli") or ""
    release_expected = report.get("talon_release") or ""
    release_ok = bool(release_expected and
                      release.splitlines()[0].strip() == "Talon " + release_expected)
    version = (report.get("tool_versions") or {}).get("claude_cli") or ""
    plugin_version = report.get("tokeneconomizer_sha") or ""
    fingerprints = report.get("workload_sha256") or {}
    same_input = (len(fingerprints.get("baseline", "")) == 64 and
                  fingerprints.get("baseline") == fingerprints.get("after"))
    controls = bool(model and version and len(plugin_version) == 40 and same_input and
                    report.get("comparison_policy") == "separate $7.50 Talon agents")
    # A proposed deny list has NO runtime effect; an injection prepared for
    # a future session does not prove anything reached a measured request.
    # Only signals attributed to an ACTUAL measured Claude session count.
    measured_interventions = [
        {"task": r.get("task"),
         "injected_facts": int(r.get("plugin_injected_facts") or 0),
         "pruned_tools": list(r.get("plugin_pruned_tools") or []),
         "nudges": int(r.get("plugin_nudges") or 0)}
        for r in after if r.get("task") in MEASURED
    ]
    intervention = any(x["injected_facts"] > 0 or x["pruned_tools"] or
                       x["nudges"] > 0 for x in measured_interventions)
    # A hook session record is evidence of loading, NOT of useful optimization.
    hooks = int(report.get("token_economizer_hook_sessions") or 0)
    activation = hooks >= 5 and intervention
    x, y = calculated_measured
    savings = x - y
    lower = x > 0 and y < x
    checks = [
        {"id": "released_talon", "pass": release_ok,
         "detail": f"Recorded {release.splitlines()[0] if release else 'unknown'}; expected {release_expected or 'unknown'}"},
        {"id": "same_workload_and_model", "pass": controls and paired,
         "detail": f"Model {model}; 5 paired measured tasks (IDs 6–10), equal starting-workspace SHA-256, one CLI version and pinned plugin"},
        {"id": "complete_two_arms", "pass": complete,
         "detail": f"Baseline {len(before)}/10, plugin {len(after)}/10; statuses {statuses}"},
        {"id": "signed_talon_receipts", "pass": signed,
         "detail": f"{sum(bool(r.get('signed_evidence_verified')) for r in all_tasks)}/{len(all_tasks)} tasks with independently verified signed receipts"},
        {"id": "cost_reconciles_to_receipts", "pass": reconciliation,
         "detail": "Measured AND full-arm cost totals equal sums of the same task receipts"},
        {"id": "quality_and_execution", "pass": passing and complete,
         "detail": f"Sealed grading, CLI success, zero provider errors/denials for all {len(all_tasks)} tasks"},
        {"id": "actual_plugin_intervention", "pass": activation,
         "detail": f"{hooks} hook sessions; measured-session effects {measured_interventions}; total history {signals}"},
        {"id": "measured_cost_lower", "pass": lower and comparable,
         "detail": f"Baseline USD {x:.4f}; plugin USD {y:.4f}; difference USD {savings:.4f}"},
    ]
    if not comparable or not release_ok or not controls:
        verdict = "INCONCLUSIVE"
        headline = ("Not a complete, independently verified comparable run. "
                    "Do not claim TokenEconomizer savings.")
    elif not activation:
        verdict = "NOT_DEMONSTRATED"
        headline = ("Both arms are comparable, but no concrete TokenEconomizer "
                    "intervention was evidenced. Any cost difference cannot "
                    "be attributed to the plugin.")
    elif not lower:
        verdict = "NOT_DEMONSTRATED"
        headline = "Intervention observed, but no lower measured cost with preserved quality."
    else:
        verdict = "DEMONSTRATED"
        headline = ("In this small paired synthetic run, the plugin arm used "
                    "less Talon-estimated provider spend, both arms passed "
                    "sealed grading, and plugin intervention was observed.")
    return {
        "verdict": verdict, "headline": headline, "checks": checks,
        "paired_measured_tasks": pairs,
        "comparison_valid": comparable and release_ok and controls,
        "plugin_activation_observed": activation,
        "measured_interventions": measured_interventions,
        "cost": {
            "measured_baseline_usd": round(x, 7),
            "measured_plugin_usd": round(y, 7),
            "measured_difference_usd": round(savings, 7),
            "measured_reduction_pct": round(100 * savings / x, 2) if x > 0 else None,
            "baseline_all_tasks_usd": (spent.get("baseline") or {}).get("cost"),
            "plugin_all_tasks_usd": (spent.get("after") or {}).get("cost"),
        },
        "limits": [
            "Observed savings are paired observations, not a controlled causal estimate.",
            "Small sequential synthetic workload; no statistical significance, external validity or guaranteed repeatability.",
            "TokenEconomizer mechanism observations do not prove that they caused cost differences.",
            "Talon-estimated provider pricing is not the Anthropic invoice; $7.50/arm is an admission cap, not a hard billing ceiling.",
            "Talon only governs routed model calls; local file operations and commands are outside the perimeter.",
            "Signed receipts were verified with the local Talon signing key; exported hashes allow integrity tracking, not third-party verification without the key.",
        ],
    }


def markdown(proof, report):
    lines = [
        "# TokenEconomizer × Talon — Evidence-backed proof report",
        "",
        f"**Verdict: {proof['verdict']}**",
        "",
        proof["headline"], "",
        f"Run: `{report.get('run_id', '?')}` · Talon: `{report.get('talon_release', '?')}` "
        f"· Model: `{report.get('model', '?')}` · TokenEconomizer: "
        f"`{report.get('tokeneconomizer_sha', '?')[:12]}`", "",
        "## Evidence gates", "",
        "| Gate | Result | What the record establishes |",
        "|---|---|---|",
    ]
    for check in proof["checks"]:
        lines.append(f"| {check['id']} | {'PASS' if check['pass'] else 'NOT MET'} | "
                     + check["detail"].replace("|", "/") + " |")
    cost = proof["cost"]
    lines.extend([
        "", "## Quantified paired observation", "",
        f"- Measured repairs (5 each): baseline **USD {cost['measured_baseline_usd']:.4f}**, "
        f"plugin **USD {cost['measured_plugin_usd']:.4f}**.",
        f"- Difference: **USD {cost['measured_difference_usd']:+.4f}**; "
        f"reduction: **{cost['measured_reduction_pct']:+.2f}%** "
        if cost["measured_reduction_pct"] is not None
        else "- No measured baseline spend; percentage unavailable.",
        f"- Full-arm spend including warmups: baseline **USD {float(cost['baseline_all_tasks_usd'] or 0):.4f}**, "
        f"plugin **USD {float(cost['plugin_all_tasks_usd'] or 0):.4f}**.",
        "- **A positive cost difference is not proof of causal benefit**. "
        "Only DEMONSTRATED runs satisfy all comparative evidence gates.", "",
        "## Measured task-by-task evidence", "",
        "| Task | Baseline USD | Plugin USD | Both sealed tests pass | Verified signed receipts |",
        "|---|---:|---:|---|---|",
    ])
    for p in proof["paired_measured_tasks"]:
        a = f"{p['baseline_usd']:.4f}" if p["baseline_usd"] is not None else "—"
        b = f"{p['after_usd']:.4f}" if p["after_usd"] is not None else "—"
        rec = " / ".join(f"[{arm}]({p[key]})" if p.get(key) else "missing"
                         for arm, key in (("baseline", "baseline_receipt"),
                                          ("plugin", "after_receipt")))
        lines.append(f"| {p['task']} | {a} | {b} | "
                     f"{'yes' if p['baseline_passed'] and p['after_passed'] else 'no'} | {rec} |")
    lines.extend(["", "## Reproduction and verification", "",
                  "Receipts are stored at relative paths above; each task has `metrics.json` "
                  "including `receipt_sha256`. Talon has already run "
                  "`audit verify --file signed.json` for each recorded task.",
                  "Re-run `make present-tokeneconomizer` in the same private run directory "
                  "for the stored report. Re-run `make demo-tokeneconomizer` "
                  "for another experiment (real paid provider calls).",
                  "", "## Limits on the claim", ""])
    lines.extend(f"- {line}" for line in proof["limits"])
    return "\n".join(lines) + "\n"


def html_section(proof):
    mark = "PASS" if proof["verdict"] == "DEMONSTRATED" else proof["verdict"]
    rows = "".join("<tr><td>" + html.escape(c["id"]) + "</td><td>" +
                   ("PASS" if c["pass"] else "NOT MET") + "</td><td>" +
                   html.escape(c["detail"]) + "</td></tr>" for c in proof["checks"])
    return ('<div class="card"><h2>What this experiment actually proves</h2>'
            f'<p><strong>Verdict: {html.escape(mark)}</strong></p>'
            f'<p>{html.escape(proof["headline"])}</p>'
            '<table><thead><tr><th>Claim gate</th><th>Status</th>'
            '<th>Verification</th></tr></thead><tbody>' + rows + '</tbody></table>'
            '<p>Full receipt links, per-task evidence and limitations: '
            '<a href="proof.md">proof.md</a> · '
            '<a href="proof.json">proof.json</a>.</p></div>')
