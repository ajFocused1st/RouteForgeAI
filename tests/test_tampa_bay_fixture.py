import json
from pathlib import Path

from backend.schemas.depot import DepotCreate
from backend.schemas.stop import StopCreate
from backend.schemas.vehicle import VehicleCreate


FIXTURE_PATH = Path("fixtures/tampa-bay-development.json")


def load_fixture() -> dict:
    with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
        return json.load(fixture_file)


def test_tampa_bay_fixture_matches_integration_scenario():
    fixture = load_fixture()

    assert fixture["region"] == "Tampa Bay, Florida"
    assert fixture["depot"]["name"] == "Tampa Dispatch Depot"
    assert len(fixture["vehicles"]) == 1
    assert fixture["vehicles"][0]["max_payload_lbs"] == 3400
    assert len(fixture["stops"]) == 10

    timed_stops = [
        stop
        for stop in fixture["stops"]
        if stop["earliest_time"] is not None or stop["latest_time"] is not None
    ]
    priority_stops = [stop for stop in fixture["stops"] if stop["priority"] > 1]
    heavy_deliveries = [
        stop
        for stop in fixture["stops"]
        if stop["stop_type"] == "delivery" and stop["weight_lbs"] >= 1000
    ]
    pickups = [stop for stop in fixture["stops"] if stop["stop_type"] == "pickup"]
    normal_deliveries = [
        stop
        for stop in fixture["stops"]
        if stop["stop_type"] == "delivery"
        and stop["earliest_time"] is None
        and stop["latest_time"] is None
        and stop["priority"] == 1
        and stop["weight_lbs"] < 1000
    ]

    assert len(timed_stops) == 1
    assert len(priority_stops) == 1
    assert len(heavy_deliveries) == 1
    assert len(pickups) == 1
    assert len(normal_deliveries) == 6


def test_tampa_bay_fixture_is_schema_valid():
    fixture = load_fixture()

    DepotCreate(**fixture["depot"])
    [VehicleCreate(**vehicle) for vehicle in fixture["vehicles"]]
    [StopCreate(**stop) for stop in fixture["stops"]]


def test_tampa_bay_fixture_payload_fits_cargo_van():
    fixture = load_fixture()

    vehicle_capacity = fixture["vehicles"][0]["max_payload_lbs"]
    total_stop_weight = sum(stop["weight_lbs"] for stop in fixture["stops"])

    assert total_stop_weight <= vehicle_capacity
