from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.alert import Alert, AlertArea
from app.models.geography import District
from app.models.user import User
from app.models.audit import AuditEvent
from app.schemas.alert import AlertOut, AlertCreate
from app.api.deps import require_officer_or_admin

router = APIRouter(prefix="/alerts", tags=["Emergency Alerts"])


@router.get("", response_model=List[AlertOut])
async def list_alerts(
    district_id: Optional[int] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query("active"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Alert).options(selectinload(Alert.areas))
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    if district_id:
        query = query.join(Alert.areas).filter(AlertArea.district_id == district_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{alert_id}", response_model=AlertOut)
async def get_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).options(selectinload(Alert.areas)).filter(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.post("", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_in: AlertCreate,
    current_user: User = Depends(require_officer_or_admin),
    db: AsyncSession = Depends(get_db),
):
    new_alert = Alert(
        type=alert_in.type,
        title=alert_in.title,
        description=alert_in.description,
        severity=alert_in.severity,
        issuer=alert_in.issuer,
        valid_from=alert_in.valid_from,
        valid_to=alert_in.valid_to,
        status="active",
    )
    db.add(new_alert)
    await db.flush()

    for did in alert_in.district_ids or []:
        d_res = await db.execute(select(District).filter(District.id == did))
        dist = d_res.scalar_one_or_none()
        if dist:
            area = AlertArea(
                alert_id=new_alert.id,
                district_id=dist.id,
                boundary_geojson=dist.boundary_geojson,
            )
            db.add(area)

    audit = AuditEvent(
        actor=current_user.email,
        action="create_alert",
        affected_record=f"Alert:{new_alert.id}",
        details={"severity": alert_in.severity, "type": alert_in.type},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(new_alert)
    return new_alert
