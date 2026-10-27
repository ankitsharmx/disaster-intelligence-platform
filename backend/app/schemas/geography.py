from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DistrictResolveRequest(BaseModel):
    latitude: float
    longitude: float


class DistrictResolveResponse(BaseModel):
    found: bool
    district: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class FacilityOut(BaseModel):
    id: int
    name: str
    category: str
    district_id: int
    latitude: float
    longitude: float
    contact_number: Optional[str] = None
    capacity: Optional[int] = None
    details: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class DistrictOut(BaseModel):
    id: int
    name: str
    code: Optional[str] = None
    center_lat: Optional[float] = None
    center_lon: Optional[float] = None
    boundary_geojson: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)
