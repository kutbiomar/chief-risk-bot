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
    assert response.headers.get("x-request-id")


def test_request_id_echoes_client_value() -> None:
    client = TestClient(app)

    response = client.get("/api/health", headers={"X-Request-Id": "test-request-id"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request-id"
