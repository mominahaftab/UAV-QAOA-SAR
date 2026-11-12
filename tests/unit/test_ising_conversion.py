"""Unit tests for QUBO-to-Ising conversion.

Verifies:
- Constant offset is preserved correctly.
- h (linear) coefficients are correct.
- J (quadratic) coupling matrix is upper-triangular.
- SparsePauliOp has correct number of qubits.
- Variable-to-qubit mapping is preserved.
- QUBO energy == Ising energy for all 65,536 canonical basis states (exhaustive).
- Random assignment energy equivalence.
"""
import numpy as np
import pytest

from backend.sar.scenario import get_canonical_benchmark_scenario
from backend.solvers.qubo.formulation import build_qubo
from backend.solvers.qubo.conversion import qubo_to_ising


@pytest.fixture(scope="module")
def canonical_qubo():
    scenario = get_canonical_benchmark_scenario()
    return build_qubo(scenario.coverage_matrix, k_coverage=3, penalty=7.0)


@pytest.fixture(scope="module")
def canonical_ising(canonical_qubo):
    return qubo_to_ising(canonical_qubo)


# ------------------------------------------------------------------
# Structure tests
# ------------------------------------------------------------------

def test_ising_num_qubits(canonical_ising):
    assert canonical_ising.num_qubits == 16


def test_ising_pauli_op_num_qubits(canonical_ising):
    assert canonical_ising.pauli_op.num_qubits == 16


def test_ising_pauli_op_has_terms(canonical_ising):
    assert len(canonical_ising.pauli_op) > 0


def test_ising_h_shape(canonical_ising):
    assert canonical_ising.h.shape == (16,)


def test_ising_J_shape(canonical_ising):
    assert canonical_ising.J.shape == (16, 16)


def test_ising_J_is_upper_triangular(canonical_ising):
    """J matrix must only have entries in upper triangle (i < j)."""
    lower = np.tril(canonical_ising.J, -1)
    np.testing.assert_allclose(lower, 0.0, atol=1e-10)


def test_ising_variable_map_preserved(canonical_qubo, canonical_ising):
    """Variable map must match QUBO's map."""
    assert canonical_ising.variable_map == canonical_qubo.variable_map


def test_ising_pauli_string_length(canonical_ising):
    """All Pauli strings in SparsePauliOp must be length 16."""
    for label in canonical_ising.pauli_op.paulis.to_labels():
        assert len(label) == 16, f"Pauli string length mismatch: {label}"


# ------------------------------------------------------------------
# Energy equivalence tests
# ------------------------------------------------------------------

def test_ising_energy_all_zeros(canonical_qubo, canonical_ising):
    """All-zero assignment: QUBO and Ising energies must match."""
    bits = np.zeros(16, dtype=int)
    e_qubo = canonical_qubo.evaluate_fast(bits)
    e_ising = canonical_ising.evaluate_ising_fast(bits)
    assert abs(e_qubo - e_ising) < 1e-9, f"QUBO={e_qubo}, Ising={e_ising}"


def test_ising_energy_feasible_assignment(canonical_qubo, canonical_ising):
    """Known feasible assignment [W1,W2,W3,W4] with correct slacks: energy = 4.0."""
    bits = np.zeros(16, dtype=int)
    bits[:4] = 1          # x0,x1,x2,x3
    bits[6 + 2 * 4] = 1  # b_40 for T5 excess=1
    e_qubo = canonical_qubo.evaluate_fast(bits)
    e_ising = canonical_ising.evaluate_ising_fast(bits)
    assert abs(e_qubo - 4.0) < 1e-9
    assert abs(e_ising - 4.0) < 1e-9
    assert abs(e_qubo - e_ising) < 1e-9


def test_ising_energy_random_assignments(canonical_qubo, canonical_ising):
    """QUBO and Ising energies must match for 500 random binary assignments."""
    rng = np.random.default_rng(9999)
    for trial in range(500):
        bits = rng.integers(0, 2, size=16)
        e_qubo = canonical_qubo.evaluate_fast(bits)
        e_ising = canonical_ising.evaluate_ising_fast(bits)
        assert abs(e_qubo - e_ising) < 1e-9, (
            f"Trial {trial}: QUBO={e_qubo}, Ising={e_ising}, bits={bits}"
        )


def test_ising_exhaustive_all_65536_assignments(canonical_qubo, canonical_ising):
    """EXHAUSTIVE: QUBO == Ising energy for every one of the 2^16 = 65,536 basis states.

    A bit-ordering error in Pauli-string construction is a critical failure.
    This test catches it completely.
    """
    n = 16
    mismatches = 0
    first_mismatch = None

    for idx in range(2 ** n):
        bits = np.array([(idx >> b) & 1 for b in range(n)], dtype=float)
        e_qubo = canonical_qubo.evaluate_fast(bits)
        e_ising = canonical_ising.evaluate_ising_fast(bits)
        if abs(e_qubo - e_ising) > 1e-6:
            mismatches += 1
            if first_mismatch is None:
                first_mismatch = (idx, e_qubo, e_ising, bits.copy())

    if mismatches > 0:
        idx, eq, ei, bits = first_mismatch
        pytest.fail(
            f"Exhaustive QUBO-Ising mismatch: {mismatches} failures out of 65536. "
            f"First at idx={idx}: QUBO={eq}, Ising={ei}, bits={bits}"
        )


# ------------------------------------------------------------------
# Offset and coefficient sanity checks
# ------------------------------------------------------------------

def test_ising_constant_is_finite(canonical_ising):
    assert np.isfinite(canonical_ising.constant)


def test_ising_all_h_finite(canonical_ising):
    assert np.all(np.isfinite(canonical_ising.h))


def test_ising_all_J_finite(canonical_ising):
    assert np.all(np.isfinite(canonical_ising.J))

