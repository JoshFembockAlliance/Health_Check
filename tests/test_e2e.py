"""Playwright end-to-end tests for the Project Health Check app.

Requires a running server on localhost:8000.
Run with: pytest tests/test_e2e.py --headed (add --headed to see the browser)
"""
import re
import pytest
from playwright.sync_api import Page, expect

BASE = "http://localhost:8000"


# ── Dashboard ──────────────────────────────────────────────────────────────

def test_dashboard_loads(page: Page):
    """Dashboard renders the hero cards and project name."""
    page.goto(BASE)
    expect(page).to_have_title(re.compile(r"Dashboard|Project"))
    # Three hero cards are always present
    expect(page.locator(".hero-card")).to_have_count(3)


def test_dashboard_shows_nav_links(page: Page):
    """All navigation links are present."""
    page.goto(BASE)
    for label in ["Dashboard", "Features", "Capacity", "Risks", "PM Notes", "Settings"]:
        expect(page.locator(f"nav a", has_text=label)).to_be_visible()


def test_dashboard_print_button_exists(page: Page):
    """Print/export button is visible in the title row."""
    page.goto(BASE)
    btn = page.locator("button.print-btn")
    expect(btn).to_be_visible()


# ── Settings ──────────────────────────────────────────────────────────────

def test_settings_page_loads(page: Page):
    """Settings page renders the project form."""
    page.goto(f"{BASE}/settings")
    expect(page.locator("h2", has_text="Settings")).to_be_visible()
    # Project name input exists (scope to the project form to avoid ambiguity)
    expect(page.locator("form[action='/settings/project'] input[name='name']")).to_be_visible()


def test_add_and_delete_role(page: Page):
    """Can add a role via the Settings form and it appears in the table."""
    page.goto(f"{BASE}/settings")

    # The "Add Role" form is inside a <details> element — open it first
    page.locator("details:has(form[action='/settings/roles/add']) summary").click()

    role_form = page.locator("form[action='/settings/roles/add']")
    role_form.locator("input[name='name']").fill("E2E Test Role")
    role_form.locator("input[name='day_rate']").fill("999")
    role_form.locator("button[type='submit']").click()

    # Role appears in the roles table as an editable input
    expect(page.locator("td input[name='name'][value='E2E Test Role']").first).to_be_visible()

    # Delete all E2E Test Role entries (handles leftover state from previous runs)
    while page.locator("td input[name='name'][value='E2E Test Role']").count() > 0:
        page.locator("button[formaction*='/settings/roles/'][formaction*='/delete']").last.click()
        page.locator("#confirm-ok").click()
        page.wait_for_load_state("networkidle")


def test_add_and_delete_overhead(page: Page):
    """Can add an overhead via the Settings form and it appears in the table."""
    page.goto(f"{BASE}/settings")

    # The "Add Overhead" form is inside a <details> element — open it first
    page.locator("details:has(form[action='/settings/overheads/add']) summary").click()

    oh_form = page.locator("form[action='/settings/overheads/add']")
    oh_form.locator("input[name='name']").fill("E2E Test Overhead")
    oh_form.locator("input[name='description']").fill("E2E test description")
    oh_form.locator("input[name='amount']").fill("12345")
    oh_form.locator("button[type='submit']").click()

    # Overhead appears in the overheads table as an editable input
    expect(page.locator("td input[name='name'][value='E2E Test Overhead']").first).to_be_visible()

    # Delete all E2E Test Overhead entries (handles leftover state from previous runs)
    while page.locator("td input[name='name'][value='E2E Test Overhead']").count() > 0:
        page.locator("button[formaction*='/settings/overheads/'][formaction*='/delete']").last.click()
        page.locator("#confirm-ok").click()
        page.wait_for_load_state("networkidle")


# ── Features ──────────────────────────────────────────────────────────────

def test_features_page_loads(page: Page):
    """Features page renders without error."""
    page.goto(f"{BASE}/features")
    expect(page.locator("h2", has_text="Features")).to_be_visible()


