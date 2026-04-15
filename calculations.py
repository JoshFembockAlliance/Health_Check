from collections import defaultdict
from datetime import date, timedelta
from typing import Literal


def business_days_between(start: date, end: date) -> int:
    """Count business days from start (inclusive) to end (exclusive).
    Returns 0 if start >= end.
    """
    if start >= end:
        return 0
    days = 0
    current = start
    while current < end:
        if current.weekday() < 5:  # Mon–Fri
            days += 1
        current += timedelta(days=1)
    return days


def parse_date(s: str) -> date | None:
    """Parse an ISO date string (YYYY-MM-DD). Returns None for empty or invalid input."""
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def remaining_days(budget_days: float, percent_complete: int) -> float:
    """Days not yet consumed: budget_days × (1 - completion %)."""
    return budget_days * (1 - percent_complete / 100)


def budget_dollars(budget_days: float, day_rate: float) -> float:
    """Convert a day budget to dollars at the given day rate."""
    return budget_days * day_rate


def remaining_dollars(budget_days: float, percent_complete: int, day_rate: float) -> float:
    """Dollar value of remaining work for a single deliverable."""
    return remaining_days(budget_days, percent_complete) * day_rate


def deliverable_summary(d: dict, day_rate: float) -> dict:
    """Enrich a deliverable dict with computed dollar and remaining-day fields."""
    bd = d["budget_days"]
    pc = d["percent_complete"]
    return {
        **d,
        "budget_dollars": budget_dollars(bd, day_rate),
        "remaining_days": remaining_days(bd, pc),
        "remaining_dollars": remaining_dollars(bd, pc, day_rate),
    }


def requirement_summary(req: dict, deliverables: list[dict], day_rate: float) -> dict:
    """Aggregate a list of enriched deliverables into a requirement-level summary.

    weighted_completion is the budget-day-weighted average completion across
    all deliverables (larger deliverables count more).
    """
    total_days = sum(d["budget_days"] for d in deliverables)
    total_dollars = sum(d["budget_dollars"] for d in deliverables)
    total_remaining_days = sum(d["remaining_days"] for d in deliverables)
    total_remaining_dollars = sum(d["remaining_dollars"] for d in deliverables)
    if total_days > 0:
        weighted_completion = sum(
            d["budget_days"] * d["percent_complete"] for d in deliverables
        ) / total_days
    else:
        weighted_completion = 0
    return {
        **req,
        "deliverables": deliverables,
        "total_days": total_days,
        "total_dollars": total_dollars,
        "remaining_days": total_remaining_days,
        "remaining_dollars": total_remaining_dollars,
        "weighted_completion": weighted_completion,
    }


def feature_summary(feature: dict, requirements: list[dict]) -> dict:
    """Aggregate a list of requirement summaries into a feature-level summary.

    weighted_completion rolls up from requirements the same way requirements
    roll up from deliverables — weighted by total_days at each level.
    """
    total_days = sum(r["total_days"] for r in requirements)
    total_dollars = sum(r["total_dollars"] for r in requirements)
    total_remaining_days = sum(r["remaining_days"] for r in requirements)
    total_remaining_dollars = sum(r["remaining_dollars"] for r in requirements)
    if total_days > 0:
        weighted_completion = sum(
            r["total_days"] * r["weighted_completion"] for r in requirements
        ) / total_days
    else:
        weighted_completion = 0
    return {
        **feature,
        "requirements": requirements,
        "total_days": total_days,
        "total_dollars": total_dollars,
        "remaining_days": total_remaining_days,
        "remaining_dollars": total_remaining_dollars,
        "weighted_completion": weighted_completion,
    }


