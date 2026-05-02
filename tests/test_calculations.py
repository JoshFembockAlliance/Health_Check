"""Unit tests for calculations.py business logic."""
from datetime import date, timedelta
import pytest
from calculations import (
    business_days_between,
    parse_date,
    add_business_days,
    remaining_days,
    budget_dollars,
    remaining_dollars,
    effective_impact_days,
    unrealised_exposure_days,
    resolution_label,
    deliverable_summary,
    requirement_summary,
    feature_summary,
    project_summary,
    agile_project_summary,
    fixed_price_project_summary,
    milestones_summary,
    feature_health,
    get_week_monday,
    capacity_days_remaining,
    capacity_plan_summary,
    capacity_budget_summary,
    projected_overhead_team_dollars,
    agile_burndown_chart_data,
)


# ── business_days_between ──────────────────────────────────────────────────

class TestBusinessDaysBetween:
    def test_same_day_returns_zero(self):
        d = date(2024, 1, 15)
        assert business_days_between(d, d) == 0

    def test_start_after_end_returns_zero(self):
        assert business_days_between(date(2024, 1, 20), date(2024, 1, 15)) == 0

    def test_one_full_week(self):
        # Monday to following Monday = 5 business days
        assert business_days_between(date(2024, 1, 15), date(2024, 1, 22)) == 5

    def test_skips_weekends(self):
        # Friday to Monday = 1 business day
        assert business_days_between(date(2024, 1, 19), date(2024, 1, 22)) == 1

    def test_two_weeks(self):
        assert business_days_between(date(2024, 1, 1), date(2024, 1, 15)) == 10

    def test_weekend_start_to_monday(self):
        # Saturday to Monday: end date is exclusive, Saturday/Sunday skipped → 0
        assert business_days_between(date(2024, 1, 20), date(2024, 1, 22)) == 0


# ── effective_impact_days ──────────────────────────────────────────────────

class TestEffectiveImpactDays:
    def test_zero_percent_returns_zero(self):
        assert effective_impact_days(10.0, 0.0) == 0.0

    def test_hundred_percent_returns_full(self):
        assert effective_impact_days(10.0, 100.0) == pytest.approx(10.0)

    def test_partial_returns_proportional(self):
        assert effective_impact_days(10.0, 40.0) == pytest.approx(4.0)

    def test_partial_open_risk_counts(self):
        # Realised % is independent of status — open risks with partial
        # realisation still contribute to the realised total.
        assert effective_impact_days(8.0, 25.0) == pytest.approx(2.0)

    def test_zero_impact_returns_zero(self):
        assert effective_impact_days(0.0, 75.0) == 0.0


class TestUnrealisedExposureDays:
    def test_open_zero_percent_full_exposure(self):
        assert unrealised_exposure_days(10.0, "todo", 0.0) == pytest.approx(10.0)

    def test_open_partial_realised(self):
        # 10 days × (1 - 30%) = 7 days still at risk
        assert unrealised_exposure_days(10.0, "doing", 30.0) == pytest.approx(7.0)

    def test_closed_risk_has_no_exposure(self):
        # Closed risks have zero remaining exposure regardless of realised %
        assert unrealised_exposure_days(10.0, "done", 0.0) == 0.0
        assert unrealised_exposure_days(10.0, "done", 50.0) == 0.0
        assert unrealised_exposure_days(10.0, "done", 100.0) == 0.0


class TestResolutionLabel:
    def test_open_risks_have_no_label(self):
        assert resolution_label("todo", 50.0) == ""
        assert resolution_label("doing", 100.0) == ""

    def test_closed_zero_is_avoided(self):
        assert resolution_label("done", 0.0) == "Avoided"

    def test_closed_full_is_realised(self):
        assert resolution_label("done", 100.0) == "Realised"

    def test_closed_partial_is_mitigated(self):
        assert resolution_label("done", 1.0) == "Mitigated"
        assert resolution_label("done", 50.0) == "Mitigated"
        assert resolution_label("done", 99.0) == "Mitigated"


# ── deliverable_summary ────────────────────────────────────────────────────

class TestDeliverableSummary:
    def test_basic_summary(self):
        d = {"budget_days": 10.0, "percent_complete": 50}
        result = deliverable_summary(d, day_rate=1000.0)
        assert result["budget_dollars"] == 10_000.0
        assert result["remaining_days"] == 5.0
        assert result["remaining_dollars"] == 5_000.0

    def test_zero_percent_complete(self):
        d = {"budget_days": 8.0, "percent_complete": 0}
        result = deliverable_summary(d, day_rate=500.0)
        assert result["remaining_days"] == 8.0
        assert result["remaining_dollars"] == 4_000.0

    def test_fully_complete(self):
        d = {"budget_days": 8.0, "percent_complete": 100}
        result = deliverable_summary(d, day_rate=500.0)
        assert result["remaining_days"] == 0.0
        assert result["remaining_dollars"] == 0.0

    def test_original_fields_preserved(self):
        d = {"budget_days": 5.0, "percent_complete": 25, "name": "Design"}
        result = deliverable_summary(d, day_rate=1000.0)
        assert result["name"] == "Design"


# ── requirement_summary ────────────────────────────────────────────────────

class TestRequirementSummary:
    def _make_del(self, budget_days, pct, rate=1000.0):
        d = {"budget_days": budget_days, "percent_complete": pct}
        return deliverable_summary(d, rate)

    def test_aggregates_totals(self):
        dels = [self._make_del(10, 0), self._make_del(10, 0)]
        req = {"id": 1, "name": "Req"}
        result = requirement_summary(req, dels, 1000.0)
        assert result["total_days"] == 20.0
        assert result["total_dollars"] == 20_000.0
        assert result["remaining_days"] == 20.0

    def test_weighted_completion(self):
        # 10 days at 100% and 10 days at 0% → 50% weighted
        dels = [self._make_del(10, 100), self._make_del(10, 0)]
        req = {"id": 1, "name": "Req"}
        result = requirement_summary(req, dels, 1000.0)
        assert result["weighted_completion"] == pytest.approx(50.0)

    def test_empty_deliverables(self):
        req = {"id": 1, "name": "Req"}
        result = requirement_summary(req, [], 1000.0)
        assert result["total_days"] == 0.0
        assert result["weighted_completion"] == 0.0


# ── feature_summary ────────────────────────────────────────────────────────

