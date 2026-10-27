import pytest
from app.services.geography_service import GeographyService, geography_service


def test_coordinate_inside_district():
    """Test point strictly inside Mumbai City boundaries."""
    # Marine Drive / Nariman Point area
    res = geography_service.resolve_district(lat=18.9300, lon=72.8250)
    assert res is not None
    assert res["name"] == "Mumbai City"
    assert res["code"] == "MUM_CITY"


def test_coordinate_inside_suburban_district():
    """Test point strictly inside Mumbai Suburban boundaries."""
    # Andheri area
    res = geography_service.resolve_district(lat=19.1190, lon=72.8465)
    assert res is not None
    assert res["name"] == "Mumbai Suburban"
    assert res["code"] == "MUM_SUB"


def test_coordinate_outside_supported_boundaries():
    """Test point outside all supported Maharashtra districts (e.g., Delhi, Bangalore, Bay of Bengal)."""
    # New Delhi
    res_delhi = geography_service.resolve_district(lat=28.6139, lon=77.2090)
    assert res_delhi is None

    # Middle of Arabian Sea
    res_sea = geography_service.resolve_district(lat=18.5000, lon=70.0000)
    assert res_sea is None


def test_coordinate_on_boundary():
    """
    Test point located directly on the boundary edge between Mumbai City and Mumbai Suburban.
    Boundary latitude is exactly 19.0400.
    """
    res = geography_service.resolve_district(lat=19.0400, lon=72.8400)
    assert res is not None
    assert res["name"] in ["Mumbai City", "Mumbai Suburban"]


def test_haversine_distance():
    """Test distance calculation between Colaba and Santacruz (approx 20 km)."""
    dist_km = GeographyService.calculate_haversine_distance_km(
        lat1=18.9067, lon1=72.8147,
        lat2=19.0760, lon2=72.8777,
    )
    assert 18.0 <= dist_km <= 23.0
