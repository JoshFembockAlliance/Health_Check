"""Playwright end-to-end tests for the Project Health Check app.

Requires a running server on localhost:8000.
Run with: pytest tests/test_e2e.py --headed (add --headed to see the browser)

All project-scoped routes are prefixed with /p/{project_id}/. The seed
project is id=1 ("AGL" in dev, "New Project" in a fresh DB).
"""
import re
import pytest
from playwright.sync_api import Page, expect

BASE = "http://localhost:8000"
P1 = f"{BASE}/p/1"


# ── Cross-project landing (sidebar shell) ─────────────────────────────────

def test_root_lists_projects(page: Page):
    """/ shows the cross-project list and sidebar projects section."""
    page.goto(BASE)
    expect(page).to_have_title(re.compile(r"All Projects|Project"))
    # Sidebar always shows a Projects section
    expect(page.locator(".sidebar .sidebar-section", has_text="Projects")).to_be_visible()


# ── Dashboard ──────────────────────────────────────────────────────────────

def test_dashboard_loads(page: Page):
    """Dashboard renders hero cards and project name in the topbar."""
    page.goto(f"{P1}/")
    expect(page).to_have_title(re.compile(r"Dashboard"))
    assert page.locator(".hero-card").count() >= 1


def test_dashboard_shows_tab_nav(page: Page):
    """All topbar tab links are present on a project page."""
    page.goto(f"{P1}/")
    for label in ["Dashboard", "Features", "Capacity", "Risks", "PM Notes", "Settings"]:
        expect(page.locator(f".top-nav a", has_text=label).first).to_be_visible()


def test_dashboard_print_button_exists(page: Page):
    """PDF export button lives in the topbar and calls window.print."""
    page.goto(f"{P1}/")
    btn = page.locator(".top-actions button", has_text="PDF")
    expect(btn).to_be_visible()


# ── Settings ──────────────────────────────────────────────────────────────

def test_settings_page_loads(page: Page):
    """Settings page renders the project form."""
    page.goto(f"{P1}/settings")
    expect(page.locator(".page-title", has_text="Settings")).to_be_visible()
    expect(page.locator("form[action='/p/1/settings/project'] input[name='name']").first).to_be_visible()


def test_add_and_delete_role(page: Page):
    """Can add a role via the Settings form and it appears in the roles table."""
    page.goto(f"{P1}/settings")
    page.locator("details:has(form[action='/p/1/settings/roles/add']) summary").click()
    role_form = page.locator("form[action='/p/1/settings/roles/add']")
    role_form.locator("input[name='name']").fill("E2E Test Role")
    role_form.locator("input[name='day_rate']").fill("999")
    role_form.locator("button[type='submit']").click()
    expect(page.locator("td input[name='name'][value='E2E Test Role']").first).to_be_visible()
    while page.locator("td input[name='name'][value='E2E Test Role']").count() > 0:
        page.locator("button[formaction*='/p/1/settings/roles/'][formaction*='/delete']").last.click()
        page.locator("#confirm-ok").click()
        page.wait_for_load_state("networkidle")


def test_add_and_delete_overhead(page: Page):
    """Can add an overhead via the Settings form and it appears in the table."""
    page.goto(f"{P1}/settings")
    page.locator("details:has(form[action='/p/1/settings/overheads/add']) summary").click()
    oh_form = page.locator("form[action='/p/1/settings/overheads/add']")
    oh_form.locator("input[name='name']").fill("E2E Test Overhead")
    oh_form.locator("input[name='description']").fill("E2E test description")
    oh_form.locator("input[name='amount']").fill("12345")
    oh_form.locator("button[type='submit']").click()
    expect(page.locator("td input[name='name'][value='E2E Test Overhead']").first).to_be_visible()
    while page.locator("td input[name='name'][value='E2E Test Overhead']").count() > 0:
        page.locator("button[formaction*='/p/1/settings/overheads/'][formaction*='/delete']").last.click()
        page.locator("#confirm-ok").click()
        page.wait_for_load_state("networkidle")


