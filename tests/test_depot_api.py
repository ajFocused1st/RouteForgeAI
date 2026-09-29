from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.config import Settings
from backend.database.session import (
    create_database_engine,
    create_session_factory,
    get_db_session,
    initialize_database,
)
from backend.main import create_app


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


@pytest.fixture
def client(tmp_path):
    database_url = sqlite_url(tmp_path / "depot_api.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))
    app = create_app(Settings(database_url=database_url))

    def override_db_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def depot_payload() -> dict:
    return {
        "name": "Main Depot",
        "address": "123 Dispatch Way, Tampa, FL",
        "latitude": 27.9506,
        "longitude": -82.4572,
        "default_start_time": "08:00:00",
        "active": True,
    }


def create_depot(client: TestClient) -> dict:
    response = client.post("/api/depots", json=depot_payload())
    assert response.status_code == 201
    return response.json()["data"]


def test_create_depot_returns_structured_response(client):
    data = create_depot(client)

    assert data["id"] == 1
    assert data["name"] == "Main Depot"
    assert data["active"] is True


def test_list_depots_returns_created_depots(client):
    create_depot(client)

    response = client.get("/api/depots")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["name"] == "Main Depot"


def test_get_depot_returns_one_depot(client):
    depot = create_depot(client)

    response = client.get(f"/api/depots/{depot['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == depot["id"]


def test_update_depot_changes_only_requested_fields(client):
    depot = create_depot(client)

    response = client.put(
        f"/api/depots/{depot['id']}",
        json={"name": "Updated Depot", "latitude": 28.0},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Depot"
    assert data["latitude"] == 28.0
    assert data["address"] == "123 Dispatch Way, Tampa, FL"


def test_delete_depot_deactivates_depot(client):
    depot = create_depot(client)

    response = client.delete(f"/api/depots/{depot['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["active"] is False

    get_response = client.get(f"/api/depots/{depot['id']}")
    assert get_response.json()["data"]["active"] is False


def test_unknown_depot_returns_structured_404(client):
    response = client.get("/api/depots/999")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "data": None,
        "error": {
            "code": "http_error",
            "message": "Depot not found.",
            "details": None,
        },
    }


def test_create_depot_rejects_invalid_coordinates(client):
    payload = depot_payload()
    payload["latitude"] = 91

    response = client.post("/api/depots", json=payload)

    assert response.status_code == 422
    assert response.json()["ok"] is False
