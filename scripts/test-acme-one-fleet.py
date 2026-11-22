#!/usr/bin/env python3
"""ACME full-fleet acceptance: FOUR native use cases, ONE persistent Talon.

Tests live HR MCP, customer-support model+synthetic refund, Document Processing
session-cost admission, and real synthetic OrderDesk PostgreSQL recovery in one
Talon process, company policy, data directory and read-only Operations Console.

The n8n import and actual Claude/OpenShell client are proven (or explicitly
NOT proven) by their separate consumer gates. This script makes no claim of
real Shopify payments, external provider inference, or Claude/OpenShell hop.
"""
import http.cookiejar as cookiejar
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

ROOT = Path(__file__).resolve().parents[1]
HR = ROOT / "cases/people-analytics-copilot"
SHOP = ROOT / "integrations/n8n/shopify-support"
ORDER = ROOT / "cases/claude-postgres-incident"
CORE = Path(os.environ.get("TALON_CORE_DIR", ROOT.parent / "talon")).resolve()
TALON = str(Path(os.environ.get("TALON_FLEET_BIN", shutil.which("talon") or "")).resolve())
EXPECTED_SHA = os.environ.get("TALON_CORE_SHA", "")
SUPPORT = "customer-support"
PEOPLE = "hr-analytics-assistant"
DOCUMENT = "document-summary"
ORDERDESK = "orderdesk-oncall"
NAMES = (SUPPORT, PEOPLE, DOCUMENT, ORDERDESK)
KEY_RE = re.compile(r"talon_uc_[0-9a-f]{48}")
REVIEW_RE = re.compile(r"talon_appr_cred_[0-9a-f]+\.[A-Za-z0-9_-]+")


def assert_true(value, explanation):
    if not value:
        raise AssertionError(explanation)


def run(args, *, cwd=None, env=None):
    proc = subprocess.run([str(a) for a in args], cwd=cwd, env=env,
                          capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"command {args[:3]} failed ({proc.returncode}): "
                           f"{proc.stdout[-1400:]} {proc.stderr[-1400:]}")
    return proc.stdout


def available_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def http(url, payload=None, *, key=None, headers=None, opener=None):
    data = None if payload is None else json.dumps(payload).encode()
    hh = {"Content-Type": "application/json", **(headers or {})}
    if key:
        hh["Authorization"] = "Bearer " + key
    req = Request(url, data=data, method="POST" if data is not None else "GET", headers=hh)
    try:
        with (opener or urlopen)(req, timeout=20) as response:
            raw = response.read()
            if not raw:
                return response.status, {}
            try:
                return response.status, json.loads(raw)
            except ValueError:
                # /health and /healthz are allowed to return plain text.
                return response.status, {"body": raw[:200].decode(errors="replace")}
    except HTTPError as error:
        raw = error.read()
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = {"body": raw[:200].decode(errors="replace")}
        return error.code, parsed


def wait(url, seconds=40):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            status, _ = http(url)
            if status == 200:
                return
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(0.3)
    raise RuntimeError(f"timed out waiting for {url}")


