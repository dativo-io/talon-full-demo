"""Operator presenter UI contract: whitelist, parity with shell, authentication.

Runs without Docker, Talon or a real HTTP service network.
"""
import importlib.util
import json
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "people_analytics_presenter.py"
spec = importlib.util.spec_from_file_location("people_analytics_presenter", SCRIPT)
presenter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(presenter)


class PresenterMappingTests(unittest.TestCase):
    def test_all_ui_actions_have_explicit_real_commands(self):
        expected = {"services", "before", "counters", "reset", "ui_networks",
                    "talon_networks", "hr_networks", "ui_mounts", "boundary",
                    "agent_policy", "proxy_policy", "discover", "allow", "deny",
                    "backend_counts", "evidence_export", "evidence_verify"}
        self.assertEqual(set(presenter.CATALOG), expected)
        for name, phase, title, shell in presenter.ACTIONS:
            self.assertTrue(phase and title and shell)
            self.assertNotIn("; rm ", shell)
            args = presenter.build_command(name, runner=lambda _: "synthetic-container-id\n")
            self.assertTrue(args)
            self.assertEqual(args[0], "docker")
            self.assertFalse(any("sh -c" in x for x in args))
            if name in ("before", "reset"):
                self.assertIn("hr-server", args)
            if name in ("deny", "allow", "discover"):
                self.assertIn("ui", args)
                self.assertEqual(args[-1], name)

    def test_rejects_arbitrary_container_execution(self):
        with self.assertRaises(ValueError):
            presenter.build_command("exec -T hr-server cat /data/hr.duckdb")
        self.assertNotIn("full_sql", presenter.CATALOG)
        self.assertNotIn("delete", presenter.CATALOG)

    def test_presenter_result_is_real_process_output(self):
        class Process:
            returncode = 7
            stdout = "actual stdout"
            stderr = "actual stderr"
        with patch.object(presenter, "_environment", return_value={}), \
             patch.object(presenter.subprocess, "run", return_value=Process()) as run:
            result = presenter.perform("deny")
        self.assertFalse(result["ok"])
        self.assertEqual(result["exit_code"], 7)
        self.assertEqual(result["stdout"], "actual stdout")
        self.assertEqual(result["stderr"], "actual stderr")
        self.assertEqual(run.call_args.args[0][-3:], ["python3", "verify_isolation.py", "deny"])


class PresenterHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0),
                                         presenter.handler_factory("test-operator-secret"))
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()

    def request(self, endpoint, method="GET", token=None, origin=None, data=None):
        headers = {}
        if token is not None:
            headers["X-Presenter-Token"] = token
        if origin is not None:
            headers["Origin"] = origin
        if data is not None:
            headers["Content-Type"] = "application/json"
        return urlopen(Request(self.base + endpoint, method=method, headers=headers,
                               data=json.dumps(data).encode() if data is not None else None),
                       timeout=5)

    def test_public_page_contains_description_but_no_secret(self):
        with self.request("/") as response:
            html = response.read().decode()
        self.assertIn("Operator authentication", html)
        self.assertIn("same", html.lower())
        self.assertNotIn("test-operator-secret", html)

    def test_catalog_requires_token_and_includes_exact_shell_text(self):
        with self.assertRaises(HTTPError) as exc:
            self.request("/api/actions")
        self.assertEqual(exc.exception.code, 401)
        with self.request("/api/actions", token="test-operator-secret") as response:
            catalog = json.load(response)
        self.assertEqual({item["id"] for item in catalog}, set(presenter.CATALOG))
        self.assertEqual(catalog[0]["command"], presenter.CATALOG["services"][3])

    def test_execution_rejects_missing_token_and_cross_origin(self):
        with patch.object(presenter, "perform") as action:
            for token, origin in [(None, "http://127.0.0.1:8502"),
                                  ("wrong", "http://127.0.0.1:8502"),
                                  ("test-operator-secret", "https://evil.example")]:
                with self.assertRaises(HTTPError) as exc:
                    self.request("/api/run", "POST", token, origin, {"action": "before"})
                self.assertEqual(exc.exception.code, 403)
            action.assert_not_called()

    def test_authenticated_execution_returns_unmodified_process_result(self):
        expected = {"action": "deny", "ok": True, "exit_code": 0,
                    "stdout": "Signed Talon denial", "stderr": "",
                    "command": presenter.CATALOG["deny"][3]}
        with patch.object(presenter, "perform", return_value=expected) as action:
            with self.request("/api/run", "POST", "test-operator-secret",
                              "http://127.0.0.1:8502", {"action": "deny"}) as response:
                self.assertEqual(json.load(response), expected)
        action.assert_called_once_with("deny")

    def test_unknown_action_not_dispatched(self):
        with patch.object(presenter, "perform") as action:
            with self.assertRaises(HTTPError) as exc:
                self.request("/api/run", "POST", "test-operator-secret",
                             "http://127.0.0.1:8502", {"action": "../etc/passwd"})
            self.assertEqual(exc.exception.code, 400)
            action.assert_not_called()


if __name__ == "__main__":
    unittest.main()