class TestFeatureSummary:
    def _make_req(self, total_days, weighted_completion, total_dollars=None):
        if total_dollars is None:
            total_dollars = total_days * 1000.0
        return {
            "total_days": total_days,
            "total_dollars": total_dollars,
            "remaining_days": total_days * (1 - weighted_completion / 100),
            "remaining_dollars": total_dollars * (1 - weighted_completion / 100),
            "weighted_completion": weighted_completion,
            "deliverables": [],
        }

    def test_aggregates_requirements(self):
        reqs = [self._make_req(10, 50), self._make_req(10, 50)]
        feature = {"id": 1, "name": "Feature"}
        result = feature_summary(feature, reqs)
        assert result["total_days"] == 20.0
        assert result["weighted_completion"] == pytest.approx(50.0)

    def test_unequal_weighted_completion(self):
        # 10 days at 100%, 30 days at 0% → 25% weighted
        reqs = [self._make_req(10, 100), self._make_req(30, 0)]
        feature = {"id": 1, "name": "Feature"}
        result = feature_summary(feature, reqs)
        assert result["weighted_completion"] == pytest.approx(25.0)

    def test_empty_requirements(self):
        feature = {"id": 1, "name": "Feature"}
        result = feature_summary(feature, [])
        assert result["total_days"] == 0.0
        assert result["weighted_completion"] == 0.0


# ── project_summary ────────────────────────────────────────────────────────