def project_summary(
    project: dict,
    features: list[dict],
    adjustments: list[dict],
    default_day_rate: float,
    realised_risk_dollars: float = 0.0,
    overhead_dollars: float = 0.0,
) -> dict:
    """Compute all top-level project financial metrics.

    realised_risk_dollars: dollars consumed by closed risks (avoided=0,
    mitigated=partial, realised=full). These reduce the accessible budget
    and therefore the Budget Days Remaining figure.

    overhead_dollars: sum of project overheads (PM salary, licences, etc.).
    These are committed non-delivery costs that reduce the budget pool
    available for feature work — so they reduce both accessible_budget
    (flowing through to Budget Days Remaining and Capacity Remaining) and
    unallocated_budget (so features/overheads/unallocated tile to current_budget).
    """
    total_adj = sum(a["amount"] for a in adjustments)
    current_budget = project["initial_budget"] + total_adj

    # Accessible budget excludes dollars already consumed by closed/realised risks
    # and dollars committed to overheads (non-delivery costs).
    accessible_budget = current_budget - realised_risk_dollars - overhead_dollars

    start = parse_date(project["start_date"])
    as_of = parse_date(project["as_of_date"])
    elapsed_days = business_days_between(start, as_of) if start and as_of else 0

    daily_burn = project["team_size"] * default_day_rate
    expected_spend = daily_burn * elapsed_days
    expected_burn_pct = (expected_spend / current_budget * 100) if current_budget else 0
    current_burn_pct = (project["actual_spend"] / current_budget * 100) if current_budget else 0
    burn_delta = project["actual_spend"] - expected_spend

    allocated_days = sum(f["total_days"] for f in features)
    allocated_dollars = sum(f["total_dollars"] for f in features)
    total_remaining_days = sum(f["remaining_days"] for f in features)
    total_remaining_dollars = sum(f["remaining_dollars"] for f in features)

    if allocated_days > 0:
        overall_completion = sum(
            f["total_days"] * f["weighted_completion"] for f in features
        ) / allocated_days
    else:
        overall_completion = 0

    # Unallocated budget tiles cleanly with allocated_dollars and overhead_dollars:
    # current_budget = allocated_to_features + allocated_to_overheads + unallocated
    unallocated_budget = current_budget - allocated_dollars - overhead_dollars
    # Days remaining is based on accessible budget (after realised risk and overhead deductions)
    budget_days_remaining = (accessible_budget - project["actual_spend"]) / daily_burn if daily_burn else 0

    return {
        "current_budget": current_budget,
        "accessible_budget": accessible_budget,
        "realised_risk_dollars": realised_risk_dollars,
        "overhead_dollars": overhead_dollars,
        "initial_budget": project["initial_budget"],
        "total_adjustments": total_adj,
        "elapsed_days": elapsed_days,
        "daily_burn": daily_burn,
        "expected_spend": expected_spend,
        "expected_burn_pct": expected_burn_pct,
        "actual_spend": project["actual_spend"],
        "current_burn_pct": current_burn_pct,
        "burn_delta": burn_delta,
        "allocated_days": allocated_days,
        "allocated_dollars": allocated_dollars,
        "remaining_days": total_remaining_days,
        "remaining_dollars": total_remaining_dollars,
        "overall_completion": overall_completion,
        "unallocated_budget": unallocated_budget,
        "budget_days_remaining": budget_days_remaining,
    }


def effective_impact_days(
    impact_days: float,
    status: str,
    resolution_type,
    mitigation_percentage: float,
) -> float:
    """Return the realised impact days for a risk.
    Open risks (todo/doing): full impact_days.
    avoided:   0
    mitigated: impact_days × (mitigation_percentage / 100)
    realised:  impact_days (full)
    None (done but no resolution set): treat as realised (conservative).
    """
    if status != "done":
        return impact_days
    if resolution_type == "avoided":
        return 0.0
    if resolution_type == "mitigated":
        return impact_days * (mitigation_percentage / 100.0)
    return impact_days  # "realised" or NULL — conservative


