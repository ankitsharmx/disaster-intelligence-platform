"""
Unit & Integration Tests for ML Flood Prediction Service & API Endpoint
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.intelligence.flood_ml_service import flood_ml_service

@pytest.mark.asyncio
async def test_flood_ml_service_direct():
    """Verify that the FloodMLInferenceService loads and produces a structured prediction."""
    res = flood_ml_service.predict(
        district_id=2,
        district_name="Amritsar",
        observations={
            "rainfall": {"values": {"rainfall_1h_mm": 25.0, "rainfall_24h_mm": 80.0}}
        }
    )
    assert res["hazard"] == "FLOOD"
    assert res["prediction_horizon_hours"] == 72
    assert "risk_probability" in res
    assert res["risk_level"] in ["LOW", "MODERATE", "HIGH"]
    assert res["is_official_warning"] is False
    assert "contributing_factors" in res

@pytest.mark.asyncio
async def test_flood_ml_api_endpoint():
    """Verify GET /api/v1/intelligence/risk/flood with engine=ml returns 200 with ML fields."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/intelligence/risk/flood?district_id=2&rainfall_1h_mm=30.0&rainfall_24h_mm=95.0&engine=ml")
        assert resp.status_code == 200
        data = resp.json()
        assert data["hazard"] == "FLOOD"
        assert "risk_probability" in data
        assert "risk_level" in data
        assert "model_version" in data
        assert data["is_official_warning"] is False