class TestProjectSummary:
    def _make_project(self, budget=100_000, team_size=2, spend=0,
                      start="2024-01-15", as_of="2024-01-22"):
        return {
            "initial_budget": budget,
            "team_size": team_size,
            "actual_spend": spend,
            "start_date": start,
            "as_of_date": as_of,
        }

    def test_basic_budget_days_remaining(self):
        # Days remaining = accessible_budget / daily_burn
        # With $0 actual spend and $100k budget at $1k/day → 100 days
        proj = self._make_project(budget=100_000, team_size=1, spend=0)
        result = project_summary(proj, [], [], default_day_rate=1_000.0)
        assert result["budget_days_remaining"] == pytest.approx(100.0)

    def test_budget_days_remaining_with_spend(self):
        # $10k spent from $100k budget at $1k/day → 90 days remaining
        # (spend is subtracted once, via current_budget → accessible_budget)
        proj = self._make_project(budget=100_000, team_size=1, spend=10_000)
        result = project_summary(proj, [], [], default_day_rate=1_000.0)
        assert result["budget_days_remaining"] == pytest.approx(90.0)

    def test_total_budget_includes_adjustments(self):
        proj = self._make_project(budget=100_000)
        adjustments = [{"amount": 10_000}, {"amount": -5_000}]
        result = project_summary(proj, [], adjustments, default_day_rate=1_000.0)
        assert result["total_budget"] == 105_000.0

    def test_current_budget_subtracts_actual_spend(self):
        # current_budget = total_budget − actual_spend.
        # Spend that has been invoiced is no longer accessible.
        proj = self._make_project(budget=100_000, spend=30_000)
        result = project_summary(proj, [], [], default_day_rate=1_000.0)
        assert result["total_budget"] == 100_000.0
        assert result["current_budget"] == 70_000.0

    def test_current_budget_combines_adjustments_and_spend(self):
        proj = self._make_project(budget=100_000, spend=15_000)
        adjustments = [{"amount": 10_000}]
        result = project_summary(proj, [], adjustments, default_day_rate=1_000.0)
        assert result["total_budget"] == 110_000.0
        assert result["current_budget"] == 95_000.0

    def test_realised_risk_alone_does_not_reduce_accessible_budget(self):
        # Realised risks represent team time already in actual_spend (a
        # categorisation of how spend was used). Passing realised_risk_dollars
        # without spend means the data is inconsistent — but the calc must
        # not double-count. Accessible reflects only spend and overheads.
        proj = self._make_project(budget=100_000, team_size=1, spend=0)
        result = project_summary(proj, [], [], default_day_rate=1_000.0, realised_risk_dollars=10_000.0)
        assert result["accessible_budget"] == 100_000.0
        assert result["realised_risk_dollars"] == 10_000.0

    def test_realised_risk_categorises_spend_not_additive(self):
        # When realised risk time is reflected in actual_spend (the consistent
        # case), accessible drops by the spend amount only — not by spend +
        # realised. realised_risk_dollars then describes what slice of that
        # spend went on risk handling.
        proj = self._make_project(budget=100_000, team_size=1, spend=10_000)
        result = project_summary(proj, [], [], default_day_rate=1_000.0, realised_risk_dollars=10_000.0)
        assert result["accessible_budget"] == 90_000.0   # = 100k − spend; no extra realised deduction
        assert result["realised_risk_dollars"] == 10_000.0

    def test_budget_days_remaining_uses_accessible_budget(self):
        proj = self._make_project(budget=100_000, team_size=1, spend=20_000,
                                  start="2024-01-15", as_of="2024-01-15")
        # spend=20k → current_budget=80k; no overhead → accessible=80k → 80 days
        result = project_summary(proj, [], [], default_day_rate=1_000.0, realised_risk_dollars=20_000.0)
        assert result["budget_days_remaining"] == pytest.approx(80.0)

    def test_zero_realised_risk_keeps_full_budget(self):
        proj = self._make_project(budget=100_000, team_size=1, spend=0,
                                  start="2024-01-15", as_of="2024-01-15")
        result = project_summary(proj, [], [], default_day_rate=1_000.0)
        assert result["accessible_budget"] == 100_000.0
        assert result["budget_days_remaining"] == pytest.approx(100.0)

    def test_overhead_reduces_accessible_budget(self):
        # $10k of overheads on $100k budget → $90k accessible
        proj = self._make_project(budget=100_000, team_size=1, spend=0)
        result = project_summary(proj, [], [], default_day_rate=1_000.0, overhead_dollars=10_000.0)
        assert result["accessible_budget"] == 90_000.0
        assert result["overhead_dollars"] == 10_000.0

    def test_overhead_reduces_budget_days_remaining(self):
        # No elapsed days, $100k budget, $20k overhead at $1k/day → 80 days
        proj = self._make_project(budget=100_000, team_size=1, spend=0,
                                  start="2024-01-15", as_of="2024-01-15")
        result = project_summary(proj, [], [], default_day_rate=1_000.0, overhead_dollars=20_000.0)
        assert result["budget_days_remaining"] == pytest.approx(80.0)

    def test_overhead_reduces_unallocated_budget(self):
        # $100k budget, $30k allocated to features, $20k overhead → $50k unallocated
        proj = self._make_project(budget=100_000)
        features = [
            {"total_days": 30, "total_dollars": 30_000, "remaining_days": 30,
             "remaining_dollars": 30_000, "weighted_completion": 0.0},
        ]
        result = project_summary(proj, features, [], default_day_rate=1_000.0, overhead_dollars=20_000.0)
        assert result["unallocated_budget"] == 50_000.0
        # Identity: features + overheads + realised_risks + unallocated == total_budget
        assert (result["allocated_dollars"] + result["overhead_dollars"]
                + result["realised_risk_dollars"] + result["unallocated_budget"]) == pytest.approx(result["total_budget"])

    def test_open_risk_dollars_default_zero(self):
        # open_risk_dollars defaults to 0 when not supplied and the summary
        # still carries the field for the dashboard template.
        proj = self._make_project(budget=100_000, team_size=1, spend=0)
        result = project_summary(proj, [], [], default_day_rate=1_000.0)
        assert result["open_risk_dollars"] == 0.0

    def test_open_risk_dollars_round_trips(self):
        # open_risk_dollars is pass-through metadata — does not affect other
        # computed values, only reported for the 'at risk' badge.
        proj = self._make_project(budget=100_000, team_size=1, spend=0)
        result = project_summary(
            proj, [], [], default_day_rate=1_000.0,
            realised_risk_dollars=5_000.0, open_risk_dollars=8_000.0,
        )
        assert result["open_risk_dollars"] == 8_000.0
        # Accessible budget excludes spend + overhead. Realised risks are
        # part of spend (here spend=0 so accessible == total).
        assert result["accessible_budget"] == 100_000.0
        # Unallocated is the *allocation* view: total − features − overhead
        # − realised_risk earmark. So realised still appears here as an
        # earmark even though it doesn't reduce accessible.
        assert result["unallocated_budget"] == 95_000.0

    def test_realised_risk_excluded_from_unallocated(self):
        # Realised risk dollars must not appear as unallocated budget.
        # $100k budget, $10k risk, $20k overhead, $30k features → $40k unallocated
        proj = self._make_project(budget=100_000)
        features = [
            {"total_days": 30, "total_dollars": 30_000, "remaining_days": 30,
             "remaining_dollars": 30_000, "weighted_completion": 0.0},
        ]
        result = project_summary(
            proj, features, [], default_day_rate=1_000.0,
            realised_risk_dollars=10_000.0, overhead_dollars=20_000.0,
        )
        assert result["unallocated_budget"] == pytest.approx(40_000.0)
        assert (result["allocated_dollars"] + result["overhead_dollars"]
                + result["realised_risk_dollars"] + result["unallocated_budget"]) == pytest.approx(result["total_budget"])

    def test_overhead_reduces_accessible_realised_does_not(self):
        # Overhead is an additional deduction; realised risk is a sub-category
        # of spend (here spend=0 so realised has no effect on accessible).
        # $100k − $0 spend − $10k overhead = $90k accessible.
        proj = self._make_project(budget=100_000, team_size=1, spend=0)
        result = project_summary(
            proj, [], [], default_day_rate=1_000.0,
            realised_risk_dollars=5_000.0, overhead_dollars=10_000.0,
        )
        assert result["accessible_budget"] == 90_000.0
        assert result["realised_risk_dollars"] == 5_000.0
        assert result["overhead_dollars"] == 10_000.0

    def test_zero_overhead_keeps_full_budget(self):
        # Default overhead_dollars=0.0 → no change to accessible or unallocated
        proj = self._make_project(budget=100_000, team_size=1, spend=0,
                                  start="2024-01-15", as_of="2024-01-15")
        result = project_summary(proj, [], [], default_day_rate=1_000.0)
        assert result["overhead_dollars"] == 0.0
        assert result["accessible_budget"] == 100_000.0
        assert result["unallocated_budget"] == 100_000.0

    def test_expected_burn_pct(self):
        # 1 person, $1k/day, $100k budget, 5 days elapsed → 5% expected burn
        proj = self._make_project(budget=100_000, team_size=1, spend=0)
        result = project_summary(proj, [], [], default_day_rate=1_000.0)
        assert result["expected_burn_pct"] == pytest.approx(5.0)

    def test_feature_expected_burn_pct_excludes_overhead(self):
        # $100k budget, $20k overhead → feature budget = $80k
        # 1 person, $1k/day, 5 days elapsed → expected_spend = $5k
        # feature_expected_burn_pct = 5_000 / 80_000 * 100 = 6.25%
        proj = self._make_project(budget=100_000, team_size=1, spend=0)
        result = project_summary(proj, [], [], default_day_rate=1_000.0, overhead_dollars=20_000.0)
        assert result["feature_expected_burn_pct"] == pytest.approx(6.25)

    def test_feature_expected_burn_pct_no_overhead_matches_expected(self):
        # With no overhead, feature_expected_burn_pct should equal expected_burn_pct
        proj = self._make_project(budget=100_000, team_size=1, spend=0)
        result = project_summary(proj, [], [], default_day_rate=1_000.0)
        assert result["feature_expected_burn_pct"] == pytest.approx(result["expected_burn_pct"])

    def test_overall_completion_weighted_by_days(self):
        proj = self._make_project()
        features = [
            {"total_days": 10, "total_dollars": 10_000, "remaining_days": 0,
             "remaining_dollars": 0, "weighted_completion": 100.0},
            {"total_days": 30, "total_dollars": 30_000, "remaining_days": 30,
             "remaining_dollars": 30_000, "weighted_completion": 0.0},
        ]
        result = project_summary(proj, features, [], default_day_rate=1_000.0)
        assert result["overall_completion"] == pytest.approx(25.0)


# ── feature_health ─────────────────────────────────────────────────────────

