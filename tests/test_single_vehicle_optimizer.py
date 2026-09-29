from backend.optimization import OptimizerStatus, SingleVehicleOptimizer


def test_single_vehicle_optimizer_returns_deterministic_stop_order():
    optimizer = SingleVehicleOptimizer()
    matrix = [
        [0, 2, 9, 10],
        [1, 0, 6, 4],
        [15, 7, 0, 8],
        [6, 3, 12, 0],
    ]

    result = optimizer.solve(matrix, depot_index=0)

    assert result.solver_status == OptimizerStatus.OPTIMAL
    assert result.optimized_stop_order == [2, 3, 1]


def test_single_vehicle_optimizer_supports_nonzero_depot_index():
    optimizer = SingleVehicleOptimizer()
    matrix = [
        [0, 5, 1],
        [5, 0, 2],
        [1, 2, 0],
    ]

    result = optimizer.solve(matrix, depot_index=1)

    assert result.solver_status == OptimizerStatus.OPTIMAL
    assert result.optimized_stop_order == [2, 0]


def test_single_vehicle_optimizer_returns_empty_order_for_depot_only():
    optimizer = SingleVehicleOptimizer()

    result = optimizer.solve([[0]], depot_index=0)

    assert result.solver_status == OptimizerStatus.OPTIMAL
    assert result.optimized_stop_order == []


def test_single_vehicle_optimizer_accepts_route_within_payload_capacity():
    optimizer = SingleVehicleOptimizer()
    matrix = [
        [0, 2, 9, 10],
        [1, 0, 6, 4],
        [15, 7, 0, 8],
        [6, 3, 12, 0],
    ]

    result = optimizer.solve(
        matrix,
        depot_index=0,
        stop_weights=[0, 500, 800, 700],
        vehicle_payload_capacity=2500,
    )

    assert result.solver_status == OptimizerStatus.OPTIMAL
    assert result.optimized_stop_order == [2, 3, 1]


def test_single_vehicle_optimizer_rejects_route_exceeding_payload_capacity():
    optimizer = SingleVehicleOptimizer()
    matrix = [
        [0, 2, 9],
        [1, 0, 6],
        [15, 7, 0],
    ]

    result = optimizer.solve(
        matrix,
        depot_index=0,
        stop_weights=[0, 1500, 2000],
        vehicle_payload_capacity=3000,
    )

    assert result.solver_status == OptimizerStatus.CAPACITY_EXCEEDED
    assert result.optimized_stop_order == []


def test_single_vehicle_optimizer_respects_time_windows():
    optimizer = SingleVehicleOptimizer()
    matrix = [
        [0, 5, 1],
        [1, 0, 5],
        [1, 1, 0],
    ]

    result = optimizer.solve(
        matrix,
        depot_index=0,
        earliest_arrivals=[0, 0, 10],
        latest_arrivals=[100, 6, 100],
        service_durations=[0, 0, 0],
        route_start_time=0,
        required_end_time=20,
    )

    assert result.solver_status == OptimizerStatus.OPTIMAL
    assert result.optimized_stop_order == [1, 2]


def test_single_vehicle_optimizer_returns_no_feasible_solution_for_impossible_windows():
    optimizer = SingleVehicleOptimizer()
    matrix = [
        [0, 5, 1],
        [1, 0, 5],
        [1, 1, 0],
    ]

    result = optimizer.solve(
        matrix,
        depot_index=0,
        earliest_arrivals=[0, 0, 10],
        latest_arrivals=[100, 4, 100],
        service_durations=[0, 0, 0],
        route_start_time=0,
        required_end_time=20,
    )

    assert result.solver_status == OptimizerStatus.NO_FEASIBLE_SOLUTION
    assert result.optimized_stop_order == []


def test_single_vehicle_optimizer_enforces_service_duration_and_required_end_time():
    optimizer = SingleVehicleOptimizer()
    matrix = [
        [0, 5, 5],
        [5, 0, 5],
        [5, 5, 0],
    ]

    feasible_result = optimizer.solve(
        matrix,
        depot_index=0,
        service_durations=[0, 10, 0],
        route_start_time=0,
        required_end_time=25,
    )
    infeasible_result = optimizer.solve(
        matrix,
        depot_index=0,
        service_durations=[0, 10, 0],
        route_start_time=0,
        required_end_time=20,
    )

    assert feasible_result.solver_status == OptimizerStatus.OPTIMAL
    assert infeasible_result.solver_status == OptimizerStatus.NO_FEASIBLE_SOLUTION
    assert infeasible_result.optimized_stop_order == []


def test_single_vehicle_optimizer_rejects_invalid_matrix():
    optimizer = SingleVehicleOptimizer()

    ragged_result = optimizer.solve([[0, 1], [1]], depot_index=0)
    negative_result = optimizer.solve([[0, -1], [1, 0]], depot_index=0)
    bad_depot_result = optimizer.solve([[0]], depot_index=1)

    assert ragged_result.solver_status == OptimizerStatus.INVALID_INPUT
    assert negative_result.solver_status == OptimizerStatus.INVALID_INPUT
    assert bad_depot_result.solver_status == OptimizerStatus.INVALID_INPUT


def test_single_vehicle_optimizer_rejects_invalid_payload_inputs():
    optimizer = SingleVehicleOptimizer()
    matrix = [
        [0, 2],
        [1, 0],
    ]

    wrong_length = optimizer.solve(
        matrix,
        depot_index=0,
        stop_weights=[0],
        vehicle_payload_capacity=100,
    )
    negative_weight = optimizer.solve(
        matrix,
        depot_index=0,
        stop_weights=[0, -1],
        vehicle_payload_capacity=100,
    )
    negative_capacity = optimizer.solve(
        matrix,
        depot_index=0,
        stop_weights=[0, 1],
        vehicle_payload_capacity=-1,
    )

    assert wrong_length.solver_status == OptimizerStatus.INVALID_INPUT
    assert negative_weight.solver_status == OptimizerStatus.INVALID_INPUT
    assert negative_capacity.solver_status == OptimizerStatus.INVALID_INPUT


def test_single_vehicle_optimizer_rejects_invalid_time_window_inputs():
    optimizer = SingleVehicleOptimizer()
    matrix = [
        [0, 2],
        [1, 0],
    ]

    wrong_length = optimizer.solve(
        matrix,
        depot_index=0,
        earliest_arrivals=[0],
    )
    negative_service = optimizer.solve(
        matrix,
        depot_index=0,
        service_durations=[0, -1],
    )
    invalid_window = optimizer.solve(
        matrix,
        depot_index=0,
        earliest_arrivals=[0, 10],
        latest_arrivals=[100, 5],
    )
    invalid_end = optimizer.solve(
        matrix,
        depot_index=0,
        route_start_time=10,
        required_end_time=5,
    )

    assert wrong_length.solver_status == OptimizerStatus.INVALID_INPUT
    assert negative_service.solver_status == OptimizerStatus.INVALID_INPUT
    assert invalid_window.solver_status == OptimizerStatus.INVALID_INPUT
    assert invalid_end.solver_status == OptimizerStatus.INVALID_INPUT
