from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import os
import csv
import io
import zipfile
import html as _html_module
from datetime import datetime, date as _date, timedelta

from database import init_db, get_db, seed_project_defaults, PROJECT_SCOPED_TABLES
from calculations import (
    deliverable_summary,
    requirement_summary,
    feature_summary,
    project_summary,
    feature_health,
    effective_impact_days,
    unrealised_exposure_days,
    resolution_label,
    capacity_days_remaining,
    capacity_plan_summary,
    capacity_budget_summary,
    get_week_monday,
    parse_date,
)

app = FastAPI()
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


# ── Formatting filters ──

def fmt_currency(value):
    if value is None:
        return "$0"
    return f"${value:,.0f}"


def fmt_pct(value):
    if value is None:
        return "0%"
    return f"{value:.1f}%"


def fmt_days(value):
    if value is None:
        return "0"
    return f"{value:,.1f}"


def fmt_age_days(iso_date_str):
    if not iso_date_str:
        return None
    try:
        d = _date.fromisoformat(iso_date_str)
    except (ValueError, TypeError):
        return None
    return (_date.today() - d).days


def render_rich(value):
    if not value:
        return ""
    stripped = value.strip()
    if stripped.startswith("<"):
        return stripped
    return _html_module.escape(stripped).replace("\n", "<br>")


templates.env.filters["currency"] = fmt_currency
templates.env.filters["pct"] = fmt_pct
templates.env.filters["days"] = fmt_days
templates.env.filters["age_days"] = fmt_age_days
templates.env.filters["render_rich"] = render_rich


@app.on_event("startup")
def startup():
    init_db()


# ── Project-scoped helpers ──

