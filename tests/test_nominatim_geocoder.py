from urllib.error import URLError

from backend.geocoding.nominatim import NominatimGeocodingProvider


def test_nominatim_normalizes_address_without_guessing():
    provider = NominatimGeocodingProvider(user_agent="RouteForgeAI test")

    assert provider.normalize_address("  123   Main   St  ") == "123 Main St"


def test_nominatim_returns_matched_result_from_single_candidate():
    calls = []

    def transport(url, headers, timeout_seconds):
        calls.append((url, headers, timeout_seconds))
        return [
            {
                "display_name": "123 Main St, Tampa, Florida, USA",
                "lat": "27.9506",
                "lon": "-82.4572",
                "importance": 0.87,
            }
        ]

    provider = NominatimGeocodingProvider(
        user_agent="RouteForgeAI test",
        transport=transport,
        timeout_seconds=3,
    )

    result = provider.geocode("123 Main St Tampa FL")

    assert result.status == "matched"
    assert result.normalized_address == "123 Main St, Tampa, Florida, USA"
    assert result.latitude == 27.9506
    assert result.longitude == -82.4572
    assert result.confidence == 0.87
    assert calls[0][1]["User-Agent"] == "RouteForgeAI test"
    assert calls[0][2] == 3
    assert "format=jsonv2" in calls[0][0]


def test_nominatim_cache_reuses_normalized_address_result():
    call_count = 0

    def transport(url, headers, timeout_seconds):
        nonlocal call_count
        call_count += 1
        return [
            {
                "display_name": "123 Main St, Tampa, Florida, USA",
                "lat": "27.9506",
                "lon": "-82.4572",
                "importance": 0.87,
            }
        ]

    provider = NominatimGeocodingProvider(
        user_agent="RouteForgeAI test",
        transport=transport,
    )

    first = provider.geocode(" 123 Main St ")
    second = provider.geocode("123   Main   St")

    assert first == second
    assert call_count == 1


def test_nominatim_reports_ambiguous_results_without_coordinates():
    def transport(url, headers, timeout_seconds):
        return [
            {"display_name": "Main St, Tampa", "lat": "27.1", "lon": "-82.1"},
            {"display_name": "Main St, Orlando", "lat": "28.1", "lon": "-81.1"},
        ]

    provider = NominatimGeocodingProvider(
        user_agent="RouteForgeAI test",
        transport=transport,
    )

    result = provider.geocode("Main St")

    assert result.status == "ambiguous"
    assert result.latitude is None
    assert result.longitude is None
    assert "user review required" in result.message


def test_nominatim_reports_not_found():
    provider = NominatimGeocodingProvider(
        user_agent="RouteForgeAI test",
        transport=lambda url, headers, timeout_seconds: [],
    )

    result = provider.geocode("Not A Real Address")

    assert result.status == "not_found"
    assert result.confidence == 0


def test_nominatim_handles_timeout_or_network_error():
    def transport(url, headers, timeout_seconds):
        raise URLError("timed out")

    provider = NominatimGeocodingProvider(
        user_agent="RouteForgeAI test",
        transport=transport,
    )

    result = provider.geocode("123 Main St")

    assert result.status == "provider_error"
    assert result.latitude is None
    assert result.longitude is None
    assert "timed out" in result.message
