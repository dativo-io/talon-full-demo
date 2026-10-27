"""Prevent demo docs from claiming a second UI or unverified provider behavior."""
from pathlib import Path
import re
import unittest

CASE=Path(__file__).resolve().parent
ROOT=CASE.parents[1]
DOCS=[CASE/name for name in ("README.md","UI_PLAYBOOK.md","PRESENTER_COMMANDS.md",
      "PEOPLE_ANALYTICS_DEMO_PLAN.md","ADVANCED_SETUP.md","CI_COVERAGE.md")]
DOCS.extend([ROOT/"README.md",ROOT/"docs"/"AUDIENCE_DEMOS.md"])

class DocumentationContract(unittest.TestCase):
    def test_links_and_fences(self):
        for path in DOCS:
            body=path.read_text()
            for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)",body):
                relative=target.split("#")[0].split("?")[0].strip()
                if relative and "://" not in relative and not relative.startswith(("mailto:","#")):
                    self.assertTrue((path.parent/relative).exists(),f"{path}: {relative}")
            for marker in ("~~~","```"):
                self.assertEqual(sum(line.lstrip().startswith(marker) for line in body.splitlines())%2,
                                 0,f"{path}: unbalanced {marker}")
    def test_single_ui_and_detailed_boundaries(self):
        for path in DOCS[:6]:
            body=path.read_text()
            self.assertNotIn("8502",body)
        readme=DOCS[0].read_text()
        for word in ("infra","config","talon","app","reapply","hr_aggregate_sql",
                     "feat/people-analytics-governed-demo","Docker","signed"):
            self.assertIn(word,readme)
        self.assertIn("```mermaid\nflowchart",readme)
        self.assertIn("```mermaid\nflowchart",DOCS[3].read_text())
        self.assertIn("fake",DOCS[5].read_text().lower())
        self.assertIn("not a packet capture",DOCS[4].read_text().lower())
    def test_js_syntax(self):
        import shutil,subprocess
        if not shutil.which("node"):self.skipTest("node not installed")
        from web_ui import HTML
        script=HTML.split("<script>",1)[1].split("</script>",1)[0]
        p=subprocess.run(["node","--check"],input=script,text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)

if __name__=="__main__":unittest.main()
