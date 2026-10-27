from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.report import CitizenReport, ReportReview
from app.models.alert import Alert
from app.models.hazard import HazardObservation
from app.models.geography import Facility
from app.models.user import User
from app.models.audit import AuditEvent
from app.schemas.report import CitizenReportReviewCreate, CitizenReportOut
from app.api.deps import require_officer_or_admin

router = APIRouter(prefix="/officer", tags=["Officer Operations"])


@router.post("/reports/{report_id}/review", response_model=CitizenReportOut)
async def review_citizen_report(
    report_id: int,
    review_in: CitizenReportReviewCreate,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CitizenReport).filter(CitizenReport.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    review = ReportReview(
        report_id=report.id,
        reviewer_id=current_user.id,
        decision=review_in.decision,
        notes=review_in.notes,
    )
    db.add(review)

    # Update report status
    report.status = review_in.decision
    db.add(report)

    audit = AuditEvent(
        actor=current_user.email,
        action="review_report",
        affected_record=f"CitizenReport:{report.id}",
        details={"decision": review_in.decision, "notes": review_in.notes},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/dashboard-summary")
async def get_dashboard_summary(
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    # Active alerts count
    alerts_q = await db.execute(select(func.count(Alert.id)).filter(Alert.status == "active"))
    active_alerts = alerts_q.scalar_one()

    # Pending citizen reports
    pending_rep_q = await db.execute(
        select(func.count(CitizenReport.id)).filter(CitizenReport.status.in_(["submitted", "under_review"]))
    )
    pending_reports = pending_rep_q.scalar_one()

    # Total facilities
    fac_q = await db.execute(select(func.count(Facility.id)))
    facilities_total = fac_q.scalar_one()

    # Total hazard observations
    obs_q = await db.execute(select(func.count(HazardObservation.id)))
    observations_total = obs_q.scalar_one()

    return {
        "active_alerts_count": active_alerts,
        "pending_reports_count": pending_reports,
        "total_facilities": facilities_total,
        "total_hazard_observations": observations_total,
        "assigned_district_id": current_user.assigned_district_id,
    }
