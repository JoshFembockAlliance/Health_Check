"""demo_seed.py — Generate a demo SQLite database with sample data.

Creates (or recreates) a `demo.db` file populated with two projects:
  - "Alpha Mobile App"   (agile_feature_development)
  - "Beta Integration"   (fixed_price)

Usage:
    python demo_seed.py                     # creates demo.db
    python demo_seed.py --path my_demo.db   # custom path

To run the app against the demo database:
    HEALTH_CHECK_DB=demo.db uvicorn main:app --reload

Re-run this script any time the schema changes or new demo data is needed.
The database file is excluded from git (*.db in .gitignore) — commit this
script, not the binary.
"""
import argparse
import os
import sys

# Ensure we can import database from the same directory.
sys.path.insert(0, os.path.dirname(__file__))


def build(db_path: str) -> None:
    os.environ["HEALTH_CHECK_DB"] = db_path
    if os.path.exists(db_path):
        os.remove(db_path)

    # Import after env var is set so database.py picks up the path.
    import database
    import importlib
    importlib.reload(database)
    database.init_db()

    import sqlite_utils
    db = sqlite_utils.Database(db_path)

    # ── Agile project ──────────────────────────────────────────────────────

    db["projects"].update(1, {
        "name": "Alpha Mobile App",
        "description": "Cross-platform mobile app for retail customers.",
        "start_date": "2025-01-13",
        "as_of_date": "2025-04-28",
        "end_date": "2025-09-26",
        "initial_budget": 500_000.0,
        "actual_spend": 185_000.0,
        "team_size": 3,
        "health_on_track_pct": 100.0,
        "health_at_risk_pct": 80.0,
        "accent": "cyan",
        "theme": "light",
        "project_type": "agile_feature_development",
    })

    # Roles for the agile project
    eng_id = db["roles"].insert({"project_id": 1, "name": "Engineer", "day_rate": 1600.0, "category": "delivery"}).last_pk
    ba_id = db["roles"].insert({"project_id": 1, "name": "Business Analyst", "day_rate": 1200.0, "category": "overhead"}).last_pk
    db["roles"].update(1, {"name": "Senior Engineer", "day_rate": 1800.0, "category": "delivery"})
    db["projects"].update(1, {"default_role_id": eng_id, "overhead_team_size": 1, "default_overhead_role_id": ba_id})

    # Budget adjustments
    db["budget_adjustments"].insert({"project_id": 1, "amount": 25_000.0, "date": "2025-03-01", "description": "Scope extension — push notifications"})

    # Overheads
    db["overheads"].insert({"project_id": 1, "name": "PM Retainer", "description": "Weekly PM oversight", "amount": 15_000.0, "sort_order": 1})
    db["overheads"].insert({"project_id": 1, "name": "Tooling Licences", "description": "Figma, Jira, etc.", "amount": 3_600.0, "sort_order": 2})

    # Features
    auth_id = db["features"].insert({"project_id": 1, "name": "Authentication & Onboarding", "sort_order": 10, "started": 1, "expanded_scope": 0}).last_pk
    catalogue_id = db["features"].insert({"project_id": 1, "name": "Product Catalogue", "sort_order": 20, "started": 1, "expanded_scope": 0}).last_pk
    checkout_id = db["features"].insert({"project_id": 1, "name": "Checkout & Payments", "sort_order": 30, "started": 1, "expanded_scope": 0}).last_pk
    notif_id = db["features"].insert({"project_id": 1, "name": "Push Notifications", "sort_order": 40, "started": 0, "expanded_scope": 1}).last_pk

    # Requirements & deliverables (auth feature — mostly done)
    req_login = db["requirements"].insert({"feature_id": auth_id, "name": "Login & signup flows", "sort_order": 10, "expanded_scope": 0}).last_pk
    db["deliverables"].insert({"requirement_id": req_login, "name": "Email/password login", "budget_days": 3.0, "percent_complete": 100, "priority": "must", "role_id": eng_id, "sort_order": 10, "expanded_scope": 0})
    db["deliverables"].insert({"requirement_id": req_login, "name": "Social login (Google)", "budget_days": 4.0, "percent_complete": 100, "priority": "must", "role_id": eng_id, "sort_order": 20, "expanded_scope": 0})
    db["deliverables"].insert({"requirement_id": req_login, "name": "Onboarding wizard", "budget_days": 5.0, "percent_complete": 80, "priority": "should", "role_id": eng_id, "sort_order": 30, "expanded_scope": 0})

    req_profile = db["requirements"].insert({"feature_id": auth_id, "name": "Profile management", "sort_order": 20, "expanded_scope": 0}).last_pk
    db["deliverables"].insert({"requirement_id": req_profile, "name": "Edit profile details", "budget_days": 2.0, "percent_complete": 100, "priority": "must", "role_id": eng_id, "sort_order": 10, "expanded_scope": 0})
    db["deliverables"].insert({"requirement_id": req_profile, "name": "Change password", "budget_days": 1.5, "percent_complete": 100, "priority": "must", "role_id": eng_id, "sort_order": 20, "expanded_scope": 0})

    # Requirements & deliverables (catalogue — in progress)
    req_browse = db["requirements"].insert({"feature_id": catalogue_id, "name": "Browse & search", "sort_order": 10, "expanded_scope": 0}).last_pk
    db["deliverables"].insert({"requirement_id": req_browse, "name": "Category listing", "budget_days": 4.0, "percent_complete": 100, "priority": "must", "role_id": eng_id, "sort_order": 10, "expanded_scope": 0})
    db["deliverables"].insert({"requirement_id": req_browse, "name": "Full-text product search", "budget_days": 6.0, "percent_complete": 60, "priority": "must", "role_id": eng_id, "sort_order": 20, "expanded_scope": 0})
    db["deliverables"].insert({"requirement_id": req_browse, "name": "Filter & sort", "budget_days": 4.0, "percent_complete": 30, "priority": "should", "role_id": eng_id, "sort_order": 30, "expanded_scope": 0})

    req_pdp = db["requirements"].insert({"feature_id": catalogue_id, "name": "Product detail page", "sort_order": 20, "expanded_scope": 0}).last_pk
    db["deliverables"].insert({"requirement_id": req_pdp, "name": "Image gallery", "budget_days": 3.0, "percent_complete": 50, "priority": "must", "role_id": eng_id, "sort_order": 10, "expanded_scope": 0})
    db["deliverables"].insert({"requirement_id": req_pdp, "name": "Related products", "budget_days": 3.0, "percent_complete": 0, "priority": "could", "role_id": eng_id, "sort_order": 20, "expanded_scope": 0})

    # Requirements & deliverables (checkout — not started)
    req_cart = db["requirements"].insert({"feature_id": checkout_id, "name": "Cart management", "sort_order": 10, "expanded_scope": 0}).last_pk
    db["deliverables"].insert({"requirement_id": req_cart, "name": "Add/remove items", "budget_days": 3.0, "percent_complete": 0, "priority": "must", "role_id": eng_id, "sort_order": 10, "expanded_scope": 0})
    db["deliverables"].insert({"requirement_id": req_cart, "name": "Quantity controls", "budget_days": 2.0, "percent_complete": 0, "priority": "must", "role_id": eng_id, "sort_order": 20, "expanded_scope": 0})

    req_pay = db["requirements"].insert({"feature_id": checkout_id, "name": "Payment integration", "sort_order": 20, "expanded_scope": 0}).last_pk
    db["deliverables"].insert({"requirement_id": req_pay, "name": "Stripe card payment", "budget_days": 8.0, "percent_complete": 0, "priority": "must", "role_id": eng_id, "sort_order": 10, "expanded_scope": 0})
    db["deliverables"].insert({"requirement_id": req_pay, "name": "Apple Pay / Google Pay", "budget_days": 5.0, "percent_complete": 0, "priority": "should", "role_id": eng_id, "sort_order": 20, "expanded_scope": 0})

    # Requirements & deliverables (push notifications — expanded scope)
    req_push = db["requirements"].insert({"feature_id": notif_id, "name": "Order status notifications", "sort_order": 10, "expanded_scope": 1}).last_pk
    db["deliverables"].insert({"requirement_id": req_push, "name": "FCM/APNS integration", "budget_days": 6.0, "percent_complete": 0, "priority": "must", "role_id": eng_id, "sort_order": 10, "expanded_scope": 1})
    db["deliverables"].insert({"requirement_id": req_push, "name": "Notification preferences", "budget_days": 3.0, "percent_complete": 0, "priority": "should", "role_id": eng_id, "sort_order": 20, "expanded_scope": 1})

    # Risks
    r1 = db["risks"].insert({"project_id": 1, "name": "Third-party payment API delays", "description": "Stripe onboarding SLA may slip.", "status": "open", "date_identified": "2025-02-10", "due_date": "2025-06-30", "impact_days": 10.0, "timeline_impact_days": 5.0, "sort_order": 10, "realised_percentage": 0.0, "resultant_work": ""}).last_pk
    r2 = db["risks"].insert({"project_id": 1, "name": "iOS App Store review delay", "description": "First submission typically takes 1–2 weeks.", "status": "open", "date_identified": "2025-03-15", "due_date": "2025-08-15", "impact_days": 8.0, "timeline_impact_days": 10.0, "sort_order": 20, "realised_percentage": 0.0, "resultant_work": ""}).last_pk
    r3 = db["risks"].insert({"project_id": 1, "name": "Key engineer sick leave", "description": "Senior engineer had extended sick leave in Feb.", "status": "done", "date_identified": "2025-02-01", "due_date": "2025-02-28", "impact_days": 6.0, "timeline_impact_days": 0.0, "sort_order": 30, "realised_percentage": 100.0, "resultant_work": "Sprint replanning completed. Scope de-prioritised related product feature."}).last_pk

    db["risk_features"].insert({"risk_id": r1, "feature_id": checkout_id})
    db["risk_features"].insert({"risk_id": r2, "feature_id": checkout_id})
    db["risk_features"].insert({"risk_id": r3, "feature_id": catalogue_id})

    # Decisions
    d1 = db["decisions"].insert({"project_id": 1, "name": "Drop Android-first approach in favour of cross-platform React Native", "description": "<p>After prototyping natively, React Native was selected to reduce delivery time.</p>", "expected_outcome": "30% reduction in delivery timeline by sharing code between iOS and Android.", "decision_date": "2025-01-20", "decision_type": "Pivot", "sort_order": 10}).last_pk
    d2 = db["decisions"].insert({"project_id": 1, "name": "Related products section is a 'could have', not 'must have'", "description": "<p>Deferred to post-MVP given budget constraints.</p>", "expected_outcome": "MVP shipped on budget without related products.", "decision_date": "2025-03-05", "decision_type": "Scope Adjustment", "sort_order": 20}).last_pk
    db["decision_features"].insert({"decision_id": d1, "feature_id": auth_id})
    db["decision_features"].insert({"decision_id": d2, "feature_id": catalogue_id})

    # Capacity periods (weekly, delivery team)
    for week, size in [
        ("2025-01-13", 3), ("2025-01-20", 3), ("2025-01-27", 3),
        ("2025-02-03", 3), ("2025-02-10", 2), ("2025-02-17", 2),  # sick leave period
        ("2025-02-24", 3), ("2025-03-03", 3), ("2025-03-10", 3),
        ("2025-03-17", 3), ("2025-03-24", 3), ("2025-03-31", 3),
        ("2025-04-07", 3), ("2025-04-14", 3), ("2025-04-22", 3),
    ]:
        db["capacity_periods"].insert({"project_id": 1, "week_start_date": week, "role_id": eng_id, "team_size": size})

    # BA overhead capacity (1 person throughout)
    for week in [
        "2025-01-13", "2025-01-20", "2025-01-27",
        "2025-02-03", "2025-02-10", "2025-02-17", "2025-02-24",
        "2025-03-03", "2025-03-10", "2025-03-17", "2025-03-24", "2025-03-31",
        "2025-04-07", "2025-04-14", "2025-04-22",
    ]:
        db["capacity_periods"].insert({"project_id": 1, "week_start_date": week, "role_id": ba_id, "team_size": 1})

    # PM notes
    db["pm_notes"].insert({"project_id": 1, "name": "Sprint 8 review — strong velocity", "description": "<p>Team recovered well from Feb sick leave. Checkout feature on track for next sprint.</p>", "status": "active", "due_date": "", "sort_order": 10})
    db["pm_notes"].insert({"project_id": 1, "name": "Stripe integration — risk watch", "description": "<p>Stripe onboarding initiated. Chase weekly.</p>", "status": "sticky", "due_date": "2025-06-01", "sort_order": 20})

    # ── Fixed-price project ────────────────────────────────────────────────

    fp_id = db["projects"].insert({
        "name": "Beta Integration",
        "description": "ERP integration for a logistics client. Fixed-price contract.",
        "start_date": "2025-02-03",
        "as_of_date": "2025-04-28",
        "end_date": "2025-08-29",
        "initial_budget": 0.0,
        "actual_spend": 68_000.0,
        "team_size": 2,
        "health_on_track_pct": 100.0,
        "health_at_risk_pct": 80.0,
        "accent": "purple",
        "theme": "light",
        "project_type": "fixed_price",
        "overhead_team_size": 0,
        "default_overhead_role_id": 0,
    }).last_pk

    fp_eng_id = db["roles"].insert({"project_id": fp_id, "name": "Developer", "day_rate": 1500.0, "category": "delivery"}).last_pk
    db["projects"].update(fp_id, {"default_role_id": fp_eng_id})

    # Milestones (sorted in delivery order)
    m1 = db["milestones"].insert({"project_id": fp_id, "name": "Discovery & Design", "description": "Requirements workshops and technical architecture sign-off.", "value": 30_000.0, "sort_order": 10}).last_pk
    m2 = db["milestones"].insert({"project_id": fp_id, "name": "API Integration", "description": "ERP read/write API layer complete and tested.", "value": 60_000.0, "sort_order": 20}).last_pk
    m3 = db["milestones"].insert({"project_id": fp_id, "name": "User Interface", "description": "Frontend portal delivered and UAT-approved.", "value": 50_000.0, "sort_order": 30}).last_pk
    m4 = db["milestones"].insert({"project_id": fp_id, "name": "Go-Live & Handover", "description": "Production deployment and handover documentation.", "value": 20_000.0, "sort_order": 40}).last_pk

    # Milestone 1 fully paid, Milestone 2 invoiced but not yet paid
    db["milestone_invoices"].insert({"milestone_id": m1, "invoice_number": "INV-001", "amount": 30_000.0, "status": "paid", "issue_date": "2025-03-01", "paid_date": "2025-03-15"})
    db["milestone_invoices"].insert({"milestone_id": m2, "invoice_number": "INV-002", "amount": 60_000.0, "status": "invoiced", "issue_date": "2025-04-20", "paid_date": ""})

    # Features for the fixed-price project
    fp_disc = db["features"].insert({"project_id": fp_id, "name": "Discovery & Architecture", "sort_order": 10, "started": 1, "expanded_scope": 0}).last_pk
    fp_api = db["features"].insert({"project_id": fp_id, "name": "ERP API Layer", "sort_order": 20, "started": 1, "expanded_scope": 0}).last_pk
    fp_ui = db["features"].insert({"project_id": fp_id, "name": "Portal UI", "sort_order": 30, "started": 0, "expanded_scope": 0}).last_pk

    db["milestone_features"].insert({"milestone_id": m1, "feature_id": fp_disc})
    db["milestone_features"].insert({"milestone_id": m2, "feature_id": fp_api})
    db["milestone_features"].insert({"milestone_id": m3, "feature_id": fp_ui})

    fp_req1 = db["requirements"].insert({"feature_id": fp_disc, "name": "Requirements workshops", "sort_order": 10, "expanded_scope": 0}).last_pk
    db["deliverables"].insert({"requirement_id": fp_req1, "name": "Stakeholder interviews", "budget_days": 3.0, "percent_complete": 100, "priority": "must", "role_id": fp_eng_id, "sort_order": 10, "expanded_scope": 0})
    db["deliverables"].insert({"requirement_id": fp_req1, "name": "Tech architecture doc", "budget_days": 4.0, "percent_complete": 100, "priority": "must", "role_id": fp_eng_id, "sort_order": 20, "expanded_scope": 0})

    fp_req2 = db["requirements"].insert({"feature_id": fp_api, "name": "ERP read endpoints", "sort_order": 10, "expanded_scope": 0}).last_pk
    db["deliverables"].insert({"requirement_id": fp_req2, "name": "Inventory read API", "budget_days": 6.0, "percent_complete": 100, "priority": "must", "role_id": fp_eng_id, "sort_order": 10, "expanded_scope": 0})
    db["deliverables"].insert({"requirement_id": fp_req2, "name": "Order status read API", "budget_days": 5.0, "percent_complete": 80, "priority": "must", "role_id": fp_eng_id, "sort_order": 20, "expanded_scope": 0})

    fp_req3 = db["requirements"].insert({"feature_id": fp_api, "name": "ERP write endpoints", "sort_order": 20, "expanded_scope": 0}).last_pk
    db["deliverables"].insert({"requirement_id": fp_req3, "name": "Order creation API", "budget_days": 7.0, "percent_complete": 40, "priority": "must", "role_id": fp_eng_id, "sort_order": 10, "expanded_scope": 0})
    db["deliverables"].insert({"requirement_id": fp_req3, "name": "Webhook callbacks", "budget_days": 4.0, "percent_complete": 0, "priority": "must", "role_id": fp_eng_id, "sort_order": 20, "expanded_scope": 0})

    fp_req4 = db["requirements"].insert({"feature_id": fp_ui, "name": "Dashboard views", "sort_order": 10, "expanded_scope": 0}).last_pk
    db["deliverables"].insert({"requirement_id": fp_req4, "name": "Inventory dashboard", "budget_days": 5.0, "percent_complete": 0, "priority": "must", "role_id": fp_eng_id, "sort_order": 10, "expanded_scope": 0})
    db["deliverables"].insert({"requirement_id": fp_req4, "name": "Order management view", "budget_days": 6.0, "percent_complete": 0, "priority": "must", "role_id": fp_eng_id, "sort_order": 20, "expanded_scope": 0})

    # A risk
    db["risks"].insert({"project_id": fp_id, "name": "ERP vendor API changes without notice", "description": "<p>Vendor has a history of breaking changes between minor versions.</p>", "status": "open", "date_identified": "2025-02-15", "due_date": "2025-08-01", "impact_days": 5.0, "timeline_impact_days": 3.0, "sort_order": 10, "realised_percentage": 0.0, "resultant_work": ""})

    # A decision
    db["decisions"].insert({"project_id": fp_id, "name": "Use REST over GraphQL for the ERP integration layer", "description": "<p>Client's IT team has existing REST tooling and monitoring.</p>", "expected_outcome": "Faster client sign-off on technical approach.", "decision_date": "2025-02-12", "decision_type": "Pivot", "sort_order": 10})

    print(f"Demo database written to: {db_path}")
    print(f"  Project 1: Alpha Mobile App  (agile, id=1)")
    print(f"  Project 2: Beta Integration  (fixed_price, id={fp_id})")
    print()
    print("To start the app with demo data:")
    print(f"  HEALTH_CHECK_DB={db_path} uvicorn main:app --reload")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Health Check demo database")
    parser.add_argument("--path", default="demo.db", help="Output path for the SQLite database")
    args = parser.parse_args()
    build(args.path)
