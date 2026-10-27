#!/usr/bin/env python3
"""REAL browser acceptance against live isolated Docker services + released Talon.

Requires: pip install playwright && python -m playwright install chromium
This is distinct from the offline HTTP/unit tests: a Chromium user clicks
through both applications, invokes actual Docker/Talon commands via the
authenticated operator console, and checks receipts and backend effects.

Only fictional HR data. No billable provider and no simulated PASS responses.
"""
from __future__ import annotations

import importlib.util
import json
import secrets
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parent.parent
CONSOLE = ROOT / "scripts" / "people_analytics_presenter.py"
SPEC = importlib.util.spec_from_file_location("people_analytics_presenter", CONSOLE)
presenter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(presenter)

APP = "http://127.0.0.1:8501"
CONSOLE_URL = "http://127.0.0.1:8502"


def check_http_isolation(operator_token: str):
    # The operator API is not publicly executable; browser auth is mandatory.
    req = Request(CONSOLE_URL + "/api/actions")
    try:
        urlopen(req, timeout=4)
    except HTTPError as e:
        assert e.code == 401, e.code
    else:
        raise AssertionError("Unauthenticated console action catalog exposed")
    req = Request(CONSOLE_URL + "/api/run", data=b'{"action":"before"}',
                  headers={"Content-Type": "application/json", "Origin": "https://attacker.invalid",
                           "X-Presenter-Token": operator_token})
    try:
        urlopen(req, timeout=4)
    except HTTPError as e:
        assert e.code == 403, e.code
    else:
        raise AssertionError("Cross-origin privileged action accepted")


def exercise_business_ui(page):
    page.goto(APP + "/", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Workforce Intelligence")).to_be_visible()
    expect(page.locator("#mode")).to_have_text("GUIDED · NO LLM", timeout=15000)
    expect(page.locator("#charts")).to_have_attribute("src", "/charts")
    iframe = page.frame_locator("#charts")
    expect(iframe.locator("body")).to_contain_text("workforce", ignore_case=True, timeout=15000)

    # Filter changes the actual backend query and embedded charts, not just a UI label.
    departments = page.locator("#department")
    expect(departments.locator("option")).not_to_have_count(1)
    departments.select_option("Sales")
    expect(page.locator("#charts")).to_have_attribute("src", "/charts?department=Sales")
    expect(iframe.locator("body")).to_contain_text("Sales", timeout=15000)

    # Guided answers still execute real authorized Talon MCP calls.
    page.get_by_role("button", name="Ask assistant").click()
    expect(page.locator("#answer")).to_contain_text("Latest monthly attrition", timeout=30000)
    expect(page.locator("#answer")).to_contain_text("NOT a model-generated answer")
    expect(page.locator("#receipt")).to_contain_text("Decision: allow")
    expect(page.locator("#receipt")).to_contain_text("Committed: true")
    expect(page.locator("#tools")).not_to_contain_text("hr_employee_export")
    expect(page.locator("#counters")).to_contain_text("authenticated operator proof console")

    # This is an explicit operator probe, NOT a model-selected forbidden action.
    page.get_by_role("button", name="Force a forbidden export through Talon").click()
    expect(page.locator("#probe")).to_have_text("DENIED — not dispatched", timeout=30000)
    expect(page.locator("#receipt")).to_contain_text("Decision: deny")
    expect(page.locator("#receipt")).to_contain_text("Committed: true")
    print("PASS: real Chromium dashboard, filter, guided Talon aggregate and forbidden-tool receipt")


def exercise_operator_console(page, token: str):
    page.goto(CONSOLE_URL + "/", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="People Analytics · Operator Proof Console")).to_be_visible()
    expect(page.get_by_text("No runtime switch:", exact=False)).to_be_visible()
    expect(page.locator("#overview")).to_be_hidden()
    page.get_by_label("Operator token").fill(token)
    page.get_by_role("button", name="Unlock", exact=True).click()
    expect(page.get_by_text("Unlocked. Commands run only when you select Run.")).to_be_visible()
    actions = presenter.ACTIONS
    cards = page.locator("article.action")
    expect(cards).to_have_count(len(actions))

    for index, (action, phase, title, _command) in enumerate(actions):
        card = cards.nth(index)
        expect(card.get_by_role("heading", name=title)).to_be_visible()
        if action in ("before", "reset"):
            page.once("dialog", lambda dialog: dialog.accept())
        card.get_by_role("button", name="Run check").click()
        expect(card.get_by_role("status")).to_have_text("Exit 0 · command succeeded", timeout=65000)
        output = card.locator("pre").last.inner_text()
        assert "Exit code: 0" in output, (action, output[:500])
        if action == "before":
            assert "Synthetic employee example" in output
        elif action == "reset":
            assert "explicitly reset to zero" in output
        elif action == "discover":
            assert "hr_attrition_summary" in output and "Employee-level export is absent" in output
        elif action == "allow":
            assert '"decision": "allow"' in output
        elif action == "deny":
            assert '"decision": "deny"' in output and "not_dispatched" in output
        elif action == "backend_counts":
            assert "zero employee exports" in output
        elif action == "evidence_verify":
            assert "Invalid records: 0" in output and "Missing signature: 0" in output
        print(f"PASS: browser operator step {index+1}/{len(actions)} {action}")

    expect(page.locator("#progressText")).to_contain_text(
        f"{len(actions)} / {len(actions)} checks succeeded")
    print("PASS: authenticated browser executed all real operator/CLI actions with signed evidence")


def main():
    token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(("127.0.0.1", 8502), presenter.handler_factory(token))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        check_http_isolation(token)
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            try:
                context = browser.new_context(viewport={"width": 1365, "height": 950},
                                              locale="en-US", accept_downloads=False)
                page = context.new_page()
                page.set_default_timeout(15000)
                exercise_business_ui(page)
                exercise_operator_console(page, token)
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
    print("PASS: isolated People Analytics end-to-end browser journey, real Talon, no real provider")


if __name__ == "__main__":
    main()
