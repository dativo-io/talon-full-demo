"""Incremental synthetic *repository* workload for a bounded plugin study.

24 service tickets in four interconnected Python packages, with public smoke
assertions and sealed edge-case graders. No runtime/third-party dependencies.
Not SWE-Bench, not a replication of the TokenEconomizer paper.
"""
import hashlib
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SPECS = json.loads("[{\"id\":\"01\",\"category\":\"normalize\",\"name\":\"user_handle\",\"description\":\"Normalize a handle: strip, lowercase, remove one leading @ and replace spaces with underscores.\",\"payload\":\"  @Ada Lovelace  \",\"expected\":\"ada_lovelace\",\"edges\":[[\"@Two  Words\",\"two__words\"],[\"BASIC\",\"basic\"]]},{\"id\":\"02\",\"category\":\"normalize\",\"name\":\"email_domain\",\"description\":\"Extract a lowercase domain from an email after trimming surrounding spaces.\",\"payload\":\" Dev@Example.COM \",\"expected\":\"example.com\",\"edges\":[[\"a@B.C\",\"b.c\"],[\"person@Sub.Example.Org\",\"sub.example.org\"]]},{\"id\":\"03\",\"category\":\"normalize\",\"name\":\"account_ref\",\"description\":\"Canonicalize account references: uppercase and remove hyphens and spaces.\",\"payload\":\" ab- 12-c \",\"expected\":\"AB12C\",\"edges\":[[\"x-y z\",\"XYZ\"],[\"  A1  \",\"A1\"]]},{\"id\":\"04\",\"category\":\"normalize\",\"name\":\"slug\",\"description\":\"URL slug: trim, lowercase and collapse consecutive whitespace to one hyphen.\",\"payload\":\" Hello   Data World \",\"expected\":\"hello-data-world\",\"edges\":[[\" A   B \",\"a-b\"],[\"ONE\",\"one\"]]},{\"id\":\"05\",\"category\":\"normalize\",\"name\":\"country\",\"description\":\"Standardize country codes: UK->GB, EL->GR, others uppercase after trimming.\",\"payload\":\" uk \",\"expected\":\"GB\",\"edges\":[[\"el\",\"GR\"],[\"pl\",\"PL\"]]},{\"id\":\"06\",\"category\":\"normalize\",\"name\":\"phone\",\"description\":\"Normalize phone punctuation: preserve initial +, keep digits, discard punctuation.\",\"payload\":\"+48 (22) 123-45\",\"expected\":\"+482212345\",\"edges\":[[\" 123-456 \",\"123456\"],[\"+1 (555) 44\",\"+155544\"]]},{\"id\":\"07\",\"category\":\"routing\",\"name\":\"priority\",\"description\":\"Severity label: P0->critical, P1->high, P2->medium, else low. Case insensitive.\",\"payload\":\"p1\",\"expected\":\"high\",\"edges\":[[\"P0\",\"critical\"],[\"p3\",\"low\"]]},{\"id\":\"08\",\"category\":\"routing\",\"name\":\"channel\",\"description\":\"Channel: outage->pager, question->chat, report->email, else queue.\",\"payload\":\"outage\",\"expected\":\"pager\",\"edges\":[[\"question\",\"chat\"],[\"unknown\",\"queue\"]]},{\"id\":\"09\",\"category\":\"routing\",\"name\":\"region\",\"description\":\"Route country: PL/DE/FR->eu, US/CA->na, everything else->global. Case insensitive.\",\"payload\":\"PL\",\"expected\":\"eu\",\"edges\":[[\"ca\",\"na\"],[\"JP\",\"global\"]]},{\"id\":\"10\",\"category\":\"routing\",\"name\":\"owner\",\"description\":\"Route team slug: data->platform, security->trust, growth->product, else operations.\",\"payload\":\"data\",\"expected\":\"platform\",\"edges\":[[\"security\",\"trust\"],[\"other\",\"operations\"]]},{\"id\":\"11\",\"category\":\"routing\",\"name\":\"incident_bucket\",\"description\":\"Age in minutes: below 15 fresh, below 60 active, otherwise stale.\",\"payload\":12,\"expected\":\"fresh\",\"edges\":[[59,\"active\"],[60,\"stale\"]]},{\"id\":\"12\",\"category\":\"routing\",\"name\":\"retry_tier\",\"description\":\"HTTP code: 429/503->backoff, 500/502->retry, else none.\",\"payload\":429,\"expected\":\"backoff\",\"edges\":[[500,\"retry\"],[401,\"none\"]]},{\"id\":\"13\",\"category\":\"policy\",\"name\":\"pii_class\",\"description\":\"Classify field: email/phone/ssn->sensitive, name/address->personal, else public.\",\"payload\":\"email\",\"expected\":\"sensitive\",\"edges\":[[\"address\",\"personal\"],[\"event\",\"public\"]]},{\"id\":\"14\",\"category\":\"policy\",\"name\":\"role_level\",\"description\":\"Role permissions: admin->write, analyst->read, guest->none, unknown->none.\",\"payload\":\"analyst\",\"expected\":\"read\",\"edges\":[[\"admin\",\"write\"],[\"unknown\",\"none\"]]},{\"id\":\"15\",\"category\":\"policy\",\"name\":\"retention\",\"description\":\"Retention days: audit->365, raw->30, cache->7, else 0.\",\"payload\":\"audit\",\"expected\":365,\"edges\":[[\"cache\",7],[\"other\",0]]},{\"id\":\"16\",\"category\":\"policy\",\"name\":\"risk_band\",\"description\":\"Risk score: >=80 high, >=40 medium, otherwise low.\",\"payload\":81,\"expected\":\"high\",\"edges\":[[40,\"medium\"],[0,\"low\"]]},{\"id\":\"17\",\"category\":\"policy\",\"name\":\"access_decision\",\"description\":\"Compare clearance and classification in order public < personal < sensitive. Input mapping with keys classification and clearance. Return allow or deny.\",\"payload\":{\"classification\":\"personal\",\"clearance\":\"sensitive\"},\"expected\":\"allow\",\"edges\":[[{\"classification\":\"sensitive\",\"clearance\":\"public\"},\"deny\"],[{\"classification\":\"public\",\"clearance\":\"personal\"},\"allow\"]]},{\"id\":\"18\",\"category\":\"policy\",\"name\":\"redact_email\",\"description\":\"Mask local email part with its first character followed by ***; preserve domain.\",\"payload\":\"alice@example.com\",\"expected\":\"a***@example.com\",\"edges\":[[\"b@a.io\",\"b***@a.io\"],[\"user@x.org\",\"u***@x.org\"]]},{\"id\":\"19\",\"category\":\"billing\",\"name\":\"cents\",\"description\":\"Convert a USD amount to integer cents using decimal ROUND_HALF_UP, avoiding binary-float rounding.\",\"payload\":12.345,\"expected\":1235,\"edges\":[[0.005,1],[1.994,199]]},{\"id\":\"20\",\"category\":\"billing\",\"name\":\"tier\",\"description\":\"Spend tier (USD): <10 tiny, <100 small, else large.\",\"payload\":15,\"expected\":\"small\",\"edges\":[[9.99,\"tiny\"],[100,\"large\"]]},{\"id\":\"21\",\"category\":\"billing\",\"name\":\"usage_ratio\",\"description\":\"For a mapping of spent and limit, return ratio rounded to two decimal places. If limit is zero return 0.\",\"payload\":{\"spent\":12,\"limit\":50},\"expected\":0.24,\"edges\":[[{\"spent\":1,\"limit\":0},0],[{\"spent\":100,\"limit\":100},1]]},{\"id\":\"22\",\"category\":\"billing\",\"name\":\"token_cost\",\"description\":\"For tokens and rate_per_million in mapping, return USD cost rounded to six decimals.\",\"payload\":{\"tokens\":125000,\"rate_per_million\":3},\"expected\":0.375,\"edges\":[[{\"tokens\":10,\"rate_per_million\":2},0.00002],[{\"tokens\":0,\"rate_per_million\":5},0]]},{\"id\":\"23\",\"category\":\"billing\",\"name\":\"alert_band\",\"description\":\"Spend utilization percent: >=100 blocked, >=80 warn, else ok.\",\"payload\":85,\"expected\":\"warn\",\"edges\":[[100,\"blocked\"],[79,\"ok\"]]},{\"id\":\"24\",\"category\":\"billing\",\"name\":\"batch_total\",\"description\":\"Sum integer amounts in a list, including empty list returning zero.\",\"payload\":[10,5,1],\"expected\":16,\"edges\":[[[],0],[[2,-2,7],7]]}]")
WARMUP = 8
TASK_COUNT = len(SPECS)
DESIGN = "repository-stream-v1"


