from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.responses import success_response
from backend.config import Settings, get_settings
from backend.database.session import get_db_session
from backend.models.depot import Depot
from backend.models.stop import Stop
from backend.models.vehicle import Vehicle
from backend.optimization import MultiVehicleConfig, MultiVehicleOptimizer, OptimizerStatus
from backend.routing import RoutingProvider, ValhallaRoutingProvider
from backend.schemas.dispatch import (
    DispatchOptimizeRequest,
    DispatchOptimizeResult,
    DispatchVehicleRoute,
)
from backend.schemas.routing import Coordinate, DistanceMatrix, RouteGeometry, TravelTimeMatrix

router = APIRouter(prefix="/dispatch", tags=["dispatch"])


def get_dispatch_routing_provider(
    settings: Settings = Depends(get_settings),
) -> RoutingProvider:
    return ValhallaRoutingProvider(
        base_url=settings.valhalla_url,
        costing=settings.valhalla_costing,
    )


@router.post("/optimize")
def optimize_dispatch(
    dispatch_in: DispatchOptimizeRequest,
    db: Session = Depends(get_db_session),
    provider: RoutingProvider = Depends(get_dispatch_routing_provider),
) -> dict:
    if len(dispatch_in.vehicle_ids) != len(set(dispatch_in.vehicle_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="vehicle_ids cannot contain duplicates.",
        )
    if len(dispatch_in.stop_ids) != len(set(dispatch_in.stop_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="stop_ids cannot contain duplicates.",
        )

    depot = db.get(Depot, dispatch_in.depot_id)
    if depot is None or not depot.active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dispatch depot is missing or inactive.",
        )

    vehicles = _load_vehicles(dispatch_in.vehicle_ids, db)
    stops = _load_stops(dispatch_in.stop_ids, db)
    locations = [_coordinate(depot.latitude, depot.longitude, "depot")]
    locations.extend(
        _coordinate(stop.latitude, stop.longitude, f"stop {stop.id}") for stop in stops
    )

    try:
        travel_matrix = provider.travel_time_matrix(locations)
        distance_matrix = provider.distance_matrix(locations)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    optimizer_result = MultiVehicleOptimizer().solve(
        travel_time_matrix=travel_matrix.durations_minutes,
        distance_matrix=distance_matrix.distances_miles,
        vehicles=[
            MultiVehicleConfig(
                vehicle_id=str(vehicle.id),
                capacity=vehicle.max_payload_lbs,
                start_depot_index=0,
                end_depot_index=0,
                max_hours=(
                    vehicle.max_route_minutes / 60
                    if vehicle.max_route_minutes is not None
                    else None
                ),
                max_mileage=vehicle.max_route_miles,
            )
            for vehicle in vehicles
        ],
        stop_weights=[0, *(stop.weight_lbs for stop in stops)],
        service_durations=[0, *(stop.service_minutes for stop in stops)],
    )
    if optimizer_result.solver_status != OptimizerStatus.OPTIMAL:
        return success_response(
            DispatchOptimizeResult(
                solver_status=optimizer_result.solver_status,
                depot_id=depot.id,
                routes=[],
            )
        )

    stop_by_node_index = {index + 1: stop for index, stop in enumerate(stops)}
    routes = [
        _vehicle_route_response(
            vehicle=vehicle,
            depot=depot,
            node_order=optimizer_result.routes_by_vehicle.get(str(vehicle.id), []),
            stop_by_node_index=stop_by_node_index,
            provider=provider,
        )
        for vehicle in vehicles
    ]
    return success_response(
        DispatchOptimizeResult(
            solver_status=optimizer_result.solver_status,
            depot_id=depot.id,
            routes=routes,
        )
    )


def _load_vehicles(vehicle_ids: list[int], db: Session) -> list[Vehicle]:
    vehicles_by_id = {
        vehicle.id: vehicle
        for vehicle in db.scalars(select(Vehicle).where(Vehicle.id.in_(vehicle_ids))).all()
    }
    missing_or_inactive = [
        vehicle_id
        for vehicle_id in vehicle_ids
        if vehicle_id not in vehicles_by_id or not vehicles_by_id[vehicle_id].active
    ]
    if missing_or_inactive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vehicle ids missing or inactive: {missing_or_inactive}.",
        )

    return [vehicles_by_id[vehicle_id] for vehicle_id in vehicle_ids]


def _load_stops(stop_ids: list[int], db: Session) -> list[Stop]:
    stops_by_id = {
        stop.id: stop
        for stop in db.scalars(select(Stop).where(Stop.id.in_(stop_ids))).all()
    }
    missing_or_inactive = [
        stop_id
        for stop_id in stop_ids
        if stop_id not in stops_by_id or not stops_by_id[stop_id].active
    ]
    if missing_or_inactive:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stop ids missing or inactive: {missing_or_inactive}.",
        )

    return [stops_by_id[stop_id] for stop_id in stop_ids]


def _vehicle_route_response(
    vehicle: Vehicle,
    depot: Depot,
    node_order: list[int],
    stop_by_node_index: dict[int, Stop],
    provider: RoutingProvider,
) -> DispatchVehicleRoute:
    ordered_stops = [stop_by_node_index[node] for node in node_order]
    locations = [_coordinate(depot.latitude, depot.longitude, "depot")]
    locations.extend(
        _coordinate(stop.latitude, stop.longitude, f"stop {stop.id}")
        for stop in ordered_stops
    )
    locations.append(_coordinate(depot.latitude, depot.longitude, "depot"))

    if ordered_stops:
        geometry = provider.route_geometry(locations)
        legs = provider.route_legs(locations)
    else:
        geometry = RouteGeometry(coordinates=[])
        legs = []

    distance = sum(leg.distance_miles for leg in legs)
    travel_duration = sum(leg.travel_duration_minutes for leg in legs)
    service_duration = sum(stop.service_minutes for stop in ordered_stops)
    payload = sum(stop.weight_lbs for stop in ordered_stops)
    return DispatchVehicleRoute(
        vehicle_id=vehicle.id,
        vehicle_name=vehicle.name,
        optimized_stop_order=[stop.id for stop in ordered_stops],
        total_distance_miles=distance,
        total_travel_duration_minutes=travel_duration,
        total_service_duration_minutes=service_duration,
        total_route_duration_minutes=travel_duration + service_duration,
        payload_lbs=payload,
        remaining_capacity_lbs=(
            vehicle.max_payload_lbs - payload
            if vehicle.max_payload_lbs is not None
            else None
        ),
        geometry=geometry,
        legs=legs,
        coordinates=locations,
    )


def _coordinate(latitude: float, longitude: float, label: str) -> Coordinate:
    try:
        return Coordinate(latitude=latitude, longitude=longitude)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid coordinates for {label}.",
        ) from exc
