# Legacy data model (FastAPI + SQLite)

Snapshot of the schema as it exists in `Health_Check/` at the start of the Alliance Toolkit migration. Sourced from [models.py](../models.py) (Pydantic) and [database.py](../database.py) (SQLite DDL + additive migrations). This is the spec for the Django models built in Stage 2 of the migration.

All project-scoped tables carry a `project_id` FK to `projects.id`. The `PROJECT_SCOPED_TABLES` list lives in [database.py:20](../database.py) and is the authoritative scoping rule.

## Entities

### projects (`projects`)
Top-level engagement. Pre-multi-project this was a singleton `project` table; row id=1 is preserved.

| Field | Type | Notes |
|---|---|---|
| id | int (PK) | |
| name | str | |
| description | str | |
| start_date | str (ISO date) | |
| as_of_date | str (ISO date) | "today" reference for dashboard math |
| end_date | str (ISO date) | |
| initial_budget | float | $ |
| team_size | float | delivery team headcount |
| actual_spend | float | $ |
| default_role_id | int → roles.id | non-FK in DB but logically references roles |
| overhead_team_size | float | non-delivery headcount |
| default_overhead_role_id | int → roles.id | |
| health_on_track_pct | float | dashboard band threshold |
| health_at_risk_pct | float | dashboard band threshold |
| accent | str | UI token (e.g. "cyan") |
| theme | str | "light" / "dark" |
| icon | str | |
| project_type | str | `agile_feature_development` (default) or `fixed_price`. See [DESIGN_RULES](../DESIGN_RULES.md). |

### roles (`roles`)
Per-project rate card. **Category** distinguishes delivery (produces earned value) from overhead (BAs, designers, SMEs, facilitators — pre-committed budget burn).

| Field | Type | Notes |
|---|---|---|
| id | int (PK) | |
| project_id | int → projects.id | |
| name | str | |
| day_rate | float | $/day |
| category | str | `delivery` or `overhead` (see `VALID_ROLE_CATEGORIES`) |

### Work Breakdown Structure — features → requirements → deliverables

Three-tier WBS. Only the bottom tier (deliverables) carries budget and completion.

#### features (`features`)
| Field | Type | Notes |
|---|---|---|
| id | int (PK) | |
| project_id | int → projects.id | |
| name | str | |
| sort_order | int | |
| started | int (0/1) | drives "in flight" filtering |
| expanded_scope | int (0/1) | scope-creep flag |

#### requirements (`requirements`)
| Field | Type | Notes |
|---|---|---|
| id | int (PK) | |
| feature_id | int → features.id | |
| name | str | |
| sort_order | int | |
| expanded_scope | int (0/1) | |

#### deliverables (`deliverables`)
| Field | Type | Notes |
|---|---|---|
| id | int (PK) | |
| requirement_id | int → requirements.id | |
| name | str | |
| budget_days | float | the only place days are recorded |
| percent_complete | int (0–100) | |
| priority | str | "Must Have" default |
| role_id | int → roles.id (nullable) | drives $ via day_rate |
| sort_order | int | |
| expanded_scope | int (0/1) | |

### risks (`risks`) + risk_features (`risk_features`)
Risk register with a 0–100 realised percentage and explicit timeline-vs-budget impact split. Linked to features via the M2M `risk_features`.

| Field | Type | Notes |
|---|---|---|
| id | int (PK) | |
| project_id | int → projects.id | |
| name | str | |
| description | str | |
| status | str | "todo" / "doing" / "done" |
| date_identified | str (ISO date) | |
| due_date | str (ISO date) | |
| impact_days | float | budget impact (days) |
| timeline_impact_days | float | schedule impact (days) — separate from budget |
| realised_percentage | float (0–100) | replaces legacy `resolution_type` + `mitigation_percentage` (migrated in DB) |
| resultant_work | str | |
| sort_order | int | |

`risk_features` (M2M): `(risk_id → risks.id, feature_id → features.id)`.

