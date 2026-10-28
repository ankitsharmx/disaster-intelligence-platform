from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.overview_service import overview_service

router = APIRouter(prefix="/overview", tags=["Situational Awareness Overview"])


@router.get("")
async def get_overview(
    district_id: int = Query(..., description="Target district ID for situational synthesis"),
    db: AsyncSession = Depends(get_db),
):
    """
    Synthesizes the comprehensive district situational overview:
    - Latest valid multi-hazard observations with source and demo/live status
    - Applicable active emergency alerts with official vs prototype distinction
    - Real-time automated risk estimations based on sensor inputs
    - Contextual safety guidance and evacuation recommendations
    - Health and retrieval status of upstream data providers
    """
    return await overview_service.get_district_overview(db=db, district_id=district_id)
