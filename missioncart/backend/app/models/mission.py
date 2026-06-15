from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from uuid import uuid4
from datetime import datetime
from enum import Enum


class DomainEnum(str, Enum):
    event = "event"
    home_setup = "home_setup"
    electronics = "electronics"
    travel = "travel"
    baby_care = "baby_care"
    pet_care = "pet_care"
    seasonal = "seasonal"
    general = "general"


class SafetyEnum(str, Enum):
    child_safe = "child_safe"
    baby_safe = "baby_safe"
    pet_safe = "pet_safe"
    general = "general"


class MissionSpec(BaseModel):
    mission_id: str = Field(default_factory=lambda: str(uuid4()))
    raw_goal: str
    goal: str = ""
    domain: str = "general"
    occasion: Optional[str] = None
    headcount: Optional[int] = None
    deadline_hours: Optional[int] = None
    budget_max: Optional[float] = None
    budget_min: Optional[float] = None
    location_pincode: Optional[str] = None
    safety_context: Optional[str] = None
    household_size: Optional[int] = None
    trip_duration_days: Optional[int] = None
    pet_weight_kg: Optional[float] = None
    pet_age_months: Optional[int] = None
    baby_age_weeks: Optional[int] = None
    special_constraints: List[str] = []
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_type: Optional[str] = None
    unsupported_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class NeedItem(BaseModel):
    need_id: str = Field(default_factory=lambda: str(uuid4()))
    label: str
    priority: Literal["must_have", "should_have", "optional"]
    priority_weight: float = 1.0
    category_candidates: List[str] = []
    units_required: int = 0
    packs_required: int = 0
    quantity: float = 1.0
    unit: str = "piece"
    reason: str = ""
    budget_fraction: float = 0.0
    budget_ceiling: float = 0.0
    safety_tags: List[str] = []
    compatibility_check_required: bool = True


class MissionDecomposed(BaseModel):
    spec: MissionSpec
    needs: List[NeedItem]
    estimated_total: float = 0.0


class CoverageScore(BaseModel):
    fraction: float
    covered: int
    total: int
    display: str
    all_must_haves_covered: bool
    missing: List[str]