def get_project(project_id: int):
    """Return a single project row or raise 404."""
    db = get_db()
    try:
        return db["projects"].get(project_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")


def get_all_projects():
    """List every project row ordered by id — used for the sidebar."""
    db = get_db()
    return list(db.execute("SELECT * FROM projects ORDER BY id").fetchall()) if False else [
        dict(row) for row in db["projects"].rows
    ]


def get_roles(project_id: int):
    db = get_db()
    return list(db.execute(
        "SELECT * FROM roles WHERE project_id = ? ORDER BY id", [project_id]
    ).fetchall())


def get_role_rate(role_id, roles, default_rate):
    for r in roles:
        # sqlite rows support indexing by name when using db.execute; but here
        # roles may be dicts (from sqlite_utils .rows). Handle both.
        rid = r["id"] if isinstance(r, dict) else r[0]
        rate = r["day_rate"] if isinstance(r, dict) else r[2]
        if rid == role_id:
            return rate
    return default_rate


def _roles_as_dicts(project_id: int):
    """Return roles as plain dicts — the template & role-rate lookups want this shape."""
    db = get_db()
    rows = list(db.execute(
        "SELECT id, project_id, name, day_rate FROM roles WHERE project_id = ? ORDER BY id",
        [project_id],
    ).fetchall())
    return [{"id": r[0], "project_id": r[1], "name": r[2], "day_rate": r[3]} for r in rows]


def build_feature_data(project_id: int, feature_id: Optional[int] = None):
    db = get_db()
    project = get_project(project_id)
    roles = _roles_as_dicts(project_id)
    default_role_rate = get_role_rate(project["default_role_id"], roles, 0)

    sel = "SELECT id, name, sort_order, started FROM features"
    if feature_id:
        features_rows = list(db.execute(
            f"{sel} WHERE id = ? AND project_id = ?",
            [feature_id, project_id],
        ).fetchall())
    else:
        features_rows = list(db.execute(
            f"{sel} WHERE project_id = ? ORDER BY sort_order, id",
            [project_id],
        ).fetchall())

    enriched_features = []
    for f in features_rows:
        fdict = {"id": f[0], "name": f[1], "sort_order": f[2], "started": f[3] if len(f) > 3 else 0}
        reqs = list(db.execute(
            "SELECT * FROM requirements WHERE feature_id = ? ORDER BY sort_order, id", [fdict["id"]]
        ).fetchall())

        enriched_reqs = []
        for r in reqs:
            rdict = {"id": r[0], "feature_id": r[1], "name": r[2], "sort_order": r[3]}
            dels = list(db.execute(
                "SELECT * FROM deliverables WHERE requirement_id = ? ORDER BY sort_order, id",
                [rdict["id"]],
            ).fetchall())
            enriched_dels = []
            for d in dels:
                ddict = {
                    "id": d[0], "requirement_id": d[1], "name": d[2],
                    "budget_days": d[3], "percent_complete": d[4],
                    "priority": d[5], "role_id": d[6], "sort_order": d[7],
                }
                rate = get_role_rate(ddict["role_id"], roles, default_role_rate)
                enriched_dels.append(deliverable_summary(ddict, rate))

            enriched_reqs.append(requirement_summary(rdict, enriched_dels, default_role_rate))

        enriched_features.append(feature_summary(fdict, enriched_reqs))

    return enriched_features, project, roles, default_role_rate


def _dashboard_counts(project_id: int):
    """Counts used for topbar nav badges."""
    db = get_db()
    feat_count = db.execute(
        "SELECT COUNT(*) FROM features WHERE project_id = ?", [project_id]
    ).fetchone()[0]
    open_risks = db.execute(
        "SELECT COUNT(*) FROM risks WHERE project_id = ? AND status != 'done'",
        [project_id],
    ).fetchone()[0]
    open_notes = db.execute(
        "SELECT COUNT(*) FROM pm_notes WHERE project_id = ? AND status != 'done'",
        [project_id],
    ).fetchone()[0]
    return {"features": feat_count, "risks": open_risks, "notes": open_notes}


def _project_shell_meta(project_id: int):
    """Summary meta used by sidebar project list (completion %, status)."""
    db = get_db()
    # Use features' weighted completion for a project's completion
    rows = list(db.execute(
        "SELECT f.id FROM features f WHERE f.project_id = ?", [project_id]
    ).fetchall())
    if not rows:
        return {"completion": 0, "status": "todo"}
    features, _, _, _ = build_feature_data(project_id)
    total_days = sum(f["total_days"] for f in features)
    if total_days <= 0:
        return {"completion": 0, "status": "todo"}
    completion = sum(f["total_days"] * f["weighted_completion"] for f in features) / total_days
    status = "done" if completion >= 100 else ("doing" if completion > 0 else "todo")
    return {"completion": round(completion), "status": status}


def shell_context(project_id: Optional[int]) -> dict:
    """Common context for base.html: sidebar project list + per-project counts."""
    db = get_db()
    proj_rows = [dict(r) for r in db["projects"].rows]
    projects_list = []
    for pr in proj_rows:
        meta = _project_shell_meta(pr["id"])
        projects_list.append({
            "id": pr["id"],
            "name": pr["name"],
            "description": pr.get("description", ""),
            "completion": meta["completion"],
            "status": meta["status"],
        })

    active_project = None
    counts = {"features": 0, "risks": 0, "notes": 0}
    if project_id is not None:
        active_project = get_project(project_id)
        counts = _dashboard_counts(project_id)

    return {
        "projects_list": projects_list,
        "active_project": active_project,
        "active_project_id": project_id,
        "nav_counts": counts,
    }


# ── Cross-project dashboard ──

@app.get("/")
def cross_project_dashboard(request: Request):
    ctx = {"request": request, "active": "all", "active_page": "all_projects"}
    ctx.update(shell_context(None))
    return templates.TemplateResponse(request, "cross_project.html", ctx)


# ── Project CRUD ──

@app.post("/projects/add")
def add_project(name: str = Form(...), description: str = Form("")):
    db = get_db()
    pid = db["projects"].insert({
        "name": name or "New Project",
        "description": description,
        "start_date": "",
        "as_of_date": "",
        "initial_budget": 0.0,
        "team_size": 1,
        "actual_spend": 0.0,
        "default_role_id": 0,
        "health_on_track_pct": 100.0,
        "health_at_risk_pct": 80.0,
    }).last_pk
    seed_project_defaults(pid)
    return RedirectResponse(f"/p/{pid}/settings", status_code=303)


@app.post("/projects/{project_id}/delete")
def delete_project(project_id: int):
    db = get_db()
    # Guard: never delete the last project.
    count = db["projects"].count
    if count <= 1:
        return RedirectResponse(f"/p/{project_id}/settings", status_code=303)
    # Cascade delete child rows.
    # Collect feature ids for requirement/deliverable cleanup.
    feat_ids = [r[0] for r in db.execute(
        "SELECT id FROM features WHERE project_id = ?", [project_id]
    ).fetchall()]
    if feat_ids:
        placeholders = ",".join("?" * len(feat_ids))
        req_ids = [r[0] for r in db.execute(
            f"SELECT id FROM requirements WHERE feature_id IN ({placeholders})", feat_ids
        ).fetchall()]
        if req_ids:
            rp = ",".join("?" * len(req_ids))
            db.execute(f"DELETE FROM deliverables WHERE requirement_id IN ({rp})", req_ids)
            db.execute(f"DELETE FROM requirements WHERE id IN ({rp})", req_ids)
    # Collect risk ids for risk_features cleanup.
    risk_ids = [r[0] for r in db.execute(
        "SELECT id FROM risks WHERE project_id = ?", [project_id]
    ).fetchall()]
    if risk_ids:
        rip = ",".join("?" * len(risk_ids))
        db.execute(f"DELETE FROM risk_features WHERE risk_id IN ({rip})", risk_ids)

    for tbl in PROJECT_SCOPED_TABLES:
        db.execute(f"DELETE FROM {tbl} WHERE project_id = ?", [project_id])
    db["projects"].delete(project_id)
    return RedirectResponse("/", status_code=303)


# ── Dashboard ──

@app.get("/p/{project_id}/")
@app.get("/p/{project_id}")
def dashboard(request: Request, project_id: int):
    db = get_db()
    features, project, roles, default_rate = build_feature_data(project_id)
    adj_rows = list(db.execute(
        "SELECT * FROM budget_adjustments WHERE project_id = ? ORDER BY date", [project_id]
    ).fetchall())
    adjustments = [
        {"id": r[0], "amount": r[1], "date": r[2], "description": r[3]} for r in adj_rows
    ] if adj_rows and len(adj_rows[0]) == 4 else [dict(r) for r in db["budget_adjustments"].rows_where("project_id = ?", [project_id])]
    overhead_rows = list(db["overheads"].rows_where("project_id = ?", [project_id]))
    overheads = [dict(r) for r in overhead_rows]
    overhead_total = sum(o["amount"] for o in overheads)

    risk_rows = db.execute(
        "SELECT status, impact_days, realised_percentage FROM risks WHERE project_id = ?",
        [project_id],
    ).fetchall()
    open_risks = [r for r in risk_rows if r[0] != "done"]
    closed_risks = [r for r in risk_rows if r[0] == "done"]

    realised_risk_days = sum(
        effective_impact_days(r[1], r[2] or 0.0) for r in risk_rows
    )
    realised_risk_dollars = realised_risk_days * default_rate
    open_exposure_days = sum(
        unrealised_exposure_days(r[1], r[0], r[2] or 0.0) for r in risk_rows
    )
    open_risk_dollars = open_exposure_days * default_rate

    summary = project_summary(
        project, features, adjustments, default_rate,
        realised_risk_dollars=realised_risk_dollars,
        overhead_dollars=overhead_total,
        open_risk_dollars=open_risk_dollars,
    )

    on_track_pct = project.get("health_on_track_pct", 100.0)
    at_risk_pct = project.get("health_at_risk_pct", 80.0)

    started_features = [f for f in features if f.get("started", 0) and f["total_days"] > 0]
    started_total_days = sum(f["total_days"] for f in started_features)
    if started_total_days > 0:
        started_completion = sum(
            f["total_days"] * f["weighted_completion"] for f in started_features
        ) / started_total_days
    else:
        started_completion = 0

    total_feature_days = sum(f["total_days"] for f in features if f["total_days"] > 0)
    feature_burn_pct = summary["feature_expected_burn_pct"]
    if started_total_days > 0 and total_feature_days > 0:
        started_adjusted_target = min(
            100.0,
            feature_burn_pct * total_feature_days / started_total_days,
        )
    else:
        started_adjusted_target = feature_burn_pct

    for f in features:
        effective_target = (
            started_adjusted_target if (f.get("started", 0) and f["total_days"] > 0)
            else feature_burn_pct
        )
        f["health"] = feature_health(f, effective_target, on_track_pct, at_risk_pct)

    summary["started_completion"] = started_completion
    summary["started_feature_count"] = len(started_features)
    summary["total_feature_count"] = len([f for f in features if f["total_dollars"] > 0])

    avoided = sum(r[1] for r in closed_risks if (r[2] or 0.0) == 0)
    current_budget = summary["current_budget"]
    open_risk_pct = min(100.0, open_risk_dollars / current_budget * 100) if current_budget else 0.0
    locked_risk_pct = min(100.0 - open_risk_pct, realised_risk_dollars / current_budget * 100) if current_budget else 0.0
    daily_burn = summary["daily_burn"]
    open_impact_budget_days = open_risk_dollars / daily_burn if daily_burn else 0.0
    risk_summary = {
        "open_count": len(open_risks),
        "done_count": len(closed_risks),
        "open_impact_days": open_exposure_days,
        "open_impact_dollars": open_risk_dollars,
        "open_impact_budget_days": open_impact_budget_days,
        "effective_impact_days": realised_risk_days,
        "effective_impact_dollars": realised_risk_dollars,
        "avoided_days": avoided,
        "effective_impact_pct": min(100.0, realised_risk_dollars / current_budget * 100) if current_budget else 0.0,
        "open_impact_pct": open_risk_pct,
        "open_risk_pct": round(open_risk_pct, 1),
        "locked_risk_pct": round(locked_risk_pct, 1),
    }

    as_of = parse_date(project.get("as_of_date", ""))
    end_dt = parse_date(project.get("end_date", ""))
    cap_rows = list(db.execute(
        "SELECT cp.id, cp.week_start_date, cp.role_id, cp.team_size, "
        "COALESCE(r.name, 'Default') as role_name, "
        "COALESCE(r.day_rate, ?) as day_rate "
        "FROM capacity_periods cp "
        "LEFT JOIN roles r ON cp.role_id = r.id "
        "WHERE cp.project_id = ? "
        "ORDER BY cp.week_start_date",
        [default_rate, project_id]
    ).fetchall())
    enriched_capacity = [
        {
            "id": row[0],
            "week_start_date": row[1],
            "week_monday": parse_date(row[1]),
            "role_id": row[2],
            "team_size": row[3],
            "role_name": row[4],
            "day_rate": row[5],
        }
        for row in cap_rows
    ]
    cap_summary = capacity_plan_summary(
        as_of or _date.today(),
        end_dt,
        enriched_capacity,
        project.get("team_size", 1),
        summary["daily_burn"],
    )
    remaining_budget = summary["accessible_budget"] - summary["actual_spend"]
    cap_budget = capacity_budget_summary(
        remaining_budget,
        as_of or _date.today(),
        enriched_capacity,
        summary["daily_burn"],
        project.get("team_size", 1),
    )

    as_of_str = project.get("as_of_date", "")
    note_rows = list(db.execute(
        "SELECT id, name, description, status, due_date FROM pm_notes "
        "WHERE project_id = ? ORDER BY sort_order, id", [project_id]
    ).fetchall())
    sticky_notes = []
    dated_notes = []
    aof = parse_date(as_of_str)
    for nr in note_rows:
        nstatus = nr[3]
        if nstatus == "done":
            continue
        note_dict = {"id": nr[0], "name": nr[1], "description": nr[2], "status": nstatus, "due_date": nr[4]}
        if nstatus == "sticky":
            sticky_notes.append(note_dict)
            continue
        ndue = parse_date(nr[4])
        if aof and ndue and (ndue <= aof or ndue <= aof + timedelta(days=14)):
            dated_notes.append(note_dict)
    dated_notes.sort(key=lambda n: n["due_date"] or "9999-99-99")
    dashboard_notes = sticky_notes + dated_notes
    notes_overflow = max(0, len(dashboard_notes) - 3)
    dashboard_notes = dashboard_notes[:3]

    ctx = {
        "request": request,
        "active": "dashboard",
        "active_page": "dashboard",
        "project": project,
        "features": features,
        "adjustments": adjustments,
        "overheads": overheads,
        "summary": summary,
        "roles": roles,
        "risk_summary": risk_summary,
        "cap_summary": cap_summary,
        "cap_budget": cap_budget,
        "dashboard_notes": dashboard_notes,
        "notes_overflow": notes_overflow,
    }
    ctx.update(shell_context(project_id))
    return templates.TemplateResponse(request, "dashboard.html", ctx)


# ── Settings ──

@app.get("/p/{project_id}/settings")
def settings_page(request: Request, project_id: int):
    db = get_db()
    project = get_project(project_id)
    roles = _roles_as_dicts(project_id)
    adjustments = list(db["budget_adjustments"].rows_where("project_id = ?", [project_id]))
    adjustments = [dict(a) for a in adjustments]
    overheads = [dict(o) for o in db["overheads"].rows_where(
        "project_id = ?", [project_id], order_by="sort_order, id"
    )]
    ctx = {
        "request": request,
        "active": "settings",
        "active_page": "settings",
        "project": project,
        "roles": roles,
        "adjustments": adjustments,
        "overheads": overheads,
    }
    ctx.update(shell_context(project_id))
    return templates.TemplateResponse(request, "settings.html", ctx)


@app.post("/p/{project_id}/settings/project")
def update_project(
    project_id: int,
    name: str = Form(...),
    description: str = Form(""),
    start_date: str = Form(""),
    as_of_date: str = Form(""),
    initial_budget: float = Form(0),
    actual_spend: float = Form(0),
    health_on_track_pct: float = Form(100.0),
    health_at_risk_pct: float = Form(80.0),
):
    db = get_db()
    db["projects"].update(project_id, {
        "name": name,
        "description": description,
        "start_date": start_date,
        "as_of_date": as_of_date,
        "initial_budget": initial_budget,
        "actual_spend": actual_spend,
        "health_on_track_pct": health_on_track_pct,
        "health_at_risk_pct": health_at_risk_pct,
    })
    return RedirectResponse(f"/p/{project_id}/settings", status_code=303)


VALID_ACCENTS = {"cyan","indigo","emerald","mono","violet","rose","amber","forest","plum","slate","coral","teal","lime","ocean","wine"}
VALID_THEMES = {"light", "dark"}

@app.post("/p/{project_id}/settings/visual")
def update_visual(
    project_id: int,
    accent: str = Form("cyan"),
    theme: str = Form("light"),
):
    db = get_db()
    safe_accent = accent if accent in VALID_ACCENTS else "cyan"
    safe_theme = theme if theme in VALID_THEMES else "light"
    db["projects"].update(project_id, {"accent": safe_accent, "theme": safe_theme})
    return RedirectResponse(f"/p/{project_id}/settings#visual", status_code=303)


@app.post("/p/{project_id}/settings/roles/add")
def add_role(project_id: int, name: str = Form(...), day_rate: float = Form(0)):
    db = get_db()
    db["roles"].insert({"project_id": project_id, "name": name, "day_rate": day_rate})
    return RedirectResponse(f"/p/{project_id}/settings", status_code=303)


@app.post("/p/{project_id}/settings/roles/{role_id}/update")
def update_role(project_id: int, role_id: int, name: str = Form(...), day_rate: float = Form(0)):
    db = get_db()
    db["roles"].update(role_id, {"name": name, "day_rate": day_rate})
    return RedirectResponse(f"/p/{project_id}/settings", status_code=303)


@app.post("/p/{project_id}/settings/roles/{role_id}/delete")
def delete_role(project_id: int, role_id: int):
    db = get_db()
    db["roles"].delete(role_id)
    return RedirectResponse(f"/p/{project_id}/settings", status_code=303)


@app.post("/p/{project_id}/settings/adjustments/add")
def add_adjustment(
    project_id: int,
    amount: float = Form(0),
    date: str = Form(""),
    description: str = Form(""),
):
    db = get_db()
    db["budget_adjustments"].insert({
        "project_id": project_id,
        "amount": amount,
        "date": date,
        "description": description,
    })
    return RedirectResponse(f"/p/{project_id}/settings", status_code=303)


@app.post("/p/{project_id}/settings/adjustments/{adj_id}/delete")
def delete_adjustment(project_id: int, adj_id: int):
    db = get_db()
    db["budget_adjustments"].delete(adj_id)
    return RedirectResponse(f"/p/{project_id}/settings", status_code=303)


@app.post("/p/{project_id}/settings/overheads/add")
def add_overhead(
    project_id: int,
    name: str = Form(...),
    description: str = Form(""),
    amount: float = Form(0),
):
    db = get_db()
    max_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) FROM overheads WHERE project_id = ?",
        [project_id],
    ).fetchone()[0]
    db["overheads"].insert({
        "project_id": project_id,
        "name": name,
        "description": description,
        "amount": amount,
        "sort_order": max_order + 1,
    })
    return RedirectResponse(f"/p/{project_id}/settings", status_code=303)


