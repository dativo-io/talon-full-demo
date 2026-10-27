"""People Analytics documentation contract.

Keeps quickstart, UI/CLI playbooks, customer narrative and CI matrix linked,
executable and honest about simulated data versus real Talon.
"""
from pathlib import Path
import re
import unittest

CASE = Path(__file__).resolve().parent
ROOT = CASE.parents[1]

DOCS = [
    CASE / "README.md",
    CASE / "UI_PLAYBOOK.md",
    CASE / "PRESENTER_COMMANDS.md",
    CASE / "PEOPLE_ANALYTICS_DEMO_PLAN.md",
    CASE / "ADVANCED_SETUP.md",
    CASE / "CI_COVERAGE.md",
    ROOT / "README.md",
    ROOT / "docs" / "AUDIENCE_DEMOS.md",
]


class DocumentationContract(unittest.TestCase):
    def test_all_local_markdown_links_exist(self):
        for doc in DOCS:
            body = doc.read_text(encoding="utf-8")
            with self.subTest(doc=doc.name):
                for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", body):
                    clean = target.split("#", 1)[0].split("?", 1)[0].strip()
                    if not clean or "://" in clean or clean.startswith(("mailto:", "#")):
                        continue
                    self.assertTrue((doc.parent / clean).exists(),
                                    f"{doc}: broken relative link {target}")

    def test_markdown_code_fences_are_balanced(self):
        for doc in DOCS:
            lines = doc.read_text(encoding="utf-8").splitlines()
            for marker in ("~~~", "```"):
                fences = [line for line in lines if line.lstrip().startswith(marker)]
                self.assertEqual(len(fences) % 2, 0, f"{doc}: unbalanced {marker}")

    def test_docs_have_diagrams_and_current_branch(self):
        readme = (CASE / "README.md").read_text(encoding="utf-8")
        plan = (CASE / "PEOPLE_ANALYTICS_DEMO_PLAN.md").read_text(encoding="utf-8")
        self.assertIn("```mermaid\nflowchart", readme)
        self.assertIn("```mermaid\nflowchart", plan)
        self.assertIn("feat/people-analytics-governed-demo", readme)
        self.assertIn("feat/people-analytics-governed-demo",
                      (CASE / "PRESENTER_COMMANDS.md").read_text(encoding="utf-8"))
        for doc in DOCS:
            self.assertNotIn("feat/people-analytics-copilot-v1",
                             doc.read_text(encoding="utf-8"),
                             f"obsolete PR branch in {doc}")

    def test_both_presenter_paths_use_actual_actions(self):
        cli = (CASE / "PRESENTER_COMMANDS.md").read_text(encoding="utf-8")
        ui = (CASE / "UI_PLAYBOOK.md").read_text(encoding="utf-8")
        runner = (CASE / "verify_isolation.py").read_text(encoding="utf-8")
        for action in ("before", "counters", "reset", "boundary", "discover",
                       "allow", "deny", "backend-counts"):
            with self.subTest(action=action):
                self.assertIn(f"verify_isolation.py {action}", cli)
        for name in ("presenter_before", "presenter_counters", "presenter_reset",
                     "presenter_boundary", "presenter_discover", "presenter_allow",
                     "presenter_deny", "backend_counts"):
            self.assertIn(f"def {name}(", runner)
        for doc in (cli, ui):
            for fragment in ("BEFORE", "RESET", "Talon", "Docker", "since reset"):
                self.assertIn(fragment.lower(), doc.lower())

    def test_technical_inspector_and_live_provider_scope(self):
        readme = (CASE / "README.md").read_text(encoding="utf-8")
        ui = (CASE / "UI_PLAYBOOK.md").read_text(encoding="utf-8")
        advanced = (CASE / "ADVANCED_SETUP.md").read_text(encoding="utf-8")
        for term in ("Talon", "Docker", "HR_AI_TRACE", "LIVE"):
            self.assertIn(term, readme)
        for term in ("DuckDB", "Talon", "mcp.request", "mcp.response",
                     "llm.gateway.request", "llm.gateway.response"):
            self.assertIn(term, ui)
        self.assertIn("HR_DEMO_TRACE_PAYLOADS=1", advanced)
        self.assertIn("not a packet capture", advanced.lower())

    def test_guide_is_truthful_and_easy_to_find(self):
        readme = (CASE / "README.md").read_text(encoding="utf-8")
        plan = (CASE / "PEOPLE_ANALYTICS_DEMO_PLAN.md").read_text(encoding="utf-8")
        for path in ("UI_PLAYBOOK.md", "PRESENTER_COMMANDS.md",
                     "PEOPLE_ANALYTICS_DEMO_PLAN.md", "ADVANCED_SETUP.md",
                     "CI_COVERAGE.md"):
            self.assertIn(path, readme)
        self.assertIn("not a Talon on/off switch", readme)
        self.assertIn("has not been executed", readme)
        self.assertIn("different", plan)
        self.assertIn("GUIDED", readme)
        self.assertIn("fake", (CASE / "CI_COVERAGE.md").read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
