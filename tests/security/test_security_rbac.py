"""
Multi-Hazard Disaster Intelligence Platform - Master Testing Suite
Category 04 & 11: Authentication, RBAC, Security & Data Protection (AUTH-01..09, SEC-01..12)
"""

import sys
from pathlib import Path
from datetime import timedelta
import pytest
from httpx import AsyncClient, ASGITransport

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT / "backend"))

from app.main import app
from app.core.security import create_access_token
from app.db.session import AsyncSessionLocal
from app.models.report import CitizenReport, ReportStatus

@pytest.mark.asyncio
async def test_auth_01_citizen_forbidden_from_verification():
    """AUTH-01: Citizen role calling officer verification route receives HTTP 403 Forbidden."""
    citizen_token = create_access_token(subject=5)  # Citizen user ID 5
    headers = {"Authorization": f"Bearer {citizen_token}"}
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/officer/reports/1/review", json={"decision": "verified", "notes": "Hacked"}, headers=headers)
        assert resp.status_code in [401, 403], f"Expected 403 Forbidden, got {resp.status_code}"

@pytest.mark.asyncio
async def test_auth_02_district_officer_cross_district_restriction():
    """AUTH-02: Officer assigned to District 2 cannot inspect details of District 4 reports."""
    # Seed a report strictly in District 4 (Pune)
    async with AsyncSessionLocal() as session:
        async with session.begin():
            rep = CitizenReport(
                id=94,
                district_id=4,
                type="flood",
                description="Mutha river overflowing near Deccan gymkhana",
                latitude=18.5204,
                longitude=73.8567,
                status=ReportStatus.SUBMITTED,
            )
            session.add(rep)

    officer_mumbai_token = create_access_token(subject=3)  # Officer Mumbai Suburban (District 2)
    headers = {"Authorization": f"Bearer {officer_mumbai_token}"}
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/officer/reports/94/detail", headers=headers)
        assert resp.status_code == 403, f"Cross-district access should be 403, got {resp.status_code}"

@pytest.mark.asyncio
async def test_auth_04_prevent_role_escalation():
    """AUTH-04: Citizen sending role='system_admin' in registration payload cannot self-escalate."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/auth/register", json={
            "email": "attacker@evil.com",
            "password": "Password@123456",
            "full_name": "Attacker",
            "role": "system_admin"  # Attempt privilege escalation
        })
        if resp.status_code == 201:
            data = resp.json()
            assert data.get("role") == "citizen", "Privilege escalation vulnerability: user became system_admin!"

@pytest.mark.asyncio
async def test_auth_07_expired_token_rejected():
    """AUTH-07: Expired JWT token is rejected with HTTP 401."""
    expired_token = create_access_token(
        subject=5,
        expires_delta=timedelta(seconds=-60)  # Expired 1 minute ago
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/auth/me", headers=headers)
        assert resp.status_code == 401

@pytest.mark.asyncio
async def test_sec_01_sql_injection_immunity():
    """SEC-01: SQL injection strings in parameters are safely handled by SQLAlchemy parameterization."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Attempt SQLi in query parameter
        resp = await ac.get("/api/v1/overview?district_id=1%20OR%201=1")
        assert resp.status_code in [422, 404, 400]

@pytest.mark.asyncio
async def test_sec_02_xss_mitigation():
    """SEC-02: Stored script tags in description do not cause server execution and are safely preserved as text."""
    xss_payload = "<script>alert('pwned')</script>"
    citizen_token = create_access_token(subject=5)
    headers = {"Authorization": f"Bearer {citizen_token}"}
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/reports", json={
            "type": "flood",
            "description": xss_payload,
            "latitude": 19.0760,
            "longitude": 72.8777
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "<script>" in data["description"]

@pytest.mark.asyncio
async def test_sec_06_password_never_exposed_in_api():
    """SEC-06: Passwords or password hashes are never serialized into API responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/v1/auth/login", json={"email": "citizen@example.com", "password": "Citizen@123456"})
        assert resp.status_code == 200
        content = resp.text
        assert "hashed_password" not in content
        assert "password" not in resp.json()

@pytest.mark.asyncio
async def test_sec_12_zero_unverified_reports_on_public_map():
    """SEC-12 (Original Success Criterion #7): Exactly ZERO unverified reports appear on public map."""
    # Seed one unverified report and one verified report in district 2
    async with AsyncSessionLocal() as session:
        async with session.begin():
            r_unverified = CitizenReport(
                id=901,
                district_id=2,
                type="flood",
                description="Unverified citizen rumor",
                latitude=19.12,
                longitude=72.88,
                status=ReportStatus.SUBMITTED,
            )
            r_verified = CitizenReport(
                id=902,
                district_id=2,
                type="flood",
                description="Confirmed flood inundation",
                latitude=19.13,
                longitude=72.89,
                status=ReportStatus.VERIFIED,
            )
            session.add_all([r_unverified, r_verified])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/map/layers?district_id=2")
        assert resp.status_code == 200
        data = resp.json()
        incidents = data.get("incidents", {}).get("features", [])
        
        incident_ids = [feat["id"] for feat in incidents]
        # Zero unverified reports tolerance
        assert 901 not in incident_ids, "CRITICAL SECURITY BREACH: Unverified report leaked to public map!"
        for feat in incidents:
            assert feat["properties"]["status"] == "verified", f"Non-verified report leaked: {feat}"
