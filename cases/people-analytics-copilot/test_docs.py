"""Keep the customer-facing People Analytics docs navigable and truthful.

This deliberately tests structure and runnable command names—not prose style.
Executed by make people-analytics-validate and CI.
"""
from pathlib import Path
import re
import unittest

CASE = Path(__file__).resolve().parent
ROOT = CASE.parents[1]

DOCS = [
    CASE / "README.md",
    CASE / "PRESENTER_COMMANDS.md",
    CASE / "UI_PLAYBOOK.md",
    CASE / "PEOPLE_ANALYTICS_DEMO_PLAN.md",
    ROOT / "README.md",
    ROOT / "docs" / "AUDIENCE_DEMOS.md",
]


class DocumentationContract(unittest.TestCase):
    def test_relative_markdown_links_resolve(self):
        for doc in DOCS:
            content = doc.read_text(encoding="utf-8")
            with self.subTest(doc=doc.name):
                # Only filesystem-relative Markdown links; HTTP/anchors are out of scope.
                for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", content):
                    clean = target.split("#", 1)[0].split("?", 1)[0].strip()
                    if not clean or "://" in clean or clean.startswith(("mailto:", "#")):
                        continue
                    self.assertTrue((doc.parent / clean).exists(),
                                    f"{doc}: broken link to {target}")

    def test_code_fences_balanced(self):
        for doc in DOCS:
            lines = doc.read_text(encoding="utf-8").splitlines()
            for marker in ("~~~", "\x60\x60\x60"):
                fences = [line for line in lines if line.lstrip().startswith(marker)]
                self.assertEqual(len(fences) % 2, 0,
                                 f"{doc}: unbalanced Markdown {marker} fences")

    def test_presenter_commands_exist_in_runner(self):
        docs = (CASE / "PRESENTER_COMMANDS.md").read_text(encoding="utf-8")
        script = (CASE / "verify_isolation.py").read_text(encoding="utf-8")
        for action in ("before", "counters", "reset", "boundary", "discover",
                       "allow", "deny", "backend-counts"):
            with self.subTest(action=action):
                self.assertIn(f"verify_isolation.py {action}", docs)
        for action in ("presenter_before", "presenter_counters", "presenter_reset",
                       "presenter_boundary", "presenter_discover", "presenter_allow",
                       "presenter_deny", "backend_counts"):
            self.assertIn(f"def {action}(", script)

    def test_customer_docs_distinguish_real_from_simulated(self):
        readme = (CASE / "README.md").read_text(encoding="utf-8")
        plan = (CASE / "PEOPLE_ANALYTICS_DEMO_PLAN.md").read_text(encoding="utf-8")
        presenter = (CASE / "PRESENTER_COMMANDS.md").read_text(encoding="utf-8")
        self.assertIn("Talon on/off switch", readme)
        self.assertIn("not a before/after policy flip", presenter)
        self.assertIn("not been executed", readme)
        self.assertIn("not Talon enforcement", plan)
        self.assertIn("since reset", presenter)
        self.assertIn("PRESENTER_COMMANDS.md", readme)
        self.assertIn("PEOPLE_ANALYTICS_DEMO_PLAN.md", readme)
        self.assertIn("UI_PLAYBOOK.md", readme)
        ui = (CASE / "UI_PLAYBOOK.md").read_text(encoding="utf-8")
        for evidence in ("BEFORE", "RESET", "decision=allow", "decision=deny",
                         "signed", "8501", "8502"):
            self.assertIn(evidence, ui)



if __name__ == "__main__":
    unittest.main()