@app.post("/p/{project_id}/settings/overheads/{overhead_id}/update")
def update_overhead(
    project_id: int,
    overhead_id: int,
    name: str = Form(...),
    description: str = Form(""),
    amount: float = Form(0),
):
    db = get_db()
    db["overheads"].update(overhead_id, {
        "name": name,
        "description": description,
        "amount": amount,
    })
    return RedirectResponse(f"/p/{project_id}/settings", status_code=303)


@app.post("/p/{project_id}/settings/overheads/{overhead_id}/delete")
def delete_overhead(project_id: int, overhead_id: int):
    db = get_db()
    db["overheads"].delete(overhead_id)
    return RedirectResponse(f"/p/{project_id}/settings", status_code=303)


# ── Features ──

@app.get("/p/{project_id}/features")
def features_list(request: Request, project_id: int):
    features, project, roles, default_rate = build_feature_data(project_id)
    ctx = {
        "request": request,
        "active": "features",
        "active_page": "features",
        "features": features,
        "project": project,
    }
    ctx.update(shell_context(project_id))
    return templates.TemplateResponse(request, "features.html", ctx)


@app.post("/p/{project_id}/features/{feature_id}/toggle-started")
def toggle_started(project_id: int, feature_id: int):
    db = get_db()
    f = db["features"].get(feature_id)
    db["features"].update(feature_id, {"started": 0 if f.get("started", 0) else 1})
    return RedirectResponse(f"/p/{project_id}/", status_code=303)


