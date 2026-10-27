from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.geography import State, District, Facility


class GeographyRepository:
    async def get_state_by_code(self, db: AsyncSession, code: str) -> Optional[State]:
        res = await db.execute(select(State).filter(State.code == code))
        return res.scalar_one_or_none()

    async def get_all_districts(self, db: AsyncSession) -> List[District]:
        res = await db.execute(select(District))
        return res.scalars().all()

    async def get_district_by_name(self, db: AsyncSession, name: str) -> Optional[District]:
        res = await db.execute(select(District).filter(District.name.ilike(f"%{name}%")))
        return res.scalar_one_or_none()

    async def get_facilities_by_district(self, db: AsyncSession, district_id: int) -> List[Facility]:
        res = await db.execute(select(Facility).filter(Facility.district_id == district_id))
        return res.scalars().all()


geography_repository = GeographyRepository()
