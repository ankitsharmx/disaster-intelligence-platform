from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ReportMediaOut(BaseModel):
    id: int
    report_id: int
    file_path: str
    file_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    content_type: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportReviewOut(BaseModel):
    id: int
    report_id: int
    reviewer_id: int
    decision: str
    notes: Optional[str] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class CitizenReportCreate(BaseModel):
    type: str = Field(..., description="flood, waterlogging, landslide, etc.")
    description: str = Field(..., min_length=5, description="Factual description of hazard incident")
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class CitizenReportReviewCreate(BaseModel):
    decision: str = Field(..., description="verified, rejected, resolved")
    notes: Optional[str] = Field(None, description="Officer verification remarks")


class CitizenReportReopenRequest(BaseModel):
    notes: str = Field(..., min_length=5, description="Justification for reopening incident investigation")


class CitizenReportOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    district_id: Optional[int] = None
    assigned_officer_id: Optional[int] = None
    type: str
    description: str
    latitude: float
    longitude: float
    status: str
    confidence_score: float
    is_duplicate: bool
    duplicate_of_id: Optional[int] = None
    reopened_count: int = 0
    reopened_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    media: List[ReportMediaOut] = []
    reviews: List[ReportReviewOut] = []

    model_config = ConfigDict(from_attributes=True)