@app.post("/api/p/{project_id}/features/{feature_id}/toggle-started")
def api_toggle_started(project_id: int, feature_id: int):
    db = get_db()
    f = db["features"].get(feature_id)
    new_val = 0 if f.get("started", 0) else 1
    db["features"].update(feature_id, {"started": new_val})
    return JSONResponse({"ok": True, "started": new_val})


@app.post("/p/{project_id}/features/add")
def add_feature(project_id: int, name: str = Form(...)):
    db = get_db()
    max_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) FROM features WHERE project_id = ?",
        [project_id],
    ).fetchone()[0]
    db["features"].insert({
        "project_id": project_id,
        "name": name,
        "sort_order": max_order + 1,
        "started": 0,
    })
    return RedirectResponse(f"/p/{project_id}/features", status_code=303)


@app.post("/p/{project_id}/features/{feature_id}/update")
def update_feature(project_id: int, feature_id: int, name: str = Form(...)):
    db = get_db()
    db["features"].update(feature_id, {"name": name})
    return RedirectResponse(f"/p/{project_id}/features/{feature_id}", status_code=303)


@app.post("/p/{project_id}/features/{feature_id}/delete")
def delete_feature(project_id: int, feature_id: int):
    db = get_db()
    reqs = list(db.execute("SELECT id FROM requirements WHERE feature_id = ?", [feature_id]).fetchall())
    for r in reqs:
        db.execute("DELETE FROM deliverables WHERE requirement_id = ?", [r[0]])
    db.execute("DELETE FROM requirements WHERE feature_id = ?", [feature_id])
    db["features"].delete(feature_id)
    return RedirectResponse(f"/p/{project_id}/features", status_code=303)


# ── Feature Detail ──

@app.get("/p/{project_id}/features/{feature_id}")
def feature_detail(request: Request, project_id: int, feature_id: int):
    features, project, roles, default_rate = build_feature_data(project_id, feature_id)
    if not features:
        return RedirectResponse(f"/p/{project_id}/features", status_code=303)
    ctx = {
        "request": request,
        "active": "features",
        "active_page": "features",
        "feature": features[0],
        "project": project,
        "roles": roles,
    }
    ctx.update(shell_context(project_id))
    return templates.TemplateResponse(request, "feature_detail.html", ctx)


# ── Requirements ──

@app.post("/p/{project_id}/features/{feature_id}/requirements/add")
def add_requirement(project_id: int, feature_id: int, name: str = Form(...)):
    db = get_db()
    max_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) FROM requirements WHERE feature_id = ?", [feature_id]
    ).fetchone()[0]
    db["requirements"].insert({"feature_id": feature_id, "name": name, "sort_order": max_order + 1})
    return RedirectResponse(f"/p/{project_id}/features/{feature_id}", status_code=303)


@app.post("/p/{project_id}/requirements/{req_id}/update")
def update_requirement(project_id: int, req_id: int, name: str = Form(...)):
    db = get_db()
    req = db["requirements"].get(req_id)
    db["requirements"].update(req_id, {"name": name})
    return RedirectResponse(f"/p/{project_id}/features/{req['feature_id']}", status_code=303)


@app.post("/p/{project_id}/requirements/{req_id}/delete")
def delete_requirement(project_id: int, req_id: int):
    db = get_db()
    req = db["requirements"].get(req_id)
    feature_id = req["feature_id"]
    db.execute("DELETE FROM deliverables WHERE requirement_id = ?", [req_id])
    db["requirements"].delete(req_id)
    return RedirectResponse(f"/p/{project_id}/features/{feature_id}", status_code=303)


# ── Deliverables ──

