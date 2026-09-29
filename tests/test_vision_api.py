import base64

from fastapi.testclient import TestClient

from backend.api.vision import get_vision_provider
from backend.config import Settings
from backend.main import create_app
from backend.schemas.vision import ExtractedStop


class DeterministicVisionProvider:
    provider_name = "deterministic-vision"

    def extract_stops(
        self,
        image: bytes,
        content_type: str | None = None,
    ) -> list[ExtractedStop]:
        assert image == b"image bytes"
        assert content_type == "image/png"
        return [
            ExtractedStop(
                customer="Acme Bakery",
                address="123 Main St",
                stop_type="delivery",
                weight_lbs=25,
                time_window="08:00-10:00",
                notes="Dock",
                confidence=0.82,
            )
        ]


def test_extract_screenshot_stops_returns_structured_stops():
    app = create_app()
    app.dependency_overrides[get_vision_provider] = lambda: DeterministicVisionProvider()

    with TestClient(app) as client:
        response = client.post(
            "/api/vision/extract",
            json={
                "image_base64": base64.b64encode(b"image bytes").decode("ascii"),
                "content_type": "image/png",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["stops"][0]["customer"] == "Acme Bakery"
    assert data["stops"][0]["address"] == "123 Main St"
    assert data["stops"][0]["confidence"] == 0.82


def test_extract_screenshot_stops_rejects_invalid_base64():
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/vision/extract",
            json={"image_base64": "not base64", "content_type": "image/png"},
        )

    assert response.status_code == 422
    assert "image_base64" in response.json()["error"]["message"]


def test_extract_screenshot_stops_rejects_unsupported_content_type():
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/vision/extract",
            json={
                "image_base64": base64.b64encode(b"image bytes").decode("ascii"),
                "content_type": "text/plain",
            },
        )

    assert response.status_code == 415
    assert "content_type" in response.json()["error"]["message"]


def test_extract_screenshot_stops_rejects_oversized_image_before_provider_call():
    app = create_app(Settings(max_vision_image_bytes=4))
    provider = DeterministicVisionProvider()

    def fail_extract_stops(image: bytes, content_type: str | None = None):
        raise AssertionError("Vision extraction should not be called.")

    provider.extract_stops = fail_extract_stops
    app.dependency_overrides[get_vision_provider] = lambda: provider

    with TestClient(app) as client:
        response = client.post(
            "/api/vision/extract",
            json={
                "image_base64": base64.b64encode(b"image bytes").decode("ascii"),
                "content_type": "image/png",
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 413
    assert "Image is too large" in response.json()["error"]["message"]
