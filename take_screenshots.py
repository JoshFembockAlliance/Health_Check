#!/usr/bin/env python3
"""One-shot script: seed demo DB, start server, capture README screenshots, clean up."""

import os
import sys
import subprocess
import time
import sqlite_utils
from datetime import date, timedelta
from playwright.sync_api import sync_playwright

DB_PATH = os.path.join(os.path.dirname(__file__), "health_check.db")
OUT_DIR = os.path.join(os.path.dirname(__file__), "readme_screenshots")
PORT = 8765
BASE = f"http://localhost:{PORT}"
P1 = f"{BASE}/p/1"

# ── Demo data ────────────────────────────────────────────────────────────────

def seed():
    from database import init_db, get_db
    init_db()
    db = get_db()

    # Overwrite the blank seed project with realistic demo values
    today = date(2026, 4, 21)
    db["projects"].update(1, {
        "name": "Acme Platform Refresh",
        "description": "Full-stack rebuild of the Acme customer portal and billing system.",
        "start_date": "2025-10-01",
        "as_of_date": today.isoformat(),
        "initial_budget": 500000.0,
        "actual_spend": 82000.0,
        "health_on_track_pct": 100.0,
        "health_at_risk_pct": 80.0,
        "accent": "cyan",
        "theme": "light",
    })

    # Roles
    db["roles"].delete_where("project_id = 1")
    r_dev = db["roles"].insert({"project_id": 1, "name": "Senior Developer", "day_rate": 1600.0}).last_pk
    r_des = db["roles"].insert({"project_id": 1, "name": "UI Designer",       "day_rate": 1200.0}).last_pk
    r_qa  = db["roles"].insert({"project_id": 1, "name": "QA Engineer",       "day_rate": 1100.0}).last_pk
    db["projects"].update(1, {"default_role_id": r_dev})

    # Budget adjustment
    db["budget_adjustments"].delete_where("project_id = 1")
    db["budget_adjustments"].insert({"project_id": 1, "amount": 25000.0, "date": "2026-01-15",
                                      "description": "Phase 2 scope addition approved by steering committee"})

    # Overheads
    db["overheads"].delete_where("project_id = 1")
    db["overheads"].insert({"project_id": 1, "name": "Infrastructure & Hosting", "description": "AWS services", "amount": 18000.0, "sort_order": 1})
    db["overheads"].insert({"project_id": 1, "name": "QA Tooling",              "description": "Playwright + CI licences", "amount": 4500.0, "sort_order": 2})

    # Features + requirements + deliverables
    feats = [
        (1, "User Authentication & SSO",    1,  1),
        (2, "Dashboard & Reporting",         2,  1),
        (3, "Billing & Subscriptions",       3,  1),
        (4, "Mobile Experience",             4,  0),
        (5, "Admin Portal",                  5,  0),
    ]
    db["features"].delete_where("project_id = 1")

    for fid, fname, sort, started in feats:
        db["features"].insert({"id": fid, "project_id": 1, "name": fname, "sort_order": sort, "started": started})

    # Requirements & deliverables
    req_id = 1
    del_id = 1

    def add_req(fid, name, deliverables):
        nonlocal req_id, del_id
        db["requirements"].insert({"id": req_id, "feature_id": fid, "name": name, "sort_order": req_id})
        cur_req = req_id
        req_id += 1
        for dname, days, pct, priority, role in deliverables:
            db["deliverables"].insert({
                "id": del_id, "requirement_id": cur_req, "name": dname,
                "budget_days": days, "percent_complete": pct,
                "priority": priority, "role_id": role, "sort_order": del_id,
            })
            del_id += 1

    # Feature 1: User Authentication (100% done)
    add_req(1, "OAuth 2.0 / SSO Integration", [
        ("Research identity provider options",  2,  100, "must",   r_dev),
        ("Implement Auth0 integration",         8,  100, "must",   r_dev),
        ("SSO token refresh & session mgmt",    4,  100, "must",   r_dev),
        ("Design login / logout screens",       2,  100, "should", r_des),
    ])
    add_req(1, "Role-based Access Control", [
        ("Define permission matrix",            1,  100, "must",   r_dev),
        ("Backend middleware enforcement",      3,  100, "must",   r_dev),
        ("Frontend route guards",               2,  100, "must",   r_dev),
        ("RBAC smoke test suite",               2,  100, "must",   r_qa),
    ])

    # Feature 2: Dashboard & Reporting (72% done)
    add_req(2, "Live Metrics Cards", [
        ("Identify KPI data sources",           1,  100, "must",   r_dev),
        ("Build data aggregation API",          6,  100, "must",   r_dev),
        ("Card component library",              3,  100, "should", r_des),
        ("Real-time websocket feed",            5,   60, "should", r_dev),
    ])
    add_req(2, "Exportable PDF Reports", [
        ("Report template design",              2,   80, "should", r_des),
        ("PDF generation service",              4,   50, "must",   r_dev),
        ("Scheduled email delivery",            3,    0, "could",  r_dev),
    ])
    add_req(2, "Custom Date Ranges", [
        ("Date-range picker component",         2,  100, "must",   r_des),
        ("Backend filter parameters",           2,   70, "must",   r_dev),
    ])

    # Feature 3: Billing & Subscriptions (45% done)
    add_req(3, "Stripe Integration", [
        ("Stripe account & product setup",      1,  100, "must",   r_dev),
        ("Subscription lifecycle webhooks",     5,   70, "must",   r_dev),
        ("Payment method management UI",        4,   20, "must",   r_des),
        ("Invoice generation & PDF",            4,    0, "must",   r_dev),
    ])
    add_req(3, "Plan Management", [
        ("Plan comparison page",                3,   60, "must",   r_des),
        ("Upgrade / downgrade flows",           5,   20, "must",   r_dev),
        ("Proration calculations",              3,    0, "must",   r_dev),
    ])

    # Feature 4: Mobile Experience (8% done)
    add_req(4, "Responsive Redesign", [
        ("Audit current breakpoints",           1,   80, "must",   r_des),
        ("Redesign card layout for mobile",     5,    0, "must",   r_des),
        ("Touch gesture support",               4,    0, "should", r_dev),
    ])
    add_req(4, "Native-feel Navigation", [
        ("Bottom nav bar component",            3,    0, "must",   r_des),
        ("Swipe transitions",                   2,    0, "could",  r_dev),
    ])

    # Feature 5: Admin Portal (0% done)
    add_req(5, "User Management", [
        ("User list & search UI",               4,    0, "must",   r_des),
        ("Invite / deactivate flows",           4,    0, "must",   r_dev),
        ("Bulk role assignment",                3,    0, "should", r_dev),
    ])
    add_req(5, "Audit Log", [
        ("Event capture middleware",            3,    0, "must",   r_dev),
        ("Log viewer UI with filters",          5,    0, "should", r_des),
    ])

    # Risks
    db["risks"].delete_where("project_id = 1")
    base = date(2026, 1, 10)
    db["risks"].insert({"project_id": 1, "name": "Third-party API deprecation",
        "description": "Stripe's legacy Charges API is deprecated in Q3; migration required before cutover.",
        "status": "open", "date_identified": "2026-01-10", "due_date": "2026-06-01",
        "impact_days": 12.0, "timeline_impact_days": 8.0, "sort_order": 1,
        "realised_percentage": 0.0, "resultant_work": ""})
    db["risks"].insert({"project_id": 1, "name": "Lead developer unavailability",
        "description": "Senior dev booked for 2-week client offsite in May, reducing capacity.",
        "status": "open", "date_identified": "2026-02-18", "due_date": "2026-05-31",
        "impact_days": 8.0, "timeline_impact_days": 10.0, "sort_order": 2,
        "realised_percentage": 0.0, "resultant_work": ""})
    db["risks"].insert({"project_id": 1, "name": "Scope expansion: custom reporting",
        "description": "Stakeholders requesting bespoke CSV export on top of PDF exports.",
        "status": "open", "date_identified": "2026-03-05", "due_date": "2026-06-15",
        "impact_days": 5.0, "timeline_impact_days": 3.0, "sort_order": 3,
        "realised_percentage": 0.0, "resultant_work": ""})
    db["risks"].insert({"project_id": 1, "name": "Database migration complexity",
        "description": "Legacy Oracle schema harder to map than estimated; required an extra sprint.",
        "status": "done", "date_identified": "2025-11-20", "due_date": "2026-01-31",
        "impact_days": 6.0, "timeline_impact_days": 5.0, "sort_order": 4,
        "realised_percentage": 100.0,
        "resultant_work": "Added a dedicated migration sprint (sprints 3–4) with extra DBA support."})

    # Capacity
    db["capacity_periods"].delete_where("project_id = 1")
    start = date(2026, 1, 5)
    for i in range(16):
        week = (start + timedelta(weeks=i)).isoformat()
        db["capacity_periods"].insert({"project_id": 1, "week_start_date": week, "role_id": r_dev, "team_size": 2})
        db["capacity_periods"].insert({"project_id": 1, "week_start_date": week, "role_id": r_des, "team_size": 1})
        if i >= 4:
            db["capacity_periods"].insert({"project_id": 1, "week_start_date": week, "role_id": r_qa, "team_size": 1})

    # PM Notes
    db["pm_notes"].delete_where("project_id = 1")
    db["pm_notes"].insert({"project_id": 1, "name": "Review UI designs with client",
        "description": "Walk through Figma mockups for billing flows and mobile nav.",
        "status": "todo", "due_date": "2026-04-25", "sort_order": 1})
    db["pm_notes"].insert({"project_id": 1, "name": "Prepare Sprint 9 backlog",
        "description": "Prioritise mobile + billing items for the upcoming sprint.",
        "status": "todo", "due_date": "2026-04-23", "sort_order": 2})
    db["pm_notes"].insert({"project_id": 1, "name": "Update risk register post-retro",
        "description": "Add new scope-creep risk identified in Sprint 8 retrospective.",
        "status": "todo", "due_date": "2026-04-28", "sort_order": 3})
    db["pm_notes"].insert({"project_id": 1, "name": "Sign off Phase 1 deliverables",
        "description": "Authentication and dashboard features approved by product owner.",
        "status": "done", "due_date": "2026-03-31", "sort_order": 4})
    db["pm_notes"].insert({"project_id": 1, "name": "Agree DB migration strategy with DBA",
        "description": "Resolved: Oracle → Postgres via pgloader with manual FK fixes.",
        "status": "done", "due_date": "2026-01-28", "sort_order": 5})

    print("Demo data seeded.")


