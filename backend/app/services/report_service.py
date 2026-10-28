import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import UploadFile, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from shapely.geometry import Point
from geoalchemy2.shape import from_shape

from app.models.report import CitizenReport, ReportMedia, ReportReview, ReportStatus
from app.models.user import User
from app.models.audit import AuditEvent
from app.db.session import AsyncSessionLocal
from app.services.geography_service import geography_service
from app.intelligence.scoring import ConfidenceScorer
from app.intelligence.duplicate_detector import duplicate_detector
from app.core.roles import Role
from app.core.exceptions import (
    EntityNotFoundException,
    PermissionDeniedException,
    DistrictAccessDeniedException,
    FileValidationException,
    InvalidOperationException,
)

logger = logging.getLogger("report_service")

# File upload limits
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "video/mp4",
    "application/pdf",
}

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def async_process_report_intelligence(report_id: int):
    """
    Background worker task: executes duplicate detection, spatial clustering,
    and sensor corroboration asynchronously without delaying HTTP submission.
    """
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                res = await session.execute(select(CitizenReport).filter(CitizenReport.id == report_id))
                report = res.scalar_one_or_none()
                if not report:
                    return

                # Retrieve candidates within same day and type
                today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
                candidates_q = await session.execute(
                    select(CitizenReport).filter(
                        CitizenReport.id != report.id,
                        CitizenReport.type == report.type,
                        CitizenReport.created_at >= today,
                    )
                )
                candidates = [
                    {
                        "id": c.id,
                        "type": c.type,
                        "description": c.description,
                        "latitude": c.latitude,
                        "longitude": c.longitude,
                        "created_at": c.created_at,
                    }
                    for c in candidates_q.scalars().all()
                ]

                new_rep_dict = {
                    "type": report.type,
                    "description": report.description,
                    "latitude": report.latitude,
                    "longitude": report.longitude,
                    "created_at": report.created_at,
                }
                is_dup, orig_id, match_score = duplicate_detector.is_duplicate(new_rep_dict, candidates)
                if is_dup:
                    report.is_duplicate = True
                    report.duplicate_of_id = orig_id
                    logger.info(f"Report {report.id} flagged as duplicate of {orig_id} (match: {match_score})")

                # Corroborate score
                updated_score = ConfidenceScorer.calculate_score(
                    description=report.description,
                    has_media=False,
                    user_role="citizen",
                )
                report.confidence_score = updated_score
                session.add(report)

                audit = AuditEvent(
                    actor="background_intelligence_worker",
                    action="report_intelligence_analyzed",
                    affected_record=f"CitizenReport:{report.id}",
                    details={"is_duplicate": is_dup, "duplicate_of_id": orig_id, "confidence": updated_score},
                )
                session.add(audit)
    except Exception as e:
        logger.error(f"Error in background intelligence processing for report {report_id}: {e}")


