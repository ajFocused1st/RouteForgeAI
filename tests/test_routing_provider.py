import pytest
from pydantic import ValidationError

from backend.routing import RoutingProvider
from backend.schemas.routing import (
    Coordinate,
    DistanceMatrix,
    RouteGeometry,
    RouteLeg,
    TravelTimeMatrix,
)


class LocalTestRoutingProvider:
    provider_name = "local-test-routing"

    def travel_time_matrix(self, locations: list[Coordinate]) -> TravelTimeMatrix:
        size = len(locations)
        return TravelTimeMatrix(
            durations_minutes=[
                [0 if row == column else 10 for column in range(size)]
                for row in range(size)
            ]
        )

    def distance_matrix(self, locations: list[Coordinate]) -> DistanceMatrix:
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
        return [
            RouteLeg(
                start=start,
                end=end,
                distance_miles=5,
                travel_duration_minutes=10,
                geometry=RouteGeometry(coordinates=[start, end]),
            )
            for start, end in zip(locations, locations[1:])
        ]


def test_routing_provider_contract_supports_matrices_geometry_and_legs():
    provider: RoutingProvider = LocalTestRoutingProvider()
    locations = [
        Coordinate(latitude=27.9506, longitude=-82.4572),
        Coordinate(latitude=27.9606, longitude=-82.4672),
    ]

    travel_times = provider.travel_time_matrix(locations)
    distances = provider.distance_matrix(locations)
    geometry = provider.route_geometry(locations)
    legs = provider.route_legs(locations)

    assert travel_times.durations_minutes == [[0, 10], [10, 0]]
    assert distances.distances_miles == [[0, 5], [5, 0]]
    assert geometry.coordinates == locations
    assert len(legs) == 1
    assert legs[0].distance_miles == 5
    assert legs[0].travel_duration_minutes == 10


def test_routing_matrices_must_be_square_and_non_negative():
    with pytest.raises(ValidationError):
        TravelTimeMatrix(durations_minutes=[[0, 1], [1]])

    with pytest.raises(ValidationError):
        DistanceMatrix(distances_miles=[[0, -1], [1, 0]])


def test_route_leg_rejects_negative_metrics():
    coordinate = Coordinate(latitude=27.9506, longitude=-82.4572)

    with pytest.raises(ValidationError):
        RouteLeg(
            start=coordinate,
            end=coordinate,
            distance_miles=-1,
            travel_duration_minutes=10,
        )

    with pytest.raises(ValidationError):
        RouteLeg(
            start=coordinate,
            end=coordinate,
            distance_miles=1,
            travel_duration_minutes=-10,
        )
