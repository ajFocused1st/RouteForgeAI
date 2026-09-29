from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.api.routes import get_routing_provider
from backend.config import Settings
from backend.database.session import (
    create_database_engine,
    create_session_factory,
    get_db_session,
    initialize_database,
)
from backend.main import create_app
from backend.schemas.routing import Coordinate, DistanceMatrix, RouteGeometry, RouteLeg, TravelTimeMatrix


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


@pytest.fixture
def client(tmp_path):
    database_url = sqlite_url(tmp_path / "route_api.db")
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


def vehicle_payload() -> dict:
    return {
        "name": "Cargo Van 1",
        "max_payload_lbs": 3400,
        "active": True,
    }


def stop_payload(name: str, latitude: float) -> dict:
    return {
        "name": name,
        "address": "123 Dispatch Way, Tampa, FL",
        "normalized_address": "123 Dispatch Way, Tampa, FL 33602",
        "latitude": latitude,
        "longitude": -82.4572,
        "stop_type": "delivery",
        "quantity": 1,
        "weight_lbs": 100,
        "service_minutes": 15,
        "priority": 1,
        "address_status": "confirmed",
        "active": True,
    }


def create_route_dependencies(client: TestClient) -> dict:
    depot = client.post("/api/depots", json=depot_payload()).json()["data"]
    vehicle = client.post("/api/vehicles", json=vehicle_payload()).json()["data"]
    first_stop = client.post(
        "/api/stops",
        json=stop_payload("First Stop", 27.9506),
    ).json()["data"]
    second_stop = client.post(
        "/api/stops",
        json=stop_payload("Second Stop", 27.9606),
    ).json()["data"]
    return {
        "depot": depot,
        "vehicle": vehicle,
        "stops": [first_stop, second_stop],
    }


def route_payload(client: TestClient) -> dict:
    dependencies = create_route_dependencies(client)
    return {
        "name": "Morning Route",
        "depot_id": dependencies["depot"]["id"],
        "vehicle_id": dependencies["vehicle"]["id"],
        "stop_ids": [stop["id"] for stop in dependencies["stops"]],
        "active": True,
    }


def create_route(client: TestClient) -> dict:
    response = client.post("/api/routes", json=route_payload(client))
    assert response.status_code == 201
    return response.json()["data"]


class DeterministicRoutingProvider:
    provider_name = "test-routing"

    def __init__(self):
        self.geometry_requests = 0
        self.leg_requests = 0

    def travel_time_matrix(self, locations: list[Coordinate]) -> TravelTimeMatrix:
        return TravelTimeMatrix(
            durations_minutes=[
                [0, 10, 2],
                [10, 0, 2],
                [2, 2, 0],
            ]
        )

    def distance_matrix(self, locations: list[Coordinate]) -> DistanceMatrix:
        return DistanceMatrix(
            distances_miles=[
                [0, 10, 2],
                [10, 0, 2],
                [2, 2, 0],
            ]
        )

    def route_geometry(self, locations: list[Coordinate]) -> RouteGeometry:
        self.geometry_requests += 1
        return RouteGeometry(coordinates=locations)

    def route_legs(self, locations: list[Coordinate]) -> list[RouteLeg]:
        self.leg_requests += 1
        return [
            RouteLeg(
                start=locations[index],
                end=locations[index + 1],
                distance_miles=2,
                travel_duration_minutes=2,
                geometry=RouteGeometry(
                    coordinates=[locations[index], locations[index + 1]]
                ),
            )
            for index in range(len(locations) - 1)
        ]


class AlternateRoutingProvider(DeterministicRoutingProvider):
    provider_name = "alternate-test-routing"

    def travel_time_matrix(self, locations: list[Coordinate]) -> TravelTimeMatrix:
        return TravelTimeMatrix(
            durations_minutes=[
                [0, 1, 10],
                [1, 0, 1],
                [10, 1, 0],
            ]
        )

    def distance_matrix(self, locations: list[Coordinate]) -> DistanceMatrix:
        return DistanceMatrix(
            distances_miles=[
                [0, 3, 12],
                [3, 0, 3],
                [12, 3, 0],
            ]
        )

    def route_legs(self, locations: list[Coordinate]) -> list[RouteLeg]:
        self.leg_requests += 1
        return [
            RouteLeg(
                start=locations[index],
                end=locations[index + 1],
                distance_miles=3,
                travel_duration_minutes=4,
                geometry=RouteGeometry(
                    coordinates=[locations[index], locations[index + 1]]
                ),
            )
            for index in range(len(locations) - 1)
        ]


def optimize_route_with_provider(
    client: TestClient,
    route_id: int,
    provider: DeterministicRoutingProvider,
):
    client.app.dependency_overrides[get_routing_provider] = lambda: provider
    return client.post(f"/api/routes/{route_id}/optimize")


def test_create_route_assigns_stops_in_order(client):
    data = create_route(client)

    assert data["id"] == 1
    assert data["name"] == "Morning Route"
    assert [stop["stop_order"] for stop in data["stops"]] == [1, 2]
    assert [stop["stop_id"] for stop in data["stops"]] == [1, 2]


