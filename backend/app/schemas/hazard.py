from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class HazardObservationCreate(BaseModel):
    hazard_type: str
    values: Dict[str, Any]
    observed_time: Optional[datetime] = None
    source: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class HazardObservationOut(BaseModel):
    id: int
    hazard_type: str
    values: Dict[str, Any]
    observed_time: datetime
    source: str
    district_id: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DataSourceRunOut(BaseModel):
    id: int
    source: str
    mode: str
    status: str
    retrieval_time: datetime
    records_count: int
    error: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
