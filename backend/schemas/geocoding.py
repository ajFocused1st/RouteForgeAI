from typing import Literal

from pydantic import BaseModel, Field

GeocodeStatus = Literal[
    "matched",
    "ambiguous",
    "not_found",
    "invalid",
    "provider_error",
]


class GeocodeResult(BaseModel):
    original_address: str = Field(min_length=1)
    normalized_address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    confidence: float = Field(ge=0, le=1)
    status: GeocodeStatus
    provider: str = Field(min_length=1)
    message: str | None = None


GeocodeValidationStatus = Literal[
    "confirmed",
    "low_confidence",
    "ambiguous",
    "not_found",
    "user_review_required",
]


class GeocodeReviewStop(BaseModel):
    row_id: str = Field(min_length=1)
    customer: str | None = None
    address: str = Field(min_length=1)
    stop_type: str | None = None
    weight_lbs: float | None = Field(default=None, ge=0)
    time_window: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class GeocodeReviewRequest(BaseModel):
    stops: list[GeocodeReviewStop] = Field(default_factory=list)


class GeocodeReviewResult(BaseModel):
    row_id: str
    original_address: str
    normalized_address: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    geocode_status: GeocodeStatus
    validation_status: GeocodeValidationStatus
    confidence: float
    provider: str
    message: str | None = None
