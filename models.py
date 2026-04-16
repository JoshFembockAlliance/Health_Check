from pydantic import BaseModel
from typing import Optional


class Role(BaseModel):
    id: Optional[int] = None
    name: str
    day_rate: float


class Project(BaseModel):
    id: int = 1
    name: str = "New Project"
    start_date: str = ""
    as_of_date: str = ""
    initial_budget: float = 0.0
    team_size: int = 1
    actual_spend: float = 0.0
    default_role_id: int = 1
    health_on_track_pct: float = 100.0   # completion >= expected * this% → On Track
    health_at_risk_pct: float = 80.0     # completion >= expected * this% → At Risk, below → Behind


class BudgetAdjustment(BaseModel):
    id: Optional[int] = None
    amount: float
    date: str
    description: str


class Feature(BaseModel):
    id: Optional[int] = None
    name: str
    sort_order: int = 0
    started: int = 0  # 0 = not started, 1 = started


class Requirement(BaseModel):
    id: Optional[int] = None
    feature_id: int
    name: str
    sort_order: int = 0


class Deliverable(BaseModel):
    id: Optional[int] = None
    requirement_id: int
    name: str
    budget_days: float = 0.0
    percent_complete: int = 0
    priority: str = "Must Have"
    role_id: Optional[int] = None
    sort_order: int = 0


class Risk(BaseModel):
    id: Optional[int] = None
    name: str
    description: str = ""
    status: str = "todo"  # todo, doing, done
    due_date: str = ""
    impact_days: float = 0.0
    # timeline_impact_days: schedule slip in days, separate from impact_days
    # which measures billable/budget cost. A sequencing hiccup might cost 3d
    # of billable time but slip the schedule by 10d — both are worth noting
    # but only impact_days flows into budget calculations.
    timeline_impact_days: float = 0.0
    sort_order: int = 0
    # realised_percentage is independent of status: even an open risk can have
    # some portion already absorbed. 0 = nothing realised yet, 100 = fully
    # absorbed. For closed risks the derived label is Avoided (0%),
    # Mitigated (1-99%), or Realised (100%).
    realised_percentage: float = 0.0
    # resultant_work: free text describing the work items that flow from
    # realised impact (e.g. "3 days went into rebuilding the sync layer").
    # Kept separate from description so the narrative about what changed
    # is distinct from the narrative about what we're now doing about it.
    resultant_work: str = ""


class RiskFeature(BaseModel):
    risk_id: int
    feature_id: int


class Overhead(BaseModel):
    id: Optional[int] = None
    name: str
    description: str = ""
    amount: float = 0.0
    sort_order: int = 0
