from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.base import BaseRepository
from app.models.report import CitizenReport


class ReportRepository(BaseRepository[CitizenReport]):
    def __init__(self):
        super().__init__(CitizenReport)

    async def get_by_status(self, db: AsyncSession, status: str) -> List[CitizenReport]:
        q = select(CitizenReport).filter(CitizenReport.status == status).order_by(CitizenReport.created_at.desc())
        res = await db.execute(q)
        return res.scalars().all()


report_repository = ReportRepository()
