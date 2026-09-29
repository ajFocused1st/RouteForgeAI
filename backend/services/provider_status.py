import json
from collections.abc import Callable
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.schemas.status import ProviderStatusItem, ProviderStatusReport

StatusTransport = Callable[[str, float], dict]


def default_status_transport(url: str, timeout_seconds: float) -> dict:
    request = Request(url, headers={"User-Agent": "RouteForgeAI status"})
    with urlopen(request, timeout=timeout_seconds) as response:
        content_type = response.headers.get("Content-Type", "")
        body = response.read().decode("utf-8")
        if "application/json" in content_type:
            return json.loads(body or "{}")
        return {"body": body[:200]}


class ProviderStatusService:
    def __init__(
        self,
        settings: Settings,
        db: Session,
        transport: StatusTransport = default_status_transport,
        timeout_seconds: float = 3.0,
    ):
        self.settings = settings
        self.db = db
        self.transport = transport
        self.timeout_seconds = timeout_seconds

    def report(self) -> ProviderStatusReport:
        providers = [
            self._backend_status(),
            self._database_status(),
            self._ollama_status(),
            self._valhalla_status(),
            self._geocoder_status(),
            self._map_data_status(),
        ]
        return ProviderStatusReport(
            overall_status=self._overall_status(providers),
            providers=providers,
        )

    def _backend_status(self) -> ProviderStatusItem:
        return ProviderStatusItem(
            name="backend",
            status="ok",
            message=f"{self.settings.app_name} backend is running.",
            details={
                "version": self.settings.app_version,
                "environment": self.settings.environment,
            },
        )

    def _database_status(self) -> ProviderStatusItem:
        try:
            self.db.execute(text("SELECT 1")).scalar_one()
        except Exception as exc:
            return ProviderStatusItem(
                name="database",
                status="unavailable",
                message="Database connection failed.",
                details={"error": str(exc), "database_url": self.settings.database_url},
            )

        return ProviderStatusItem(
            name="database",
            status="ok",
            message="Database connection is available.",
            details={"database_url": self.settings.database_url},
        )

    def _ollama_status(self) -> ProviderStatusItem:
        url = f"{self.settings.ollama_url.rstrip('/')}/api/tags"
        try:
            data = self.transport(url, self.timeout_seconds)
        except (TimeoutError, HTTPError, URLError, OSError, RuntimeError) as exc:
            return ProviderStatusItem(
                name="ollama",
                status="unavailable",
                message="Ollama is not reachable.",
                details={"url": self.settings.ollama_url, "error": str(exc)},
            )

        models = [
            model.get("name")
            for model in data.get("models", [])
            if isinstance(model, dict) and model.get("name")
        ]
        return ProviderStatusItem(
            name="ollama",
            status="ok",
            message="Ollama is reachable.",
            details={
                "url": self.settings.ollama_url,
                "models": models,
                "ai_model": self.settings.ollama_ai_model,
                "vision_model": self.settings.ollama_vision_model,
            },
        )

    def _valhalla_status(self) -> ProviderStatusItem:
        url = f"{self.settings.valhalla_url.rstrip('/')}/status"
        try:
            data = self.transport(url, self.timeout_seconds)
        except (TimeoutError, HTTPError, URLError, OSError, RuntimeError) as exc:
            return ProviderStatusItem(
                name="valhalla",
                status="unavailable",
                message="Valhalla routing service is not reachable.",
                details={"url": self.settings.valhalla_url, "error": str(exc)},
            )

        return ProviderStatusItem(
            name="valhalla",
            status="ok",
            message="Valhalla routing service is reachable.",
            details={
                "url": self.settings.valhalla_url,
                "costing": self.settings.valhalla_costing,
                "status": data,
            },
        )

    def _geocoder_status(self) -> ProviderStatusItem:
        url = f"{self.settings.geocoder_url.rstrip('/')}/status.php"
        try:
            self.transport(url, self.timeout_seconds)
        except (TimeoutError, HTTPError, URLError, OSError, RuntimeError) as exc:
            return ProviderStatusItem(
                name="geocoder",
                status="warning",
                message="Configured geocoder could not be reached.",
                details={
                    "provider": "nominatim",
                    "url": self.settings.geocoder_url,
                    "error": str(exc),
                },
            )

        return ProviderStatusItem(
            name="geocoder",
            status="ok",
            message="Configured Nominatim geocoder is reachable.",
            details={"provider": "nominatim", "url": self.settings.geocoder_url},
        )

    def _map_data_status(self) -> ProviderStatusItem:
        map_path = Path(self.settings.map_data_path)
        routing_path = Path(self.settings.routing_data_path)
        map_files = self._file_count(map_path)
        routing_files = self._file_count(routing_path)

        if not map_path.exists() or not routing_path.exists():
            return ProviderStatusItem(
                name="map_data",
                status="unavailable",
                message="Map or routing data directory is missing.",
                details={
                    "map_data_path": str(map_path),
                    "routing_data_path": str(routing_path),
                    "map_data_exists": map_path.exists(),
                    "routing_data_exists": routing_path.exists(),
                },
            )

        if map_files == 0 and routing_files == 0:
            return ProviderStatusItem(
                name="map_data",
                status="warning",
                message="Map and routing data directories exist but contain no files.",
                details={
                    "map_data_path": str(map_path),
                    "routing_data_path": str(routing_path),
                    "map_file_count": map_files,
                    "routing_file_count": routing_files,
                },
            )

        return ProviderStatusItem(
            name="map_data",
            status="ok",
            message="Local map or routing data files are present.",
            details={
                "map_data_path": str(map_path),
                "routing_data_path": str(routing_path),
                "map_file_count": map_files,
                "routing_file_count": routing_files,
            },
        )

    def _file_count(self, path: Path) -> int:
        if not path.exists() or not path.is_dir():
            return 0
        return sum(1 for candidate in path.rglob("*") if candidate.is_file())

    def _overall_status(
        self,
        providers: list[ProviderStatusItem],
    ) -> str:
        if any(provider.status == "unavailable" for provider in providers):
            return "unavailable"
        if any(provider.status == "warning" for provider in providers):
            return "warning"
        return "ok"
