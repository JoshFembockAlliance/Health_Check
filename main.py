from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import os
import csv
import io
import zipfile
from datetime import datetime, date as _date, timedelta

from database import init_db, get_db
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
    """Number of whole days between an ISO date string and today.
    Returns None for missing/invalid input so templates can hide the age.
    """
    if not iso_date_str:
        return None
    try:
        d = _date.fromisoformat(iso_date_str)
    except (ValueError, TypeError):
        return None
    return (_date.today() - d).days


templates.env.filters["currency"] = fmt_currency
templates.env.filters["pct"] = fmt_pct
templates.env.filters["days"] = fmt_days
templates.env.filters["age_days"] = fmt_age_days


@app.on_event("startup")
def startup():
    init_db()


def get_project():
    db = get_db()
    return list(db["project"].rows)[0]


def get_roles():
    db = get_db()
    return list(db["roles"].rows)


def get_role_rate(role_id, roles, default_rate):
    for r in roles:
        if r["id"] == role_id:
            return r["day_rate"]
    return default_rate


def build_feature_data(feature_id=None):
    db = get_db()
    project = get_project()
    roles = get_roles()
    default_role_rate = get_role_rate(project["default_role_id"], roles, 0)

    if feature_id:
        features_rows = [db["features"].get(feature_id)]
    else:
        features_rows = list(db.execute("SELECT * FROM features ORDER BY sort_order, id").fetchall())

    enriched_features = []
    for f in features_rows:
        if isinstance(f, dict):
            fid = f["id"]
            fdict = f
        else:
            fid = f[0]
            fdict = {"id": f[0], "name": f[1], "sort_order": f[2], "started": f[3] if len(f) > 3 else 0}

        reqs = list(db.execute(
            "SELECT * FROM requirements WHERE feature_id = ? ORDER BY sort_order, id", [fid]
        ).fetchall())

        enriched_reqs = []
        for r in reqs:
            rdict = {"id": r[0], "feature_id": r[1], "name": r[2], "sort_order": r[3]}
            dels = list(db.execute(
                "SELECT * FROM deliverables WHERE requirement_id = ? ORDER BY sort_order, id", [rdict["id"]]
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


# ── Dashboard ──

@app.get("/")
def dashboard(request: Request):
    db = get_db()
    features, project, roles, default_rate = build_feature_data()
    adjustments = list(db["budget_adjustments"].rows)
    overheads = list(db["overheads"].rows)
    overhead_total = sum(o["amount"] for o in overheads)

    # Risk rows needed early so realised/open risk dollars can flow into project_summary.
    # Tuple positions: (status, impact_days, realised_percentage).
    risk_rows = db.execute(
        "SELECT status, impact_days, realised_percentage FROM risks"
    ).fetchall()
    open_risks = [r for r in risk_rows if r[0] != "done"]
    closed_risks = [r for r in risk_rows if r[0] == "done"]

    # Realised risk days are summed across ALL risks — realised_percentage is
    # independent of status, so open risks with partial realisation count too.
    realised_risk_days = sum(
        effective_impact_days(r[1], r[2] or 0.0) for r in risk_rows
    )
    realised_risk_dollars = realised_risk_days * default_rate
    # Open risk exposure = unrealised portion of open risks only.
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

    # Compute weighted completion for started features only
    started_features = [f for f in features if f.get("started", 0) and f["total_days"] > 0]
    started_total_days = sum(f["total_days"] for f in started_features)
    if started_total_days > 0:
        started_completion = sum(
            f["total_days"] * f["weighted_completion"] for f in started_features
        ) / started_total_days
    else:
        started_completion = 0

    # Adjust the target for started features: they must carry the full project
    # completion load since non-started features contribute nothing.
    # adjusted_target = min(100, feature_expected_burn_pct × total_days / started_days)
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

    # Risk exposure breakdown for the Risk Exposure section.
    # open_exposure_days: unrealised portion of open risks (still at risk).
    # realised_risk_days: already-absorbed portion across ALL risks
    #   (open-with-partial + closed).
    # avoided_days: closed risks that landed at 0% — days "saved" vs impact.
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

    # Capacity planning data for dashboard
    as_of = parse_date(project.get("as_of_date", ""))
    end_dt = parse_date(project.get("end_date", ""))
    cap_rows = list(db.execute(
        "SELECT cp.id, cp.week_start_date, cp.role_id, cp.team_size, "
        "COALESCE(r.name, 'Default') as role_name, "
        "COALESCE(r.day_rate, ?) as day_rate "
        "FROM capacity_periods cp "
        "LEFT JOIN roles r ON cp.role_id = r.id "
        "ORDER BY cp.week_start_date",
        [default_rate]
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

    # PM Notes for dashboard: sticky + overdue + due within 14 days, not done.
    # Stickies always show first; remaining notes sorted ascending by due_date.
    # Columns: 0=id, 1=name, 2=description, 3=status, 4=due_date
    as_of_str = project.get("as_of_date", "")
    note_rows = list(db.execute(
        "SELECT id, name, description, status, due_date FROM pm_notes ORDER BY sort_order, id"
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
    # Sort non-sticky notes by due_date ascending (None sorts last)
    dated_notes.sort(key=lambda n: n["due_date"] or "9999-99-99")
    dashboard_notes = sticky_notes + dated_notes
    notes_overflow = max(0, len(dashboard_notes) - 3)
    dashboard_notes = dashboard_notes[:3]

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active": "dashboard",
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
    })


# ── Settings ──

@app.get("/settings")
def settings_page(request: Request):
    db = get_db()
    project = get_project()
    roles = get_roles()
    adjustments = list(db["budget_adjustments"].rows)
    overheads = list(db.execute("SELECT * FROM overheads ORDER BY sort_order, id").fetchall())
    overheads = [
        {"id": o[0], "name": o[1], "description": o[2], "amount": o[3], "sort_order": o[4]}
        for o in overheads
    ]
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "active": "settings",
        "project": project,
        "roles": roles,
        "adjustments": adjustments,
        "overheads": overheads,
    })


@app.post("/settings/project")
def update_project(
    name: str = Form(...),
    start_date: str = Form(""),
    as_of_date: str = Form(""),
    initial_budget: float = Form(0),
    actual_spend: float = Form(0),
    health_on_track_pct: float = Form(100.0),
    health_at_risk_pct: float = Form(80.0),
):
    db = get_db()
    # team_size and default_role_id are managed via /capacity/defaults
    db["project"].update(1, {
        "name": name,
        "start_date": start_date,
        "as_of_date": as_of_date,
        "initial_budget": initial_budget,
        "actual_spend": actual_spend,
        "health_on_track_pct": health_on_track_pct,
        "health_at_risk_pct": health_at_risk_pct,
    })
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/roles/add")
def add_role(name: str = Form(...), day_rate: float = Form(0)):
    db = get_db()
    db["roles"].insert({"name": name, "day_rate": day_rate})
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/roles/{role_id}/update")
def update_role(role_id: int, name: str = Form(...), day_rate: float = Form(0)):
    db = get_db()
    db["roles"].update(role_id, {"name": name, "day_rate": day_rate})
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/roles/{role_id}/delete")
def delete_role(role_id: int):
    db = get_db()
    db["roles"].delete(role_id)
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/adjustments/add")
def add_adjustment(amount: float = Form(0), date: str = Form(""), description: str = Form("")):
    db = get_db()
    db["budget_adjustments"].insert({"amount": amount, "date": date, "description": description})
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/adjustments/{adj_id}/delete")
def delete_adjustment(adj_id: int):
    db = get_db()
    db["budget_adjustments"].delete(adj_id)
    return RedirectResponse("/settings", status_code=303)


# ── Overheads ──
# Fixed dollar costs that reduce the budget pool available for delivery
# (PM salary, tool licences, etc.). Sum is deducted from accessible_budget
# in project_summary() so all "remaining budget" displays reflect it.

@app.post("/settings/overheads/add")
def add_overhead(name: str = Form(...), description: str = Form(""), amount: float = Form(0)):
    db = get_db()
    max_order = db.execute("SELECT COALESCE(MAX(sort_order), 0) FROM overheads").fetchone()[0]
    db["overheads"].insert({
        "name": name,
        "description": description,
        "amount": amount,
        "sort_order": max_order + 1,
    })
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/overheads/{overhead_id}/update")
def update_overhead(
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
    return RedirectResponse("/settings", status_code=303)


@app.post("/settings/overheads/{overhead_id}/delete")
def delete_overhead(overhead_id: int):
    db = get_db()
    db["overheads"].delete(overhead_id)
    return RedirectResponse("/settings", status_code=303)


# ── Features ──

@app.get("/features")
def features_list(request: Request):
    features, project, roles, default_rate = build_feature_data()
    return templates.TemplateResponse("features.html", {
        "request": request,
        "active": "features",
        "features": features,
        "project": project,
    })


@app.post("/features/{feature_id}/toggle-started")
def toggle_started(feature_id: int):
    db = get_db()
    f = db["features"].get(feature_id)
    db["features"].update(feature_id, {"started": 0 if f.get("started", 0) else 1})
    return RedirectResponse("/", status_code=303)


@app.post("/api/features/{feature_id}/toggle-started")
def api_toggle_started(feature_id: int):
    db = get_db()
    f = db["features"].get(feature_id)
    new_val = 0 if f.get("started", 0) else 1
    db["features"].update(feature_id, {"started": new_val})
    return JSONResponse({"ok": True, "started": new_val})


@app.post("/features/add")
def add_feature(name: str = Form(...)):
    db = get_db()
    max_order = db.execute("SELECT COALESCE(MAX(sort_order), 0) FROM features").fetchone()[0]
    db["features"].insert({"name": name, "sort_order": max_order + 1})
    return RedirectResponse("/features", status_code=303)


@app.post("/features/{feature_id}/update")
def update_feature(feature_id: int, name: str = Form(...)):
    db = get_db()
    db["features"].update(feature_id, {"name": name})
    return RedirectResponse(f"/features/{feature_id}", status_code=303)


@app.post("/features/{feature_id}/delete")
def delete_feature(feature_id: int):
    db = get_db()
    reqs = list(db.execute("SELECT id FROM requirements WHERE feature_id = ?", [feature_id]).fetchall())
    for r in reqs:
        db.execute("DELETE FROM deliverables WHERE requirement_id = ?", [r[0]])
    db.execute("DELETE FROM requirements WHERE feature_id = ?", [feature_id])
    db["features"].delete(feature_id)
    return RedirectResponse("/features", status_code=303)


# ── Feature Detail ──

@app.get("/features/{feature_id}")
def feature_detail(request: Request, feature_id: int):
    features, project, roles, default_rate = build_feature_data(feature_id)
    if not features:
        return RedirectResponse("/features", status_code=303)
    return templates.TemplateResponse("feature_detail.html", {
        "request": request,
        "active": "features",
        "feature": features[0],
        "project": project,
        "roles": roles,
    })


# ── Requirements ──

@app.post("/features/{feature_id}/requirements/add")
def add_requirement(feature_id: int, name: str = Form(...)):
    db = get_db()
    max_order = db.execute(
        "SELECT COALESCE(MAX(sort_order), 0) FROM requirements WHERE feature_id = ?", [feature_id]
    ).fetchone()[0]
    db["requirements"].insert({"feature_id": feature_id, "name": name, "sort_order": max_order + 1})
    return RedirectResponse(f"/features/{feature_id}", status_code=303)


@app.post("/requirements/{req_id}/update")
def update_requirement(req_id: int, name: str = Form(...)):
    db = get_db()
    req = db["requirements"].get(req_id)
    db["requirements"].update(req_id, {"name": name})
    return RedirectResponse(f"/features/{req['feature_id']}", status_code=303)


@app.post("/requirements/{req_id}/delete")
def delete_requirement(req_id: int):
    db = get_db()
    req = db["requirements"].get(req_id)
    feature_id = req["feature_id"]
    db.execute("DELETE FROM deliverables WHERE requirement_id = ?", [req_id])
    db["requirements"].delete(req_id)
    return RedirectResponse(f"/features/{feature_id}", status_code=303)


# ── Deliverables ──

@app.post("/requirements/{req_id}/deliverables/add")
def add_deliverable(
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
    return RedirectResponse(f"/features/{req['feature_id']}", status_code=303)


@app.post("/deliverables/{del_id}/update")
def update_deliverable(
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
    return RedirectResponse(f"/features/{req['feature_id']}", status_code=303)


@app.post("/api/deliverables/{del_id}/percent")
def update_percent(del_id: int, percent_complete: int = Form(0)):
    db = get_db()
    db["deliverables"].update(del_id, {"percent_complete": max(0, min(100, percent_complete))})
    d = db["deliverables"].get(del_id)
    req = db["requirements"].get(d["requirement_id"])
    return JSONResponse({"ok": True, "feature_id": req["feature_id"]})


@app.post("/api/deliverables/{del_id}/update")
def api_update_deliverable(
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


@app.post("/deliverables/{del_id}/delete")
def delete_deliverable(del_id: int):
    db = get_db()
    d = db["deliverables"].get(del_id)
    req = db["requirements"].get(d["requirement_id"])
    feature_id = req["feature_id"]
    db["deliverables"].delete(del_id)
    return RedirectResponse(f"/features/{feature_id}", status_code=303)


# ── Risks ──

@app.get("/risks")
def risks_page(request: Request):
    db = get_db()
    project = get_project()
    roles = get_roles()
    default_role_rate = get_role_rate(project["default_role_id"], roles, 0)
    risks = list(db.execute(
        "SELECT id, name, description, status, due_date, impact_days, sort_order, realised_percentage, resultant_work, timeline_impact_days, date_identified FROM risks ORDER BY sort_order, id"
    ).fetchall())
    features_rows = list(db.execute("SELECT id, name FROM features ORDER BY sort_order, id").fetchall())
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
        # Get linked features
        links = list(db.execute(
            "SELECT f.id, f.name FROM risk_features rf JOIN features f ON rf.feature_id = f.id WHERE rf.risk_id = ?",
            [rdict["id"]]
        ).fetchall())
        rdict["linked_features"] = [{"id": l[0], "name": l[1]} for l in links]
        enriched_risks.append(rdict)

    # Summary counts
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

    return templates.TemplateResponse("risks.html", {
        "request": request,
        "active": "risks",
        "risks": enriched_risks,
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
    })


def _clamp_pct(value: float) -> float:
    """Constrain a percentage value to [0, 100]."""
    return max(0.0, min(100.0, value))


@app.post("/risks/add")
def add_risk(
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
    max_order = db.execute("SELECT COALESCE(MAX(sort_order), 0) FROM risks").fetchone()[0]
    # If the PM doesn't supply a raise-date, default to today so the age
    # indicator starts counting from creation rather than showing blank.
    if not date_identified:
        date_identified = _date.today().isoformat()
    db["risks"].insert({
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
    return RedirectResponse("/risks", status_code=303)


@app.post("/risks/{risk_id}/update")
def update_risk(
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
    return RedirectResponse("/risks", status_code=303)


@app.post("/risks/{risk_id}/delete")
def delete_risk(risk_id: int):
    db = get_db()
    db.execute("DELETE FROM risk_features WHERE risk_id = ?", [risk_id])
    db["risks"].delete(risk_id)
    return RedirectResponse("/risks", status_code=303)


@app.post("/api/risks/{risk_id}/status")
def update_risk_status(risk_id: int, status: str = Form("todo")):
    """Inline status change from a risk card. Realised % is handled
    independently via /api/risks/{id}/realised — no modal flow needed.
    """
    if status not in ("todo", "doing", "done"):
        return JSONResponse({"ok": False, "error": "invalid status"})
    db = get_db()
    db["risks"].update(risk_id, {"status": status})
    return JSONResponse({"ok": True, "status": status})


@app.post("/api/risks/{risk_id}/realised")
def update_risk_realised(risk_id: int, realised_percentage: float = Form(0.0)):
    """Inline edit of realised % from a risk card."""
    db = get_db()
    db["risks"].update(risk_id, {"realised_percentage": _clamp_pct(realised_percentage)})
    return JSONResponse({"ok": True, "realised_percentage": _clamp_pct(realised_percentage)})


@app.post("/risks/{risk_id}/link-feature")
def link_feature_to_risk(risk_id: int, feature_id: int = Form(...)):
    db = get_db()
    existing = db.execute(
        "SELECT COUNT(*) FROM risk_features WHERE risk_id = ? AND feature_id = ?",
        [risk_id, feature_id]
    ).fetchone()[0]
    if not existing:
        db["risk_features"].insert({"risk_id": risk_id, "feature_id": feature_id})
    return RedirectResponse("/risks", status_code=303)


@app.post("/risks/{risk_id}/unlink-feature/{feature_id}")
def unlink_feature_from_risk(risk_id: int, feature_id: int):
    db = get_db()
    db.execute(
        "DELETE FROM risk_features WHERE risk_id = ? AND feature_id = ?",
        [risk_id, feature_id]
    )
    return RedirectResponse("/risks", status_code=303)


# ── PM Notes ──

@app.get("/pm-notes")
def pm_notes_page(request: Request):
    db = get_db()
    project = get_project()
    notes = list(db.execute(
        "SELECT id, name, description, status, due_date, sort_order "
        "FROM pm_notes ORDER BY "
        "CASE status WHEN 'sticky' THEN 0 WHEN 'todo' THEN 1 WHEN 'doing' THEN 2 ELSE 3 END, "
        "due_date ASC, sort_order, id"
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
    return templates.TemplateResponse("pm_notes.html", {
        "request": request,
        "active": "pm_notes",
        "project": project,
        "notes": enriched,
        "counts": counts,
    })


@app.post("/pm-notes/add")
def add_note(
    name: str = Form(...),
    description: str = Form(""),
    status: str = Form("todo"),
    due_date: str = Form(""),
):
    db = get_db()
    max_order = db.execute("SELECT COALESCE(MAX(sort_order), 0) FROM pm_notes").fetchone()[0]
    db["pm_notes"].insert({
        "name": name,
        "description": description,
        "status": status,
        "due_date": due_date if status != "sticky" else "",
        "sort_order": max_order + 1,
    })
    return RedirectResponse("/pm-notes", status_code=303)


@app.post("/pm-notes/{note_id}/update")
def update_note(
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
    return RedirectResponse("/pm-notes", status_code=303)


@app.post("/pm-notes/{note_id}/delete")
def delete_note(note_id: int):
    db = get_db()
    db["pm_notes"].delete(note_id)
    return RedirectResponse("/pm-notes", status_code=303)


# ── Capacity Planning ──

@app.get("/capacity")
def capacity_page(request: Request):
    db = get_db()
    project = get_project()
    roles = get_roles()
    default_rate = get_role_rate(project["default_role_id"], roles, 0)

    rows = list(db.execute(
        "SELECT cp.id, cp.week_start_date, cp.role_id, cp.team_size, "
        "COALESCE(r.name, 'Default') as role_name, "
        "COALESCE(r.day_rate, ?) as day_rate "
        "FROM capacity_periods cp "
        "LEFT JOIN roles r ON cp.role_id = r.id "
        "ORDER BY cp.week_start_date, cp.id",
        [default_rate]
    ).fetchall())

    # Group periods by week for display (regular dict preserves insertion order in Python 3.7+)
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

    return templates.TemplateResponse("capacity.html", {
        "request": request,
        "active": "capacity",
        "project": project,
        "roles": roles,
        "weeks": weeks,
    })


@app.post("/capacity/add")
def add_capacity_period(
    week_start_date: str = Form(...),
    role_id: Optional[int] = Form(None),
    team_size: int = Form(1),
):
    db = get_db()
    # Normalise to Monday of the given week
    try:
        d = _date.fromisoformat(week_start_date)
        monday = d - timedelta(days=d.weekday())
    except ValueError:
        return RedirectResponse("/capacity", status_code=303)
    db["capacity_periods"].insert({
        "week_start_date": monday.isoformat(),
        "role_id": role_id,
        "team_size": max(0, team_size),
    })
    return RedirectResponse("/capacity", status_code=303)


@app.post("/capacity/{period_id}/delete")
def delete_capacity_period(period_id: int):
    db = get_db()
    db["capacity_periods"].delete(period_id)
    return RedirectResponse("/capacity", status_code=303)


@app.post("/capacity/defaults")
def update_capacity_defaults(
    team_size: int = Form(1),
    default_role_id: int = Form(1),
):
    """Update the project-level default team size and role used for weeks
    without an explicit capacity entry."""
    db = get_db()
    db["project"].update(1, {
        "team_size": max(1, team_size),
        "default_role_id": default_role_id,
    })
    return RedirectResponse("/capacity", status_code=303)


# ── Export / Import ──

EXPORT_TABLES = ["project", "roles", "budget_adjustments", "features", "requirements", "deliverables", "risks", "risk_features", "overheads"]


@app.get("/export")
def export_csv():
    db = get_db()
    buf = io.BytesIO()
    project = get_project()
    project_name = project["name"].replace(" ", "_").replace("/", "-")
    filename = f"{project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for table_name in EXPORT_TABLES:
            if table_name not in db.table_names():
                continue
            rows = list(db[table_name].rows)
            if not rows:
                continue
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
            zf.writestr(f"{table_name}.csv", output.getvalue())

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/import")
async def import_csv(file: UploadFile = File(...)):
    db = get_db()
    content = await file.read()
    buf = io.BytesIO(content)

    with zipfile.ZipFile(buf, "r") as zf:
        # Clear existing data in reverse FK order
        for table_name in reversed(EXPORT_TABLES):
            if table_name in db.table_names():
                db[table_name].delete_where()

        for table_name in EXPORT_TABLES:
            csv_filename = f"{table_name}.csv"
            if csv_filename not in zf.namelist():
                continue
            csv_content = zf.read(csv_filename).decode("utf-8")
            reader = csv.DictReader(io.StringIO(csv_content))
            for row in reader:
                # Convert numeric fields
                cleaned = {}
                for k, v in row.items():
                    if v == "" or v is None:
                        cleaned[k] = None
                    else:
                        try:
                            if "." in v:
                                cleaned[k] = float(v)
                            else:
                                cleaned[k] = int(v)
                        except (ValueError, TypeError):
                            cleaned[k] = v
                db[table_name].insert(cleaned)

    # Re-run init to ensure any missing columns/defaults exist
    init_db()

    return RedirectResponse("/settings", status_code=303)
