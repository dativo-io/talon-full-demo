#!/usr/bin/env python3
"""Credential-free checks for the *reference* benchmark mini-pilot."""
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("reference", ROOT / "scripts" / "tokeneconomizer-reference.py")
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)


class ReferencePilotTest(unittest.TestCase):
    def test_fixed_budgets_and_sample_cap(self):
        self.assertEqual(ref.demo.ARM_BUDGET, 5.0)
        self.assertEqual(ref.task_limit(), 6)
        with patch.dict(os.environ, {"TE_REFERENCE_TASK_LIMIT": "8"}):
            self.assertEqual(ref.task_limit(), 8)
        for value in ("0", "9", "-1"):
            with patch.dict(os.environ, {"TE_REFERENCE_TASK_LIMIT": value}):
                with self.assertRaises(RuntimeError):
                    ref.task_limit()

    def test_agent_env_never_exposes_provider_key(self):
        values = {"agent_baseline": "talon-test-agent-secret",
                  "agent_after": "second-test-agent-secret"}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "must-not-leak",
                                         "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
                                         "COPILOT_PROVIDER_BASE_URL": "https://api.anthropic.com"}):
                env = ref.provider_env(values, "test", "baseline", path, path / "tasks.json",
                                       path / "results", path / "empty-env")
            self.assertNotIn("ANTHROPIC_API_KEY", env)
            self.assertNotIn("ANTHROPIC_BASE_URL", env)
            self.assertEqual(env["COPILOT_PROVIDER_API_KEY"], values["agent_baseline"])
            self.assertIn("/v1/proxy/anthropic", env["COPILOT_PROVIDER_BASE_URL"])
            self.assertIn("X-Talon-Session-ID:", env["COPILOT_PROVIDER_HEADERS"])
            self.assertEqual(env["ARMS"], "baseline")
            other = ref.provider_env(values, "test", "after", path, path / "tasks.json",
                                     path / "results", path / "empty-env")
            self.assertEqual(other["ARMS"], "trimech-web")
            self.assertNotEqual(other["COPILOT_PROVIDER_API_KEY"], env["COPILOT_PROVIDER_API_KEY"])

    def test_official_workload_order_required(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            projects = base / "projects"
            (projects / "expressjs").mkdir(parents=True)
            evaluator = base / "apps" / "eval" / "dist"
            evaluator.mkdir(parents=True)
            (evaluator / "index.js").write_text("// offline fixture")
            taskfile = base / "webbench_tasks.json"
            tasks = [{"instance_id": f"task-{i}", "repo": "expressjs"}
                     for i in range(1, 9)]
            taskfile.write_text(json.dumps(tasks))
            with patch.dict(os.environ, {"TE_REFERENCE_PROJECTS": str(projects),
                                         "TE_REFERENCE_TASKS": str(taskfile)}):
                self.assertEqual(ref.inputs()[2], [f"task-{i}" for i in range(1, 7)])
                tasks[1]["instance_id"] = "task-77"
                taskfile.write_text(json.dumps(tasks))
                with self.assertRaises(RuntimeError):
                    ref.inputs()

    def test_run_is_opt_in_before_any_dependencies_or_cost(self):
        with patch.dict(os.environ, {"TE_REFERENCE_PAID_CONFIRM": "",
                                     "ANTHROPIC_API_KEY": "not-used"}):
            with self.assertRaisesRegex(RuntimeError, "TE_REFERENCE_PAID_CONFIRM"):
                ref.run()


if __name__ == "__main__":
    unittest.main()
