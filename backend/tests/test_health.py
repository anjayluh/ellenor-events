from fastapi.testclient import TestClient

from app.main import app


def test_health_check():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_check_exposes_status_without_secret_values():
    client = TestClient(app)
    response = client.get("/health/readiness")
    assert response.status_code in {200, 503}
    payload = response.json()
    assert payload["service"] == "eecs-api"
    assert "database_configured" in payload
    assert "database_connected" in payload
    assert "supabase_auth_configured" in payload
    assert "access_token" not in payload
    assert "secret" not in payload