class Fleet:
    def __init__(self, work):
        self.work = work
        self.install = work / "install"
        self.install.mkdir()
        (work / "state").mkdir()
        self.env = os.environ.copy()
        self.env.update({
            "TALON_DATA_DIR": str(work / "state"),
            "TALON_SECRETS_KEY": secrets.token_hex(32),
            "TALON_SIGNING_KEY": secrets.token_hex(32),
            "TALON_ADMIN_KEY": secrets.token_hex(24),
            "TALON_GATEWAY_CONFIG": str(self.install / "talon.config.yaml"),
            "TALON_AGENTS_DIR": str(self.install / "agents"),
            "HR_DEMO_DB_PATH": str(work / "hr.duckdb"),
        })
        self.ports = {name: available_port() for name in ("talon", "shop", "doc", "ui")}
        # The committed HR and OrderDesk applications bind these exact ports.
        self.hrport = 9091
        self.orderport = 9080
        self.procs = []
        self.logs = []
        self.keys = {}
        self.ops = {}
        self.compose = ["docker", "compose", "-p", "talon-acme-one-fleet", "-f",
                        str(ORDER / "compose.yaml")]

    def cli(self, *args, extra=None):
        env = {**self.env, **(extra or {})}
        return run([TALON, *args], cwd=self.install, env=env)

    def spawn(self, name, cmd, *, cwd=None, env=None):
        logfile = (self.work / (name + ".log")).open("w")
        self.logs.append(logfile)
        child = subprocess.Popen(cmd, cwd=cwd, env=env or self.env,
                                 stdout=logfile, stderr=subprocess.STDOUT)
        self.procs.append(child)
        return child

    def addr(self):
        return f"http://127.0.0.1:{self.ports['talon']}"

    def call(self, path, payload=None, *, agent=None, reviewer=None, session=None):
        headers = {}
        if session:
            headers["X-Talon-Session-ID"] = session
        return http(self.addr() + path, payload, key=reviewer or self.keys.get(agent),
                    headers=headers)

    def mcp(self, key, method, tool=None, arguments=None, session="fleet-hr"):
        meta = {
            "io.modelcontextprotocol/protocolVersion": "2026-07-28",
            "io.modelcontextprotocol/clientInfo": {"name": "acme-fleet", "version": "1"},
            "io.modelcontextprotocol/clientCapabilities": {},
        }
        params = {"_meta": meta}
        headers = {"MCP-Protocol-Version": "2026-07-28",
                   "Mcp-Method": method, "Accept": "application/json, text/event-stream",
                   "X-Talon-Session-ID": session}
        if tool is not None:
            params["name"] = tool
            params["arguments"] = arguments or {}
            headers["Mcp-Name"] = tool
        return http(self.addr() + "/mcp",
                    {"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                    key=key, headers=headers)

    @staticmethod
    def governance(result):
        obj = result.get("result", {}).get("_meta")
        if isinstance(obj, dict):
            return obj.get("io.dativo.talon/governance")
        return (result.get("error", {}).get("data") or {}).get("io.dativo.talon/governance")

    def independent(self, kind):
        if kind == "hr":
            return http(f"http://127.0.0.1:{self.hrport}/debug/counters")[1]
        if kind == "shop":
            return http(f"http://127.0.0.1:{self.ports['shop']}/count")[1]
        if kind == "order":
            return http(f"http://127.0.0.1:{self.orderport}/_test/state")[1]
        if kind == "doc":
            return http(f"http://127.0.0.1:{self.ports['doc']}/count")[1]
        raise ValueError(kind)

    def operation(self, agent, op, action, args):
        code, out = self.call("/v1/action-operations",
                              {"operation_id": op, "action": action, "arguments": args},
                              agent=agent)
        return code, out

    def attempt(self, agent, op):
        return self.call(f"/v1/action-operations/{op}/attempts", {},
                         agent=agent)

    def review(self, reviewer, approval_id):
        return self.call(f"/v1/approvals/{approval_id}/decisions",
                         {"decision": "approve", "reason": "Synthetic independent ACME review"},
                         reviewer=reviewer)

    def prepare(self):
        assert_true(EXPECTED_SHA == "156188dea65cb6feab01aa92093a00e7717a6dd6",
                    "test must use the exact verified merged Talon main SHA")
        assert_true(TALON and Path(TALON).is_file(), "source-built Talon binary required")
        assert_true((CORE / "examples/n8n-refund/use-case-action.append.yaml").is_file(),
                    "pinned core checkout missing")
        run(["docker", "info"])
        run(["python3", "warehouse.py", "seed"], cwd=HR, env=self.env)
        self.spawn("hr", ["python3", "demo.py", "hr"], cwd=HR)
        wait(f"http://127.0.0.1:{self.hrport}/debug/counters")
        self.spawn("shop", ["python3", str(SHOP / "fixture.py"),
                            "--port", str(self.ports["shop"]),
                            "--log", str(self.work / "shop.jsonl"),
                            "--action-fixture"])
        wait(f"http://127.0.0.1:{self.ports['shop']}/health")
        self.spawn("document-provider", ["python3", str(ROOT / "scripts/acme-fleet-provider.py"),
                                         "--port", str(self.ports["doc"])])
        wait(f"http://127.0.0.1:{self.ports['doc']}/health")
        run(self.compose + ["up", "--build", "-d", "--wait"], cwd=ORDER)
        wait(f"http://127.0.0.1:{self.orderport}/_test/state", 60)

        cfg = f"""agents_dir: ./agents
agents_reload_interval: "2s"
gateway:
  enabled: true
  listen_prefix: "/v1/proxy"
  providers:
    openai:
      enabled: true
      secret_name: openai-api-key
      base_url: "http://127.0.0.1:{self.ports['shop']}"
      allowed_models: ["gpt-4o-mini"]
    mock-openai:
      enabled: true
      secret_name: mock-openai-key
      base_url: "http://127.0.0.1:{self.ports['doc']}"
      region: "LOCAL"
      api_family: "openai"
      allowed_models: ["gpt-4o-mini"]
  organization_policy:
    defaults:
      pii_action: block
      daily_cost: 10.00
    constraints:
      forbidden_tools: [hr_employee_export, volume_delete]
      action_approvals:
        rules:
          orderdesk-staging-repair:
            actions: [reconcile_staging_db_credentials]
            approver_groups: [oncall]
        argument_rules:
          refund-too-large:
            actions: [create_refund_request]
            argument: amount
            type: decimal
            operator: gt
            value: "500.00"
            effect: deny
    log_prompts: false
    log_responses: false
"""
        (self.install / "talon.config.yaml").write_text(cfg)
        pricing = self.install / "pricing"
        pricing.mkdir()
        (pricing / "models.yaml").write_text(
            'version: "1"\ncurrency: USD\nproviders:\n'
            '  openai:\n    models:\n      gpt-4o-mini:\n'
            '        input_per_1m: 0.15\n        output_per_1m: 0.60\n'
            '  mock-openai:\n    inherit: openai\n')

        for name in NAMES:
            output = self.cli("agents", "add", name, "--tenant", "acme",
                              "--owner", f"{name}-operations",
                              "--description", f"ACME {name} existing application")
            match = KEY_RE.search(output)
            assert_true(match, f"native Talon registration omitted {name} key")
            self.keys[name] = match.group()
        assert_true(len(set(self.keys.values())) == 4, "four agents share a credential")

        agentpath = self.install / "agents"
        hr_file = (HR / "agent.talon.yaml").read_text()
        hr_file = hr_file.replace("  name: hr-analytics-assistant\n",
                                  "  name: hr-analytics-assistant\n  tenant_id: acme\n", 1)
        (agentpath / PEOPLE / "agent.talon.yaml").write_text(hr_file)

        support_path = agentpath / SUPPORT / "agent.talon.yaml"
        action_snippet = (CORE / "examples/n8n-refund/use-case-action.append.yaml").read_text()
        action_snippet = action_snippet.replace(
            "https://refunds.internal/v1/refunds",
            f"http://127.0.0.1:{self.ports['shop']}/refunds")
        with support_path.open("a") as f:
            f.write("\n" + action_snippet)

        order_file = (ORDER / "config/agent.talon.yaml.template").read_text()
        order_file = order_file.replace("name: claude-orderdesk", "name: orderdesk-oncall", 1)
        order_file = order_file.replace("claude-orderdesk-talon-key", "orderdesk-oncall-talon-key")
        # Host-key fixture only: remove the real OpenShell workload binding.
        # Do not claim this is a verified sandbox hop.
        order_file, count = re.subn(
            r"  workload_identity:\n    bindings:\n      - runtime: openshell\n"
            r"        subject: .*\n", "", order_file, count=1)
        assert_true(count == 1, "the OpenShell workload boundary changed; refuse host-key fixture")
        (agentpath / ORDERDESK / "agent.talon.yaml").write_text(order_file)

        doc_file = f"""agent:
  name: document-summary
  description: ACME document processing synthetic cost-bound use case
  version: "1.0.0"
  tenant_id: acme
  key:
    secret_name: document-summary-talon-key
policies:
  allowed_providers: ["mock-openai"]
  cost_limits:
    per_request: 1.00
    daily: 10.00
    monthly: 100.00
  session_limits:
    max_cost: 0.45
audit:
  log_level: detailed
  retention_days: 30
  include_prompts: false
  include_responses: false
"""
        (agentpath / DOCUMENT / "agent.talon.yaml").write_text(doc_file)
        self.cli("secrets", "set", "openai-api-key", "synthetic-provider-key")
        self.cli("secrets", "set", "mock-openai-key", "synthetic-document-provider")
        self.cli("validate")
        for name in NAMES:
            effective = self.cli("agents", "show", name, "--effective")
            assert_true("volume_delete" in effective,
                        f"company forbidden-tools rule not projected for {name}")
        for group in ("support-leads", "oncall"):
            output = self.cli("approver", "add", "--name", f"acme-{group}",
                              "--tenant", "acme", "--groups", group)
            match = REVIEW_RE.search(output)
            assert_true(match, f"independent {group} reviewer not issued")
            self.keys["review-" + group] = match.group()
        self.spawn("talon", [TALON, "serve", "--host", "127.0.0.1", "--port",
                             str(self.ports["talon"]), "--gateway",
                             "--gateway-config", str(self.install / "talon.config.yaml")],
                   cwd=self.install)
        wait(self.addr() + "/health", 60)
        print("PASS four native use-case keys and one company policy, one Talon serve+store", flush=True)

    def hr(self):
        c, out = self.mcp(self.keys[PEOPLE], "tools/list")
        names = {t["name"] for t in out.get("result", {}).get("tools", [])}
        assert_true(c == 200 and "hr_aggregate_sql" in names
                    and "hr_employee_export" not in names, str(out)[:500])
        c, other = self.mcp(self.keys[SUPPORT], "tools/list", session="fleet-support")
        other_names = {t["name"] for t in other.get("result", {}).get("tools", [])}
        assert_true("hr_aggregate_sql" not in other_names, "support key can discover HR")
        c, good = self.mcp(self.keys[PEOPLE], "tools/call", "hr_headcount_summary", {})
        g = self.governance(good)
        assert_true(c == 200 and g and g.get("code") == "allowed",
                    f"HR governed aggregate failed: {good}")
        assert_true(self.independent("hr")["hr_headcount_summary"] == 1,
                    "HR read did not execute exactly once")
        self.ops["hr-read"] = g["operationId"]
        c, denied = self.mcp(self.keys[PEOPLE], "tools/call",
                             "hr_employee_export", {"scope": "all"})
        d = self.governance(denied)
        assert_true(d and d.get("code") == "policy_denied"
                    and d.get("provenance") == "not_dispatched", str(denied)[:500])
        assert_true(self.independent("hr")["hr_employee_export"] == 0,
                    "forbidden employee export reached HR")
        self.ops["hr-deny"] = d["operationId"]
        c, unknown = self.mcp(self.keys[PEOPLE], "tools/call", "hr_aggregate_sql",
                              {"sql": "SELECT employee_id, full_name FROM employees"})
        u = self.governance(unknown)
        assert_true(u and u.get("code") == "upstream_outcome_unknown",
                    f"backend rejection must remain UNKNOWN: {unknown}")
        assert_true(self.independent("hr")["hr_aggregate_sql"] == 1,
                    "HR rejection was not dispatched exactly once")
        self.ops["hr-unknown"] = u["operationId"]
        print("PASS HR real backend: aggregate=1, export=0, SQL UNKNOWN=1; distinct key", flush=True)

    def support(self):
        facts = {"issue_hints": ["order_status"], "financial_status": "PAID",
                 "fulfillment_status": "UNFULFILLED", "proposed_refund_eur": None}
        req = {"model": "gpt-4o-mini", "messages": [{"role": "user",
               "content": json.dumps(facts)}]}
        c, out = self.call("/v1/proxy/openai/v1/chat/completions", req,
                           agent=SUPPORT, session="fleet-support")
        assert_true(c == 200 and out.get("choices"), f"support useful draft failed {out}")
        count = (self.work / "shop.jsonl").read_text().count('"kind": "provider_call"')
        assert_true(count == 1, "support provider was not reached exactly once")
        c, blocked = self.call("/v1/proxy/openai/v1/chat/completions",
                              {"model": "gpt-4o-mini", "messages": [
                                  {"role": "user", "content":
                                   "Email jan.kowalski@example.com and IBAN PL61109010140000071219812874"}]},
                              agent=SUPPORT, session="fleet-support")
        assert_true(c in (400, 403), f"company PII rule did not deny: {blocked}")
        assert_true((self.work / "shop.jsonl").read_text().count('"kind": "provider_call"') == 1,
                    "provider saw a PII-denied request")

        def body(amount):
            return {"ticket_id": "SUP-1001", "amount": amount, "currency": "EUR"}

        code, denied = self.operation(SUPPORT, "fleet-refund-750",
                                      "create_refund_request", body("750.00"))
        assert_true(code == 403 and self.independent("shop")["calls"] == 0,
                    f"company refund DENY dispatched: {code} {denied}")
        self.ops["support-deny"] = "fleet-refund-750"
        code, allow = self.operation(SUPPORT, "fleet-refund-25",
                                     "create_refund_request", body("25.00"))
        assert_true(code in (200, 201, 202), f"refund establish: {allow}")
        assert_true(self.independent("shop")["calls"] == 0, "establish dispatched refund")
        code, claim = self.attempt(SUPPORT, "fleet-refund-25")
        assert_true(code == 200 and self.independent("shop")["calls"] == 1,
                    f"refund claim not exactly once: {code} {claim}")
        code, again = self.attempt(SUPPORT, "fleet-refund-25")
        assert_true(code == 409 and self.independent("shop")["calls"] == 1,
                    "replay double-refunded")
        code, conflict = self.operation(SUPPORT, "fleet-refund-25",
                                        "create_refund_request", body("26.00"))
        assert_true(code == 409 and self.independent("shop")["calls"] == 1,
                    "changed arguments under same intent dispatched")
        self.ops["support-25"] = "fleet-refund-25"
        code, review = self.operation(SUPPORT, "fleet-refund-249",
                                      "create_refund_request", body("249.00"))
        approval = (review.get("operation") or {}).get("approval") or {}
        assert_true(code == 202 and approval.get("id"),
                    f"expected separate reviewer: {code} {review}")
        assert_true(self.independent("shop")["calls"] == 1, "pending review dispatched")
        code, premature = self.attempt(SUPPORT, "fleet-refund-249")
        assert_true(code == 409 and self.independent("shop")["calls"] == 1,
                    "claim before review dispatched")
        code, decision = self.review(self.keys["review-support-leads"], approval["id"])
        assert_true(code == 200 and self.independent("shop")["calls"] == 1,
                    f"review should not dispatch: {code} {decision}")
        code, result = self.attempt(SUPPORT, "fleet-refund-249")
        assert_true(code == 200 and self.independent("shop")["calls"] == 2,
                    f"approved refund missing: {code} {result}")
        ledger = self.independent("shop")
        assert_true([x["amount"] for x in ledger["operations"]] == ["25.00", "249.00"],
                    f"incorrect independent synthetic ledger: {ledger}")
        self.ops["support-249"] = "fleet-refund-249"
        print("PASS Support: useful governed draft; PII 0 upstream; "
              "€25 1, €249 1 after review, €750 0, replay/conflict 0", flush=True)

    def document(self):
        prompt = {"model": "gpt-4o-mini", "messages": [
                  {"role": "user", "content": "Summarize the synthetic quarterly document."}]}
        status = []
        for _ in range(3):
            code, output = self.call("/v1/proxy/mock-openai/v1/chat/completions",
                                     prompt, agent=DOCUMENT, session="fleet-document")
            status.append(code)
            if code == 403:
                assert_true(output.get("error", {}).get("code") == "session_budget_exceeded",
                            f"wrong budget denial: {output}")
        assert_true(status == [200, 200, 403], f"session-budget outcome {status}")
        assert_true(self.independent("doc")["calls"] == 2,
                    "denied document request reached upstream")
        print("PASS Document: 2 useful synthetic model results, next cost denial, provider=2", flush=True)

    def orderdesk(self):
        before = self.independent("order")
        assert_true(before["staging"]["body"]["sqlstate"] == "28P01"
                    and before["production"]["rowCount"] == 1000, "OrderDesk fixture not in outage")
        code, denial = self.operation(ORDERDESK, "fleet-order-deny",
                                      "volume_delete", {"volume_id": "vol_production"})
        assert_true(code == 403 and self.independent("order")["infrastructure"]["volumeDeleteCalls"] == 0,
                    f"forbidden infrastructure mutation: {code} {denial}")
        self.ops["order-deny"] = "fleet-order-deny"
        operation = "fleet-order-repair"
        code, pending = self.operation(ORDERDESK, operation,
                                       "reconcile_staging_db_credentials",
                                       {"environment": "staging", "service": "orderdesk-api",
                                        "target_revision": "rev-002"})
        approval = (pending.get("operation") or {}).get("approval") or {}
        assert_true(code == 202 and approval.get("id"), f"on-call reviewer not required {pending}")
        assert_true(self.independent("order")["staging"]["body"]["sqlstate"] == "28P01",
                    "order operation dispatched before reviewer")
        code, approve = self.review(self.keys["review-oncall"], approval["id"])
        assert_true(code == 200, f"independent oncall approval failed: {approve}")
        assert_true(self.independent("order")["staging"]["body"]["sqlstate"] == "28P01",
                    "approval executed a repair")
        code, claim = self.attempt(ORDERDESK, operation)
        assert_true(code == 200 and claim.get("attempt", {}).get("status") == "succeeded",
                    f"repair claim failed: {code} {claim}")
        code, replay = self.attempt(ORDERDESK, operation)
        after = self.independent("order")
        assert_true(code == 409 and after["staging"]["httpStatus"] == 200
                    and after["orderdeskBusiness"]["httpStatus"] == 200
                    and after["production"]["rowCount"] == 1000
                    and after["production"]["amountSum"] == "55555500"
                    and after["dispatchCounts"]["reconcile_staging_db_credentials"] == 1
                    and after["infrastructure"]["volumeDeleteCalls"] == 0,
                    f"OrderDesk recovery, production or replay incorrect: {after}")
        self.ops["order-repair"] = operation
        print("PASS OrderDesk: real PostgreSQL staging outage recovered, production unchanged; "
              "oncall independent approval, 1 dispatch, volume delete=0", flush=True)

    def proofs(self):
        for label, operation in self.ops.items():
            result = self.cli("audit", "verify", "--operation", operation)
            assert_true("Lifecycle: VALID" in result,
                        f"{label} does not have a signed valid lifecycle")
        result = self.work / "signed-fleet.json"
        self.cli("audit", "export", "--format", "signed-json",
                 "--output", str(result))
        self.cli("audit", "verify", "--file", str(result))
        proof = result.read_text()
        for secret in (self.env["TALON_SECRETS_KEY"], self.env["TALON_SIGNING_KEY"],
                       self.env["TALON_ADMIN_KEY"], *self.keys.values()):
            assert_true(secret not in proof, "signed evidence leaked private credentials")
        rows = json.loads(proof)["records"]
        observed = {r.get("agent_id") for r in rows}
        assert_true(set(NAMES) <= observed, f"not all four applications have Talon evidence {observed}")
        assert_true(len(rows) >= 12, f"too few independent lifecycle/LLM proofs: {len(rows)}")
        print(f"PASS ONE signed proof pack, {len(rows)} records, four distinct real use-case identities, "
              f"{len(self.ops)} signed action lifecycles, zero leaked keys", flush=True)

    def console(self):
        self.spawn("console", [TALON, "ui", "serve", "--listen",
                               f"127.0.0.1:{self.ports['ui']}", "--store-wait", "20s"],
                   cwd=self.install)
        base = f"http://127.0.0.1:{self.ports['ui']}"
        wait(base + "/healthz", 50)
        logs = self.work / "console.log"
        code = None
        for _ in range(60):
            match = re.search(r"Talon console pairing code: ([A-Z2-9]{5}(?:-[A-Z2-9]{5}){3})",
                              logs.read_text())
            if match:
                code = match.group(1)
                break
            time.sleep(.2)
        assert_true(code, "native Console did not print private one-time pairing code")
        assert_true(http(base + "/console/v1/use-cases")[0] == 401,
                    "Console served use cases before browser pairing")
        jar = cookiejar.CookieJar()
        opener = build_opener(HTTPCookieProcessor(jar))
        status, _ = http(base + "/console/auth/pair", {"code": code}, opener=opener.open)
        assert_true(status == 200, "Console pairing failed")
        assert_true(len(list(jar)) == 1 and list(jar)[0].has_nonstandard_attr("HttpOnly"),
                    "Console session missing HttpOnly cookie")
        status, fleet = http(base + "/console/v1/use-cases", opener=opener.open)
        text = json.dumps(fleet)
        assert_true(status == 200 and all(name in text for name in NAMES),
                    f"Console does not show all four observed identities: {text[:900]}")
        for page in ("overview", "approvals", "sessions", "costs",
                     "configuration", "system"):
            assert_true(http(base + "/console/v1/" + page, opener=opener.open)[0] == 200,
                        f"Console {page} did not use the shared data store")
        assert_true(http(base + "/v1/secrets", opener=opener.open)[0] == 404,
                    "Console has a privileged route")
        print("PASS paired native Console sees 4 use cases in SAME store, "
              "all seven read-only areas and no privileged route", flush=True)

    def cleanup(self):
        for p in reversed(self.procs):
            if p.poll() is None:
                p.terminate()
        for p in reversed(self.procs):
            try:
                p.wait(timeout=8)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=5)
        try:
            run(self.compose + ["down", "-v", "--remove-orphans"], cwd=ORDER)
        finally:
            for f in self.logs:
                f.close()


def main():
    if not EXPECTED_SHA:
        raise RuntimeError("TALON_CORE_SHA must identify exact reviewed producer source")
    print("Producer:", EXPECTED_SHA, "binary:", run([TALON, "version"]).splitlines()[0],
          "(source-built, NOT an official released artifact)", flush=True)
    with tempfile.TemporaryDirectory(prefix="acme-four-use-cases-") as folder:
        fleet = Fleet(Path(folder))
        try:
            fleet.prepare()
            fleet.hr()
            fleet.support()
            fleet.document()
            fleet.orderdesk()
            fleet.proofs()
            fleet.console()
            print("PASS ACME ONE REAL TALON INSTALLATION: FOUR useful existing-use-case "
                  "boundaries; one company policy; counters+signed evidence+Console", flush=True)
            print("NOT RUN in this shared lane: n8n application UI, Claude/OpenShell "
                  "runtime C01-C12, paid LLM, real Shopify transactions", flush=True)
        except Exception:
            for file in (fleet.work / "talon.log", fleet.work / "hr.log",
                         fleet.work / "console.log", fleet.work / "document-provider.log"):
                if file.is_file():
                    print(f"--- diagnostic {file.name} (tail, keys must not be printed)", file=sys.stderr)
                    for line in file.read_text(errors="replace").splitlines()[-25:]:
                        print(line[:250], file=sys.stderr)
            raise
        finally:
            fleet.cleanup()


if __name__ == "__main__":
    main()
