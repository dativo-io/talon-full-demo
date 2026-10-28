#!/usr/bin/env python3
"""Single-browser real Chromium acceptance: actual Docker/Talon, fake-model-free GUIDED mode."""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parent.parent
APP="http://127.0.0.1:8501"

def main():
    with sync_playwright() as p:
        import os
        browser=p.chromium.launch(headless=True,channel=os.environ.get("HR_BROWSER_CHANNEL") or None,args=["--no-sandbox"])
        try:
            page=browser.new_page(viewport={"width":1365,"height":950})
            page.set_default_timeout(20000)
            try:
                page.goto(APP,wait_until="domcontentloaded")
                expect(page.get_by_role("heading",name="Workforce Intelligence")).to_be_visible()
                expect(page.locator("#mode")).to_contain_text("GUIDED")
                expect(page.locator("#charts")).to_have_attribute("src","/charts")
                page.locator("#department").select_option("Sales")
                expect(page.locator("#charts")).to_have_attribute("src","/charts?department=Sales")
                page.get_by_role("button",name="Run SQL through Talon").click()
                expect(page.locator("#sqlResult")).to_contain_text("EXECUTED",timeout=30000)
                expect(page.locator("#sqlResult")).to_contain_text("minimum_cohort_size")
                expect(page.locator("#receipt")).to_contain_text("Decision: allow")
                # Reproduce the exact class of department filter tried in the UI.
                page.get_by_role("button",name="Customer departments").click()
                expect(page.locator("#sql")).to_have_value(re.compile(r"department LIKE '%Customer%'"))
                page.get_by_role("button",name="Run SQL through Talon").click()
                expect(page.locator("#sqlResult")).to_contain_text("EXECUTED",timeout=30000)
                expect(page.locator("#sqlResult")).to_contain_text("active_department_like")
                expect(page.locator("#receipt")).to_contain_text("Decision: allow")
                sql=page.locator("#sql")
                sql.fill("SELECT employee_id, full_name, monthly_salary_mxn FROM employees")
                page.get_by_role("button",name="Run SQL through Talon").click()
                expect(page.locator("#sqlResult")).to_contain_text("REJECTED · HR SQL validator",timeout=30000)
                expect(page.locator("#receipt")).to_contain_text("Decision: allow")
                page.get_by_role("button",name="Ask assistant").click()
                expect(page.locator("#answer")).to_contain_text("Guided deterministic analysis",timeout=30000)
                page.get_by_role("button",name="Request individual employee records").click()
                expect(page.locator("#probe")).to_contain_text("BLOCKED · Talon denied hr_employee_export",timeout=30000)
                expect(page.locator("#receipt")).to_contain_text("Decision: deny")
                expect(page.locator("#receipt")).to_contain_text("Committed: true")
                expect(page.locator("#allowedTools")).to_contain_text("hr_attrition_summary")
                expect(page.locator("#allowedTools")).not_to_contain_text("hr_employee_export")
                expect(page.locator("#activity")).to_contain_text("hr_employee_export · deny · not dispatched")
                expect(page.locator("#activity")).to_contain_text("hr_aggregate_sql · allow · HR rejected SQL")
                expect(page.locator("#sessionCommands")).to_contain_text("talon costs --session")
                expect(page.locator("#sessionCommands")).to_contain_text("talon audit list --session")
                assert re.search(r"hr-demo-[a-z0-9]+",page.locator("#sessionLabel").inner_text())
            except Exception:
                dest=ROOT/"cases/people-analytics-copilot/.state/browser-failure.png"
                dest.parent.mkdir(parents=True,exist_ok=True)
                try: page.screenshot(path=str(dest),full_page=True)
                except Exception: pass
                raise
        finally: browser.close()
    print("PASS: one dashboard; permitted SQL, HR rejection, AI MCP, Talon export denial; actual receipts")

if __name__=="__main__": main()
