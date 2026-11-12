"""Unit tests for SARScenario and coverage model."""
import pytest

from backend.sar.scenario import (
    SARScenario,
    ScenarioValidationError,
    get_canonical_benchmark_scenario,
)
from backend.sar.spatial import SpatialTarget, SpatialWaypoint, generate_spatial_scenario


def test_canonical_matrix_dimensions():
    """Requirement 1: Canonical matrix dimensions (5 targets, 6 candidate waypoints)."""
    scenario = get_canonical_benchmark_scenario()
    assert scenario.num_targets == 5
    assert scenario.num_waypoints == 6
    assert len(scenario.coverage_matrix) == 5
    for row in scenario.coverage_matrix:
        assert len(row) == 6


def test_canonical_target_and_waypoint_ids():
    """Requirement 2: Correct target and waypoint IDs."""
    scenario = get_canonical_benchmark_scenario()
    assert scenario.target_ids == ["T1", "T2", "T3", "T4", "T5"]
    assert scenario.waypoint_ids == ["W1", "W2", "W3", "W4", "W5", "W6"]
    assert scenario.k_coverage == 3


def test_binary_matrix_validation():
    """Requirement 3: Binary matrix validation (only 0 and 1 permitted)."""
    valid_scenario = SARScenario(
        name="ValidBinary",
        target_ids=["T1"],
        waypoint_ids=["W1"],
        coverage_matrix=[[1]],
        k_coverage=1,
    )
    assert valid_scenario.coverage_matrix[0][0] == 1

    # Non-binary value raises validation error
    with pytest.raises(ScenarioValidationError, match="binary"):
        SARScenario(
            name="InvalidBinary",
            target_ids=["T1"],
            waypoint_ids=["W1"],
            coverage_matrix=[[2]],
            k_coverage=1,
        )


def test_invalid_matrix_dimensions():
    """Requirement 4: Invalid matrix dimensions."""
    # Row count mismatch
    with pytest.raises(ScenarioValidationError, match="row count"):
        SARScenario(
            name="RowMismatch",
            target_ids=["T1", "T2"],
            waypoint_ids=["W1"],
            coverage_matrix=[[1]],  # 1 row instead of 2
            k_coverage=1,
        )

    # Column count mismatch
    with pytest.raises(ScenarioValidationError, match="length"):
        SARScenario(
            name="ColMismatch",
            target_ids=["T1"],
            waypoint_ids=["W1", "W2"],
            coverage_matrix=[[1]],  # 1 col instead of 2
            k_coverage=1,
        )


def test_invalid_k_values():
    """Requirement 5: Invalid k values (k < 1 must be rejected)."""
    with pytest.raises(ScenarioValidationError, match="k_coverage must be >= 1"):
        SARScenario(
            name="ZeroK",
            target_ids=["T1"],
            waypoint_ids=["W1"],
            coverage_matrix=[[1]],
            k_coverage=0,
        )

    with pytest.raises(ScenarioValidationError, match="k_coverage must be >= 1"):
        SARScenario(
            name="NegativeK",
            target_ids=["T1"],
            waypoint_ids=["W1"],
            coverage_matrix=[[1]],
            k_coverage=-2,
        )


def test_coverage_counts():
    """Requirement 6: Accurate coverage counting for single waypoints and subsets."""
    scenario = get_canonical_benchmark_scenario()

    # Selecting only W1 (index 0)
    # W1 covers T2, T3, T4, T5 (does not cover T1)
    counts_w1 = scenario.get_coverage_counts(["W1"])
    assert counts_w1["T1"] == 0
    assert counts_w1["T2"] == 1
    assert counts_w1["T3"] == 1
    assert counts_w1["T4"] == 1
    assert counts_w1["T5"] == 1

    # Selecting by integer indices [0, 1] -> W1 and W2
    counts_w1_w2 = scenario.get_coverage_counts([0, 1])
    # T1 covered by W2 (1)
    # T2 covered by W1 (1)
    # T3 covered by W1, W2 (2)
    # T4 covered by W1, W2 (2)
    # T5 covered by W1, W2 (2)
    assert counts_w1_w2 == {"T1": 1, "T2": 1, "T3": 2, "T4": 2, "T5": 2}


