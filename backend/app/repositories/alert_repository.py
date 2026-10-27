from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.repositories.base import BaseRepository
from app.models.alert import Alert


class AlertRepository(BaseRepository[Alert]):
    def __init__(self):
        super().__init__(Alert)

    async def get_active_alerts(self, db: AsyncSession) -> List[Alert]:
        q = select(Alert).options(selectinload(Alert.areas)).filter(Alert.status == "active")
        res = await db.execute(q)
        return res.scalars().all()


alert_repository = AlertRepository()
