from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.report import CitizenReport, ReportReview, ReportStatus
from app.models.alert import Alert
from app.models.hazard import HazardObservation
from app.models.geography import Facility
from app.models.user import User
from app.schemas.report import (
    CitizenReportReviewCreate,
    CitizenReportReopenRequest,
    CitizenReportOut,
)
from app.api.deps import require_officer_or_above
from app.services.report_service import report_service
from app.core.roles import Role

router = APIRouter(prefix="/officer", tags=["Officer Operations & Verification Queue"])


@router.get("/reports", response_model=List[CitizenReportOut])
async def get_officer_review_queue(
    status: Optional[str] = Query(None, description="Filter by status: submitted, under_review, verified, rejected, resolved"),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    Officer review queue.
    JURISDICTION ENFORCEMENT:
    District officers can ONLY retrieve reports belonging to their assigned district.
    State administrators can retrieve reports across districts in their assigned state.
    System administrators have global visibility.
    """
    return await report_service.get_officer_review_queue(
        db=db,
        officer=current_user,
        status=status,
        limit=limit,
    )


@router.post("/reports/{report_id}/assign", response_model=CitizenReportOut)
async def assign_report_to_self(
    report_id: int,
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    Assigns an incident report to the authenticated officer.
    Workflow transition: SUBMITTED -> UNDER_REVIEW.
    """
    return await report_service.assign_report(
        db=db,
        officer=current_user,
        report_id=report_id,
    )


@router.post("/reports/{report_id}/review", response_model=CitizenReportOut)
async def review_citizen_report(
    report_id: int,
    review_in: CitizenReportReviewCreate,
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    Applies an official review decision (verified, rejected, or resolved).
    Atomically updates report status, creates review record, and writes audit event.
    """
    return await report_service.review_report(
        db=db,
        officer=current_user,
        report_id=report_id,
        decision=review_in.decision,
        notes=review_in.notes,
    )


@router.post("/reports/{report_id}/reopen", response_model=CitizenReportOut)
async def reopen_incident_report(
    report_id: int,
    reopen_in: CitizenReportReopenRequest,
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    Formally reopens a previously resolved or rejected incident report.
    Workflow transition: RESOLVED/REJECTED -> UNDER_REVIEW.
    Increments reopened_count and logs audit trail with justification notes.
    """
    return await report_service.reopen_report(
        db=db,
        officer=current_user,
        report_id=report_id,
        notes=reopen_in.notes,
    )


@router.get("/dashboard-summary")
async def get_dashboard_summary(
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """Overview metrics scoped to officer's assigned jurisdiction."""
    district_filter = None
    if current_user.normalized_role == Role.DISTRICT_OFFICER:
        district_filter = current_user.assigned_district_id

    # Active alerts count
    alerts_q = select(func.count(Alert.id)).filter(Alert.status == "active")
    alerts_res = await db.execute(alerts_q)
    active_alerts = alerts_res.scalar_one()

    # Pending citizen reports
    pending_rep_q = select(func.count(CitizenReport.id)).filter(
        CitizenReport.status.in_([ReportStatus.SUBMITTED, ReportStatus.UNDER_REVIEW])
    )
    if district_filter:
        pending_rep_q = pending_rep_q.filter(CitizenReport.district_id == district_filter)
    pending_res = await db.execute(pending_rep_q)
    pending_reports = pending_res.scalar_one()

    # Total facilities
    fac_q = select(func.count(Facility.id))
    if district_filter:
        fac_q = fac_q.filter(Facility.district_id == district_filter)
    fac_res = await db.execute(fac_q)
    facilities_total = fac_res.scalar_one()

    # Total hazard observations
    obs_q = select(func.count(HazardObservation.id))
    if district_filter:
        obs_q = obs_q.filter(HazardObservation.district_id == district_filter)
    obs_res = await db.execute(obs_q)
    observations_total = obs_res.scalar_one()

    return {
        "active_alerts_count": active_alerts,
        "pending_reports_count": pending_reports,
        "total_facilities": facilities_total,
        "total_hazard_observations": observations_total,
        "assigned_district_id": current_user.assigned_district_id,
        "assigned_state_id": current_user.assigned_state_id,
        "role": current_user.role,
    }
