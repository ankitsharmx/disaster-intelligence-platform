from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.alert import Alert, AlertArea
from app.models.user import User
from app.schemas.alert import AlertOut, AlertCreate, AlertDraftCreate, AlertCancelRequest
from app.api.deps import require_officer_or_above, get_current_user
from app.services.alert_service import alert_service
from app.core.roles import Role

router = APIRouter(prefix="/alerts", tags=["Emergency Alerts"])


@router.get("", response_model=List[AlertOut])
async def list_alerts(
    district_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List alerts. Citizens and unauthenticated users ONLY receive active alerts.
    Officers and Admins can query all statuses including drafts.
    """
    query = select(Alert).options(selectinload(Alert.areas))

    is_privileged = current_user and current_user.normalized_role in {
        Role.DISTRICT_OFFICER,
        Role.STATE_ADMIN,
        Role.SYSTEM_ADMIN,
    }

    if not is_privileged:
        query = query.filter(Alert.status == "active")
    elif status:
        query = query.filter(Alert.status == status)

    if severity:
        query = query.filter(Alert.severity == severity.lower())
    if district_id:
        query = query.join(Alert.areas).filter(AlertArea.district_id == district_id)

    result = await db.execute(query.order_by(Alert.created_at.desc()))
    return result.scalars().all()


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).options(selectinload(Alert.areas)).filter(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
async def issue_alert(
    alert_in: AlertCreate,
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """Issues an active alert. Strictly validates user district jurisdiction."""
    return await alert_service.create_alert(
        db=db,
        user=current_user,
        type=alert_in.type,
        title=alert_in.title,
        description=alert_in.description,
        severity=alert_in.severity,
        issuer=alert_in.issuer,
        valid_from=alert_in.valid_from,
        valid_to=alert_in.valid_to,
        district_ids=alert_in.district_ids or [],
        is_official=alert_in.is_official,
        as_draft=False,
    )


@router.post("/draft", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
async def draft_alert(
    alert_in: AlertDraftCreate,
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """Creates an alert in DRAFT status. Not published to public feeds."""
    return await alert_service.create_alert(
        db=db,
        user=current_user,
        type=alert_in.type,
        title=alert_in.title,
        description=alert_in.description,
        severity=alert_in.severity,
        issuer=alert_in.issuer,
        valid_from=alert_in.valid_from,
        valid_to=alert_in.valid_to,
        district_ids=alert_in.district_ids or [],
        is_official=alert_in.is_official,
        as_draft=True,
    )


@router.post("/{alert_id}/issue", response_model=AlertOut)
async def issue_draft_alert(
    alert_id: int,
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """Transitions a draft alert to active status."""
    return await alert_service.issue_draft(db=db, user=current_user, alert_id=alert_id)


@router.post("/{alert_id}/cancel", response_model=AlertOut)
async def cancel_alert(
    alert_id: int,
    req: AlertCancelRequest = AlertCancelRequest(),
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """Cancels an alert with an audit log reason."""
    return await alert_service.cancel_alert(db=db, user=current_user, alert_id=alert_id, reason=req.reason or "")


@router.post("/{alert_id}/expire", response_model=AlertOut)
async def expire_alert(
    alert_id: int,
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """Manually expires an alert."""
    return await alert_service.expire_alert(db=db, user=current_user, alert_id=alert_id)
