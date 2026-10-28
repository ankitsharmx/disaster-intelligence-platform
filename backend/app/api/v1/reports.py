from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, File, BackgroundTasks, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.report import CitizenReport, ReportStatus
from app.models.user import User
from app.schemas.report import (
    CitizenReportCreate,
    CitizenReportOut,
    ReportMediaOut,
)
from app.api.deps import get_current_user, require_current_user
from app.services.report_service import report_service
from app.core.roles import Role
from app.core.exceptions import PermissionDeniedException, EntityNotFoundException

router = APIRouter(prefix="/reports", tags=["Incident Reporting"])


@router.post("", response_model=CitizenReportOut, status_code=status.HTTP_201_CREATED)
async def submit_incident_report(
    report_in: CitizenReportCreate,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submits a new citizen hazard report.
    - Initial status set immediately to SUBMITTED.
    - Resolves geographic district containment.
    - Response returns immediately without blocking on expensive ML/sensor fetches.
    - Background worker handles duplicate detection and sensor corroboration asynchronously.
    """
    return await report_service.submit_report(
        db=db,
        user=current_user,
        type=report_in.type,
        description=report_in.description,
        latitude=report_in.latitude,
        longitude=report_in.longitude,
        background_tasks=background_tasks,
    )


@router.post("/{report_id}/media", response_model=ReportMediaOut, status_code=status.HTTP_201_CREATED)
async def upload_report_attachment(
    report_id: int,
    file: UploadFile = File(..., description="Image, video, or PDF attachment"),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Uploads supporting media proof to an existing incident report.
    - Validates file size (max 10MB).
    - Validates MIME type (JPEG, PNG, WebP, GIF, MP4, PDF).
    - Stores file in persistent volume directory.
    - Recalculates confidence score upon attachment.
    """
    return await report_service.upload_report_media(
        db=db,
        user=current_user,
        report_id=report_id,
        file=file,
    )


@router.get("/my", response_model=List[CitizenReportOut])
async def get_my_submitted_reports(
    current_user: User = Depends(require_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves all reports submitted by the authenticated citizen with review history."""
    return await report_service.get_citizen_own_reports(db=db, user=current_user)


@router.get("", response_model=List[CitizenReportOut])
async def get_public_verified_reports(
    district_id: Optional[int] = Query(None, description="Filter by district"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """
    Public verified incident feed.
    ENFORCEMENT RULE: Citizens and public map endpoints NEVER receive unverified reports.
    Only reports reviewed and marked VERIFIED by authorized officers appear here.
    """
    return await report_service.get_public_verified_reports(
        db=db,
        district_id=district_id,
        limit=limit,
    )


@router.get("/{report_id}", response_model=CitizenReportOut)
async def get_report_detail(
    report_id: int,
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves incident report details.
    - Public / Unauthenticated: permitted ONLY if report is VERIFIED.
    - Citizen: permitted if it is their own report OR if it is VERIFIED.
    - Officer / Admin: permitted if within their jurisdiction.
    """
    q = (
        select(CitizenReport)
        .options(selectinload(CitizenReport.media), selectinload(CitizenReport.reviews))
        .filter(CitizenReport.id == report_id)
    )
    res = await db.execute(q)
    report = res.scalar_one_or_none()
    if not report:
        raise EntityNotFoundException("CitizenReport", report_id)

    # Check access rule
    if report.status == ReportStatus.VERIFIED:
        return report

    if current_user:
        user_role = current_user.normalized_role
        if user_role in {Role.SYSTEM_ADMIN, Role.STATE_ADMIN}:
            return report
        if user_role == Role.DISTRICT_OFFICER and report.district_id == current_user.assigned_district_id:
            return report
        if report.user_id == current_user.id:
            return report

    raise PermissionDeniedException("This report is currently under verification and not publicly viewable.")
