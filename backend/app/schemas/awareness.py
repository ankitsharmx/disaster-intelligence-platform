from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AwarenessOut(BaseModel):
    id: int
    hazard: str
    stage: str
    language: str
    title: str
    instructions: List[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
