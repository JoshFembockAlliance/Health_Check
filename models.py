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
