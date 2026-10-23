#!/usr/bin/env python3
"""The public paid demo can never silently expand above the agreed budget."""
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
    def test_default_live_policies_are_five_dollars_per_arm(self):
        ns = runpy.run_path(str(RUNNER))
        self.assertEqual(ns["ARM_BUDGET"], 5.0)
        for arm in ("baseline", "after"):
            policy = ns["agent_policy"](arm)
            self.assertIn("daily: 5.00", policy)
            self.assertIn("monthly: 5.00", policy)
            self.assertIn("max_cost: 5.00", policy)

    def test_direct_invocation_cannot_expand_budget(self):
        for value in ("5.01", "15", "100"):
            env = dict(os.environ, TE_DEMO_PROFILE="study",
                       TE_DEMO_ARM_BUDGET=value)
            env.pop("ANTHROPIC_API_KEY", None)
            result = subprocess.run(
                [sys.executable, str(RUNNER), "run"], env=env,
                cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("<= USD 5 per arm", result.stderr)
            self.assertNotIn("Preparing isolated identities", result.stdout)

    def test_make_targets_preserve_total_budget(self):
        self.assertIn("TE_DEMO_PROFILE=study TE_DEMO_ARM_BUDGET=5 ", MAKE)
        self.assertIn("TE_DEMO_PROFILE=study TE_DEMO_ARM_BUDGET=1.66 ", MAKE)
        self.assertIn("python3 -u scripts/tokeneconomizer-demo.py run", MAKE)
        # Three independently initialized ledgers must have equal per-seed
        # budgets and 3 * 1.66 = 4.98 < 5 per named arm.
        self.assertLessEqual(3 * 1.66, 5.0)


if __name__ == "__main__":
    unittest.main()
