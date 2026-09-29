from dataclasses import dataclass
from datetime import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.economics.deadhead import DeadheadCalculator, DeadheadStop
from backend.models.depot import Depot
from backend.models.route import Route, RouteStop, RouteVersion
from backend.models.stop import Stop
from backend.models.vehicle import Vehicle
from backend.optimization import OptimizerStatus, SingleVehicleOptimizer
from backend.routing.provider import RoutingProvider
from backend.schemas.route import (
    OptimizedStopRead,
    RouteOptimizationMetrics,
    RouteOptimizationResult,
)
from backend.schemas.routing import Coordinate, RouteGeometry, RouteLeg
from backend.services.routing_matrix import RoutingMatrixService


@dataclass(frozen=True)
class RouteOptimizationFailure:
    status_code: int
    message: str


class RouteOptimizationError(Exception):
    def __init__(self, failure: RouteOptimizationFailure):
        self.failure = failure


class RouteOptimizationService:
    def __init__(
        self,
        db: Session,
        provider: RoutingProvider,
        optimizer: SingleVehicleOptimizer | None = None,
    ):
        self.db = db
        self.provider = provider
        self.optimizer = optimizer or SingleVehicleOptimizer()

    def optimize(self, route: Route) -> RouteOptimizationResult:
        depot, vehicle, route_stops, stops = self._validate_route(route)
        matrix_result = RoutingMatrixService(
            self.db,
            self.provider,
        ).build_for_depot_and_stops(depot, stops)

        optimizer_result = self.optimizer.solve(
            matrix_result.travel_time_matrix.durations_minutes,
            depot_index=0,
            stop_weights=[0, *(stop.weight_lbs for stop in stops)],
            vehicle_payload_capacity=vehicle.max_payload_lbs,
            earliest_arrivals=[0, *(self._minutes_since_midnight(stop.earliest_time) or 0 for stop in stops)],
            latest_arrivals=[
                self._route_end_minutes(depot, vehicle),
                *(
                    self._minutes_since_midnight(stop.latest_time)
                    or self._route_end_minutes(depot, vehicle)
                    for stop in stops
                ),
            ],
            service_durations=[0, *(stop.service_minutes for stop in stops)],
            route_start_time=self._minutes_since_midnight(depot.default_start_time),
            required_end_time=self._route_end_minutes(depot, vehicle),
        )

        if optimizer_result.solver_status != OptimizerStatus.OPTIMAL:
            version = self._save_route_version(
                route=route,
                solver_status=optimizer_result.solver_status,
                total_distance_miles=None,
                total_travel_duration_minutes=None,
                total_service_duration_minutes=None,
                total_route_duration_minutes=None,
                route_metrics={
                    "optimized_stop_order": optimizer_result.optimized_stop_order,
                    "cache_hit": matrix_result.cache_hit,
                },
            )
            raise RouteOptimizationError(
                RouteOptimizationFailure(
                    status_code=409,
                    message=(
                        "Route has no feasible optimization solution."
                        if optimizer_result.solver_status
                        == OptimizerStatus.NO_FEASIBLE_SOLUTION
                        else f"Route optimization failed: {optimizer_result.solver_status}."
                    ),
                )
            )

        ordered_stops = [
            stops[node_index - 1] for node_index in optimizer_result.optimized_stop_order
        ]
        locations = self._final_locations(depot, ordered_stops)
        geometry = self.provider.route_geometry(locations)
        legs = self.provider.route_legs(locations)
        metrics = self._metrics(legs, ordered_stops, vehicle, matrix_result.cache_hit)
        optimized_stops = self._optimized_stops(
            ordered_stops,
            legs,
            self._minutes_since_midnight(depot.default_start_time),
        )
        version = self._save_route_version(
            route=route,
            solver_status=optimizer_result.solver_status,
            total_distance_miles=metrics.total_distance_miles,
            total_travel_duration_minutes=metrics.total_travel_duration_minutes,
            total_service_duration_minutes=metrics.total_service_duration_minutes,
            total_route_duration_minutes=metrics.total_route_duration_minutes,
            route_metrics={
                "optimized_stop_order": [stop.id for stop in ordered_stops],
                "stops": [stop.model_dump() for stop in optimized_stops],
                "geometry": geometry.model_dump(),
                "legs": [leg.model_dump() for leg in legs],
                "coordinates": [location.model_dump() for location in locations],
                "payload_lbs": metrics.payload_lbs,
                "pre_pickup_deadhead_miles": metrics.pre_pickup_deadhead_miles,
                "between_job_repositioning_miles": (
                    metrics.between_job_repositioning_miles
                ),
                "post_delivery_deadhead_miles": metrics.post_delivery_deadhead_miles,
                "return_to_depot_deadhead_miles": (
                    metrics.return_to_depot_deadhead_miles
                ),
                "total_unloaded_miles": metrics.total_unloaded_miles,
                "deadhead_percentage": metrics.deadhead_percentage,
                "cache_hit": matrix_result.cache_hit,
            },
        )

        return RouteOptimizationResult(
            route_id=route.id,
            route_version_id=version.id,
            version_number=version.version_number,
            solver_status=optimizer_result.solver_status,
            optimized_stop_order=[stop.id for stop in ordered_stops],
            stops=optimized_stops,
            metrics=metrics,
            geometry=geometry,
            legs=legs,
            coordinates=locations,
        )

    def _validate_route(
        self,
        route: Route,
    ) -> tuple[Depot, Vehicle, list[RouteStop], list[Stop]]:
        if not route.active:
            self._fail(400, "Route is inactive and cannot be optimized.")

        if route.depot_id is None:
            self._fail(400, "Route must have a depot before optimization.")

        if route.vehicle_id is None:
            self._fail(400, "Route must have a vehicle before optimization.")

        depot = self.db.get(Depot, route.depot_id)
        vehicle = self.db.get(Vehicle, route.vehicle_id)
        if depot is None or not depot.active:
            self._fail(400, "Route depot is missing or inactive.")

        if vehicle is None or not vehicle.active:
            self._fail(400, "Route vehicle is missing or inactive.")

        route_stops = self.db.scalars(
            select(RouteStop)
            .where(RouteStop.route_id == route.id)
            .order_by(RouteStop.stop_order)
        ).all()
        if not route_stops:
            self._fail(400, "Route must have at least one stop before optimization.")

        stops = []
        for route_stop in route_stops:
            stop = self.db.get(Stop, route_stop.stop_id)
            if stop is None or not stop.active:
                self._fail(
                    400,
                    f"Route stop {route_stop.stop_id} is missing or inactive.",
                )
            stops.append(stop)

        return depot, vehicle, route_stops, stops

    def _metrics(
        self,
        legs: list[RouteLeg],
        ordered_stops: list[Stop],
        vehicle: Vehicle,
        cache_hit: bool,
    ) -> RouteOptimizationMetrics:
        total_distance = sum(leg.distance_miles for leg in legs)
        total_travel = sum(leg.travel_duration_minutes for leg in legs)
        total_service = sum(stop.service_minutes for stop in ordered_stops)
        payload = sum(stop.weight_lbs for stop in ordered_stops)
        deadhead = DeadheadCalculator().calculate(
            [
                DeadheadStop(stop_type=stop.stop_type, weight_lbs=stop.weight_lbs)
                for stop in ordered_stops
            ],
            [leg.distance_miles for leg in legs],
        )

        return RouteOptimizationMetrics(
            total_distance_miles=total_distance,
            total_travel_duration_minutes=total_travel,
            total_service_duration_minutes=total_service,
            total_route_duration_minutes=total_travel + total_service,
            number_of_stops=len(ordered_stops),
            payload_lbs=payload,
            remaining_capacity_lbs=vehicle.max_payload_lbs - payload,
            pre_pickup_deadhead_miles=deadhead.pre_pickup_deadhead_miles,
            between_job_repositioning_miles=deadhead.between_job_repositioning_miles,
            post_delivery_deadhead_miles=deadhead.post_delivery_deadhead_miles,
            return_to_depot_deadhead_miles=deadhead.return_to_depot_deadhead_miles,
            total_unloaded_miles=deadhead.total_unloaded_miles,
            deadhead_percentage=deadhead.deadhead_percentage,
            cache_hit=cache_hit,
        )

    def _optimized_stops(
        self,
        ordered_stops: list[Stop],
        legs: list[RouteLeg],
        route_start_minutes: int,
    ) -> list[OptimizedStopRead]:
        elapsed = float(route_start_minutes)
        optimized_stops = []

        for index, stop in enumerate(ordered_stops, start=1):
            inbound_leg = legs[index - 1]
            elapsed += inbound_leg.travel_duration_minutes
            eta = elapsed
            elapsed += stop.service_minutes
            optimized_stops.append(
                OptimizedStopRead(
                    stop_id=stop.id,
                    stop_order=index,
                    eta_minutes=eta,
                    departure_minutes=elapsed,
                    distance_from_previous_miles=inbound_leg.distance_miles,
                    travel_duration_minutes=inbound_leg.travel_duration_minutes,
                    service_duration_minutes=stop.service_minutes,
                )
            )

        return optimized_stops

    def _final_locations(
        self,
        depot: Depot,
        ordered_stops: list[Stop],
    ) -> list[Coordinate]:
        locations = [Coordinate(latitude=depot.latitude, longitude=depot.longitude)]
        locations.extend(
            Coordinate(latitude=stop.latitude, longitude=stop.longitude)
            for stop in ordered_stops
        )
        locations.append(Coordinate(latitude=depot.latitude, longitude=depot.longitude))
        return locations

    def _save_route_version(
        self,
        route: Route,
        solver_status: str,
        total_distance_miles: float | None,
        total_travel_duration_minutes: float | None,
        total_service_duration_minutes: int | None,
        total_route_duration_minutes: float | None,
        route_metrics: dict,
    ) -> RouteVersion:
        current_max = self.db.scalar(
            select(func.max(RouteVersion.version_number)).where(
                RouteVersion.route_id == route.id
            )
        )
        version = RouteVersion(
            route_id=route.id,
            version_number=(current_max or 0) + 1,
            solver_status=str(solver_status),
            total_distance_miles=total_distance_miles,
            total_travel_duration_minutes=(
                round(total_travel_duration_minutes)
                if total_travel_duration_minutes is not None
                else None
            ),
            total_service_duration_minutes=total_service_duration_minutes,
            total_route_duration_minutes=(
                round(total_route_duration_minutes)
                if total_route_duration_minutes is not None
                else None
            ),
            route_metrics=route_metrics,
        )
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        return version

    def _route_end_minutes(self, depot: Depot, vehicle: Vehicle) -> int | None:
        if vehicle.max_route_minutes is None:
            return None

        return self._minutes_since_midnight(depot.default_start_time) + vehicle.max_route_minutes

    def _minutes_since_midnight(self, value: time | None) -> int | None:
        if value is None:
            return None

        return value.hour * 60 + value.minute

    def _fail(self, status_code: int, message: str) -> None:
        raise RouteOptimizationError(
            RouteOptimizationFailure(status_code=status_code, message=message)
        )
