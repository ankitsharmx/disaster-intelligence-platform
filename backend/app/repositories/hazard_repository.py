from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.hazard import HazardObservation, DataSourceRun


class HazardRepository(BaseRepository[HazardObservation]):
    def __init__(self):
        super().__init__(HazardObservation)

    async def get_recent_by_district(
        self, db: AsyncSession, district_id: int, since: datetime
    ) -> List[HazardObservation]:
        q = (
            select(HazardObservation)
            .filter(HazardObservation.district_id == district_id, HazardObservation.observed_time >= since)
            .order_by(HazardObservation.observed_time.desc())
        )
        res = await db.execute(q)
        return res.scalars().all()


hazard_repository = HazardRepository()
