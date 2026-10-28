from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AlertAreaOut(BaseModel):
    id: int
    alert_id: int
    district_id: Optional[int] = None
    boundary_geojson: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class AlertCreate(BaseModel):
    type: str
    title: str
    description: str
    severity: str  # low, medium, high, critical
    issuer: str
    valid_from: datetime
    valid_to: datetime
    district_ids: Optional[List[int]] = []
    is_official: Optional[bool] = None


class AlertDraftCreate(AlertCreate):
    pass


class AlertCancelRequest(BaseModel):
    reason: Optional[str] = "Disaster condition neutralized or alert superseded"


class AlertOut(BaseModel):
    id: int
    type: str
    title: str
    description: str
    severity: str
    issuer: str
    is_official: bool
    valid_from: datetime
    valid_to: datetime
    status: str
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    areas: List[AlertAreaOut] = []

    model_config = ConfigDict(from_attributes=True)
