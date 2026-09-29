import pytest

from backend.economics.deadhead import DeadheadCalculator, DeadheadStop


def test_deadhead_calculates_pickup_and_return_categories():
    metrics = DeadheadCalculator().calculate(
        [
            DeadheadStop(stop_type="pickup", weight_lbs=100),
            DeadheadStop(stop_type="delivery", weight_lbs=100),
        ],
        [3, 12, 4],
    )

    assert metrics.pre_pickup_deadhead_miles == 3
    assert metrics.between_job_repositioning_miles == 0
    assert metrics.post_delivery_deadhead_miles == 0
    assert metrics.return_to_depot_deadhead_miles == 4
    assert metrics.total_unloaded_miles == 7
    assert metrics.deadhead_percentage == pytest.approx((7 / 19) * 100)


def test_deadhead_calculates_between_job_repositioning_after_delivery():
    metrics = DeadheadCalculator().calculate(
        [
            DeadheadStop(stop_type="delivery", weight_lbs=100),
            DeadheadStop(stop_type="pickup", weight_lbs=50),
            DeadheadStop(stop_type="delivery", weight_lbs=50),
        ],
        [5, 7, 9, 2],
    )

    assert metrics.pre_pickup_deadhead_miles == 0
    assert metrics.between_job_repositioning_miles == 7
    assert metrics.post_delivery_deadhead_miles == 0
    assert metrics.return_to_depot_deadhead_miles == 2
    assert metrics.total_unloaded_miles == 9
    assert metrics.deadhead_percentage == pytest.approx((9 / 23) * 100)


def test_deadhead_calculator_requires_depot_legs():
    with pytest.raises(ValueError, match="must include depot legs"):
        DeadheadCalculator().calculate(
            [DeadheadStop(stop_type="pickup", weight_lbs=100)],
            [3],
        )