class TestFeatureHealth:
    def _make_feature(self, total_dollars=10_000, weighted_completion=50.0):
        return {"total_dollars": total_dollars, "weighted_completion": weighted_completion}

    def test_not_budgeted_when_no_dollars(self):
        f = self._make_feature(total_dollars=0)
        result = feature_health(f, expected_burn_pct=50.0, on_track_threshold=100.0, at_risk_threshold=80.0)
        assert result["status"] == "not_budgeted"

    def test_on_track(self):
        # completion=50, expected_burn=50 → at 100% threshold → on_track
        f = self._make_feature(weighted_completion=50.0)
        result = feature_health(f, expected_burn_pct=50.0, on_track_threshold=100.0, at_risk_threshold=80.0)
        assert result["status"] == "on_track"

    def test_at_risk(self):
        # completion=41, expected_burn=50 → 82% of target (between 80-100%) → at_risk
        f = self._make_feature(weighted_completion=41.0)
        result = feature_health(f, expected_burn_pct=50.0, on_track_threshold=100.0, at_risk_threshold=80.0)
        assert result["status"] == "at_risk"

    def test_behind(self):
        # completion=30, expected_burn=50 → 60% of target (below 80%) → behind
        f = self._make_feature(weighted_completion=30.0)
        result = feature_health(f, expected_burn_pct=50.0, on_track_threshold=100.0, at_risk_threshold=80.0)
        assert result["status"] == "behind"

    def test_zero_expected_burn_is_on_track(self):
        # No time has elapsed yet — everything is on track
        f = self._make_feature(weighted_completion=0.0)
        result = feature_health(f, expected_burn_pct=0.0, on_track_threshold=100.0, at_risk_threshold=80.0)
        assert result["status"] == "on_track"

    def test_badge_class_matches_status(self):
        f = self._make_feature(weighted_completion=50.0)
        result = feature_health(f, 50.0, 100.0, 80.0)
        assert result["badge_class"] == "badge-green"

    def test_labels_present(self):
        f = self._make_feature(weighted_completion=0.0)
        result = feature_health(f, 50.0, 100.0, 80.0)
        assert "label" in result
        assert result["label"] == "Behind"


# ── get_week_monday ────────────────────────────────────────────────────────

class TestGetWeekMonday:
    def test_monday_returns_itself(self):
        monday = date(2024, 1, 15)  # known Monday
        assert get_week_monday(monday) == monday

    def test_wednesday_returns_monday(self):
        wednesday = date(2024, 1, 17)
        assert get_week_monday(wednesday) == date(2024, 1, 15)

    def test_sunday_returns_previous_monday(self):
        sunday = date(2024, 1, 21)
        assert get_week_monday(sunday) == date(2024, 1, 15)


# ── capacity_days_remaining ────────────────────────────────────────────────

class TestCapacityDaysRemaining:
    def _monday(self, y, m, d):
        return date(y, m, d)

    def test_no_capacity_uses_default_burn(self):
        # $5000 budget, $1000/day default, no capacity periods → 5 days
        result = capacity_days_remaining(
            remaining_budget=5_000.0,
            as_of_date=date(2024, 1, 15),  # Monday
            capacity_periods=[],
            default_daily_burn=1_000.0,
        )
        assert result == pytest.approx(5.0)

    def test_capacity_period_overrides_burn(self):
        # $2000 budget, capacity period: 1 person at $500/day for this week.
        # Should give 4 days (staying within the capacity week).
        monday = date(2024, 1, 15)
        periods = [{"week_monday": monday, "day_rate": 500.0, "team_size": 1}]
        result = capacity_days_remaining(
            remaining_budget=2_000.0,
            as_of_date=monday,
            capacity_periods=periods,
            default_daily_burn=1_000.0,
        )
        assert result == pytest.approx(4.0)

    def test_skips_weekends(self):
        # Friday start, $1000 budget at $1000/day → 1 day (skips weekend)
        friday = date(2024, 1, 19)
        result = capacity_days_remaining(
            remaining_budget=1_000.0,
            as_of_date=friday,
            capacity_periods=[],
            default_daily_burn=1_000.0,
        )
        assert result == pytest.approx(1.0)

    def test_zero_budget_returns_zero(self):
        result = capacity_days_remaining(
            remaining_budget=0.0,
            as_of_date=date(2024, 1, 15),
            capacity_periods=[],
            default_daily_burn=1_000.0,
        )
        assert result == pytest.approx(0.0)

    def test_partial_day(self):
        # $1500 at $1000/day → 1.5 days
        result = capacity_days_remaining(
            remaining_budget=1_500.0,
            as_of_date=date(2024, 1, 15),
            capacity_periods=[],
            default_daily_burn=1_000.0,
        )
        assert result == pytest.approx(1.5)

    def test_multiple_role_periods_same_week(self):
        # Two roles in same week: $500/day each = $1000/day total
        # $5000 budget → 5 days
        monday = date(2024, 1, 15)
        periods = [
            {"week_monday": monday, "day_rate": 500.0, "team_size": 1},
            {"week_monday": monday, "day_rate": 500.0, "team_size": 1},
        ]
        result = capacity_days_remaining(
            remaining_budget=5_000.0,
            as_of_date=monday,
            capacity_periods=periods,
            default_daily_burn=2_000.0,
        )
        assert result == pytest.approx(5.0)


# ── capacity_plan_summary ──────────────────────────────────────────────────

class TestCapacityPlanSummary:
    def test_no_periods_uses_default_team(self):
        # 5 business days, default team size 2 → 10 person-days
        as_of = date(2024, 1, 15)  # Monday
        end = date(2024, 1, 22)    # Next Monday (5 business days)
        result = capacity_plan_summary(
            as_of_date=as_of,
            end_date=end,
            capacity_periods=[],
            default_team_size=2,
            default_daily_burn=2_000.0,
        )
        assert result["total_person_days"] == pytest.approx(10.0)
        assert result["has_periods"] is False

    def test_with_periods_counts_correctly(self):
        as_of = date(2024, 1, 15)
        end = date(2024, 1, 22)
        # 3 people for this week
        periods = [{
            "week_monday": date(2024, 1, 15),
            "day_rate": 1000.0,
            "team_size": 3,
            "role_name": "Developer",
        }]
        result = capacity_plan_summary(
            as_of_date=as_of,
            end_date=end,
            capacity_periods=periods,
            default_team_size=1,
            default_daily_burn=1_000.0,
        )
        assert result["total_person_days"] == pytest.approx(15.0)  # 3 × 5 days
        assert result["has_periods"] is True

    def test_two_week_breakdown_by_role(self):
        as_of = date(2024, 1, 15)
        end = date(2024, 2, 12)
        periods = [{
            "week_monday": date(2024, 1, 15),
            "day_rate": 1000.0,
            "team_size": 2,
            "role_name": "Developer",
        }]
        result = capacity_plan_summary(
            as_of_date=as_of,
            end_date=end,
            capacity_periods=periods,
            default_team_size=1,
            default_daily_burn=1_000.0,
        )
        # 2 people for 5 days in the first week (within 2-week window)
        assert result["two_week_by_role"].get("Developer", 0) == pytest.approx(10.0)


# ── capacity_budget_summary ────────────────────────────────────────────────

