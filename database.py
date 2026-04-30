"""database.py — SQLite schema initialisation and migration.

All tables are created here if they don't exist. Additive migrations
(new columns) are also applied here so that an existing database
automatically gains new fields on the next server start.

Multi-project: the former singleton `project` table now holds one row
per project. Every project-scoped table (features, risks, pm_notes,
budget_adjustments, capacity_periods, overheads, roles) carries a
`project_id` column. Requirements/deliverables inherit scope through
features; risk_features through risks.
"""
import sqlite_utils
import os
from datetime import date as _date

DB_PATH = os.path.join(os.path.dirname(__file__), "health_check.db")

# Tables that are scoped to a single project via a project_id column.
PROJECT_SCOPED_TABLES = [
    "roles",
    "features",
    "risks",
    "pm_notes",
    "decisions",
    "budget_adjustments",
    "capacity_periods",
    "overheads",
    "milestones",
]

# Project types. "agile_feature_development" is the legacy default; any project
# without an explicit type will render as agile. "fixed_price" opts into the
# milestone-driven dashboard and data model.
PROJECT_TYPE_AGILE = "agile_feature_development"
PROJECT_TYPE_FIXED_PRICE = "fixed_price"
VALID_PROJECT_TYPES = {PROJECT_TYPE_AGILE, PROJECT_TYPE_FIXED_PRICE}


def get_db() -> sqlite_utils.Database:
    """Return a sqlite_utils Database handle. A new connection is opened each call."""
    return sqlite_utils.Database(DB_PATH)


def _ensure_project_id_column(db, table_name: str, default_project_id: int = 1):
    """Backfill a project_id column on an existing table, defaulting to project 1."""
    if table_name not in db.table_names():
        return
    cols = {col.name for col in db[table_name].columns}
    if "project_id" not in cols:
        db[table_name].add_column("project_id", int, not_null_default=default_project_id)


