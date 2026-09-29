from pathlib import Path

from sqlalchemy import inspect, select

from backend.database.session import (
    create_database_engine,
    create_session_factory,
    initialize_database,
)
from backend.geocoding.cache import GeocodeCacheService
from backend.models.geocode_cache import GeocodeCache
from backend.schemas.geocoding import GeocodeResult


class CountingGeocoder:
    provider_name = "counting-test"

    def __init__(self):
        self.calls = 0

    def normalize_address(self, address: str) -> str:
        return " ".join(address.strip().split())

    def geocode(self, address: str) -> GeocodeResult:
        self.calls += 1
        normalized_address = self.normalize_address(address)
        return GeocodeResult(
            original_address=address,
            normalized_address=normalized_address,
            latitude=27.9506,
            longitude=-82.4572,
            confidence=0.9,
            status="matched",
            provider=self.provider_name,
        )


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def test_initialize_database_creates_geocode_cache_table(tmp_path):
    database_url = sqlite_url(tmp_path / "cache.db")

    initialize_database(database_url)

    table_names = inspect(create_database_engine(database_url)).get_table_names()
    assert "geocode_cache" in table_names


def test_geocode_cache_avoids_repeated_lookup_for_normalized_address(tmp_path):
    database_url = sqlite_url(tmp_path / "cache_lookup.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))
    provider = CountingGeocoder()

    with session_factory() as session:
        cache = GeocodeCacheService(session, provider)
        first = cache.geocode(" 123 Main St ")
        second = cache.geocode("123   Main   St")

        rows = session.scalars(select(GeocodeCache)).all()

    assert provider.calls == 1
    assert len(rows) == 1
    assert rows[0].original_address == " 123 Main St "
    assert rows[0].normalized_address == "123 Main St"
    assert rows[0].latitude == 27.9506
    assert rows[0].longitude == -82.4572
    assert rows[0].provider == "counting-test"
    assert rows[0].status == "matched"
    assert rows[0].timestamp is not None
    assert first.status == "matched"
    assert second.status == "matched"
    assert second.message == "Returned from geocode cache."


def test_geocode_cache_is_scoped_by_provider(tmp_path):
    database_url = sqlite_url(tmp_path / "provider_scope.db")
    initialize_database(database_url)
    session_factory = create_session_factory(create_database_engine(database_url))
    first_provider = CountingGeocoder()
    second_provider = CountingGeocoder()
    second_provider.provider_name = "other-provider"

    with session_factory() as session:
        GeocodeCacheService(session, first_provider).geocode("123 Main St")
        GeocodeCacheService(session, second_provider).geocode("123 Main St")
        rows = session.scalars(select(GeocodeCache)).all()

    assert first_provider.calls == 1
    assert second_provider.calls == 1
    assert len(rows) == 2
    assert {row.provider for row in rows} == {"counting-test", "other-provider"}