class TestCapacityBudgetSummary:
    def test_no_periods_uses_default_burn_and_team_size(self):
        # $5000 budget at $1000/day default, team_size=2 → 5 budget days, 10 person-days
        result = capacity_budget_summary(
            remaining_budget=5_000.0,
            as_of_date=date(2024, 1, 15),  # Monday
            capacity_periods=[],
            default_daily_burn=1_000.0,
            default_team_size=2,
        )
        assert result["budget_days"] == pytest.approx(5.0)
        assert result["person_days"] == pytest.approx(10.0)

    def test_with_capacity_period_uses_period_burn_and_size(self):
        # $2000 budget, 1 person at $500/day → 4 budget days, 4 person-days
        monday = date(2024, 1, 15)
        periods = [{"week_monday": monday, "day_rate": 500.0, "team_size": 1}]
        result = capacity_budget_summary(
            remaining_budget=2_000.0,
            as_of_date=monday,
            capacity_periods=periods,
            default_daily_burn=1_000.0,
            default_team_size=3,
        )
        assert result["budget_days"] == pytest.approx(4.0)
        assert result["person_days"] == pytest.approx(4.0)

    def test_multi_role_same_week_sums_headcount(self):
        # 2 devs at $500/day + 1 designer at $800/day = $1800/day burn, 3 people/day
        # $3600 budget → 2 budget days, 6 person-days
        monday = date(2024, 1, 15)
        periods = [
            {"week_monday": monday, "day_rate": 500.0, "team_size": 2},
            {"week_monday": monday, "day_rate": 800.0, "team_size": 1},
        ]
        result = capacity_budget_summary(
            remaining_budget=3_600.0,
            as_of_date=monday,
            capacity_periods=periods,
            default_daily_burn=1_000.0,
            default_team_size=1,
        )
        assert result["budget_days"] == pytest.approx(2.0)
        assert result["person_days"] == pytest.approx(6.0)

    def test_partial_last_day(self):
        # $1500 at $1000/day, team_size=4 → 1.5 budget days, 6 person-days
        result = capacity_budget_summary(
            remaining_budget=1_500.0,
            as_of_date=date(2024, 1, 15),
            capacity_periods=[],
            default_daily_burn=1_000.0,
            default_team_size=4,
        )
        assert result["budget_days"] == pytest.approx(1.5)
        assert result["person_days"] == pytest.approx(6.0)

    def test_zero_budget_returns_zero(self):
        result = capacity_budget_summary(
            remaining_budget=0.0,
            as_of_date=date(2024, 1, 15),
            capacity_periods=[],
            default_daily_burn=1_000.0,
            default_team_size=2,
        )
        assert result["budget_days"] == pytest.approx(0.0)
        assert result["person_days"] == pytest.approx(0.0)

    def test_skips_weekends(self):
        # Friday start, $2000 at $1000/day, team_size=2 → 2 budget days skipping weekend
        friday = date(2024, 1, 19)
        result = capacity_budget_summary(
            remaining_budget=2_000.0,
            as_of_date=friday,
            capacity_periods=[],
            default_daily_burn=1_000.0,
            default_team_size=2,
        )
        assert result["budget_days"] == pytest.approx(2.0)
        assert result["person_days"] == pytest.approx(4.0)


# ── milestones_summary / fixed_price_project_summary ─────────────────────

def _feat(fid, days, completion):
    """Minimal feature dict shaped like feature_summary output for fixed-price tests."""
    return {
        "id": fid,
        "name": f"F{fid}",
        "total_days": days,
        "total_dollars": days * 1000,
        "weighted_completion": completion,
        "remaining_days": days * (1 - completion / 100),
        "remaining_dollars": days * (1 - completion / 100) * 1000,
    }


class TestMilestonesSummary:
    def test_bar_widths_proportional_to_value(self):
        milestones = [
            {"id": 1, "name": "A", "description": "", "value": 10_000, "sort_order": 1},
            {"id": 2, "name": "B", "description": "", "value": 20_000, "sort_order": 2},
            {"id": 3, "name": "C", "description": "", "value": 30_000, "sort_order": 3},
        ]
        result = milestones_summary(milestones, [], [], [])
        # Widths: 1/6 ≈ 16.67, 2/6 ≈ 33.33, 3/6 = 50.00
        assert result[0]["bar_width_pct"] == pytest.approx(100 / 6)
        assert result[1]["bar_width_pct"] == pytest.approx(200 / 6)
        assert result[2]["bar_width_pct"] == pytest.approx(50.0)
        # Starts are cumulative
        assert result[0]["bar_start_pct"] == pytest.approx(0.0)
        assert result[1]["bar_start_pct"] == pytest.approx(100 / 6)
        assert result[2]["bar_start_pct"] == pytest.approx(50.0)

    def test_empty_milestones_returns_empty(self):
        assert milestones_summary([], [], [], []) == []

    def test_status_derived_from_invoices(self):
        milestones = [
            {"id": 1, "name": "A", "description": "", "value": 10_000, "sort_order": 1},
        ]
        # No invoices → pending
        out = milestones_summary(milestones, [], [], [])
        assert out[0]["status"] == "pending"
        # Partial invoice, not fully paid → invoiced
        invoices = [{"id": 1, "milestone_id": 1, "amount": 5_000, "status": "invoiced"}]
        out = milestones_summary(milestones, invoices, [], [])
        assert out[0]["status"] == "invoiced"
        assert out[0]["invoiced_amount"] == 5_000
        assert out[0]["paid_amount"] == 0
        # Fully paid up to value → paid
        invoices = [{"id": 1, "milestone_id": 1, "amount": 10_000, "status": "paid"}]
        out = milestones_summary(milestones, invoices, [], [])
        assert out[0]["status"] == "paid"
        assert out[0]["paid_amount"] == 10_000

    def test_linked_completion_weighted_by_feature_days(self):
        milestones = [{"id": 1, "name": "A", "description": "", "value": 10_000, "sort_order": 1}]
        features = [_feat(1, 10, 100), _feat(2, 30, 0)]  # 10d @ 100% + 30d @ 0% = 25%
        links = [{"milestone_id": 1, "feature_id": 1}, {"milestone_id": 1, "feature_id": 2}]
        out = milestones_summary(milestones, [], features, links)
        assert out[0]["linked_completion_pct"] == pytest.approx(25.0)
        assert sorted(out[0]["linked_feature_ids"]) == [1, 2]

    def test_colour_band_bands(self):
        m = [{"id": 1, "name": "A", "description": "", "value": 100, "sort_order": 1}]
        # 0% → pending
        out = milestones_summary(m, [], [_feat(1, 10, 0)], [{"milestone_id": 1, "feature_id": 1}])
        assert out[0]["colour_band"] == "pending"
        # 60% → in_progress
        out = milestones_summary(m, [], [_feat(1, 10, 60)], [{"milestone_id": 1, "feature_id": 1}])
        assert out[0]["colour_band"] == "in_progress"
        # 100% → ready
        out = milestones_summary(m, [], [_feat(1, 10, 100)], [{"milestone_id": 1, "feature_id": 1}])
        assert out[0]["colour_band"] == "ready"
        # Any invoice → invoiced band wins over completion
        invoices = [{"id": 1, "milestone_id": 1, "amount": 50, "status": "invoiced"}]
        out = milestones_summary(m, invoices, [_feat(1, 10, 0)], [{"milestone_id": 1, "feature_id": 1}])
        assert out[0]["colour_band"] == "invoiced"
        # Fully paid → paid band
        invoices = [{"id": 1, "milestone_id": 1, "amount": 100, "status": "paid"}]
        out = milestones_summary(m, invoices, [_feat(1, 10, 0)], [{"milestone_id": 1, "feature_id": 1}])
        assert out[0]["colour_band"] == "paid"

    def test_sort_order_governs_bar_placement(self):
        # Even if passed out of order, sort_order determines placement.
        milestones = [
            {"id": 2, "name": "Second", "description": "", "value": 10, "sort_order": 2},
            {"id": 1, "name": "First", "description": "", "value": 10, "sort_order": 1},
        ]
        out = milestones_summary(milestones, [], [], [])
        assert out[0]["id"] == 1
        assert out[1]["id"] == 2


