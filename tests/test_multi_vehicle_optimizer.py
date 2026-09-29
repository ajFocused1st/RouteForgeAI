from backend.optimization import (
    MultiVehicleConfig,
    MultiVehicleOptimizer,
    OptimizerStatus,
)


def test_multi_vehicle_optimizer_splits_stops_across_vehicles_by_depot():
    optimizer = MultiVehicleOptimizer()
    matrix = [
        [0, 9, 1, 9],
        [9, 0, 9, 1],
        [1, 9, 0, 9],
        [9, 1, 9, 0],
    ]
    vehicles = [
        MultiVehicleConfig(
            vehicle_id="north",
            capacity=200,
            start_depot_index=0,
            end_depot_index=0,
        ),
        MultiVehicleConfig(
            vehicle_id="south",
            capacity=200,
            start_depot_index=1,
            end_depot_index=1,
        ),
    ]

    result = optimizer.solve(
        travel_time_matrix=matrix,
        distance_matrix=matrix,
        vehicles=vehicles,
        stop_weights=[0, 0, 100, 100],
    )

    assert result.solver_status == OptimizerStatus.OPTIMAL
    assert result.routes_by_vehicle["north"] == [2]
    assert result.routes_by_vehicle["south"] == [3]


def test_multi_vehicle_optimizer_enforces_vehicle_capacity():
    optimizer = MultiVehicleOptimizer()
    matrix = [
        [0, 1, 1],
        [1, 0, 1],
        [1, 1, 0],
    ]
    vehicles = [
        MultiVehicleConfig(
            vehicle_id="van-1",
            capacity=100,
            start_depot_index=0,
            end_depot_index=0,
        ),
        MultiVehicleConfig(
            vehicle_id="van-2",
            capacity=100,
            start_depot_index=0,
            end_depot_index=0,
        ),
    ]

    result = optimizer.solve(
        travel_time_matrix=matrix,
        distance_matrix=matrix,
        vehicles=vehicles,
        stop_weights=[0, 150, 50],
    )

    assert result.solver_status == OptimizerStatus.CAPACITY_EXCEEDED
    assert result.routes_by_vehicle == {}


def test_multi_vehicle_optimizer_allows_optional_capacity():
    optimizer = MultiVehicleOptimizer()
    matrix = [
        [0, 1, 1],
        [1, 0, 1],
        [1, 1, 0],
    ]

    result = optimizer.solve(
        travel_time_matrix=matrix,
        distance_matrix=matrix,
        vehicles=[
            MultiVehicleConfig(
                vehicle_id="open-capacity",
                capacity=None,
                start_depot_index=0,
                end_depot_index=0,
            )
        ],
        stop_weights=[0, 150, 50],
    )

    assert result.solver_status == OptimizerStatus.OPTIMAL
    assert sorted(result.routes_by_vehicle["open-capacity"]) == [1, 2]


def test_multi_vehicle_optimizer_enforces_max_hours():
    optimizer = MultiVehicleOptimizer()
    matrix = [
        [0, 20, 20],
        [20, 0, 20],
        [20, 20, 0],
    ]
    vehicles = [
        MultiVehicleConfig(
            vehicle_id="van-1",
            capacity=100,
            start_depot_index=0,
            end_depot_index=0,
            max_hours=1,
        ),
        MultiVehicleConfig(
            vehicle_id="van-2",
            capacity=100,
            start_depot_index=0,
            end_depot_index=0,
            max_hours=1,
        ),
    ]

    feasible = optimizer.solve(
        travel_time_matrix=matrix,
        distance_matrix=matrix,
        vehicles=vehicles,
        stop_weights=[0, 10, 10],
    )
    infeasible = optimizer.solve(
        travel_time_matrix=matrix,
        distance_matrix=matrix,
        vehicles=[
            MultiVehicleConfig(
                vehicle_id="van-1",
                capacity=100,
                start_depot_index=0,
                end_depot_index=0,
                max_hours=0.5,
            ),
            MultiVehicleConfig(
                vehicle_id="van-2",
                capacity=100,
                start_depot_index=0,
                end_depot_index=0,
                max_hours=0.5,
            ),
        ],
        stop_weights=[0, 10, 10],
    )

    assert feasible.solver_status == OptimizerStatus.OPTIMAL
    assert sorted(
        stop_id
        for route in feasible.routes_by_vehicle.values()
        for stop_id in route
    ) == [1, 2]
    assert infeasible.solver_status == OptimizerStatus.NO_FEASIBLE_SOLUTION
    assert infeasible.routes_by_vehicle == {}


def test_multi_vehicle_optimizer_enforces_max_mileage():
    optimizer = MultiVehicleOptimizer()
    time_matrix = [
        [0, 1, 1],
        [1, 0, 1],
        [1, 1, 0],
    ]
    distance_matrix = [
        [0, 40, 40],
        [40, 0, 40],
        [40, 40, 0],
    ]

    result = optimizer.solve(
        travel_time_matrix=time_matrix,
        distance_matrix=distance_matrix,
        vehicles=[
            MultiVehicleConfig(
                vehicle_id="van-1",
                capacity=100,
                start_depot_index=0,
                end_depot_index=0,
                max_mileage=50,
            ),
            MultiVehicleConfig(
                vehicle_id="van-2",
                capacity=100,
                start_depot_index=0,
                end_depot_index=0,
                max_mileage=50,
            ),
        ],
        stop_weights=[0, 10, 10],
    )

    assert result.solver_status == OptimizerStatus.NO_FEASIBLE_SOLUTION
    assert result.routes_by_vehicle == {}


def test_multi_vehicle_optimizer_rejects_invalid_inputs():
    optimizer = MultiVehicleOptimizer()
    vehicle = MultiVehicleConfig(
        vehicle_id="van-1",
        capacity=100,
        start_depot_index=0,
        end_depot_index=0,
    )

    ragged = optimizer.solve(
        travel_time_matrix=[[0, 1], [1]],
        distance_matrix=[[0, 1], [1, 0]],
        vehicles=[vehicle],
        stop_weights=[0, 10],
    )
    mismatched_weights = optimizer.solve(
        travel_time_matrix=[[0, 1], [1, 0]],
        distance_matrix=[[0, 1], [1, 0]],
        vehicles=[vehicle],
        stop_weights=[0],
    )
    bad_depot = optimizer.solve(
        travel_time_matrix=[[0, 1], [1, 0]],
        distance_matrix=[[0, 1], [1, 0]],
        vehicles=[
            MultiVehicleConfig(
                vehicle_id="van-1",
                capacity=100,
                start_depot_index=3,
                end_depot_index=0,
            )
        ],
        stop_weights=[0, 10],
    )

    assert ragged.solver_status == OptimizerStatus.INVALID_INPUT
    assert mismatched_weights.solver_status == OptimizerStatus.INVALID_INPUT
    assert bad_depot.solver_status == OptimizerStatus.INVALID_INPUT