# ── Screenshots ───────────────────────────────────────────────────────────────

PAGES = [
    ("Dashboard",      f"{P1}/",           "Dashboard.png"),
    ("Features",       f"{P1}/features",   "Features.png"),
    ("Feature Detail", f"{P1}/features/1", "Feature_Detail.png"),
    ("Capacity",       f"{P1}/capacity",   "Capacity.png"),
    ("Risks",          f"{P1}/risks",      "Risks.png"),
    ("PM Notes",       f"{P1}/notes",      "PM_Notes.png"),
    ("Settings",       f"{P1}/settings",   "Settings.png"),
]


def capture():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # Block Google Fonts to avoid network waits
        page.route("**fonts.googleapis.com**", lambda r: r.abort())
        page.route("**fonts.gstatic.com**",    lambda r: r.abort())

        for label, url, fname in PAGES:
            print(f"  Capturing {label}…")
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(400)
            out = os.path.join(OUT_DIR, fname)
            page.screenshot(path=out, full_page=False)
            print(f"    → {out}")

        browser.close()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        print("health_check.db already exists — remove it first if you want fresh demo data.")
        sys.exit(1)

    print("Seeding demo database…")
    seed()

    print(f"Starting server on port {PORT}…")
    srv = subprocess.Popen(
        ["uvicorn", "main:app", "--port", str(PORT), "--log-level", "warning"],
        cwd=os.path.dirname(__file__),
    )
    time.sleep(3)

    try:
        print("Taking screenshots…")
        capture()
        print("Done.")
    finally:
        srv.terminate()
        srv.wait()
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print("Cleaned up demo database.")
