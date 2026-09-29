import base64
import json

import pytest

from backend.vision import OllamaVisionExtractionProvider, VisionExtractionError

SAMPLE_SCREENSHOT_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def test_ollama_vision_provider_sends_structured_vision_request():
    captured = {}

    def transport(url: str, payload: dict, timeout_seconds: float) -> dict:
        captured["url"] = url
        captured["payload"] = payload
        captured["timeout_seconds"] = timeout_seconds
        return {
            "message": {
                "content": json.dumps(
                    {
                        "stops": [
                            {
                                "customer": "Acme Bakery",
                                "address": "123 Main St, Tampa, FL",
                                "stop_type": "delivery",
                                "quantity": 4,
                                "weight_lbs": 120.5,
                                "time_window": "08:00-10:00",
                                "notes": "Rear dock",
                                "confidence": 0.87,
                            }
                        ]
                    }
                )
            }
        }

    provider = OllamaVisionExtractionProvider(
        base_url="http://localhost:11434",
        model="llama3.2-vision",
        timeout_seconds=12,
        transport=transport,
    )

    stops = provider.extract_stops(SAMPLE_SCREENSHOT_BYTES, content_type="image/png")

    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["timeout_seconds"] == 12
    assert captured["payload"]["model"] == "llama3.2-vision"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["options"] == {"temperature": 0}
    assert captured["payload"]["format"]["properties"]["stops"]["type"] == "array"
    assert captured["payload"]["messages"][1]["images"] == [
        base64.b64encode(SAMPLE_SCREENSHOT_BYTES).decode("ascii")
    ]
    assert "Do not invent" in captured["payload"]["messages"][0]["content"]
    assert stops[0].address == "123 Main St, Tampa, FL"
    assert stops[0].confidence == 0.87


def test_ollama_vision_provider_preserves_uncertain_text():
    def transport(url: str, payload: dict, timeout_seconds: float) -> dict:
        return {
            "message": {
                "content": json.dumps(
                    {
                        "stops": [
                            {
                                "customer": "A?me B?kery",
                                "address": "12? Main St",
                                "stop_type": "unknown",
                                "quantity": None,
                                "weight_lbs": None,
                                "time_window": "8?-10?",
                                "notes": "partially obscured",
                                "confidence": 0.31,
                            }
                        ]
                    }
                )
            }
        }

    provider = OllamaVisionExtractionProvider(transport=transport)

    stops = provider.extract_stops(SAMPLE_SCREENSHOT_BYTES, content_type="image/png")

    assert stops[0].customer == "A?me B?kery"
    assert stops[0].address == "12? Main St"
    assert stops[0].time_window == "8?-10?"
    assert stops[0].confidence == 0.31


def test_ollama_vision_provider_rejects_non_json_response():
    def transport(url: str, payload: dict, timeout_seconds: float) -> dict:
        return {"message": {"content": "not json"}}

    provider = OllamaVisionExtractionProvider(transport=transport)

    with pytest.raises(VisionExtractionError, match="not valid JSON"):
        provider.extract_stops(SAMPLE_SCREENSHOT_BYTES, content_type="image/png")


def test_ollama_vision_provider_rejects_schema_invalid_response():
    def transport(url: str, payload: dict, timeout_seconds: float) -> dict:
        return {
            "message": {
                "content": json.dumps(
                    {
                        "stops": [
                            {
                                "customer": "Acme Bakery",
                                "address": "123 Main St",
                                "stop_type": "delivery",
                                "confidence": 1.2,
                            }
                        ]
                    }
                )
            }
        }

    provider = OllamaVisionExtractionProvider(transport=transport)

    with pytest.raises(VisionExtractionError, match="schema validation"):
        provider.extract_stops(SAMPLE_SCREENSHOT_BYTES, content_type="image/png")


def test_ollama_vision_provider_requires_image_bytes():
    provider = OllamaVisionExtractionProvider(transport=lambda url, payload, timeout: {})

    with pytest.raises(ValueError, match="Image bytes are required"):
        provider.extract_stops(b"", content_type="image/png")
