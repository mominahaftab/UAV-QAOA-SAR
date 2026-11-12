"""Unit and integration tests for the QAOA solver.

NOTE: These tests use p=1 and limited shots to keep runtime reasonable.
They verify correctness of circuit structure, decoding, and result fields —
not convergence to global optimum.

Scientific disclaimer: These tests run on a LOCAL Qiskit Aer SIMULATOR.
No quantum hardware is used. No quantum advantage is claimed.
"""
import warnings
import numpy as np
import pytest

from backend.sar.scenario import get_canonical_benchmark_scenario
from backend.solvers.base import OptimizationProblem
from backend.solvers.qubo.formulation import build_qubo
from backend.solvers.qubo.conversion import qubo_to_ising
from backend.solvers.qaoa.solver import (
    QAOASolver,
    _build_qaoa_circuit,
    _decode_bitstring,
    _check_feasibility,
    _compute_expectation_statevector,
)


@pytest.fixture(scope="module")
def canonical_scenario():
    return get_canonical_benchmark_scenario()


@pytest.fixture(scope="module")
def canonical_problem(canonical_scenario):
    return canonical_scenario.to_optimization_problem()


@pytest.fixture(scope="module")
def canonical_qubo(canonical_problem):
    return build_qubo(canonical_problem.sensing_matrix, k_coverage=3, penalty=7.0)


@pytest.fixture(scope="module")
def canonical_ising(canonical_qubo):
    return qubo_to_ising(canonical_qubo)


# ------------------------------------------------------------------
# Circuit structure tests
# ------------------------------------------------------------------

def test_qaoa_circuit_qubit_count(canonical_ising):
    """Circuit must have 16 qubits for the canonical 16-variable QUBO."""
    ansatz = _build_qaoa_circuit(canonical_ising.pauli_op, p=1)
    assert ansatz.num_qubits == 16


def test_qaoa_circuit_parameter_count_p1(canonical_ising):
    """p=1 circuit must have exactly 2 parameters (1 gamma, 1 beta)."""
    ansatz = _build_qaoa_circuit(canonical_ising.pauli_op, p=1)
    assert len(ansatz.parameters) == 2


def test_qaoa_circuit_parameter_count_p2(canonical_ising):
    """p=2 circuit must have exactly 4 parameters."""
    ansatz = _build_qaoa_circuit(canonical_ising.pauli_op, p=2)
    assert len(ansatz.parameters) == 4


def test_qaoa_circuit_can_be_simulated(canonical_ising):
    """Assigned circuit must run without error on AerSimulator."""
    from qiskit_aer import AerSimulator
    from qiskit import transpile

    ansatz = _build_qaoa_circuit(canonical_ising.pauli_op, p=1)
    bound = ansatz.assign_parameters([0.5, 0.3])
    qc = bound.copy()
    qc.measure_all()
    sim = AerSimulator(method="statevector")
    qc_t = transpile(qc, sim)
    result = sim.run(qc_t, shots=50, seed_simulator=0).result()
    counts = result.get_counts()
    assert sum(counts.values()) == 50


# ------------------------------------------------------------------
# Bitstring decoding tests
# ------------------------------------------------------------------

def test_decode_bitstring_all_zeros():
    """All-zeros bitstring -> all zero bits."""
    wp, sl = _decode_bitstring("0000000000000000", 16, 6, 5)
    assert wp == [0] * 6
    assert sl == [0] * 10


def test_decode_bitstring_all_ones():
    """All-ones bitstring -> all one bits."""
    wp, sl = _decode_bitstring("1111111111111111", 16, 6, 5)
    assert wp == [1] * 6
    assert sl == [1] * 10


def test_decode_bitstring_qubit_ordering():
    """Qiskit returns rightmost char = qubit 0.
    So "0000000000000001" -> qubit 0 = 1 -> x_0 = 1."""
    wp, sl = _decode_bitstring("0000000000000001", 16, 6, 5)
    assert wp[0] == 1  # x_0 selected
    assert all(wp[i] == 0 for i in range(1, 6))


def test_decode_bitstring_waypoint_w1_w2():
    """Bitstring encoding x_0=1, x_1=1, rest zero:
    qubit 0 = char at index 15 = '1', qubit 1 = char at index 14 = '1'."""
    # Build: 16-char string, rightmost=qubit0
    s = "0" * 14 + "11"  # chars: ...11 -> qubit1=1, qubit0=1
    wp, sl = _decode_bitstring(s, 16, 6, 5)
    assert wp[0] == 1
    assert wp[1] == 1
    assert all(wp[i] == 0 for i in range(2, 6))


# ------------------------------------------------------------------
# Feasibility checking tests
# ------------------------------------------------------------------

def test_feasibility_fully_covered(canonical_scenario):
    """Known feasible selection [W1,W2,W3,W4] = indices [0,1,2,3]."""
    bits = [1, 1, 1, 1, 0, 0]
    is_feas, ratio, counts = _check_feasibility(
        bits, canonical_scenario.coverage_matrix, k_coverage=3
    )
    assert is_feas is True
    assert ratio == 1.0
    assert all(c >= 3 for c in counts)


def test_feasibility_partially_covered(canonical_scenario):
    """Selection [W1] only: cannot satisfy k=3 for most targets."""
    bits = [1, 0, 0, 0, 0, 0]
    is_feas, ratio, counts = _check_feasibility(
        bits, canonical_scenario.coverage_matrix, k_coverage=3
    )
    assert is_feas is False
    assert ratio < 1.0


