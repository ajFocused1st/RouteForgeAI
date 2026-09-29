from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.responses import success_response
from backend.config import Settings, get_settings
from backend.database.session import get_db_session
from backend.geocoding import GeocodingProvider, NominatimGeocodingProvider
from backend.geocoding.cache import GeocodeCacheService
from backend.schemas.geocoding import (
    GeocodeReviewRequest,
    GeocodeReviewResult,
    GeocodeResult,
    GeocodeValidationStatus,
)

router = APIRouter(prefix="/geocoding", tags=["geocoding"])


def get_geocoding_provider(
    settings: Settings = Depends(get_settings),
) -> GeocodingProvider:
    return NominatimGeocodingProvider(user_agent=settings.app_name)


@router.post("/review-stops")
def geocode_review_stops(
    review_in: GeocodeReviewRequest,
    db: Session = Depends(get_db_session),
    provider: GeocodingProvider = Depends(get_geocoding_provider),
) -> dict:
    cache = GeocodeCacheService(db, provider)
    results = []

    for stop in review_in.stops:
        geocode_result = cache.geocode(stop.address)
        results.append(
            GeocodeReviewResult(
                row_id=stop.row_id,
                original_address=geocode_result.original_address,
                normalized_address=geocode_result.normalized_address,
                latitude=geocode_result.latitude,
                longitude=geocode_result.longitude,
                geocode_status=geocode_result.status,
                validation_status=_validation_status(geocode_result),
                confidence=geocode_result.confidence,
                provider=geocode_result.provider,
                message=geocode_result.message,
            )
        )

    return success_response(results)


def _validation_status(result: GeocodeResult) -> GeocodeValidationStatus:
    if result.status == "matched":
        return "confirmed" if result.confidence >= 0.7 else "low_confidence"

    if result.status == "ambiguous":
        return "ambiguous"

    if result.status == "not_found":
        return "not_found"

    return "user_review_required"
