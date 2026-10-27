from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CitizenReportCreate(BaseModel):
    type: str
    description: str
    latitude: float
    longitude: float


class CitizenReportReviewCreate(BaseModel):
    decision: str  # verified, rejected, escalated, closed
    notes: Optional[str] = None


class CitizenReportOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    district_id: Optional[int] = None
    type: str
    description: str
    latitude: float
    longitude: float
    status: str
    confidence_score: float
    is_duplicate: bool
    duplicate_of_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