### decisions (`decisions`) + decision_features (`decision_features`)
Pivot/scope-change log. Linked to features via M2M.

| Field | Type | Notes |
|---|---|---|
| id | int (PK) | |
| project_id | int → projects.id | |
| name | str | |
| description | str | |
| expected_outcome | str | |
| decision_date | str (ISO date) | |
| decision_type | str | "Pivot" default |
| sort_order | int | |

`decision_features` (M2M): `(decision_id → decisions.id, feature_id → features.id)`.

### budget_adjustments (`budget_adjustments`)
One row per +/- budget change event. Sum is added to `initial_budget` to get total budget.

| Field | Type | Notes |
|---|---|---|
| id | int (PK) | |
| project_id | int → projects.id | |
| amount | float | signed $ |
| date | str (ISO date) | |
| description | str | |

### capacity_periods (`capacity_periods`)
Per-week per-role headcount override. Drives burndown projections.

| Field | Type | Notes |
|---|---|---|
| id | int (PK) | |
| project_id | int → projects.id | |
| week_start_date | str (ISO date) | Monday |
| role_id | int → roles.id | |
| team_size | float | headcount for that role that week |

### overheads (`overheads`)
Pre-committed overhead $ that burn against budget without producing earned value (licences, infra, etc).

| Field | Type | Notes |
|---|---|---|
| id | int (PK) | |
| project_id | int → projects.id | |
| name | str | |
| description | str | |
| amount | float | $ |
| sort_order | int | |

### pm_notes (`pm_notes`)
Free-form PM register. Status mirrors a kanban (todo/doing/done).

| Field | Type | Notes |
|---|---|---|
| id | int (PK) | |
| project_id | int → projects.id | |
| name | str | |
| description | str | |
| status | str | |
| due_date | str (ISO date) | |
| sort_order | int | |

### Fixed-price milestone chain — milestones → milestone_features + milestone_invoices

Only used when `projects.project_type = 'fixed_price'`. Sum of `milestones.value` *is* the project budget for fixed-price projects.

#### milestones (`milestones`)
| Field | Type | Notes |
|---|---|---|
| id | int (PK) | |
| project_id | int → projects.id | |
| name | str | |
| description | str | |
| value | float | contracted $ |
| sort_order | int | drives bar position on dashboard |

#### milestone_features (`milestone_features`) — M2M
`(milestone_id → milestones.id, feature_id → features.id)`. Linked features colour the milestone's bar section by weighted completion; they do not determine bar position (value does).

#### milestone_invoices (`milestone_invoices`)
A milestone can be split across multiple invoices. Sum of invoice amounts ≤ milestone value (enforced in routes).

| Field | Type | Notes |
|---|---|---|
| id | int (PK) | |
| milestone_id | int → milestones.id | |
| invoice_number | str | |
| amount | float | $ |
| status | str | "invoiced" or "paid" |
| issue_date | str (ISO date) | |
| paid_date | str (ISO date) | |

## Notes for the Django port

- **Date storage:** every "date" field is currently a string (ISO format). Django port should use `models.DateField` and convert empties to `null=True, blank=True`.
- **0/1 booleans:** `started`, `expanded_scope` columns are stored as int. Use `models.BooleanField` in Django.
- **Cascade behaviour:** SQLite FK constraints are declared but not enforced (sqlite-utils doesn't enable `PRAGMA foreign_keys`). The route layer deletes children manually. Django port should set explicit `on_delete=models.CASCADE` where deletion should propagate (Feature → Requirements → Deliverables; Risk → RiskFeature; etc.), and `on_delete=models.PROTECT` for `default_role_id` references.
- **Project-scoped query rule:** every list endpoint filters by `project_id`. Django port should put this on a custom manager or mixin to avoid leak risk under multi-PM auth (Stage 2).
- **Audit candidates:** Project, Feature, Risk, Decision, Milestone, MilestoneInvoice — all have business-meaningful history. Wire `alliance_platform.audit` here.
- **Soft-delete:** not used in legacy schema. Consider adding for Project at minimum.
