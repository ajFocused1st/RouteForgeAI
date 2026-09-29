import base64
import json
from collections.abc import Callable
from dataclasses import dataclass
from json import JSONDecodeError
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from backend.schemas.vision import ExtractedStop

OllamaTransport = Callable[[str, dict, float], dict]


class VisionExtractionError(RuntimeError):
    """Raised when local vision extraction cannot produce valid structured data."""


class _OllamaStopExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stops: list[ExtractedStop] = Field(default_factory=list)


def _default_transport(url: str, payload: dict, timeout_seconds: float) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


@dataclass
class OllamaVisionExtractionProvider:
    base_url: str = "http://127.0.0.1:11434"
    model: str = "llama3.2-vision"
    timeout_seconds: float = 60.0
    transport: OllamaTransport = _default_transport
    provider_name: str = "ollama"

    def extract_stops(
        self,
        image: bytes,
        content_type: str | None = None,
    ) -> list[ExtractedStop]:
        if not image:
            raise ValueError("Image bytes are required for vision extraction.")

        try:
            response = self.transport(
                f"{self.base_url.rstrip('/')}/api/chat",
                self._payload(image, content_type),
                self.timeout_seconds,
            )
        except (TimeoutError, HTTPError, URLError, OSError) as exc:
            raise VisionExtractionError(f"Ollama vision request failed: {exc}") from exc

        return self._parse_response(response)

    def _payload(self, image: bytes, content_type: str | None) -> dict:
        return {
            "model": self.model,
            "stream": False,
            "format": _OllamaStopExtractionResponse.model_json_schema(),
            "options": {"temperature": 0},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You extract delivery route stop lists from screenshots. "
                        "Return only JSON that matches the provided schema. "
                        "Do not invent, complete, normalize, geocode, or guess "
                        "addresses. Preserve uncertain text exactly as visible in "
                        "the screenshot. Use null for unreadable fields and low "
                        "confidence for uncertain rows."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Extract each visible stop row from this screenshot. "
                        "Fields: customer, address, stop_type, quantity, "
                        "weight_lbs, time_window, notes, confidence. "
                        "Allowed stop_type values are pickup, delivery, "
                        "pickup_delivery, or unknown. If text is partial or "
                        "uncertain, preserve the partial text and lower confidence."
                        f" Image content type: {content_type or 'unknown'}."
                    ),
                    "images": [base64.b64encode(image).decode("ascii")],
                },
            ],
        }

    def _parse_response(self, response: dict) -> list[ExtractedStop]:
        content = response.get("message", {}).get("content")
        if not isinstance(content, str):
            raise VisionExtractionError("Ollama response did not include message content.")

        try:
            data = json.loads(content)
        except JSONDecodeError as exc:
            raise VisionExtractionError("Ollama response was not valid JSON.") from exc

        try:
            extracted = _OllamaStopExtractionResponse.model_validate(data)
        except ValidationError as exc:
            raise VisionExtractionError("Ollama response failed schema validation.") from exc

        return extracted.stops
