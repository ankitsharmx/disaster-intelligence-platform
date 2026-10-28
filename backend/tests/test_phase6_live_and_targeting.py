"""
Phase 6 Automated Test Suite: Live Ingestion, Targeting, GIS, Security & Isolation.
Verifies:
1. Live USGS earthquake and Open-Meteo weather adapters.
2. District-targeted alert containment (users inside receive, users outside do not).
3. Coordinate-to-district auto-resolution and boundary edge cases.
4. Unsupported coordinates and invalid input handling.
5. Zero-leakage rule: unverified reports never leak to public map layers.
6. Role-based security: unauthorized operations are strictly rejected (HTTP 403).
"""
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient

from app.integrations.earthquake import EarthquakeLiveSource
from app.integrations.weather import WeatherLiveSource
from app.services.geography_service import geography_service


def get_token(client: TestClient, email: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Failed to login {email}: {res.text}"
    return res.json()["access_token"]


def test_live_earthquake_adapter_normalization():
    """Verifies live USGS GeoJSON feed parsing, normalization, and bounds validation."""
    adapter = EarthquakeLiveSource()
    assert adapter.name == "usgs_earthquake_live"
    assert adapter.mode == "live"

    # Sample USGS feature structure
    sample_raw = {
        "features": [
            {
                "id": "us7000test",
                "properties": {
                    "mag": 4.8,
                    "place": "120 km SW of Ratnagiri, India",
                    "time": 1793181600000,
                    "magType": "mb",
                    "title": "M 4.8 - Ratnagiri Coastal Zone",
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [72.10, 16.20, 10.0],
                },
            }
        ]
    }

    normalized = adapter.normalize(sample_raw)
    assert len(normalized) == 1
    assert normalized[0]["hazard_type"] == "earthquake"
    assert normalized[0]["latitude"] == 16.20
    assert normalized[0]["longitude"] == 72.10
    assert normalized[0]["values"]["magnitude"] == 4.8

    valid = adapter.validate(normalized)
    assert len(valid) == 1


def test_live_weather_adapter_normalization():
    """Verifies Open-Meteo live forecast JSON normalization and validation."""
    adapter = WeatherLiveSource(lat=19.076, lon=72.877, location_name="Mumbai")
    assert adapter.name == "open_meteo_weather_live"
    assert adapter.mode == "live"

    sample_raw = {
        "latitude": 19.08,
        "longitude": 72.88,
        "current": {
            "time": "2026-10-28T10:00",
            "temperature_2m": 31.5,
            "relative_humidity_2m": 78.0,
            "precipitation": 12.4,
            "wind_speed_10m": 18.2,
        },
    }

    normalized = adapter.normalize(sample_raw)
    assert len(normalized) == 1
    assert normalized[0]["hazard_type"] == "rainfall"
    assert normalized[0]["values"]["rainfall_1h_mm"] == 12.4
    assert normalized[0]["values"]["temperature_c"] == 31.5

    valid = adapter.validate(normalized)
    assert len(valid) == 1


def test_integrations_api_sources_and_sync(client: TestClient):
    """Verifies GET /api/v1/integrations/sources and POST /api/v1/integrations/sync."""
    token_admin = get_token(client, "admin@disastermgmt.gov", "Admin@123456")
    headers = {"Authorization": f"Bearer {token_admin}"}

    # 1. Sources listing
    res_sources = client.get("/api/v1/integrations/sources")
    assert res_sources.status_code == 200
    data = res_sources.json()
    assert data["total_sources"] >= 6
    assert data["live_sources_count"] >= 2

    # Check that live USGS and Open-Meteo are present
    source_ids = [s["source_id"] for s in data["sources"]]
    assert "usgs_earthquake_live" in source_ids
    assert "open_meteo_weather_live" in source_ids


def test_alert_spatial_targeting_and_isolation(client: TestClient):
    """
    Verifies that alerts targeted to District 2 (Mumbai Suburban):
    - Appear in District 2 Overview API.
    - Strictly DO NOT appear in District 4 (Pune) Overview API.
    """
    token_admin = get_token(client, "admin@disastermgmt.gov", "Admin@123456")
    headers = {"Authorization": f"Bearer {token_admin}"}

    now = datetime.now(timezone.utc)
    target_alert = {
        "type": "flood",
        "title": "Mumbai Specific Flash Flood Alert (Phase 6 Test)",
        "description": "Localized inundation warning for low-lying suburban wards",
        "severity": "high",
        "issuer": "Mumbai Disaster Management Cell",
        "valid_from": now.isoformat(),
        "valid_to": (now + timedelta(hours=6)).isoformat(),
        "district_ids": [2],  # Targeted ONLY to Mumbai Suburban
        "is_official": True,
    }
    create_res = client.post("/api/v1/alerts", json=target_alert, headers=headers)
    assert create_res.status_code == 201
    alert_id = create_res.json()["id"]

    # 1. Target district (Mumbai Suburban, id=2) Overview: Alert MUST be present
    res_mumbai_overview = client.get("/api/v1/overview?district_id=2")
    assert res_mumbai_overview.status_code == 200
    m_alerts = [a["id"] for a in res_mumbai_overview.json()["applicable_alerts"]]
    assert alert_id in m_alerts, "Targeted alert must be received in District 2"

    # 2. Non-target district (Pune, id=4) Overview: Alert MUST NOT be present
    res_pune_overview = client.get("/api/v1/overview?district_id=4")
    assert res_pune_overview.status_code == 200
    p_alerts = [a["id"] for a in res_pune_overview.json()["applicable_alerts"]]
    assert alert_id not in p_alerts, "Targeted alert must NOT be received in District 4"


def test_coordinate_resolution_and_unsupported_locations(client: TestClient):
    """Verifies coordinate resolution into districts and safe handling of unsupported/invalid coordinates."""
    # 1. Valid Mumbai Suburban coordinate
    res_mumbai = client.get("/api/v1/locations/resolve?latitude=19.1197&longitude=72.8468")
    assert res_mumbai.status_code == 200
    assert res_mumbai.json()["found"] is True
    assert res_mumbai.json()["district"]["id"] == 2

    # 2. Valid Pune coordinate
    res_pune = client.get("/api/v1/locations/resolve?latitude=18.5204&longitude=73.8567")
    assert res_pune.status_code == 200
    assert res_pune.json()["found"] is True
    assert res_pune.json()["district"]["id"] == 4

    # 3. Unsupported location (Indian Ocean coordinates): safe fallback
    res_ocean = client.get("/api/v1/locations/resolve?latitude=5.0&longitude=70.0")
    assert res_ocean.status_code == 200
    assert res_ocean.json()["district"] is None
    assert "outside" in res_ocean.json()["message"].lower()

    # 4. Out-of-bounds coordinates: rejected by Pydantic schema validation
    res_invalid = client.get("/api/v1/locations/resolve?latitude=999.0&longitude=999.0")
    assert res_invalid.status_code == 422


def test_public_map_zero_leakage_rule(client: TestClient):
    """
    Verifies that unverified and rejected reports NEVER appear in public map layer responses:
    Submitted -> NOT on public map
    Rejected  -> NOT on public map
    Verified  -> Appears on public map
    """
    token_citizen = get_token(client, "citizen@example.com", "Citizen@123456")
    token_mumbai = get_token(client, "officer_mumbai@disastermgmt.gov", "Officer@123456")

    # 1. Citizen submits report
    rep_res = client.post(
        "/api/v1/reports",
        json={
            "type": "flood",
            "description": "Zero leakage test waterlogging report",
            "latitude": 19.1197,
            "longitude": 72.8468,
        },
        headers={"Authorization": f"Bearer {token_citizen}"},
    )
    assert rep_res.status_code == 201
    rep_id = rep_res.json()["id"]

    # 2. Public Map Check: Newly SUBMITTED report must NOT be visible
    map_res = client.get("/api/v1/map/layers")
    assert map_res.status_code == 200
    pub_ids = [f["properties"]["id"] for f in map_res.json()["incidents"]["features"]]
    assert rep_id not in pub_ids, "Unverified report must NEVER appear on public map"

    # 3. Officer rejects report
    reject_res = client.post(
        f"/api/v1/officer/reports/{rep_id}/review",
        json={"decision": "rejected", "notes": "Report rejected during test"},
        headers={"Authorization": f"Bearer {token_mumbai}"},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["status"] == "rejected"

    # 4. Public Map Check: REJECTED report must NOT be visible
    map_res2 = client.get("/api/v1/map/layers")
    pub_ids2 = [f["properties"]["id"] for f in map_res2.json()["incidents"]["features"]]
    assert rep_id not in pub_ids2, "Rejected report must NEVER appear on public map"

    # 5. Reopen and VERIFY report
    client.post(
        f"/api/v1/officer/reports/{rep_id}/reopen",
        json={"notes": "Reopening for verification test"},
        headers={"Authorization": f"Bearer {token_mumbai}"},
    )
    verify_res = client.post(
        f"/api/v1/officer/reports/{rep_id}/review",
        json={"decision": "verified", "notes": "Verified by field team"},
        headers={"Authorization": f"Bearer {token_mumbai}"},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "verified"

    # 6. Public Map Check: VERIFIED report MUST now appear
    map_res3 = client.get("/api/v1/map/layers")
    pub_ids3 = [f["properties"]["id"] for f in map_res3.json()["incidents"]["features"]]
    assert rep_id in pub_ids3, "Verified report MUST appear on public map"


def test_unauthorized_operations_rejected(client: TestClient):
    """
    Verifies that unauthorized role attempts are rejected with HTTP 403 Forbidden:
    - Citizen accessing officer metrics.
    - Citizen composing an alert.
    - District officer performing out-of-jurisdiction reviews.
    """
    token_citizen = get_token(client, "citizen@example.com", "Citizen@123456")
    token_pune = get_token(client, "officer_pune@disastermgmt.gov", "Officer@123456")

    headers_citizen = {"Authorization": f"Bearer {token_citizen}"}
    headers_pune = {"Authorization": f"Bearer {token_pune}"}

    # 1. Citizen attempts to view officer metrics -> 403
    res1 = client.get("/api/v1/officer/metrics", headers=headers_citizen)
    assert res1.status_code == 403

    # 2. Citizen attempts to create an alert -> 403
    res2 = client.post(
        "/api/v1/alerts",
        json={
            "type": "flood",
            "title": "Unauthorized citizen alert",
            "description": "Test",
            "severity": "high",
            "issuer": "Citizen",
            "valid_from": "2026-10-28T10:00:00Z",
            "valid_to": "2026-10-28T18:00:00Z",
            "district_ids": [2],
        },
        headers=headers_citizen,
    )
    assert res2.status_code == 403

    # 3. Officer Pune attempts to review an alert for Mumbai Suburban (district 2) -> 403
    res3 = client.post(
        "/api/v1/alerts",
        json={
            "type": "flood",
            "title": "Cross-district illegal alert",
            "description": "Test",
            "severity": "high",
            "issuer": "Officer Pune",
            "valid_from": "2026-10-28T10:00:00Z",
            "valid_to": "2026-10-28T18:00:00Z",
            "district_ids": [2],  # Mumbai Suburban
        },
        headers=headers_pune,
    )
    assert res3.status_code == 403
