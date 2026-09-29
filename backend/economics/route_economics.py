from dataclasses import dataclass, field


@dataclass(frozen=True)
class RouteEconomicsInput:
    operating_miles: float
    route_duration_minutes: float
    operating_cost_per_mile: float
    driver_hourly_rate: float
    stop_count: int = 0
    service_charges: list[float] = field(default_factory=list)
    default_service_charge: float = 0
    tolls: float = 0
    parking: float = 0
    route_expenses: float = 0


@dataclass(frozen=True)
class RouteEconomicsResult:
    revenue: float
    operating_miles: float
    route_cost: float
    driver_cost: float
    contribution: float
    revenue_per_operating_mile: float | None
    cost_per_operating_mile: float | None
    contribution_per_operating_mile: float | None
    margin: float | None


class RouteEconomicsCalculator:
    def calculate(self, economics_input: RouteEconomicsInput) -> RouteEconomicsResult:
        self._validate(economics_input)

        revenue = self._revenue(economics_input)
        mileage_cost = (
            economics_input.operating_miles
            * economics_input.operating_cost_per_mile
        )
        route_cost = (
            mileage_cost
            + economics_input.tolls
            + economics_input.parking
            + economics_input.route_expenses
        )
        driver_cost = (
            economics_input.route_duration_minutes / 60
        ) * economics_input.driver_hourly_rate
        total_cost = route_cost + driver_cost
        contribution = revenue - total_cost

        return RouteEconomicsResult(
            revenue=revenue,
            operating_miles=economics_input.operating_miles,
            route_cost=route_cost,
            driver_cost=driver_cost,
            contribution=contribution,
            revenue_per_operating_mile=self._ratio(
                revenue,
                economics_input.operating_miles,
            ),
            cost_per_operating_mile=self._ratio(
                total_cost,
                economics_input.operating_miles,
            ),
            contribution_per_operating_mile=self._ratio(
                contribution,
                economics_input.operating_miles,
            ),
            margin=self._ratio(contribution, revenue),
        )

    def _revenue(self, economics_input: RouteEconomicsInput) -> float:
        if economics_input.service_charges:
            return sum(economics_input.service_charges)

        return economics_input.stop_count * economics_input.default_service_charge

    def _ratio(self, numerator: float, denominator: float) -> float | None:
        if denominator == 0:
            return None

        return numerator / denominator

    def _validate(self, economics_input: RouteEconomicsInput) -> None:
        numeric_fields = {
            "operating_miles": economics_input.operating_miles,
            "route_duration_minutes": economics_input.route_duration_minutes,
            "operating_cost_per_mile": economics_input.operating_cost_per_mile,
            "driver_hourly_rate": economics_input.driver_hourly_rate,
            "default_service_charge": economics_input.default_service_charge,
            "tolls": economics_input.tolls,
            "parking": economics_input.parking,
            "route_expenses": economics_input.route_expenses,
        }
        for field_name, value in numeric_fields.items():
            if value < 0:
                raise ValueError(f"{field_name} cannot be negative.")

        if economics_input.stop_count < 0:
            raise ValueError("stop_count cannot be negative.")

        if any(charge < 0 for charge in economics_input.service_charges):
            raise ValueError("service_charges cannot contain negative values.")
