"""Unit tests for calculations.py business logic."""
from datetime import date, timedelta
import pytest
from calculations import (
    business_days_between,
    effective_impact_days,
    deliverable_summary,
    requirement_summary,
    feature_summary,
    project_summary,
    feature_health,
    get_week_monday,
    capacity_days_remaining,
    capacity_plan_summary,
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
    def test_open_todo_returns_full_impact(self):
        assert effective_impact_days(10.0, "todo", None, 0.0) == 10.0

    def test_open_doing_returns_full_impact(self):
        assert effective_impact_days(5.0, "doing", "avoided", 100.0) == 5.0

    def test_done_avoided_returns_zero(self):
        assert effective_impact_days(10.0, "done", "avoided", 0.0) == 0.0

    def test_done_mitigated_returns_partial(self):
        assert effective_impact_days(10.0, "done", "mitigated", 40.0) == pytest.approx(4.0)

    def test_done_mitigated_fully(self):
        assert effective_impact_days(10.0, "done", "mitigated", 100.0) == pytest.approx(10.0)

    def test_done_realised_returns_full(self):
        assert effective_impact_days(10.0, "done", "realised", 0.0) == 10.0

    def test_done_no_resolution_returns_full_conservative(self):
        assert effective_impact_days(10.0, "done", None, 0.0) == 10.0

    def test_zero_impact(self):
        assert effective_impact_days(0.0, "todo", None, 0.0) == 0.0


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
        # Days remaining = (accessible_budget - actual_spend) / daily_burn
        # With $0 actual spend and $100k budget at $1k/day → 100 days
        proj = self._make_project(budget=100_000, team_size=1, spend=0)
        result = project_summary(proj, [], [], default_day_rate=1_000.0)
        assert result["budget_days_remaining"] == pytest.approx(100.0)

    def test_budget_days_remaining_with_spend(self):
        # $10k spent from $100k budget at $1k/day → 90 days remaining
        proj = self._make_project(budget=100_000, team_size=1, spend=10_000)
        result = project_summary(proj, [], [], default_day_rate=1_000.0)
        assert result["budget_days_remaining"] == pytest.approx(90.0)

    def test_current_budget_includes_adjustments(self):
        proj = self._make_project(budget=100_000)
        adjustments = [{"amount": 10_000}, {"amount": -5_000}]
        result = project_summary(proj, [], adjustments, default_day_rate=1_000.0)
        assert result["current_budget"] == 105_000.0

    def test_realised_risk_reduces_accessible_budget(self):
        proj = self._make_project(budget=100_000, team_size=1, spend=0)
        result = project_summary(proj, [], [], default_day_rate=1_000.0, realised_risk_dollars=10_000.0)
        assert result["accessible_budget"] == 90_000.0
        assert result["realised_risk_dollars"] == 10_000.0

    def test_budget_days_remaining_uses_accessible_budget(self):
        proj = self._make_project(budget=100_000, team_size=1, spend=0,
                                  start="2024-01-15", as_of="2024-01-15")
        # No elapsed days, so days remaining = accessible_budget / daily_burn
        result = project_summary(proj, [], [], default_day_rate=1_000.0, realised_risk_dollars=20_000.0)
        assert result["budget_days_remaining"] == pytest.approx(80.0)

    def test_zero_realised_risk_keeps_full_budget(self):
        proj = self._make_project(budget=100_000, team_size=1, spend=0,
                                  start="2024-01-15", as_of="2024-01-15")
        result = project_summary(proj, [], [], default_day_rate=1_000.0)
        assert result["accessible_budget"] == 100_000.0
        assert result["budget_days_remaining"] == pytest.approx(100.0)

    def test_expected_burn_pct(self):
        # 1 person, $1k/day, $100k budget, 5 days elapsed → 5% expected burn
        proj = self._make_project(budget=100_000, team_size=1, spend=0)
        result = project_summary(proj, [], [], default_day_rate=1_000.0)
        assert result["expected_burn_pct"] == pytest.approx(5.0)

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
