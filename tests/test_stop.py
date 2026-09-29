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
from backend.models.customer import Customer
from backend.models.stop import Stop
from backend.schemas.stop import StopCreate, StopRead, StopUpdate


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def valid_stop_payload() -> dict:
    return {
        "name": "Dock Pickup",
        "address": "123 Dispatch Way, Tampa, FL",
        "normalized_address": "123 Dispatch Way, Tampa, FL 33602",
        "latitude": 27.9506,
        "longitude": -82.4572,
        "stop_type": "pickup",
        "quantity": 2,
        "weight_lbs": 125.5,
        "service_minutes": 15,
        "priority": 1,
        "earliest_time": time(8, 0),
        "latest_time": time(12, 0),
        "special_instructions": "Use loading dock.",
        "address_status": "confirmed",
    }


def test_stop_schema_accepts_valid_data():
    stop = StopCreate(**valid_stop_payload())

    assert stop.name == "Dock Pickup"
    assert stop.stop_type == "pickup"
    assert stop.active is True


@pytest.mark.parametrize("stop_type", ["pickup", "delivery", "pickup_delivery"])
def test_stop_schema_accepts_supported_stop_types(stop_type):
    payload = valid_stop_payload()
    payload["stop_type"] = stop_type

    assert StopCreate(**payload).stop_type == stop_type


def test_stop_schema_rejects_invalid_stop_type():
    payload = valid_stop_payload()
    payload["stop_type"] = "return"

    with pytest.raises(ValidationError):
        StopCreate(**payload)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("latitude", 91),
        ("longitude", -181),
        ("quantity", -1),
        ("weight_lbs", -1),
        ("service_minutes", -1),
        ("priority", -1),
    ],
)
def test_stop_schema_rejects_invalid_values(field_name, value):
    payload = valid_stop_payload()
    payload[field_name] = value

    with pytest.raises(ValidationError):
        StopCreate(**payload)

    with pytest.raises(ValidationError):
        StopUpdate(**{field_name: value})


def test_stop_schema_rejects_invalid_time_window():
    payload = valid_stop_payload()
    payload["earliest_time"] = time(13, 0)
    payload["latest_time"] = time(12, 0)

    with pytest.raises(ValidationError):
        StopCreate(**payload)

    with pytest.raises(ValidationError):
        StopUpdate(earliest_time=time(13, 0), latest_time=time(12, 0))


def test_initialize_database_creates_stop_table(tmp_path):
    database_url = sqlite_url(tmp_path / "stops.db")

    initialize_database(database_url)

    table_names = inspect(create_database_engine(database_url)).get_table_names()
    assert "stops" in table_names


def test_stop_model_persists_and_serializes(tmp_path):
    database_url = sqlite_url(tmp_path / "persist.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))

    with session_factory() as session:
        customer = Customer(name="Acme Supply")
        session.add(customer)
        session.commit()
        session.refresh(customer)

        stop = Stop(customer_id=customer.id, **valid_stop_payload())
        session.add(stop)
        session.commit()
        session.refresh(stop)

        serialized = StopRead.model_validate(stop)

    assert serialized.id == 1
    assert serialized.customer_id == 1
    assert serialized.name == "Dock Pickup"
    assert serialized.stop_type == "pickup"
    assert serialized.quantity == 2
    assert serialized.weight_lbs == 125.5
    assert serialized.service_minutes == 15
    assert serialized.priority == 1
    assert serialized.address_status == "confirmed"
    assert serialized.active is True
    assert serialized.created_at is not None
    assert serialized.updated_at is not None
