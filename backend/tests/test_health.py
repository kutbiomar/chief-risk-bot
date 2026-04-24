from fastapi.testclient import TestClient

from backend.main import app


def test_healthcheck_returns_200() -> None:
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded", "fail"}
    assert body["environment"]
    assert body["checked_at"]
    assert "components" in body
    assert "database" in body["components"]
    assert body["components"]["database"]["status"] in {"ok", "degraded", "fail"}
    assert "metrics" in body
    assert "requests_total" in body["metrics"]
