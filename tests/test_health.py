from fastapi.testclient import TestClient

from backend.main import create_app


def test_health_endpoint_returns_structured_response():
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "service": "RouteForge AI",
            "version": "0.1.0",
            "environment": "local",
        },
        "error": None,
    }
