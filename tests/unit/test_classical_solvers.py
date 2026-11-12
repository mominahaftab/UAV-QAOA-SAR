"""Unit tests for classical solvers (SciPy MILP, BruteForce Enumeration, Greedy)."""
import pytest

from backend.sar.scenario import SARScenario, get_canonical_benchmark_scenario
from backend.solvers.base import OptimizationProblem
from backend.solvers.classical.greedy import GreedySolver
from backend.solvers.classical.milp import (
    BruteForceEnumerationValidator,
    SciPyMILPSolver,
)


@pytest.fixture
def canonical_scenario():
    return get_canonical_benchmark_scenario()


@pytest.fixture
def canonical_problem(canonical_scenario):
    return canonical_scenario.to_optimization_problem()


def test_exact_milp_optimum_on_canonical_benchmark(canonical_problem):
    """Requirement 9: Exact MILP optimum = 4."""
    solver = SciPyMILPSolver()
    result = solver.solve(canonical_problem)

    assert result.solver_name == "scipy_milp"
    assert result.is_feasible is True
    assert result.num_selected == 4
    assert result.cost == 4.0
    assert result.coverage_achieved == 1.0
    assert len(result.selected_waypoints) == 4


def test_enumeration_optimum_on_canonical_benchmark(canonical_problem):
    """Requirement 10: Enumeration optimum = 4."""
    validator = BruteForceEnumerationValidator()
    enum_res = validator.validate(canonical_problem)

    assert enum_res.is_feasible is True
    assert enum_res.min_waypoints == 4


def test_enumeration_identifies_exactly_9_optima(canonical_problem):
    """Requirement 11: Exactly 9 optimal combinations identified on canonical benchmark."""
    validator = BruteForceEnumerationValidator()
    enum_res = validator.validate(canonical_problem)

    assert enum_res.num_optimal_combinations == 9
    assert len(enum_res.optimal_combinations) == 9


def test_every_optimal_combination_is_feasible(canonical_scenario, canonical_problem):
    """Requirement 12: Every returned optimal combination must satisfy all five coverage constraints."""
    validator = BruteForceEnumerationValidator()
    enum_res = validator.validate(canonical_problem)

    for combo in enum_res.optimal_combinations:
        assert len(combo) == 4
        # Verify via scenario that this subset is completely feasible
        assert canonical_scenario.is_feasible(combo) is True
        counts = canonical_scenario.get_coverage_counts(combo)
        for t_id, cnt in counts.items():
            assert cnt >= 3, f"Target {t_id} received only {cnt} coverage in combo {combo}"


def test_greedy_solution_feasible_on_canonical_benchmark(canonical_problem, canonical_scenario):
    """Requirement 13: Greedy solution is feasible on the canonical benchmark."""
    solver = GreedySolver()
    result = solver.solve(canonical_problem)

    assert result.solver_name == "greedy"
    assert result.is_feasible is True
    assert result.coverage_achieved == 1.0
    assert canonical_scenario.is_feasible(result.selected_waypoints) is True

    # The greedy heuristic finds a valid feasible subset
    # On this canonical benchmark, greedy selects 4 waypoints
    assert result.num_selected in (4, 5)
    assert result.metadata["is_heuristic"] is True


def test_infeasible_scenario_handling():
    """Requirement 14: Infeasible scenario handling."""
    # Scenario where target 1 requires k=3, but only 2 waypoints cover it
    infeasible_problem = OptimizationProblem(
        num_targets=2,
        num_waypoints=3,
        sensing_matrix=[
            [1, 1, 0],  # T1 only covered by W0, W1 (max possible coverage = 2)
            [1, 1, 1],  # T2 covered by W0, W1, W2
        ],
        k_coverage=3,   # Requires 3 covers, which is impossible for T1
    )

    # Test SciPy MILP handles infeasibility cleanly
    milp_solver = SciPyMILPSolver()
    milp_res = milp_solver.solve(infeasible_problem)
    assert milp_res.is_feasible is False
    assert milp_res.cost == float("inf")
    assert milp_res.num_selected == 0
    assert milp_res.selected_waypoints == []

    # Test Greedy handles infeasibility cleanly
    greedy_solver = GreedySolver()
    greedy_res = greedy_solver.solve(infeasible_problem)
    assert greedy_res.is_feasible is False
    assert greedy_res.cost == float("inf")
    # greedy should have selected W0, W1, W2 and noticed remaining deficit cannot be reduced
    assert greedy_res.coverage_achieved < 1.0

    # Test Enumeration handles infeasibility
    validator = BruteForceEnumerationValidator()
    enum_res = validator.validate(infeasible_problem)
    assert enum_res.is_feasible is False
    assert enum_res.min_waypoints == -1
    assert enum_res.num_optimal_combinations == 0


def test_deterministic_greedy_tie_breaking(canonical_problem):
    """Requirement 15: Deterministic tie-breaking by waypoint ID so results are reproducible."""
    solver = GreedySolver()

    # Run solver multiple times
    res1 = solver.solve(canonical_problem)
    res2 = solver.solve(canonical_problem)
    res3 = solver.solve(canonical_problem)

    assert res1.selected_waypoints == res2.selected_waypoints == res3.selected_waypoints
    assert res1.cost == res2.cost == res3.cost
    assert res1.execution_time_ms >= 0.0

    # Specifically verify the tie-breaking on a symmetric 2-waypoint problem
    # Two identical waypoints W0 and W1 covering T0
    tie_problem = OptimizationProblem(
        num_targets=1,
        num_waypoints=2,
        sensing_matrix=[[1, 1]],
        k_coverage=1,
    )
    tie_res = solver.solve(tie_problem)
    # Tie broken by smallest index -> W0 (index 0) selected
    assert tie_res.selected_waypoints == [0]


def test_empty_and_zero_k_inputs():
    """Requirement 16 (solvers): Solvers safely handle degenerate inputs."""
    empty_problem = OptimizationProblem(
        num_targets=0,
        num_waypoints=0,
        sensing_matrix=[],
        k_coverage=0,
    )

    milp_solver = SciPyMILPSolver()
    res_milp = milp_solver.solve(empty_problem)
    assert res_milp.is_feasible is False
    assert res_milp.cost == float("inf")

    greedy_solver = GreedySolver()
    res_greedy = greedy_solver.solve(empty_problem)
    assert res_greedy.is_feasible is False
    assert res_greedy.cost == float("inf")