@app.post("/p/{project_id}/requirements/{req_id}/deliverables/add")
def add_deliverable(
    project_id: int,
    req_id: int,
    name: str = Form(...),
    budget_days: float = Form(0),
    priority: str = Form("Must Have"),
    role_id: Optional[int] = Form(None),
):
    db = get_db()
    req = db["requirements"].get(req_id)
    max_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) FROM deliverables WHERE requirement_id = ?", [req_id]
    ).fetchone()[0]
    db["deliverables"].insert({
        "requirement_id": req_id,
        "name": name,
        "budget_days": budget_days,
        "percent_complete": 0,
        "priority": priority,
        "role_id": role_id,
        "sort_order": max_order + 1,
    })
    return RedirectResponse(f"/p/{project_id}/features/{req['feature_id']}", status_code=303)


@app.post("/p/{project_id}/deliverables/{del_id}/update")
def update_deliverable(
    project_id: int,
    del_id: int,
    name: str = Form(...),
    budget_days: float = Form(0),
    percent_complete: int = Form(0),
    priority: str = Form("Must Have"),
    role_id: Optional[int] = Form(None),
):
    db = get_db()
    d = db["deliverables"].get(del_id)
    req = db["requirements"].get(d["requirement_id"])
    db["deliverables"].update(del_id, {
        "name": name,
        "budget_days": budget_days,
        "percent_complete": max(0, min(100, percent_complete)),
        "priority": priority,
        "role_id": role_id if role_id else None,
    })
    return RedirectResponse(f"/p/{project_id}/features/{req['feature_id']}", status_code=303)


@app.post("/api/p/{project_id}/deliverables/{del_id}/percent")
def update_percent(project_id: int, del_id: int, percent_complete: int = Form(0)):
    db = get_db()
    db["deliverables"].update(del_id, {"percent_complete": max(0, min(100, percent_complete))})
    d = db["deliverables"].get(del_id)
    req = db["requirements"].get(d["requirement_id"])
    return JSONResponse({"ok": True, "feature_id": req["feature_id"]})


@app.post("/api/p/{project_id}/deliverables/{del_id}/update")
def api_update_deliverable(
    project_id: int,
    del_id: int,
    name: str = Form(...),
    budget_days: float = Form(0),
    percent_complete: int = Form(0),
    priority: str = Form("Must Have"),
    role_id: Optional[int] = Form(None),
):
    db = get_db()
    db["deliverables"].update(del_id, {
        "name": name,
        "budget_days": budget_days,
        "percent_complete": max(0, min(100, percent_complete)),
        "priority": priority,
        "role_id": role_id if role_id else None,
    })
    return JSONResponse({"ok": True})


@app.post("/p/{project_id}/deliverables/{del_id}/delete")
def delete_deliverable(project_id: int, del_id: int):
    db = get_db()
    d = db["deliverables"].get(del_id)
    req = db["requirements"].get(d["requirement_id"])
    feature_id = req["feature_id"]
    db["deliverables"].delete(del_id)
    return RedirectResponse(f"/p/{project_id}/features/{feature_id}", status_code=303)


# ── Risks ──

def _severity_band(risk: dict) -> str:
    score = risk["effective_impact_days"] + 0.5 * risk["unrealised_days"]
    if score <= 0:
        return "none"
    if score >= 5:
        return "high"
    if score >= 2:
        return "med"
    return "low"


def _sort_risks(risks: list, sort_key: str) -> list:
    if sort_key == "impact":
        return sorted(risks, key=lambda r: -r["impact_days"])
    if sort_key == "age":
        today = _date.today()
        def _age(r):
            d = parse_date(r["date_identified"])
            return (today - d).days if d else -1
        return sorted(risks, key=lambda r: -_age(r))
    if sort_key == "name":
        return sorted(risks, key=lambda r: r["name"].lower())
    status_order = {"todo": 0, "doing": 1, "done": 2}
    return sorted(risks, key=lambda r: (status_order.get(r["status"], 3), r["sort_order"]))


@app.get("/p/{project_id}/risks")
def risks_page(request: Request, project_id: int, sort: str = "status", filter: str = "all"):
    db = get_db()
    project = get_project(project_id)
    roles = _roles_as_dicts(project_id)
    default_role_rate = get_role_rate(project["default_role_id"], roles, 0)
    risks = list(db.execute(
        "SELECT id, name, description, status, due_date, impact_days, sort_order, "
        "realised_percentage, resultant_work, timeline_impact_days, date_identified "
        "FROM risks WHERE project_id = ? ORDER BY sort_order, id",
        [project_id],
    ).fetchall())
    features_rows = list(db.execute(
        "SELECT id, name FROM features WHERE project_id = ? ORDER BY sort_order, id",
        [project_id],
    ).fetchall())
    all_features = [{"id": f[0], "name": f[1]} for f in features_rows]

    enriched_risks = []
    for r in risks:
        rdict = {
            "id": r[0], "name": r[1], "description": r[2], "status": r[3],
            "due_date": r[4], "impact_days": r[5], "sort_order": r[6],
            "realised_percentage": r[7] or 0.0,
            "resultant_work": r[8] or "",
            "timeline_impact_days": r[9] or 0.0,
            "date_identified": r[10] or "",
        }
        rdict["impact_dollars"] = rdict["impact_days"] * default_role_rate
        rdict["effective_impact_days"] = effective_impact_days(
            rdict["impact_days"], rdict["realised_percentage"]
        )
        rdict["effective_impact_dollars"] = rdict["effective_impact_days"] * default_role_rate
        rdict["unrealised_days"] = unrealised_exposure_days(
            rdict["impact_days"], rdict["status"], rdict["realised_percentage"]
        )
        rdict["unrealised_dollars"] = rdict["unrealised_days"] * default_role_rate
        rdict["resolution_label"] = resolution_label(rdict["status"], rdict["realised_percentage"])
        rdict["severity_band"] = _severity_band(rdict)
        links = list(db.execute(
            "SELECT f.id, f.name FROM risk_features rf JOIN features f ON rf.feature_id = f.id WHERE rf.risk_id = ?",
            [rdict["id"]]
        ).fetchall())
        rdict["linked_features"] = [{"id": l[0], "name": l[1]} for l in links]
        enriched_risks.append(rdict)

    todo_count = sum(1 for r in enriched_risks if r["status"] == "todo")
    doing_count = sum(1 for r in enriched_risks if r["status"] == "doing")
    done_count = sum(1 for r in enriched_risks if r["status"] == "done")
    open_impact_days = sum(r["unrealised_days"] for r in enriched_risks)
    open_impact_dollars = open_impact_days * default_role_rate
    effective_impact_days_total = sum(r["effective_impact_days"] for r in enriched_risks)
    effective_impact_dollars_total = effective_impact_days_total * default_role_rate
    avoided_days = sum(
        r["impact_days"] for r in enriched_risks
        if r["status"] == "done" and r["realised_percentage"] == 0
    )

    if filter == "open":
        visible_risks = [r for r in enriched_risks if r["status"] != "done"]
    elif filter == "closed":
        visible_risks = [r for r in enriched_risks if r["status"] == "done"]
    else:
        visible_risks = list(enriched_risks)
    visible_risks = _sort_risks(visible_risks, sort)

    ctx = {
        "request": request,
        "active": "risks",
        "active_page": "risks",
        "project": project,
        "risks": visible_risks,
        "all_features": all_features,
        "summary": {
            "todo": todo_count,
            "doing": doing_count,
            "done": done_count,
            "open_impact_days": open_impact_days,
            "open_impact_dollars": open_impact_dollars,
            "effective_impact_days": effective_impact_days_total,
            "effective_impact_dollars": effective_impact_dollars_total,
            "avoided_days": avoided_days,
        },
        "default_rate": default_role_rate,
        "sort_key": sort,
        "filter_key": filter,
    }
    ctx.update(shell_context(project_id))
    return templates.TemplateResponse(request, "risks.html", ctx)


