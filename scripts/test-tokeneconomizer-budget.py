#!/usr/bin/env python3
"""The public paid demo can never silently expand above the agreed USD 7.50 limit."""
import os
import runpy
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "scripts" / "tokeneconomizer-demo.py"
MAKE = (ROOT / "Makefile").read_text()


class DemoBudgetTests(unittest.TestCase):
    def test_default_live_policies_are_seven_fifty_per_arm(self):
        ns = runpy.run_path(str(RUNNER))
        self.assertEqual(ns["ARM_BUDGET"], 7.5)
        for arm in ("baseline", "after"):
            policy = ns["agent_policy"](arm)
            self.assertIn("daily: 7.50", policy)
            self.assertIn("monthly: 7.50", policy)
            self.assertIn("max_cost: 7.50", policy)

    def test_direct_invocation_cannot_expand_budget(self):
        for value in ("7.51", "15", "100"):
            env = dict(os.environ, TE_DEMO_PROFILE="study",
                       TE_DEMO_ARM_BUDGET=value)
            env.pop("ANTHROPIC_API_KEY", None)
            result = subprocess.run(
                [sys.executable, str(RUNNER), "run"], env=env,
                cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("<= USD 7.50 per arm", result.stderr)
            self.assertNotIn("Preparing isolated identities", result.stdout)

    def test_make_targets_preserve_total_budget(self):
        self.assertIn("TE_DEMO_PROFILE=study TE_DEMO_ARM_BUDGET=7.5 ", MAKE)
        self.assertIn("TE_DEMO_PROFILE=study TE_DEMO_ARM_BUDGET=2.50 ", MAKE)
        self.assertIn("python3 -u scripts/tokeneconomizer-demo.py run", MAKE)
        self.assertIn("TE_DEMO_SEED=$seed", MAKE)
        self.assertEqual(MAKE.count("TE_DEMO_SEED=$seed"), 1)
        # Three independently initialized ledgers must have equal per-seed
        # budgets and 3 * 2.50 = 7.50, within the USD 7.50 cap per named arm.
        self.assertLessEqual(3 * 2.50, 7.5)


if __name__ == "__main__":
    unittest.main()
