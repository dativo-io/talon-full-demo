#!/usr/bin/env python3
"""Capture real People Analytics and Talon Console screenshots on disposable CI.

Only captures actual, passing UI state. Never renders mock data or pairing codes.
"""
import re
import subprocess
import time
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cases/people-analytics-copilot/.state/japan-screenshots"
OUT.mkdir(parents=True, exist_ok=True)
WORKFORCE = "http://127.0.0.1:8501"
CONSOLE = "http://127.0.0.1:8787"
COMPOSE = ["docker", "compose", "-f", "cases/people-analytics-copilot/compose.isolated.yaml"]
PAIR = re.compile(r"Talon console pairing code: ([A-Z2-9]{5}(?:-[A-Z2-9]{5}){3})")

def run(args):
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout

with sync_playwright() as p:
    import os
    browser = p.chromium.launch(headless=True, channel=os.environ.get("HR_BROWSER_CHANNEL") or None, args=["--no-sandbox"])
    try:
        page = browser.new_page(viewport={"width": 1550, "height": 1050}, device_scale_factor=1)
        page.set_default_timeout(30000)
        page.goto(WORKFORCE, wait_until="domcontentloaded")
        expect(page.get_by_role("heading", name="Workforce Intelligence")).to_be_visible()
        expect(page.locator("#mode")).to_contain_text("GUIDED")
        page.screenshot(path=str(OUT / "01-workforce-real-ui.png"), full_page=True)
        print("PASS: genuine Workforce application initial screen")

        page.get_by_role("button", name="Run SQL through Talon").click()
        expect(page.locator("#sqlResult")).to_contain_text("EXECUTED")
        expect(page.locator("#receipt")).to_contain_text("Decision: allow")
        page.screenshot(path=str(OUT / "02-workforce-talon-allow.png"), full_page=True)
        print("PASS: genuine Talon-allowed aggregate")

        page.get_by_role("button", name="Request individual employee records").click()
        expect(page.locator("#probe")).to_contain_text("BLOCKED · Talon denied hr_employee_export")
        expect(page.locator("#receipt")).to_contain_text("Decision: deny")
        expect(page.locator("#activity")).to_contain_text("hr_employee_export · deny · not dispatched")
        page.screenshot(path=str(OUT / "03-workforce-talon-deny.png"), full_page=True)
        print("PASS: genuine Talon-denied employee export")

        # Restart ONLY read-only Console (not HR/Talon) to issue a fresh private pairing code.
        run(COMPOSE + ["--profile", "operator", "up", "--no-deps", "-d", "--force-recreate", "talon-ui"])
        token = None
        for _ in range(70):
            try:
                log = run(COMPOSE + ["--profile", "operator", "logs", "--no-color", "talon-ui"])
                codes = PAIR.findall(log)
                if codes and page.request.get(CONSOLE + "/healthz", timeout=1500).status == 200:
                    token = codes[-1]
                    break
            except Exception:
                pass
            time.sleep(1)
        assert token, "Could not obtain private single-use Console pairing code"
        c = browser.new_page(viewport={"width": 1550, "height": 1050}, device_scale_factor=1)
        c.set_default_timeout(30000)
        c.goto(CONSOLE + "/overview", wait_until="domcontentloaded")
        expect(c.locator("#code")).to_be_visible()
        c.locator("#code").fill(token)
        c.locator("#pair-form button[type=submit]").click()
        expect(c.get_by_role("heading", name="Overview", level=1)).to_be_visible()
        assert token not in c.url and token not in c.content()
        c.screenshot(path=str(OUT / "04-talon-console-overview.png"), full_page=True)
        print("PASS: genuine paired native Talon Console Overview")

        for slug, label, name in [
            ("use-cases", "AI Use Cases", "05-talon-console-use-cases.png"),
            ("sessions", "Sessions", "06-talon-console-sessions.png"),
            ("system", "System", "07-talon-console-system.png"),
        ]:
            c.goto(CONSOLE + "/" + slug, wait_until="domcontentloaded")
            expect(c.get_by_role("heading", name=label, level=1)).to_be_visible()
            c.screenshot(path=str(OUT / name), full_page=True)
            print("PASS: genuine native Console " + label)
        assert "hr-analytics-assistant" in c.request.get(CONSOLE + "/console/v1/use-cases").text()
        assert "hr_employee_export" in c.request.get(CONSOLE + "/console/v1/use-cases/hr-analytics-assistant/effective-policy").text()
        print("PASS: Console reports actual HR use case and forbidden export")
    finally:
        browser.close()
(OUT / "README.txt").write_text(
    "Genuine browser screenshots from the current source-pinned People Analytics case,\n"
    "not external OpenAI inference. The Workforce app runs GUIDED deterministic text;\n"
    "the Talon governed MCP decisions, HR DuckDB backend and native Console are real.\n"
    "Source: dativo-io/talon-full-demo/cases/people-analytics-copilot.\n"
    "Screenshots use fictional employee data; do not represent real HR data.\n"
)
print("PASS: People Analytics presenter screenshots captured from real browser state")
