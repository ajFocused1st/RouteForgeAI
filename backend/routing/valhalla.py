import json
from collections.abc import Callable
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from backend.schemas.routing import (
    Coordinate,
    DistanceMatrix,
    RouteGeometry,
    RouteLeg,
    TravelTimeMatrix,
)

ValhallaTransport = Callable[[str, dict | None, float], dict]
KM_TO_MILES = 0.621371


def _default_transport(url: str, payload: dict | None, timeout_seconds: float) -> dict:
    if payload is None:
        request_url = url
    else:
        request_url = f"{url}?{urlencode({'json': json.dumps(payload)})}"

    with urlopen(request_url, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass
class ValhallaRoutingProvider:
    base_url: str = "http://127.0.0.1:8002"
    costing: str = "auto"
    timeout_seconds: float = 10.0
    transport: ValhallaTransport = _default_transport
    provider_name: str = "valhalla"

    def health_check(self) -> dict:
        return self._request("/status")

    def travel_time_matrix(self, locations: list[Coordinate]) -> TravelTimeMatrix:
        matrix = self._matrix(locations)
        return TravelTimeMatrix(
            durations_minutes=[
                [cell["time"] / 60 for cell in row]
                for row in matrix["sources_to_targets"]
            ]
        )

    def distance_matrix(self, locations: list[Coordinate]) -> DistanceMatrix:
        matrix = self._matrix(locations)
        return DistanceMatrix(
            distances_miles=[
                [cell["distance"] * KM_TO_MILES for cell in row]
                for row in matrix["sources_to_targets"]
            ]
        )

    def route_geometry(self, locations: list[Coordinate]) -> RouteGeometry:
        route = self._route(locations)
        legs = route.get("trip", {}).get("legs", [])
        polylines = [leg["shape"] for leg in legs if leg.get("shape")]
        return RouteGeometry(polyline=";".join(polylines) if polylines else None)

    def route_legs(self, locations: list[Coordinate]) -> list[RouteLeg]:
        route = self._route(locations)
        legs = route.get("trip", {}).get("legs", [])
        route_legs = []

        for index, leg in enumerate(legs):
            summary = leg.get("summary", {})
            route_legs.append(
                RouteLeg(
                    start=locations[index],
                    end=locations[index + 1],
                    distance_miles=float(summary.get("length", 0)),
                    travel_duration_minutes=float(summary.get("time", 0)) / 60,
                    geometry=RouteGeometry(polyline=leg.get("shape")),
                )
            )

        return route_legs

    def _matrix(self, locations: list[Coordinate]) -> dict:
        if len(locations) < 1:
            raise ValueError("At least one location is required for a matrix request.")

        valhalla_locations = self._locations_payload(locations)
        return self._request(
            "/sources_to_targets",
            {
                "sources": valhalla_locations,
                "targets": valhalla_locations,
                "costing": self.costing,
            },
        )

    def _route(self, locations: list[Coordinate]) -> dict:
        if len(locations) < 2:
            raise ValueError("At least two locations are required for a route request.")

        return self._request(
            "/route",
            {
                "locations": self._locations_payload(locations),
                "costing": self.costing,
                "directions_options": {"units": "miles"},
            },
        )

    def _request(self, path: str, payload: dict | None = None) -> dict:
        url = f"{self.base_url.rstrip('/')}{path}"
        try:
            return self.transport(url, payload, self.timeout_seconds)
        except (TimeoutError, HTTPError, URLError, OSError) as exc:
            raise RuntimeError(f"Valhalla request failed: {exc}") from exc

    def _locations_payload(self, locations: list[Coordinate]) -> list[dict[str, float]]:
        return [
            {"lat": location.latitude, "lon": location.longitude}
            for location in locations
        ]
