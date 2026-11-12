"""Unit tests for QUBO formulation.

Verifies:
- Correct variable count (16 total for 5T-6W-k3 canonical instance).
- Correct variable ordering and naming.
- Correct waypoint/slack separation.
- Penalty coefficient stored correctly.
- Direct penalty evaluator vs QUBO polynomial evaluator (must match).
- Known feasible assignment energy = 4.
- Infeasible assignment has energy > 4.
- All-zero assignment energy matches analytical expectation.
- Invalid inputs raise QUBOFormulationError.
"""
import numpy as np
import pytest

from backend.sar.scenario import get_canonical_benchmark_scenario
from backend.solvers.qubo.formulation import (
    QUBOFormulationError,
    QUBOProblem,
    build_qubo,
)


@pytest.fixture(scope="module")
def canonical_qubo():
    scenario = get_canonical_benchmark_scenario()
    return build_qubo(scenario.coverage_matrix, k_coverage=3, penalty=7.0)


@pytest.fixture(scope="module")
def canonical_A():
    scenario = get_canonical_benchmark_scenario()
    return np.array(scenario.coverage_matrix)


# ------------------------------------------------------------------
# Variable structure tests
# ------------------------------------------------------------------

def test_qubo_num_variables(canonical_qubo):
    """Requirement: 16 total variables (6 waypoints + 10 slacks for 5 targets)."""
    assert canonical_qubo.num_variables == 16


def test_qubo_num_waypoints(canonical_qubo):
    assert canonical_qubo.num_waypoints == 6


def test_qubo_num_targets(canonical_qubo):
    assert canonical_qubo.num_targets == 5


def test_qubo_q_matrix_shape(canonical_qubo):
    assert canonical_qubo.Q.shape == (16, 16)


def test_qubo_q_matrix_symmetric(canonical_qubo):
    """Q must be symmetric."""
    np.testing.assert_allclose(canonical_qubo.Q, canonical_qubo.Q.T, atol=1e-10)


def test_qubo_variable_ordering(canonical_qubo):
    """Variable map must have waypoints x_0..x_5 at indices 0..5,
    and slack b_j_0, b_j_1 at indices 6..15."""
    vm = canonical_qubo.variable_map
    # Waypoints
    for i in range(6):
        assert vm[f"x_{i}"] == i
    # Slacks: target j -> b_j_0 at 6+2j, b_j_1 at 6+2j+1
    for j in range(5):
        assert vm[f"b_{j}_0"] == 6 + 2 * j
        assert vm[f"b_{j}_1"] == 6 + 2 * j + 1


def test_qubo_waypoint_slack_separation(canonical_qubo):
    """First 6 indices are waypoints; indices 6-15 are slacks."""
    vm = canonical_qubo.variable_map
    waypoint_indices = {vm[f"x_{i}"] for i in range(6)}
    slack_indices = {vm[f"b_{j}_{k}"] for j in range(5) for k in range(2)}
    assert waypoint_indices == set(range(6))
    assert slack_indices == set(range(6, 16))
    assert waypoint_indices.isdisjoint(slack_indices)


def test_qubo_penalty_coefficient(canonical_qubo):
    assert canonical_qubo.penalty == 7.0


# ------------------------------------------------------------------
# Energy evaluator tests
# ------------------------------------------------------------------

def test_qubo_all_zero_assignment(canonical_qubo, canonical_A):
    """All-zero: objective=0, all constraints violated by k=3, so energy = 7*5*9 = 315."""
    bits = np.zeros(16, dtype=int)
    e_fast = canonical_qubo.evaluate_fast(bits)
    e_direct = canonical_qubo.evaluate_direct_penalty(bits, canonical_A)
    assert abs(e_fast - 315.0) < 1e-9
    assert abs(e_direct - 315.0) < 1e-9


def test_qubo_direct_vs_polynomial_all_zeros(canonical_qubo, canonical_A):
    bits = np.zeros(16, dtype=int)
    e_fast = canonical_qubo.evaluate_fast(bits)
    e_direct = canonical_qubo.evaluate_direct_penalty(bits, canonical_A)
    assert abs(e_fast - e_direct) < 1e-9