class ReportService:
    @classmethod
    async def submit_report(
        cls,
        db: AsyncSession,
        user: Optional[User],
        type: str,
        description: str,
        latitude: float,
        longitude: float,
        background_tasks: BackgroundTasks,
    ) -> CitizenReport:
        # 1. Resolve district from coordinates
        district_info = geography_service.resolve_district(latitude, longitude)
        district_id = district_info.get("id") if district_info else None

        # 2. Fast initial baseline score
        user_role = user.role if user else "citizen"
        initial_score = ConfidenceScorer.calculate_score(description=description, user_role=user_role)

        geo_point = from_shape(Point(longitude, latitude), srid=4326)

        # 3. Save report with initial SUBMITTED status
        report = CitizenReport(
            user_id=user.id if user else None,
            district_id=district_id,
            type=type,
            description=description,
            location=geo_point,
            latitude=latitude,
            longitude=longitude,
            status=ReportStatus.SUBMITTED,
            confidence_score=initial_score,
            is_duplicate=False,
        )
        db.add(report)
        await db.flush()

        audit = AuditEvent(
            actor=user.email if user else "anonymous",
            action="report_submitted",
            affected_record=f"CitizenReport:{report.id}",
            details={"type": report.type, "district_id": district_id},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(report)

        # 4. Trigger non-blocking background analysis
        background_tasks.add_task(async_process_report_intelligence, report.id)

        return report

    @classmethod
    async def upload_report_media(
        cls,
        db: AsyncSession,
        user: Optional[User],
        report_id: int,
        file: UploadFile,
    ) -> ReportMedia:
        # 1. Verify report exists
        q = await db.execute(select(CitizenReport).filter(CitizenReport.id == report_id))
        report = q.scalar_one_or_none()
        if not report:
            raise EntityNotFoundException("CitizenReport", report_id)

        # Permissions check: citizen can only upload to their own report
        if user and user.normalized_role == Role.CITIZEN and report.user_id != user.id:
            raise PermissionDeniedException("You can only upload attachments to your own reports.")

        # 2. Validate MIME content type
        content_type = file.content_type or ""
        if content_type.lower() not in ALLOWED_CONTENT_TYPES:
            raise FileValidationException(
                f"File type '{content_type}' is not permitted. Allowed: {list(ALLOWED_CONTENT_TYPES)}"
            )

        # 3. Read and validate file size
        file_bytes = await file.read()
        file_size = len(file_bytes)
        if file_size > MAX_FILE_SIZE_BYTES:
            raise FileValidationException(
                f"File size exceeds maximum permitted limit of {MAX_FILE_SIZE_BYTES / (1024*1024)} MB."
            )

        # 4. Save file to persistent storage volume
        file_ext = Path(file.filename or "media").suffix or ".bin"
        unique_filename = f"{report_id}_{uuid.uuid4().hex[:10]}{file_ext}"
        destination_path = UPLOAD_DIR / unique_filename

        with open(destination_path, "wb") as f:
            f.write(file_bytes)

        # 5. Persist record and boost report confidence
        relative_web_path = f"/uploads/{unique_filename}"
        media = ReportMedia(
            report_id=report.id,
            file_path=relative_web_path,
            file_name=file.filename or unique_filename,
            file_size_bytes=file_size,
            content_type=content_type,
        )
        db.add(media)

        # Elevate confidence score due to photographic proof
        report.confidence_score = min(1.0, report.confidence_score + 0.20)
        db.add(report)

        audit = AuditEvent(
            actor=user.email if user else "anonymous",
            action="report_media_uploaded",
            affected_record=f"CitizenReport:{report.id}",
            details={"file_name": file.filename, "file_size": file_size, "content_type": content_type},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(media)
        return media

    @classmethod
    async def get_public_verified_reports(
        cls,
        db: AsyncSession,
        district_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[CitizenReport]:
        """
        Enforces public publication rule:
        Citizens and map feeds ONLY receive VERIFIED incident reports.
        """
        query = (
            select(CitizenReport)
            .options(selectinload(CitizenReport.media))
            .filter(CitizenReport.status == ReportStatus.VERIFIED)
            .order_by(CitizenReport.created_at.desc())
            .limit(limit)
        )
        if district_id:
            query = query.filter(CitizenReport.district_id == district_id)

        res = await db.execute(query)
        return res.scalars().all()

    @classmethod
    async def get_citizen_own_reports(cls, db: AsyncSession, user: User) -> List[CitizenReport]:
        """Returns reports submitted by the authenticated citizen."""
        query = (
            select(CitizenReport)
            .options(selectinload(CitizenReport.media), selectinload(CitizenReport.reviews))
            .filter(CitizenReport.user_id == user.id)
            .order_by(CitizenReport.created_at.desc())
        )
        res = await db.execute(query)
        return res.scalars().all()

    @classmethod
    async def get_officer_review_queue(
        cls,
        db: AsyncSession,
        officer: User,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[CitizenReport]:
        """
        Retrieves review queue strictly restricted by officer's permitted district jurisdiction.
        """
        user_role = officer.normalized_role
        query = (
            select(CitizenReport)
            .options(selectinload(CitizenReport.media), selectinload(CitizenReport.reviews))
            .order_by(CitizenReport.created_at.desc())
            .limit(limit)
        )

        if user_role == Role.DISTRICT_OFFICER:
            if not officer.assigned_district_id:
                return []
            query = query.filter(CitizenReport.district_id == officer.assigned_district_id)
        elif user_role == Role.STATE_ADMIN:
            from app.models.geography import District
            query = query.join(District, CitizenReport.district_id == District.id).filter(
                District.state_id == officer.assigned_state_id
            )

        if status:
            query = query.filter(CitizenReport.status == status.lower())

        res = await db.execute(query)
        return res.scalars().all()

    @classmethod
    async def assign_report(cls, db: AsyncSession, officer: User, report_id: int) -> CitizenReport:
        """Assigns report to officer and transitions status to UNDER_REVIEW."""
        q = await db.execute(select(CitizenReport).filter(CitizenReport.id == report_id))
        report = q.scalar_one_or_none()
        if not report:
            raise EntityNotFoundException("CitizenReport", report_id)

        # Enforce district jurisdiction
        if officer.normalized_role == Role.DISTRICT_OFFICER:
            if report.district_id != officer.assigned_district_id:
                raise DistrictAccessDeniedException(officer.assigned_district_id, report.district_id)

        report.assigned_officer_id = officer.id
        report.status = ReportStatus.UNDER_REVIEW
        report.updated_at = datetime.now(timezone.utc)
        db.add(report)

        audit = AuditEvent(
            actor=officer.email,
            action="report_assigned",
            affected_record=f"CitizenReport:{report.id}",
            details={"assigned_to": officer.email, "status": ReportStatus.UNDER_REVIEW},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(report)
        return report

    @classmethod
    async def review_report(
        cls,
        db: AsyncSession,
        officer: User,
        report_id: int,
        decision: str,
        notes: Optional[str] = None,
    ) -> CitizenReport:
        """
        Executes formal officer review decision:
        Decision must be 'verified', 'rejected', or 'resolved'.
        """
        decision_clean = decision.lower().strip()
        allowed_decisions = {ReportStatus.VERIFIED, ReportStatus.REJECTED, ReportStatus.RESOLVED}
        if decision_clean not in allowed_decisions:
            raise InvalidOperationException(f"Invalid review decision '{decision}'. Allowed: {list(allowed_decisions)}")

        q = await db.execute(select(CitizenReport).filter(CitizenReport.id == report_id))
        report = q.scalar_one_or_none()
        if not report:
            raise EntityNotFoundException("CitizenReport", report_id)

        # Enforce district jurisdiction
        if officer.normalized_role == Role.DISTRICT_OFFICER:
            if report.district_id != officer.assigned_district_id:
                raise DistrictAccessDeniedException(officer.assigned_district_id, report.district_id)

        # Record review
        review = ReportReview(
            report_id=report.id,
            reviewer_id=officer.id,
            decision=decision_clean,
            notes=notes,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(review)

        # Update report status
        report.status = decision_clean
        report.updated_at = datetime.now(timezone.utc)
        db.add(report)

        audit = AuditEvent(
            actor=officer.email,
            action=f"report_decision_{decision_clean}",
            affected_record=f"CitizenReport:{report.id}",
            details={"decision": decision_clean, "notes": notes},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(report)
        return report

    @classmethod
    async def reopen_report(cls, db: AsyncSession, officer: User, report_id: int, notes: str) -> CitizenReport:
        """
        Reopens a previously resolved or rejected incident report.
        Workflow: transitions status back to UNDER_REVIEW, increments reopened_count.
        """
        q = await db.execute(select(CitizenReport).filter(CitizenReport.id == report_id))
        report = q.scalar_one_or_none()
        if not report:
            raise EntityNotFoundException("CitizenReport", report_id)

        # Enforce jurisdiction
        if officer.normalized_role == Role.DISTRICT_OFFICER:
            if report.district_id != officer.assigned_district_id:
                raise DistrictAccessDeniedException(officer.assigned_district_id, report.district_id)

        if report.status not in {ReportStatus.REJECTED, ReportStatus.RESOLVED}:
            raise InvalidOperationException(
                f"Only reports in 'rejected' or 'resolved' status can be reopened. Current status: '{report.status}'."
            )

        report.status = ReportStatus.UNDER_REVIEW
        report.reopened_count += 1
        report.reopened_at = datetime.now(timezone.utc)
        report.updated_at = datetime.now(timezone.utc)
        db.add(report)

        review = ReportReview(
            report_id=report.id,
            reviewer_id=officer.id,
            decision="reopened",
            notes=notes,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(review)

        audit = AuditEvent(
            actor=officer.email,
            action="report_reopened",
            affected_record=f"CitizenReport:{report.id}",
            details={"reopened_count": report.reopened_count, "notes": notes},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(report)
        return report


report_service = ReportService()