def order(seed=0):
    """Stratified ordering: learning and measured phases cover all four domains."""
    if seed not in (0, 1, 2):
        raise ValueError("supported study seeds are 0, 1 and 2")
    groups = {name: [s for s in SPECS if s["category"] == name]
              for name in ("normalize", "routing", "policy", "billing")}
    rng = random.Random(seed)
    for values in groups.values():
        rng.shuffle(values)
    stream = [groups[group][i] for i in range(6)
              for group in ("normalize", "routing", "policy", "billing")]
    assert len(stream) == TASK_COUNT
    return stream


def write_repo(path):
    path = Path(path)
    if path.exists():
        shutil.rmtree(path)
    for sub in ("agentops", "agentops/rules", "issues", "tests", "docs"):
        (path / sub).mkdir(parents=True, exist_ok=True)
    (path / "agentops/__init__.py").write_text('"""AI operations ticket service."""\n')
    (path / "agentops/rules/__init__.py").write_text("")
    modules = sorted({x["category"] for x in SPECS})
    for module in modules:
        defs = ['"""Shared '+module+' business rules (implement issue functions here)."""', ""]
        for s in SPECS:
            if s["category"] == module:
                defs.extend([f'def {s["name"]}(value):',
                             f'    """Implement ticket {s["id"]}: see issues/{s["id"]}.md."""',
                             '    raise NotImplementedError("issue not implemented")', ""])
        (path / "agentops/rules" / (module + ".py")).write_text("\n".join(defs))
    svc = [
        '"""Public service routing layer. Each ticket updates a domain rule AND this registry."""',
        "from agentops.rules import " + ", ".join(modules),
        "",
        "HANDLERS = {",
    ]
    svc.extend(f'    "{s["id"]}": None, # {s["category"]}.{s["name"]}'
               for s in SPECS)
    svc.extend(["}", "", "def resolve(ticket, payload):",
                '    """Resolve two-digit ticket ID; implementations belong in rules modules."""',
                '    handler = HANDLERS[str(ticket).zfill(2)]',
                '    if handler is None:',
                '        raise NotImplementedError("wire ticket handler into HANDLERS")',
                '    return handler(payload)', ""])
    (path / "agentops/service.py").write_text("\n".join(svc))
    (path / "README.md").write_text(
        "# AgentOps ticket service\n\n"
        "A small, persistent Python service that accumulates ticket changes. "
        "Tickets live under issues/, domain implementations under agentops/rules/, "
        "and the public API is agentops.service.resolve(ticket, payload). "
        "Every ticket needs BOTH a rule and an API registration.\n\n"
        "See docs/testing.md before running tests. Do not change issue specifications "
        "or tests when repairing an issue. Avoid adding dependencies.\n")
    (path / "docs/testing.md").write_text(
        "# Development conventions\n\n"
        "Use the Python standard library only. From the checkout root, run "
        "`python3 -m unittest tests.test_issue_NN` for a ticket (NN = 01..24). "
        "Never run bare `pytest`: it is not a declared dependency. "
        "After each change, also run `python3 -m unittest discover -s tests`. "
        "The actual acceptance suite also contains hidden edge cases.\n")
    for s in SPECS:
        (path / "issues" / (s["id"] + ".md")).write_text(
            f'# Issue {s["id"]}: {s["name"]}\n\n'
            f'Domain: {s["category"]}.\n\n'
            f'{s["description"]}\n\n'
            'Implement the named function in its domain rule module AND register '
            'it in agentops/service.py. Keep previous tickets working.\n'
            f'Public example payload: {json.dumps(s["payload"])}\n'
            f'Expected service response: {json.dumps(s["expected"])}\n')
        (path / "tests/__init__.py").write_text("")
        (path / "tests" / ("test_issue_"+s["id"]+".py")).write_text(
            "import unittest\nfrom agentops.service import resolve\n"
            f"class Ticket{int(s['id'])}(unittest.TestCase):\n"
            "    def test_visible_case(self):\n"
            f"        self.assertEqual(resolve({json.dumps(s['id'])}, "
            f"{repr(s['payload'])}), {repr(s['expected'])})\n")
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)


