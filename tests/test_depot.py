from datetime import time
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from backend.database.session import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from backend.models.depot import Depot
from backend.schemas.depot import DepotCreate, DepotRead, DepotUpdate


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_depot_schema_accepts_valid_data():
    depot = DepotCreate(
        name="Main Depot",
        address="123 Dispatch Way, Tampa, FL",
        latitude=27.9506,
        longitude=-82.4572,
        default_start_time=time(7, 30),
    )

    assert depot.name == "Main Depot"
    assert depot.active is True
    assert depot.default_start_time == time(7, 30)


def test_depot_schema_rejects_invalid_coordinates():
    with pytest.raises(ValidationError):
        DepotCreate(
            name="Bad Depot",
            address="Unknown",
            latitude=91,
            longitude=-82.4572,
        )

    with pytest.raises(ValidationError):
        DepotUpdate(longitude=-181)


def test_initialize_database_creates_depot_table(tmp_path):
    database_url = sqlite_url(tmp_path / "depots.db")

    initialize_database(database_url)

    table_names = inspect(create_database_engine(database_url)).get_table_names()
    assert "depots" in table_names


def test_depot_model_persists_and_serializes(tmp_path):
    database_url = sqlite_url(tmp_path / "persist.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))

    with session_factory() as session:
        depot = Depot(
            name="Main Depot",
            address="123 Dispatch Way, Tampa, FL",
            latitude=27.9506,
            longitude=-82.4572,
            default_start_time=time(8, 15),
        )
        session.add(depot)
        session.commit()
        session.refresh(depot)

        serialized = DepotRead.model_validate(depot)

    assert serialized.id == 1
    assert serialized.name == "Main Depot"
    assert serialized.default_start_time == time(8, 15)
    assert serialized.active is True
    assert serialized.created_at is not None
    assert serialized.updated_at is not None
