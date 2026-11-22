#!/usr/bin/env python3
"""Paired native Talon Operations Console browser over the REAL HR Compose state.

This is NOT the Workforce UI browser smoke (port 8501). It starts the actual
read-only talon-ui process from the same source-built Talon executable and data
directory as the running governed /mcp instance; no paid model or fixture
Console API is substituted. The pairing code is read from the container log
in-process only, never printed into the CI output.
"""
import re
import subprocess
import time
from playwright.sync_api import expect, sync_playwright

CONSOLE = "http://127.0.0.1:8787"
COMPOSE = ["docker", "compose", "-f", "cases/people-analytics-copilot/compose.isolated.yaml"]
CODE = re.compile(r"Talon console pairing code: ([A-Z2-9]{5}(?:-[A-Z2-9]{5}){3})")

def code_from_log():
    logs = subprocess.run(COMPOSE + ["--profile", "operator", "logs", "--no-color", "talon-ui"],
                          capture_output=True, text=True, check=True).stdout
    matches = CODE.findall(logs)
    return matches[-1] if matches else None

def main():
    subprocess.run(COMPOSE + ["--profile", "operator", "up", "--no-deps", "-d", "talon-ui"],
                   check=True)
    with sync_playwright() as p:
        import os
        browser = p.chromium.launch(headless=True, channel=os.environ.get("HR_BROWSER_CHANNEL") or None,
                                    args=["--no-sandbox"])
        try:
            page = browser.new_page(viewport={"width": 1365, "height": 950})
            page.set_default_timeout(20000)
            deadline = time.monotonic() + 60
            token = None
            while time.monotonic() < deadline:
                try:
                    status = page.request.get(CONSOLE + "/healthz", timeout=2000).status
                    token = code_from_log()
                    if status == 200 and token:
                        break
                except Exception:
                    pass
                time.sleep(1)
            assert token, "Native Console did not start and issue a one-time pairing code"
            # The console is read-only and unpaired users cannot see the HR store.
            assert page.request.get(CONSOLE + "/console/v1/system").status == 401
            page.goto(CONSOLE + "/overview", wait_until="domcontentloaded")
            expect(page.locator("#code")).to_be_visible()
            page.locator("#code").fill(token)
            page.locator("#pair-form button[type=submit]").click()
            expect(page.get_by_role("heading", name="Overview", level=1)).to_be_visible()
            cookies = page.context.cookies()
            assert len(cookies) == 1 and cookies[0]["name"] == "talon_console_session"
            assert cookies[0]["httpOnly"] and cookies[0]["sameSite"] == "Strict"
            assert token not in page.url and token not in page.content()
            # Only a real signed HR run makes the actual use case and sessions
            # visible; prove the API is reading them, not simply that a page loads.
            for route in ("overview", "use-cases", "use-cases/hr-analytics-assistant",
                          "use-cases/hr-analytics-assistant/effective-policy",
                          "approvals", "sessions", "costs", "configuration", "system"):
                response = page.request.get(CONSOLE + "/console/v1/" + route)
                assert response.status == 200, f"Console API {route}: {response.status}"
            use_cases = page.request.get(CONSOLE + "/console/v1/use-cases").text()
            assert "hr-analytics-assistant" in use_cases, "HR use case not visible in native Console"
            sessions = page.request.get(CONSOLE + "/console/v1/sessions").text()
            assert "hr-demo-" in sessions, "Real HR session not visible in Console"
            effective = page.request.get(CONSOLE + "/console/v1/use-cases/hr-analytics-assistant/effective-policy").text()
            assert "hr_employee_export" in effective, "Forbidden HR action missing from Console effective policy"
            for path, heading in (
                ("use-cases", "AI Use Cases"), ("approvals", "Approvals"),
                ("sessions", "Sessions"), ("costs", "Costs"),
                ("configuration", "Configuration"), ("system", "System"),
            ):
                page.goto(CONSOLE + "/" + path)
                expect(page.get_by_role("heading", name=heading, level=1)).to_be_visible()
            assert page.request.post(CONSOLE + "/console/v1/overview", data={}).status == 405
            assert page.request.get(CONSOLE + "/v1/secrets").status == 404
            # No native Console approval buttons: the console is not an approver.
            page.goto(CONSOLE + "/approvals")
            assert page.get_by_role("button", name=re.compile(r"^(approve|reject)$", re.I)).count() == 0
            assert page.request.get(CONSOLE + "/console/v1/system").status == 200
            print("PASS: real HR Compose installation; native paired seven-area Console, "
                  "MCP use-case policy, real sessions, no admin/write route or approval buttons")
        finally:
            browser.close()

if __name__ == "__main__":
    main()