def _clamp_pct(value: float) -> float:
    return max(0.0, min(100.0, value))


@app.post("/p/{project_id}/risks/add")
def add_risk(
    project_id: int,
    name: str = Form(...),
    description: str = Form(""),
    status: str = Form("todo"),
    date_identified: str = Form(""),
    due_date: str = Form(""),
    impact_days: float = Form(0),
    timeline_impact_days: float = Form(0),
    realised_percentage: float = Form(0.0),
    resultant_work: str = Form(""),
):
    db = get_db()
    max_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) FROM risks WHERE project_id = ?",
        [project_id],
    ).fetchone()[0]
    if not date_identified:
        date_identified = _date.today().isoformat()
    db["risks"].insert({
        "project_id": project_id,
        "name": name,
        "description": description,
        "status": status,
        "date_identified": date_identified,
        "due_date": due_date,
        "impact_days": impact_days,
        "timeline_impact_days": timeline_impact_days,
        "sort_order": max_order + 1,
        "realised_percentage": _clamp_pct(realised_percentage),
        "resultant_work": resultant_work,
    })
    return RedirectResponse(f"/p/{project_id}/risks", status_code=303)


@app.post("/p/{project_id}/risks/{risk_id}/update")
def update_risk(
    project_id: int,
    risk_id: int,
    name: str = Form(...),
    description: str = Form(""),
    status: str = Form("todo"),
    date_identified: str = Form(""),
    due_date: str = Form(""),
    impact_days: float = Form(0),
    timeline_impact_days: float = Form(0),
    realised_percentage: float = Form(0.0),
    resultant_work: str = Form(""),
):
    db = get_db()
    db["risks"].update(risk_id, {
        "name": name,
        "description": description,
        "status": status,
        "date_identified": date_identified,
        "due_date": due_date,
        "impact_days": impact_days,
        "timeline_impact_days": timeline_impact_days,
        "realised_percentage": _clamp_pct(realised_percentage),
        "resultant_work": resultant_work,
    })
    return RedirectResponse(f"/p/{project_id}/risks", status_code=303)


@app.post("/p/{project_id}/risks/{risk_id}/delete")
def delete_risk(project_id: int, risk_id: int):
    db = get_db()
    db.execute("DELETE FROM risk_features WHERE risk_id = ?", [risk_id])
    db["risks"].delete(risk_id)
    return RedirectResponse(f"/p/{project_id}/risks", status_code=303)


@app.post("/api/p/{project_id}/risks/{risk_id}/status")
def update_risk_status(project_id: int, risk_id: int, status: str = Form("todo")):
    if status not in ("todo", "doing", "done"):
        return JSONResponse({"ok": False, "error": "invalid status"})
    db = get_db()
    db["risks"].update(risk_id, {"status": status})
    return JSONResponse({"ok": True, "status": status})


@app.post("/api/p/{project_id}/risks/{risk_id}/realised")
def update_risk_realised(project_id: int, risk_id: int, realised_percentage: float = Form(0.0)):
    db = get_db()
    db["risks"].update(risk_id, {"realised_percentage": _clamp_pct(realised_percentage)})
    return JSONResponse({"ok": True, "realised_percentage": _clamp_pct(realised_percentage)})


@app.post("/p/{project_id}/risks/{risk_id}/link-feature")
def link_feature_to_risk(project_id: int, risk_id: int, feature_id: int = Form(...)):
    db = get_db()
    existing = db.execute(
        "SELECT COUNT(*) FROM risk_features WHERE risk_id = ? AND feature_id = ?",
        [risk_id, feature_id]
    ).fetchone()[0]
    if not existing:
        db["risk_features"].insert({"risk_id": risk_id, "feature_id": feature_id})
    return RedirectResponse(f"/p/{project_id}/risks", status_code=303)


@app.post("/p/{project_id}/risks/{risk_id}/unlink-feature/{feature_id}")
def unlink_feature_from_risk(project_id: int, risk_id: int, feature_id: int):
    db = get_db()
    db.execute(
        "DELETE FROM risk_features WHERE risk_id = ? AND feature_id = ?",
        [risk_id, feature_id]
    )
    return RedirectResponse(f"/p/{project_id}/risks", status_code=303)


# ── PM Notes ──

@app.get("/p/{project_id}/pm-notes")
def pm_notes_page(request: Request, project_id: int, filter: str = "all"):
    db = get_db()
    project = get_project(project_id)
    notes = list(db.execute(
        "SELECT id, name, description, status, due_date, sort_order "
        "FROM pm_notes WHERE project_id = ? ORDER BY "
        "CASE status WHEN 'sticky' THEN 0 WHEN 'todo' THEN 1 WHEN 'doing' THEN 2 ELSE 3 END, "
        "due_date ASC, sort_order, id", [project_id]
    ).fetchall())
    enriched = [
        {"id": r[0], "name": r[1], "description": r[2], "status": r[3], "due_date": r[4], "sort_order": r[5]}
        for r in notes
    ]
    counts = {
        "todo": sum(1 for n in enriched if n["status"] == "todo"),
        "doing": sum(1 for n in enriched if n["status"] == "doing"),
        "done": sum(1 for n in enriched if n["status"] == "done"),
        "sticky": sum(1 for n in enriched if n["status"] == "sticky"),
    }
    visible = enriched if filter not in ("sticky", "todo", "doing", "done") else [
        n for n in enriched if n["status"] == filter
    ]
    ctx = {
        "request": request,
        "active": "pm_notes",
        "active_page": "pm_notes",
        "project": project,
        "notes": visible,
        "counts": counts,
        "filter_key": filter,
    }
    ctx.update(shell_context(project_id))
    return templates.TemplateResponse(request, "pm_notes.html", ctx)


