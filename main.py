from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import os
import csv
import io
import zipfile
from datetime import datetime

from database import init_db, get_db
from calculations import (
    deliverable_summary,
    requirement_summary,
    feature_summary,
    project_summary,
    feature_health,
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
    summary = project_summary(project, features, adjustments, default_rate)

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

    for f in features:
        # Use started-weighted expected burn for started features,
        # but only evaluate health for features that have started
        if f.get("started", 0) and f["total_dollars"] > 0:
            # Scale expected burn by how much of the started budget this feature represents
            f["health"] = feature_health(
                f,
                summary["expected_burn_pct"],
                on_track_pct,
                at_risk_pct,
            )
        else:
            f["health"] = feature_health(
                f,
                summary["expected_burn_pct"],
                on_track_pct,
                at_risk_pct,
            )

    summary["started_completion"] = started_completion
    summary["started_feature_count"] = len(started_features)
    summary["total_feature_count"] = len([f for f in features if f["total_dollars"] > 0])

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
    health_on_track_pct: float = Form(100.0),
    health_at_risk_pct: float = Form(80.0),
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
        "SELECT id, name, description, status, due_date, impact_days, sort_order FROM risks ORDER BY sort_order, id"
    ).fetchall())
    features_rows = list(db.execute("SELECT id, name FROM features ORDER BY sort_order, id").fetchall())
    all_features = [{"id": f[0], "name": f[1]} for f in features_rows]

    enriched_risks = []
    for r in risks:
        rdict = {
            "id": r[0], "name": r[1], "description": r[2], "status": r[3],
            "due_date": r[4], "impact_days": r[5], "sort_order": r[6],
        }
        rdict["impact_dollars"] = rdict["impact_days"] * default_role_rate
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
    total_impact_days = sum(r["impact_days"] for r in enriched_risks if r["status"] != "done")
    total_impact_dollars = sum(r["impact_dollars"] for r in enriched_risks if r["status"] != "done")

    return templates.TemplateResponse("risks.html", {
        "request": request,
        "active": "risks",
        "risks": enriched_risks,
        "all_features": all_features,
        "summary": {
            "todo": todo_count,
            "doing": doing_count,
            "done": done_count,
            "total_impact_days": total_impact_days,
            "total_impact_dollars": total_impact_dollars,
        },
        "default_rate": default_role_rate,
    })


@app.post("/risks/add")
def add_risk(
    name: str = Form(...),
    description: str = Form(""),
    status: str = Form("todo"),
    due_date: str = Form(""),
    impact_days: float = Form(0),
):
    db = get_db()
    max_order = db.execute("SELECT COALESCE(MAX(sort_order), 0) FROM risks").fetchone()[0]
    db["risks"].insert({
        "name": name,
        "description": description,
        "status": status,
        "due_date": due_date,
        "impact_days": impact_days,
        "sort_order": max_order + 1,
    })
    return RedirectResponse("/risks", status_code=303)


@app.post("/risks/{risk_id}/update")
def update_risk(
    risk_id: int,
    name: str = Form(...),
    description: str = Form(""),
    status: str = Form("todo"),
    due_date: str = Form(""),
    impact_days: float = Form(0),
):
    db = get_db()
    db["risks"].update(risk_id, {
        "name": name,
        "description": description,
        "status": status,
        "due_date": due_date,
        "impact_days": impact_days,
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
    db = get_db()
    if status in ("todo", "doing", "done"):
        db["risks"].update(risk_id, {"status": status})
    return JSONResponse({"ok": True, "status": status})


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


# ── Export / Import ──

EXPORT_TABLES = ["project", "roles", "budget_adjustments", "features", "requirements", "deliverables", "risks", "risk_features"]


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
