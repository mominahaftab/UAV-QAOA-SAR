"""Integration test: Classical vs QAOA solver comparison on the canonical benchmark.

Verifies that all Phase 2 classical solvers remain functional and that QAOA
results can be meaningfully compared against them.

SCIENTIFIC NOTE: This test verifies solver integration and result structure.
It does NOT claim that QAOA outperforms classical solvers or demonstrates
quantum advantage on this small simulated benchmark.
"""
import warnings
import numpy as np
import pytest

from backend.sar.scenario import get_canonical_benchmark_scenario
from backend.solvers.classical.milp import SciPyMILPSolver, BruteForceEnumerationValidator
from backend.solvers.classical.greedy import GreedySolver
from backend.solvers.qaoa.solver import QAOASolver


@pytest.fixture(scope="module")
def canonical_scenario():
    return get_canonical_benchmark_scenario()


@pytest.fixture(scope="module")
def canonical_problem(canonical_scenario):
    return canonical_scenario.to_optimization_problem()


@pytest.fixture(scope="module")
def milp_result(canonical_problem):
    return SciPyMILPSolver().solve(canonical_problem)


@pytest.fixture(scope="module")
def enum_result(canonical_problem):
    return BruteForceEnumerationValidator().validate(canonical_problem)


@pytest.fixture(scope="module")
def greedy_result(canonical_problem):
    return GreedySolver().solve(canonical_problem)


@pytest.fixture(scope="module")
def qaoa_result(canonical_problem):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        solver = QAOASolver(
            qaoa_depth=1, shots=200, penalty=7.0,
            optimizer="COBYLA", max_iterations=50, random_seed=42,
        )
        return solver.solve(canonical_problem)


# ------------------------------------------------------------------
# Phase 2 classical solvers remain functional
# ------------------------------------------------------------------

def test_milp_still_optimal(milp_result):
    assert milp_result.is_feasible is True
    assert milp_result.num_selected == 4


def test_enumeration_still_9_optima(enum_result):
    assert enum_result.min_waypoints == 4
    assert enum_result.num_optimal_combinations == 9


def test_greedy_still_feasible(greedy_result):
    assert greedy_result.is_feasible is True


# ------------------------------------------------------------------
# QAOA integrates with existing problem model
# ------------------------------------------------------------------

def test_qaoa_uses_base_solver_interface(qaoa_result):
    assert qaoa_result.solver_name == "qaoa"
    assert hasattr(qaoa_result, "selected_waypoints")
    assert hasattr(qaoa_result, "is_feasible")
    assert hasattr(qaoa_result, "coverage_achieved")
    assert hasattr(qaoa_result, "execution_time_ms")
    assert hasattr(qaoa_result, "metadata")


def test_qaoa_metadata_has_quantum_flags(qaoa_result):
    assert qaoa_result.metadata["is_quantum_simulation"] is True
    assert qaoa_result.metadata["quantum_advantage_claimed"] is False


def test_qaoa_feasible_result_matches_coverage_matrix(canonical_scenario, qaoa_result):
    """If QAOA reports feasible, verify independently against coverage model."""
    if qaoa_result.is_feasible:
        assert canonical_scenario.is_feasible(qaoa_result.selected_waypoints) is True
        counts = canonical_scenario.get_coverage_counts(qaoa_result.selected_waypoints)
        for t_id, count in counts.items():
            assert count >= 3, f"Target {t_id} has only {count} coverage"


def test_qaoa_no_infeasible_repaired_silently(qaoa_result):
    """If QAOA reports infeasible (no_feasible_sample), selected_waypoints must be empty."""
    if not qaoa_result.is_feasible:
        assert qaoa_result.selected_waypoints == []
        assert qaoa_result.cost == float("inf")


def test_comparison_all_solvers_complete(milp_result, greedy_result, qaoa_result):
    """All four solvers must produce valid results (no uncaught exceptions)."""
    for result in [milp_result, greedy_result, qaoa_result]:
        assert isinstance(result.is_feasible, bool)
        assert isinstance(result.selected_waypoints, list)
        assert result.execution_time_ms >= 0.0