def test_feasibility_infeasible_returns_false_not_repaired(canonical_scenario):
    """Infeasible selections must NEVER be silently repaired."""
    bits = [0, 0, 0, 0, 0, 0]
    is_feas, ratio, counts = _check_feasibility(
        bits, canonical_scenario.coverage_matrix, k_coverage=3
    )
    assert is_feas is False
    assert ratio == 0.0


# ------------------------------------------------------------------
# Statevector expectation test
# ------------------------------------------------------------------

def test_expectation_is_finite(canonical_ising):
    """Statevector expectation at any fixed params must return a finite number."""
    ansatz = _build_qaoa_circuit(canonical_ising.pauli_op, p=1)
    exp_val = _compute_expectation_statevector(ansatz, canonical_ising.pauli_op, np.array([0.3, 0.2]))
    assert np.isfinite(exp_val), f"Expectation was not finite: {exp_val}"


# ------------------------------------------------------------------
# Full solver integration tests (lightweight: 100 shots, 50 iter)
# ------------------------------------------------------------------

@pytest.fixture(scope="module")
def qaoa_result_light(canonical_problem):
    """Run a lightweight QAOA solve for structural/integration testing."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        solver = QAOASolver(
            qaoa_depth=1,
            shots=100,
            penalty=7.0,
            optimizer="COBYLA",
            max_iterations=50,
            random_seed=42,
        )
        return solver.solve_qaoa(canonical_problem)


def test_qaoa_result_num_qubits(qaoa_result_light):
    assert qaoa_result_light.num_qubits == 16


def test_qaoa_result_depth(qaoa_result_light):
    assert qaoa_result_light.qaoa_depth_p == 1


def test_qaoa_result_gamma_beta_length(qaoa_result_light):
    assert len(qaoa_result_light.gamma) == 1
    assert len(qaoa_result_light.beta) == 1


def test_qaoa_result_gamma_beta_finite(qaoa_result_light):
    assert np.isfinite(qaoa_result_light.gamma).all()
    assert np.isfinite(qaoa_result_light.beta).all()


def test_qaoa_result_ising_expectation_finite(qaoa_result_light):
    assert np.isfinite(qaoa_result_light.ising_expectation)


def test_qaoa_result_shots_total(qaoa_result_light):
    total = qaoa_result_light.feasible_sample_count + qaoa_result_light.infeasible_sample_count
    assert total == 100


def test_qaoa_result_feasible_rate_in_range(qaoa_result_light):
    assert 0.0 <= qaoa_result_light.feasible_rate <= 1.0


def test_qaoa_result_no_silent_repair(qaoa_result_light):
    """If status is 'feasible', selected waypoints must actually satisfy coverage."""
    if qaoa_result_light.status == "feasible":
        from backend.sar.scenario import get_canonical_benchmark_scenario
        scenario = get_canonical_benchmark_scenario()
        assert scenario.is_feasible(qaoa_result_light.selected_waypoints) is True
        # Coverage ratio must be 1.0 for feasible result
        assert qaoa_result_light.coverage_achieved == 1.0
    elif qaoa_result_light.status == "no_feasible_sample":
        assert qaoa_result_light.selected_waypoints == []
        assert qaoa_result_light.is_feasible is False


def test_qaoa_result_no_infeasible_repaired_as_feasible(canonical_problem):
    """With a problem that is truly infeasible, solver must not invent a feasible result."""
    infeasible_problem = OptimizationProblem(
        num_targets=1,
        num_waypoints=2,
        sensing_matrix=[[1, 1]],  # Max coverage = 2 for any subset
        k_coverage=3,              # Impossible
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        solver = QAOASolver(shots=100, max_iterations=20, random_seed=0)
        result = solver.solve_qaoa(infeasible_problem)
    # Should report no feasible sample, not invent one
    assert result.is_feasible is False


def test_qaoa_base_solver_interface(canonical_problem):
    """QAOASolver must work through BaseSolver.solve() interface."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        solver = QAOASolver(shots=100, max_iterations=20, random_seed=0)
        result = solver.solve(canonical_problem)
    assert result.solver_name == "qaoa"
    assert isinstance(result.selected_waypoints, list)
    assert isinstance(result.is_feasible, bool)
    assert isinstance(result.execution_time_ms, float)


def test_qaoa_reproducibility_with_fixed_seed(canonical_problem):
    """Two runs with the same seed must return identical parameter values."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        solver1 = QAOASolver(shots=50, max_iterations=30, random_seed=777)
        solver2 = QAOASolver(shots=50, max_iterations=30, random_seed=777)
        r1 = solver1.solve_qaoa(canonical_problem)
        r2 = solver2.solve_qaoa(canonical_problem)
    # Optimized parameters should be identical across runs
    np.testing.assert_allclose(r1.gamma, r2.gamma, atol=1e-10)
    np.testing.assert_allclose(r1.beta, r2.beta, atol=1e-10)


def test_qaoa_metadata_populated(canonical_problem):
    """OptimizationResult metadata must be fully populated after solve()."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        solver = QAOASolver(shots=50, max_iterations=20, random_seed=0)
        result = solver.solve(canonical_problem)
    md = result.metadata
    assert "gamma" in md
    assert "beta" in md
    assert "qaoa_depth_p" in md
    assert "shots" in md
    assert "simulator_name" in md
    assert "is_quantum_simulation" in md
    assert md["quantum_advantage_claimed"] is False
    assert md["is_heuristic"] is True

