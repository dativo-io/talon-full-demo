#!/usr/bin/env python3
"""Credential-free checks for the original full-project Web-Bench reference experiment."""
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
    def test_full_stream_only_and_explicit_budget_optin(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(ref.demo.ARM_BUDGET, 5.0)
            self.assertEqual(ref.task_limit(), 20)
            self.assertEqual(ref.reference_budget(), 5.0)
        for value in ("0", "6", "8", "19", "21", "-1"):
            with patch.dict(os.environ, {"TE_REFERENCE_TASK_LIMIT": value}):
                with self.assertRaisesRegex(RuntimeError, "INVALID BENCHMARK"):
                    ref.task_limit()
        with patch.dict(os.environ, {"TE_REFERENCE_TASK_LIMIT": "20"}):
            self.assertEqual(ref.task_limit(), 20)
        with patch.dict(os.environ, {"TE_REFERENCE_ARM_BUDGET_USD": "10.00",
                                     "TE_REFERENCE_HIGHER_BUDGET_CONFIRM": ""},
                        clear=True):
            with self.assertRaisesRegex(RuntimeError, "HIGHER_BUDGET_CONFIRM"):
                ref.reference_budget()
        with patch.dict(os.environ, {"TE_REFERENCE_ARM_BUDGET_USD": "10.00",
                                     "TE_REFERENCE_HIGHER_BUDGET_CONFIRM": "YES"},
                        clear=True):
            self.assertEqual(ref.reference_budget(), 10.0)
        for value in ("0", "-1", "26", "inf", "nan"):
            with patch.dict(os.environ, {"TE_REFERENCE_ARM_BUDGET_USD": value}):
                with self.assertRaises(RuntimeError):
                    ref.reference_budget()

    def test_source_provenance_rejects_finished_gold_instead_of_init(self):
        with tempfile.TemporaryDirectory() as folder:
            projects = Path(folder) / "projects"
            initial = projects / "expressjs" / "src-init"
            completed = projects / "expressjs" / "src"
            settings = Path(folder) / "tools" / "evaluator" / "src" / "settings"
            initial.mkdir(parents=True)
            completed.mkdir(parents=True)
            settings.mkdir(parents=True)
            (initial / "index.js").write_text("initial")
            (completed / "index.js").write_text("reference")
            (settings / "bench.ts").write_text(
                "if (startTask) { outputProjectDir.push(srcDir) } "
                "else { outputProjectDir.push(initDir) }; "
                "fullTasks.length !== tasks.length")
            task_ids = [f"task-{i}" for i in range(1, 21)]
            with contextlib.redirect_stdout(io.StringIO()) as out:
                ref.initial_state_preflight(projects, task_ids)
            self.assertIn("starts from src-init", out.getvalue())
            with self.assertRaisesRegex(RuntimeError, "all 20"):
                ref.initial_state_preflight(projects, task_ids[:6])
            (initial / "routes" / "home").mkdir(parents=True)
            (initial / "routes" / "home" / "api.js").write_text("gold contamination")
            with self.assertRaisesRegex(RuntimeError, "completed home routes"):
                ref.initial_state_preflight(projects, task_ids)

    def test_full_stream_arm_timeout_is_bounded(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(ref.arm_timeout_seconds(), 14400)
        for invalid in ("0", "3599", "14401", "inf", "bad"):
            with patch.dict(os.environ, {"TE_REFERENCE_ARM_TIMEOUT_S": invalid}):
                with self.assertRaises(RuntimeError):
                    ref.arm_timeout_seconds()
        with patch.dict(os.environ, {"TE_REFERENCE_ARM_TIMEOUT_S": "3600"}):
            self.assertEqual(ref.arm_timeout_seconds(), 3600)

    def test_full_stream_live_log_and_group_cleanup_are_local_only(self):
        from subprocess import TimeoutExpired
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live_log = root / "harness.log"
            proc = type("FakeProcess", (), {"pid": 4242,
                                            "wait": lambda self, timeout: 0})()
            with patch.object(ref.subprocess, "Popen", return_value=proc) as start:
                self.assertEqual(ref.execute_official_arm({"PATH": "/usr/bin"}, root,
                                                           live_log), 0)
            self.assertEqual(start.call_args.kwargs["start_new_session"], True)
            self.assertTrue(live_log.exists())
            self.assertEqual(live_log.stat().st_mode & 0o777, 0o600)
            count = []
            def fake_wait(timeout):
                count.append(timeout)
                if len(count) == 1:
                    raise TimeoutExpired("bash", timeout)
                return -15
            proc.wait = fake_wait
            with patch.object(ref.subprocess, "Popen", return_value=proc):
                with patch.object(ref.os, "killpg") as kill:
                    with self.assertRaisesRegex(RuntimeError, "Terminated process group"):
                        ref.execute_official_arm({"PATH": "/usr/bin"}, root,
                                                 live_log)
            kill.assert_called_once_with(4242, ref.signal.SIGTERM)
            self.assertEqual(count[1], 15)

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
                     for i in range(1, 21)]
            taskfile.write_text(json.dumps(tasks))
            with patch.dict(os.environ, {"TE_REFERENCE_PROJECTS": str(projects),
                                         "TE_REFERENCE_TASKS": str(taskfile)}):
                self.assertEqual(ref.inputs()[2], [f"task-{i}" for i in range(1, 21)])
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

    def test_tool_update_without_catalog_and_text_errors_do_not_imply_missing_tools(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            events = [
                {"type": "session.tools_updated", "data": {"model": "claude-sonnet-5"}},
                {"type": "tool.execution_start", "data": {"toolName": "view"}},
                {"type": "tool.execution_complete", "data": {
                    "result": "notes mention permission denied and no such file"}},
                {"type": "assistant.message", "data": {"content": "No edits made"}},
            ]
            trace.write_text("\n".join(json.dumps(e) for e in events) + "\n")
            summary = ref.transcript_activity(trace)
            self.assertEqual(summary["tool_update_fields"], ["model"])
            self.assertFalse(summary["tool_catalog_exposed"])
            self.assertEqual(summary["explicit_tool_failures"], {})
            self.assertEqual(summary["assistant_messages_with_content"], 1)
            self.assertNotIn("permission denied", str(summary))

    def test_tool_explicit_failed_status_is_counted_without_result_text(self):
        with tempfile.TemporaryDirectory() as directory:
            trace = Path(directory) / "trace.jsonl"
            events = [
                {"type": "tool.execution_complete", "data": {
                    "isError": True, "output": "secret"}},
                {"type": "tool.execution_complete", "data": {
                    "exitCode": 127, "output": "secret"}},
            ]
            trace.write_text("\n".join(json.dumps(e) for e in events) + "\n")
            summary = ref.transcript_activity(trace)
            self.assertEqual(summary["explicit_tool_failures"],
                             {"is_error": 1, "exit_code_nonzero": 1})
            self.assertNotIn("secret", str(summary))

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

    def test_analyze_excludes_unreached_and_incomplete_pairs_without_proof(self):
        import csv
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            idx = root / "official-results" / "copilot_webbench_sonnet5" / "index"
            idx.mkdir(parents=True)
            fields = ["arm", "repo", "seed", "instance", "webbench_attempts",
                      "usage_incomplete", "usage_incomplete_reason", "not_graded",
                      "resolved_p1", "resolved_p2", "cost_effective_tokens"]
            with (idx / "all_rows.csv").open("w", newline="") as stream:
                out = csv.DictWriter(stream, fieldnames=fields)
                out.writeheader()
                for arm in ("baseline", "trimech-web"):
                    for n in range(1, 21):
                        # Baseline completed 1..14 and failed 15;
                        # experimental completed 1..9 and failed 10.
                        reached = n <= (15 if arm == "baseline" else 10)
                        incomplete = (n == 15 and arm == "baseline"
                                      or n == 10 and arm == "trimech-web")
                        resolved = reached and not incomplete
                        out.writerow({
                            "arm": arm, "repo": "expressjs", "seed": "0",
                            "instance": f"task-{n}",
                            "webbench_attempts": "2" if reached else "0",
                            "usage_incomplete": str(incomplete),
                            "usage_incomplete_reason": "tokens_source=mixed" if incomplete else "",
                            "not_graded": "False", "resolved_p1": str(resolved),
                            "resolved_p2": str(resolved),
                            # Unrealistically cheap unreached rows MUST be excluded.
                            "cost_effective_tokens":
                                ("100" if arm == "baseline" else "80") if reached else "0",
                        })
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                ref.analyze(str(root))
            txt = output.getvalue()
            self.assertIn("Both arms ATTEMPTED: 10", txt)
            self.assertIn("Both attempted, graded, complete usage: 9", txt)
            self.assertIn("Attempted but excluded from COST comparison: ['task-10']", txt)
            self.assertIn("baseline: 900.0 effective tokens", txt)
            self.assertIn("trimech-web: 720.0 effective tokens", txt)
            self.assertIn("descriptive change: -20.0%", txt)
            self.assertIn("MISSING (wrapper may be unfinished/failed)", txt)
            self.assertIn("No model calls", txt)
            self.assertNotIn("2,000.0 effective tokens", txt)

    def test_model_failure_classifies_errors_without_revealing_secrets(self):
        examples = (
            ({"error": {"message": "429 Too Many Requests sk-ant-test"}}, "rate_limit_429"),
            ({"error": {"message": "overloaded_error status 529"}}, "upstream_overload_5xx"),
            ({"message": "context window exceeded secret"}, "context_length"),
            ({"error": {"message": "ECONNRESET secret"}}, "timeout_or_transport"),
            ({"error": {"message": "unknown secret"}}, "unclassified"),
        )
        for event, expected in examples:
            got = ref.classify_copilot_failure(event)
            self.assertEqual(got, expected)
            self.assertNotIn("secret", got)

    def test_model_failure_diagnosis_is_metadata_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "reference-20261023T203253Z-5e50676f"
            for arm, failed in (("baseline", False), ("trimech-web", True)):
                run = (root / "official-results" / "copilot_webbench_sonnet5"
                       / arm / "expressjs_s0" / "20261023T210000Z")
                run.mkdir(parents=True)
                (run / "row.json").write_text(json.dumps({
                    "instance": "task-10", "resolved": not failed,
                    "webbench_attempts": 2 if failed else 1,
                    "webbench_answered_files": [[], []] if failed else [["a.js"]]}))
                events = [
                    {"type": "model.call_start", "data": {"secret": "HIDE"}},
                    {"type": "tool.execution_start",
                     "data": {"toolName": "view", "arguments": "SECRET"}},
                ]
                if failed:
                    events += [
                        {"type": "model.call_failure",
                         "data": {"error": {"message": "429 Too Many Requests HIDE"}}},
                        {"type": "session.error",
                         "data": {"error": "429 HIDE"}}
                    ]
                (run / "transcript.jsonl").write_text(
                    "\n".join(json.dumps(x) for x in events) + "\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                ref.diagnose_model_failures(str(root))
            summary = out.getvalue()
            self.assertIn("rate_limit_429", summary)
            self.assertIn("model_failures=1", summary)
            self.assertIn("session_errors=1", summary)
            self.assertNotIn("HIDE", summary)
            self.assertNotIn("SECRET", summary)
            self.assertNotIn("a.js", summary)

    def test_recover_saved_signatures_separately_from_original_proof(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "reference-20261023T203253Z-5e50676f"
            store = root / "talon-store"
            store.mkdir(parents=True)
            keys = {
                "vault": "TEST-NOT-PRODUCTION", "signing": "test-s",
                "admin": "test-a", "agent_baseline": "test-b",
                "agent_after": "test-c"}
            (root / "keys.json").write_text(json.dumps(keys))
            with patch.object(ref.shutil, "which", return_value="/usr/bin/talon"):
                def fake_audit(vals, rid, arm, out):
                    self.assertEqual(rid, root.name)
                    self.assertEqual(vals, keys)
                    self.assertEqual(out, root / "recovered-evidence" / arm)
                    return {"signed_records": 9, "provider_calls": 8,
                            "talon_estimated_usd": 0.3, "denials": 1}
                with patch.object(ref, "audit_agent", side_effect=fake_audit) as audit:
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        summary = ref.recover_evidence(str(root))
                    self.assertEqual(audit.call_count, 2)
            self.assertTrue(summary["evidence_complete"])
            self.assertEqual(summary["signed_evidence"]["after"]["denials"], 1)
            self.assertFalse((root / "reference-proof.json").exists())
            path = root / "reference-recovered-evidence.json"
            self.assertTrue(path.exists())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertNotIn("TEST-NOT-PRODUCTION", path.read_text())
            self.assertNotIn("TEST-NOT-PRODUCTION", buffer.getvalue())

    def test_recover_partial_failure_does_not_certify_both_arms(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "reference-20261023T203253Z-5e50676f"
            (root / "talon-store").mkdir(parents=True)
            (root / "keys.json").write_text(json.dumps(
                {k: "secret" for k in ("vault", "signing", "admin",
                                       "agent_baseline", "agent_after")}))
            def one_fails(vals, rid, arm, out):
                if arm == "after":
                    raise RuntimeError("No matching signed records")
                return {"signed_records": 3, "provider_calls": 2,
                        "talon_estimated_usd": 0.2, "denials": 0}
            with patch.object(ref.shutil, "which", return_value="/usr/bin/talon"):
                with patch.object(ref, "audit_agent", side_effect=one_fails):
                    with contextlib.redirect_stdout(io.StringIO()):
                        with self.assertRaisesRegex(RuntimeError, "incomplete"):
                            ref.recover_evidence(str(root))
            result = json.loads((root / "reference-recovered-evidence.json").read_text())
            self.assertFalse(result["evidence_complete"])
            self.assertEqual(len(result["errors"]), 1)
            self.assertFalse((root / "reference-proof.json").exists())

    def test_run_is_opt_in_before_any_dependencies_or_cost(self):
        with patch.dict(os.environ, {"TE_REFERENCE_PAID_CONFIRM": "",
                                     "TE_REFERENCE_FULL_STREAM_CONFIRM": "",
                                     "ANTHROPIC_API_KEY": "not-used"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "TE_REFERENCE_PAID_CONFIRM"):
                ref.run()
        with patch.dict(os.environ, {"TE_REFERENCE_PAID_CONFIRM": "YES",
                                     "TE_REFERENCE_FULL_STREAM_CONFIRM": "",
                                     "ANTHROPIC_API_KEY": "not-used"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "FULL_STREAM_CONFIRM"):
                ref.run()
        with patch.dict(os.environ, {"TE_REFERENCE_PAID_CONFIRM": "YES",
                                     "TE_REFERENCE_FULL_STREAM_CONFIRM": "YES",
                                     "TE_REFERENCE_TASK_LIMIT": "6",
                                     "ANTHROPIC_API_KEY": "not-used"}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "INVALID BENCHMARK"):
                ref.run()


if __name__ == "__main__":
    unittest.main()
