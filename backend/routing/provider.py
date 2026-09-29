from typing import Protocol

from backend.schemas.routing import (
    Coordinate,
    DistanceMatrix,
    RouteGeometry,
    RouteLeg,
    TravelTimeMatrix,
)


class RoutingProvider(Protocol):
    """Provider contract for route network calculations."""

    provider_name: str

    def travel_time_matrix(self, locations: list[Coordinate]) -> TravelTimeMatrix:
        """Return pairwise travel times in minutes."""

    def distance_matrix(self, locations: list[Coordinate]) -> DistanceMatrix:
        """Return pairwise distances in miles."""

    def route_geometry(self, locations: list[Coordinate]) -> RouteGeometry:
        """Return route geometry for ordered locations."""

    def route_legs(self, locations: list[Coordinate]) -> list[RouteLeg]:
        """Return per-leg routing details for ordered locations."""
