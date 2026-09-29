import os

import pytest

from backend.routing.valhalla import ValhallaRoutingProvider
from backend.schemas.routing import Coordinate


def valhalla_or_skip() -> ValhallaRoutingProvider:
    provider = ValhallaRoutingProvider(
        base_url=os.getenv("ROUTEFORGE_VALHALLA_URL", "http://127.0.0.1:8002"),
        timeout_seconds=2,
    )
    try:
        provider.health_check()
    except RuntimeError as exc:
        pytest.skip(f"Valhalla is not running: {exc}")
    return provider


def florida_locations() -> list[Coordinate]:
    return [
        Coordinate(latitude=27.9506, longitude=-82.4572),
        Coordinate(latitude=27.9642, longitude=-82.4526),
    ]


def test_valhalla_status_integration_skips_when_unavailable():
    provider = valhalla_or_skip()

    status = provider.health_check()

    assert "version" in status


def test_valhalla_matrix_integration_skips_when_unavailable():
    provider = valhalla_or_skip()

    matrix = provider.travel_time_matrix(florida_locations())

    assert len(matrix.durations_minutes) == 2
    assert len(matrix.durations_minutes[0]) == 2


def test_valhalla_route_integration_skips_when_unavailable():
    provider = valhalla_or_skip()

    legs = provider.route_legs(florida_locations())

    assert len(legs) == 1
