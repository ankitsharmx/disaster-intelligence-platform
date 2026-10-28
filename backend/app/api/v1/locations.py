from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.geography import State, District, Facility
from app.schemas.geography import (
    DistrictResolveRequest,
    DistrictResolveResponse,
    DistrictOut,
    FacilityOut,
)
from app.services.geography_service import geography_service, GeographyService

router = APIRouter(prefix="/locations", tags=["Locations & Geography"])


@router.get("/states")
async def list_states(db: AsyncSession = Depends(get_db)):
    """Retrieves all registered states and count of districts."""
    query = select(State).options(selectinload(State.districts))
    res = await db.execute(query)
    states = res.scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "code": s.code,
            "districts_count": len(s.districts),
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in states
    ]


@router.get("/districts", response_model=List[DistrictOut])
async def list_districts(
    state_id: Optional[int] = Query(None, description="Filter districts by state ID"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves administrative districts with center coordinates and boundary polygons."""
    query = select(District)
    if state_id:
        query = query.filter(District.state_id == state_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/resolve", response_model=DistrictResolveResponse)
async def resolve_district_get(
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate"),
):
    """
    GET coordinate-to-district resolution endpoint.
    Determines administrative district containment using fast point-in-polygon evaluation.
    """
    res = geography_service.resolve_district(latitude, longitude)
    if res:
        return {"found": True, "district": res, "message": f"Resolved to {res.get('name')}"}
    return {
        "found": False,
        "district": None,
        "message": "Coordinates are outside the supported geographic boundary.",
    }


@router.post("/resolve", response_model=DistrictResolveResponse)
async def resolve_district_post(coords: DistrictResolveRequest):
    """POST coordinate-to-district resolution endpoint."""
    return await resolve_district_get(coords.latitude, coords.longitude)


@router.post("/resolve-district", response_model=DistrictResolveResponse, deprecated=True)
async def resolve_district_legacy(coords: DistrictResolveRequest):
    """Legacy compatibility endpoint."""
    return await resolve_district_get(coords.latitude, coords.longitude)


@router.get("/facilities", response_model=List[FacilityOut])
async def list_facilities(
    district_id: Optional[int] = Query(None, description="Filter by district ID"),
    category: Optional[str] = Query(None, description="hospital, shelter, police, fire_station"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Facility)
    if district_id:
        query = query.filter(Facility.district_id == district_id)
    if category:
        query = query.filter(Facility.category == category)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/nearest-facilities")
async def get_nearest_facilities(
    latitude: float = Query(..., description="User latitude"),
    longitude: float = Query(..., description="User longitude"),
    category: Optional[str] = Query(None, description="hospital, shelter, police, fire_station"),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    query = select(Facility)
    if category:
        query = query.filter(Facility.category == category)
    result = await db.execute(query)
    facilities = result.scalars().all()

    sorted_facs = []
    for f in facilities:
        dist_km = GeographyService.calculate_haversine_distance_km(latitude, longitude, f.latitude, f.longitude)
        sorted_facs.append({
            "id": f.id,
            "name": f.name,
            "category": f.category,
            "distance_km": round(dist_km, 2),
            "latitude": f.latitude,
            "longitude": f.longitude,
            "contact_number": f.contact_number,
            "capacity": f.capacity,
            "details": f.details,
        })

    sorted_facs.sort(key=lambda x: x["distance_km"])
    return sorted_facs[:limit]
