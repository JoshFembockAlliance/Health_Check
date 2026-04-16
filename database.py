"""database.py — SQLite schema initialisation and migration.

All tables are created here if they don't exist. Additive migrations
(new columns) are also applied here so that an existing database
automatically gains new fields on the next server start.
"""
import sqlite_utils
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "health_check.db")


def get_db() -> sqlite_utils.Database:
    """Return a sqlite_utils Database handle. A new connection is opened each call."""
    return sqlite_utils.Database(DB_PATH)


def init_db():
    """Create all tables and run additive migrations. Safe to call on every startup."""
    db = get_db()

    # roles — named day-rate buckets (e.g. "Developer $1,435/day").
    # The project has a default_role_id; deliverables can override with a specific role.
    if "roles" not in db.table_names():
        db["roles"].create({
            "id": int,
            "name": str,
            "day_rate": float,
        }, pk="id")

    # project — singleton row (id=1). All financial settings live here.
    # health_on_track_pct / health_at_risk_pct are percentage thresholds used by
    # feature_health() to colour-code each feature's progress badge.
    if "project" not in db.table_names():
        db["project"].create({
            "id": int,
            "name": str,
            "start_date": str,
            "as_of_date": str,
            "initial_budget": float,
            "team_size": int,
            "actual_spend": float,
            "default_role_id": int,
            "health_on_track_pct": float,
            "health_at_risk_pct": float,
        }, pk="id")

    # budget_adjustments — one row per change event (e.g. scope increase, contingency).
    # current_budget = initial_budget + SUM(adjustments.amount)
    if "budget_adjustments" not in db.table_names():
        db["budget_adjustments"].create({
            "id": int,
            "amount": float,
            "date": str,
            "description": str,
        }, pk="id")

    # features → requirements → deliverables: three-tier work breakdown structure.
    # started=1 means the PM has acknowledged this feature is in flight,
    # which affects the adjusted health target on the dashboard.
    if "features" not in db.table_names():
        db["features"].create({
            "id": int,
            "name": str,
            "sort_order": int,
            "started": int,  # 0 = not started, 1 = started
        }, pk="id")

    # Migration: add started column if missing
    feat_cols = {col.name for col in db["features"].columns}
    if "started" not in feat_cols:
        db["features"].add_column("started", int, not_null_default=0)

    if "requirements" not in db.table_names():
        db["requirements"].create({
            "id": int,
            "feature_id": int,
            "name": str,
            "sort_order": int,
        }, pk="id", foreign_keys=[("feature_id", "features")])

    if "deliverables" not in db.table_names():
        db["deliverables"].create({
            "id": int,
            "requirement_id": int,
            "name": str,
            "budget_days": float,
            "percent_complete": int,
            "priority": str,
            "role_id": int,
            "sort_order": int,
        }, pk="id", foreign_keys=[("requirement_id", "requirements"), ("role_id", "roles")])

    # Seed default role and project if empty
    if db["roles"].count == 0:
        db["roles"].insert({"name": "Default", "day_rate": 1435.00})

    # Add threshold columns to existing databases that don't have them
    existing_cols = {col.name for col in db["project"].columns}
    if "health_on_track_pct" not in existing_cols:
        db["project"].add_column("health_on_track_pct", float, not_null_default=100.0)
    if "health_at_risk_pct" not in existing_cols:
        db["project"].add_column("health_at_risk_pct", float, not_null_default=80.0)

    # risks — project risks with impact measured in days.
    # status drives the lifecycle (todo/doing/done); realised_percentage
    # (0-100, independent of status) determines how many impact_days
    # have already been absorbed into the budget via effective_impact_days().
    if "risks" not in db.table_names():
        db["risks"].create({
            "id": int,
            "name": str,
            "description": str,
            "status": str,
            "due_date": str,
            "impact_days": float,
            "sort_order": int,
            "realised_percentage": float,
            "resultant_work": str,
        }, pk="id")

    # Migration: reshape legacy (resolution_type, mitigation_percentage) columns
    # into a single realised_percentage field.
    if "risks" in db.table_names():
        risk_cols = {col.name for col in db["risks"].columns}
        if "name" not in risk_cols:
            db["risks"].add_column("name", str, not_null_default="")
        if "resultant_work" not in risk_cols:
            db["risks"].add_column("resultant_work", str, not_null_default="")
        if "realised_percentage" not in risk_cols:
            db["risks"].add_column("realised_percentage", float, not_null_default=0.0)
            # Back-fill from the legacy columns if they are still present.
            if "resolution_type" in risk_cols and "mitigation_percentage" in risk_cols:
                db.execute("UPDATE risks SET realised_percentage = 0 WHERE resolution_type = 'avoided'")
                db.execute("UPDATE risks SET realised_percentage = mitigation_percentage WHERE resolution_type = 'mitigated'")
                db.execute("UPDATE risks SET realised_percentage = 100 WHERE resolution_type = 'realised'")
                # Conservative default — any closed risk without a resolution
                # previously counted as fully realised; match that.
                db.execute("UPDATE risks SET realised_percentage = 100 WHERE status = 'done' AND (resolution_type IS NULL OR resolution_type = '')")
                db.conn.commit()
        # Drop legacy columns once migration has run.
        current_cols = {col.name for col in db["risks"].columns}
        legacy_cols = {c for c in ("resolution_type", "mitigation_percentage") if c in current_cols}
        if legacy_cols:
            db["risks"].transform(drop=legacy_cols)

    if "risk_features" not in db.table_names():
        db["risk_features"].create({
            "risk_id": int,
            "feature_id": int,
        }, foreign_keys=[("risk_id", "risks"), ("feature_id", "features")])

    # Capacity planning: one row per (week, role) pair.
    # Multiple rows can exist for the same week to represent different roles.
    # NULL role_id means use the project's default role/rate for that team_size.
    if "capacity_periods" not in db.table_names():
        db["capacity_periods"].create({
            "id": int,
            "week_start_date": str,  # ISO date of Monday of the week
            "role_id": int,          # NULL = default role
            "team_size": int,        # number of people with this role this week
        }, pk="id", foreign_keys=[("role_id", "roles")])

    # PM Notes: freeform notes with status lifecycle and optional due dates.
    # Status "sticky" notes always appear on the dashboard regardless of due date.
    if "pm_notes" not in db.table_names():
        db["pm_notes"].create({
            "id": int,
            "name": str,
            "description": str,
            "status": str,       # "todo" | "doing" | "done" | "sticky"
            "due_date": str,     # ISO date; NULL/empty for sticky notes is fine
            "sort_order": int,
        }, pk="id")

    # overheads — fixed dollar costs that reduce the budget pool available for
    # feature delivery (e.g. PM salary, tool licences, cloud hosting).
    # Sum of amount is deducted from accessible_budget in project_summary().
    if "overheads" not in db.table_names():
        db["overheads"].create({
            "id": int,
            "name": str,
            "description": str,
            "amount": float,
            "sort_order": int,
        }, pk="id")

    if db["project"].count == 0:
        default_role = list(db["roles"].rows)[0]
        db["project"].insert({
            "id": 1,
            "name": "New Project",
            "start_date": "",
            "as_of_date": "",
            "initial_budget": 0.0,
            "team_size": 1,
            "actual_spend": 0.0,
            "default_role_id": default_role["id"],
            "health_on_track_pct": 100.0,
            "health_at_risk_pct": 80.0,
        })
