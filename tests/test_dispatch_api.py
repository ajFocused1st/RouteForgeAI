from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.dispatch import get_dispatch_routing_provider
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


class DispatchRoutingProvider:
    provider_name = "dispatch-test-routing"

    def travel_time_matrix(self, locations: list[Coordinate]) -> TravelTimeMatrix:
        return TravelTimeMatrix(durations_minutes=self._matrix(len(locations), 1))

    def distance_matrix(self, locations: list[Coordinate]) -> DistanceMatrix:
        return DistanceMatrix(distances_miles=self._matrix(len(locations), 3))

    def route_geometry(self, locations: list[Coordinate]) -> RouteGeometry:
        return RouteGeometry(coordinates=locations)

    def route_legs(self, locations: list[Coordinate]) -> list[RouteLeg]:
        return [
            RouteLeg(
                start=locations[index],
                end=locations[index + 1],
                distance_miles=2 + index,
                travel_duration_minutes=3 + index,
                geometry=RouteGeometry(
                    coordinates=[locations[index], locations[index + 1]]
                ),
            )
            for index in range(len(locations) - 1)
        ]

    def _matrix(self, size: int, base: float) -> list[list[float]]:
        return [
            [0 if row == column else base + row + column for column in range(size)]
            for row in range(size)
        ]


def test_dispatch_optimize_returns_separate_vehicle_routes(tmp_path):
    database_url = sqlite_url(tmp_path / "dispatch.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))
    app = create_app(Settings(database_url=database_url))

    def override_db_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_dispatch_routing_provider] = (
        lambda: DispatchRoutingProvider()
    )

    with TestClient(app) as client:
        depot = client.post(
            "/api/depots",
            json={
                "name": "Main Depot",
                "address": "123 Dispatch Way, Tampa, FL",
                "latitude": 27.9506,
                "longitude": -82.4572,
                "default_start_time": "08:00:00",
                "active": True,
            },
        ).json()["data"]
        first_vehicle = client.post(
            "/api/vehicles",
            json={"name": "Van 1", "max_payload_lbs": 100, "active": True},
        ).json()["data"]
        second_vehicle = client.post(
            "/api/vehicles",
            json={"name": "Van 2", "max_payload_lbs": 100, "active": True},
        ).json()["data"]
        first_stop = client.post(
            "/api/stops",
            json=stop_payload("First Stop", 27.9506),
        ).json()["data"]
        second_stop = client.post(
            "/api/stops",
            json=stop_payload("Second Stop", 27.9606),
        ).json()["data"]

        response = client.post(
            "/api/dispatch/optimize",
            json={
                "depot_id": depot["id"],
                "vehicle_ids": [first_vehicle["id"], second_vehicle["id"]],
                "stop_ids": [first_stop["id"], second_stop["id"]],
            },
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["solver_status"] == "optimal"
    assert data["depot_id"] == depot["id"]
    assert [route["vehicle_id"] for route in data["routes"]] == [
        first_vehicle["id"],
        second_vehicle["id"],
    ]
    assert sorted(
        stop_id
        for route in data["routes"]
        for stop_id in route["optimized_stop_order"]
    ) == [first_stop["id"], second_stop["id"]]
    assert all(len(route["geometry"]["coordinates"]) == 3 for route in data["routes"])
    assert all(route["payload_lbs"] == 100 for route in data["routes"])

    app.dependency_overrides.clear()


def test_dispatch_optimize_reports_nonoptimal_solver_status(tmp_path):
    database_url = sqlite_url(tmp_path / "dispatch-infeasible.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))
    app = create_app(Settings(database_url=database_url))

    def override_db_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_dispatch_routing_provider] = (
        lambda: DispatchRoutingProvider()
    )

    with TestClient(app) as client:
        depot = client.post(
            "/api/depots",
            json={
                "name": "Main Depot",
                "address": "123 Dispatch Way, Tampa, FL",
                "latitude": 27.9506,
                "longitude": -82.4572,
                "default_start_time": "08:00:00",
                "active": True,
            },
        ).json()["data"]
        vehicle = client.post(
            "/api/vehicles",
            json={"name": "Small Van", "max_payload_lbs": 50, "active": True},
        ).json()["data"]
        stop = client.post(
            "/api/stops",
            json=stop_payload("Heavy Stop", 27.9506),
        ).json()["data"]

        response = client.post(
            "/api/dispatch/optimize",
            json={
                "depot_id": depot["id"],
                "vehicle_ids": [vehicle["id"]],
                "stop_ids": [stop["id"]],
            },
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["solver_status"] == "capacity_exceeded"
    assert data["routes"] == []

    app.dependency_overrides.clear()


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
