#!/usr/bin/env python3
"""Credential-free checks for the *reference* benchmark mini-pilot."""
import importlib.util
import contextlib
import io
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

    def test_one_project_export_preserves_upstream_order_and_text(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            projects = base / "web-bench" / "projects"
            (projects / "expressjs").mkdir(parents=True)
            experiments = base / "upstream" / "experiments"
            (experiments / "workloads").mkdir(parents=True)
            manifest = {"groups": {"expressjs": [f"task-{i}" for i in range(1, 21)]}}
            (experiments / "workloads" / "webbench.json").write_text(json.dumps(manifest))
            task_file = projects / "expressjs" / "tasks.jsonl"
            task_file.write_text("".join(json.dumps({"id": f"task-{i}",
                                                     "description": f"Original task {i}"}) +
                                         "\n" for i in range(1, 21)))
            output = base / "benchmark_tasks.json"
            rows = ref.export_expressjs_tasks(projects, output, experiments)
            self.assertEqual(len(rows), 20)
            self.assertEqual([r["instance_id"] for r in rows],
                             [f"task-{i}" for i in range(1, 21)])
            self.assertEqual(rows[5]["problem_statement"], "Original task 6")
            self.assertEqual(json.loads(output.read_text()), rows)
            task_file.write_text('{"id": "task-1", "description": "missing rest"}\n')
            with self.assertRaisesRegex(RuntimeError, "differs from official"):
                ref.export_expressjs_tasks(projects, output, experiments)

    def test_default_paths_need_no_manual_exports(self):
        with patch.dict(os.environ, {}, clear=True):
            projects, tasks = ref.reference_paths()
            self.assertEqual(projects, ref.DEFAULT_WEBBENCH / "projects")
            self.assertEqual(tasks, ref.DEFAULT_EXPORT)

    def test_prepare_gives_clear_node_prerequisite_before_download(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with patch.object(ref, "reference_paths",
                              return_value=(path / "web-bench" / "projects",
                                            path / "tasks.json")):
                with patch.object(ref.shutil, "which", return_value=None):
                    with self.assertRaisesRegex(RuntimeError, "Node.js 22"):
                        ref.prepare()
                with patch.object(ref.shutil, "which", return_value="/usr/bin/node"):
                    with patch.object(ref.subprocess, "run",
                                      return_value=type("Version", (), {"stdout": "v18.20.1"})()):
                        with self.assertRaisesRegex(RuntimeError, "requires Node.js 22"):
                            ref.prepare()

    def test_copilot_preflight_missing_binary_is_keyless(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(ref.Path, "home", return_value=Path(directory)):
                with patch.object(ref.shutil, "which", return_value=None):
                    with self.assertRaisesRegex(RuntimeError, "1.0.84-7"):
                        ref.copilot_preflight()
            # Only local path lookup happened, never a provider call.

    def test_copilot_preflight_reports_original_version(self):
        mock_version = type("Version", (), {
            "returncode": 0, "stdout": "GitHub Copilot CLI 1.0.84-7\\n",
            "stderr": ""})()
        with patch.object(ref.shutil, "which", return_value="/tmp/copilot"):
            with patch.object(ref.subprocess, "run", return_value=mock_version) as proc:
                result = ref.copilot_preflight()
        self.assertEqual(result["binary"], "/tmp/copilot")
        self.assertIn("1.0.84-7", result["version"])
        self.assertEqual(proc.call_args.kwargs["env"], ref.demo.safe_env())
        self.assertEqual(proc.call_args.args[0], ["/tmp/copilot", "--version"])

    def test_playwright_preflight_rejects_missing_system_libraries_without_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            projects = Path(directory) / "projects"
            (projects / "expressjs").mkdir(parents=True)
            failure = type("Process", (), {
                "returncode": 1, "stdout": "",
                "stderr": "chrome-headless-shell: error while loading shared libraries: "
                          "libatk-1.0.so.0: cannot open shared object file"})()
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "should-never-leak"}):
                with patch.object(ref.demo, "execute", return_value=failure) as call:
                    with self.assertRaisesRegex(RuntimeError, "libatk-1.0.so.0"):
                        ref.playwright_preflight(projects)
            command = call.call_args.args[0]
            self.assertEqual(command[:2], ["node", "-e"])
            self.assertIn("chromium.launch", command[2])
            self.assertNotIn("ANTHROPIC_API_KEY", call.call_args.kwargs["env"])
            self.assertEqual(call.call_args.kwargs["cwd"], projects / "expressjs")

    def test_playwright_preflight_succeeds_with_local_browser_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            projects = Path(directory) / "projects"
            (projects / "expressjs").mkdir(parents=True)
            success = type("Process", (), {
                "returncode": 0, "stdout": "Chromium 143\\n", "stderr": ""})()
            with patch.object(ref.demo, "execute", return_value=success) as call:
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    ref.playwright_preflight(projects)
            self.assertIn("PASS: local Playwright browser launch", output.getvalue())
            self.assertFalse(call.call_args.kwargs["check"])

    def test_transcript_activity_uses_executions_not_streaming_chunks(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "transcript.jsonl"
            events = (
                [{"type": "model.call_start"}] * 2
                + [{"type": "assistant.tool_call_delta",
                    "data": {"toolName": "view", "arguments": "secret"}}] * 200
                + [{"type": "tool.execution_start",
                    "data": {"toolName": "view", "arguments": "do-not-print"}},
                   {"type": "tool.execution_complete", "data": {"output": "secret"}},
                   {"type": "tool.execution_start",
                    "data": {"toolName": "bash", "arguments": "secret"}},
                   {"type": "tool.execution_complete", "data": {"output": "secret"}}])
            trace.write_text("\n".join(json.dumps(x) for x in events) + "\n")
            summary = ref.transcript_activity(trace)
            self.assertEqual(summary["model_calls"], 2)
            self.assertEqual(summary["tool_execution_started"], 2)
            self.assertEqual(summary["tool_execution_completed"], 2)
            self.assertEqual(summary["executed_tools"], {"bash": 1, "view": 1})
            self.assertNotIn("secret", str(summary))
            self.assertIsNone(ref.transcript_activity(Path(directory) / "missing"))

    def test_offline_diagnosis_distinguishes_unreached_from_attempted(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "reference-proof.json").write_text(json.dumps({
                "upstream_sha": ref.demo.TOKENECONOMIZER_COMMIT,
                "task_ids": ["task-1", "task-2"]}))
            for arm in ("baseline", "trimech-web"):
                cell = root / "official-results" / "copilot_webbench_sonnet5" / arm / "expressjs_s0"
                for index, (attempts, unreached) in enumerate(((2, False), (0, True)), 1):
                    run = cell / f"20261023T00000{index}Z"
                    run.mkdir(parents=True)
                    (run / "row.json").write_text(json.dumps({
                        "instance": f"task-{index}", "resolved": False,
                        "webbench_attempts": attempts,
                        "webbench_attempt_results": [False] * attempts,
                        "unreached": unreached, "num_turns": attempts * 5,
                        "run_dir": str(run)}))
            capture = io.StringIO()
            with contextlib.redirect_stdout(capture):
                ref.diagnose(str(root))
            output = capture.getvalue()
            self.assertIn("STREAM CENSORED", output)
            self.assertIn("'attempted': 1", output)
            self.assertIn("'unreached': 1", output)
            self.assertIn("No API calls made", output)

    def test_run_is_opt_in_before_any_dependencies_or_cost(self):
        with patch.dict(os.environ, {"TE_REFERENCE_PAID_CONFIRM": "",
                                     "ANTHROPIC_API_KEY": "not-used"}):
            with self.assertRaisesRegex(RuntimeError, "TE_REFERENCE_PAID_CONFIRM"):
                ref.run()


if __name__ == "__main__":
    unittest.main()
