import pytest

from backend.economics.route_economics import (
    RouteEconomicsCalculator,
    RouteEconomicsInput,
)


def test_route_economics_calculates_revenue_costs_and_contribution():
    result = RouteEconomicsCalculator().calculate(
        RouteEconomicsInput(
            operating_miles=100,
            route_duration_minutes=180,
            operating_cost_per_mile=1.25,
            driver_hourly_rate=30,
            service_charges=[120, 130],
            tolls=10,
            parking=5,
            route_expenses=20,
        )
    )

    assert result.revenue == 250
    assert result.operating_miles == 100
    assert result.route_cost == 160
    assert result.driver_cost == 90
    assert result.contribution == 0
    assert result.revenue_per_operating_mile == 2.5
    assert result.cost_per_operating_mile == 2.5
    assert result.contribution_per_operating_mile == 0
    assert result.margin == 0


def test_route_economics_uses_default_service_charge_when_no_stop_charges():
    result = RouteEconomicsCalculator().calculate(
        RouteEconomicsInput(
            operating_miles=40,
            route_duration_minutes=60,
            operating_cost_per_mile=1,
            driver_hourly_rate=20,
            stop_count=3,
            default_service_charge=50,
        )
    )

    assert result.revenue == 150
    assert result.route_cost == 40
    assert result.driver_cost == 20
    assert result.contribution == 90
    assert result.revenue_per_operating_mile == 3.75
    assert result.cost_per_operating_mile == 1.5
    assert result.contribution_per_operating_mile == 2.25
    assert result.margin == 0.6


def test_route_economics_keeps_contribution_distinct_from_profit():
    result = RouteEconomicsCalculator().calculate(
        RouteEconomicsInput(
            operating_miles=10,
            route_duration_minutes=30,
            operating_cost_per_mile=1,
            driver_hourly_rate=20,
            service_charges=[50],
        )
    )

    assert hasattr(result, "contribution")
    assert not hasattr(result, "profit")
    assert not hasattr(result, "accounting_profit")


def test_route_economics_returns_none_for_zero_denominator_ratios():
    result = RouteEconomicsCalculator().calculate(
        RouteEconomicsInput(
            operating_miles=0,
            route_duration_minutes=0,
            operating_cost_per_mile=1,
            driver_hourly_rate=20,
            service_charges=[],
            stop_count=0,
            default_service_charge=50,
        )
    )

    assert result.revenue == 0
    assert result.revenue_per_operating_mile is None
    assert result.cost_per_operating_mile is None
    assert result.contribution_per_operating_mile is None
    assert result.margin is None


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("operating_miles", -1),
        ("route_duration_minutes", -1),
        ("operating_cost_per_mile", -1),
        ("driver_hourly_rate", -1),
        ("default_service_charge", -1),
        ("tolls", -1),
        ("parking", -1),
        ("route_expenses", -1),
        ("stop_count", -1),
    ],
)
def test_route_economics_rejects_negative_inputs(field_name, value):
    payload = {
        "operating_miles": 10,
        "route_duration_minutes": 30,
        "operating_cost_per_mile": 1,
        "driver_hourly_rate": 20,
        field_name: value,
    }

    with pytest.raises(ValueError, match="cannot be negative"):
        RouteEconomicsCalculator().calculate(RouteEconomicsInput(**payload))


def test_route_economics_rejects_negative_service_charges():
    with pytest.raises(ValueError, match="service_charges"):
        RouteEconomicsCalculator().calculate(
            RouteEconomicsInput(
                operating_miles=10,
                route_duration_minutes=30,
                operating_cost_per_mile=1,
                driver_hourly_rate=20,
                service_charges=[50, -1],
            )
        )
