from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.geography import District, Facility, State
from app.schemas.geography import (
    DistrictResolveRequest,
    DistrictResolveResponse,
    DistrictOut,
    FacilityOut,
)
from app.services.geography_service import geography_service, GeographyService

router = APIRouter(prefix="/locations", tags=["Locations & Geography"])


@router.post("/resolve-district", response_model=DistrictResolveResponse)
async def resolve_district_endpoint(coords: DistrictResolveRequest, db: AsyncSession = Depends(get_db)):
    """
    Resolves geographic coordinates (latitude, longitude) to the administrative district.
    Uses high-speed spatial point-in-polygon resolution.
    """
    res = geography_service.resolve_district(coords.latitude, coords.longitude)
    if res:
        return {"found": True, "district": res, "message": f"Resolved to {res.get('name')}"}
    return {
        "found": False,
        "district": None,
        "message": "Coordinates are outside the supported geographic boundary.",
    }


@router.get("/districts", response_model=List[DistrictOut])
async def list_districts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(District))
    return result.scalars().all()


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
    """Computes nearest emergency facilities sorted by great-circle distance."""
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
