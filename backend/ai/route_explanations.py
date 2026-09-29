from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.ai.provider import AIProvider
from backend.models.depot import Depot
from backend.models.route import Route, RouteStop, RouteVersion
from backend.models.stop import Stop
from backend.models.vehicle import Vehicle
from backend.schemas.ai import AIRouteExplanationResponse


class AIRouteExplanationError(RuntimeError):
    """Raised when application facts for an AI route explanation are unavailable."""


class AIRouteExplanationService:
    def __init__(self, db: Session, provider: AIProvider):
        self.db = db
        self.provider = provider

    def explain(
        self,
        question: str,
        route_id: int,
        route_version: int | None = None,
        base_version: int | None = None,
        comparison_version: int | None = None,
        shipment_weight_lbs: float | None = None,
    ) -> AIRouteExplanationResponse:
        route = self._get_route(route_id)
        intent = self._intent(question)
        facts = self._facts_for_intent(
            intent=intent,
            route=route,
            route_version=route_version,
            base_version=base_version,
            comparison_version=comparison_version,
            shipment_weight_lbs=shipment_weight_lbs,
        )
        facts["ai_grounding_rule"] = (
            "Explain only these application-calculated facts. Do not invent "
            "mileage, capacity, stop order, ETAs, feasibility, or version deltas."
        )
        explanation = self.provider.explain_results(facts, question=question)
        return AIRouteExplanationResponse(
            question=question,
            intent=intent,
            explanation=explanation,
            application_facts=facts,
        )

    def _facts_for_intent(
        self,
        intent: str,
        route: Route,
        route_version: int | None,
        base_version: int | None,
        comparison_version: int | None,
        shipment_weight_lbs: float | None,
    ) -> dict[str, Any]:
        if intent == "deadhead":
            return self._deadhead_facts(route, route_version)

        if intent == "infeasible":
            return self._infeasible_facts(route, route_version)

        if intent == "version_change":
            if base_version is None or comparison_version is None:
                raise AIRouteExplanationError(
                    "base_version and comparison_version are required."
                )
            return self._version_change_facts(route, base_version, comparison_version)

        if intent == "shipment_fit":
            return self._shipment_fit_facts(route, route_version, shipment_weight_lbs)

        return self._route_summary_facts(route, route_version)

    def _deadhead_facts(
        self,
        route: Route,
        route_version: int | None,
    ) -> dict[str, Any]:
        version = self._get_version(route.id, route_version)
        ordered_stops = self._ordered_stops_for_version(route, version)
        legs = self._legs(version)
        if len(legs) != len(ordered_stops) + 1:
            raise AIRouteExplanationError(
                "Route version does not include complete leg distances."
            )

        current_load = self._initial_depot_load(ordered_stops)
        by_stop: dict[int, float] = {stop.id: 0.0 for stop in ordered_stops}
        return_to_depot = 0.0

        for leg_index, leg in enumerate(legs):
            distance = self._number(leg.get("distance_miles"))
            if current_load <= 0:
                if leg_index == len(ordered_stops):
                    return_to_depot += distance
                else:
                    by_stop[ordered_stops[leg_index].id] += distance

            if leg_index < len(ordered_stops):
                current_load = self._load_after_stop(
                    current_load,
                    ordered_stops[leg_index],
                )

        most_deadhead_stop_id = (
            max(by_stop, key=lambda stop_id: by_stop[stop_id]) if by_stop else None
        )
        return {
            "route_id": route.id,
            "version_number": version.version_number,
            "total_unloaded_miles": self._metric(version, "total_unloaded_miles"),
            "deadhead_percentage": self._metric(version, "deadhead_percentage"),
            "return_to_depot_deadhead_miles": return_to_depot,
            "deadhead_miles_by_stop": [
                {
                    "stop_id": stop.id,
                    "stop_name": stop.name,
                    "unloaded_miles_into_stop": by_stop[stop.id],
                }
                for stop in ordered_stops
            ],
            "most_deadhead_stop": (
                {
                    "stop_id": most_deadhead_stop_id,
                    "unloaded_miles_into_stop": by_stop[most_deadhead_stop_id],
                }
                if most_deadhead_stop_id is not None
                else None
            ),
        }

    def _infeasible_facts(
        self,
        route: Route,
        route_version: int | None,
    ) -> dict[str, Any]:
        version = self._get_version(route.id, route_version)
        route_stops = self._route_stops(route.id)
        stops = [self._get_stop(route_stop.stop_id) for route_stop in route_stops]
        vehicle = self.db.get(Vehicle, route.vehicle_id) if route.vehicle_id else None
        depot = self.db.get(Depot, route.depot_id) if route.depot_id else None
        payload = sum(stop.weight_lbs for stop in stops)
        return {
            "route_id": route.id,
            "version_number": version.version_number,
            "solver_status": version.solver_status,
            "is_infeasible": version.solver_status == "no_feasible_solution",
            "vehicle": (
                {
                    "id": vehicle.id,
                    "name": vehicle.name,
                    "max_payload_lbs": vehicle.max_payload_lbs,
                    "max_route_minutes": vehicle.max_route_minutes,
                }
                if vehicle is not None
                else None
            ),
            "depot": (
                {
                    "id": depot.id,
                    "name": depot.name,
                    "default_start_time": str(depot.default_start_time),
                }
                if depot is not None
                else None
            ),
            "payload_lbs": payload,
            "stops": [
                {
                    "id": stop.id,
                    "name": stop.name,
                    "weight_lbs": stop.weight_lbs,
                    "service_minutes": stop.service_minutes,
                    "earliest_time": str(stop.earliest_time) if stop.earliest_time else None,
                    "latest_time": str(stop.latest_time) if stop.latest_time else None,
                }
                for stop in stops
            ],
        }

    def _version_change_facts(
        self,
        route: Route,
        base_version: int,
        comparison_version: int,
    ) -> dict[str, Any]:
        base = self._get_version(route.id, base_version)
        comparison = self._get_version(route.id, comparison_version)
        return {
            "route_id": route.id,
            "base_version": base.version_number,
            "comparison_version": comparison.version_number,
            "miles": self._scalar_comparison(
                base.total_distance_miles,
                comparison.total_distance_miles,
            ),
            "drive_time_minutes": self._scalar_comparison(
                base.total_travel_duration_minutes,
                comparison.total_travel_duration_minutes,
            ),
            "route_time_minutes": self._scalar_comparison(
                base.total_route_duration_minutes,
                comparison.total_route_duration_minutes,
            ),
            "payload_lbs": self._scalar_comparison(
                self._metric(base, "payload_lbs"),
                self._metric(comparison, "payload_lbs"),
            ),
            "stop_order": {
                "base": self._stop_order(base),
                "comparison": self._stop_order(comparison),
            },
        }

    def _shipment_fit_facts(
        self,
        route: Route,
        route_version: int | None,
        shipment_weight_lbs: float | None,
    ) -> dict[str, Any]:
        version = self._get_version(route.id, route_version)
        vehicle = self.db.get(Vehicle, route.vehicle_id) if route.vehicle_id else None
        current_payload = self._metric(version, "payload_lbs")
        if current_payload is None:
            current_payload = sum(
                self._get_stop(route_stop.stop_id).weight_lbs
                for route_stop in self._route_stops(route.id)
            )
        capacity = vehicle.max_payload_lbs if vehicle is not None else None
        remaining = capacity - current_payload if capacity is not None else None
        fits = (
            shipment_weight_lbs <= remaining
            if shipment_weight_lbs is not None and remaining is not None
            else None
        )
        return {
            "route_id": route.id,
            "version_number": version.version_number,
            "vehicle": (
                {
                    "id": vehicle.id,
                    "name": vehicle.name,
                    "max_payload_lbs": capacity,
                }
                if vehicle is not None
                else None
            ),
            "current_payload_lbs": current_payload,
            "remaining_capacity_lbs": remaining,
            "shipment_weight_lbs": shipment_weight_lbs,
            "fits": fits,
        }

    def _route_summary_facts(
        self,
        route: Route,
        route_version: int | None,
    ) -> dict[str, Any]:
        version = self._get_version(route.id, route_version)
        return {
            "route_id": route.id,
            "version_number": version.version_number,
            "solver_status": version.solver_status,
            "total_distance_miles": version.total_distance_miles,
            "total_travel_duration_minutes": version.total_travel_duration_minutes,
            "total_route_duration_minutes": version.total_route_duration_minutes,
            "route_metrics": version.route_metrics or {},
        }

    def _get_route(self, route_id: int) -> Route:
        route = self.db.get(Route, route_id)
        if route is None:
            raise AIRouteExplanationError("Route not found.")
        return route

    def _get_version(
        self,
        route_id: int,
        version_number: int | None,
    ) -> RouteVersion:
        statement = select(RouteVersion).where(RouteVersion.route_id == route_id)
        if version_number is None:
            statement = statement.order_by(RouteVersion.version_number.desc())
        else:
            statement = statement.where(RouteVersion.version_number == version_number)
        version = self.db.scalar(statement)
        if version is None:
            raise AIRouteExplanationError("Route version not found.")
        return version

    def _route_stops(self, route_id: int) -> list[RouteStop]:
        return self.db.scalars(
            select(RouteStop)
            .where(RouteStop.route_id == route_id)
            .order_by(RouteStop.stop_order)
        ).all()

    def _ordered_stops_for_version(
        self,
        route: Route,
        version: RouteVersion,
    ) -> list[Stop]:
        ordered_ids = self._stop_order(version)
        if not ordered_ids:
            ordered_ids = [route_stop.stop_id for route_stop in self._route_stops(route.id)]
        return [self._get_stop(stop_id) for stop_id in ordered_ids]

    def _get_stop(self, stop_id: int) -> Stop:
        stop = self.db.get(Stop, stop_id)
        if stop is None:
            raise AIRouteExplanationError(f"Stop {stop_id} not found.")
        return stop

    def _legs(self, version: RouteVersion) -> list[dict[str, Any]]:
        metrics = version.route_metrics or {}
        legs = metrics.get("legs")
        if not isinstance(legs, list):
            return []
        return [leg for leg in legs if isinstance(leg, dict)]

    def _stop_order(self, version: RouteVersion) -> list[int]:
        metrics = version.route_metrics or {}
        order = metrics.get("optimized_stop_order")
        if not isinstance(order, list):
            return []
        return [stop_id for stop_id in order if isinstance(stop_id, int)]

    def _metric(self, version: RouteVersion, key: str) -> float | int | None:
        metrics = version.route_metrics or {}
        value = metrics.get(key)
        return value if isinstance(value, int | float) else None

    def _number(self, value: Any) -> float:
        if not isinstance(value, int | float):
            raise AIRouteExplanationError("Route leg is missing a numeric distance.")
        return float(value)

    def _scalar_comparison(
        self,
        base: float | int | None,
        comparison: float | int | None,
    ) -> dict[str, float | int | None]:
        return {
            "base": base,
            "comparison": comparison,
            "difference": (
                comparison - base
                if base is not None and comparison is not None
                else None
            ),
        }

    def _initial_depot_load(self, stops: list[Stop]) -> float:
        load = 0.0
        for stop in stops:
            if stop.stop_type == "delivery":
                load += stop.weight_lbs
                continue
            if stop.stop_type == "pickup_delivery":
                load += stop.weight_lbs
            break
        return max(0.0, load)

    def _load_after_stop(self, current_load: float, stop: Stop) -> float:
        if stop.stop_type == "pickup":
            return current_load + stop.weight_lbs
        if stop.stop_type == "delivery":
            return max(0.0, current_load - stop.weight_lbs)
        if stop.stop_type == "pickup_delivery":
            return max(0.0, current_load - stop.weight_lbs) + stop.weight_lbs
        return current_load

    def _intent(self, question: str) -> str:
        normalized = question.lower()
        if "deadhead" in normalized:
            return "deadhead"
        if "infeasible" in normalized or "no feasible" in normalized:
            return "infeasible"
        if "version" in normalized and (
            "changed" in normalized or "change" in normalized or "compare" in normalized
        ):
            return "version_change"
        if "fit" in normalized or "shipment" in normalized or "capacity" in normalized:
            return "shipment_fit"
        return "route_summary"
