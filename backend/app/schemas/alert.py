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
    severity: str
    issuer: str
    valid_from: datetime
    valid_to: datetime
    district_ids: Optional[List[int]] = []


class AlertOut(BaseModel):
    id: int
    type: str
    title: str
    description: str
    severity: str
    issuer: str
    valid_from: datetime
    valid_to: datetime
    status: str
    created_at: datetime
    areas: List[AlertAreaOut] = []

    model_config = ConfigDict(from_attributes=True)
