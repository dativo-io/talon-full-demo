"""Conservative evaluation of a multi-ticket repository stream.

Do not conflate one-seed directional observation with the paper's multi-seed
experiment. Full-stream cache-aware USD and external task correctness lead.
"""
import html

def _total(rows, key):
    return sum(float(r.get(key) or 0) for r in rows)

def assess(report):
    a = (report.get("tasks") or {}).get("baseline") or []
    b = (report.get("tasks") or {}).get("after") or []
    n = int(report.get("task_limit") or 0)
    warmup = int(report.get("warmup_count") or 0)
    full = report.get("arm_total_including_warmups") or {}
    measured = (report.get("baseline") or {}, report.get("with_tokeneconomizer") or {})
    expected = (report.get("talon_release") or "")
    version = (report.get("tool_versions") or {}).get("talon_cli") or ""
    version_ok = bool(expected and version.splitlines()[0] == "Talon " + expected)
    digests = report.get("workload_sha256") or {}
    same = bool(len(digests.get("baseline") or "") == 64 and
                digests.get("baseline") == digests.get("after"))
    ordered = report.get("task_order") or []
    paired = (n == 24 and warmup == 8 and len(ordered) == n and
              len(set(ordered)) == n and
              [row.get("issue_id") for row in a] == ordered and
              [row.get("issue_id") for row in b] == ordered and
              [row.get("task") for row in a] == list(range(1,n+1)) and
              [row.get("task") for row in b] == list(range(1,n+1)))
    signed = bool(a and b and all(
        r.get("signed_evidence_verified") is True and
        r.get("receipt_sha256") and
        r.get("receipt", "").endswith("/signed.json") and
        r.get("calls",0) > 0 and r.get("records",0) >= r.get("calls",0) and
        r.get("provider_errors",0) == 0 and
        r.get("denials",0) == 0 and not r.get("budget_denied")
        for r in a+b))
    # Signed task cost must reconcile to both the separately shown measurement
    # window and whole-stream cost. No missing expensive "warmup" calls.
    costs_reconciled = (bool(a and b) and
        abs(_total(a,"cost") - float((full.get("baseline") or {}).get("cost") or 0)) < 1e-6 and
        abs(_total(b,"cost") - float((full.get("after") or {}).get("cost") or 0)) < 1e-6 and
        abs(_total(a[warmup:],"cost") - float(measured[0].get("cost") or 0)) < 1e-6 and
        abs(_total(b[warmup:],"cost") - float(measured[1].get("cost") or 0)) < 1e-6)
    study = report.get("profile") == "study" and report.get("workload_design") == "repository-stream-v1"
    versions = report.get("tool_versions") or {}
    controlled = bool(study and version_ok and same and paired and
                      versions.get("claude_cli") and report.get("model") and
                      len(report.get("tokeneconomizer_sha") or "") == 40 and
                      report.get("reasoning_effort") == "high" and
                      report.get("token_economizer_config") == "defaults-no-paid-helpers")
    completed = len(a) == len(b) == n and not report.get("run_error") and all(
        r.get("cli_success") for r in a+b)
    # Compare pass rates without expecting all real coding issues to be solved.
    passed_a = sum(bool(r.get("passed")) for r in a)
    passed_b = sum(bool(r.get("passed")) for r in b)
    regression_failures = sum(r.get("regression_free") is not True for r in a+b)
    quality = passed_a >= 12 and passed_b >= passed_a and regression_failures == 0
    full_a, full_b = _total(a,"cost"), _total(b,"cost")
    cheaper = full_a > 0 and full_b < full_a
    interventions = [
        {"task":r.get("task"), "issue_id":r.get("issue_id"),
         "injected_facts":int(r.get("plugin_injected_facts") or 0),
         "pruned_tools":list(r.get("plugin_pruned_tools") or []),
         "nudges":int(r.get("plugin_nudges") or 0)}
        for r in b if r.get("task",0)>warmup
    ]
    activated = any(x["injected_facts"] or x["pruned_tools"] or x["nudges"] for x in interventions)
    catalog = (report.get("tokeneconomizer_catalog") or {}).get("status") == "recorded"
    defaults = report.get("pruning_mode") == "default"
    compatible = controlled and completed and signed and costs_reconciled and catalog
    checks = [
        {"id":"published_talon_version","pass":version_ok,"detail":version.splitlines()[0] if version else "missing"},
        {"id":"paired_seed_and_starting_repository","pass":paired and same,"detail":"24 paired tasks; identical initial source SHA-256; seeded order"},
        {"id":"explicit_execution_controls","pass":controlled,"detail":"Pinned provider/model/CLI, high effort, published plugin SHA and default no-paid-helpers configuration"},
        {"id":"completed_without_policy_failures","pass":completed and signed,"detail":f"{len(a)}/24 baseline and {len(b)}/24 plugin; attributable, verified signed sessions"},
        {"id":"full_and_measured_cost_reconciles","pass":costs_reconciled,"detail":"Every displayed USD total matches real signed task receipts"},
        {"id":"independent_grader","pass":quality,"detail":f"Baseline {passed_a}/24 passed, plugin {passed_b}/24; cumulative hidden regressions {regression_failures}; require >=12 baseline successes and no regression"},
        {"id":"plugin_setup","pass":catalog,"detail":"Upstream-recommended Claude tool catalog captured"},
        {"id":"plugin_mechanism_applied","pass":activated,"detail":f"{sum(bool(x['injected_facts'] or x['pruned_tools'] or x['nudges']) for x in interventions)} measured tasks received a recorded intervention"},
        {"id":"full_stream_cost_lower","pass":cheaper and compatible,"detail":f"Baseline USD {full_a:.4f}; plugin USD {full_b:.4f}"},
        {"id":"production_default_pruning","pass":defaults,"detail":"No artificial tool-pruning quiet-time override"}
    ]
    if not compatible:
        verdict = "INCONCLUSIVE"
        title = "Stream was not fully comparable or auditable; no cost claim is supported."
    elif passed_a < 12:
        verdict = "INCONCLUSIVE"
        title = "Too few baseline issues passed to assess cost per meaningful successful work."
    elif not quality:
        verdict = "QUALITY_REGRESSION"
        title = "Previously working tickets regressed or the plugin resolved fewer tickets; cost savings are not sufficient."
    elif not cheaper:
        verdict = "NOT_DEMONSTRATED"
        title = "No net cost improvement across the entire repository stream."
    elif not activated:
        verdict = "LOWER_COST_UNATTRIBUTED"
        title = ("Plugin arm happened to cost less across this stream, but no "
                 "optimization action was observed in the measured sessions; "
                 "no benefit can be attributed to TokenEconomizer.")
    else:
        verdict = "PRELIMINARY_SAVINGS"
        title = ("Lower whole-stream Talon-estimated spend with no observed decline in "
                 "graded task successes. This single-seed result is not a causal "
                 "claim or replication of the paper.")
    pairs = []
    net = 0.0
    for pos in range(min(len(a),len(b))):
        cost_a, cost_b = float(a[pos].get("cost") or 0), float(b[pos].get("cost") or 0)
        net += cost_a - cost_b
        pairs.append({"position":pos+1, "issue":a[pos].get("issue_id"),
                      "phase":"learn" if pos<warmup else "measured",
                      "baseline_usd":round(cost_a,7), "plugin_usd":round(cost_b,7),
                      "baseline_passed":bool(a[pos].get("passed")),
                      "plugin_passed":bool(b[pos].get("passed")),
                      "cumulative_savings_usd":round(net,7),
                      "baseline_receipt":a[pos].get("receipt"),
                      "plugin_receipt":b[pos].get("receipt")})
    return {
        "verdict":verdict,"headline":title,"checks":checks,
        "comparison_valid":compatible,"plugin_activation_observed":activated,
        "paired_tasks":pairs,"measured_interventions":interventions,
        "pilot":True,"seed":report.get("seed"), "pruning_mode":report.get("pruning_mode"),
        "correctness":{"baseline_passed":passed_a,"plugin_passed":passed_b,
                       "baseline_total":len(a),"plugin_total":len(b)},
        "cost":{"whole_stream_baseline_usd":round(full_a,7),
                "whole_stream_plugin_usd":round(full_b,7),
                "whole_stream_delta_usd":round(full_a-full_b,7),
                "whole_stream_reduction_pct":round(100*(full_a-full_b)/full_a,2) if full_a else None,
                "measured_baseline_usd":round(_total(a[warmup:],"cost"),7),
                "measured_plugin_usd":round(_total(b[warmup:],"cost"),7),
                "baseline_usd_per_pass":round(full_a/passed_a,6) if passed_a else None,
                "plugin_usd_per_pass":round(full_b/passed_b,6) if passed_b else None},
        "limits":["This is NOT the 277-task SWE-Bench paper replication.",
                  "24 internally authored service tickets are narrower than real engineering issues.",
                  "One seed is exploratory; collect three independently initialized seeded runs.",
                  "Arms run sequentially; cache behavior and sampling variability can affect cost.",
                  "Original paper uses an experimental controller, not this production plugin.",
                  "Plugin runs with default free helpers; paid LLM helpers disabled.",
                  "Costs are signed Talon provider-pricing estimates, not Anthropic invoices.",
                  "A lower measured cost does not prove TokenEconomizer caused it."]
    }