def init_db():
    """Create all tables and run additive migrations. Safe to call on every startup."""
    db = get_db()

    # projects — one row per tracked engagement. The singleton `project` table
    # has been renamed; the row with id=1 is preserved on migration so existing
    # databases stay intact.
    if "projects" not in db.table_names() and "project" in db.table_names():
        # Migrate old singleton `project` table → `projects` multi-row table.
        db.execute("ALTER TABLE project RENAME TO projects")
    if "projects" not in db.table_names():
        db["projects"].create({
            "id": int,
            "name": str,
            "description": str,
            "start_date": str,
            "as_of_date": str,
            "initial_budget": float,
            "team_size": float,
            "actual_spend": float,
            "default_role_id": int,
            "health_on_track_pct": float,
            "health_at_risk_pct": float,
        }, pk="id")

    # Additive migrations on projects table
    existing_cols = {col.name for col in db["projects"].columns}
    if "description" not in existing_cols:
        db["projects"].add_column("description", str, not_null_default="")
    if "health_on_track_pct" not in existing_cols:
        db["projects"].add_column("health_on_track_pct", float, not_null_default=100.0)
    if "health_at_risk_pct" not in existing_cols:
        db["projects"].add_column("health_at_risk_pct", float, not_null_default=80.0)
    if "accent" not in existing_cols:
        db["projects"].add_column("accent", str, not_null_default="cyan")
    if "theme" not in existing_cols:
        db["projects"].add_column("theme", str, not_null_default="light")
    if "icon" not in existing_cols:
        db["projects"].add_column("icon", str, not_null_default="")
    if "end_date" not in existing_cols:
        db["projects"].add_column("end_date", str, not_null_default="")
    if "project_type" not in existing_cols:
        db["projects"].add_column("project_type", str, not_null_default=PROJECT_TYPE_AGILE)
    # Overhead-team defaults: parallel to team_size / default_role_id, but
    # scoped to non-delivery (overhead-category) roles. Headcount × default
    # overhead role rate is used to extrapolate projected overhead-team $
    # for weeks past the planned capacity horizon. See DESIGN_RULES §1.
    if "overhead_team_size" not in existing_cols:
        db["projects"].add_column("overhead_team_size", int, not_null_default=0)
    if "default_overhead_role_id" not in existing_cols:
        db["projects"].add_column("default_overhead_role_id", int, not_null_default=0)

    # roles — named day-rate buckets. Now per-project so each engagement can
    # have its own rate card.
    if "roles" not in db.table_names():
        db["roles"].create({
            "id": int,
            "project_id": int,
            "name": str,
            "day_rate": float,
            "category": str,
        }, pk="id", foreign_keys=[("project_id", "projects")])

    # roles.category — 'delivery' (default) or 'overhead'. Overhead-category
    # roles burn budget as pre-committed overhead instead of feature-delivery
    # capacity (BAs, designers, SMEs, facilitators). See DESIGN_RULES §1.
    role_cols = {col.name for col in db["roles"].columns}
    if "category" not in role_cols:
        db["roles"].add_column("category", str, not_null_default="delivery")

    # features → requirements → deliverables: three-tier work breakdown structure.
    if "features" not in db.table_names():
        db["features"].create({
            "id": int,
            "project_id": int,
            "name": str,
            "sort_order": int,
            "started": int,
        }, pk="id", foreign_keys=[("project_id", "projects")])

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

    # budget_adjustments — one row per change event.
    if "budget_adjustments" not in db.table_names():
        db["budget_adjustments"].create({
            "id": int,
            "project_id": int,
            "amount": float,
            "date": str,
            "description": str,
        }, pk="id", foreign_keys=[("project_id", "projects")])

    # risks
    if "risks" not in db.table_names():
        db["risks"].create({
            "id": int,
            "project_id": int,
            "name": str,
            "description": str,
            "status": str,
            "date_identified": str,
            "due_date": str,
            "impact_days": float,
            "timeline_impact_days": float,
            "sort_order": int,
            "realised_percentage": float,
            "resultant_work": str,
        }, pk="id", foreign_keys=[("project_id", "projects")])

    if "risks" in db.table_names():
        risk_cols = {col.name for col in db["risks"].columns}
        if "name" not in risk_cols:
            db["risks"].add_column("name", str, not_null_default="")
        if "resultant_work" not in risk_cols:
            db["risks"].add_column("resultant_work", str, not_null_default="")
        if "timeline_impact_days" not in risk_cols:
            db["risks"].add_column("timeline_impact_days", float, not_null_default=0.0)
        if "date_identified" not in risk_cols:
            today = _date.today().isoformat()
            db["risks"].add_column("date_identified", str, not_null_default=today)
        if "realised_percentage" not in risk_cols:
            db["risks"].add_column("realised_percentage", float, not_null_default=0.0)
            if "resolution_type" in risk_cols and "mitigation_percentage" in risk_cols:
                db.execute("UPDATE risks SET realised_percentage = 0 WHERE resolution_type = 'avoided'")
                db.execute("UPDATE risks SET realised_percentage = mitigation_percentage WHERE resolution_type = 'mitigated'")
                db.execute("UPDATE risks SET realised_percentage = 100 WHERE resolution_type = 'realised'")
                db.execute("UPDATE risks SET realised_percentage = 100 WHERE status = 'done' AND (resolution_type IS NULL OR resolution_type = '')")
                db.conn.commit()
        current_cols = {col.name for col in db["risks"].columns}
        legacy_cols = {c for c in ("resolution_type", "mitigation_percentage") if c in current_cols}
        if legacy_cols:
            db["risks"].transform(drop=legacy_cols)

    if "risk_features" not in db.table_names():
        db["risk_features"].create({
            "risk_id": int,
            "feature_id": int,
        }, foreign_keys=[("risk_id", "risks"), ("feature_id", "features")])

    # Capacity planning
    if "capacity_periods" not in db.table_names():
        db["capacity_periods"].create({
            "id": int,
            "project_id": int,
            "week_start_date": str,
            "role_id": int,
            "team_size": float,
        }, pk="id", foreign_keys=[("role_id", "roles"), ("project_id", "projects")])

    # PM Notes
    if "pm_notes" not in db.table_names():
        db["pm_notes"].create({
            "id": int,
            "project_id": int,
            "name": str,
            "description": str,
            "status": str,
            "due_date": str,
            "sort_order": int,
        }, pk="id", foreign_keys=[("project_id", "projects")])

    # Decisions — pivots, acknowledged limitations, scope adjustments
    if "decisions" not in db.table_names():
        db["decisions"].create({
            "id": int,
            "project_id": int,
            "name": str,
            "description": str,
            "decision_date": str,
            "decision_type": str,
            "sort_order": int,
        }, pk="id", foreign_keys=[("project_id", "projects")])

    existing_decision_cols = {col.name for col in db["decisions"].columns} if "decisions" in db.table_names() else set()
    if "expected_outcome" not in existing_decision_cols and "decisions" in db.table_names():
        db["decisions"].add_column("expected_outcome", str, not_null_default="")

    if "decision_features" not in db.table_names():
        db["decision_features"].create({
            "decision_id": int,
            "feature_id": int,
        }, foreign_keys=[("decision_id", "decisions"), ("feature_id", "features")])

    # overheads
    if "overheads" not in db.table_names():
        db["overheads"].create({
            "id": int,
            "project_id": int,
            "name": str,
            "description": str,
            "amount": float,
            "sort_order": int,
        }, pk="id", foreign_keys=[("project_id", "projects")])

    # Milestones — fixed-price project type only. Each milestone carries a
    # contracted value; the sum of milestone values *is* the fixed-price
    # project's total_budget. Bar position on the dashboard is determined
    # by sort_order × value share.
    if "milestones" not in db.table_names():
        db["milestones"].create({
            "id": int,
            "project_id": int,
            "name": str,
            "description": str,
            "value": float,
            "sort_order": int,
        }, pk="id", foreign_keys=[("project_id", "projects")])

    # milestone_features — M2M link. Linked features colour the milestone's
    # section of the progress bar by their weighted completion; they do NOT
    # determine the bar position (value does).
    if "milestone_features" not in db.table_names():
        db["milestone_features"].create({
            "milestone_id": int,
            "feature_id": int,
        }, foreign_keys=[("milestone_id", "milestones"), ("feature_id", "features")])

    # milestone_invoices — a milestone can be billed in one or more instalments.
    # status = "invoiced" or "paid"; summed invoice amounts must not exceed the
    # milestone's value (enforced in the route layer).
    if "milestone_invoices" not in db.table_names():
        db["milestone_invoices"].create({
            "id": int,
            "milestone_id": int,
            "invoice_number": str,
            "amount": float,
            "status": str,
            "issue_date": str,
            "paid_date": str,
        }, pk="id", foreign_keys=[("milestone_id", "milestones")])

    # Backfill project_id on every project-scoped table (for DBs migrated from
    # the pre-multi-project schema).
    for tbl in PROJECT_SCOPED_TABLES:
        _ensure_project_id_column(db, tbl, default_project_id=1)

    # Seed the first project + default role if the DB is empty.
    if db["projects"].count == 0:
        db["projects"].insert({
            "id": 1,
            "name": "New Project",
            "description": "",
            "start_date": "",
            "as_of_date": "",
            "initial_budget": 0.0,
            "team_size": 1,
            "actual_spend": 0.0,
            "default_role_id": 1,
            "health_on_track_pct": 100.0,
            "health_at_risk_pct": 80.0,
            "project_type": PROJECT_TYPE_AGILE,
        })

    if db["roles"].count == 0:
        db["roles"].insert({"project_id": 1, "name": "Default", "day_rate": 1435.00})


def seed_project_defaults(project_id: int) -> int:
    """Seed a newly created project with a Default role, returning the role_id.
    Also sets the project's default_role_id to that role."""
    db = get_db()
    role_id = db["roles"].insert({
        "project_id": project_id,
        "name": "Default",
        "day_rate": 1435.00,
    }).last_pk
    db["projects"].update(project_id, {"default_role_id": role_id})
    return role_id
