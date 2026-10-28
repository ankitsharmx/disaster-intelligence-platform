from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.audit import AuditEvent
from app.models.user import User
from app.api.deps import require_admin_or_above

router = APIRouter(prefix="/audit", tags=["Audit Log & Governance"])


@router.get("/events")
async def list_audit_events(
    actor: Optional[str] = Query(None, description="Filter by actor email or service name"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_admin_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    Administrative audit trail endpoint.
    Restricted to State Administrators and System Administrators.
    Returns immutable records of alert creations, reviews, assignments, and system operations.
    """
    query = select(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit)
    if actor:
        query = query.filter(AuditEvent.actor == actor)
    if action:
        query = query.filter(AuditEvent.action.ilike(f"%{action}%"))

    res = await db.execute(query)
    events = res.scalars().all()
    return [
        {
            "id": e.id,
            "actor": e.actor,
            "action": e.action,
            "affected_record": e.affected_record,
            "details": e.details,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        }
        for e in events
    ]
