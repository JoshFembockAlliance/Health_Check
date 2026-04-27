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


def agile_project_summary(
    project: dict,
    features: list[dict],
    adjustments: list[dict],
    default_day_rate: float,
    realised_risk_dollars: float = 0.0,
    overhead_dollars: float = 0.0,
    open_risk_dollars: float = 0.0,
) -> dict:
    """Compute all top-level project financial metrics.

    realised_risk_dollars: dollars absorbed by risk handling — impact_days ×
    realised% × day_rate, summed across risks. Treated as a CATEGORISATION
    of actual_spend (the team time on realised risks IS part of logged
    spend), not as an additional deduction. Used by the dashboard to split
    spend into earned-value vs realised-risk vs unrealised-spend buckets.
    Does NOT independently reduce accessible_budget — that subtraction
    would double-count the spend already deducted via current_budget.

    open_risk_dollars: dollars of unrealised exposure from open risks —
    impact_days × (1 - realised%) × day_rate, summed. Reported on the
    summary so the dashboard can surface "at risk" next to unallocated
    budget. Does NOT reduce accessible_budget (open risks haven't landed
    yet and may still be mitigated), but flags the unallocated value as
    unsafe to fully allocate.

    overhead_dollars: sum of project overheads (PM salary, licences, etc.).
    These are committed non-delivery costs that reduce the budget pool
    available for feature work — so they reduce both accessible_budget
    (flowing through to Budget Days Remaining and Capacity Remaining) and
    unallocated_budget (so features/overheads/realised_risks/unallocated
    tile to total_budget).

    Budget vocabulary — three distinct values, each with a single purpose:
      * total_budget       = initial_budget + adjustments. The full pot
                             assigned to the project. Denominator for burn %.
      * current_budget     = total_budget − actual_spend. What remains to be
                             spent. "We can't spend what we've already spent."
      * accessible_budget  = current_budget − overhead. What's still
                             available for feature delivery (overheads are
                             pre-committed; realised risks are already
                             netted out via actual_spend).
    """
    total_adj = sum(a["amount"] for a in adjustments)
    actual_spend = project["actual_spend"]

    # total_budget: the full pot assigned to the project — initial award plus
    # any adjustments/infusions. This is the "ceiling" used as the denominator
    # for burn % and as the base of the allocation identity.
    total_budget = project["initial_budget"] + total_adj

    # current_budget: what is still liquid. Dollars that have already been
    # invoiced are gone — they can't be spent again — so we subtract them
    # from the pot. Every downstream "what can we still do?" figure flows
    # from here.
    current_budget = total_budget - actual_spend

    # accessible_budget: current_budget minus money committed to overheads
    # (non-delivery costs). Realised risks are NOT subtracted here — they
    # represent team time already spent on risk handling, which is already
    # reflected in actual_spend (and therefore in current_budget). Subtracting
    # them again would double-count. Realised risks remain available as a
    # categorisation of how spend was used (see dashboard breakdown).
    accessible_budget = current_budget - overhead_dollars

    start = parse_date(project["start_date"])
    as_of = parse_date(project["as_of_date"])
    elapsed_days = business_days_between(start, as_of) if start and as_of else 0

    daily_burn = project["team_size"] * default_day_rate
    expected_spend = daily_burn * elapsed_days

    # Burn percentages use total_budget as the denominator: they answer
    # "what fraction of the full project pot has been / should have been
    # spent by now?" — a stable reference that doesn't shift as spend lands.
    expected_burn_pct = (expected_spend / total_budget * 100) if total_budget else 0
    current_burn_pct = (actual_spend / total_budget * 100) if total_budget else 0
    # Feature completion comparisons exclude overhead — it never contributes
    # to feature delivery, so including it would understate the target.
    feature_budget = total_budget - overhead_dollars
    feature_expected_burn_pct = (expected_spend / feature_budget * 100) if feature_budget > 0 else 0
    burn_delta = actual_spend - expected_spend

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

    # Unallocated budget tiles cleanly with the other planning buckets:
    # total_budget = features + overheads + realised_risks + unallocated.
    # This is an allocation view (what is the pot earmarked for?), not a
    # liquidity view, so it sits against total_budget, not current_budget.
    unallocated_budget = total_budget - allocated_dollars - overhead_dollars - realised_risk_dollars

    # budget_days_remaining: full-team days available for team-on-feature
    # work — accessible_budget converted to days at the team burn rate.
    # Overheads are reserved off the top (cannot be redirected); realised
    # risks are already netted out via actual_spend → current_budget.
    budget_days_remaining = accessible_budget / daily_burn if daily_burn else 0

    # total_budget_days_remaining: identical to budget_days_remaining under
    # the current model (both flow from accessible_budget). Kept as a
    # separate name because the agile dashboard hero card uses this label
    # specifically; consolidate at a quieter time.
    total_budget_days_remaining = budget_days_remaining

    return {
        "total_budget": total_budget,
        "current_budget": current_budget,
        "accessible_budget": accessible_budget,
        "realised_risk_dollars": realised_risk_dollars,
        "open_risk_dollars": open_risk_dollars,
        "overhead_dollars": overhead_dollars,
        "initial_budget": project["initial_budget"],
        "total_adjustments": total_adj,
        "elapsed_days": elapsed_days,
        "daily_burn": daily_burn,
        "expected_spend": expected_spend,
        "expected_burn_pct": expected_burn_pct,
        "feature_expected_burn_pct": feature_expected_burn_pct,
        "actual_spend": actual_spend,
        "current_burn_pct": current_burn_pct,
        "burn_delta": burn_delta,
        "allocated_days": allocated_days,
        "allocated_dollars": allocated_dollars,
        "remaining_days": total_remaining_days,
        "remaining_dollars": total_remaining_dollars,
        "overall_completion": overall_completion,
        "unallocated_budget": unallocated_budget,
        "budget_days_remaining": budget_days_remaining,
        "total_budget_days_remaining": total_budget_days_remaining,
    }