class TestFixedPriceProjectSummary:
    def _project(self, **overrides):
        base = {
            "id": 1,
            "initial_budget": 0,
            "actual_spend": 0,
            "team_size": 1,
            "start_date": "",
            "as_of_date": "",
        }
        base.update(overrides)
        return base

    def test_total_budget_is_sum_of_milestone_values(self):
        milestones = milestones_summary([
            {"id": 1, "name": "A", "description": "", "value": 10_000, "sort_order": 1},
            {"id": 2, "name": "B", "description": "", "value": 20_000, "sort_order": 2},
            {"id": 3, "name": "C", "description": "", "value": 30_000, "sort_order": 3},
        ], [], [], [])
        result = fixed_price_project_summary(self._project(), [], milestones, default_day_rate=1_000.0)
        assert result["total_budget"] == 60_000

    def test_margin_equals_paid_minus_spent(self):
        milestones = milestones_summary([
            {"id": 1, "name": "A", "description": "", "value": 10_000, "sort_order": 1},
        ], [{"id": 1, "milestone_id": 1, "amount": 10_000, "status": "paid"}], [], [])
        result = fixed_price_project_summary(
            self._project(actual_spend=4_000),
            [],
            milestones,
            default_day_rate=1_000.0,
        )
        assert result["paid_to_date"] == 10_000
        assert result["invoiced_to_date"] == 10_000
        assert result["margin"] == 6_000
        assert result["projected_margin"] == 6_000

    def test_projected_margin_includes_invoiced_not_yet_paid(self):
        milestones = milestones_summary([
            {"id": 1, "name": "A", "description": "", "value": 10_000, "sort_order": 1},
        ], [{"id": 1, "milestone_id": 1, "amount": 10_000, "status": "invoiced"}], [], [])
        result = fixed_price_project_summary(
            self._project(actual_spend=2_000),
            [],
            milestones,
            default_day_rate=1_000.0,
        )
        assert result["paid_to_date"] == 0
        assert result["invoiced_to_date"] == 10_000
        assert result["margin"] == -2_000
        assert result["projected_margin"] == 8_000

    def test_next_milestone_skips_paid(self):
        raw = [
            {"id": 1, "name": "A", "description": "", "value": 10, "sort_order": 1},
            {"id": 2, "name": "B", "description": "", "value": 10, "sort_order": 2},
        ]
        invoices = [{"id": 1, "milestone_id": 1, "amount": 10, "status": "paid"}]
        milestones = milestones_summary(raw, invoices, [], [])
        result = fixed_price_project_summary(self._project(), [], milestones, default_day_rate=1_000.0)
        assert result["next_milestone"]["id"] == 2
        assert result["paid_count"] == 1

    def test_next_milestone_none_when_all_paid(self):
        raw = [{"id": 1, "name": "A", "description": "", "value": 10, "sort_order": 1}]
        invoices = [{"id": 1, "milestone_id": 1, "amount": 10, "status": "paid"}]
        milestones = milestones_summary(raw, invoices, [], [])
        result = fixed_price_project_summary(self._project(), [], milestones, default_day_rate=1_000.0)
        assert result["next_milestone"] is None

    def test_overall_completion_weighted_days(self):
        features = [_feat(1, 10, 100), _feat(2, 30, 0)]  # 10/40 = 25%
        result = fixed_price_project_summary(self._project(), features, [], default_day_rate=1_000.0)
        assert result["overall_completion"] == pytest.approx(25.0)



# ── Overhead-team projection ───────────────────────────────────────────────

