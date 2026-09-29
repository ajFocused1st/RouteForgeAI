from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect

from backend.database.session import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from backend.models.cost_profile import CostProfile
from backend.schemas.cost_profile import (
    CostProfileCreate,
    CostProfileRead,
    CostProfileUpdate,
)


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_cost_profile_schema_accepts_valid_data():
    profile = CostProfileCreate(
        name="Local Delivery",
        operating_cost_per_mile=0.78,
        driver_hourly_rate=28,
        tolls=12.5,
        parking=8,
        route_expenses=15,
        default_service_charge=4.5,
    )

    assert profile.name == "Local Delivery"
    assert profile.operating_cost_per_mile == 0.78
    assert profile.driver_hourly_rate == 28
    assert profile.active is True


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("operating_cost_per_mile", -0.01),
        ("driver_hourly_rate", -0.01),
        ("tolls", -0.01),
        ("parking", -0.01),
        ("route_expenses", -0.01),
        ("default_service_charge", -0.01),
    ],
)
def test_cost_profile_schema_rejects_negative_money_fields(field_name, value):
    payload = {
        "name": "Invalid Cost Profile",
        "operating_cost_per_mile": 0.78,
        "driver_hourly_rate": 28,
        field_name: value,
    }

    with pytest.raises(ValidationError):
        CostProfileCreate(**payload)

    with pytest.raises(ValidationError):
        CostProfileUpdate(**{field_name: value})


def test_initialize_database_creates_cost_profile_table(tmp_path):
    database_url = sqlite_url(tmp_path / "cost_profiles.db")

    initialize_database(database_url)

    table_names = inspect(create_database_engine(database_url)).get_table_names()
    assert "cost_profiles" in table_names


def test_cost_profile_model_persists_and_serializes(tmp_path):
    database_url = sqlite_url(tmp_path / "persist.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))

    with session_factory() as session:
        profile = CostProfile(
            name="Local Delivery",
            operating_cost_per_mile=0.78,
            driver_hourly_rate=28,
            tolls=12.5,
            parking=8,
            route_expenses=15,
            default_service_charge=4.5,
        )
        session.add(profile)
        session.commit()
        session.refresh(profile)

        serialized = CostProfileRead.model_validate(profile)

    assert serialized.id == 1
    assert serialized.name == "Local Delivery"
    assert serialized.operating_cost_per_mile == 0.78
    assert serialized.driver_hourly_rate == 28
    assert serialized.tolls == 12.5
    assert serialized.parking == 8
    assert serialized.route_expenses == 15
    assert serialized.default_service_charge == 4.5
    assert serialized.active is True
    assert serialized.created_at is not None
    assert serialized.updated_at is not None
