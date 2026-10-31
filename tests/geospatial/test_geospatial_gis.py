"""
Multi-Hazard Disaster Intelligence Platform - Master Testing Suite
Category 05: Geospatial & GIS Testing (GIS-01 to GIS-10 & Geotargeting)
"""

import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "backend"))

from app.main import app
from app.services.geography_service import geography_service

# Ground Truth Coordinates across Maharashtra and Punjab districts
GROUND_TRUTH_POINTS = [
    # (lat, lon, expected_name, is_supported)
    (19.0760, 72.8777, "Mumbai Suburban", True),
    (18.9220, 72.8347, "Mumbai City", True),
    (18.5204, 73.8567, "Pune", True),
    (31.6340, 74.8723, None, False), # Outside Maharashtra demo polygons
    (30.9010, 75.8573, None, False),
    (0.0, 0.0, None, False), # Atlantic Ocean
    (51.5074, -0.1278, None, False), # London
]

def test_gis_01_and_02_district_resolution_accuracy():
    """GIS-01 & GIS-02 (Original Target: >=95% resolution accuracy on supported points)."""
    correct = 0
    total_evaluated = 0

    for lat, lon, exp_name, is_supported in GROUND_TRUTH_POINTS:
        resolved = geography_service.resolve_district(lat, lon)
        total_evaluated += 1
        if is_supported:
            if resolved and exp_name in resolved.get("name", ""):
                correct += 1
        else:
            if resolved is None:
                correct += 1

    accuracy = correct / total_evaluated
    print(f"\nLocation resolution accuracy: {accuracy:.1%} ({correct}/{total_evaluated})")
    assert accuracy >= 0.95, f"Location resolution accuracy below target: {accuracy:.1%}"

@pytest.mark.asyncio
async def test_gis_05_and_06_invalid_coordinates_rejected():
    """GIS-05 & GIS-06: Coordinates exceeding physical lat/lon bounds rejected with 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Invalid Lat > 90
        res_lat = await ac.get("/api/v1/locations/resolve?latitude=95.0&longitude=72.8")
        assert res_lat.status_code == 422, "Lat > 90 must return 422 Unprocessable"

        # Invalid Lon > 180
        res_lon = await ac.get("/api/v1/locations/resolve?latitude=19.0&longitude=195.0")
        assert res_lon.status_code == 422, "Lon > 180 must return 422 Unprocessable"

@pytest.mark.asyncio
async def test_gis_alert_geotargeting_precision_and_recall():
    """GIS-Alert: Alert issued for District 2 is received by District 2 overview, strictly absent from District 4."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Query overview for targeted district 2 (Mumbai Suburban)
        res_target = await ac.get("/api/v1/overview?district_id=2")
        assert res_target.status_code == 200
        data_target = res_target.json()
        target_alerts = data_target.get("applicable_alerts", [])

        # Query overview for non-targeted district 4 (Pune)
        res_other = await ac.get("/api/v1/overview?district_id=4")
        assert res_other.status_code == 200
        data_other = res_other.json()
        other_alerts = data_other.get("applicable_alerts", [])

        target_ids = {a["id"] for a in target_alerts}
        other_ids = {a["id"] for a in other_alerts}

        assert 1 in target_ids, "Targeted district 2 failed to receive Alert #1"
        assert 1 not in other_ids, "Alert leakage: Untargeted district 4 received Alert #1!"
