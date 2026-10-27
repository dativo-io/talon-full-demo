"""Keep the People Analytics integration docs accurate and shell examples executable."""
from pathlib import Path
import re
import shutil
import subprocess
import unittest

CASE=Path(__file__).resolve().parent
ROOT=CASE.parents[1]
DOCS=[CASE/"README.md",CASE/"CI_COVERAGE.md",ROOT/"README.md",ROOT/"docs"/"AUDIENCE_DEMOS.md"]

class DocumentationContract(unittest.TestCase):
    def test_links_and_fences(self):
        for path in DOCS:
            body=path.read_text(encoding="utf-8")
            for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)",body):
                local=target.split("#",1)[0].split("?",1)[0].strip()
                if local and "://" not in local and not local.startswith(("mailto:","#")):
                    self.assertTrue((path.parent/local).exists(),f"{path}: {local}")
            for fence in ("~~~","```"):
                self.assertEqual(sum(x.lstrip().startswith(fence) for x in body.splitlines())%2,0,f"{path}: {fence}")
    def test_native_talon_workflow(self):
        body=(CASE/"README.md").read_text()
        for term in ("talon init", "talon validate", "talon secrets set", "talon audit",
                     "talon-mcp", "hr_aggregate_sql", "docker compose", "SIGNED", "DuckDB"):
            self.assertIn(term.casefold(),body.casefold())
        self.assertIn("```mermaid\nflowchart",body)
        # Observability examples must retain their correct provenance and limits.
        for field in ("metrics_reconcile_recovered", "recovered_events",
                      "correlation_id", "X-Talon-Session-ID", "data_flow_recorded",
                      "flow_items", "flow_regions=US", "HR_AI_TRACE",
                      "not_dispatched", "talon audit verify --session",
                      "talon costs --session", "session_budget_exceeded",
                      "hr_employee_export", "tool_calls_denied"):
            self.assertIn(field, body)
        self.assertNotIn("scripts/people-analytics-isolated.sh",body)
        self.assertNotIn("presenter",body.lower())
        self.assertNotIn("8502",body)
        spec=(CASE/"compose.isolated.yaml").read_text()
        self.assertIn("talon-cli:",spec)
        self.assertNotIn("talon-init:",spec)
    def test_js_syntax(self):
        if not shutil.which("node"):self.skipTest("Node.js is not installed")
        from web_ui import HTML
        script=HTML.split("<script>",1)[1].split("</script>",1)[0]
        result=subprocess.run(["node","--check"],input=script,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=="__main__":unittest.main()
