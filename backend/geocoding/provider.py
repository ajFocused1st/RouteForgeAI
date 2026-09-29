from typing import Protocol

from backend.schemas.geocoding import GeocodeResult


class GeocodingProvider(Protocol):
    """Provider contract for address normalization and geocoding."""

    provider_name: str

    def normalize_address(self, address: str) -> str:
        """Return a normalized address string without guessing missing details."""

    def geocode(self, address: str) -> GeocodeResult:
        """Return coordinates, confidence, and status for an address."""
