#!/usr/bin/env python3
"""Fast, offline navigation and truth-boundary gate for the canonical Full Demo docs.

Run from any working directory. It checks local links, the four-case catalog,
the existence of current source/test paths and the explicit release boundary.
It cannot claim that a runtime case was executed; CI owns that separately.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    Path("README.md"),
    Path("README_LEGACY.md"),
    Path("docs/README.md"),
    Path("docs/DEMO_CATALOG.md"),
    Path("docs/TEST_MATRIX.md"),
    Path("docs/DEMO_EXPERIENCE_INDEX.md"),
]
CHECK_LINKS = [p for p in PAGES if p != Path("README_LEGACY.md")]
DESTINATIONS = [
    "cases/people-analytics-copilot/README.md",
    "cases/claude-postgres-incident/README.md",
    "integrations/n8n/shopify-support/README.md",
    "integrations/n8n/quarterly-compliance-workflow.json",
    "scripts/test-acme-one-fleet.py",
    "scripts/acme-fleet-provider.py",
    ".github/workflows/acme-governed-main-acceptance.yml",
    "docs/DEMO_CATALOG.md",
    "docs/TEST_MATRIX.md",
]
for item in PAGES + list(map(Path, DESTINATIONS)):
    assert (ROOT / item).exists(), f"missing canonical source or navigation: {item}"

links = 0
for page in CHECK_LINKS:
    text = (ROOT / page).read_text()
    for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text):
        address = target.split("#", 1)[0].split("?", 1)[0].strip()
        if not address or "://" in address or address.startswith(("mailto:", "data:")):
            continue
        resolved = (ROOT / page.parent / address).resolve()
        assert resolved.is_relative_to(ROOT.resolve()), (
            f"local link escapes repository: {page}: {target}"
        )
        assert resolved.exists(), f"broken local link: {page}: {target}"
        links += 1

readme = (ROOT / "README.md").read_text()
catalog = (ROOT / "docs/DEMO_CATALOG.md").read_text()
matrix = (ROOT / "docs/TEST_MATRIX.md").read_text()
assert len(readme) < 11000, "root README should stay a concise landing page"
for name in ("Customer Support", "People Analytics", "OrderDesk", "Document Processing"):
    assert name in readme and name in catalog, f"missing first-class ACME use case: {name}"
for marker in ("one company", "source-built", "NOT RUN", "41 signed records",
               "OpenShell", "v1.17.0", "one-installation", "native Console"):
    assert marker.lower() in (readme + catalog + matrix).lower(), f"missing trust boundary: {marker}"
assert "v1.17.0-rc.2" in matrix
assert "2.30.4" in catalog and "2.48.5" in catalog
assert "read-only" in catalog and "not a fifth" in readme
assert "README_LEGACY.md" in readme and "README_LEGACY.md" in catalog

print(f"PASS canonical Full Demo: {len(CHECK_LINKS)} live docs, "
      f"{links} local links, 4 first-class cases and explicit NOT RUN boundaries")
print("This is a documentation/source contract; actual Talon and business-effect "
      "acceptance is in the independently executed CI/runtime workflows.")