def test_add_and_delete_feature(page: Page):
    """Can add a feature and then delete it."""
    page.goto(f"{BASE}/features")

    page.fill("input[name='name']", "E2E Test Feature")
    page.locator("form[action='/features/add'] button[type='submit']").click()

    expect(page.locator("text=E2E Test Feature")).to_be_visible()

    # Delete it via confirm dialog bypass: find and submit the delete form directly
    delete_form = page.locator("form[action*='/features/'][action*='/delete']").last
    delete_form.evaluate("f => f.submit()")

    expect(page.locator("text=E2E Test Feature")).not_to_be_visible()


# ── Risks ──────────────────────────────────────────────────────────────────

def test_risks_page_loads(page: Page):
    """Risks page renders without error."""
    page.goto(f"{BASE}/risks")
    expect(page.locator("h2", has_text="Risks")).to_be_visible()


def test_add_and_delete_risk(page: Page):
    """Can add a risk and then delete it."""
    page.goto(f"{BASE}/risks")

    page.locator("form[action='/risks/add'] input[name='name']").fill("E2E Test Risk")
    page.locator("form[action='/risks/add'] input[name='impact_days']").fill("5")
    page.locator("form[action='/risks/add'] button[type='submit']").click()

    expect(page.locator("h3:has-text('E2E Test Risk')").first).to_be_visible()

    # Delete all E2E Test Risk entries (handles leftover state from previous runs)
    while page.locator("h3:has-text('E2E Test Risk')").count() > 0:
        delete_url = page.locator(
            "article:has(h3:has-text('E2E Test Risk')) button[formaction*='/delete']"
        ).last.get_attribute("formaction")
        with page.expect_navigation():
            page.evaluate(f"""() => {{
                const f = document.createElement('form');
                f.method = 'post';
                f.action = '{delete_url}';
                document.body.appendChild(f);
                f.submit();
            }}""")

    expect(page.locator("text=E2E Test Risk")).not_to_be_visible()


# ── Capacity Planning ──────────────────────────────────────────────────────

def test_capacity_page_loads(page: Page):
    """Capacity Planning page renders without error."""
    page.goto(f"{BASE}/capacity")
    expect(page.locator("h2", has_text="Capacity Planning")).to_be_visible()


def test_add_and_delete_capacity_period(page: Page):
    """Can add a capacity period and delete it."""
    page.goto(f"{BASE}/capacity")

    page.fill("input[name='week_start_date']", "2025-06-02")
    page.fill("input[name='team_size']", "3")
    page.locator("form[action='/capacity/add'] button[type='submit']").click()

    expect(page.locator("text=2025-06-02")).to_be_visible()

    # Delete it
    delete_form = page.locator("form[action*='/capacity/'][action*='/delete']").last
    delete_form.evaluate("f => f.submit()")

    expect(page.locator("text=2025-06-02")).not_to_be_visible()


# ── PM Notes ──────────────────────────────────────────────────────────────

def test_pm_notes_page_loads(page: Page):
    """PM Notes page renders the summary cards and add form."""
    page.goto(f"{BASE}/pm-notes")
    expect(page.locator("h2", has_text="PM Notes")).to_be_visible()
    expect(page.locator(".summary-card", has_text="Sticky")).to_be_visible()


def test_add_and_delete_note(page: Page):
    """Can add a PM note and then delete it."""
    page.goto(f"{BASE}/pm-notes")

    page.fill("input[name='name']", "E2E Test Note")
    page.locator("form[action='/pm-notes/add'] button[type='submit']").click()

    expect(page.locator("text=E2E Test Note")).to_be_visible()

    # Delete it
    delete_form = page.locator("form[action*='/pm-notes/'][action*='/delete']").last
    delete_form.evaluate("f => f.submit()")

    expect(page.locator("text=E2E Test Note")).not_to_be_visible()
