from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class SubscriptionCreate(BaseModel):
    endpoint: str
    p256dh: Optional[str] = None
    auth: Optional[str] = None
    district_id: Optional[int] = None


class SubscriptionOut(BaseModel):
    id: int
    endpoint: str
    district_id: Optional[int] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationDispatchTest(BaseModel):
    district_id: int
    title: str
    message: str
