#!/usr/bin/env python3
"""Study evaluator and three-seed aggregation tests, all offline."""
import copy
import runpy
import unittest

from tokeneconomizer_workload import TASK_COUNT, WARMUP, DESIGN, order
from tokeneconomizer_study_proof import assess, markdown, html_section

aggregate = runpy.run_path("scripts/tokeneconomizer-study-aggregate.py")["aggregate"]


def fake(seed=0):
    ids=[s["id"] for s in order(seed)]
    tasks={}
    for arm, unit in (("baseline",0.10),("after",0.08)):
        tasks[arm]=[
            {"task":i+1,"issue_id":key,"cost":unit,"passed":True,
             "cli_success":True,"calls":1,"records":1,
             "signed_evidence_verified":True,"receipt_sha256":"f"*64,
             "receipt":f"{arm}/task-{i+1:02d}/signed.json",
             "provider_errors":0,"denials":0,"budget_denied":False,
             "plugin_injected_facts":1 if arm=="after" and i==10 else 0}
            for i,key in enumerate(ids)]
    return {
        "run_id":f"OFFLINE-UNIT-TEST-SEED-{seed}",
        "profile":"study","seed":seed,"task_limit":TASK_COUNT,
        "warmup_count":WARMUP,"workload_design":DESIGN,
        "task_order":ids,"model":"claude-sonnet-5",
        "talon_release":"v1.15.3","tokeneconomizer_sha":"0"*40,
        "workload_sha256":{"baseline":"a"*64,"after":"a"*64},
        "reasoning_effort":"high","pruning_mode":"default",
        "token_economizer_config":"defaults-no-paid-helpers",
        "tokeneconomizer_catalog":{"status":"recorded"},
        "tool_versions":{"talon_cli":"Talon v1.15.3\nGo: go1.26.10",
                         "claude_cli":"2.1.307"},
        "run_error":"","tasks":tasks,
        "baseline":{"cost":1.6},"with_tokeneconomizer":{"cost":1.28},
        "arm_total_including_warmups":{"baseline":{"cost":2.4},"after":{"cost":1.92}}
    }


class StudyProofTests(unittest.TestCase):
    def proof(self,r):
        return assess(r)

    def test_single_seed_is_preliminary_not_replication(self):
        r=fake()
        p=self.proof(r)
        self.assertEqual(p["verdict"],"PRELIMINARY_SAVINGS")
        self.assertEqual(len(p["paired_tasks"]),24)
        self.assertAlmostEqual(p["cost"]["whole_stream_reduction_pct"],20)
        self.assertIn("entire stream",markdown(p,r))
        self.assertIn("Cumulative savings",html_section(p))
        self.assertTrue(p["plugin_activation_observed"])

    def test_sequential_learning_cost_cannot_be_excluded(self):
        r=fake()
        for i in range(WARMUP):
            r["tasks"]["after"][i]["cost"]=0.20
        r["arm_total_including_warmups"]["after"]["cost"]=2.88
        p=self.proof(r)
        self.assertEqual(p["verdict"],"NOT_DEMONSTRATED")
        self.assertGreater(p["cost"]["whole_stream_plugin_usd"],
                           p["cost"]["whole_stream_baseline_usd"])

    def test_bad_controls_fail_closed(self):
        for key,bad in [
            ("workload_sha256",{"baseline":"a"*64,"after":"b"*64}),
            ("reasoning_effort","low"),
            ("tokeneconomizer_catalog",{"status":"failed"}),
            ("task_order",["01"]*24),
            ("token_economizer_config","accelerated-pruning-ablation")
        ]:
            r=fake()
            r[key]=bad
            self.assertEqual(self.proof(r)["verdict"],"INCONCLUSIVE",key)

    def test_failures_and_missing_receipts_fail_closed(self):
        for field,value in [("receipt_sha256",""),("signed_evidence_verified",False),
                            ("provider_errors",1),("cli_success",False),
                            ("denials",1)]:
            r=fake()
            r["tasks"]["after"][5][field]=value
            self.assertEqual(self.proof(r)["verdict"],"INCONCLUSIVE",field)

    def test_cost_aggregation_is_audited(self):
        r=fake()
        r["baseline"]["cost"]=0.01
        self.assertEqual(self.proof(r)["verdict"],"INCONCLUSIVE")

    def test_quality_is_not_required_to_be_perfect_but_cannot_regress(self):
        r=fake()
        for x in r["tasks"]["after"][:2]:
            x["passed"]=False
        self.assertEqual(self.proof(r)["verdict"],"QUALITY_REGRESSION")
        r=fake()
        for x in r["tasks"]["baseline"][:2]:
            x["passed"]=False
        self.assertEqual(self.proof(r)["verdict"],"PRELIMINARY_SAVINGS")

    def test_three_seed_non_cherry_picking(self):
        reports=[fake(seed) for seed in range(3)]
        for r in reports:
            r["proof"]=self.proof(r)
        a=aggregate(reports)
        self.assertEqual(a["status"],"REPEATED_DIRECTIONAL_SAVINGS")
        self.assertEqual(len(a["runs"]),3)
        reports[1]["proof"]["comparison_valid"]=False
        self.assertEqual(aggregate(reports)["status"],"INCONCLUSIVE")
        reports=[fake(seed) for seed in range(3)]
        for r in reports:
            r["proof"]=self.proof(r)
        reports[1]["proof"]["cost"]["whole_stream_plugin_usd"]=3.1
        a=aggregate(reports)
        self.assertEqual(a["status"],"MIXED_DIRECTION")

if __name__=="__main__":
    unittest.main()
