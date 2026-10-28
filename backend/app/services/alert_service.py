from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.alert import Alert, AlertArea
from app.models.geography import District
from app.models.user import User
from app.models.audit import AuditEvent
from app.core.roles import Role
from app.core.exceptions import (
    EntityNotFoundException,
    PermissionDeniedException,
    DistrictAccessDeniedException,
    InvalidOperationException,
)


class AlertService:
    @staticmethod
    async def validate_jurisdiction(user: User, district_ids: List[int], db: AsyncSession):
        """Enforces that the user has jurisdiction over all requested districts."""
        user_role = user.normalized_role

        if user_role == Role.SYSTEM_ADMIN:
            return  # System Admin has unrestricted jurisdiction

        if user_role == Role.STATE_ADMIN:
            if not user.assigned_state_id:
                raise PermissionDeniedException("State Administrator is not assigned to a state.")
            for did in district_ids:
                q = await db.execute(select(District).filter(District.id == did))
                d = q.scalar_one_or_none()
                if not d or d.state_id != user.assigned_state_id:
                    raise DistrictAccessDeniedException(officer_district_id=None, requested_district_id=did)
            return

        if user_role == Role.DISTRICT_OFFICER:
            if not user.assigned_district_id:
                raise PermissionDeniedException("District Officer is not assigned to any district.")
            for did in district_ids:
                if did != user.assigned_district_id:
                    raise DistrictAccessDeniedException(
                        officer_district_id=user.assigned_district_id,
                        requested_district_id=did,
                    )
            return

        raise PermissionDeniedException("Citizens are not authorized to manage emergency alerts.")

    @classmethod
    async def create_alert(
        cls,
        db: AsyncSession,
        user: User,
        type: str,
        title: str,
        description: str,
        severity: str,
        issuer: str,
        valid_from: datetime,
        valid_to: datetime,
        district_ids: List[int],
        is_official: Optional[bool] = None,
        as_draft: bool = False,
    ) -> Alert:
        # 1. Validate timestamps
        if valid_to <= valid_from:
            raise InvalidOperationException("Alert 'valid_to' must be strictly later than 'valid_from'.")

        # 2. Validate jurisdiction
        if not district_ids and user.normalized_role == Role.DISTRICT_OFFICER:
            district_ids = [user.assigned_district_id]
        await cls.validate_jurisdiction(user, district_ids, db)

        # 3. Determine official vs prototype status
        if is_official is None:
            # Default to official for system/state admins, prototype for district officers during demos
            is_official = user.normalized_role in {Role.SYSTEM_ADMIN, Role.STATE_ADMIN}

        initial_status = "draft" if as_draft else "active"

        # 4. Atomic transaction: Alert + Areas + AuditEvent
        alert = Alert(
            type=type,
            title=title,
            description=description,
            severity=severity.lower(),
            issuer=issuer,
            is_official=is_official,
            valid_from=valid_from,
            valid_to=valid_to,
            status=initial_status,
            created_by_user_id=user.id,
        )
        db.add(alert)
        await db.flush()

        for did in district_ids:
            d_res = await db.execute(select(District).filter(District.id == did))
            dist = d_res.scalar_one_or_none()
            if dist:
                area = AlertArea(
                    alert_id=alert.id,
                    district_id=dist.id,
                    boundary_geojson=dist.boundary_geojson,
                )
                db.add(area)

        action_name = "alert_drafted" if as_draft else "alert_issued"
        audit = AuditEvent(
            actor=user.email,
            action=action_name,
            affected_record=f"Alert:{alert.id}",
            details={
                "status": initial_status,
                "severity": alert.severity,
                "is_official": alert.is_official,
                "districts": district_ids,
            },
        )
        db.add(audit)
        await db.commit()
        await db.refresh(alert)
        return alert

    @classmethod
    async def issue_draft(cls, db: AsyncSession, user: User, alert_id: int) -> Alert:
        """Promotes a draft alert to active state."""
        q = await db.execute(select(Alert).options(selectinload(Alert.areas)).filter(Alert.id == alert_id))
        alert = q.scalar_one_or_none()
        if not alert:
            raise EntityNotFoundException("Alert", alert_id)

        district_ids = [a.district_id for a in alert.areas if a.district_id]
        await cls.validate_jurisdiction(user, district_ids, db)

        if alert.status != "draft":
            raise InvalidOperationException(f"Only alerts in 'draft' status can be issued. Current status: {alert.status}")

        alert.status = "active"
        alert.updated_at = datetime.now(timezone.utc)
        db.add(alert)

        audit = AuditEvent(
            actor=user.email,
            action="alert_issued",
            affected_record=f"Alert:{alert.id}",
            details={"previous_status": "draft", "new_status": "active"},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(alert)
        return alert

    @classmethod
    async def cancel_alert(cls, db: AsyncSession, user: User, alert_id: int, reason: str = "") -> Alert:
        """Cancels an active or draft alert."""
        q = await db.execute(select(Alert).options(selectinload(Alert.areas)).filter(Alert.id == alert_id))
        alert = q.scalar_one_or_none()
        if not alert:
            raise EntityNotFoundException("Alert", alert_id)

        district_ids = [a.district_id for a in alert.areas if a.district_id]
        await cls.validate_jurisdiction(user, district_ids, db)

        if alert.status in {"cancelled", "expired"}:
            raise InvalidOperationException(f"Alert is already {alert.status}.")

        alert.status = "cancelled"
        alert.updated_at = datetime.now(timezone.utc)
        db.add(alert)

        audit = AuditEvent(
            actor=user.email,
            action="alert_cancelled",
            affected_record=f"Alert:{alert.id}",
            details={"reason": reason},
        )
        db.add(audit)
        await db.commit()
        await db.refresh(alert)
        return alert

    @classmethod
    async def expire_alert(cls, db: AsyncSession, user: User, alert_id: int) -> Alert:
        """Marks an alert expired."""
        q = await db.execute(select(Alert).options(selectinload(Alert.areas)).filter(Alert.id == alert_id))
        alert = q.scalar_one_or_none()
        if not alert:
            raise EntityNotFoundException("Alert", alert_id)

        district_ids = [a.district_id for a in alert.areas if a.district_id]
        await cls.validate_jurisdiction(user, district_ids, db)

        alert.status = "expired"
        alert.updated_at = datetime.now(timezone.utc)
        db.add(alert)

        audit = AuditEvent(
            actor=user.email,
            action="alert_expired",
            affected_record=f"Alert:{alert.id}",
        )
        db.add(audit)
        await db.commit()
        await db.refresh(alert)
        return alert


alert_service = AlertService()
