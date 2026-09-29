from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.api.responses import success_response
from backend.config import Settings, get_settings
from backend.database.session import get_db_session
from backend.models.depot import Depot
from backend.models.route import Route, RouteStop, RouteVersion
from backend.models.stop import Stop
from backend.models.vehicle import Vehicle
from backend.routing import RoutingProvider, ValhallaRoutingProvider
from backend.schemas.route import (
    RouteCreate,
    RouteRead,
    RouteUpdate,
    RouteVersionComparisonRead,
    RouteVersionRead,
    RouteVersionScalarComparison,
    RouteVersionStopOrderComparison,
    RouteVersionStopPositionChange,
)
from backend.services.route_optimization import (
    RouteOptimizationError,
    RouteOptimizationService,
)

router = APIRouter(prefix="/routes", tags=["routes"])


def get_routing_provider(
    settings: Settings = Depends(get_settings),
) -> RoutingProvider:
    return ValhallaRoutingProvider(
        base_url=settings.valhalla_url,
        costing=settings.valhalla_costing,
    )


def _route_response(route: Route, db: Session) -> RouteRead:
    route_stops = db.scalars(
        select(RouteStop)
        .where(RouteStop.route_id == route.id)
        .order_by(RouteStop.stop_order)
    ).all()

    return RouteRead.model_validate(
        {
            "id": route.id,
            "name": route.name,
            "depot_id": route.depot_id,
            "vehicle_id": route.vehicle_id,
            "active": route.active,
            "stops": route_stops,
            "created_at": route.created_at,
            "updated_at": route.updated_at,
        }
    )


def _get_route_or_404(route_id: int, db: Session) -> Route:
    route = db.get(Route, route_id)
    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found.",
        )

    return route


def _get_route_version_or_404(
    route_id: int,
    version_number: int,
    db: Session,
) -> RouteVersion:
    version = db.scalar(
        select(RouteVersion).where(
            RouteVersion.route_id == route_id,
            RouteVersion.version_number == version_number,
        )
    )
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route version not found.",
        )

    return version


def _scalar_comparison(
    base: float | int | None,
    comparison: float | int | None,
) -> RouteVersionScalarComparison:
    difference = (
        comparison - base
        if base is not None and comparison is not None
        else None
    )
    return RouteVersionScalarComparison(
        base=base,
        comparison=comparison,
        difference=difference,
    )


def _metric_number(version: RouteVersion, key: str) -> float | int | None:
    if version.route_metrics is None:
        return None

    value = version.route_metrics.get(key)
    if isinstance(value, int | float):
        return value

    return None


def _stop_order(version: RouteVersion) -> list[int]:
    if version.route_metrics is None:
        return []

    order = version.route_metrics.get("optimized_stop_order")
    if not isinstance(order, list):
        return []

    return [stop_id for stop_id in order if isinstance(stop_id, int)]


def _stop_order_comparison(
    base_order: list[int],
    comparison_order: list[int],
) -> RouteVersionStopOrderComparison:
    base_positions = {
        stop_id: index + 1 for index, stop_id in enumerate(base_order)
    }
    comparison_positions = {
        stop_id: index + 1 for index, stop_id in enumerate(comparison_order)
    }
    all_stop_ids = sorted(set(base_order) | set(comparison_order))
    position_changes = [
        RouteVersionStopPositionChange(
            stop_id=stop_id,
            base_position=base_positions.get(stop_id),
            comparison_position=comparison_positions.get(stop_id),
        )
        for stop_id in all_stop_ids
        if base_positions.get(stop_id) != comparison_positions.get(stop_id)
    ]

    return RouteVersionStopOrderComparison(
        base=base_order,
        comparison=comparison_order,
        changed=base_order != comparison_order,
        added=[stop_id for stop_id in comparison_order if stop_id not in base_positions],
        removed=[stop_id for stop_id in base_order if stop_id not in comparison_positions],
        position_changes=position_changes,
    )


def _validate_route_references(
    db: Session,
    depot_id: int | None = None,
    vehicle_id: int | None = None,
    stop_ids: list[int] | None = None,
) -> None:
    if depot_id is not None and db.get(Depot, depot_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Depot {depot_id} does not exist.",
        )

    if vehicle_id is not None and db.get(Vehicle, vehicle_id) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Vehicle {vehicle_id} does not exist.",
        )

    if stop_ids is not None:
        existing_stop_ids = set(
            db.scalars(select(Stop.id).where(Stop.id.in_(stop_ids))).all()
        )
        missing_stop_ids = [
            stop_id for stop_id in stop_ids if stop_id not in existing_stop_ids
        ]
        if missing_stop_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stop ids not found: {missing_stop_ids}.",
            )


