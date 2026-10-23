#!/usr/bin/env python3
"""Offline negative/positive test matrix for evidence-backed proof verdict.

Synthetic fixtures here exercise the *evaluator*, never published as demo
results. Live proof still requires real Talon signatures and Claude calls.
"""
import copy
import unittest
from tokeneconomizer_proof import assess, markdown, html_section


def sample():
    arms = {}
    for arm, unit in (("baseline", 0.025), ("after", 0.020)):
        arms[arm] = [
            {"task": i, "cost": unit, "passed": True, "cli_success": True,
             "provider_errors": 0, "budget_denied": False, "denials": 0,
             "calls": 1, "records": 1, "signed_evidence_verified": True,
             "receipt": f"{arm}/task-{i:02d}/signed.json",
             "receipt_sha256": "f" * 64,
             "plugin_injected_facts": 1 if arm == "after" and i == 6 else 0,
             "plugin_pruned_tools": [], "plugin_nudges": 0}
            for i in range(1, 11)]
    return {
        "run_id": "OFFLINE-UNIT-FIXTURE-NOT-A-LIVE-RUN",
        "talon_release": "v1.15.3",
        "tool_versions": {"talon_cli": "Talon v1.15.3\nGo: go1.26.10",
                          "claude_cli": "2.1.300"},
        "model": "claude-sonnet-5", "tokeneconomizer_sha": "0" * 40,
        "comparison_policy": "separate $5 Talon agents",
        "workload_sha256": {"baseline": "a" * 64, "after": "a" * 64},
        "task_limit": 10, "run_error": "", "tasks": arms,
        "arm_status": {"baseline": "completed", "after": "completed"},
        "token_economizer_hook_sessions": 10,
        "plugin_mechanisms_observed": {
            "session_injections": 1, "learned_facts": 2,
            "proposed_tools": 0, "pruned_tools": 0, "nudges": 0},
        "baseline": {"cost": 0.125},
        "with_tokeneconomizer": {"cost": 0.100},
        "arm_total_including_warmups": {
            "baseline": {"cost": 0.250}, "after": {"cost": 0.200}},
    }


class ProofVerdictTests(unittest.TestCase):
    def test_positive_observation_limited_to_paired_synthetic_run(self):
        report = sample()
        proof = assess(report)
        self.assertEqual(proof["verdict"], "DEMONSTRATED")
        self.assertEqual(len(proof["paired_measured_tasks"]), 5)
        self.assertAlmostEqual(proof["cost"]["measured_reduction_pct"], 20)
        self.assertIn("not a controlled causal estimate", markdown(proof, report))
        self.assertIn("signed.json", markdown(proof, report))
        self.assertIn("What this experiment actually proves", html_section(proof))

    def test_hook_presence_alone_does_not_prove_intervention(self):
        report = sample()
        report["plugin_mechanisms_observed"] = {
            "session_injections": 0, "learned_facts": 1,
            "proposed_tools": 3, "pruned_tools": 0, "nudges": 0}
        # A prepared (but never injected) fact or proposal is not action.
        report["tasks"]["after"][5]["plugin_injected_facts"] = 0
        self.assertEqual(assess(report)["verdict"], "NOT_DEMONSTRATED")

    def test_no_savings_even_with_plugin_intervention(self):
        report = sample()
        for row in report["tasks"]["after"]:
            if row["task"] >= 6:
                row["cost"] = 0.032
        report["with_tokeneconomizer"]["cost"] = 0.160
        report["arm_total_including_warmups"]["after"]["cost"] = 0.260
        self.assertEqual(assess(report)["verdict"], "NOT_DEMONSTRATED")

    def test_totals_must_reconcile_to_signed_receipts(self):
        report = sample()
        report["baseline"]["cost"] = 0.250   # doubled on paper; receipts did not change
        self.assertEqual(assess(report)["verdict"], "INCONCLUSIVE")

    def test_unmatched_workspaces_fail_claim(self):
        report = sample()
        report["workload_sha256"]["after"] = "b" * 64
        self.assertEqual(assess(report)["verdict"], "INCONCLUSIVE")

    def test_unsigned_or_missing_receipts_fail_claim(self):
        for key, val in [("signed_evidence_verified", False),
                         ("receipt_sha256", ""), ("calls", 0)]:
            report = sample()
            report["tasks"]["after"][0][key] = val
            self.assertEqual(assess(report)["verdict"], "INCONCLUSIVE")

    def test_quality_or_cli_failure_fails_claim(self):
        for key, val in [("passed", False), ("cli_success", False),
                         ("provider_errors", 1), ("denials", 1),
                         ("budget_denied", True)]:
            report = sample()
            report["tasks"]["baseline"][8][key] = val
            self.assertEqual(assess(report)["verdict"], "INCONCLUSIVE")

    def test_missing_measured_pair_fails_claim(self):
        report = sample()
        report["tasks"]["after"].pop()
        self.assertEqual(assess(report)["verdict"], "INCONCLUSIVE")

    def test_smoke_has_no_measured_savings_claim(self):
        report = sample()
        report["task_limit"] = 1
        for arm in ("baseline", "after"):
            report["tasks"][arm] = report["tasks"][arm][:1]
            report["arm_status"][arm] = "smoke_only"
        self.assertEqual(assess(report)["verdict"], "INCONCLUSIVE")

    def test_unexpected_binary_release_is_rejected(self):
        report = sample()
        report["tool_versions"]["talon_cli"] = "Talon v1.15.2"
        self.assertEqual(assess(report)["verdict"], "INCONCLUSIVE")

    def test_fatal_run_error_is_not_a_valid_demo(self):
        report = sample()
        report["run_error"] = "after task 8: evidence missing"
        self.assertEqual(assess(report)["verdict"], "INCONCLUSIVE")


if __name__ == "__main__":
    unittest.main()
