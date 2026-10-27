from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "version" in data


def test_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_resolve_district_api(client: TestClient):
    # Inside Mumbai City
    payload = {"latitude": 18.9500, "longitude": 72.8300}
    response = client.post("/api/v1/locations/resolve-district", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["found"] is True
    assert data["district"]["name"] == "Mumbai City"

    # Outside boundaries
    payload_out = {"latitude": 28.6139, "longitude": 77.2090}
    response_out = client.post("/api/v1/locations/resolve-district", json=payload_out)
    assert response_out.status_code == 200
    data_out = response_out.json()
    assert data_out["found"] is False


def test_replay_status_api(client: TestClient):
    response = client.get("/api/v1/replay/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "speed" in data
