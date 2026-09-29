from typing import Protocol

from backend.schemas.vision import ExtractedStop


class VisionExtractionProvider(Protocol):
    """Provider contract for extracting stops from route screenshots."""

    provider_name: str

    def extract_stops(
        self,
        image: bytes,
        content_type: str | None = None,
    ) -> list[ExtractedStop]:
        """Return structured stop candidates from an image without routing them."""
