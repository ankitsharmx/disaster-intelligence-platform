import pytest
import io
from fastapi.testclient import TestClient


def get_token(client: TestClient, email: str, password: str) -> str:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Failed to login {email}: {res.text}"
    return res.json()["access_token"]


def test_auth_four_roles(client: TestClient):
    """Verifies authentication for all 4 documented roles."""
    roles = [
        ("admin@disastermgmt.gov", "Admin@123456", "system_admin"),
        ("state_admin_mh@disastermgmt.gov", "StateAdmin@123456", "state_admin"),
        ("officer_mumbai@disastermgmt.gov", "Officer@123456", "district_officer"),
        ("officer_pune@disastermgmt.gov", "Officer@123456", "district_officer"),
        ("citizen@example.com", "Citizen@123456", "citizen"),
    ]
    for email, pwd, expected_role in roles:
        res = client.post("/api/v1/auth/login", json={"email": email, "password": pwd})
        assert res.status_code == 200
        data = res.json()
        assert data["role"] == expected_role
        assert "access_token" in data


def test_public_registration_restricts_to_citizen(client: TestClient):
    """Verifies that public sign-up cannot self-elevate to officer or admin."""
    payload = {
        "email": "new_citizen@example.com",
        "full_name": "Test Citizen",
        "password": "Password@123",
        "role": "system_admin",  # Attacker attempts to register as system_admin
    }
    res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 201
    user = res.json()
    assert user["role"] == "citizen"  # Server forced role to citizen


def test_location_and_overview_apis(client: TestClient):
    """Verifies Location and Situational Awareness Overview APIs."""
    # 1. States endpoint
    states_res = client.get("/api/v1/locations/states")
    assert states_res.status_code == 200
    states = states_res.json()
    assert len(states) >= 1
    assert states[0]["code"] == "MH"

    # 2. Districts endpoint
    districts_res = client.get("/api/v1/locations/districts")
    assert districts_res.status_code == 200
    districts = districts_res.json()
    assert len(districts) >= 3

    # 3. GET /locations/resolve
    resolve_res = client.get("/api/v1/locations/resolve?latitude=19.12&longitude=72.88")
    assert resolve_res.status_code == 200
    assert resolve_res.json()["found"] is True
    assert resolve_res.json()["district"]["name"] == "Mumbai Suburban"

    # 4. GET /overview?district_id=2
    overview_res = client.get("/api/v1/overview?district_id=2")
    assert overview_res.status_code == 200
    overview = overview_res.json()
    assert overview["district"]["name"] == "Mumbai Suburban"
    assert "overall_status" in overview
    assert "observations" in overview
    assert "applicable_alerts" in overview
    assert "risk_estimates" in overview
    assert "safety_guidance" in overview
    assert "data_sources_status" in overview


