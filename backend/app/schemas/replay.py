from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class ReplayStartRequest(BaseModel):
    scenario: Optional[str] = "monsoon_flood_scenario.json"
    speed: Optional[float] = 1.0


class ReplaySpeedRequest(BaseModel):
    speed: float


class ReplayStatusResponse(BaseModel):
    status: str
    speed: float
    scenario_id: Optional[str] = None
    scenario_name: Optional[str] = None
    current_offset_seconds: float
    total_duration_seconds: float
    progress_percent: float
    events_total: int
    events_emitted: int
    last_event: Optional[Dict[str, Any]] = None
