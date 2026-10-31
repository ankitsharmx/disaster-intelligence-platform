"""
Unit & Integration Tests for ML Landslide Susceptibility & Risk Service
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.intelligence.landslide_ml_service import landslide_ml_service

@pytest.mark.asyncio
async def test_landslide_ml_service_direct():
    """Verify that LandslideMLInferenceService loads and produces structured predictions."""
    res = landslide_ml_service.predict(
        district_id=5,
        district_name="Raigad",
        slope_deg=34.0,
        elevation_m=950.0,
        observations={
            "rainfall": {"values": {"rainfall_24h_mm": 110.0, "rainfall_72h_mm": 260.0}}
        }
    )
    assert res["hazard"] == "LANDSLIDE"
    assert "susceptibility_probability" in res
    assert "dynamic_risk_probability" in res
    assert res["risk_level"] in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert res["is_official_warning"] is False
    assert res["rainfall_trigger_status"] in ["CRITICAL_PORE_PRESSURE", "HIGH_SATURATION", "MODERATE_INFILTRATION", "NOMINAL_STABLE"]
    assert "contributing_factors" in res

@pytest.mark.asyncio
async def test_landslide_ml_api_endpoint():
    """Verify GET /api/v1/intelligence/risk/landslide with engine=ml returns 200 with dynamic metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/intelligence/risk/landslide?district_id=5&rainfall_72h_mm=180.0&rainfall_24h_mm=80.0&avg_slope_deg=32.0&engine=ml")
        assert resp.status_code == 200
        data = resp.json()
        assert data["hazard"] == "LANDSLIDE"
        assert "susceptibility_probability" in data
        assert "dynamic_risk_probability" in data
        assert "risk_level" in data
        assert "rainfall_trigger_status" in data
        assert data["is_official_warning"] is False