def test_qubo_known_feasible_assignment(canonical_qubo, canonical_A):
    """Select W1,W2,W3,W4 (indices 0,1,2,3) with correct slack bits.
    Coverage for T5: x0+x1+x2+x3 = 4 -> excess=1 -> b_40=1,b_41=0.
    All other targets get exactly 3 coverage -> excess=0.
    Expected QUBO energy = 4 (objective only, no constraint violation)."""
    bits = np.zeros(16, dtype=int)
    bits[:4] = 1          # x0,x1,x2,x3 = 1
    bits[6 + 2 * 4] = 1  # b_40 = 1 (T5 excess=1 = 1*1 + 2*0)
    e_fast = canonical_qubo.evaluate_fast(bits)
    e_direct = canonical_qubo.evaluate_direct_penalty(bits, canonical_A)
    assert abs(e_fast - 4.0) < 1e-9, f"Expected 4.0, got {e_fast}"
    assert abs(e_direct - 4.0) < 1e-9
    assert abs(e_fast - e_direct) < 1e-9


def test_qubo_infeasible_assignment_higher_energy(canonical_qubo, canonical_A):
    """Select only 2 waypoints: cannot satisfy k=3, so energy > 4."""
    bits = np.zeros(16, dtype=int)
    bits[0] = 1  # Only W1
    bits[1] = 1  # Only W2
    # Slacks at zero -> constraints violated
    e = canonical_qubo.evaluate_fast(bits)
    e_direct = canonical_qubo.evaluate_direct_penalty(bits, canonical_A)
    assert e > 4.0, f"Infeasible assignment should have energy > 4, got {e}"
    assert abs(e - e_direct) < 1e-9


def test_qubo_direct_vs_polynomial_random_assignments(canonical_qubo, canonical_A):
    """Direct and polynomial evaluators must match for random binary assignments."""
    rng = np.random.default_rng(1234)
    for _ in range(100):
        bits = rng.integers(0, 2, size=16)
        e_fast = canonical_qubo.evaluate_fast(bits)
        e_direct = canonical_qubo.evaluate_direct_penalty(bits, canonical_A)
        assert abs(e_fast - e_direct) < 1e-9, f"Mismatch: fast={e_fast}, direct={e_direct}, bits={bits}"


def test_qubo_minimum_energy_is_4(canonical_qubo, canonical_A):
    """The minimum QUBO energy over all 2^16 assignments should be 4.0."""
    min_energy = float("inf")
    min_bits = None
    for idx in range(2 ** 16):
        bits = np.array([(idx >> b) & 1 for b in range(16)], dtype=float)
        e = canonical_qubo.evaluate_fast(bits)
        if e < min_energy:
            min_energy = e
            min_bits = bits.copy()
    assert abs(min_energy - 4.0) < 1e-9, f"Expected minimum 4.0, got {min_energy}"
    # The minimum must correspond to a feasible waypoint selection
    wp_bits = min_bits[:6].astype(int).tolist()
    A = canonical_A
    counts = A @ np.array(wp_bits)
    assert np.all(counts >= 3), f"Min-energy assignment is infeasible: counts={counts}"


# ------------------------------------------------------------------
# Input validation tests
# ------------------------------------------------------------------

def test_qubo_invalid_non_binary_matrix():
    with pytest.raises(QUBOFormulationError, match="binary"):
        build_qubo([[1, 2, 1]], k_coverage=1, penalty=5.0)


def test_qubo_invalid_k_zero():
    with pytest.raises(QUBOFormulationError, match="k_coverage"):
        build_qubo([[1, 1]], k_coverage=0, penalty=5.0)


def test_qubo_invalid_negative_penalty():
    with pytest.raises(QUBOFormulationError, match="Penalty"):
        build_qubo([[1, 1]], k_coverage=1, penalty=-1.0)


def test_qubo_invalid_zero_penalty():
    with pytest.raises(QUBOFormulationError, match="Penalty"):
        build_qubo([[1, 1]], k_coverage=1, penalty=0.0)


def test_qubo_invalid_empty_matrix():
    with pytest.raises(QUBOFormulationError, match="2D|at least one"):
        build_qubo([], k_coverage=1, penalty=5.0)