def test_feasibility_checking():
    """Requirement 7: Feasibility checking against k."""
    scenario = get_canonical_benchmark_scenario()

    # Empty selection is infeasible
    assert not scenario.is_feasible([])

    # Selection of W1, W2, W3 (size 3) cannot meet k=3 for T5 (since T5 has only 4 total covers)
    # Specifically, check counts
    assert not scenario.is_feasible([0, 1, 2])

    # Canonical known optimal subset: [W1, W2, W3, W4] -> indices [0, 1, 2, 3]
    # T1: W2, W3, W4 = 3
    # T2: W1, W3, W4 = 3
    # T3: W1, W2, W4 = 3
    # T4: W1, W2, W3 = 3
    # T5: W1, W2, W3, W4 = 4
    assert scenario.is_feasible([0, 1, 2, 3])
    assert scenario.calculate_coverage_ratio([0, 1, 2, 3]) == 1.0


def test_deficit_calculation():
    """Requirement 8: Deficit calculation: max(0, k - coverage_count)."""
    scenario = get_canonical_benchmark_scenario()
    # k = 3
    # If selection is empty: deficit is 3 for all targets
    deficits_empty = scenario.get_deficits([])
    for t_id in scenario.target_ids:
        assert deficits_empty[t_id] == 3

    # For [0, 1] (W1, W2): counts are {T1: 1, T2: 1, T3: 2, T4: 2, T5: 2}
    # deficits should be {T1: 2, T2: 2, T3: 1, T4: 1, T5: 1}
    deficits_w1_w2 = scenario.get_deficits([0, 1])
    assert deficits_w1_w2 == {"T1": 2, "T2": 2, "T3": 1, "T4": 1, "T5": 1}

    # For feasible selection [0, 1, 2, 3]: all deficits should be 0
    deficits_opt = scenario.get_deficits([0, 1, 2, 3])
    assert all(d == 0 for d in deficits_opt.values())


def test_empty_and_invalid_input_handling():
    """Requirement 16: Empty and invalid input handling."""
    # Empty name
    with pytest.raises(ScenarioValidationError, match="name"):
        SARScenario("   ", ["T1"], ["W1"], [[1]], 1)

    # Duplicate target IDs
    with pytest.raises(ScenarioValidationError, match="duplicate"):
        SARScenario("DupT", ["T1", "T1"], ["W1"], [[1], [1]], 1)

    # Duplicate waypoint IDs
    with pytest.raises(ScenarioValidationError, match="duplicate"):
        SARScenario("DupW", ["T1"], ["W1", "W1"], [[1, 1]], 1)

    # Empty target IDs
    with pytest.raises(ScenarioValidationError, match="target_ids"):
        SARScenario("EmptyT", [], ["W1"], [], 1)

    # Non-existent waypoint ID queried
    scenario = get_canonical_benchmark_scenario()
    with pytest.raises(KeyError, match="W999"):
        scenario.get_coverage_counts(["W999"])

    # Out of range waypoint index
    with pytest.raises(IndexError, match="out of range"):
        scenario.get_coverage_counts([99])


def test_spatial_generator_separation():
    """Verify abstract spatial sensing generator works independently and validates radius."""
    targets = [
        SpatialTarget(id="ST1", x=0.0, y=0.0),
        SpatialTarget(id="ST2", x=100.0, y=0.0),
    ]
    waypoints = [
        SpatialWaypoint(id="SW1", x=0.0, y=0.0),
        SpatialWaypoint(id="SW2", x=200.0, y=0.0),
    ]

    # Radius = 50: SW1 covers ST1 (dist 0), but not ST2 (dist 100); SW2 covers neither
    spatial_scenario = generate_spatial_scenario(
        name="SpatialTest",
        targets=targets,
        waypoints=waypoints,
        sensor_radius=50.0,
        k_coverage=1,
    )
    assert spatial_scenario.coverage_matrix == [
        [1, 0],  # ST1
        [0, 0],  # ST2
    ]

    # Non-positive radius raises error
    with pytest.raises(ScenarioValidationError, match="sensor_radius must be positive"):
        generate_spatial_scenario("BadRadius", targets, waypoints, sensor_radius=0.0, k_coverage=1)

