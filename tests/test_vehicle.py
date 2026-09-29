from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from backend.database.session import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from backend.models.vehicle import Vehicle
from backend.schemas.vehicle import VehicleCreate, VehicleRead, VehicleUpdate


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_vehicle_schema_accepts_valid_data():
    vehicle = VehicleCreate(
        name="Cargo Van 1",
        max_payload_lbs=3400,
        max_volume_cubic_ft=420,
        max_route_miles=180,
        max_route_minutes=480,
    )

    assert vehicle.name == "Cargo Van 1"
    assert vehicle.max_payload_lbs == 3400
    assert vehicle.active is True


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("max_payload_lbs", -1),
        ("max_volume_cubic_ft", -1),
        ("max_route_miles", -1),
        ("max_route_minutes", -1),
    ],
)
def test_vehicle_schema_rejects_negative_capacities(field_name, value):
    payload = {
        "name": "Invalid Vehicle",
        "max_payload_lbs": 1000,
        field_name: value,
    }

    with pytest.raises(ValidationError):
        VehicleCreate(**payload)

    with pytest.raises(ValidationError):
        VehicleUpdate(**{field_name: value})


def test_initialize_database_creates_vehicle_table(tmp_path):
    database_url = sqlite_url(tmp_path / "vehicles.db")

    initialize_database(database_url)

    table_names = inspect(create_database_engine(database_url)).get_table_names()
    assert "vehicles" in table_names


def test_vehicle_model_persists_and_serializes(tmp_path):
    database_url = sqlite_url(tmp_path / "persist.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))

    with session_factory() as session:
        vehicle = Vehicle(
            name="Cargo Van 1",
            max_payload_lbs=3400,
            max_volume_cubic_ft=None,
            max_route_miles=180,
            max_route_minutes=480,
        )
        session.add(vehicle)
        session.commit()
        session.refresh(vehicle)

        serialized = VehicleRead.model_validate(vehicle)

    assert serialized.id == 1
    assert serialized.name == "Cargo Van 1"
    assert serialized.max_payload_lbs == 3400
    assert serialized.max_volume_cubic_ft is None
    assert serialized.max_route_miles == 180
    assert serialized.max_route_minutes == 480
    assert serialized.active is True
    assert serialized.created_at is not None
    assert serialized.updated_at is not None
