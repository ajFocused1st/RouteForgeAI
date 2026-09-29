from typing import Literal

from pydantic import BaseModel, Field

ExtractedStopType = Literal["pickup", "delivery", "pickup_delivery", "unknown"]


class ExtractedStop(BaseModel):
    customer: str | None = Field(default=None, min_length=1)
    address: str | None = Field(default=None, min_length=1)
    stop_type: ExtractedStopType = "unknown"
    quantity: float | None = Field(default=None, ge=0)
    weight_lbs: float | None = Field(default=None, ge=0)
    time_window: str | None = Field(default=None, min_length=1)
    notes: str | None = Field(default=None, min_length=1)
    confidence: float = Field(ge=0, le=1)


class VisionExtractionRequest(BaseModel):
    image_base64: str = Field(min_length=1)
    content_type: str | None = None


class VisionExtractionResult(BaseModel):
    stops: list[ExtractedStop] = Field(default_factory=list)
