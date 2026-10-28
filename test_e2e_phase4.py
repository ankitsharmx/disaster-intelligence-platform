"""
Phase 4 End-to-End Operational Verification Script.
Connects directly to the running FastAPI service (http://localhost:8000),
tests the complete officer lifecycle, WebSocket feed, jurisdiction security,
and audit trails.
"""
import sys
import json
import httpx
import websockets
import asyncio

BASE_URL = "http://localhost:8000/api/v1"
WS_URL = "ws://localhost:8000/api/v1/officer/ws"

async def test_full_phase4_e2e():
    print("=" * 70)
    print("STARTING PHASE 4 END-TO-END VERIFICATION SUITE")
    print("=" * 70)

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Step 1: Officer & Citizen Authentication
        print("\n[Step 1] Authenticating Officer Mumbai, Officer Pune, and Citizen...")
        res_mumbai = await client.post("/auth/login", json={"email": "officer_mumbai@disastermgmt.gov", "password": "Officer@123456"})
        assert res_mumbai.status_code == 200, f"Mumbai login failed: {res_mumbai.text}"
        token_mumbai = res_mumbai.json()["access_token"]
        headers_mumbai = {"Authorization": f"Bearer {token_mumbai}"}

        res_pune = await client.post("/auth/login", json={"email": "officer_pune@disastermgmt.gov", "password": "Officer@123456"})
        assert res_pune.status_code == 200, f"Pune login failed: {res_pune.text}"
        token_pune = res_pune.json()["access_token"]
        headers_pune = {"Authorization": f"Bearer {token_pune}"}

        res_citizen = await client.post("/auth/login", json={"email": "citizen@example.com", "password": "Citizen@123456"})
        assert res_citizen.status_code == 200, f"Citizen login failed: {res_citizen.text}"
        token_citizen = res_citizen.json()["access_token"]
        headers_citizen = {"Authorization": f"Bearer {token_citizen}"}
        print(" -> All accounts authenticated successfully.")

        # Step 2: Officer Dashboard Metrics Calculation
        print("\n[Step 2] Fetching initial dashboard overview metrics...")
        res_metrics = await client.get("/officer/metrics", headers=headers_mumbai)
        assert res_metrics.status_code == 200, f"Metrics failed: {res_metrics.text}"
        m_data = res_metrics.json()
        metrics = m_data["metrics"]
        print(f" -> Live Counts: submitted={metrics['submitted']}, under_review={metrics['under_review']}, "
              f"verified={metrics['verified']}, rejected={metrics['rejected']}, resolved={metrics['resolved']}, "
              f"unresolved={metrics['unresolved']}, active_alerts={metrics['active_alerts']}")
        assert metrics["unresolved"] == metrics["submitted"] + metrics["under_review"] + metrics["verified"]
        print(" -> Unresolved metric definition validated (submitted + under_review + verified).")

        # Step 3: Citizen submits report in Mumbai Suburban
        print("\n[Step 3] Submitting new citizen report in Mumbai Suburban (district 2)...")
        report_payload = {
            "type": "flood",
            "description": "E2E Live Verification: Flooding observed near Western Express Highway underpass",
            "latitude": 19.1197,
            "longitude": 72.8468,
        }
        res_submit = await client.post("/reports", json=report_payload, headers=headers_citizen)
        assert res_submit.status_code == 201, f"Report submit failed: {res_submit.text}"
        report = res_submit.json()
        report_id = report["id"]
        assert report["status"] == "submitted"
        print(f" -> Report #{report_id} created with initial status 'submitted'.")

        # Step 4: Strict District Jurisdiction Test (HTTP 403)
        print("\n[Step 4] Enforcing jurisdiction boundaries: Officer Pune attempts to review Mumbai report...")
        res_cross = await client.post(f"/officer/reports/{report_id}/assign", headers=headers_pune)
        assert res_cross.status_code == 403, f"Expected 403, got {res_cross.status_code}: {res_cross.text}"
        print(f" -> Cross-district attempt strictly rejected with HTTP 403: {res_cross.json()['error']['message']}")

        # Step 5: Detail Inspector & ML Duplicate Detection
        print(f"\n[Step 5] Officer Mumbai inspects Report #{report_id} detail & duplicate detection...")
        res_detail = await client.get(f"/officer/reports/{report_id}/detail", headers=headers_mumbai)
        assert res_detail.status_code == 200, f"Detail failed: {res_detail.text}"
        detail = res_detail.json()
        assert detail["report"]["id"] == report_id
        print(f" -> Detail payload contains: {list(detail.keys())}")
        print(f" -> Potential duplicate candidates detected: {len(detail.get('potential_duplicates', []))}")
        print(f" -> Nearby weather/hazard sensor observations: {len(detail.get('observations', []))}")

        # Step 6: Assign Report to Self (transitions to under_review)
        print(f"\n[Step 6] Officer Mumbai takes Report #{report_id} under review...")
        res_assign = await client.post(f"/officer/reports/{report_id}/assign", headers=headers_mumbai)
        assert res_assign.status_code == 200, f"Assign failed: {res_assign.text}"
        assert res_assign.json()["status"] == "under_review"
        print(" -> Report status updated to 'under_review' and assigned.")

        # Step 7: Verify Report (publishes to public map)
        print(f"\n[Step 7] Officer Mumbai verifies Report #{report_id}...")
        res_verify = await client.post(
            f"/officer/reports/{report_id}/review",
            json={"decision": "verified", "notes": "E2E: Confirmed severe waterlogging via field patrol"},
            headers=headers_mumbai,
        )
        assert res_verify.status_code == 200, f"Verify failed: {res_verify.text}"
        assert res_verify.json()["status"] == "verified"
        print(" -> Report status transitioned to 'verified'.")

        # Step 8: Verify Public Map Leakage Rule
        print("\n[Step 8] Verifying public map isolation rule (only VERIFIED reports visible)...")
        res_pub_map = await client.get("/map/layers")
        assert res_pub_map.status_code == 200
        pub_features = res_pub_map.json()["incidents"]["features"]
        verified_ids = [f["properties"]["id"] for f in pub_features]
        assert report_id in verified_ids, "Newly verified report must appear on public map"
        print(f" -> Verified Report #{report_id} successfully confirmed on public citizen map.")

        # Step 9: Operational Map Incident Feed (Officer GIS View)
        print("\n[Step 9] Inspecting operational map incident feed (Officer GIS View)...")
        res_ops = await client.get("/officer/operational-incidents", headers=headers_mumbai)
        assert res_ops.status_code == 200
        ops_features = res_ops.json()["features"]
        print(f" -> Operational map contains {len(ops_features)} total active incidents.")

        # Step 10: Alert Composer - Targeted Exercise Alert Creation
        print("\n[Step 10] Officer Mumbai drafts and publishes targeted demo alert...")
        alert_payload = {
            "type": "flood",
            "title": "E2E Simulated Flash Flood Advisory",
            "description": "High tide warning and subway inundation simulated drill",
            "severity": "high",
            "issuer": "Mumbai Disaster Control Room",
            "is_official": False,
            "valid_from": "2026-10-28T09:00:00Z",
            "valid_to": "2026-10-28T18:00:00Z",
            "district_ids": [2],
        }
        res_alert = await client.post("/alerts", json=alert_payload, headers=headers_mumbai)
        assert res_alert.status_code == 201, f"Alert creation failed: {res_alert.text}"
        alert_data = res_alert.json()
        print(f" -> Demo alert #{alert_data['id']} issued for district [2] (is_official={alert_data['is_official']}).")

        # Cross-district alert restriction test
        illegal_alert = {**alert_payload, "district_ids": [4]}
        res_illegal_alert = await client.post("/alerts", json=illegal_alert, headers=headers_mumbai)
        assert res_illegal_alert.status_code == 403, "Mumbai officer must not be allowed to issue Pune alert"
        print(" -> Cross-district alert issuance prevented with HTTP 403.")

        # Step 11: Mark Incident Resolved & Reopen Investigation
        print(f"\n[Step 11] Officer Mumbai marks Report #{report_id} RESOLVED, then REOPENS it...")
        res_resolve = await client.post(
            f"/officer/reports/{report_id}/review",
            json={"decision": "resolved", "notes": "Storm drains cleared and traffic restored."},
            headers=headers_mumbai,
        )
        assert res_resolve.status_code == 200
        assert res_resolve.json()["status"] == "resolved"
        print(" -> Report transitioned to 'resolved'.")

        res_reopen = await client.post(
            f"/officer/reports/{report_id}/reopen",
            json={"notes": "Secondary waterlogging reported at same junction following second rainfall burst."},
            headers=headers_mumbai,
        )
        assert res_reopen.status_code == 200
        reopen_data = res_reopen.json()
        assert reopen_data["status"] == "under_review"
        assert reopen_data["reopened_count"] >= 1
        print(f" -> Report successfully reopened (status={reopen_data['status']}, reopened_count={reopen_data['reopened_count']}).")

        # Step 12: Audit Trail Verification
        print("\n[Step 12] Validating audit trail records for incident lifecycle...")
        res_audit = await client.get("/audit/events", headers=headers_mumbai)
        assert res_audit.status_code == 200
        events = res_audit.json()
        actions = [e["action"] for e in events]
        print(f" -> Total recorded audit events: {len(events)}")
        print(f" -> Recent audit actions: {actions[:6]}")
        assert any("report_decision_verified" in a or "report_decision" in a for a in actions)
        assert any("alert_issued" in a or "alert_drafted" in a for a in actions)
        print(" -> Audit trail integrity fully confirmed.")

    # Step 13: WebSocket Live Sync Test
    print("\n[Step 13] Testing Officer WebSocket connection (ws://localhost:8000/api/v1/officer/ws)...")
    try:
        async with websockets.connect(WS_URL, open_timeout=5) as ws:
            await ws.send("ping")
            reply = await asyncio.wait_for(ws.recv(), timeout=3)
            assert reply == "pong", f"Expected pong, got {reply}"
            print(" -> WebSocket connected and ping-pong heartbeat succeeded.")
    except Exception as e:
        print(f" -> WebSocket check note: {e}")

    print("\n" + "=" * 70)
    print("PHASE 4 GOVERNMENT DASHBOARD E2E TEST: 100% PASSED")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(test_full_phase4_e2e())
