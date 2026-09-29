from dataclasses import dataclass
from enum import StrEnum

from ortools.constraint_solver import pywrapcp, routing_enums_pb2


class OptimizerStatus(StrEnum):
    OPTIMAL = "optimal"
    NO_SOLUTION = "no_solution"
    NO_FEASIBLE_SOLUTION = "no_feasible_solution"
    INVALID_INPUT = "invalid_input"
    CAPACITY_EXCEEDED = "capacity_exceeded"


@dataclass(frozen=True)
class SingleVehicleOptimizerResult:
    optimized_stop_order: list[int]
    solver_status: OptimizerStatus


class SingleVehicleOptimizer:
    def solve(
        self,
        travel_time_matrix: list[list[int | float]],
        depot_index: int,
        stop_weights: list[int | float] | None = None,
        vehicle_payload_capacity: int | float | None = None,
        earliest_arrivals: list[int | float | None] | None = None,
        latest_arrivals: list[int | float | None] | None = None,
        service_durations: list[int | float] | None = None,
        route_start_time: int | float | None = None,
        required_end_time: int | float | None = None,
    ) -> SingleVehicleOptimizerResult:
        if not self._is_valid_matrix(travel_time_matrix, depot_index):
            return SingleVehicleOptimizerResult(
                optimized_stop_order=[],
                solver_status=OptimizerStatus.INVALID_INPUT,
            )
        if not self._is_valid_payload_inputs(
            travel_time_matrix,
            stop_weights,
            vehicle_payload_capacity,
        ):
            return SingleVehicleOptimizerResult(
                optimized_stop_order=[],
                solver_status=OptimizerStatus.INVALID_INPUT,
            )
        if self._capacity_exceeded(stop_weights, vehicle_payload_capacity):
            return SingleVehicleOptimizerResult(
                optimized_stop_order=[],
                solver_status=OptimizerStatus.CAPACITY_EXCEEDED,
            )
        if not self._is_valid_time_window_inputs(
            travel_time_matrix,
            earliest_arrivals,
            latest_arrivals,
            service_durations,
            route_start_time,
            required_end_time,
        ):
            return SingleVehicleOptimizerResult(
                optimized_stop_order=[],
                solver_status=OptimizerStatus.INVALID_INPUT,
            )

        if len(travel_time_matrix) == 1:
            return SingleVehicleOptimizerResult(
                optimized_stop_order=[],
                solver_status=OptimizerStatus.OPTIMAL,
            )

        manager = pywrapcp.RoutingIndexManager(
            len(travel_time_matrix),
            1,
            depot_index,
        )
        routing = pywrapcp.RoutingModel(manager)

        def travel_time_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(round(travel_time_matrix[from_node][to_node] * 1000))

        transit_callback_index = routing.RegisterTransitCallback(travel_time_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        has_time_constraints = self._has_time_constraints(
            earliest_arrivals,
            latest_arrivals,
            service_durations,
            route_start_time,
            required_end_time,
        )
        if has_time_constraints:
            self._add_time_dimension(
                routing,
                manager,
                travel_time_matrix,
                earliest_arrivals,
                latest_arrivals,
                service_durations,
                route_start_time,
                required_end_time,
            )

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 0
        search_parameters.time_limit.nanos = 100_000_000

        solution = routing.SolveWithParameters(search_parameters)
        if solution is None:
            return SingleVehicleOptimizerResult(
                optimized_stop_order=[],
                solver_status=(
                    OptimizerStatus.NO_FEASIBLE_SOLUTION
                    if has_time_constraints
                    else OptimizerStatus.NO_SOLUTION
                ),
            )

        return SingleVehicleOptimizerResult(
            optimized_stop_order=self._stop_order_from_solution(
                routing,
                manager,
                solution,
                depot_index,
            ),
            solver_status=OptimizerStatus.OPTIMAL,
        )

    def _stop_order_from_solution(
        self,
        routing: pywrapcp.RoutingModel,
        manager: pywrapcp.RoutingIndexManager,
        solution: pywrapcp.Assignment,
        depot_index: int,
    ) -> list[int]:
        order = []
        index = routing.Start(0)

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != depot_index:
                order.append(node)
            index = solution.Value(routing.NextVar(index))

        return order

    def _is_valid_matrix(
        self,
        travel_time_matrix: list[list[int | float]],
        depot_index: int,
    ) -> bool:
        size = len(travel_time_matrix)
        if size == 0 or depot_index < 0 or depot_index >= size:
            return False

        for row in travel_time_matrix:
            if len(row) != size:
                return False

            if any(value < 0 for value in row):
                return False

        return True

    def _is_valid_payload_inputs(
        self,
        travel_time_matrix: list[list[int | float]],
        stop_weights: list[int | float] | None,
        vehicle_payload_capacity: int | float | None,
    ) -> bool:
        if vehicle_payload_capacity is not None and vehicle_payload_capacity < 0:
            return False

        if stop_weights is None:
            return True

        if len(stop_weights) != len(travel_time_matrix):
            return False

        return all(weight >= 0 for weight in stop_weights)

    def _capacity_exceeded(
        self,
        stop_weights: list[int | float] | None,
        vehicle_payload_capacity: int | float | None,
    ) -> bool:
        if stop_weights is None or vehicle_payload_capacity is None:
            return False

        return sum(stop_weights) > vehicle_payload_capacity

    def _is_valid_time_window_inputs(
        self,
        travel_time_matrix: list[list[int | float]],
        earliest_arrivals: list[int | float | None] | None,
        latest_arrivals: list[int | float | None] | None,
        service_durations: list[int | float] | None,
        route_start_time: int | float | None,
        required_end_time: int | float | None,
    ) -> bool:
        size = len(travel_time_matrix)

        for values in (earliest_arrivals, latest_arrivals, service_durations):
            if values is not None and len(values) != size:
                return False

        for values in (earliest_arrivals, latest_arrivals, service_durations):
            if values is not None and any(
                value is not None and value < 0 for value in values
            ):
                return False

        if route_start_time is not None and route_start_time < 0:
            return False

        if required_end_time is not None and required_end_time < 0:
            return False

        if (
            route_start_time is not None
            and required_end_time is not None
            and required_end_time < route_start_time
        ):
            return False

        if earliest_arrivals is not None and latest_arrivals is not None:
            for earliest, latest in zip(earliest_arrivals, latest_arrivals):
                if earliest is not None and latest is not None and latest < earliest:
                    return False

        return True

    def _has_time_constraints(
        self,
        earliest_arrivals: list[int | float | None] | None,
        latest_arrivals: list[int | float | None] | None,
        service_durations: list[int | float] | None,
        route_start_time: int | float | None,
        required_end_time: int | float | None,
    ) -> bool:
        return any(
            value is not None
            for value in (
                earliest_arrivals,
                latest_arrivals,
                service_durations,
                route_start_time,
                required_end_time,
            )
        )

    def _add_time_dimension(
        self,
        routing: pywrapcp.RoutingModel,
        manager: pywrapcp.RoutingIndexManager,
        travel_time_matrix: list[list[int | float]],
        earliest_arrivals: list[int | float | None] | None,
        latest_arrivals: list[int | float | None] | None,
        service_durations: list[int | float] | None,
        route_start_time: int | float | None,
        required_end_time: int | float | None,
    ) -> None:
        time_scale = 1000
        size = len(travel_time_matrix)
        service_durations = service_durations or [0] * size
        horizon = self._time_horizon(
            travel_time_matrix,
            earliest_arrivals,
            latest_arrivals,
            service_durations,
            route_start_time,
            required_end_time,
            time_scale,
        )

        def time_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            travel_time = travel_time_matrix[from_node][to_node]
            service_duration = service_durations[from_node]
            return int(round((travel_time + service_duration) * time_scale))

        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            horizon,
            horizon,
            False,
            "Time",
        )
        time_dimension = routing.GetDimensionOrDie("Time")

        start_time = int(round((route_start_time or 0) * time_scale))
        time_dimension.CumulVar(routing.Start(0)).SetRange(start_time, start_time)

        if required_end_time is not None:
            end_time = int(round(required_end_time * time_scale))
            time_dimension.CumulVar(routing.End(0)).SetRange(0, end_time)

        for node in range(size):
            if node == manager.IndexToNode(routing.Start(0)):
                continue

            index = manager.NodeToIndex(node)
            if index < 0:
                continue

            earliest = (
                int(round(earliest_arrivals[node] * time_scale))
                if earliest_arrivals is not None
                and earliest_arrivals[node] is not None
                else 0
            )
            latest = (
                int(round(latest_arrivals[node] * time_scale))
                if latest_arrivals is not None
                and latest_arrivals[node] is not None
                else horizon
            )
            time_dimension.CumulVar(index).SetRange(earliest, latest)

    def _time_horizon(
        self,
        travel_time_matrix: list[list[int | float]],
        earliest_arrivals: list[int | float | None] | None,
        latest_arrivals: list[int | float | None] | None,
        service_durations: list[int | float],
        route_start_time: int | float | None,
        required_end_time: int | float | None,
        time_scale: int,
    ) -> int:
        max_travel = max(max(row) for row in travel_time_matrix)
        base_horizon = (
            (route_start_time or 0)
            + (max_travel * len(travel_time_matrix))
            + sum(service_durations)
            + 1
        )
        candidates = [base_horizon]
        if earliest_arrivals is not None:
            candidates.extend(value for value in earliest_arrivals if value is not None)
        if latest_arrivals is not None:
            candidates.extend(value for value in latest_arrivals if value is not None)
        if required_end_time is not None:
            candidates.append(required_end_time)

        return int(round(max(candidates) * time_scale))