def test_list_routes_returns_routes_with_assigned_stops(client):
    create_route(client)

    response = client.get("/api/routes")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert len(body["data"]) == 1
    assert body["data"][0]["name"] == "Morning Route"
    assert len(body["data"][0]["stops"]) == 2


def test_get_route_returns_one_route(client):
    route = create_route(client)

    response = client.get(f"/api/routes/{route['id']}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == route["id"]


def test_update_route_changes_fields_and_replaces_stop_assignments(client):
    route = create_route(client)

    response = client.put(
        f"/api/routes/{route['id']}",
        json={"name": "Updated Route", "stop_ids": [2]},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Updated Route"
    assert [stop["stop_id"] for stop in data["stops"]] == [2]
    assert [stop["stop_order"] for stop in data["stops"]] == [1]


def test_unknown_route_returns_structured_404(client):
    response = client.get("/api/routes/999")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "data": None,
        "error": {
            "code": "http_error",
            "message": "Route not found.",
            "details": None,
        },
    }


def test_create_route_rejects_missing_stop_with_readable_error(client):
    dependencies = create_route_dependencies(client)

    response = client.post(
        "/api/routes",
        json={
            "name": "Bad Route",
            "depot_id": dependencies["depot"]["id"],
            "vehicle_id": dependencies["vehicle"]["id"],
            "stop_ids": [999],
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == "Stop ids not found: [999]."


def test_create_route_rejects_duplicate_stop_ids_with_validation_error(client):
    dependencies = create_route_dependencies(client)
    stop_id = dependencies["stops"][0]["id"]

    response = client.post(
        "/api/routes",
        json={
            "name": "Bad Route",
            "depot_id": dependencies["depot"]["id"],
            "vehicle_id": dependencies["vehicle"]["id"],
            "stop_ids": [stop_id, stop_id],
        },
    )

    body = response.json()
    assert response.status_code == 422
    assert body["ok"] is False
    assert "stop_ids cannot contain duplicates" in body["error"]["details"][0]["msg"]


def test_optimize_route_returns_complete_result_and_route_version(client):
    route = create_route(client)
    provider = DeterministicRoutingProvider()

    response = optimize_route_with_provider(client, route["id"], provider)

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["route_id"] == route["id"]
    assert data["version_number"] == 1
    assert data["solver_status"] == "optimal"
    assert data["optimized_stop_order"] == [2, 1]
    assert [stop["stop_order"] for stop in data["stops"]] == [1, 2]
    assert data["metrics"] == {
        "total_distance_miles": 6.0,
        "total_travel_duration_minutes": 6.0,
        "total_service_duration_minutes": 30,
        "total_route_duration_minutes": 36.0,
        "number_of_stops": 2,
        "payload_lbs": 200.0,
        "remaining_capacity_lbs": 3200.0,
        "pre_pickup_deadhead_miles": 0.0,
        "between_job_repositioning_miles": 0.0,
        "post_delivery_deadhead_miles": 0.0,
        "return_to_depot_deadhead_miles": 2.0,
        "total_unloaded_miles": 2.0,
        "deadhead_percentage": 33.33333333333333,
        "cache_hit": False,
    }
    assert len(data["geometry"]["coordinates"]) == 4
    assert len(data["legs"]) == 3
    assert provider.geometry_requests == 1
    assert provider.leg_requests == 1


def test_optimize_route_preserves_previous_versions(client):
    route = create_route(client)
    provider = DeterministicRoutingProvider()

    first = optimize_route_with_provider(client, route["id"], provider)
    second = optimize_route_with_provider(client, route["id"], provider)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["data"]["version_number"] == 1
    assert second.json()["data"]["version_number"] == 2
    assert first.json()["data"]["route_version_id"] != second.json()["data"]["route_version_id"]

    versions_response = client.get(f"/api/routes/{route['id']}/versions")
    assert versions_response.status_code == 200
    versions = versions_response.json()["data"]
    assert [version["version_number"] for version in versions] == [1, 2]
    assert versions[0]["id"] == first.json()["data"]["route_version_id"]
    assert versions[1]["id"] == second.json()["data"]["route_version_id"]
    assert versions[0]["route_metrics"]["optimized_stop_order"] == [2, 1]
    assert versions[1]["route_metrics"]["optimized_stop_order"] == [2, 1]


def test_get_route_version_returns_one_preserved_version(client):
    route = create_route(client)
    provider = DeterministicRoutingProvider()
    first = optimize_route_with_provider(client, route["id"], provider).json()["data"]
    optimize_route_with_provider(client, route["id"], provider)

    response = client.get(f"/api/routes/{route['id']}/versions/1")

    assert response.status_code == 200
    version = response.json()["data"]
    assert version["id"] == first["route_version_id"]
    assert version["route_id"] == route["id"]
    assert version["version_number"] == 1
    assert version["solver_status"] == "optimal"
    assert version["total_distance_miles"] == 6.0
    assert version["route_metrics"]["return_to_depot_deadhead_miles"] == 2.0
    assert version["route_metrics"]["total_unloaded_miles"] == 2.0
    assert version["route_metrics"]["cache_hit"] is False


def test_unknown_route_version_returns_structured_404(client):
    route = create_route(client)

    response = client.get(f"/api/routes/{route['id']}/versions/999")

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Route version not found."


def test_compare_route_versions_returns_clear_differences(client):
    route = create_route(client)

    first = optimize_route_with_provider(
        client,
        route["id"],
        DeterministicRoutingProvider(),
    )
    client.put("/api/stops/1", json={"weight_lbs": 250})
    second = optimize_route_with_provider(
        client,
        route["id"],
        AlternateRoutingProvider(),
    )

    response = client.get(f"/api/routes/{route['id']}/versions/compare/1/2")

    assert first.status_code == 200
    assert second.status_code == 200
    assert response.status_code == 200
    comparison = response.json()["data"]
    assert comparison["base_version"] == 1
    assert comparison["comparison_version"] == 2
    assert comparison["miles"] == {
        "base": 6.0,
        "comparison": 9.0,
        "difference": 3.0,
    }
    assert comparison["drive_time_minutes"] == {
        "base": 6,
        "comparison": 12,
        "difference": 6,
    }
    assert comparison["route_time_minutes"] == {
        "base": 36,
        "comparison": 42,
        "difference": 6,
    }
    assert comparison["payload_lbs"] == {
        "base": 200.0,
        "comparison": 350.0,
        "difference": 150.0,
    }
    assert comparison["stop_order"]["base"] == [2, 1]
    assert comparison["stop_order"]["comparison"] == [1, 2]
    assert comparison["stop_order"]["changed"] is True
    assert comparison["stop_order"]["added"] == []
    assert comparison["stop_order"]["removed"] == []
    assert comparison["stop_order"]["position_changes"] == [
        {"stop_id": 1, "base_position": 2, "comparison_position": 1},
        {"stop_id": 2, "base_position": 1, "comparison_position": 2},
    ]


def test_optimize_route_rejects_route_without_stops(client):
    dependencies = create_route_dependencies(client)
    route_response = client.post(
        "/api/routes",
        json={
            "name": "Empty Route",
            "depot_id": dependencies["depot"]["id"],
            "vehicle_id": dependencies["vehicle"]["id"],
            "stop_ids": [],
        },
    )
    route = route_response.json()["data"]

    response = optimize_route_with_provider(
        client,
        route["id"],
        DeterministicRoutingProvider(),
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == (
        "Route must have at least one stop before optimization."
    )


def test_optimize_route_rejects_inactive_depot(client):
    route = create_route(client)
    client.put(f"/api/depots/{route['depot_id']}", json={"active": False})

    response = optimize_route_with_provider(
        client,
        route["id"],
        DeterministicRoutingProvider(),
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == (
        "Route depot is missing or inactive."
    )


def test_optimize_route_rejects_inactive_vehicle(client):
    route = create_route(client)
    client.put(f"/api/vehicles/{route['vehicle_id']}", json={"active": False})

    response = optimize_route_with_provider(
        client,
        route["id"],
        DeterministicRoutingProvider(),
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == (
        "Route vehicle is missing or inactive."
    )


def test_optimize_route_rejects_inactive_stop(client):
    route = create_route(client)
    stop_id = route["stops"][0]["stop_id"]
    client.delete(f"/api/stops/{stop_id}")

    response = optimize_route_with_provider(
        client,
        route["id"],
        DeterministicRoutingProvider(),
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == (
        f"Route stop {stop_id} is missing or inactive."
    )


def test_optimize_route_saves_failed_version_when_payload_exceeds_capacity(client):
    route = create_route(client)
    client.put(f"/api/vehicles/{route['vehicle_id']}", json={"max_payload_lbs": 150})

    response = optimize_route_with_provider(
        client,
        route["id"],
        DeterministicRoutingProvider(),
    )

    assert response.status_code == 409
    assert response.json()["error"]["message"] == (
        "Route optimization failed: capacity_exceeded."
    )

    versions_response = client.get(f"/api/routes/{route['id']}/versions")
    assert versions_response.status_code == 200
    versions = versions_response.json()["data"]
    assert len(versions) == 1
    assert versions[0]["solver_status"] == "capacity_exceeded"
    assert versions[0]["route_metrics"]["optimized_stop_order"] == []


def test_optimize_route_returns_clear_error_when_no_feasible_solution(client):
    dependencies = create_route_dependencies(client)
    client.put(
        f"/api/stops/{dependencies['stops'][0]['id']}",
        json={"latest_time": "08:02:00"},
    )
    route_response = client.post(
        "/api/routes",
        json={
            "name": "Impossible Route",
            "depot_id": dependencies["depot"]["id"],
            "vehicle_id": dependencies["vehicle"]["id"],
            "stop_ids": [stop["id"] for stop in dependencies["stops"]],
        },
    )
    route = route_response.json()["data"]

    response = optimize_route_with_provider(
        client,
        route["id"],
        DeterministicRoutingProvider(),
    )

    assert response.status_code == 409
    assert response.json()["error"]["message"] == (
        "Route has no feasible optimization solution."
    )
