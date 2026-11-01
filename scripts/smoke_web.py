"""Drives a Demo Run through the built web app in the installed Edge. Not collected by pytest.

    uv run --with playwright python scripts/smoke_web.py
"""
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import expect, sync_playwright

PORT = 8765
URL = f"http://127.0.0.1:{PORT}"
WAIT = 90_000  # demo pacing, not a performance target


def wait_for_server() -> None:
    for _ in range(60):
        try:
            urllib.request.urlopen(f"{URL}/api/meta", timeout=1)
            return
        except OSError:
            time.sleep(0.5)
    sys.exit("scout serve did not come up")


def main() -> None:
    server = subprocess.Popen(["uv", "run", "scout", "serve", "--demo", "--port", str(PORT)])
    try:
        wait_for_server()
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="msedge")
            page = browser.new_page()
            problems: list[str] = []
            page.on("console", lambda m: m.type == "error" and "422" not in m.text and problems.append(m.text))  # 422 is the refused edit
            page.on("pageerror", lambda e: problems.append(str(e)))
            expect.set_options(timeout=WAIT)

            # "fail" makes the demo stop once, so Resume has something to resume.
            page.goto(URL)
            page.get_by_placeholder("e.g. Senior data engineer").fill("Data engineer in Austin fail")
            page.get_by_role("button", name="Start", exact=True).click()

            page.get_by_role("button", name="Continue without answering", exact=True).click()

            page.get_by_role("button", name="Edit", exact=True).click()
            page.get_by_label("Target Postings").fill("5")
            page.get_by_role("button", name="Use this plan", exact=True).click()
            expect(page.locator('[aria-invalid="true"]')).to_be_visible()  # the server refused it
            page.get_by_role("button", name="Cancel", exact=True).click()
            page.get_by_role("button", name="Approve", exact=True).click()

            # A reload mid-Run rebuilds the page from the log and carries on.
            page.reload()
            page.get_by_role("button", name="Search wider", exact=True).click()

            page.get_by_role("button", name="Resume", exact=True).click()
            expect(page.locator("article.brief")).to_be_visible()
            expect(page.get_by_text("How this Run went")).to_be_visible()

            assert not problems, problems
            browser.close()
        print("smoke ok")
    finally:
        # /T: `uv run` spawns the real server as a child, which terminate() would leave listening.
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(server.pid)], capture_output=True)


if __name__ == "__main__":
    main()
