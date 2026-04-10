from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import os

from database import init_db, get_db
from calculations import (
    deliverable_summary,
    requirement_summary,
    feature_summary,
    project_summary,
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


templates.env.filters["currency"] = fmt_currency
templates.env.filters["pct"] = fmt_pct
templates.env.filters["days"] = fmt_days


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
            fdict = {"id": f[0], "name": f[1], "sort_order": f[2]}

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
    summary = project_summary(project, features, adjustments, default_rate)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active": "dashboard",
        "project": project,
        "features": features,
        "adjustments": adjustments,
        "summary": summary,
        "roles": roles,
    })


# ── Settings ──

@app.get("/settings")
def settings_page(request: Request):
    db = get_db()
    project = get_project()
    roles = get_roles()
    adjustments = list(db["budget_adjustments"].rows)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "active": "settings",
        "project": project,
        "roles": roles,
        "adjustments": adjustments,
    })


@app.post("/settings/project")
def update_project(
    name: str = Form(...),
    start_date: str = Form(""),
    as_of_date: str = Form(""),
    initial_budget: float = Form(0),
    team_size: int = Form(1),
    actual_spend: float = Form(0),
    default_role_id: int = Form(1),
):
    db = get_db()
    db["project"].update(1, {
        "name": name,
        "start_date": start_date,
        "as_of_date": as_of_date,
        "initial_budget": initial_budget,
        "team_size": team_size,
        "actual_spend": actual_spend,
        "default_role_id": default_role_id,
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


@app.post("/deliverables/{del_id}/delete")
def delete_deliverable(del_id: int):
    db = get_db()
    d = db["deliverables"].get(del_id)
    req = db["requirements"].get(d["requirement_id"])
    feature_id = req["feature_id"]
    db["deliverables"].delete(del_id)
    return RedirectResponse(f"/features/{feature_id}", status_code=303)