def _replace_route_stops(route_id: int, stop_ids: list[int], db: Session) -> None:
    db.execute(delete(RouteStop).where(RouteStop.route_id == route_id))
    for index, stop_id in enumerate(stop_ids, start=1):
        db.add(RouteStop(route_id=route_id, stop_id=stop_id, stop_order=index))


@router.get("")
def list_routes(db: Session = Depends(get_db_session)) -> dict:
    routes = db.scalars(select(Route).order_by(Route.id)).all()
    return success_response([_route_response(route, db) for route in routes])


@router.get("/{route_id}")
def get_route(route_id: int, db: Session = Depends(get_db_session)) -> dict:
    route = _get_route_or_404(route_id, db)
    return success_response(_route_response(route, db))


@router.get("/{route_id}/versions")
def list_route_versions(
    route_id: int,
    db: Session = Depends(get_db_session),
) -> dict:
    _get_route_or_404(route_id, db)
    versions = db.scalars(
        select(RouteVersion)
        .where(RouteVersion.route_id == route_id)
        .order_by(RouteVersion.version_number)
    ).all()
    return success_response(
        [RouteVersionRead.model_validate(version) for version in versions]
    )


@router.get("/{route_id}/versions/{version_number}")
def get_route_version(
    route_id: int,
    version_number: int,
    db: Session = Depends(get_db_session),
) -> dict:
    _get_route_or_404(route_id, db)
    version = _get_route_version_or_404(route_id, version_number, db)
    return success_response(RouteVersionRead.model_validate(version))


@router.get("/{route_id}/versions/compare/{base_version}/{comparison_version}")
def compare_route_versions(
    route_id: int,
    base_version: int,
    comparison_version: int,
    db: Session = Depends(get_db_session),
) -> dict:
    _get_route_or_404(route_id, db)
    base = _get_route_version_or_404(route_id, base_version, db)
    comparison = _get_route_version_or_404(route_id, comparison_version, db)

    return success_response(
        RouteVersionComparisonRead(
            route_id=route_id,
            base_version=base.version_number,
            comparison_version=comparison.version_number,
            miles=_scalar_comparison(
                base.total_distance_miles,
                comparison.total_distance_miles,
            ),
            drive_time_minutes=_scalar_comparison(
                base.total_travel_duration_minutes,
                comparison.total_travel_duration_minutes,
            ),
            route_time_minutes=_scalar_comparison(
                base.total_route_duration_minutes,
                comparison.total_route_duration_minutes,
            ),
            payload_lbs=_scalar_comparison(
                _metric_number(base, "payload_lbs"),
                _metric_number(comparison, "payload_lbs"),
            ),
            stop_order=_stop_order_comparison(
                _stop_order(base),
                _stop_order(comparison),
            ),
        )
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_route(
    route_in: RouteCreate,
    db: Session = Depends(get_db_session),
) -> dict:
    _validate_route_references(
        db,
        depot_id=route_in.depot_id,
        vehicle_id=route_in.vehicle_id,
        stop_ids=route_in.stop_ids,
    )
    route = Route(
        name=route_in.name,
        depot_id=route_in.depot_id,
        vehicle_id=route_in.vehicle_id,
        active=route_in.active,
    )
    db.add(route)
    db.flush()
    _replace_route_stops(route.id, route_in.stop_ids, db)
    db.commit()
    db.refresh(route)

    return success_response(_route_response(route, db))


@router.put("/{route_id}")
def update_route(
    route_id: int,
    route_in: RouteUpdate,
    db: Session = Depends(get_db_session),
) -> dict:
    route = _get_route_or_404(route_id, db)
    update_data = route_in.model_dump(exclude_unset=True)
    _validate_route_references(
        db,
        depot_id=update_data.get("depot_id"),
        vehicle_id=update_data.get("vehicle_id"),
        stop_ids=update_data.get("stop_ids"),
    )

    stop_ids = update_data.pop("stop_ids", None)
    for field, value in update_data.items():
        setattr(route, field, value)

    if stop_ids is not None:
        _replace_route_stops(route.id, stop_ids, db)

    db.commit()
    db.refresh(route)

    return success_response(_route_response(route, db))


@router.post("/{route_id}/optimize")
def optimize_route(
    route_id: int,
    db: Session = Depends(get_db_session),
    provider: RoutingProvider = Depends(get_routing_provider),
) -> dict:
    route = _get_route_or_404(route_id, db)
    try:
        result = RouteOptimizationService(db, provider).optimize(route)
    except RouteOptimizationError as exc:
        raise HTTPException(
            status_code=exc.failure.status_code,
            detail=exc.failure.message,
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return success_response(result)
