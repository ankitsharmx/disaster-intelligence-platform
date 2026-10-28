from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.geography import District, Facility
from app.models.report import CitizenReport, ReportStatus

router = APIRouter(prefix="/map", tags=["Map Data & GeoJSON Layers"])


@router.get("/layers")
async def get_map_layers(
    district_id: Optional[int] = Query(None, description="Optional district filter"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns unified GeoJSON FeatureCollections for Leaflet map views:
    - boundaries: Administrative district polygons
    - facilities: Critical infrastructure (hospitals, shelters, police, fire stations)
    - incidents: VERIFIED citizen reports only.
    
    CRITICAL SECURITY & PUBLICATION RULE:
    Public map endpoints strictly exclude unverified or rejected incident reports.
    """
    # 1. District boundaries
    d_q = select(District)
    if district_id:
        d_q = d_q.filter(District.id == district_id)
    d_res = await db.execute(d_q)
    districts = d_res.scalars().all()
    boundary_features = []
    for d in districts:
        if d.boundary_geojson:
            boundary_features.append({
                "type": "Feature",
                "id": d.id,
                "properties": {
                    "id": d.id,
                    "name": d.name,
                    "code": d.code,
                    "center": [d.center_lat, d.center_lon],
                },
                "geometry": d.boundary_geojson,
            })

    # 2. Facilities
    f_q = select(Facility)
    if district_id:
        f_q = f_q.filter(Facility.district_id == district_id)
    f_res = await db.execute(f_q)
    facilities = f_res.scalars().all()
    facility_features = []
    for f in facilities:
        facility_features.append({
            "type": "Feature",
            "id": f.id,
            "properties": {
                "name": f.name,
                "category": f.category,
                "district_id": f.district_id,
                "contact_number": f.contact_number,
                "capacity": f.capacity,
                "details": f.details,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [f.longitude, f.latitude],
            },
        })

    # 3. Public Incidents (STRICTLY VERIFIED ONLY)
    r_q = select(CitizenReport).filter(CitizenReport.status == ReportStatus.VERIFIED).limit(200)
    if district_id:
        r_q = r_q.filter(CitizenReport.district_id == district_id)
    r_res = await db.execute(r_q)
    reports = r_res.scalars().all()
    report_features = []
    for r in reports:
        report_features.append({
            "type": "Feature",
            "id": r.id,
            "properties": {
                "id": r.id,
                "type": r.type,
                "description": r.description,
                "status": r.status,
                "confidence_score": r.confidence_score,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [r.longitude, r.latitude],
            },
        })

    return {
        "boundaries": {"type": "FeatureCollection", "features": boundary_features},
        "facilities": {"type": "FeatureCollection", "features": facility_features},
        "incidents": {"type": "FeatureCollection", "features": report_features},
    }
