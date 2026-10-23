#!/usr/bin/env python3
"""Three-seed TokenEconomizer stream aggregation; never cherry-pick runs."""
import json
import os
from pathlib import Path
from tokeneconomizer_study_proof import assess as reassess

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / ".state" / "tokeneconomizer-demo"

def aggregate(reports):
    if len(reports) != 3 or sorted(r.get("seed") for r in reports) != [0,1,2]:
        raise ValueError("exactly one run per seed 0, 1 and 2 required")
    attrs = ("profile", "model", "tokeneconomizer_sha", "talon_release", "demo_revision",
             "workload_design", "pruning_mode", "reasoning_effort")
    controlled = (all(r.get("profile")=="study" and r.get("pruning_mode")=="default"
                      and len(r.get("demo_revision") or "") == 40
                      and (r.get("proof") or {}).get("comparison_valid")
                      and (r.get("proof") or {}) == reassess(r)
                      and (r.get("proof") or {}).get("verdict") in (
                          "PRELIMINARY_SAVINGS", "LOWER_COST_UNATTRIBUTED",
                          "NOT_DEMONSTRATED") for r in reports)
                  and all(len({json.dumps(r.get(k),sort_keys=True) for r in reports})==1
                          for k in attrs)
                  and len({(r.get("tool_versions") or {}).get("claude_cli")
                           for r in reports}) == 1)
    stats=[]
    for r in sorted(reports,key=lambda x:x["seed"]):
        p=r.get("proof") or {}
        costs=p.get("cost") or {}
        qa=p.get("correctness") or {}
        baseline=float(costs.get("whole_stream_baseline_usd") or 0)
        after=float(costs.get("whole_stream_plugin_usd") or 0)
        stats.append({"seed":r["seed"],"run_id":r.get("run_id"),
                      "verdict":p.get("verdict"),"baseline_usd":baseline,
                      "plugin_usd":after,"saved_usd":round(baseline-after,7),
                      "baseline_resolved":qa.get("baseline_passed"),
                      "plugin_resolved":qa.get("plugin_passed"),
                      "valid":bool(p.get("comparison_valid"))})
    good = controlled and all(x["valid"] and x["baseline_resolved"] is not None
                              and x["plugin_resolved"] is not None
                              and x["plugin_resolved"] >= x["baseline_resolved"]
                              for x in stats)
    cost_a=sum(x["baseline_usd"] for x in stats)
    cost_b=sum(x["plugin_usd"] for x in stats)
    all_lower=all(x["plugin_usd"] < x["baseline_usd"] for x in stats)
    mechanisms_all = all((r.get("proof") or {}).get("plugin_activation_observed")
                         for r in reports)
    if not good:
        status="INCONCLUSIVE"
    elif all_lower and cost_b < cost_a:
        status=("REPEATED_DIRECTIONAL_SAVINGS" if mechanisms_all
                else "REPEATED_LOWER_COST_UNATTRIBUTED")
    elif cost_b < cost_a:
        status="MIXED_DIRECTION"
    else:
        status="NO_AGGREGATE_SAVINGS"
    return {"status":status,"runs":stats,
            "three_seeds_valid":good,"three_seeds_lower":all_lower,
            "pooled_baseline_usd":round(cost_a,7),
            "pooled_plugin_usd":round(cost_b,7),
            "pooled_difference_usd":round(cost_a-cost_b,7),
            "reduction_pct":round(100*(cost_a-cost_b)/cost_a,2) if cost_a else None,
            "notes":[
                "This is three paired runs of synthetic tickets, not 277 SWE-Bench tasks.",
                "The mean of three seeded streams is exploratory; it is not proof of causality.",
                "All seeds are included, negative or incomplete; no cherry-picking.",
                "Original TokenEconomizer paper evaluated the experimental trimech controller.",
                "Talon provides signed pricing observations, not final Anthropic invoices."]}


def markdown(agg):
    rows = ["# TokenEconomizer × Talon — three seeded repository streams","",
            f"**Verdict: {agg['status']}**","",
            "| Seed | Run | Baseline USD | Plugin USD | Delta USD | Graded resolved |",
            "|---|---|---:|---:|---:|---|"]
    for r in agg["runs"]:
        rows.append(f"| {r['seed']} | {r['run_id']} | {r['baseline_usd']:.4f} | "
                    f"{r['plugin_usd']:.4f} | {r['saved_usd']:+.4f} | "
                    f"{r['baseline_resolved']}/24 vs {r['plugin_resolved']}/24 |")
    rows += ["",f"All seeds pooled: baseline USD {agg['pooled_baseline_usd']:.4f}, "
             f"plugin USD {agg['pooled_plugin_usd']:.4f}; "
             f"reduction {agg['reduction_pct']}%.", "", "## Interpretation and caveats", ""]
    rows += ["- "+s for s in agg["notes"]]
    rows += ["", "Detailed underlying proof files:", ""]
    rows += [f"- Seed {r['seed']}: [{r['run_id']}/proof.md]({r['run_id']}/proof.md)"
             for r in agg["runs"]]
    return "\n".join(rows)+"\n"


def main():
    found={}
    # Deterministic latest-run-per-seed selection, *even when that run failed*.
    for path in sorted(STATE.glob("*/comparison.json")):
        r=json.loads(path.read_text())
        if r.get("profile")=="study" and r.get("seed") in (0,1,2):
            found[r["seed"]]=r
    if len(found)!=3:
        raise SystemExit("Need three seeded study runs (0,1,2); found: "+
                         repr(sorted(found))+"; use make tokeneconomizer-study-3")
    result=aggregate(list(found.values()))
    (STATE/"study-aggregate.json").write_text(json.dumps(result,indent=2)+"\n")
    (STATE/"study-aggregate.md").write_text(markdown(result))
    print("Three-seed study verdict:",result["status"])
    print("Aggregate report:",STATE/"study-aggregate.md")
    if not result["three_seeds_valid"]:
        raise SystemExit("Aggregate incomplete or quality-regressed; no savings claim")


if __name__=="__main__":
    main()
