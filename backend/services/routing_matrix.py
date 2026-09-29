from dataclasses import dataclass

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.depot import Depot
from backend.models.routing_matrix_cache import RoutingMatrixCache
from backend.models.stop import Stop
from backend.routing.provider import RoutingProvider
from backend.schemas.routing import Coordinate, DistanceMatrix, TravelTimeMatrix


@dataclass(frozen=True)
class RoutingMatrixResult:
    travel_time_matrix: TravelTimeMatrix
    distance_matrix: DistanceMatrix
    cache_hit: bool


class RoutingMatrixService:
    def __init__(self, db: Session, provider: RoutingProvider):
        self.db = db
        self.provider = provider

    def build_for_depot_and_stops(
        self,
        depot: Depot,
        stops: list[Stop],
    ) -> RoutingMatrixResult:
        locations = self._coordinates_for(depot, stops)
        location_key = self._location_key(locations)
        cached = self.db.scalar(
            select(RoutingMatrixCache).where(
                RoutingMatrixCache.provider == self.provider.provider_name,
                RoutingMatrixCache.location_key == location_key,
            )
        )
        if cached is not None:
            return RoutingMatrixResult(
                travel_time_matrix=TravelTimeMatrix(
                    durations_minutes=cached.durations_minutes
                ),
                distance_matrix=DistanceMatrix(
                    distances_miles=cached.distances_miles
                ),
                cache_hit=True,
            )

        travel_time_matrix = self.provider.travel_time_matrix(locations)
        distance_matrix = self.provider.distance_matrix(locations)
        self.db.add(
            RoutingMatrixCache(
                provider=self.provider.provider_name,
                location_key=location_key,
                durations_minutes=travel_time_matrix.durations_minutes,
                distances_miles=distance_matrix.distances_miles,
            )
        )
        self.db.commit()

        return RoutingMatrixResult(
            travel_time_matrix=travel_time_matrix,
            distance_matrix=distance_matrix,
            cache_hit=False,
        )

    def _coordinates_for(self, depot: Depot, stops: list[Stop]) -> list[Coordinate]:
        coordinates = [self._coordinate(depot.latitude, depot.longitude, "depot")]
        coordinates.extend(
            self._coordinate(stop.latitude, stop.longitude, f"stop {stop.id}")
            for stop in stops
        )
        return coordinates

    def _coordinate(self, latitude: float, longitude: float, label: str) -> Coordinate:
        try:
            return Coordinate(latitude=latitude, longitude=longitude)
        except ValidationError as exc:
            raise ValueError(f"Invalid coordinates for {label}.") from exc

    def _location_key(self, locations: list[Coordinate]) -> str:
        return "|".join(
            f"{location.latitude:.6f},{location.longitude:.6f}"
            for location in locations
        )