# Backwards-compatible alias. Some callers (and existing tests) still import
# project_summary; for agile projects the behaviour is identical.
project_summary = agile_project_summary


# ─────────────────────────── Fixed-Price ───────────────────────────

# Colour bands used to tint a milestone's progress-bar segment by the weighted
# completion of its linked features. "invoiced"/"paid" override the linked-
# completion colour once money has moved.
MILESTONE_BAND_PENDING = "pending"       # 0–49% linked completion, no invoices
MILESTONE_BAND_IN_PROGRESS = "in_progress"  # 50–99% linked completion
MILESTONE_BAND_READY = "ready"           # 100% linked completion, not invoiced
MILESTONE_BAND_INVOICED = "invoiced"     # at least one invoice issued
MILESTONE_BAND_PAID = "paid"             # invoice amounts fully paid up to value


def _milestone_linked_completion(milestone_id: int,
                                 features_by_id: dict,
                                 milestone_feature_links: list[dict]) -> float:
    """Weighted-day completion across features linked to this milestone.

    Matches the feature-level rollup used elsewhere: sum(total_days × completion) /
    sum(total_days). Returns 0 if no linked features have budget.
    """
    linked_ids = [
        link["feature_id"] for link in milestone_feature_links
        if link["milestone_id"] == milestone_id
    ]
    linked = [features_by_id[fid] for fid in linked_ids if fid in features_by_id]
    total_days = sum(f["total_days"] for f in linked)
    if total_days <= 0:
        return 0.0
    return sum(f["total_days"] * f["weighted_completion"] for f in linked) / total_days


def milestones_summary(
    milestones: list[dict],
    invoices: list[dict],
    features: list[dict],
    milestone_feature_links: list[dict],
) -> list[dict]:
    """Enrich milestones with bar geometry, linked-feature completion, and
    invoice-derived payment status.

    Each result dict contains:
      * the original milestone fields
      * invoiced_amount, paid_amount
      * status: pending | invoiced | paid  (derived from invoices)
      * linked_completion_pct: weighted completion of linked features (0–100)
      * value_share: this milestone's fraction of total milestone value
      * bar_start_pct / bar_width_pct: placement on the progress bar
      * colour_band: which visual band to tint the segment with
      * invoices: the subset of invoices belonging to this milestone
    """
    features_by_id = {f["id"]: f for f in features}
    total_value = sum(m["value"] for m in milestones) or 0.0
    ordered = sorted(milestones, key=lambda m: (m.get("sort_order", 0), m.get("id", 0)))

    running = 0.0
    enriched = []
    for m in ordered:
        mid = m["id"]
        linked_feature_ids = [
            link["feature_id"] for link in milestone_feature_links
            if link["milestone_id"] == mid
        ]
        ms_invoices = [inv for inv in invoices if inv["milestone_id"] == mid]
        invoiced_amount = sum(inv["amount"] for inv in ms_invoices)
        paid_amount = sum(inv["amount"] for inv in ms_invoices if inv.get("status") == "paid")

        if not ms_invoices:
            status = "pending"
        elif paid_amount >= m["value"] - 1e-6 and m["value"] > 0:
            status = "paid"
        else:
            status = "invoiced"

        linked_completion = _milestone_linked_completion(mid, features_by_id, milestone_feature_links)

        if status == "paid":
            band = MILESTONE_BAND_PAID
        elif status == "invoiced":
            band = MILESTONE_BAND_INVOICED
        elif linked_completion >= 100:
            band = MILESTONE_BAND_READY
        elif linked_completion >= 50:
            band = MILESTONE_BAND_IN_PROGRESS
        else:
            band = MILESTONE_BAND_PENDING

        share = (m["value"] / total_value) if total_value > 0 else 0.0
        width_pct = share * 100.0
        start_pct = running
        running += width_pct

        enriched.append({
            **m,
            "invoices": ms_invoices,
            "invoiced_amount": invoiced_amount,
            "paid_amount": paid_amount,
            "status": status,
            "linked_completion_pct": linked_completion,
            "linked_feature_ids": linked_feature_ids,
            "value_share": share,
            "bar_start_pct": start_pct,
            "bar_width_pct": width_pct,
            "colour_band": band,
        })

    return enriched


