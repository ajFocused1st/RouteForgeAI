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
    database_url = sqlite_url(tmp_path / "vehicle_api.db")
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


def vehicle_payload() -> dict:
    return {
        "name": "Cargo Van 1",
        "max_payload_lbs": 3400,
        "max_volume_cubic_ft": 420,
        "max_route_miles": 180,
        "max_route_minutes": 480,
        "active": True,
    }


def create_vehicle(client: TestClient) -> dict:
    response = client.post("/api/vehicles", json=vehicle_payload())
    assert response.status_code == 201
    return response.json()["data"]


def test_create_vehicle_returns_structured_response(client):
    data = create_vehicle(client)

    assert data["id"] == 1
    assert data["name"] == "Cargo Van 1"
    assert data["max_payload_lbs"] == 3400
    assert data["active"] is True


def test_list_vehicles_returns_created_vehicles(client):
    create_vehicle(client)

    response = client.get("/api/vehicles")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["name"] == "Cargo Van 1"


def test_get_vehicle_returns_one_vehicle(client):
    vehicle = create_vehicle(client)

    response = client.get(f"/api/vehicles/{vehicle['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == vehicle["id"]


def test_update_vehicle_changes_only_requested_fields(client):
    vehicle = create_vehicle(client)

    response = client.put(
        f"/api/vehicles/{vehicle['id']}",
        json={"name": "Updated Van", "max_route_miles": 200},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Van"
    assert data["max_route_miles"] == 200
    assert data["max_payload_lbs"] == 3400


def test_delete_vehicle_deactivates_vehicle(client):
    vehicle = create_vehicle(client)

    response = client.delete(f"/api/vehicles/{vehicle['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["active"] is False

    get_response = client.get(f"/api/vehicles/{vehicle['id']}")
    assert get_response.json()["data"]["active"] is False


def test_unknown_vehicle_returns_structured_404(client):
    response = client.get("/api/vehicles/999")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "data": None,
        "error": {
            "code": "http_error",
            "message": "Vehicle not found.",
            "details": None,
        },
    }


def test_create_vehicle_rejects_negative_capacity(client):
    payload = vehicle_payload()
    payload["max_payload_lbs"] = -1

    response = client.post("/api/vehicles", json=payload)

    assert response.status_code == 422
    assert response.json()["ok"] is False
