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
    database_url = sqlite_url(tmp_path / "stop_api.db")
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


def stop_payload() -> dict:
    return {
        "name": "Dock Pickup",
        "address": "123 Dispatch Way, Tampa, FL",
        "normalized_address": "123 Dispatch Way, Tampa, FL 33602",
        "latitude": 27.9506,
        "longitude": -82.4572,
        "stop_type": "pickup",
        "quantity": 2,
        "weight_lbs": 125.5,
        "service_minutes": 15,
        "priority": 1,
        "earliest_time": "08:00:00",
        "latest_time": "12:00:00",
        "special_instructions": "Use loading dock.",
        "address_status": "confirmed",
        "active": True,
    }


def create_stop(client: TestClient) -> dict:
    response = client.post("/api/stops", json=stop_payload())
    assert response.status_code == 201
    return response.json()["data"]


def test_create_stop_returns_structured_response(client):
    data = create_stop(client)

    assert data["id"] == 1
    assert data["name"] == "Dock Pickup"
    assert data["stop_type"] == "pickup"
    assert data["active"] is True


def test_list_stops_returns_created_stops(client):
    create_stop(client)

    response = client.get("/api/stops")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["name"] == "Dock Pickup"


def test_get_stop_returns_one_stop(client):
    stop = create_stop(client)

    response = client.get(f"/api/stops/{stop['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == stop["id"]


def test_update_stop_changes_only_requested_fields(client):
    stop = create_stop(client)

    response = client.put(
        f"/api/stops/{stop['id']}",
        json={"name": "Updated Stop", "priority": 3},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Stop"
    assert data["priority"] == 3
    assert data["address"] == "123 Dispatch Way, Tampa, FL"


def test_delete_stop_deactivates_stop(client):
    stop = create_stop(client)

    response = client.delete(f"/api/stops/{stop['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["active"] is False

    get_response = client.get(f"/api/stops/{stop['id']}")
    assert get_response.json()["data"]["active"] is False


def test_unknown_stop_returns_structured_404(client):
    response = client.get("/api/stops/999")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "data": None,
        "error": {
            "code": "http_error",
            "message": "Stop not found.",
            "details": None,
        },
    }


def test_create_stop_rejects_invalid_stop_type_with_readable_error(client):
    payload = stop_payload()
    payload["stop_type"] = "return"

    response = client.post("/api/stops", json=payload)

    body = response.json()
    assert response.status_code == 422
    assert body["ok"] is False
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["message"] == "Request validation failed."
    assert body["error"]["details"][0]["loc"] == ["body", "stop_type"]
    assert "pickup" in body["error"]["details"][0]["msg"]


def test_create_stop_rejects_invalid_time_window_with_readable_error(client):
    payload = stop_payload()
    payload["earliest_time"] = "13:00:00"
    payload["latest_time"] = "12:00:00"

    response = client.post("/api/stops", json=payload)

    body = response.json()
    assert response.status_code == 422
    assert body["ok"] is False
    assert body["error"]["code"] == "validation_error"
    assert "earliest_time cannot be after latest_time" in body["error"]["details"][0][
        "msg"
    ]