# ── Features ──────────────────────────────────────────────────────────────

def test_features_page_loads(page: Page):
    """Features page renders without error."""
    page.goto(f"{P1}/features")
    expect(page.locator(".page-title", has_text="Features")).to_be_visible()


def test_add_and_delete_feature(page: Page):
    """Can add a feature (via the add-feature dialog) and then delete it."""
    page.goto(f"{P1}/features")
    page.locator(".page-actions button", has_text="Add feature").click()
    dlg = page.locator("#add-feature-dialog")
    expect(dlg).to_be_visible()
    dlg.locator("input[name='name']").fill("E2E Test Feature")
    dlg.locator("button[type='submit']").click()
    expect(page.locator("text=E2E Test Feature").first).to_be_visible()

    delete_form = page.locator("form[action*='/p/1/features/'][action*='/delete']").last
    delete_form.evaluate("f => f.submit()")
    expect(page.locator("text=E2E Test Feature")).not_to_be_visible()


# ── Risks ──────────────────────────────────────────────────────────────────

def test_risks_page_loads(page: Page):
    """Risks page renders without error."""
    page.goto(f"{P1}/risks")
    expect(page.locator(".page-title", has_text="Risks")).to_be_visible()


def test_add_and_delete_risk(page: Page):
    """Can add a risk (opening the add panel) and then delete it."""
    page.goto(f"{P1}/risks")
    page.locator("#toggle-add-risk").click()
    form = page.locator("form[action='/p/1/risks/add']")
    form.locator("input[name='name']").fill("E2E Test Risk")
    form.locator("input[name='impact_days']").fill("5")
    form.locator("button[type='submit']").click()

    expect(page.locator(".risk-card .title", has_text="E2E Test Risk").first).to_be_visible()

    while page.locator(".risk-card .title", has_text="E2E Test Risk").count() > 0:
        card = page.locator(".risk-card", has=page.locator(".title", has_text="E2E Test Risk")).last
        risk_id = card.get_attribute("data-risk-id")
        with page.expect_navigation():
            page.evaluate(f"""() => {{
                const f = document.createElement('form');
                f.method = 'post';
                f.action = '/p/1/risks/{risk_id}/delete';
                document.body.appendChild(f);
                f.submit();
            }}""")
    expect(page.locator(".risk-card .title", has_text="E2E Test Risk")).not_to_be_visible()


def test_risk_modal_opens_with_prefilled_data(page: Page):
    """Clicking a risk card title opens the edit modal with pre-filled fields."""
    page.goto(f"{P1}/risks")
    page.locator("#toggle-add-risk").click()
    form = page.locator("form[action='/p/1/risks/add']")
    form.locator("input[name='name']").fill("E2E Modal Risk")
    form.locator("input[name='impact_days']").fill("3")
    form.locator("button[type='submit']").click()
    expect(page.locator(".risk-card .title", has_text="E2E Modal Risk").first).to_be_visible()

    page.locator(".risk-card .title button", has_text="E2E Modal Risk").first.click()
    modal = page.locator("#risk-edit-modal")
    expect(modal).to_be_visible()
    expect(modal.locator("input[name='name']")).to_have_value("E2E Modal Risk")
    expect(modal.locator("input[name='impact_days']")).to_have_value("3")

    page.evaluate("document.getElementById('risk-edit-modal').close()")

    card = page.locator(".risk-card", has=page.locator(".title", has_text="E2E Modal Risk")).last
    risk_id = card.get_attribute("data-risk-id")
    with page.expect_navigation():
        page.evaluate(f"""() => {{
            const f = document.createElement('form');
            f.method = 'post';
            f.action = '/p/1/risks/{risk_id}/delete';
            document.body.appendChild(f);
            f.submit();
        }}""")


