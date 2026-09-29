import pytest

from backend.routing import RoutingProvider
from backend.routing.valhalla import KM_TO_MILES, ValhallaRoutingProvider
from backend.schemas.routing import Coordinate


def tampa_locations() -> list[Coordinate]:
    return [
        Coordinate(latitude=27.9506, longitude=-82.4572),
        Coordinate(latitude=27.9642, longitude=-82.4526),
    ]


def test_valhalla_provider_matches_routing_provider_contract():
    provider: RoutingProvider = ValhallaRoutingProvider(
        transport=lambda url, payload, timeout_seconds: {
            "sources_to_targets": [
                [{"time": 0, "distance": 0}, {"time": 600, "distance": 10}],
                [{"time": 620, "distance": 11}, {"time": 0, "distance": 0}],
            ]
        }
    )

    matrix = provider.travel_time_matrix(tampa_locations())

    assert matrix.durations_minutes == [[0, 10], [pytest.approx(10.333333), 0]]


def test_valhalla_health_check_uses_status_endpoint():
    calls = []

    def transport(url, payload, timeout_seconds):
        calls.append((url, payload, timeout_seconds))
        return {"version": "3.5.0", "tileset_last_modified": 123}

    provider = ValhallaRoutingProvider(
        base_url="http://valhalla.test",
        timeout_seconds=4,
        transport=transport,
    )

    result = provider.health_check()

    assert result["version"] == "3.5.0"
    assert calls == [("http://valhalla.test/status", None, 4)]


def test_valhalla_matrix_request_maps_time_and_distance_units():
    payloads = []

    def transport(url, payload, timeout_seconds):
        payloads.append(payload)
        return {
            "sources_to_targets": [
                [{"time": 0, "distance": 0}, {"time": 600, "distance": 10}],
                [{"time": 620, "distance": 11}, {"time": 0, "distance": 0}],
            ]
        }

    provider = ValhallaRoutingProvider(transport=transport)

    travel_times = provider.travel_time_matrix(tampa_locations())
    distances = provider.distance_matrix(tampa_locations())

    assert travel_times.durations_minutes[0][1] == 10
    assert distances.distances_miles[0][1] == pytest.approx(10 * KM_TO_MILES)
    assert payloads[0]["costing"] == "auto"
    assert payloads[0]["sources"] == [
        {"lat": 27.9506, "lon": -82.4572},
        {"lat": 27.9642, "lon": -82.4526},
    ]


def test_valhalla_route_request_maps_geometry_and_legs():
    def transport(url, payload, timeout_seconds):
        assert url.endswith("/route")
        assert payload["directions_options"] == {"units": "miles"}
        return {
            "trip": {
                "legs": [
                    {
                        "shape": "encoded_polyline",
                        "summary": {"length": 4.2, "time": 900},
                    }
                ]
            }
        }

    provider = ValhallaRoutingProvider(transport=transport)
    locations = tampa_locations()

    geometry = provider.route_geometry(locations)
    legs = provider.route_legs(locations)

    assert geometry.polyline == "encoded_polyline"
    assert len(legs) == 1
    assert legs[0].start == locations[0]
    assert legs[0].end == locations[1]
    assert legs[0].distance_miles == 4.2
    assert legs[0].travel_duration_minutes == 15


def test_valhalla_route_requires_two_locations():
    provider = ValhallaRoutingProvider(transport=lambda url, payload, timeout: {})

    with pytest.raises(ValueError):
        provider.route_geometry([tampa_locations()[0]])
