from dataclasses import dataclass


PICKUP_TYPES = {"pickup", "pickup_delivery"}
DELIVERY_TYPES = {"delivery", "pickup_delivery"}


@dataclass(frozen=True)
class DeadheadStop:
    stop_type: str
    weight_lbs: float


@dataclass(frozen=True)
class DeadheadMetrics:
    pre_pickup_deadhead_miles: float
    between_job_repositioning_miles: float
    post_delivery_deadhead_miles: float
    return_to_depot_deadhead_miles: float
    total_unloaded_miles: float
    deadhead_percentage: float


class DeadheadCalculator:
    def calculate(
        self,
        stops: list[DeadheadStop],
        leg_distances_miles: list[float],
    ) -> DeadheadMetrics:
        if len(leg_distances_miles) != len(stops) + 1:
            raise ValueError("leg_distances_miles must include depot legs around every stop.")

        initial_load = self._initial_depot_load(stops)
        current_load = max(0.0, initial_load)
        buckets = {
            "pre_pickup": 0.0,
            "between_job": 0.0,
            "post_delivery": 0.0,
            "return_to_depot": 0.0,
        }

        for leg_index, distance_miles in enumerate(leg_distances_miles):
            if distance_miles < 0:
                raise ValueError("leg distances cannot be negative.")

            if current_load <= 0:
                bucket = self._deadhead_bucket(stops, leg_index)
                buckets[bucket] += distance_miles

            if leg_index < len(stops):
                current_load = self._load_after_stop(current_load, stops[leg_index])

        total_route_miles = sum(leg_distances_miles)
        total_unloaded = sum(buckets.values())
        deadhead_percentage = (
            (total_unloaded / total_route_miles) * 100 if total_route_miles > 0 else 0.0
        )

        return DeadheadMetrics(
            pre_pickup_deadhead_miles=buckets["pre_pickup"],
            between_job_repositioning_miles=buckets["between_job"],
            post_delivery_deadhead_miles=buckets["post_delivery"],
            return_to_depot_deadhead_miles=buckets["return_to_depot"],
            total_unloaded_miles=total_unloaded,
            deadhead_percentage=deadhead_percentage,
        )

    def _deadhead_bucket(self, stops: list[DeadheadStop], leg_index: int) -> str:
        if leg_index == len(stops):
            return "return_to_depot"

        destination = stops[leg_index]
        if leg_index == 0:
            return (
                "pre_pickup"
                if destination.stop_type in PICKUP_TYPES
                else "post_delivery"
            )

        origin = stops[leg_index - 1]
        if origin.stop_type in DELIVERY_TYPES and destination.stop_type in PICKUP_TYPES:
            return "between_job"

        if origin.stop_type in DELIVERY_TYPES:
            return "post_delivery"

        return "between_job"

    def _load_after_stop(self, current_load: float, stop: DeadheadStop) -> float:
        if stop.stop_type == "pickup":
            return current_load + stop.weight_lbs

        if stop.stop_type == "delivery":
            return max(0.0, current_load - stop.weight_lbs)

        if stop.stop_type == "pickup_delivery":
            return max(0.0, current_load - stop.weight_lbs) + stop.weight_lbs

        raise ValueError(f"Unsupported stop type: {stop.stop_type}.")

    def _initial_depot_load(self, stops: list[DeadheadStop]) -> float:
        load = 0.0
        for stop in stops:
            if stop.stop_type == "delivery":
                load += stop.weight_lbs
                continue

            if stop.stop_type == "pickup_delivery":
                load += stop.weight_lbs

            break

        return max(0.0, load)
