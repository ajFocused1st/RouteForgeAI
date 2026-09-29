from dataclasses import dataclass

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from backend.optimization.single_vehicle import OptimizerStatus


SCALE = 1000


@dataclass(frozen=True)
class MultiVehicleConfig:
    vehicle_id: str
    capacity: int | float | None
    start_depot_index: int
    end_depot_index: int
    max_hours: int | float | None = None
    max_mileage: int | float | None = None


@dataclass(frozen=True)
class MultiVehicleOptimizerResult:
    routes_by_vehicle: dict[str, list[int]]
    solver_status: OptimizerStatus


class MultiVehicleOptimizer:
    def solve(
        self,
        travel_time_matrix: list[list[int | float]],
        distance_matrix: list[list[int | float]],
        vehicles: list[MultiVehicleConfig],
        stop_weights: list[int | float],
        service_durations: list[int | float] | None = None,
    ) -> MultiVehicleOptimizerResult:
        if not self._is_valid_input(
            travel_time_matrix,
            distance_matrix,
            vehicles,
            stop_weights,
            service_durations,
        ):
            return MultiVehicleOptimizerResult(
                routes_by_vehicle={},
                solver_status=OptimizerStatus.INVALID_INPUT,
            )

        if not vehicles:
            return MultiVehicleOptimizerResult(
                routes_by_vehicle={},
                solver_status=OptimizerStatus.INVALID_INPUT,
            )

        if self._capacity_exceeded(vehicles, stop_weights):
            return MultiVehicleOptimizerResult(
                routes_by_vehicle={},
                solver_status=OptimizerStatus.CAPACITY_EXCEEDED,
            )

        if len(travel_time_matrix) == len(self._depot_indices(vehicles)):
            return MultiVehicleOptimizerResult(
                routes_by_vehicle={vehicle.vehicle_id: [] for vehicle in vehicles},
                solver_status=OptimizerStatus.OPTIMAL,
            )

        manager = pywrapcp.RoutingIndexManager(
            len(travel_time_matrix),
            len(vehicles),
            [vehicle.start_depot_index for vehicle in vehicles],
            [vehicle.end_depot_index for vehicle in vehicles],
        )
        routing = pywrapcp.RoutingModel(manager)

        def travel_time_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(round(travel_time_matrix[from_node][to_node] * SCALE))

        travel_callback_index = routing.RegisterTransitCallback(travel_time_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(travel_callback_index)

        self._add_capacity_dimension(routing, manager, vehicles, stop_weights)
        self._add_time_dimension(
            routing,
            manager,
            travel_time_matrix,
            vehicles,
            service_durations or [0] * len(travel_time_matrix),
        )
        self._add_distance_dimension(
            routing,
            manager,
            distance_matrix,
            vehicles,
        )

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 2

        solution = routing.SolveWithParameters(search_parameters)
        if solution is None:
            return MultiVehicleOptimizerResult(
                routes_by_vehicle={},
                solver_status=OptimizerStatus.NO_FEASIBLE_SOLUTION,
            )

        return MultiVehicleOptimizerResult(
            routes_by_vehicle=self._routes_from_solution(
                routing,
                manager,
                solution,
                vehicles,
            ),
            solver_status=OptimizerStatus.OPTIMAL,
        )

    def _add_capacity_dimension(
        self,
        routing: pywrapcp.RoutingModel,
        manager: pywrapcp.RoutingIndexManager,
        vehicles: list[MultiVehicleConfig],
        stop_weights: list[int | float],
    ) -> None:
        def demand_callback(from_index: int) -> int:
            node = manager.IndexToNode(from_index)
            return int(round(stop_weights[node] * SCALE))

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,
            [
                int(round(self._vehicle_capacity(vehicle, stop_weights) * SCALE))
                for vehicle in vehicles
            ],
            True,
            "Capacity",
        )

    def _add_time_dimension(
        self,
        routing: pywrapcp.RoutingModel,
        manager: pywrapcp.RoutingIndexManager,
        travel_time_matrix: list[list[int | float]],
        vehicles: list[MultiVehicleConfig],
        service_durations: list[int | float],
    ) -> None:
        def time_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(
                round(
                    (
                        travel_time_matrix[from_node][to_node]
                        + service_durations[from_node]
                    )
                    * SCALE
                )
            )

        horizon = self._time_horizon(travel_time_matrix, service_durations, vehicles)
        time_callback_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimension(
            time_callback_index,
            0,
            horizon,
            True,
            "Time",
        )
        time_dimension = routing.GetDimensionOrDie("Time")
        for vehicle_index, vehicle in enumerate(vehicles):
            if vehicle.max_hours is not None:
                max_minutes = vehicle.max_hours * 60
                time_dimension.CumulVar(routing.End(vehicle_index)).SetRange(
                    0,
                    int(round(max_minutes * SCALE)),
                )

    def _add_distance_dimension(
        self,
        routing: pywrapcp.RoutingModel,
        manager: pywrapcp.RoutingIndexManager,
        distance_matrix: list[list[int | float]],
        vehicles: list[MultiVehicleConfig],
    ) -> None:
        def distance_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(round(distance_matrix[from_node][to_node] * SCALE))

        max_distance = self._distance_horizon(distance_matrix, vehicles)
        distance_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.AddDimension(
            distance_callback_index,
            0,
            max_distance,
            True,
            "Distance",
        )
        distance_dimension = routing.GetDimensionOrDie("Distance")
        for vehicle_index, vehicle in enumerate(vehicles):
            if vehicle.max_mileage is not None:
                distance_dimension.CumulVar(routing.End(vehicle_index)).SetRange(
                    0,
                    int(round(vehicle.max_mileage * SCALE)),
                )

    def _routes_from_solution(
        self,
        routing: pywrapcp.RoutingModel,
        manager: pywrapcp.RoutingIndexManager,
        solution: pywrapcp.Assignment,
        vehicles: list[MultiVehicleConfig],
    ) -> dict[str, list[int]]:
        depot_indices = self._depot_indices(vehicles)
        routes: dict[str, list[int]] = {}
        for vehicle_index, vehicle in enumerate(vehicles):
            index = routing.Start(vehicle_index)
            route = []
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node not in depot_indices:
                    route.append(node)
                index = solution.Value(routing.NextVar(index))
            routes[vehicle.vehicle_id] = route
        return routes

    def _is_valid_input(
        self,
        travel_time_matrix: list[list[int | float]],
        distance_matrix: list[list[int | float]],
        vehicles: list[MultiVehicleConfig],
        stop_weights: list[int | float],
        service_durations: list[int | float] | None,
    ) -> bool:
        size = len(travel_time_matrix)
        if size == 0 or len(distance_matrix) != size or len(stop_weights) != size:
            return False
        if not self._is_square_nonnegative_matrix(travel_time_matrix, size):
            return False
        if not self._is_square_nonnegative_matrix(distance_matrix, size):
            return False
        if any(weight < 0 for weight in stop_weights):
            return False
        if service_durations is not None and (
            len(service_durations) != size
            or any(duration < 0 for duration in service_durations)
        ):
            return False

        vehicle_ids = [vehicle.vehicle_id for vehicle in vehicles]
        if len(vehicle_ids) != len(set(vehicle_ids)):
            return False

        for vehicle in vehicles:
            if (
                vehicle.start_depot_index < 0
                or vehicle.start_depot_index >= size
                or vehicle.end_depot_index < 0
                or vehicle.end_depot_index >= size
            ):
                return False
            if vehicle.capacity is not None and vehicle.capacity < 0:
                return False
            if vehicle.max_hours is not None and vehicle.max_hours < 0:
                return False
            if vehicle.max_mileage is not None and vehicle.max_mileage < 0:
                return False

        return True

    def _is_square_nonnegative_matrix(
        self,
        matrix: list[list[int | float]],
        size: int,
    ) -> bool:
        for row in matrix:
            if len(row) != size:
                return False
            if any(value < 0 for value in row):
                return False
        return True

    def _capacity_exceeded(
        self,
        vehicles: list[MultiVehicleConfig],
        stop_weights: list[int | float],
    ) -> bool:
        capacities = [vehicle.capacity for vehicle in vehicles]
        if any(capacity is None for capacity in capacities):
            return False

        max_capacity = max(capacities or [0]) or 0
        total_capacity = sum(capacity or 0 for capacity in capacities)
        depot_indices = self._depot_indices(vehicles)
        required_weights = [
            weight for index, weight in enumerate(stop_weights) if index not in depot_indices
        ]
        return (
            any(weight > max_capacity for weight in required_weights)
            or sum(required_weights) > total_capacity
        )

    def _depot_indices(self, vehicles: list[MultiVehicleConfig]) -> set[int]:
        return {
            depot_index
            for vehicle in vehicles
            for depot_index in (vehicle.start_depot_index, vehicle.end_depot_index)
        }

    def _time_horizon(
        self,
        travel_time_matrix: list[list[int | float]],
        service_durations: list[int | float],
        vehicles: list[MultiVehicleConfig],
    ) -> int:
        fallback = (
            max(max(row) for row in travel_time_matrix) * len(travel_time_matrix)
            + sum(service_durations)
            + 1
        )
        constrained = [
            vehicle.max_hours * 60
            for vehicle in vehicles
            if vehicle.max_hours is not None
        ]
        return int(round(max([fallback, *constrained]) * SCALE))

    def _distance_horizon(
        self,
        distance_matrix: list[list[int | float]],
        vehicles: list[MultiVehicleConfig],
    ) -> int:
        fallback = max(max(row) for row in distance_matrix) * len(distance_matrix) + 1
        constrained = [
            vehicle.max_mileage
            for vehicle in vehicles
            if vehicle.max_mileage is not None
        ]
        return int(round(max([fallback, *constrained]) * SCALE))

    def _vehicle_capacity(
        self,
        vehicle: MultiVehicleConfig,
        stop_weights: list[int | float],
    ) -> int | float:
        if vehicle.capacity is not None:
            return vehicle.capacity

        return sum(stop_weights)
