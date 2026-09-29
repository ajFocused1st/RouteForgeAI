from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.schemas.routing import Coordinate, RouteGeometry, RouteLeg


class RouteStopAssignmentRead(BaseModel):
    id: int
    stop_id: int
    stop_order: int
    eta: datetime | None = None
    departure_time: datetime | None = None
    distance_from_previous_miles: float | None = None
    travel_duration_minutes: int | None = None
    service_duration_minutes: int | None = None

    model_config = ConfigDict(from_attributes=True)


class RouteBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    depot_id: int | None = Field(default=None, gt=0)
    vehicle_id: int | None = Field(default=None, gt=0)
    active: bool = True


class RouteCreate(RouteBase):
    stop_ids: list[int] = Field(default_factory=list)

    @field_validator("stop_ids")
    @classmethod
    def validate_stop_ids(cls, value: list[int]) -> list[int]:
        if any(stop_id <= 0 for stop_id in value):
            raise ValueError("stop_ids must contain positive integers.")

        if len(value) != len(set(value)):
            raise ValueError("stop_ids cannot contain duplicates.")

        return value


class RouteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    depot_id: int | None = Field(default=None, gt=0)
    vehicle_id: int | None = Field(default=None, gt=0)
    active: bool | None = None
    stop_ids: list[int] | None = None

    @field_validator("stop_ids")
    @classmethod
    def validate_stop_ids(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value

        if any(stop_id <= 0 for stop_id in value):
            raise ValueError("stop_ids must contain positive integers.")

        if len(value) != len(set(value)):
            raise ValueError("stop_ids cannot contain duplicates.")

        return value


class RouteRead(RouteBase):
    id: int
    stops: list[RouteStopAssignmentRead]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RouteVersionRead(BaseModel):
    id: int
    route_id: int
    version_number: int
    solver_status: str
    total_distance_miles: float | None = None
    total_travel_duration_minutes: int | None = None
    total_service_duration_minutes: int | None = None
    total_route_duration_minutes: int | None = None
    route_metrics: dict | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RouteVersionScalarComparison(BaseModel):
    base: float | int | None = None
    comparison: float | int | None = None
    difference: float | int | None = None


class RouteVersionStopPositionChange(BaseModel):
    stop_id: int
    base_position: int | None = None
    comparison_position: int | None = None


class RouteVersionStopOrderComparison(BaseModel):
    base: list[int]
    comparison: list[int]
    changed: bool
    added: list[int]
    removed: list[int]
    position_changes: list[RouteVersionStopPositionChange]


class RouteVersionComparisonRead(BaseModel):
    route_id: int
    base_version: int
    comparison_version: int
    miles: RouteVersionScalarComparison
    drive_time_minutes: RouteVersionScalarComparison
    route_time_minutes: RouteVersionScalarComparison
    payload_lbs: RouteVersionScalarComparison
    stop_order: RouteVersionStopOrderComparison


class OptimizedStopRead(BaseModel):
    stop_id: int
    stop_order: int
    eta_minutes: float | None = None
    departure_minutes: float | None = None
    distance_from_previous_miles: float | None = None
    travel_duration_minutes: float | None = None
    service_duration_minutes: int | None = None


class RouteOptimizationMetrics(BaseModel):
    total_distance_miles: float
    total_travel_duration_minutes: float
    total_service_duration_minutes: int
    total_route_duration_minutes: float
    number_of_stops: int
    payload_lbs: float
    remaining_capacity_lbs: float
    pre_pickup_deadhead_miles: float
    between_job_repositioning_miles: float
    post_delivery_deadhead_miles: float
    return_to_depot_deadhead_miles: float
    total_unloaded_miles: float
    deadhead_percentage: float
    cache_hit: bool


class RouteOptimizationResult(BaseModel):
    route_id: int
    route_version_id: int
    version_number: int
    solver_status: str
    optimized_stop_order: list[int]
    stops: list[OptimizedStopRead]
    metrics: RouteOptimizationMetrics
    geometry: RouteGeometry
    legs: list[RouteLeg]
    coordinates: list[Coordinate]
