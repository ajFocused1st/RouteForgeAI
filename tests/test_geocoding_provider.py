import pytest
from pydantic import ValidationError

from backend.geocoding import GeocodingProvider
from backend.schemas.geocoding import GeocodeResult


class LocalTestGeocoder:
    provider_name = "local-test"

    def normalize_address(self, address: str) -> str:
        return " ".join(address.strip().upper().split())

    def geocode(self, address: str) -> GeocodeResult:
        normalized_address = self.normalize_address(address)
        return GeocodeResult(
            original_address=address,
            normalized_address=normalized_address,
            latitude=27.9506,
            longitude=-82.4572,
            confidence=0.92,
            status="matched",
            provider=self.provider_name,
        )


def test_geocoding_provider_contract_supports_normalize_and_geocode():
    provider: GeocodingProvider = LocalTestGeocoder()

    assert provider.normalize_address("  123   main st  ") == "123 MAIN ST"

    result = provider.geocode("123 main st")
    assert result.provider == "local-test"
    assert result.status == "matched"
    assert result.confidence == 0.92
    assert result.latitude == 27.9506
    assert result.longitude == -82.4572


def test_geocode_result_supports_ambiguous_status_without_coordinates():
    result = GeocodeResult(
        original_address="Main Street",
        normalized_address=None,
        latitude=None,
        longitude=None,
        confidence=0.25,
        status="ambiguous",
        provider="local-test",
        message="Multiple candidate matches.",
    )

    assert result.status == "ambiguous"
    assert result.latitude is None
    assert result.longitude is None


def test_geocode_result_rejects_invalid_confidence_and_status():
    with pytest.raises(ValidationError):
        GeocodeResult(
            original_address="123 Main St",
            confidence=1.5,
            status="matched",
            provider="local-test",
        )

    with pytest.raises(ValidationError):
        GeocodeResult(
            original_address="123 Main St",
            confidence=0.8,
            status="guessed",
            provider="local-test",
        )