def fixed_price_project_summary(
    project: dict,
    features: list[dict],
    milestones_enriched: list[dict],
    default_day_rate: float,
) -> dict:
    """Top-level fixed-price metrics.

    total_budget is derived from the milestone values (not initial_budget /
    adjustments). margin is paid_to_date − actual_spend; projected_margin is
    invoiced_to_date − actual_spend. next_milestone is the first one not yet
    fully paid. overall_completion uses the same weighted-days formula the
    agile path uses so the bar reads on the same scale.
    """
    actual_spend = project["actual_spend"]
    total_budget = sum(m["value"] for m in milestones_enriched)
    invoiced_to_date = sum(m["invoiced_amount"] for m in milestones_enriched)
    paid_to_date = sum(m["paid_amount"] for m in milestones_enriched)

    margin = paid_to_date - actual_spend
    projected_margin = invoiced_to_date - actual_spend

    daily_burn = project["team_size"] * default_day_rate

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

    next_milestone = None
    for m in milestones_enriched:
        if m["status"] != "paid":
            next_milestone = m
            break

    start = parse_date(project["start_date"])
    as_of = parse_date(project["as_of_date"])
    elapsed_days = business_days_between(start, as_of) if start and as_of else 0

    return {
        "total_budget": total_budget,
        "invoiced_to_date": invoiced_to_date,
        "paid_to_date": paid_to_date,
        "margin": margin,
        "projected_margin": projected_margin,
        "actual_spend": actual_spend,
        "daily_burn": daily_burn,
        "elapsed_days": elapsed_days,
        "allocated_days": allocated_days,
        "allocated_dollars": allocated_dollars,
        "remaining_days": total_remaining_days,
        "remaining_dollars": total_remaining_dollars,
        "overall_completion": overall_completion,
        "next_milestone": next_milestone,
        "milestone_count": len(milestones_enriched),
        "paid_count": sum(1 for m in milestones_enriched if m["status"] == "paid"),
        "invoiced_count": sum(1 for m in milestones_enriched if m["status"] == "invoiced"),
    }


def effective_impact_days(impact_days: float, realised_percentage: float) -> float:
    """Return the already-realised impact days for a risk.

    realised_percentage is independent of status: an open risk can have
    partial realisation (some time irrecoverably spent), and a closed risk
    carries whatever percentage was set when it was resolved. The exposure
    (unrealised portion) is impact_days * (1 - realised_percentage/100)
    and is only meaningful for open risks.
    """
    return impact_days * (realised_percentage / 100.0)


def unrealised_exposure_days(impact_days: float, status: str, realised_percentage: float) -> float:
    """Return the portion of impact_days still at risk for an open risk.

    Closed risks carry zero remaining exposure — whatever hasn't already
    been realised is gone with the resolution.
    """
    if status == "done":
        return 0.0
    return impact_days * (1.0 - realised_percentage / 100.0)


def resolution_label(status: str, realised_percentage: float) -> str:
    """Derived display label for a closed risk.

    Open risks return an empty string (no resolution yet). Closed risks
    map to the classic register vocabulary:
      0%         → Avoided
      1% to 99%  → Mitigated
      100%       → Realised
    """
    if status != "done":
        return ""
    if realised_percentage <= 0:
        return "Avoided"
    if realised_percentage >= 100:
        return "Realised"
    return "Mitigated"


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
