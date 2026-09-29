from pathlib import Path

import pytest
from sqlalchemy import inspect, select

from backend.database.session import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from backend.models.depot import Depot
from backend.models.routing_matrix_cache import RoutingMatrixCache
from backend.models.stop import Stop
from backend.schemas.routing import Coordinate, DistanceMatrix, RouteGeometry, RouteLeg, TravelTimeMatrix
from backend.services.routing_matrix import RoutingMatrixService


class CountingRoutingProvider:
    provider_name = "counting-routing"

    def __init__(self):
        self.travel_time_calls = 0
        self.distance_calls = 0

    def travel_time_matrix(self, locations: list[Coordinate]) -> TravelTimeMatrix:
        self.travel_time_calls += 1
        size = len(locations)
        return TravelTimeMatrix(
            durations_minutes=[
                [0 if row == column else 10 for column in range(size)]
                for row in range(size)
            ]
        )

    def distance_matrix(self, locations: list[Coordinate]) -> DistanceMatrix:
        self.distance_calls += 1
        size = len(locations)
        return DistanceMatrix(
            distances_miles=[
                [0 if row == column else 5 for column in range(size)]
                for row in range(size)
            ]
        )

    def route_geometry(self, locations: list[Coordinate]) -> RouteGeometry:
        return RouteGeometry(coordinates=locations)

    def route_legs(self, locations: list[Coordinate]) -> list[RouteLeg]:
        return []


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def depot() -> Depot:
    return Depot(
        name="Main Depot",
        address="123 Dispatch Way, Tampa, FL",
        latitude=27.9506,
        longitude=-82.4572,
    )


def stop(name: str, latitude: float, longitude: float) -> Stop:
    return Stop(
        name=name,
        address="123 Dispatch Way, Tampa, FL",
        normalized_address="123 Dispatch Way, Tampa, FL 33602",
        latitude=latitude,
        longitude=longitude,
        stop_type="delivery",
        quantity=1,
        weight_lbs=100,
        service_minutes=15,
        priority=1,
        address_status="confirmed",
    )


def test_initialize_database_creates_routing_matrix_cache_table(tmp_path):
    database_url = sqlite_url(tmp_path / "routing_cache.db")

    initialize_database(database_url)

    table_names = inspect(create_database_engine(database_url)).get_table_names()
    assert "routing_matrix_cache" in table_names


def test_routing_matrix_service_generates_matrices_for_depot_and_stops(tmp_path):
    database_url = sqlite_url(tmp_path / "matrix.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))
    provider = CountingRoutingProvider()

    with session_factory() as session:
        service = RoutingMatrixService(session, provider)
        result = service.build_for_depot_and_stops(
            depot(),
            [
                stop("First Stop", 27.9606, -82.4672),
                stop("Second Stop", 27.9706, -82.4772),
            ],
        )
        cached_rows = session.scalars(select(RoutingMatrixCache)).all()

    assert result.cache_hit is False
    assert result.travel_time_matrix.durations_minutes == [
        [0, 10, 10],
        [10, 0, 10],
        [10, 10, 0],
    ]
    assert result.distance_matrix.distances_miles == [
        [0, 5, 5],
        [5, 0, 5],
        [5, 5, 0],
    ]
    assert len(cached_rows) == 1
    assert provider.travel_time_calls == 1
    assert provider.distance_calls == 1


def test_routing_matrix_service_reuses_cache_for_identical_coordinates(tmp_path):
    database_url = sqlite_url(tmp_path / "matrix_cache.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))
    provider = CountingRoutingProvider()
    stops = [
        stop("First Stop", 27.9606, -82.4672),
        stop("Second Stop", 27.9706, -82.4772),
    ]

    with session_factory() as session:
        service = RoutingMatrixService(session, provider)
        first = service.build_for_depot_and_stops(depot(), stops)
        second = service.build_for_depot_and_stops(depot(), stops)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert provider.travel_time_calls == 1
    assert provider.distance_calls == 1
    assert second.travel_time_matrix == first.travel_time_matrix
    assert second.distance_matrix == first.distance_matrix


def test_routing_matrix_service_validates_coordinates_before_provider_request(tmp_path):
    database_url = sqlite_url(tmp_path / "invalid_coords.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))
    provider = CountingRoutingProvider()
    bad_depot = depot()
    bad_depot.latitude = 91

    with session_factory() as session:
        service = RoutingMatrixService(session, provider)
        with pytest.raises(ValueError, match="Invalid coordinates for depot"):
            service.build_for_depot_and_stops(bad_depot, [])

    assert provider.travel_time_calls == 0
    assert provider.distance_calls == 0