@app.post("/p/{project_id}/pm-notes/add")
def add_note(
    project_id: int,
    name: str = Form(...),
    description: str = Form(""),
    status: str = Form("todo"),
    due_date: str = Form(""),
):
    db = get_db()
    max_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) FROM pm_notes WHERE project_id = ?",
        [project_id],
    ).fetchone()[0]
    db["pm_notes"].insert({
        "project_id": project_id,
        "name": name,
        "description": description,
        "status": status,
        "due_date": due_date if status != "sticky" else "",
        "sort_order": max_order + 1,
    })
    return RedirectResponse(f"/p/{project_id}/pm-notes", status_code=303)


@app.post("/p/{project_id}/pm-notes/{note_id}/update")
def update_note(
    project_id: int,
    note_id: int,
    name: str = Form(...),
    description: str = Form(""),
    status: str = Form("todo"),
    due_date: str = Form(""),
):
    db = get_db()
    db["pm_notes"].update(note_id, {
        "name": name,
        "description": description,
        "status": status,
        "due_date": due_date if status != "sticky" else "",
    })
    return RedirectResponse(f"/p/{project_id}/pm-notes", status_code=303)


@app.post("/p/{project_id}/pm-notes/{note_id}/delete")
def delete_note(project_id: int, note_id: int):
    db = get_db()
    db["pm_notes"].delete(note_id)
    return RedirectResponse(f"/p/{project_id}/pm-notes", status_code=303)


# ── Capacity Planning ──

@app.get("/p/{project_id}/capacity")
def capacity_page(request: Request, project_id: int):
    db = get_db()
    project = get_project(project_id)
    roles = _roles_as_dicts(project_id)
    default_rate = get_role_rate(project["default_role_id"], roles, 0)

    rows = list(db.execute(
        "SELECT cp.id, cp.week_start_date, cp.role_id, cp.team_size, "
        "COALESCE(r.name, 'Default') as role_name, "
        "COALESCE(r.day_rate, ?) as day_rate "
        "FROM capacity_periods cp "
        "LEFT JOIN roles r ON cp.role_id = r.id "
        "WHERE cp.project_id = ? "
        "ORDER BY cp.week_start_date, cp.id",
        [default_rate, project_id]
    ).fetchall())

    weeks: dict = {}
    for row in rows:
        wdate = row[1]
        if wdate not in weeks:
            weeks[wdate] = []
        weeks[wdate].append({
            "id": row[0],
            "week_start_date": row[1],
            "role_id": row[2],
            "team_size": row[3],
            "role_name": row[4],
            "day_rate": row[5],
        })

    ctx = {
        "request": request,
        "active": "capacity",
        "active_page": "capacity",
        "project": project,
        "roles": roles,
        "weeks": weeks,
    }
    ctx.update(shell_context(project_id))
    return templates.TemplateResponse(request, "capacity.html", ctx)


@app.post("/p/{project_id}/capacity/add")
def add_capacity_period(
    project_id: int,
    week_start_date: str = Form(...),
    role_id: Optional[int] = Form(None),
    team_size: int = Form(1),
):
    db = get_db()
    try:
        d = _date.fromisoformat(week_start_date)
        monday = d - timedelta(days=d.weekday())
    except ValueError:
        return RedirectResponse(f"/p/{project_id}/capacity", status_code=303)
    db["capacity_periods"].insert({
        "project_id": project_id,
        "week_start_date": monday.isoformat(),
        "role_id": role_id,
        "team_size": max(0, team_size),
    })
    return RedirectResponse(f"/p/{project_id}/capacity", status_code=303)


@app.post("/p/{project_id}/capacity/{period_id}/delete")
def delete_capacity_period(project_id: int, period_id: int):
    db = get_db()
    db["capacity_periods"].delete(period_id)
    return RedirectResponse(f"/p/{project_id}/capacity", status_code=303)


@app.post("/p/{project_id}/capacity/defaults")
def update_capacity_defaults(
    project_id: int,
    team_size: int = Form(1),
    default_role_id: int = Form(1),
):
    db = get_db()
    db["projects"].update(project_id, {
        "team_size": max(1, team_size),
        "default_role_id": default_role_id,
    })
    return RedirectResponse(f"/p/{project_id}/capacity", status_code=303)


# ── Export / Import (scoped to active project) ──

EXPORT_TABLES = [
    "projects", "roles", "budget_adjustments", "features", "requirements",
    "deliverables", "risks", "risk_features", "overheads", "pm_notes",
    "capacity_periods",
]


def _scoped_rows(db, table: str, project_id: int, feature_ids: list, risk_ids: list):
    """Rows of a table belonging to the given project."""
    if table == "projects":
        return list(db.execute("SELECT * FROM projects WHERE id = ?", [project_id]).fetchall())
    if table == "requirements":
        if not feature_ids:
            return []
        placeholders = ",".join("?" * len(feature_ids))
        return list(db.execute(
            f"SELECT * FROM requirements WHERE feature_id IN ({placeholders})",
            feature_ids,
        ).fetchall())
    if table == "deliverables":
        if not feature_ids:
            return []
        placeholders = ",".join("?" * len(feature_ids))
        return list(db.execute(
            f"SELECT * FROM deliverables WHERE requirement_id IN "
            f"(SELECT id FROM requirements WHERE feature_id IN ({placeholders}))",
            feature_ids,
        ).fetchall())
    if table == "risk_features":
        if not risk_ids:
            return []
        placeholders = ",".join("?" * len(risk_ids))
        return list(db.execute(
            f"SELECT * FROM risk_features WHERE risk_id IN ({placeholders})",
            risk_ids,
        ).fetchall())
    # default: project-scoped table
    return list(db.execute(
        f"SELECT * FROM {table} WHERE project_id = ?", [project_id]
    ).fetchall())


