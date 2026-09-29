import pytest
from pydantic import ValidationError

from backend.schemas.vision import ExtractedStop
from backend.vision import VisionExtractionProvider


class LocalTestVisionProvider:
    provider_name = "local-test-vision"

    def extract_stops(
        self,
        image: bytes,
        content_type: str | None = None,
    ) -> list[ExtractedStop]:
        assert image
        assert content_type == "image/png"
        return [
            ExtractedStop(
                customer="Acme Bakery",
                address="123 Main St, Tampa, FL",
                stop_type="delivery",
                quantity=4,
                weight_lbs=120.5,
                time_window="08:00-10:00",
                notes="Rear dock",
                confidence=0.87,
            )
        ]


def test_vision_extraction_provider_contract_returns_extracted_stops():
    provider: VisionExtractionProvider = LocalTestVisionProvider()

    stops = provider.extract_stops(b"fake image bytes", content_type="image/png")

    assert provider.provider_name == "local-test-vision"
    assert len(stops) == 1
    assert stops[0].customer == "Acme Bakery"
    assert stops[0].address == "123 Main St, Tampa, FL"
    assert stops[0].stop_type == "delivery"
    assert stops[0].quantity == 4
    assert stops[0].weight_lbs == 120.5
    assert stops[0].time_window == "08:00-10:00"
    assert stops[0].notes == "Rear dock"
    assert stops[0].confidence == 0.87


def test_extracted_stop_allows_uncertain_fields_without_guessing():
    stop = ExtractedStop(confidence=0.2)

    assert stop.customer is None
    assert stop.address is None
    assert stop.stop_type == "unknown"
    assert stop.quantity is None
    assert stop.weight_lbs is None
    assert stop.time_window is None
    assert stop.notes is None


def test_extracted_stop_rejects_invalid_values():
    with pytest.raises(ValidationError):
        ExtractedStop(confidence=1.5)

    with pytest.raises(ValidationError):
        ExtractedStop(stop_type="appointment", confidence=0.7)

    with pytest.raises(ValidationError):
        ExtractedStop(quantity=-1, confidence=0.7)

    with pytest.raises(ValidationError):
        ExtractedStop(weight_lbs=-1, confidence=0.7)
