"""Keep the People Analytics integration docs accurate and shell examples executable."""
from pathlib import Path
import re
import shutil
import subprocess
import unittest

CASE=Path(__file__).resolve().parent
ROOT=CASE.parents[1]
DOCS=[CASE/"README.md",CASE/"CI_COVERAGE.md",CASE/"screenshots"/"README.md",ROOT/"README.md",ROOT/"docs"/"AUDIENCE_DEMOS.md"]

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
    def test_architecture_and_enforcement_diagrams(self):
        body=(CASE/"README.md").read_text(encoding="utf-8")
        diagrams=re.findall(r"```mermaid\n(.*?)\n```",body,re.DOTALL)
        self.assertEqual(len(diagrams),3,
                         "Keep one business overview, one technical topology and one decision flow")
        business,topology,decisions=diagrams
        self.assertTrue(business.startswith("flowchart LR"))
        self.assertTrue(topology.startswith("flowchart LR"))
        self.assertTrue(decisions.startswith("flowchart TB"))
        self.assertLess(body.index("## Talon at a glance"),
                        body.index("## The existing application"))

        # Business overview: deliberately short, readable and faithful to the
        # governed paths. Model requests do not go to the database.
        for edge in ('U(["User"]) --> W["Workforce app"]',
                     'W -->|"AI requests"| T["Talon"]',
                     'T -->|"Model calls"| L["LLM"]',
                     'T -->|"Approved tools"| H["HR analytics"]',
                     'H --> D[("DuckDB")]',
                     'T -->|"Decisions & spend"| E["Signed evidence"]'):
            self.assertIn(edge,business)
        self.assertLessEqual(sum(1 for line in business.splitlines() if "-->" in line),6)
        self.assertNotIn("L --> D",business)
        self.assertIn("existing charts use a separate read-only analytics path",body)

        # The Workforce browser never accesses Talon, OpenAI or the HR
        # backend directly. The separately paired operator browser connects
        # only to the read-only Talon console.
        self.assertIn('B -->|"HTTP"| W',topology)
        self.assertIn('OperatorBrowser -->|"One-time pairing, read-only"| OC',topology)
        self.assertIn('OC -->|"Read-only evidence and runtime status"| E',topology)
        self.assertNotIn('OperatorBrowser -->|"HTTP"| H',topology)
        self.assertIn('W <-->|"Tool discovery, calls and receipts"| M',topology)
        self.assertIn('W <-->|"Model requests and responses"| G',topology)
        self.assertIn('M -->|"Allowed tool calls only"| H',topology)
        self.assertNotIn('B -->|',topology.replace('B -->|"HTTP"| W',''))
        self.assertIn('A -->|"Read-only aggregate queries"| D',topology)
        self.assertIn('H -->|"Named aggregates; restricted SQL"| D',topology)
        self.assertIn('C -->|"Session summaries and signature checks"| E',topology)

        # A Talon denial, a post-dispatch HR SQL rejection and provider spend
        # must be distinct paths, backed by the shared signed evidence store.
        for node in ("Talon denies; not dispatched",
                     "HR rejects SQL after dispatch; outcome unknown",
                     "Independent HR dispatch counter",
                     "Talon model and budget policy?",
                     "talon costs --session",
                     "talon audit list / verify --session"):
            self.assertIn(node,decisions)
        self.assertIn('O -->|"If model requests a tool, app dispatches it"| T',decisions)
        spec=(CASE/"compose.isolated.yaml").read_text()
        # HR and BOTH Talon data-plane processes share one network namespace.
        # Each Talon process loads the trusted HR MCP source at startup.
        # The HR listener is bound to 127.0.0.1:9091 and cannot be reached
        # directly over app_net, while both Talon ports have separate aliases.
        self.assertEqual(spec.count('network_mode: "service:hr-mcp-net"'),3)
        self.assertIn("DEMO_BIND_HOST: 127.0.0.1",spec)
        self.assertIn("aliases: [talon-mcp, talon-gateway]",spec)
        self.assertIn("volumes: [hr_data:/data:ro]",spec)
        live=spec.split("  talon-gateway:\n",1)[1].split("\n  talon-ui:",1)[0]
        for term in ('profiles: ["live"]', 'network_mode: "service:hr-mcp-net"',
                     'hr-server:', 'condition: service_healthy',
                     '"8082"', '"--gateway"'):
            self.assertIn(term,live)
        self.assertNotIn('networks: [app_net]',live)
        self.assertNotIn('ports:',live)

    def test_existing_vault_key_continuity_guard(self):
        """Do not advise regenerating credentials over persisted demo evidence."""
        body=(CASE/"README.md").read_text(encoding="utf-8")
        self.assertIn('if [ ! -f .env ]; then',body)
        self.assertIn('[ -e .state/talon/secrets.db ]',body)
        self.assertIn('[ -e .state/talon/evidence.db ]',body)
        self.assertIn('cipher: message authentication failed',body)
        self.assertIn('HR_DEMO_SECRETS_KEY',body)
        self.assertIn('HR_DEMO_SIGNING_KEY',body)
        self.assertIn('mv .state/talon "$backup"',body)
        self.assertIn('docker compose -f compose.isolated.yaml --profile live --profile operator down',body)

    def test_read_only_operator_console_compose_and_walkthrough(self):
        """The optional operator view must not become a second HR app or an admin surface."""
        body=(CASE/"README.md").read_text(encoding="utf-8")
        shots=(CASE/"screenshots"/"README.md").read_text(encoding="utf-8")
        spec=(CASE/"compose.isolated.yaml").read_text(encoding="utf-8")
        match=re.search(r"(?ms)^  talon-ui:\n(?P<service>.*?)(?=^  [\w-]+:|\Z)",spec)
        self.assertIsNotNone(match,"Expected a separately managed talon-ui service")
        service=match.group("service")
        for term in ('profiles: ["operator"]', "talon", "ui", "serve", "--listen", "0.0.0.0:8787",
                     "--allow-non-loopback",
                     "/policies/gateway.talon.yaml", "./.state/talon:/state",
                     "./.state/policy:/policies:ro", "/usr/local/bin/talon:ro",
                     "TALON_SIGNING_KEY:", 'ports: ["127.0.0.1:8787:8787"]',
                     "networks: [app_net]"):
            self.assertIn(term,service)
        for excluded in ("private_hr", "TALON_ADMIN_KEY:", "TALON_SECRETS_KEY:",
                         "volumes: *talon-volumes", "./:/case:ro", "env_file:"):
            self.assertNotIn(excluded,service,"Read-only console must not gain HR network or privileged credentials")
        self.assertIn("docker compose -f compose.isolated.yaml --profile operator exec -T talon-ui talon ui pair",body)
        # Pair prints only an acknowledgement. The generated code appears on
        # the running Console's stdout, not in the CLI command's output.
        for item in ("Talon console pairing code: XXXXX-XXXXX-XXXXX-XXXXX",
                     "--profile operator logs --no-color --tail=30 talon-ui",
                     "NOT the pairing code", "Generating a new code invalidates",
                     "--profile operator ps -a talon-ui", "ssh -L 8787:127.0.0.1:8787"):
            self.assertIn(item, body)
        self.assertIn("talon ui serve --help",body)
        self.assertIn("http://127.0.0.1:8787/",body)
        self.assertIn("read-only",body.lower())
        self.assertIn("GUIDED",body)
        self.assertIn("evidence-observed",body)
        for screenshot in ("01-talon-system.png", "02-talon-effective-policy.png",
                           "03-talon-session-timeline.png", "04-talon-evidence-verification.png",
                           "05-talon-costs-live.png"):
            self.assertIn("screenshots/"+screenshot,body)
            self.assertIn(screenshot,shots)
        self.assertIn("Never include the one-time pairing code",shots)
        for term in ("Approvals", "read only", "empty", "independent reviewer", "No action approval requests"):
            self.assertIn(term.lower(), shots.lower())
        self.assertIn("Approvals", body)
        self.assertNotIn("approve/reject buttons", body.lower())

    def test_quickstart_setup_works_from_case_directory(self):
        """A user following the case README must not need to guess the cwd."""
        body = (CASE / "README.md").read_text(encoding="utf-8")
        setup = body.split("### Prepare Talon", 1)[1].split("## 1.", 1)[0]
        first_step = body.split("## 1. Start DuckDB", 1)[1].split("## 2.", 1)[0]
        self.assertIn("from this directory", setup)
        self.assertIn("bash ../../scripts/prepare-people-analytics-talon.sh", setup)
        self.assertIn('export HR_DEMO_TALON_BIN="$(realpath ../../.state/talon-bin/talon)"', setup)
        self.assertNotIn("bash scripts/prepare-people-analytics-talon.sh", setup)
        self.assertNotIn("bash scripts/check-people-analytics-talon-binary.sh", setup)
        self.assertNotIn("cd cases/people-analytics-copilot", first_step)
        self.assertTrue((CASE / "../../scripts/prepare-people-analytics-talon.sh").resolve().is_file())
        self.assertTrue((CASE / "../../scripts/check-people-analytics-talon-binary.sh").resolve().is_file())

    def test_governed_mcp_binary_pin_and_safe_reinitialization(self):
        """Old Talon schema must not silently reject read_only or overwrite vault state."""
        body = (CASE / "README.md").read_text(encoding="utf-8")
        prepare = (ROOT / "scripts/prepare-people-analytics-talon.sh").read_text(encoding="utf-8")
        check = (ROOT / "scripts/check-people-analytics-talon-binary.sh").read_text(encoding="utf-8")
        agent = (CASE / "agent.talon.yaml").read_text(encoding="utf-8")
        self.assertEqual(agent.count("read_only: true"), 4)
        for term in ("scripts/prepare-people-analytics-talon.sh", "scripts/check-people-analytics-talon-binary.sh",
                     "no model calls", "already exists", "skipping init", "not a valid workaround"):
            self.assertIn(term.lower(), body.lower())
        self.assertNotIn('export HR_DEMO_TALON_BIN="$(command -v talon)"', body)
        self.assertIn('if [ ! -f .state/talon/agent.talon.yaml ]; then', body)
        self.assertIn('if [ ! -f .state/policy/gateway.talon.yaml ]; then', body)
        for term in ("TALON_GOVERNED_MCP_COMMIT", "go -C", "git clone", ".state/talon-bin"):
            self.assertIn(term, prepare)
        for term in ("go version -m", "vcs.revision=", "TALON_GOVERNED_MCP_COMMIT", "FAIL"):
            self.assertIn(term, check)
        for script in ("scripts/prepare-people-analytics-talon.sh",
                       "scripts/check-people-analytics-talon-binary.sh"):
            proc = subprocess.run(["bash", "-n", str(ROOT / script)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"{script}: {proc.stderr}")
        # A clearly wrong executable should fail before any Talon state change.
        if shutil.which("go"):
            import sys
            proc = subprocess.run(
                ["bash", str(ROOT / "scripts/check-people-analytics-talon-binary.sh"),
                 sys.executable],
                capture_output=True, text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("Expected:", proc.stderr)
            self.assertIn("prepare-people-analytics-talon.sh", proc.stderr)

    def test_governed_mcp_only_no_proxy_shim(self):
        """The case uses Talon's governed /mcp; the removed MCP proxy has no shim."""
        removed=("/mcp/proxy","--proxy-config","proxy.talon.yaml","proxy.isolated.talon.yaml")
        files=[p for p in CASE.rglob("*") if p.is_file() and p.suffix in (".py",".yaml",".yml",".sh","")
               and ".state" not in p.parts and "__pycache__" not in p.parts and p.name!="test_docs.py"]
        files+= [ROOT/"scripts"/name for name in ("test-people-analytics-talon.sh",
                 "test-people-analytics-real-provider.sh","test-people-analytics-policy-change.py",
                 "test-people-analytics-browser.py")]
        for path in files:
            body=path.read_text(encoding="utf-8",errors="replace")
            for term in removed:
                self.assertNotIn(term,body,f"{path} still references the removed MCP proxy ({term})")
        agent=(CASE/"agent.talon.yaml").read_text(encoding="utf-8")
        for term in ("actions:","sources:","type: mcp","definitions:","read_only: true",
                     "forbidden_tools:","- hr_employee_export"):
            self.assertIn(term,agent)
        self.assertRegex((CASE/"TALON_GOVERNED_MCP_COMMIT").read_text().strip(),r"^[0-9a-f]{40}$")
        app=(CASE/"demo.py").read_text(encoding="utf-8")
        self.assertIn("'/mcp'",app)
        self.assertIn("server/discover",app)
        self.assertIn("talon_execute_operation",app)

    def test_web_app_does_not_fabricate_employee_access_denials(self):
        app=(CASE/"demo.py").read_text(encoding="utf-8")
        prompt=(CASE/"agent_runtime.py").read_text(encoding="utf-8")
        ui=(CASE/"web_ui.py").read_text(encoding="utf-8")
        self.assertNotIn("Employee-level details are not authorized",app)
        self.assertNotIn("Unsafe proxy policy: employee export was advertised",app)
        self.assertNotIn("If asked for employee-level records, explain that you cannot access",prompt)
        self.assertNotIn("Talon forbids that capability",ui)
        self.assertIn("g.get('decision') == 'deny'",app)
        self.assertIn("g.get('decision') == 'allow'",app)
        self.assertIn("'hr_employee_export', {'scope': 'all'}",app)
        self.assertIn("name not in advertised",prompt)
        self.assertIn("if self.live_mode:",app)

    def test_js_syntax(self):
        if not shutil.which("node"):self.skipTest("Node.js is not installed")
        from web_ui import HTML
        script=HTML.split("<script>",1)[1].split("</script>",1)[0]
        result=subprocess.run(["node","--check"],input=script,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=="__main__":unittest.main()
