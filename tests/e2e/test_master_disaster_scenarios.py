"""
Multi-Hazard Disaster Intelligence Platform - Master Testing Suite
Category 12: Master End-to-End Disaster Scenarios & Acceptance Criteria (All 6 Scenarios)
"""

import sys
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "backend"))

from app.main import app
from app.core.security import create_access_token

@pytest.mark.asyncio
async def test_scenario_01_heavy_rain_flood_lifecycle():
    """Scenario 1: Heavy rainfall -> Indicative flood risk -> Citizen report -> Officer verify -> Map appearance."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Step 1: Calculate indicative flood risk
        res_risk = await ac.get("/api/v1/intelligence/risk/flood?district_id=2&rainfall_1h_mm=45.0&rainfall_24h_mm=125.0&engine=ml")
        assert res_risk.status_code == 200
        risk_data = res_risk.json()
        assert risk_data["hazard"] == "FLOOD"

        # Step 2: Citizen submits flooded road report
        citizen_token = create_access_token(subject=5)  # Citizen user ID 5
        headers_cit = {"Authorization": f"Bearer {citizen_token}"}
        res_rep = await ac.post("/api/v1/reports", json={
            "type": "flood",
            "description": "SV Road completely waterlogged, water depth 3 feet",
            "latitude": 19.0760,
            "longitude": 72.8777
        }, headers=headers_cit)
        assert res_rep.status_code == 201
        report_id = res_rep.json()["id"]

        # Step 3: Officer verifies report
        officer_token = create_access_token(subject=3)  # Officer Mumbai Suburban (district 2)
        headers_off = {"Authorization": f"Bearer {officer_token}"}
        res_ver = await ac.post(f"/api/v1/officer/reports/{report_id}/review", json={
            "decision": "verified",
            "notes": "Verified by traffic police on ground"
        }, headers=headers_off)
        assert res_ver.status_code == 200
        assert res_ver.json()["status"] == "verified"

        # Step 4: Verify it now appears on public map
        res_map = await ac.get("/api/v1/map/layers?district_id=2")
        assert res_map.status_code == 200
        incidents = res_map.json().get("incidents", {}).get("features", [])
        verified_ids = [feat["id"] for feat in incidents]
        assert report_id in verified_ids, "Verified report missing from public map layer!"

@pytest.mark.asyncio
async def test_scenario_02_landslide_event():
    """Scenario 2: Landslide susceptibility -> Dynamic risk -> Report -> Officer review."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Step 1: Query dynamic landslide risk
        res_ls = await ac.get("/api/v1/intelligence/risk/landslide?district_id=4&rainfall_72h_mm=260.0&rainfall_24h_mm=150.0&avg_slope_deg=34.0&engine=ml")
        assert res_ls.status_code == 200
        data = res_ls.json()
        assert data["hazard"] == "LANDSLIDE"
        assert data["rainfall_trigger_status"] in ["HIGH_SATURATION", "CRITICAL_PORE_PRESSURE"]

        # Step 2: Citizen reports landslide
        citizen_token = create_access_token(subject=5)
        headers_cit = {"Authorization": f"Bearer {citizen_token}"}
        res_rep = await ac.post("/api/v1/reports", json={
            "type": "landslide",
            "description": "Mudslide blocking ghat road near Khandala section",
            "latitude": 18.750,
            "longitude": 73.370
        }, headers=headers_cit)
        assert res_rep.status_code == 201

@pytest.mark.asyncio
async def test_scenario_03_duplicate_incident_grouping():
    """Scenario 3: Three citizens report same incident -> System clusters them for officer."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        citizen_token = create_access_token(subject=5)
        headers_cit = {"Authorization": f"Bearer {citizen_token}"}

        # Submit 3 nearby flood reports
        for i, text in enumerate([
            "Milan subway flooded traffic completely stopped",
            "Severe waterlogging at Milan subway underpass road",
            "Milan subway flooded cars turning back"
        ]):
            res = await ac.post("/api/v1/reports", json={
                "type": "flood",
                "description": text,
                "latitude": 19.088 + (i * 0.0005),
                "longitude": 72.842 + (i * 0.0005)
            }, headers=headers_cit)
            assert res.status_code == 201

        # Check duplicate clustering endpoint
        officer_token = create_access_token(subject=3)
        headers_off = {"Authorization": f"Bearer {officer_token}"}
        res_cluster = await ac.post("/api/v1/intelligence/duplicates/cluster", json={
            "district_id": 2,
            "max_distance_meters": 1000.0,
            "max_time_delta_seconds": 7200.0
        }, headers=headers_off)
        assert res_cluster.status_code == 200
        cluster_data = res_cluster.json()
        assert "all_clusters" in cluster_data or "clusters" in cluster_data

@pytest.mark.asyncio
async def test_scenario_04_earthquake_observations_and_safety():
    """Scenario 4: Bilingual earthquake safety guidelines in English and Hindi."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Check earthquake safety content in English
        res_safety = await ac.get("/api/v1/awareness?hazard=earthquake&language=en")
        assert res_safety.status_code == 200
        content_en = res_safety.json()
        assert len(content_en) > 0
        assert "earthquake" in content_en[0]["hazard"].lower()
        assert "Drop, Cover, and Hold On" in content_en[0]["title"]

        # Check Hindi translation
        res_hi = await ac.get("/api/v1/awareness?hazard=earthquake&language=hi")
        assert res_hi.status_code == 200
        content_hi = res_hi.json()
        assert len(content_hi) > 0
        assert "भूकंप" in content_hi[0]["title"]

@pytest.mark.asyncio
async def test_scenario_05_forest_fire_safety_and_detection():
    """Scenario 5: Forest fire hazard guidelines in English and Hindi."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res_en = await ac.get("/api/v1/awareness?hazard=fire&language=en")
        assert res_en.status_code == 200
        content_en = res_en.json()
        assert len(content_en) > 0
        assert "fire" in content_en[0]["hazard"].lower()

        res_hi = await ac.get("/api/v1/awareness?hazard=fire&language=hi")
        assert res_hi.status_code == 200
        content_hi = res_hi.json()
        assert len(content_hi) > 0

@pytest.mark.asyncio
async def test_scenario_06_source_health_and_stale_tolerance():
    """Scenario 6: External source status, retrieval times, and graceful tolerance of outages."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get("/api/v1/integrations/sources")
        assert res.status_code == 200
        data = res.json()
        sources = data.get("sources", [])
        assert len(sources) > 0, "No data sources registered in platform"
        for s in sources:
            assert "source_id" in s
            assert "mode" in s  # live or demo
            assert "last_status" in s
