import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.schemas.geocoding import GeocodeResult

Transport = Callable[[str, dict[str, str], float], list[dict]]


def _default_transport(url: str, headers: dict[str, str], timeout_seconds: float) -> list[dict]:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout_seconds) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


@dataclass
class NominatimGeocodingProvider:
    user_agent: str
    base_url: str = "https://nominatim.openstreetmap.org"
    timeout_seconds: float = 5.0
    min_request_interval_seconds: float = 1.0
    result_limit: int = 2
    transport: Transport = _default_transport
    provider_name: str = "nominatim"
    _cache: dict[str, GeocodeResult] = field(default_factory=dict)
    _last_request_at: float | None = None

    def normalize_address(self, address: str) -> str:
        return " ".join(address.strip().split())

    def geocode(self, address: str) -> GeocodeResult:
        normalized_address = self.normalize_address(address)
        if normalized_address == "":
            return GeocodeResult(
                original_address=address,
                normalized_address=None,
                latitude=None,
                longitude=None,
                confidence=0,
                status="invalid",
                provider=self.provider_name,
                message="Address is required.",
            )

        cache_key = normalized_address.casefold()
        cached_result = self._cache.get(cache_key)
        if cached_result is not None:
            return cached_result.model_copy()

        try:
            self._wait_for_rate_limit()
            candidates = self.transport(
                self._search_url(normalized_address),
                {"User-Agent": self.user_agent},
                self.timeout_seconds,
            )
            self._last_request_at = time.monotonic()
        except (TimeoutError, HTTPError, URLError, OSError) as exc:
            return GeocodeResult(
                original_address=address,
                normalized_address=normalized_address,
                latitude=None,
                longitude=None,
                confidence=0,
                status="provider_error",
                provider=self.provider_name,
                message=str(exc),
            )

        result = self._result_from_candidates(address, normalized_address, candidates)
        self._cache[cache_key] = result
        return result.model_copy()

    def _search_url(self, address: str) -> str:
        query = urlencode(
            {
                "q": address,
                "format": "jsonv2",
                "addressdetails": 1,
                "limit": self.result_limit,
            }
        )
        return f"{self.base_url.rstrip('/')}/search?{query}"

    def _wait_for_rate_limit(self) -> None:
        if self._last_request_at is None:
            return

        elapsed = time.monotonic() - self._last_request_at
        remaining = self.min_request_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _result_from_candidates(
        self,
        original_address: str,
        normalized_address: str,
        candidates: list[dict],
    ) -> GeocodeResult:
        if not candidates:
            return GeocodeResult(
                original_address=original_address,
                normalized_address=normalized_address,
                latitude=None,
                longitude=None,
                confidence=0,
                status="not_found",
                provider=self.provider_name,
                message="No geocoding candidates found.",
            )

        if len(candidates) > 1:
            return GeocodeResult(
                original_address=original_address,
                normalized_address=normalized_address,
                latitude=None,
                longitude=None,
                confidence=self._confidence(candidates[0]),
                status="ambiguous",
                provider=self.provider_name,
                message="Multiple geocoding candidates found; user review required.",
            )

        candidate = candidates[0]
        return GeocodeResult(
            original_address=original_address,
            normalized_address=str(candidate.get("display_name") or normalized_address),
            latitude=float(candidate["lat"]),
            longitude=float(candidate["lon"]),
            confidence=self._confidence(candidate),
            status="matched",
            provider=self.provider_name,
        )

    def _confidence(self, candidate: dict) -> float:
        importance = candidate.get("importance")
        if isinstance(importance, int | float):
            return max(0, min(float(importance), 1))
        return 0.5