def markdown(proof, report):
    lines=["# TokenEconomizer × Talon — repository-stream evidence",
           "",f"**{proof['verdict']}** — {proof['headline']}","",
           f"Run `{report.get('run_id')}` · seed {proof['seed']} · "
           f"model `{report.get('model')}` · effort high · pruning `{proof['pruning_mode']}`","",
           "## Headline: the entire stream (learning INCLUDED)","",
           "| Metric | Baseline | Plugin |",
           "|---|---:|---:|",
           f"| Successful tickets | {proof['correctness']['baseline_passed']}/24 | {proof['correctness']['plugin_passed']}/24 |",
           f"| Total Talon-estimated USD | ${proof['cost']['whole_stream_baseline_usd']:.4f} | ${proof['cost']['whole_stream_plugin_usd']:.4f} |",
           f"| USD per resolved ticket | {proof['cost']['baseline_usd_per_pass']} | {proof['cost']['plugin_usd_per_pass']} |",
           f"| Late 16 tickets USD (diagnostic only) | ${proof['cost']['measured_baseline_usd']:.4f} | ${proof['cost']['measured_plugin_usd']:.4f} |",
           "", "## Claim gates", "", "| Evidence gate | Result | Basis |", "|---|---|---|"]
    for c in proof["checks"]:
        lines.append(f"| {c['id']} | {'PASS' if c['pass'] else 'NOT MET'} | {c['detail'].replace('|','/')} |")
    lines += ["","## Paired task costs and cumulative break-even","","| # | Ticket | Phase | Baseline USD | Plugin USD | Cumulative saving USD | Pass both | Receipts |",
              "|---|---|---|---:|---:|---:|---|---|"]
    for p in proof["paired_tasks"]:
        rec=(" / ".join(f"[{label}]({p[key]})" if p.get(key) else "missing"
                      for label,key in (("base","baseline_receipt"),("plugin","plugin_receipt"))))
        lines.append(f"| {p['position']} | {p['issue']} | {p['phase']} | "
                     f"{p['baseline_usd']:.4f} | {p['plugin_usd']:.4f} | "
                     f"{p['cumulative_savings_usd']:+.4f} | "
                     f"{'yes' if p['baseline_passed'] and p['plugin_passed'] else 'no'} | {rec} |")
    lines += ["","## Claim boundaries","","An optimizer is not proven to *cause* savings by one paired run. "
              "The cumulative line includes the learning period. The later phase is diagnostic, "
              "never substituted for the complete-stream primary metric.",""]
    lines += ["- "+x for x in proof["limits"]]
    return "\n".join(lines)+"\n"


