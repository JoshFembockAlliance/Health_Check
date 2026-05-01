from pydantic import BaseModel
from typing import Literal, Optional


# Role categories. Delivery roles are expected to produce earned value
# (feature delivery). Overhead roles burn budget without producing earned
# value — BAs, designers, SMEs, facilitators — and are treated like
# pre-committed overhead by the dashboard math. See DESIGN_RULES §1.
ROLE_CATEGORY_DELIVERY = "delivery"
ROLE_CATEGORY_OVERHEAD = "overhead"
VALID_ROLE_CATEGORIES = {ROLE_CATEGORY_DELIVERY, ROLE_CATEGORY_OVERHEAD}


class Project(BaseModel):
    id: Optional[int] = None
    name: str = "New Project"
    description: str = ""
    start_date: str = ""
    as_of_date: str = ""
    end_date: str = ""
    initial_budget: float = 0.0
    team_size: float = 1.0
    actual_spend: float = 0.0
    default_role_id: int = 1
    overhead_team_size: float = 0.0
    default_overhead_role_id: int = 0
    health_on_track_pct: float = 100.0
    health_at_risk_pct: float = 80.0
    accent: str = "cyan"
    theme: str = "light"
    icon: str = ""
    project_type: str = "agile_feature_development"


class Role(BaseModel):
    id: Optional[int] = None
    project_id: int
    name: str
    day_rate: float
    category: Literal["delivery", "overhead"] = "delivery"


class BudgetAdjustment(BaseModel):
    id: Optional[int] = None
    project_id: int
    amount: float
    date: str
    description: str


class Feature(BaseModel):
    id: Optional[int] = None
    project_id: int
    name: str
    sort_order: int = 0
    started: int = 0
    expanded_scope: int = 0


class Requirement(BaseModel):
    id: Optional[int] = None
    feature_id: int
    name: str
    sort_order: int = 0
    expanded_scope: int = 0


class Deliverable(BaseModel):
    id: Optional[int] = None
    requirement_id: int
    name: str
    budget_days: float = 0.0
    percent_complete: int = 0
    priority: str = "Must Have"
    role_id: Optional[int] = None
    sort_order: int = 0
    expanded_scope: int = 0


class Risk(BaseModel):
    id: Optional[int] = None
    project_id: int
    name: str
    description: str = ""
    status: str = "todo"
    date_identified: str = ""
    due_date: str = ""
    impact_days: float = 0.0
    timeline_impact_days: float = 0.0
    sort_order: int = 0
    realised_percentage: float = 0.0
    resultant_work: str = ""


class RiskFeature(BaseModel):
    risk_id: int
    feature_id: int


class Decision(BaseModel):
    id: Optional[int] = None
    project_id: int
    name: str
    description: str = ""
    expected_outcome: str = ""
    decision_date: str = ""
    decision_type: str = "Pivot"
    sort_order: int = 0


class DecisionFeature(BaseModel):
    decision_id: int
    feature_id: int


class Overhead(BaseModel):
    id: Optional[int] = None
    project_id: int
    name: str
    description: str = ""
    amount: float = 0.0
    sort_order: int = 0


class Milestone(BaseModel):
    id: Optional[int] = None
    project_id: int
    name: str
    description: str = ""
    value: float = 0.0
    sort_order: int = 0


class MilestoneFeature(BaseModel):
    milestone_id: int
    feature_id: int


class MilestoneInvoice(BaseModel):
    id: Optional[int] = None
    milestone_id: int
    invoice_number: str = ""
    amount: float = 0.0
    status: str = "invoiced"
    issue_date: str = ""
    paid_date: str = ""