def test_risks_sort_by_impact(page: Page):
    """Sort=impact returns the card grid in high-to-low order."""
    page.goto(f"{P1}/risks?sort=impact")
    grid_or_empty = page.locator(".card-grid, p.muted")
    expect(grid_or_empty.first).to_be_visible()

    cards = page.locator(".risk-card")
    if cards.count() < 2:
        return
    impacts = page.evaluate("""() =>
        Array.from(document.querySelectorAll('.risk-payload')).map(el => {
            try { return JSON.parse(el.textContent).impact_days; } catch { return 0; }
        })
    """)
    for i in range(len(impacts) - 1):
        assert impacts[i] >= impacts[i + 1], f"Cards not sorted by impact: {impacts}"


# ── Capacity Planning ──────────────────────────────────────────────────────

def test_capacity_page_loads(page: Page):
    """Capacity Planning page renders without error."""
    page.goto(f"{P1}/capacity")
    expect(page.locator(".page-title", has_text="Capacity Planning")).to_be_visible()


def test_add_and_delete_capacity_period(page: Page):
    """Can add a capacity period and delete it."""
    page.goto(f"{P1}/capacity")
    page.fill("form[action='/p/1/capacity/add'] input[name='week_start_date']", "2025-06-02")
    page.fill("form[action='/p/1/capacity/add'] input[name='team_size']", "3")
    page.locator("form[action='/p/1/capacity/add'] button[type='submit']").click()

    expect(page.locator("text=2025-06-02").first).to_be_visible()

    delete_form = page.locator("form[action*='/p/1/capacity/'][action*='/delete']").last
    delete_form.evaluate("f => f.submit()")
    expect(page.locator("text=2025-06-02")).not_to_be_visible()


# ── PM Notes ──────────────────────────────────────────────────────────────

def test_pm_notes_page_loads(page: Page):
    """PM Notes page renders the stat cards and page title."""
    page.goto(f"{P1}/pm-notes")
    expect(page.locator(".page-title", has_text="PM Notes")).to_be_visible()
    expect(page.locator(".stat", has_text="Sticky").first).to_be_visible()


def test_add_and_delete_note(page: Page):
    """Can add a PM note and then delete it."""
    page.goto(f"{P1}/pm-notes")
    page.locator("#toggle-add-note").click()
    form = page.locator("form[action='/p/1/pm-notes/add']")
    form.locator("input[name='name']").fill("E2E Test Note")
    form.locator("button[type='submit']").click()

    expect(page.locator(".note-card", has=page.locator("text=E2E Test Note")).first).to_be_visible()

    while page.locator(".note-card", has=page.locator("text=E2E Test Note")).count() > 0:
        card = page.locator(".note-card", has=page.locator("text=E2E Test Note")).last
        delete_form = card.locator("form[action*='/p/1/pm-notes/'][action*='/delete']")
        delete_form.evaluate("f => f.submit()")
        page.wait_for_load_state("networkidle")

    expect(page.locator(".note-card", has=page.locator("text=E2E Test Note"))).not_to_be_visible()


# ── Multi-project sanity ──────────────────────────────────────────────────

def test_create_and_delete_project(page: Page):
    """Can create a new project via the sidebar dialog, and delete it via Settings."""
    page.goto(BASE)
    page.locator("#new-project-link").click()
    dlg = page.locator("#new-project-dialog")
    expect(dlg).to_be_visible()
    dlg.locator("input[name='name']").fill("E2E Project")
    dlg.locator("button[type='submit']").click()

    # Wait until we land on the new project's settings page.
    expect(page).to_have_url(re.compile(r"/p/\d+/settings"))
    new_pid = page.url.split("/p/")[1].split("/")[0]

    # Sidebar shows the new project
    expect(page.locator(f".sidebar-item[href='/p/{new_pid}/']")).to_be_visible()

    # Delete it via the Danger zone button (triggers confirm dialog)
    page.locator(f"form[action='/projects/{new_pid}/delete'] button").click()
    page.locator("#confirm-ok").click()
    page.wait_for_load_state("networkidle")

    # Back on the cross-project page, the project should be gone from the sidebar
    expect(page.locator(f".sidebar-item[href='/p/{new_pid}/']")).not_to_be_visible()
