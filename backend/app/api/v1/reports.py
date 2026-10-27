from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from shapely.geometry import Point
from geoalchemy2.shape import from_shape

from app.db.session import get_db
from app.models.report import CitizenReport, ReportMedia
from app.models.user import User
from app.models.audit import AuditEvent
from app.schemas.report import CitizenReportCreate, CitizenReportOut
from app.api.deps import get_current_user
from app.services.geography_service import geography_service
from app.intelligence.scoring import ConfidenceScorer
from app.intelligence.duplicate_detector import duplicate_detector

router = APIRouter(prefix="/reports", tags=["Citizen Reports"])


@router.post("", response_model=CitizenReportOut, status_code=status.HTTP_201_CREATED)
async def submit_report(
    report_in: CitizenReportCreate,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. Resolve district from coordinates
    district_info = geography_service.resolve_district(report_in.latitude, report_in.longitude)
    district_id = district_info.get("id") if district_info else None

    # 2. Check for duplicates among recent reports
    recent_query = select(CitizenReport).filter(
        CitizenReport.type == report_in.type,
        CitizenReport.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0),
    )
    result = await db.execute(recent_query)
    candidates = [
        {
            "id": r.id,
            "type": r.type,
            "description": r.description,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "created_at": r.created_at,
        }
        for r in result.scalars().all()
    ]

    new_report_dict = {
        "type": report_in.type,
        "description": report_in.description,
        "latitude": report_in.latitude,
        "longitude": report_in.longitude,
        "created_at": datetime.now(timezone.utc),
    }

    is_dup, orig_id, match_score = duplicate_detector.is_duplicate(new_report_dict, candidates)

    # 3. Calculate confidence score
    user_role = current_user.role if current_user else "citizen"
    score = ConfidenceScorer.calculate_score(
        description=report_in.description,
        has_media=False,
        user_role=user_role,
    )

    geo_point = from_shape(Point(report_in.longitude, report_in.latitude), srid=4326)

    report = CitizenReport(
        user_id=current_user.id if current_user else None,
        district_id=district_id,
        type=report_in.type,
        description=report_in.description,
        location=geo_point,
        latitude=report_in.latitude,
        longitude=report_in.longitude,
        status="submitted",
        confidence_score=score,
        is_duplicate=is_dup,
        duplicate_of_id=orig_id,
    )
    db.add(report)
    await db.flush()

    audit = AuditEvent(
        actor=current_user.email if current_user else "anonymous",
        action="submit_report",
        affected_record=f"CitizenReport:{report.id}",
        details={"type": report.type, "is_duplicate": is_dup, "confidence": score},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(report)
    return report


@router.get("", response_model=List[CitizenReportOut])
async def list_reports(
    district_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    query = select(CitizenReport).order_by(CitizenReport.created_at.desc()).limit(limit)
    if district_id:
        query = query.filter(CitizenReport.district_id == district_id)
    if status:
        query = query.filter(CitizenReport.status == status)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{report_id}", response_model=CitizenReportOut)
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(CitizenReport).filter(CitizenReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Citizen report not found")
    return report
