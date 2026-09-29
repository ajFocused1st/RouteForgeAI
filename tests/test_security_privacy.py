from fastapi.testclient import TestClient

from backend.config import Settings
from backend.main import create_app


def test_cors_allows_local_frontend_without_credentials():
    app = create_app(
        Settings(
            cors_origins=["http://localhost:5173"],
            database_url="sqlite:///:memory:",
        )
    )

    with TestClient(app) as client:
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-credentials" not in response.headers
