from datetime import datetime, time
from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from backend.database.session import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from backend.models.depot import Depot
from backend.models.route import OptimizationRun, Route, RouteStop, RouteVersion
from backend.models.stop import Stop
from backend.models.vehicle import Vehicle


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def create_route_dependencies(session):
    depot = Depot(
        name="Main Depot",
        address="123 Dispatch Way, Tampa, FL",
        latitude=27.9506,
        longitude=-82.4572,
        default_start_time=time(8, 0),
    )
    vehicle = Vehicle(name="Cargo Van 1", max_payload_lbs=3400)
    stop = Stop(
        name="Dock Pickup",
        address="123 Dispatch Way, Tampa, FL",
        normalized_address="123 Dispatch Way, Tampa, FL 33602",
        latitude=27.9506,
        longitude=-82.4572,
        stop_type="pickup",
        quantity=1,
        weight_lbs=100,
        service_minutes=15,
        priority=1,
        address_status="confirmed",
    )
    session.add_all([depot, vehicle, stop])
    session.commit()
    session.refresh(depot)
    session.refresh(vehicle)
    session.refresh(stop)
    return depot, vehicle, stop


def test_initialize_database_creates_route_tables(tmp_path):
    database_url = sqlite_url(tmp_path / "routes.db")

    initialize_database(database_url)

    table_names = inspect(create_database_engine(database_url)).get_table_names()
    assert "routes" in table_names
    assert "route_stops" in table_names
    assert "route_versions" in table_names
    assert "optimization_runs" in table_names


def test_route_stop_stores_order_and_timing_metrics(tmp_path):
    database_url = sqlite_url(tmp_path / "route_stop.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))

    with session_factory() as session:
        depot, vehicle, stop = create_route_dependencies(session)
        route = Route(name="Morning Route", depot_id=depot.id, vehicle_id=vehicle.id)
        session.add(route)
        session.commit()
        session.refresh(route)

        route_stop = RouteStop(
            route_id=route.id,
            stop_id=stop.id,
            stop_order=1,
            eta=datetime(2026, 9, 28, 9, 15),
            departure_time=datetime(2026, 9, 28, 9, 30),
            distance_from_previous_miles=12.4,
            travel_duration_minutes=28,
            service_duration_minutes=15,
        )
        session.add(route_stop)
        session.commit()
        session.refresh(route_stop)

    assert route_stop.stop_order == 1
    assert route_stop.distance_from_previous_miles == 12.4
    assert route_stop.travel_duration_minutes == 28
    assert route_stop.service_duration_minutes == 15


def test_route_versions_preserve_previous_optimization_results(tmp_path):
    database_url = sqlite_url(tmp_path / "versions.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))

    with session_factory() as session:
        depot, vehicle, _stop = create_route_dependencies(session)
        route = Route(name="Morning Route", depot_id=depot.id, vehicle_id=vehicle.id)
        session.add(route)
        session.commit()
        session.refresh(route)

        first_version = RouteVersion(
            route_id=route.id,
            version_number=1,
            solver_status="optimal",
            total_distance_miles=42.5,
            total_travel_duration_minutes=96,
            total_service_duration_minutes=30,
            total_route_duration_minutes=126,
            route_metrics={"stops": 2, "payload_lbs": 500},
        )
        second_version = RouteVersion(
            route_id=route.id,
            version_number=2,
            solver_status="optimal",
            total_distance_miles=39.2,
            total_travel_duration_minutes=89,
            total_service_duration_minutes=30,
            total_route_duration_minutes=119,
            route_metrics={"stops": 2, "payload_lbs": 500},
        )
        session.add_all([first_version, second_version])
        session.commit()

        versions = (
            session.query(RouteVersion)
            .filter(RouteVersion.route_id == route.id)
            .order_by(RouteVersion.version_number)
            .all()
        )

    assert len(versions) == 2
    assert versions[0].version_number == 1
    assert versions[0].total_distance_miles == 42.5
    assert versions[1].version_number == 2
    assert versions[1].total_distance_miles == 39.2


def test_route_version_number_is_unique_per_route(tmp_path):
    database_url = sqlite_url(tmp_path / "unique_versions.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))

    with session_factory() as session:
        depot, vehicle, _stop = create_route_dependencies(session)
        route = Route(name="Morning Route", depot_id=depot.id, vehicle_id=vehicle.id)
        session.add(route)
        session.commit()
        session.refresh(route)

        session.add(
            RouteVersion(
                route_id=route.id,
                version_number=1,
                solver_status="optimal",
            )
        )
        session.commit()

        session.add(
            RouteVersion(
                route_id=route.id,
                version_number=1,
                solver_status="infeasible",
            )
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_optimization_run_links_to_route_version(tmp_path):
    database_url = sqlite_url(tmp_path / "optimization_run.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))

    with session_factory() as session:
        depot, vehicle, _stop = create_route_dependencies(session)
        route = Route(name="Morning Route", depot_id=depot.id, vehicle_id=vehicle.id)
        session.add(route)
        session.commit()
        session.refresh(route)

        version = RouteVersion(
            route_id=route.id,
            version_number=1,
            solver_status="optimal",
            total_distance_miles=42.5,
        )
        session.add(version)
        session.commit()
        session.refresh(version)

        run = OptimizationRun(
            route_id=route.id,
            route_version_id=version.id,
            solver_status="optimal",
            route_metrics={"objective": 2550},
            completed_at=datetime(2026, 9, 28, 10, 0),
        )
        session.add(run)
        session.commit()
        session.refresh(run)

    assert run.route_id == route.id
    assert run.route_version_id == version.id
    assert run.solver_status == "optimal"
    assert run.route_metrics == {"objective": 2550}