def get_week_monday(d: date) -> date:
    """Return the Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


def capacity_days_remaining(
    remaining_budget: float,
    as_of_date: date,
    capacity_periods: list[dict],
    default_daily_burn: float,
) -> float:
    """Walk forward day-by-day from as_of_date, spending at each day's
    capacity-planned rate until the remaining budget is exhausted.

    capacity_periods: list of dicts with keys week_monday (date), day_rate (float),
                      team_size (int). Multiple entries per week (one per role).
    Returns the number of business days the budget covers.
    """
    # Build a lookup: week_monday → total daily burn for that week
    week_burns: dict[date, float] = {}
    for cp in capacity_periods:
        monday = cp["week_monday"]
        week_burns[monday] = week_burns.get(monday, 0.0) + cp["day_rate"] * cp["team_size"]

    days = 0.0
    budget_left = remaining_budget
    current = as_of_date
    safety_limit = 3650  # max 10 years forward

    for _ in range(safety_limit):
        if budget_left <= 0:
            break
        if current.weekday() < 5:  # business day
            monday = get_week_monday(current)
            daily_burn = week_burns.get(monday, default_daily_burn)
            if daily_burn <= 0:
                daily_burn = default_daily_burn
            if budget_left >= daily_burn:
                budget_left -= daily_burn
                days += 1.0
            else:
                days += budget_left / daily_burn
                budget_left = 0.0
        current += timedelta(days=1)

    return days


def capacity_budget_summary(
    remaining_budget: float,
    as_of_date: date,
    capacity_periods: list[dict],
    default_daily_burn: float,
    default_team_size: int,
) -> dict:
    """Walk forward day-by-day from as_of_date, spending at each day's
    capacity-planned rate until the remaining budget is exhausted.

    Returns:
      budget_days:  business days the remaining budget can fund (float,
                    accounting for per-week capacity fluctuations)
      person_days:  total person-days represented by those budget days
                    (team_size × days, summed week by week)

    capacity_periods entries have keys: week_monday, day_rate, team_size.
    Multiple entries per week are supported (one per role); their burn
    and headcount are summed within each week.
    """
    # Build per-week lookups: burn rate and total headcount
    week_burns: dict[date, float] = {}
    week_sizes: dict[date, int] = {}
    for cp in capacity_periods:
        monday = cp["week_monday"]
        week_burns[monday] = week_burns.get(monday, 0.0) + cp["day_rate"] * cp["team_size"]
        week_sizes[monday] = week_sizes.get(monday, 0) + cp["team_size"]

    budget_days = 0.0
    person_days = 0.0
    budget_left = remaining_budget
    current = as_of_date
    safety_limit = 3650

    for _ in range(safety_limit):
        if budget_left <= 0:
            break
        if current.weekday() < 5:  # business day
            monday = get_week_monday(current)
            daily_burn = week_burns.get(monday, default_daily_burn)
            if daily_burn <= 0:
                daily_burn = default_daily_burn
            team_size = week_sizes.get(monday, default_team_size)
            if budget_left >= daily_burn:
                budget_left -= daily_burn
                budget_days += 1.0
                person_days += team_size
            else:
                fraction = budget_left / daily_burn
                budget_days += fraction
                person_days += fraction * team_size
                budget_left = 0.0
        current += timedelta(days=1)

    return {"budget_days": budget_days, "person_days": person_days}


def capacity_plan_summary(
    as_of_date: date,
    end_date: date | None,
    capacity_periods: list[dict],
    default_team_size: int,
    default_daily_burn: float,
) -> dict:
    """Summarise capacity from as_of_date to end_date (or 52 weeks if no end_date).

    Returns:
      total_person_days: total person-days of capacity remaining
      two_week_by_role: {role_label: person_days} for the 2-week window starting as_of_date
      has_periods: whether any capacity periods exist
    """
    if end_date is None or end_date <= as_of_date:
        end_date = as_of_date + timedelta(weeks=52)

    two_week_end = as_of_date + timedelta(days=14)

    # Build week→role→team_size lookup from enriched capacity periods
    week_role: dict[date, dict[str, int]] = defaultdict(dict)
    for cp in capacity_periods:
        monday = cp["week_monday"]
        label = cp.get("role_name") or "Default"
        week_role[monday][label] = week_role[monday].get(label, 0) + cp["team_size"]

    total_person_days = 0.0
    two_week_by_role: dict[str, float] = {}

    # Walk business days from as_of_date to end_date
    current = as_of_date
    while current < end_date:
        if current.weekday() < 5:
            monday = get_week_monday(current)
            if monday in week_role:
                for role_label, size in week_role[monday].items():
                    total_person_days += size
                    if current < two_week_end:
                        two_week_by_role[role_label] = two_week_by_role.get(role_label, 0.0) + size
            else:
                total_person_days += default_team_size
                if current < two_week_end:
                    lbl = "Default"
                    two_week_by_role[lbl] = two_week_by_role.get(lbl, 0.0) + default_team_size
        current += timedelta(days=1)

    return {
        "total_person_days": total_person_days,
        "two_week_by_role": two_week_by_role,
        "has_periods": len(capacity_periods) > 0,
    }


HealthStatus = Literal["on_track", "at_risk", "behind", "not_budgeted"]


def feature_health(
    feature: dict,
    expected_burn_pct: float,
    on_track_threshold: float,
    at_risk_threshold: float,
) -> dict:
    """Determine a feature's health status by comparing its completion %
    against the project-level expected burn %.

    Logic:
      - If the feature has no budget → "not_budgeted"
      - completion >= expected_burn * (on_track_threshold / 100) → "on_track"
      - completion >= expected_burn * (at_risk_threshold / 100) → "at_risk"
      - otherwise → "behind"

    Returns a dict with status, label, badge_class, and the target % for context.
    """
    if feature["total_dollars"] <= 0:
        return {
            "status": "not_budgeted",
            "label": "Not Budgeted",
            "badge_class": "badge-grey",
            "target_pct": 0,
        }

    completion = feature["weighted_completion"]
    on_track_target = expected_burn_pct * (on_track_threshold / 100)
    at_risk_target = expected_burn_pct * (at_risk_threshold / 100)

    if completion >= on_track_target:
        status = "on_track"
        label = "On Track"
        badge_class = "badge-green"
    elif completion >= at_risk_target:
        status = "at_risk"
        label = "At Risk"
        badge_class = "badge-amber"
    else:
        status = "behind"
        label = "Behind"
        badge_class = "badge-red"

    return {
        "status": status,
        "label": label,
        "badge_class": badge_class,
        "target_pct": on_track_target,
    }
