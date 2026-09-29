from pydantic import BaseModel, Field

from backend.schemas.routing import Coordinate, RouteGeometry, RouteLeg


class DispatchOptimizeRequest(BaseModel):
    depot_id: int = Field(gt=0)
    vehicle_ids: list[int] = Field(min_length=1)
    stop_ids: list[int] = Field(min_length=1)


class DispatchVehicleRoute(BaseModel):
    vehicle_id: int
    vehicle_name: str
    optimized_stop_order: list[int]
    total_distance_miles: float
    total_travel_duration_minutes: float
    total_service_duration_minutes: int
    total_route_duration_minutes: float
    payload_lbs: float
    remaining_capacity_lbs: float | None
    geometry: RouteGeometry
    legs: list[RouteLeg]
    coordinates: list[Coordinate]


class DispatchOptimizeResult(BaseModel):
    solver_status: str
    depot_id: int
    routes: list[DispatchVehicleRoute]