class TestProjectedOverheadTeamDollars:
    def _project(self, start="2024-01-15", end="2024-02-12",
                 as_of="2024-01-22", overhead_team_size=0,
                 default_overhead_role_id=0):
        return {
            "start_date": start,
            "end_date": end,
            "as_of_date": as_of,
            "overhead_team_size": overhead_team_size,
            "default_overhead_role_id": default_overhead_role_id,
        }

    def _delivery_role(self, id=1, rate=1000.0):
        return {"id": id, "name": "Dev", "day_rate": rate, "category": "delivery"}

    def _overhead_role(self, id=2, rate=800.0, name="BA"):
        return {"id": id, "name": name, "day_rate": rate, "category": "overhead"}

    def test_zero_when_no_dates(self):
        proj = self._project(start="", end="")
        result = projected_overhead_team_dollars(proj, [], [self._overhead_role()])
        assert result["total_dollars"] == 0.0

    def test_zero_when_no_overhead_role(self):
        proj = self._project(overhead_team_size=2, default_overhead_role_id=0)
        result = projected_overhead_team_dollars(proj, [], [self._delivery_role()])
        assert result["total_dollars"] == 0.0

    def test_extrapolates_from_defaults(self):
        # 2024-01-15 (Mon) to 2024-02-12 (Mon) exclusive = 4 weeks × 5 = 20 bd
        # 1 person × $800/day × 20 days = $16k
        proj = self._project(overhead_team_size=1, default_overhead_role_id=2)
        result = projected_overhead_team_dollars(proj, [], [self._overhead_role()])
        assert result["total_dollars"] == pytest.approx(16_000.0)
        assert result["total_business_days"] == 20

    def test_capacity_period_overrides_default(self):
        # Same window: week of 2024-01-15 has 3 BAs at $800 instead of 1
        # week 1 (5 bd): 3 × 800 = $12k; weeks 2-4 (15 bd): 1 × 800 = $12k → $24k
        proj = self._project(overhead_team_size=1, default_overhead_role_id=2)
        cps = [{
            "week_monday": date(2024, 1, 15),
            "role_id": 2, "role_name": "BA", "role_category": "overhead",
            "team_size": 3, "day_rate": 800.0,
        }]
        result = projected_overhead_team_dollars(proj, cps, [self._overhead_role()])
        assert result["total_dollars"] == pytest.approx(24_000.0)

    def test_delivery_periods_ignored(self):
        # A delivery-category capacity row must NOT contribute to overhead total
        proj = self._project(overhead_team_size=0, default_overhead_role_id=0)
        cps = [{
            "week_monday": date(2024, 1, 15),
            "role_id": 1, "role_name": "Dev", "role_category": "delivery",
            "team_size": 5, "day_rate": 1000.0,
        }]
        result = projected_overhead_team_dollars(proj, cps, [self._delivery_role()])
        assert result["total_dollars"] == 0.0

    def test_realised_dollars_at_as_of(self):
        # 4-week project, as_of one week in → realised should be ~25%
        proj = self._project(start="2024-01-15", end="2024-02-12",
                             as_of="2024-01-22",
                             overhead_team_size=1, default_overhead_role_id=2)
        result = projected_overhead_team_dollars(proj, [], [self._overhead_role()])
        # 5 bd elapsed of 20 bd total = 25%
        assert result["realised_dollars"] == pytest.approx(result["total_dollars"] * 0.25)
        assert result["remaining_dollars"] == pytest.approx(result["total_dollars"] * 0.75)


# ── Agile project summary with overhead-team integration ───────────────────

class TestAgileSummaryWithOverheadTeam:
    def _make_project(self, budget=200_000, team_size=2, spend=0,
                      start="2024-01-15", as_of="2024-01-22"):
        return {
            "initial_budget": budget,
            "team_size": team_size,
            "actual_spend": spend,
            "start_date": start,
            "as_of_date": as_of,
        }

    def test_overhead_team_reduces_accessible_budget(self):
        # Like fixed overheads, overhead-team total deducts from accessible.
        proj = self._make_project(budget=200_000, team_size=1, spend=0)
        oht = {
            "total_dollars": 30_000.0, "realised_dollars": 0.0,
            "remaining_dollars": 30_000.0, "daily_burn": 0.0,
            "headcount": 0, "by_role": {},
        }
        result = agile_project_summary(
            proj, [], [], default_day_rate=1_000.0,
            fixed_overhead_dollars=10_000.0, overhead_team=oht,
        )
        # Combined overhead = $40k. Accessible = $200k − $40k = $160k.
        assert result["overhead_dollars"] == 40_000.0
        assert result["fixed_overhead_dollars"] == 10_000.0
        assert result["overhead_team_dollars"] == 30_000.0
        assert result["accessible_budget"] == 160_000.0

    def test_daily_burn_excludes_overhead_team(self):
        # daily_burn must reflect delivery headcount only, even when an
        # overhead team has its own daily burn — the overhead lifetime $ is
        # already pre-committed and including its headcount in the runway
        # denominator would double-count.
        proj = self._make_project(budget=200_000, team_size=2, spend=0,
                                  start="2024-01-15", as_of="2024-01-15")
        oht = {
            "total_dollars": 0.0, "realised_dollars": 0.0,
            "remaining_dollars": 0.0, "daily_burn": 800.0,
            "headcount": 1, "by_role": {},
        }
        result = agile_project_summary(
            proj, [], [], default_day_rate=1_000.0, overhead_team=oht,
        )
        # 2 delivery × $1000 = $2000/day; overhead's $800 is informational only
        assert result["daily_burn"] == 2_000.0
        assert result["delivery_daily_burn"] == 2_000.0
        assert result["overhead_daily_burn"] == 800.0

    def test_total_budget_days_uses_delivery_burn(self):
        # $100k accessible / $1k delivery burn = 100 days (not 50 if overhead
        # had been double-counted into the burn)
        proj = self._make_project(budget=100_000, team_size=1, spend=0,
                                  start="2024-01-15", as_of="2024-01-15")
        oht = {
            "total_dollars": 0.0, "realised_dollars": 0.0,
            "remaining_dollars": 0.0, "daily_burn": 1_000.0,
            "headcount": 1, "by_role": {},
        }
        result = agile_project_summary(
            proj, [], [], default_day_rate=1_000.0, overhead_team=oht,
        )
        assert result["total_budget_days_remaining"] == pytest.approx(100.0)

    def test_legacy_callsite_still_works(self):
        # When fixed_overhead_dollars / overhead_team are not supplied, the
        # legacy meaning of `overhead_dollars` (single combined number) is
        # preserved so old call sites (and old tests) keep passing.
        proj = self._make_project(budget=100_000, team_size=1, spend=0)
        result = agile_project_summary(
            proj, [], [], default_day_rate=1_000.0, overhead_dollars=20_000.0,
        )
        assert result["accessible_budget"] == 80_000.0
        assert result["overhead_dollars"] == 20_000.0
        assert result["overhead_team_dollars"] == 0.0


# ── capacity_budget_summary excludes overhead capacity ─────────────────────

class TestCapacityBudgetSummaryExcludesOverhead:
    def test_overhead_capacity_does_not_drain_runway(self):
        # 5 delivery × $1000 = $5k/day; overhead capacity present but
        # excluded → $50k / $5k = 10 budget days.
        cps = [
            {"week_monday": date(2024, 1, 15), "team_size": 5,
             "day_rate": 1000.0, "role_category": "delivery"},
            {"week_monday": date(2024, 1, 15), "team_size": 2,
             "day_rate": 800.0, "role_category": "overhead"},
        ]
        result = capacity_budget_summary(
            remaining_budget=50_000.0,
            as_of_date=date(2024, 1, 15),
            capacity_periods=cps,
            default_daily_burn=5_000.0,
            default_team_size=5,
        )
        assert result["budget_days"] == pytest.approx(10.0)


# ── agile_burndown_chart_data — capacity-aware projection ──────────────────

