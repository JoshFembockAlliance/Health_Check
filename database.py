import sqlite_utils
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "health_check.db")


def get_db() -> sqlite_utils.Database:
    return sqlite_utils.Database(DB_PATH)


def init_db():
    db = get_db()

    if "roles" not in db.table_names():
        db["roles"].create({
            "id": int,
            "name": str,
            "day_rate": float,
        }, pk="id")

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

    if "budget_adjustments" not in db.table_names():
        db["budget_adjustments"].create({
            "id": int,
            "amount": float,
            "date": str,
            "description": str,
        }, pk="id")

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

    if "risks" not in db.table_names():
        db["risks"].create({
            "id": int,
            "name": str,
            "description": str,
            "status": str,
            "due_date": str,
            "impact_days": float,
            "sort_order": int,
        }, pk="id")

    # Migration: add columns if missing
    if "risks" in db.table_names():
        risk_cols = {col.name for col in db["risks"].columns}
        if "name" not in risk_cols:
            db["risks"].add_column("name", str, not_null_default="")
        if "resolution_type" not in risk_cols:
            db["risks"].add_column("resolution_type", str)
        if "mitigation_percentage" not in risk_cols:
            db["risks"].add_column("mitigation_percentage", float, not_null_default=0.0)
        # Back-fill existing "done" risks — conservative default: treat as fully realised
        db.execute("UPDATE risks SET resolution_type = 'realised' WHERE status = 'done' AND resolution_type IS NULL")
        db.conn.commit()

    if "risk_features" not in db.table_names():
        db["risk_features"].create({
            "risk_id": int,
            "feature_id": int,
        }, foreign_keys=[("risk_id", "risks"), ("feature_id", "features")])

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
