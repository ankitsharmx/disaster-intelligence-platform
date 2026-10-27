from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.awareness import AwarenessContent
from app.schemas.awareness import AwarenessOut

router = APIRouter(prefix="/awareness", tags=["Disaster Awareness & Safety Guides"])


@router.get("", response_model=List[AwarenessOut])
async def list_awareness_content(
    hazard: Optional[str] = Query(None, description="flood, earthquake, cyclone, fire"),
    stage: Optional[str] = Query(None, description="before, during, after"),
    language: str = Query("en"),
    db: AsyncSession = Depends(get_db),
):
    query = select(AwarenessContent).filter(AwarenessContent.language == language)
    if hazard:
        query = query.filter(AwarenessContent.hazard == hazard)
    if stage:
        query = query.filter(AwarenessContent.stage == stage)

    result = await db.execute(query)
    return result.scalars().all()