def _minimal_project(start="2025-01-06", as_of="2025-04-28", team_size=10):
    return {
        "start_date": start,
        "as_of_date": as_of,
        "end_date": "2025-12-31",
        "team_size": team_size,
        "default_role_id": None,
        "overhead_team_size": 0,
        "default_overhead_role_id": None,
        "initial_budget": 500_000.0,
        "health_on_track_pct": 100.0,
        "health_at_risk_pct": 80.0,
    }


def _minimal_summary(daily_burn=10_000.0, accessible=200_000.0, total=500_000.0):
    return {
        "daily_burn": daily_burn,
        "accessible_budget": accessible,
        "total_budget": total,
        "overhead_dollars": 50_000.0,
        "actual_spend": 250_000.0,
        "allocated_dollars": 300_000.0,
        "overall_completion": 60.0,
        "realised_risk_dollars": 0.0,
        "remaining_dollars": 100_000.0,
        "open_risk_dollars": 0.0,
    }


class TestAgileBurndownCapacityProjection:
    def test_no_capacity_periods_uses_default_slope(self):
        # No overrides → projection should terminate at accessible / daily_burn
        # business days, same as the old constant-slope behaviour.
        project = _minimal_project()
        summary = _minimal_summary(daily_burn=10_000.0, accessible=50_000.0)
        result = agile_burndown_chart_data(project, summary, capacity_periods=[])
        assert result is not None
        # accessible=50k, daily_burn=10k → 5 budget-days → 5 business days forward
        from calculations import add_business_days
        from datetime import date
        expected_exhaustion = add_business_days(date(2025, 4, 28), 5)
        assert result["budget_exhaustion"] == expected_exhaustion

    def test_low_future_capacity_extends_budget_exhaustion(self):
        # Future week with team_size=1 (vs default 10) → burns at 10% rate →
        # budget lasts much longer than the constant-slope version.
        project = _minimal_project(team_size=10)
        summary = _minimal_summary(daily_burn=10_000.0, accessible=50_000.0)
        # Capacity period covers the next week (Mon 2025-04-28 onward)
        low_cap = [
            {
                "week_monday": date(2025, 4, 28),
                "team_size": 1,
                "day_rate": 1_000.0,  # 1 person × $1k = $1k/day vs $10k default
                "role_category": "delivery",
            }
        ]
        result = agile_burndown_chart_data(project, summary, capacity_periods=low_cap)
        assert result is not None
        from calculations import add_business_days
        baseline_exhaustion = add_business_days(date(2025, 4, 28), 5)
        # Low capacity → budget lasts longer than the default 5-day runway
        assert result["budget_exhaustion"] > baseline_exhaustion

    def test_high_future_capacity_shortens_budget_exhaustion(self):
        # Future week with team_size=50 (vs default 10) → burns 5× faster →
        # budget exhausted sooner than constant-slope version.
        project = _minimal_project(team_size=10)
        summary = _minimal_summary(daily_burn=10_000.0, accessible=50_000.0)
        high_cap = [
            {
                "week_monday": date(2025, 4, 28),
                "team_size": 50,
                "day_rate": 1_000.0,  # 50 × $1k = $50k/day vs $10k default
                "role_category": "delivery",
            }
        ]
        result = agile_burndown_chart_data(project, summary, capacity_periods=high_cap)
        assert result is not None
        from calculations import add_business_days
        baseline_exhaustion = add_business_days(date(2025, 4, 28), 5)
        assert result["budget_exhaustion"] < baseline_exhaustion

    def test_overhead_capacity_excluded_from_projection(self):
        # Overhead-role capacity periods must not affect the projection slope.
        project = _minimal_project(team_size=10)
        summary = _minimal_summary(daily_burn=10_000.0, accessible=50_000.0)
        overhead_cap = [
            {
                "week_monday": date(2025, 4, 28),
                "team_size": 100,
                "day_rate": 1_000.0,
                "role_category": "overhead",
            }
        ]
        result_overhead = agile_burndown_chart_data(project, summary, capacity_periods=overhead_cap)
        result_none = agile_burndown_chart_data(project, summary, capacity_periods=[])
        assert result_overhead is not None and result_none is not None
        assert result_overhead["budget_exhaustion"] == result_none["budget_exhaustion"]


# ── parse_date ─────────────────────────────────────────────────────────────

class TestParseDate:
    def test_valid_iso_date(self):
        assert parse_date("2025-01-15") == date(2025, 1, 15)

    def test_empty_string_returns_none(self):
        assert parse_date("") is None

    def test_none_returns_none(self):
        assert parse_date(None) is None

    def test_invalid_string_returns_none(self):
        assert parse_date("not-a-date") is None

    def test_wrong_format_returns_none(self):
        assert parse_date("15/01/2025") is None


# ── add_business_days ───────────────────────────────────────────────────────

class TestAddBusinessDays:
    def test_one_day_forward_from_monday(self):
        assert add_business_days(date(2024, 1, 15), 1) == date(2024, 1, 16)  # Mon → Tue

    def test_skips_weekend(self):
        assert add_business_days(date(2024, 1, 19), 1) == date(2024, 1, 22)  # Fri → Mon

    def test_zero_returns_start(self):
        assert add_business_days(date(2024, 1, 15), 0) == date(2024, 1, 15)

    def test_fractional_rounds_to_nearest(self):
        # 0.4 rounds to 0 → same day; 0.6 rounds to 1 → next business day
        assert add_business_days(date(2024, 1, 15), 0.4) == date(2024, 1, 15)
        assert add_business_days(date(2024, 1, 15), 0.6) == date(2024, 1, 16)

    def test_five_days_spans_one_week(self):
        assert add_business_days(date(2024, 1, 15), 5) == date(2024, 1, 22)  # Mon → Mon


# ── remaining_days / budget_dollars / remaining_dollars ────────────────────

class TestBudgetMath:
    def test_remaining_days_zero_complete(self):
        assert remaining_days(10.0, 0) == 10.0

    def test_remaining_days_half_complete(self):
        assert remaining_days(10.0, 50) == 5.0

    def test_remaining_days_fully_complete(self):
        assert remaining_days(10.0, 100) == 0.0

    def test_budget_dollars_basic(self):
        assert budget_dollars(5.0, 1_000.0) == 5_000.0

    def test_budget_dollars_zero_rate(self):
        assert budget_dollars(10.0, 0.0) == 0.0

    def test_remaining_dollars_half_done(self):
        assert remaining_dollars(10.0, 50, 1_000.0) == 5_000.0

    def test_remaining_dollars_fully_done(self):
        assert remaining_dollars(10.0, 100, 1_000.0) == 0.0