def digest(path):
    h = hashlib.sha256()
    for f in sorted(p for p in Path(path).rglob("*") if p.is_file() and ".git" not in p.parts):
        h.update(f.relative_to(path).as_posix().encode() + b"\0" + f.read_bytes())
    return h.hexdigest()


def grade(path, issue_id):
    s = next(spec for spec in SPECS if spec["id"] == str(issue_id).zfill(2))
    with tempfile.TemporaryDirectory(prefix="te-repo-hidden-grade-") as tmp:
        dst = Path(tmp)
        shutil.copytree(Path(path) / "agentops", dst / "agentops")
        assert_s = ["import unittest",
                    "from agentops.service import resolve",
                    f"from agentops.rules import {s['category']}",
                    "class Sealed(unittest.TestCase):"]
        for i, (payload, expected) in enumerate(
                [(s["payload"], s["expected"])] + s["edges"]):
            assert_s += [f"    def test_case_{i:02d}(self):",
                         f"        self.assertEqual(resolve({repr(s['id'])}, {repr(payload)}), {repr(expected)})",
                         f"        self.assertEqual({s['category']}.{s['name']}({repr(payload)}), {repr(expected)})"]
        (dst / "test_sealed.py").write_text("\n".join(assert_s) + "\n")
        result = subprocess.run([sys.executable, "-m", "unittest", "-q", "test_sealed"],
                                cwd=dst, capture_output=True, timeout=25)
        return result.returncode == 0


