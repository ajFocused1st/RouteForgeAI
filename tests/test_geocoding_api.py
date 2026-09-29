from pathlib import Path

from fastapi.testclient import TestClient

from backend.api.geocoding import get_geocoding_provider
from backend.config import Settings
from backend.database.session import (
    create_database_engine,
    create_session_factory,
    get_db_session,
    initialize_database,
)
from backend.main import create_app
from backend.schemas.geocoding import GeocodeResult


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


class ReviewGeocoder:
    provider_name = "review-test"

    def normalize_address(self, address: str) -> str:
        return " ".join(address.strip().split())

    def geocode(self, address: str) -> GeocodeResult:
        normalized_address = self.normalize_address(address)
        if normalized_address == "":
            return GeocodeResult(
                original_address=address,
                confidence=0,
                status="invalid",
                provider=self.provider_name,
                message="Address is required.",
            )

        if "Ambiguous" in normalized_address:
            return GeocodeResult(
                original_address=address,
                normalized_address=normalized_address,
                latitude=None,
                longitude=None,
                confidence=0.45,
                status="ambiguous",
                provider=self.provider_name,
                message="Multiple candidates.",
            )

        if "Missing" in normalized_address:
            return GeocodeResult(
                original_address=address,
                normalized_address=normalized_address,
                latitude=None,
                longitude=None,
                confidence=0,
                status="not_found",
                provider=self.provider_name,
            )

        if "Low" in normalized_address:
            return GeocodeResult(
                original_address=address,
                normalized_address=f"{normalized_address}, Tampa, FL",
                latitude=27.9506,
                longitude=-82.4572,
                confidence=0.52,
                status="matched",
                provider=self.provider_name,
            )

        return GeocodeResult(
            original_address=address,
            normalized_address=f"{normalized_address}, Tampa, FL",
            latitude=27.9506,
            longitude=-82.4572,
            confidence=0.91,
            status="matched",
            provider=self.provider_name,
        )


def test_geocode_review_stops_marks_confirmed_and_uncertain_addresses(tmp_path):
    database_url = sqlite_url(tmp_path / "geocoding_api.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))
    app = create_app(Settings(database_url=database_url))

    def override_db_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_geocoding_provider] = lambda: ReviewGeocoder()

    with TestClient(app) as client:
        response = client.post(
            "/api/geocoding/review-stops",
            json={
                "stops": [
                    {"row_id": "row-1", "address": " 123 Main St "},
                    {"row_id": "row-2", "address": "Low Confidence Rd"},
                    {"row_id": "row-3", "address": "Ambiguous Main St"},
                    {"row_id": "row-4", "address": "Missing Place"},
                ]
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert [row["row_id"] for row in data] == ["row-1", "row-2", "row-3", "row-4"]
    assert data[0]["normalized_address"] == "123 Main St, Tampa, FL"
    assert data[0]["latitude"] == 27.9506
    assert data[0]["longitude"] == -82.4572
    assert data[0]["validation_status"] == "confirmed"
    assert data[1]["validation_status"] == "low_confidence"
    assert data[2]["validation_status"] == "ambiguous"
    assert data[2]["latitude"] is None
    assert data[3]["validation_status"] == "not_found"
    assert data[3]["longitude"] is None
