from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.geocoding.provider import GeocodingProvider
from backend.models.geocode_cache import GeocodeCache
from backend.schemas.geocoding import GeocodeResult


class GeocodeCacheService:
    def __init__(self, db: Session, provider: GeocodingProvider):
        self.db = db
        self.provider = provider

    def geocode(self, address: str) -> GeocodeResult:
        normalized_address = self.provider.normalize_address(address)
        if normalized_address == "":
            return self.provider.geocode(address)

        cached = self.db.scalar(
            select(GeocodeCache).where(
                GeocodeCache.provider == self.provider.provider_name,
                GeocodeCache.normalized_address == normalized_address,
            )
        )
        if cached is not None:
            return GeocodeResult(
                original_address=cached.original_address,
                normalized_address=cached.normalized_address,
                latitude=cached.latitude,
                longitude=cached.longitude,
                confidence=1,
                status=cached.status,
                provider=cached.provider,
                message="Returned from geocode cache.",
            )

        result = self.provider.geocode(address)
        if result.normalized_address is not None:
            self.db.add(
                GeocodeCache(
                    original_address=result.original_address,
                    normalized_address=result.normalized_address,
                    latitude=result.latitude,
                    longitude=result.longitude,
                    provider=result.provider,
                    status=result.status,
                )
            )
            self.db.commit()

        return result
