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
        }, pk="id")

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
        })
