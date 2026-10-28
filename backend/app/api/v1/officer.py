from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, HTTPException, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.db.session import get_db, AsyncSessionLocal
from app.models.report import CitizenReport, ReportReview, ReportStatus, ReportMedia
from app.models.alert import Alert
from app.models.hazard import HazardObservation
from app.models.geography import Facility, District
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.report import (
    CitizenReportReviewCreate,
    CitizenReportReopenRequest,
    CitizenReportOut,
)
from app.api.deps import require_officer_or_above
from app.services.report_service import report_service
from app.intelligence.duplicate_detector import duplicate_detector
from app.core.roles import Role
from app.core.websocket import manager

router = APIRouter(prefix="/officer", tags=["Officer Operations & Verification Queue"])


@router.websocket("/ws")
async def websocket_dashboard_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time government dashboard synchronization.
    Broadcasts incident submissions, review decisions, and alert changes live.
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep-alive ping/pong
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@router.get("/metrics")
async def get_dashboard_metrics(
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculates operational metrics directly from PostgreSQL queries.
    Scoped strictly by jurisdiction:
    - District Officer: Assigned district only
    - State Admin: Assigned state
    - System Admin: Global
    """
    district_filter = None
    if current_user.normalized_role == Role.DISTRICT_OFFICER:
        district_filter = current_user.assigned_district_id

    # 1. Status counts
    counts = {
        "submitted": 0,
        "under_review": 0,
        "verified": 0,
        "rejected": 0,
        "resolved": 0,
        "reopened": 0,
    }

    base_q = select(CitizenReport.status, func.count(CitizenReport.id)).group_by(CitizenReport.status)
    if district_filter:
        base_q = base_q.filter(CitizenReport.district_id == district_filter)
    
    res = await db.execute(base_q)
    for row in res.all():
        st, cnt = row[0], row[1]
        if st in counts:
            counts[st] = cnt

    # Unresolved metric definition: Incidents currently requiring intervention (submitted + under_review + verified)
    unresolved_count = counts["submitted"] + counts["under_review"] + counts["verified"]

    # 2. Active alerts count
    alert_q = select(func.count(Alert.id)).filter(Alert.status == "active")
    alert_res = await db.execute(alert_q)
    active_alerts = alert_res.scalar_one()

    # 3. Recent activity from AuditEvent
    audit_q = select(AuditEvent).order_by(desc(AuditEvent.timestamp)).limit(8)
    audit_res = await db.execute(audit_q)
    recent_events = [
        {
            "id": a.id,
            "actor": a.actor,
            "action": a.action,
            "affected_record": a.affected_record,
            "timestamp": a.timestamp.isoformat(),
            "details": a.details,
        }
        for a in audit_res.scalars().all()
    ]

    return {
        "jurisdiction": {
            "role": current_user.role,
            "assigned_district_id": current_user.assigned_district_id,
            "assigned_state_id": current_user.assigned_state_id,
        },
        "metrics": {
            "submitted": counts["submitted"],
            "under_review": counts["under_review"],
            "verified": counts["verified"],
            "rejected": counts["rejected"],
            "resolved": counts["resolved"],
            "reopened": counts["reopened"],
            "unresolved": unresolved_count,
            "total_reports": sum(counts.values()),
            "active_alerts": active_alerts,
        },
        "recent_activity": recent_events,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/reports", response_model=List[CitizenReportOut])
async def get_officer_review_queue(
    status: Optional[str] = Query(None, description="submitted, under_review, verified, rejected, resolved, reopened"),
    hazard: Optional[str] = Query(None, description="flood, fire, landslide, etc."),
    limit: int = Query(100, ge=1, le=200),
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    Filterable verification queue for officers.
    Strictly scoped to officer jurisdiction in backend queries.
    """
    reports = await report_service.get_officer_review_queue(
        db=db,
        officer=current_user,
        status=status,
        limit=limit,
    )
    if hazard and hazard.lower() != "all":
        reports = [r for r in reports if hazard.lower() in r.type.lower()]
    return reports


@router.get("/reports/{report_id}/detail")
async def get_report_detail_with_context(
    report_id: int,
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    Detailed report inspector for officers:
    - Factual description, location coordinates, district boundary info
    - Attached evidence files
    - Review history timeline
    - Machine learning duplicate detection clusters
    - Supporting environmental observations (weather rainfall, river level)
    """
    q = select(CitizenReport).filter(CitizenReport.id == report_id)
    res = await db.execute(q)
    report = res.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Incident report not found.")

    # Jurisdiction enforcement
    if current_user.normalized_role == Role.DISTRICT_OFFICER:
        if report.district_id != current_user.assigned_district_id:
            raise HTTPException(
                status_code=403,
                detail=f"Report belongs to district {report.district_id}, outside your jurisdiction."
            )

    # 1. Nearby observations
    obs_q = (
        select(HazardObservation)
        .filter(HazardObservation.district_id == report.district_id)
        .order_by(desc(HazardObservation.observed_time))
        .limit(3)
    )
    obs_res = await db.execute(obs_q)
    observations = [
        {
            "hazard_type": o.hazard_type,
            "values": o.values,
            "source": o.source,
            "observed_at": o.observed_time.isoformat() if o.observed_time else None,
        }
        for o in obs_res.scalars().all()
    ]

    # 2. Duplicate detection candidates
    dup_q = select(CitizenReport).filter(
        CitizenReport.id != report.id,
        CitizenReport.district_id == report.district_id,
        CitizenReport.type == report.type,
    ).limit(5)
    dup_res = await db.execute(dup_q)
    potential_duplicates = [
        {
            "id": d.id,
            "description": d.description,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "similarity_score": duplicate_detector.calculate_similarity(report.description, d.description),
        }
        for d in dup_res.scalars().all()
    ]
    # Filter to potential matches
    matching_duplicates = [d for d in potential_duplicates if d["similarity_score"] > 0.35]

    return {
        "report": {
            "id": report.id,
            "user_id": report.user_id,
            "district_id": report.district_id,
            "assigned_officer_id": report.assigned_officer_id,
            "type": report.type,
            "description": report.description,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "status": report.status,
            "confidence_score": report.confidence_score,
            "reopened_count": report.reopened_count,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "updated_at": report.updated_at.isoformat() if report.updated_at else None,
            "media": [
                {
                    "id": m.id,
                    "file_path": m.file_path,
                    "file_name": m.file_name,
                    "content_type": m.content_type,
                    "file_size_bytes": m.file_size_bytes,
                }
                for m in (report.media or [])
            ],
            "reviews": [
                {
                    "id": rev.id,
                    "reviewer_id": rev.reviewer_id,
                    "decision": rev.decision,
                    "notes": rev.notes,
                    "timestamp": rev.timestamp.isoformat(),
                }
                for rev in (report.reviews or [])
            ],
        },
        "observations": observations,
        "potential_duplicates": matching_duplicates,
    }


@router.get("/operational-incidents")
async def get_operational_map_incidents(
    status: Optional[str] = Query(None, description="Filter by status or leave empty for all"),
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    Officer operational map endpoint.
    Unlike public map (which is strictly verified-only), this returns ALL incident reports
    within officer jurisdiction, including unverified submissions, under-review items, and rejections.
    """
    district_filter = None
    if current_user.normalized_role == Role.DISTRICT_OFFICER:
        district_filter = current_user.assigned_district_id

    q = select(CitizenReport)
    if district_filter:
        q = q.filter(CitizenReport.district_id == district_filter)
    if status and status.lower() != "all":
        q = q.filter(CitizenReport.status == status.lower())
    
    q = q.order_by(desc(CitizenReport.created_at)).limit(200)
    res = await db.execute(q)
    reports = res.scalars().all()

    features = []
    for r in reports:
        features.append({
            "type": "Feature",
            "id": r.id,
            "properties": {
                "id": r.id,
                "type": r.type,
                "description": r.description,
                "status": r.status,
                "confidence_score": r.confidence_score,
                "assigned_officer_id": r.assigned_officer_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [r.longitude, r.latitude],
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.post("/reports/{report_id}/assign", response_model=CitizenReportOut)
async def assign_report_to_self(
    report_id: int,
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """Assigns an incident report to the authenticated officer."""
    rep = await report_service.assign_report(
        db=db,
        officer=current_user,
        report_id=report_id,
    )
    await manager.broadcast({
        "type": "REPORT_ASSIGNED",
        "report_id": rep.id,
        "officer": current_user.email,
        "status": rep.status,
    })
    return rep


@router.post("/reports/{report_id}/review", response_model=CitizenReportOut)
async def review_citizen_report(
    report_id: int,
    review_in: CitizenReportReviewCreate,
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """Applies official review decision (verified, rejected, or resolved)."""
    rep = await report_service.review_report(
        db=db,
        officer=current_user,
        report_id=report_id,
        decision=review_in.decision,
        notes=review_in.notes,
    )
    await manager.broadcast({
        "type": "REPORT_REVIEWED",
        "report_id": rep.id,
        "decision": review_in.decision,
        "officer": current_user.email,
        "status": rep.status,
    })
    return rep


@router.post("/reports/{report_id}/reopen", response_model=CitizenReportOut)
async def reopen_incident_report(
    report_id: int,
    reopen_in: CitizenReportReopenRequest,
    current_user: User = Depends(require_officer_or_above),
    db: AsyncSession = Depends(get_db),
):
    """Reopens a previously resolved or rejected incident report."""
    rep = await report_service.reopen_report(
        db=db,
        officer=current_user,
        report_id=report_id,
        notes=reopen_in.notes,
    )
    await manager.broadcast({
        "type": "REPORT_REOPENED",
        "report_id": rep.id,
        "officer": current_user.email,
        "status": rep.status,
    })
    return rep
