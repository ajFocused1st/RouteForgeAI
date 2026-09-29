from pathlib import Path

from fastapi.testclient import TestClient

from backend.config import Settings
from backend.database.session import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from backend.main import create_app
from backend.services.provider_status import ProviderStatusService


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_provider_status_service_reports_readable_statuses(tmp_path):
    database_url = sqlite_url(tmp_path / "status.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))
    map_data = tmp_path / "map-data"
    routing_data = tmp_path / "routing-data"
    map_data.mkdir()
    routing_data.mkdir()
    (map_data / "florida.osm.pbf").write_text("osm", encoding="utf-8")

    def transport(url: str, timeout_seconds: float) -> dict:
        if url.endswith("/api/tags"):
            return {"models": [{"name": "llama3.1"}]}
        if url.endswith("/status"):
            return {"version": "valhalla-test"}
        if url.endswith("/status.php"):
            return {"status": "ok"}
        raise RuntimeError(f"Unexpected URL {url}")

    with session_factory() as session:
        report = ProviderStatusService(
            Settings(
                database_url=database_url,
                map_data_path=str(map_data),
                routing_data_path=str(routing_data),
            ),
            session,
            transport=transport,
        ).report()

    statuses = {provider.name: provider for provider in report.providers}
    assert report.overall_status == "ok"
    assert statuses["backend"].message == "RouteForge AI backend is running."
    assert statuses["database"].status == "ok"
    assert statuses["ollama"].details["models"] == ["llama3.1"]
    assert statuses["valhalla"].details["status"]["version"] == "valhalla-test"
    assert statuses["geocoder"].status == "ok"
    assert statuses["map_data"].details["map_file_count"] == 1


def test_provider_status_service_reports_unavailable_and_warning_states(tmp_path):
    database_url = sqlite_url(tmp_path / "status-warning.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))
    map_data = tmp_path / "empty-map-data"
    routing_data = tmp_path / "empty-routing-data"
    map_data.mkdir()
    routing_data.mkdir()

    def transport(url: str, timeout_seconds: float) -> dict:
        if url.endswith("/status.php"):
            raise RuntimeError("geocoder offline")
        raise TimeoutError("service offline")

    with session_factory() as session:
        report = ProviderStatusService(
            Settings(
                database_url=database_url,
                map_data_path=str(map_data),
                routing_data_path=str(routing_data),
            ),
            session,
            transport=transport,
        ).report()

    statuses = {provider.name: provider for provider in report.providers}
    assert report.overall_status == "unavailable"
    assert statuses["ollama"].status == "unavailable"
    assert statuses["valhalla"].status == "unavailable"
    assert statuses["geocoder"].status == "warning"
    assert statuses["map_data"].status == "warning"
    assert "contain no files" in statuses["map_data"].message


def test_provider_status_endpoint_returns_structured_report(tmp_path):
    database_url = sqlite_url(tmp_path / "status-api.db")
    settings = Settings(database_url=database_url)

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/status/providers")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    provider_names = {provider["name"] for provider in body["data"]["providers"]}
    assert {
        "backend",
        "database",
        "ollama",
        "valhalla",
        "geocoder",
        "map_data",
    }.issubset(provider_names)