@app.get("/p/{project_id}/export")
def export_csv(project_id: int):
    db = get_db()
    project = get_project(project_id)
    buf = io.BytesIO()
    project_name = project["name"].replace(" ", "_").replace("/", "-")
    filename = f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    feat_ids = [r[0] for r in db.execute(
        "SELECT id FROM features WHERE project_id = ?", [project_id]
    ).fetchall()]
    risk_ids = [r[0] for r in db.execute(
        "SELECT id FROM risks WHERE project_id = ?", [project_id]
    ).fetchall()]

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for table_name in EXPORT_TABLES:
            if table_name not in db.table_names():
                continue
            rows = _scoped_rows(db, table_name, project_id, feat_ids, risk_ids)
            if not rows:
                continue
            # Get column names
            col_names = [c.name for c in db[table_name].columns]
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=col_names)
            writer.writeheader()
            for row in rows:
                writer.writerow({col_names[i]: row[i] for i in range(len(col_names))})
            zf.writestr(f"{table_name}.csv", output.getvalue())

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/p/{project_id}/import")
async def import_csv(project_id: int, file: UploadFile = File(...)):
    """Import a zip into the active project. Overwrites the project's existing
    rows; other projects' data is untouched. Primary keys in the import are
    remapped so IDs don't collide with existing rows in other projects.
    """
    db = get_db()
    content = await file.read()
    buf = io.BytesIO(content)

    # Wipe just this project's existing rows (mirror the logic in delete_project)
    feat_ids = [r[0] for r in db.execute(
        "SELECT id FROM features WHERE project_id = ?", [project_id]
    ).fetchall()]
    if feat_ids:
        placeholders = ",".join("?" * len(feat_ids))
        req_ids = [r[0] for r in db.execute(
            f"SELECT id FROM requirements WHERE feature_id IN ({placeholders})", feat_ids
        ).fetchall()]
        if req_ids:
            rp = ",".join("?" * len(req_ids))
            db.execute(f"DELETE FROM deliverables WHERE requirement_id IN ({rp})", req_ids)
            db.execute(f"DELETE FROM requirements WHERE id IN ({rp})", req_ids)
    risk_ids = [r[0] for r in db.execute(
        "SELECT id FROM risks WHERE project_id = ?", [project_id]
    ).fetchall()]
    if risk_ids:
        rip = ",".join("?" * len(risk_ids))
        db.execute(f"DELETE FROM risk_features WHERE risk_id IN ({rip})", risk_ids)
    for tbl in PROJECT_SCOPED_TABLES:
        db.execute(f"DELETE FROM {tbl} WHERE project_id = ?", [project_id])

    # Parse zip.
    with zipfile.ZipFile(buf, "r") as zf:
        csv_data = {}
        for table_name in EXPORT_TABLES:
            csv_filename = f"{table_name}.csv"
            if csv_filename not in zf.namelist():
                continue
            csv_data[table_name] = list(csv.DictReader(
                io.StringIO(zf.read(csv_filename).decode("utf-8"))
            ))

        def _coerce(v):
            if v == "" or v is None:
                return None
            try:
                return float(v) if "." in v else int(v)
            except (ValueError, TypeError):
                return v

        # ID remapping tables: old_id → new_id
        role_map = {}
        feature_map = {}
        req_map = {}

        # Re-import roles (assign new ids, track map)
        for row in csv_data.get("roles", []):
            old_id = row.get("id")
            cleaned = {k: _coerce(v) for k, v in row.items() if k != "id"}
            cleaned["project_id"] = project_id
            new_id = db["roles"].insert(cleaned).last_pk
            if old_id:
                role_map[str(old_id)] = new_id

        # budget_adjustments, overheads, pm_notes, capacity_periods — simple scoped inserts
        for row in csv_data.get("budget_adjustments", []):
            cleaned = {k: _coerce(v) for k, v in row.items() if k != "id"}
            cleaned["project_id"] = project_id
            db["budget_adjustments"].insert(cleaned)

        for row in csv_data.get("overheads", []):
            cleaned = {k: _coerce(v) for k, v in row.items() if k != "id"}
            cleaned["project_id"] = project_id
            db["overheads"].insert(cleaned)

        for row in csv_data.get("pm_notes", []):
            cleaned = {k: _coerce(v) for k, v in row.items() if k != "id"}
            cleaned["project_id"] = project_id
            db["pm_notes"].insert(cleaned)

        # features (remap id)
        for row in csv_data.get("features", []):
            old_id = row.get("id")
            cleaned = {k: _coerce(v) for k, v in row.items() if k != "id"}
            cleaned["project_id"] = project_id
            new_id = db["features"].insert(cleaned).last_pk
            if old_id:
                feature_map[str(old_id)] = new_id

        # requirements (remap feature_id + id)
        for row in csv_data.get("requirements", []):
            old_id = row.get("id")
            old_fid = str(row.get("feature_id") or "")
            cleaned = {k: _coerce(v) for k, v in row.items() if k not in ("id", "feature_id")}
            cleaned["feature_id"] = feature_map.get(old_fid)
            if cleaned["feature_id"] is None:
                continue
            new_id = db["requirements"].insert(cleaned).last_pk
            if old_id:
                req_map[str(old_id)] = new_id

        # deliverables (remap requirement_id, role_id)
        for row in csv_data.get("deliverables", []):
            old_req = str(row.get("requirement_id") or "")
            cleaned = {k: _coerce(v) for k, v in row.items() if k not in ("id", "requirement_id", "role_id")}
            cleaned["requirement_id"] = req_map.get(old_req)
            if cleaned["requirement_id"] is None:
                continue
            old_role = row.get("role_id")
            cleaned["role_id"] = role_map.get(str(old_role)) if old_role else None
            db["deliverables"].insert(cleaned)

        # risks (remap id + track)
        risk_map = {}
        for row in csv_data.get("risks", []):
            old_id = row.get("id")
            cleaned = {k: _coerce(v) for k, v in row.items() if k != "id"}
            cleaned["project_id"] = project_id
            new_id = db["risks"].insert(cleaned).last_pk
            if old_id:
                risk_map[str(old_id)] = new_id

        # risk_features (remap both)
        for row in csv_data.get("risk_features", []):
            rid = risk_map.get(str(row.get("risk_id")))
            fid = feature_map.get(str(row.get("feature_id")))
            if rid and fid:
                db["risk_features"].insert({"risk_id": rid, "feature_id": fid})

        # capacity_periods (remap role_id)
        for row in csv_data.get("capacity_periods", []):
            cleaned = {k: _coerce(v) for k, v in row.items() if k not in ("id", "role_id")}
            cleaned["project_id"] = project_id
            old_role = row.get("role_id")
            cleaned["role_id"] = role_map.get(str(old_role)) if old_role else None
            db["capacity_periods"].insert(cleaned)

        # Update project settings (but keep id + project_id consistent)
        for row in csv_data.get("projects", []):
            cleaned = {k: _coerce(v) for k, v in row.items() if k not in ("id",)}
            # Remap default_role_id
            old_drole = cleaned.pop("default_role_id", None)
            if old_drole:
                cleaned["default_role_id"] = role_map.get(str(old_drole), old_drole)
            db["projects"].update(project_id, cleaned)

    init_db()
    return RedirectResponse(f"/p/{project_id}/settings", status_code=303)