def html_section(proof):
    rows="".join("<tr><td>"+html.escape(c["id"])+"</td><td>"+
                 ("PASS" if c["pass"] else "NOT MET")+"</td><td>"+
                 html.escape(c["detail"])+"</td></tr>" for c in proof["checks"])
    cost=proof["cost"]; q=proof["correctness"]
    curve = "".join("<tr><td>"+str(p["position"])+"</td><td>"+str(p["issue"])+
                    "</td><td>"+f"${p['cumulative_savings_usd']:+.4f}"+
                    "</td></tr>" for p in proof["paired_tasks"])
    return ('<div class="card"><h2>Evidence verdict: '+
            html.escape(proof["verdict"])+
            '</h2><p>'+html.escape(proof["headline"])+
            '</p><p><b>Whole-stream cost:</b> baseline USD '+
            f"{cost['whole_stream_baseline_usd']:.4f}"+' vs plugin USD '+
            f"{cost['whole_stream_plugin_usd']:.4f}"+'; sealed tasks solved '+
            str(q["baseline_passed"])+"/24 vs "+str(q["plugin_passed"])+
            '/24. The first eight tickets are INCLUDED in this headline.</p>'+
            '<table><thead><tr><th>Gate</th><th>Result</th><th>Basis</th>'+
            '</tr></thead><tbody>'+rows+'</tbody></table>'+
            '<p><a href="proof.md">Per-task signed receipts and limitations</a> · '+
            '<a href="proof.json">proof.json</a></p></div>'+
            '<div class="card"><h2>Cumulative savings by ticket (USD)</h2>'+
            '<p>A negative number means the plugin arm has cost more so far; '
            'this includes the learning phase.</p><table><thead><tr>'+
            '<th>Position</th><th>Ticket</th><th>Cumulative USD saving</th>'+
            '</tr></thead><tbody>'+curve+'</tbody></table></div>')