def test_alert_management_and_district_jurisdiction(client: TestClient):
    """
    Verifies alert lifecycle and strict district boundary enforcement:
    - Officer Mumbai CANNOT issue alert for Pune (district 4) -> 403 Forbidden
    - Officer Mumbai CAN issue alert for Mumbai Suburban (district 2) -> 201 Created
    """
    token_mumbai = get_token(client, "officer_mumbai@disastermgmt.gov", "Officer@123456")
    token_admin = get_token(client, "admin@disastermgmt.gov", "Admin@123456")

    # 1. Unauthorized attempt: Officer Mumbai attempts to issue alert affecting Pune
    illegal_alert = {
        "type": "flood",
        "title": "Unauthorized Pune Flood Alert",
        "description": "Cross-district test",
        "severity": "high",
        "issuer": "Officer Mumbai",
        "valid_from": "2026-10-27T10:00:00Z",
        "valid_to": "2026-10-27T18:00:00Z",
        "district_ids": [4],  # Pune
    }
    forbidden_res = client.post(
        "/api/v1/alerts",
        json=illegal_alert,
        headers={"Authorization": f"Bearer {token_mumbai}"},
    )
    assert forbidden_res.status_code == 403
    assert "Access Denied" in forbidden_res.json()["error"]["message"]

    # 2. Authorized alert: Officer Mumbai drafts alert for their assigned district 2
    valid_alert = {
        "type": "flood",
        "title": "Monsoon Flash Flood Warning",
        "description": "Heavy rainfall alert for Mumbai Suburban low-lying sectors",
        "severity": "high",
        "issuer": "Disaster Response Cell Mumbai",
        "valid_from": "2026-10-27T10:00:00Z",
        "valid_to": "2026-10-27T22:00:00Z",
        "district_ids": [2],
    }
    draft_res = client.post(
        "/api/v1/alerts/draft",
        json=valid_alert,
        headers={"Authorization": f"Bearer {token_mumbai}"},
    )
    assert draft_res.status_code == 201
    alert_data = draft_res.json()
    alert_id = alert_data["id"]
    assert alert_data["status"] == "draft"

    # 3. Issue draft alert
    issue_res = client.post(
        f"/api/v1/alerts/{alert_id}/issue",
        headers={"Authorization": f"Bearer {token_mumbai}"},
    )
    assert issue_res.status_code == 200
    assert issue_res.json()["status"] == "active"

    # 4. Cancel alert
    cancel_res = client.post(
        f"/api/v1/alerts/{alert_id}/cancel",
        json={"reason": "Water levels stabilized"},
        headers={"Authorization": f"Bearer {token_mumbai}"},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"


def test_incident_reporting_upload_and_review_lifecycle(client: TestClient):
    """
    Comprehensive test of the full reporting & verification lifecycle:
    1. Citizen submits report (initial status: SUBMITTED).
    2. Citizen uploads media proof (file size & MIME validation).
    3. Citizen checks 'my reports'.
    4. Publication rule: unverified report is NOT in public feed.
    5. Officer review queue: only officer in correct district can see & review.
    6. Officer verifies report: now published in public feed and map.
    7. Defined reopening workflow: resolved report reopened back to under_review.
    """
    token_citizen = get_token(client, "citizen@example.com", "Citizen@123456")
    token_mumbai = get_token(client, "officer_mumbai@disastermgmt.gov", "Officer@123456")
    token_pune = get_token(client, "officer_pune@disastermgmt.gov", "Officer@123456")

    # 1. Citizen submits report in Mumbai Suburban (lat 19.12, lon 72.88)
    report_payload = {
        "type": "flood",
        "description": "Kurla West road flooded up to 3 feet near station subway.",
        "latitude": 19.1200,
        "longitude": 72.8800,
    }
    submit_res = client.post(
        "/api/v1/reports",
        json=report_payload,
        headers={"Authorization": f"Bearer {token_citizen}"},
    )
    assert submit_res.status_code == 201
    report = submit_res.json()
    report_id = report["id"]
    assert report["status"] == "submitted"
    assert report["district_id"] == 2

    # 2. Upload file validation
    # 2a. Reject disallowed file type
    fake_exe = io.BytesIO(b"binary content")
    bad_upload = client.post(
        f"/api/v1/reports/{report_id}/media",
        files={"file": ("malicious.exe", fake_exe, "application/x-dosexec")},
        headers={"Authorization": f"Bearer {token_citizen}"},
    )
    assert bad_upload.status_code == 400
    assert "not permitted" in bad_upload.json()["error"]["message"]

    # 2b. Valid image upload
    fake_png = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"A" * 100)
    good_upload = client.post(
        f"/api/v1/reports/{report_id}/media",
        files={"file": ("flood_photo.png", fake_png, "image/png")},
        headers={"Authorization": f"Bearer {token_citizen}"},
    )
    assert good_upload.status_code == 201
    assert good_upload.json()["content_type"] == "image/png"

    # 3. Citizen checks own reports
    my_reports = client.get("/api/v1/reports/my", headers={"Authorization": f"Bearer {token_citizen}"})
    assert my_reports.status_code == 200
    assert any(r["id"] == report_id for r in my_reports.json())

    # 4. CRITICAL PUBLICATION RULE: Public feed must NOT contain unverified report
    public_res = client.get("/api/v1/reports")
    assert public_res.status_code == 200
    assert not any(r["id"] == report_id for r in public_res.json())

    # Map layers must also NOT contain unverified report
    map_res = client.get("/api/v1/map/layers")
    assert map_res.status_code == 200
    incidents = map_res.json()["incidents"]["features"]
    assert not any(f["properties"]["id"] == report_id for f in incidents)

    # 5. Officer queue district enforcement
    # Officer Pune (district 4) should NOT see report in district 2
    pune_queue = client.get("/api/v1/officer/reports", headers={"Authorization": f"Bearer {token_pune}"})
    assert pune_queue.status_code == 200
    assert not any(r["id"] == report_id for r in pune_queue.json())

    # Officer Pune attempting to review district 2 report must get 403 Forbidden
    forbidden_review = client.post(
        f"/api/v1/officer/reports/{report_id}/review",
        json={"decision": "verified", "notes": "Unauthorized Pune officer attempt"},
        headers={"Authorization": f"Bearer {token_pune}"},
    )
    assert forbidden_review.status_code == 403

    # Officer Mumbai (district 2) DOES see report
    mumbai_queue = client.get("/api/v1/officer/reports", headers={"Authorization": f"Bearer {token_mumbai}"})
    assert mumbai_queue.status_code == 200
    assert any(r["id"] == report_id for r in mumbai_queue.json())

    # 6. Officer Mumbai assigns and verifies report
    assign_res = client.post(
        f"/api/v1/officer/reports/{report_id}/assign",
        headers={"Authorization": f"Bearer {token_mumbai}"},
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["status"] == "under_review"

    verify_res = client.post(
        f"/api/v1/officer/reports/{report_id}/review",
        json={"decision": "verified", "notes": "Ground patrol confirmed 3ft flood level at Kurla subway."},
        headers={"Authorization": f"Bearer {token_mumbai}"},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == "verified"

    # Now that it is verified, it MUST appear in the public feed
    public_verified = client.get("/api/v1/reports")
    assert any(r["id"] == report_id for r in public_verified.json())

    # And in public map layers
    map_verified = client.get("/api/v1/map/layers")
    map_incidents = map_verified.json()["incidents"]["features"]
    assert any(f["properties"]["id"] == report_id for f in map_incidents)

    # 7. Defined reopening workflow
    # 7a. Mark resolved first
    resolve_res = client.post(
        f"/api/v1/officer/reports/{report_id}/review",
        json={"decision": "resolved", "notes": "Pumps deployed, water drained."},
        headers={"Authorization": f"Bearer {token_mumbai}"},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "resolved"

    # 7b. Reopen report
    reopen_res = client.post(
        f"/api/v1/officer/reports/{report_id}/reopen",
        json={"notes": "Fresh citizen reports indicate water backflow; reopening case."},
        headers={"Authorization": f"Bearer {token_mumbai}"},
    )
    assert reopen_res.status_code == 200
    reopened_data = reopen_res.json()
    assert reopened_data["status"] == "under_review"
    assert reopened_data["reopened_count"] == 1


def test_audit_log_endpoint(client: TestClient):
    """Verifies that audit trail is accessible only to administrators."""
    token_citizen = get_token(client, "citizen@example.com", "Citizen@123456")
    token_admin = get_token(client, "admin@disastermgmt.gov", "Admin@123456")

    # Citizen cannot access audit logs
    citizen_res = client.get("/api/v1/audit/events", headers={"Authorization": f"Bearer {token_citizen}"})
    assert citizen_res.status_code == 403

    # Admin can access audit logs
    admin_res = client.get("/api/v1/audit/events", headers={"Authorization": f"Bearer {token_admin}"})
    assert admin_res.status_code == 200
    events = admin_res.json()
    assert len(events) > 0
    assert any("report_" in e["action"] or "alert_" in e["action"] for e in events)
