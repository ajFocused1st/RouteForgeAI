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
from backend.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_customer_schema_accepts_valid_data():
    customer = CustomerCreate(
        name="Acme Supply",
        phone="813-555-0100",
        email="dispatch@example.com",
        notes="Receives deliveries at dock 2.",
    )

    assert customer.name == "Acme Supply"
    assert customer.phone == "813-555-0100"
    assert customer.email == "dispatch@example.com"
    assert customer.active is True


def test_customer_schema_allows_optional_contact_fields():
    customer = CustomerCreate(name="Walk-in Customer")

    assert customer.phone is None
    assert customer.email is None
    assert customer.notes is None


def test_customer_schema_rejects_invalid_data():
    with pytest.raises(ValidationError):
        CustomerCreate(name="")

    with pytest.raises(ValidationError):
        CustomerUpdate(email="not-an-email")


def test_initialize_database_creates_customer_table(tmp_path):
    database_url = sqlite_url(tmp_path / "customers.db")

    initialize_database(database_url)

    table_names = inspect(create_database_engine(database_url)).get_table_names()
    assert "customers" in table_names


def test_customer_model_persists_and_serializes(tmp_path):
    database_url = sqlite_url(tmp_path / "persist.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))

    with session_factory() as session:
        customer = Customer(
            name="Acme Supply",
            phone="813-555-0100",
            email="dispatch@example.com",
            notes="Receives deliveries at dock 2.",
        )
        session.add(customer)
        session.commit()
        session.refresh(customer)

        serialized = CustomerRead.model_validate(customer)

    assert serialized.id == 1
    assert serialized.name == "Acme Supply"
    assert serialized.phone == "813-555-0100"
    assert serialized.email == "dispatch@example.com"
    assert serialized.notes == "Receives deliveries at dock 2."
    assert serialized.active is True
    assert serialized.created_at is not None
    assert serialized.updated_at is not None
