from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.geography import District, Facility
from app.models.report import CitizenReport
from app.models.hazard import HazardObservation

router = APIRouter(prefix="/map", tags=["Map Data & GeoJSON Layers"])


@router.get("/layers")
async def get_map_layers(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns unified GeoJSON FeatureCollections optimized for Leaflet rendering:
    - boundaries: District polygon boundaries
    - facilities: Hospitals, shelters, police, and fire stations
    - incidents: Verified citizen reports
    """
    # 1. District boundaries
    d_res = await db.execute(select(District))
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
    f_res = await db.execute(select(Facility))
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

    # 3. Active Incident Reports
    r_res = await db.execute(
        select(CitizenReport).filter(CitizenReport.status.in_(["submitted", "verified"])).limit(100)
    )
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
                "is_duplicate": r.is_duplicate,
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