def validate():
    with tempfile.TemporaryDirectory(prefix="te-study-validate-") as tmp:
        a, b = Path(tmp) / "a", Path(tmp) / "b"
        write_repo(a)
        write_repo(b)
        assert digest(a) == digest(b)
        assert TASK_COUNT == 24 and WARMUP == 8
        assert len(set(s["id"] for s in SPECS)) == TASK_COUNT
        for seed in range(3):
            ids = [s["id"] for s in order(seed)]
            assert set(ids) == {s["id"] for s in SPECS}
            assert len(ids) == len(set(ids))
            assert {s["category"] for s in order(seed)[:WARMUP]} == {
                "normalize", "routing", "policy", "billing"}
        for s in SPECS:
            assert not grade(a, s["id"]), f"ticket {s['id']} unexpectedly passes"
            r = subprocess.run([sys.executable, "-m", "unittest",
                                "tests.test_issue_" + s["id"]],
                               cwd=a, capture_output=True, timeout=15)
            assert r.returncode != 0, f"public ticket {s['id']} already passes"
        # Mutating the public test cannot fool the sealed oracle.
        (a/"tests/test_issue_01.py").write_text("import unittest\n")
        assert not grade(a, "01")
    print("PASS: 24 incremental two-file repository tickets, three deterministic "
          "stream seeds, sealed independent grader, no API calls.")


if __name__ == "__main__":
    validate()
