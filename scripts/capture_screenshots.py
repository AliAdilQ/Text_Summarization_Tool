"""Capture real pages and check critical UI flows against a seeded local server.

Run after python seed.py and python run.py. Requires the optional Playwright
dependency and a Chromium installation; never needed for normal application use.
"""

import argparse
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def capture(base_url, executable_path=None):
    output = ROOT / "docs" / "screenshots"
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        options = {"headless": True}
        if executable_path:
            options["executable_path"] = executable_path
        browser = playwright.chromium.launch(**options)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
            color_scheme="light",
            reduced_motion="reduce",
        )
        context.grant_permissions(["clipboard-read", "clipboard-write"])
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on(
            "response",
            lambda response: (
                errors.append(f"HTTP {response.status}: {response.url}")
                if response.status >= 500 or (response.status >= 400 and "/static/" in response.url)
                else None
            ),
        )

        def visit(path):
            response = page.goto(base_url.rstrip("/") + path)
            assert response and response.status == 200, f"Could not open {path}"
            page.evaluate("document.fonts.ready")

        def screenshot(name, full_page=False):
            page.locator(".flash-message").evaluate_all(
                "elements => elements.forEach(element => element.remove())"
            )
            page.screenshot(path=str(output / name), full_page=full_page, animations="disabled")
            print(f"Captured {name}")

        def sign_in(identifier, password):
            visit("/login")
            page.locator("#identifier").fill(identifier)
            page.locator("#password").fill(password)
            page.get_by_role("button", name="Sign in", exact=True).click()
            expect(page).not_to_have_url(base_url.rstrip("/") + "/login")

        def sign_out():
            page.get_by_role("button", name="Sign out", exact=True).click()
            expect(page).to_have_url(base_url.rstrip("/") + "/")

        visit("/")
        screenshot("home.png", full_page=True)
        visit("/summarizer")
        screenshot("summarizer.png", full_page=True)
        page.get_by_role("button", name="Generate summary").click()
        expect(page.locator("#summary-error")).to_be_visible()
        page.get_by_role("button", name="Try an example").click()
        expect(page.locator("#word-count")).not_to_have_text("0")
        page.get_by_role("button", name="Generate summary").click()
        expect(page.locator("#result-content")).to_be_visible(timeout=120_000)
        screenshot("summary-result.png", full_page=True)
        page.get_by_role("button", name="Copy", exact=True).click()
        expect(page.locator("#app-toast")).to_contain_text("copied")
        with page.expect_download() as downloaded:
            page.get_by_role("button", name="Download", exact=True).click()
        assert downloaded.value.suggested_filename.endswith(".txt")
        visit("/login")
        screenshot("login.png")
        sign_in("demo", "Demo123!")
        screenshot("user-dashboard.png", full_page=True)
        visit("/workspace/history")
        screenshot("user-history.png")
        page.locator("a.table-title").first.click()
        expect(page.locator("#saved-summary")).to_be_visible()
        # A normal member must receive an actual forbidden response.
        response = page.goto(base_url.rstrip("/") + "/admin")
        assert response.status == 403
        sign_out()
        sign_in("admin", "Admin123!")
        expect(page.locator("#activity-chart")).to_be_visible()
        page.wait_for_function("window.Chart && Chart.getChart('activity-chart')")
        screenshot("admin-dashboard.png", full_page=True)
        visit("/admin/users")
        screenshot("admin-users.png")
        page.locator("input[name=q]").fill("demo")
        page.get_by_role("button", name="Search", exact=False).click()
        expect(page.locator("tbody tr")).to_have_count(1)
        visit("/admin/summaries")
        screenshot("admin-summaries.png")
        page.locator("select[name=length]").select_option("short")
        page.get_by_role("button", name="Filter", exact=False).click()
        expect(page.locator("tbody .badge-length").first).to_have_text("Short")
        visit("/admin")
        page.locator(".theme-toggle").click()
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        page.reload()
        expect(page.locator("html")).to_have_attribute("data-theme", "dark")
        page.wait_for_function("window.Chart && Chart.getChart('activity-chart')")
        screenshot("dark-mode.png", full_page=True)
        page.locator(".theme-toggle").click()
        # Check registration in the browser, then remove that test account through
        # the same admin workflow a real administrator uses.
        sign_out()
        visit("/register")
        page.locator("#username").fill("screenshot_reader")
        page.locator("#email").fill("screenshot_reader@example.com")
        page.locator("#password").fill("BrowserCheck123!")
        page.locator("#confirm_password").fill("BrowserCheck123!")
        page.get_by_role("button", name="Create account").click()
        expect(page).to_have_url(base_url.rstrip("/") + "/workspace")
        sign_out()
        sign_in("admin", "Admin123!")
        visit("/admin/users?q=screenshot_reader")
        page.get_by_role("link", name="Manage", exact=False).click()
        page.get_by_role("button", name="Delete account").click()
        expect(page.locator("#confirm-dialog")).to_be_visible()
        page.get_by_role("button", name="Confirm", exact=True).click()
        expect(page).to_have_url(base_url.rstrip("/") + "/admin/users")
        sign_out()
        # Every visible internal anchor should resolve, including error pages.
        for path in ("/", "/about", "/summarizer"):
            visit(path)
            links = page.locator('a[href^="/"]').evaluate_all(
                "links => [...new Set(links.map(link => link.getAttribute('href')))]"
            )
            for link in links:
                response = context.request.get(base_url.rstrip("/") + link)
                assert response.status < 400, f"Broken navigation: {link}"
        # Verify responsive layouts do not overflow horizontally.
        page.set_viewport_size({"width": 390, "height": 844})
        for path in ("/", "/summarizer", "/login", "/register", "/about"):
            visit(path)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
                f"Mobile overflow: {path}"
            )
        visit("/summarizer")
        screenshot("mobile-summarizer.png", full_page=True)
        sign_in("demo", "Demo123!")
        for path in ("/workspace", "/workspace/history", "/workspace/profile"):
            visit(path)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
                f"Mobile overflow: {path}"
            )
        sign_out()
        sign_in("admin", "Admin123!")
        for path in ("/admin", "/admin/users", "/admin/summaries"):
            visit(path)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (
                f"Mobile overflow: {path}"
            )
        context.close()
        browser.close()
    if errors:
        raise RuntimeError("Browser errors:\n" + "\n".join(errors))
    print(
        "Browser checks passed: authentication, generation, copy/download, admin protection, filters, account deletion, theme persistence, navigation, and mobile layouts."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument(
        "--browser-executable", help="Optional path to an existing Chromium executable"
    )
    args = parser.parse_args()
    try:
        capture(args.base_url, args.browser_executable)
    except Exception as error:
        print(f"Screenshot verification failed: {error}", file=sys.stderr)
        raise
