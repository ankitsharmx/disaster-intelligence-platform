import pytest
from fastapi.testclient import TestClient


def get_token(client: TestClient, email: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Failed to login {email}: {res.text}"
    return res.json()["access_token"]


def test_officer_metrics_endpoint(client: TestClient):
    """Verifies operational metric counts calculation and unresolved definition."""
    token_mumbai = get_token(client, "officer_mumbai@disastermgmt.gov", "Officer@123456")
    headers = {"Authorization": f"Bearer {token_mumbai}"}

    res = client.get("/api/v1/officer/metrics", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "metrics" in data
    assert "jurisdiction" in data
    assert "recent_activity" in data
    metrics = data["metrics"]

    assert "submitted" in metrics
    assert "under_review" in metrics
    assert "verified" in metrics
    assert "rejected" in metrics
    assert "resolved" in metrics
    assert "unresolved" in metrics
    assert "active_alerts" in metrics

    # Check unresolved formula: unresolved = submitted + under_review + verified
    assert metrics["unresolved"] == metrics["submitted"] + metrics["under_review"] + metrics["verified"]


def test_officer_report_lifecycle_and_review_actions(client: TestClient):
    """
    Verifies full officer workflow:
    - Citizen submits a report
    - Mumbai officer fetches detail with nearby context & duplicates
    - Mumbai officer assigns report (under_review)
    - Mumbai officer verifies report (verified)
    - Mumbai officer marks resolved (resolved)
    - Mumbai officer reopens report (under_review with reopened_count incremented)
    """
    token_citizen = get_token(client, "citizen@example.com", "Citizen@123456")
    token_mumbai = get_token(client, "officer_mumbai@disastermgmt.gov", "Officer@123456")
    token_pune = get_token(client, "officer_pune@disastermgmt.gov", "Officer@123456")

    headers_citizen = {"Authorization": f"Bearer {token_citizen}"}
    headers_mumbai = {"Authorization": f"Bearer {token_mumbai}"}
    headers_pune = {"Authorization": f"Bearer {token_pune}"}

    # 1. Citizen submits report in Mumbai Suburban (lat=19.1197, lon=72.8468 -> district 2)
    report_data = {
        "type": "flood",
        "description": "Severe road waterlogging near Andheri subway Phase 4 test",
        "latitude": 19.1197,
        "longitude": 72.8468,
    }
    submit_res = client.post("/api/v1/reports", json=report_data, headers=headers_citizen)
    assert submit_res.status_code == 201
    report_id = submit_res.json()["id"]

    # 2. Pune officer attempts to inspect/assign Mumbai report -> 403 Forbidden
    cross_assign = client.post(f"/api/v1/officer/reports/{report_id}/assign", headers=headers_pune)
    assert cross_assign.status_code == 403

    # 3. Mumbai officer inspects detail
    detail_res = client.get(f"/api/v1/officer/reports/{report_id}/detail", headers=headers_mumbai)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["report"]["id"] == report_id
    assert "potential_duplicates" in detail
    assert "observations" in detail

    # 4. Mumbai officer assigns report
    assign_res = client.post(f"/api/v1/officer/reports/{report_id}/assign", headers=headers_mumbai)
    assert assign_res.status_code == 200
    assert assign_res.json()["status"] == "under_review"

    # 5. Mumbai officer verifies report
    verify_res = client.post(
        f"/api/v1/officer/reports/{report_id}/review",
        json={"decision": "verified", "notes": "Confirmed by field unit with photo evidence"},
        headers=headers_mumbai,
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "verified"

    # 6. Mumbai officer marks resolved
    resolve_res = client.post(
        f"/api/v1/officer/reports/{report_id}/review",
        json={"decision": "resolved", "notes": "Water pumped out by municipal pumps"},
        headers=headers_mumbai,
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "resolved"

    # 7. Mumbai officer reopens report
    reopen_res = client.post(
        f"/api/v1/officer/reports/{report_id}/reopen",
        json={"notes": "Water levels rising again after heavy cloudburst"},
        headers=headers_mumbai,
    )
    assert reopen_res.status_code == 200
    reopened = reopen_res.json()
    assert reopened["status"] == "under_review"
    assert reopened["reopened_count"] >= 1


def test_operational_incidents_geojson(client: TestClient):
    """Verifies operational incidents endpoint returns GeoJSON FeatureCollection."""
    token_mumbai = get_token(client, "officer_mumbai@disastermgmt.gov", "Officer@123456")
    headers = {"Authorization": f"Bearer {token_mumbai}"}

    res = client.get("/api/v1/officer/operational-incidents", headers=headers)
    assert res.status_code == 200
    geojson = res.json()
    assert geojson["type"] == "FeatureCollection"
    assert "features" in geojson
    assert isinstance(geojson["features"], list)

    if len(geojson["features"]) > 0:
        first = geojson["features"][0]
        assert first["type"] == "Feature"
        assert "geometry" in first
        assert "properties" in first
        assert "status" in first["properties"]
        assert "type" in first["properties"]
