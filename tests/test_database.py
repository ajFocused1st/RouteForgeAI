from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from backend.config import Settings
from backend.database.session import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from backend.main import create_app


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_database_engine_connects_to_sqlite(tmp_path):
    engine = create_database_engine(sqlite_url(tmp_path / "connectivity.db"))

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()

    assert result == 1


def test_database_session_executes_queries(tmp_path):
    engine = create_database_engine(sqlite_url(tmp_path / "session.db"))
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        result = session.execute(text("SELECT 1")).scalar_one()

    assert result == 1


def test_initialize_database_creates_configured_sqlite_file(tmp_path):
    database_path = tmp_path / "initialized.db"

    initialize_database(sqlite_url(database_path))

    assert database_path.exists()
    table_names = inspect(create_database_engine(sqlite_url(database_path))).get_table_names()
    assert "customers" in table_names
    assert "cost_profiles" in table_names
    assert "depots" in table_names
    assert "geocode_cache" in table_names
    assert "optimization_runs" in table_names
    assert "route_stops" in table_names
    assert "route_versions" in table_names
    assert "routes" in table_names
    assert "routing_matrix_cache" in table_names
    assert "stops" in table_names
    assert "vehicles" in table_names


def test_app_startup_initializes_configured_database(tmp_path):
    database_path = tmp_path / "startup.db"
    settings = Settings(database_url=sqlite_url(database_path))

    with TestClient(create_app(settings)):
        pass

    assert database_path.exists()
