"""QUBO to Ising Hamiltonian Conversion.

Maps binary variables z_i ∈ {0,1} to Ising spin variables s_i ∈ {-1,+1} via:
    z_i = (1 - Z_i) / 2

where Z_i is the Pauli-Z operator on qubit i.

For the QUBO energy:
    F = sum_i Q[i,i]*z_i + sum_{i<j} Q[i,j]*z_i*z_j + offset

After substitution z_i = (1 - Z_i) / 2:
    Linear term:   Q[i,i]*z_i = Q[i,i]*(1-Z_i)/2
                             = Q[i,i]/2  -  Q[i,i]/2 * Z_i
    Quadratic term: Q[i,j]*z_i*z_j = Q[i,j]*(1-Z_i)*(1-Z_j)/4
                                   = Q[i,j]/4 * (1 - Z_i - Z_j + Z_i*Z_j)

Collecting all terms:
    H_C = C_ising*I + sum_i h_i*Z_i + sum_{i<j} J_ij * Z_i Z_j

where:
    C_ising = offset + sum_i Q[i,i]/2 + sum_{i<j} Q[i,j]/4
    h_i = -Q[i,i]/2 + sum_{j≠i} (-Q[min(i,j),max(i,j)]/4)
        = -Q[i,i]/2 - (1/4)*sum_{j<i} Q[j,i] - (1/4)*sum_{j>i} Q[i,j]
    J_ij = Q[i,j]/4   for i < j

Qiskit Pauli-string bit ordering:
    SparsePauliOp uses a string where the RIGHTMOST character corresponds to qubit 0.
    For n=3: "ZIZ" means Z on qubit 2 and qubit 0.
    We therefore construct Pauli strings with character index = (n-1-qubit_index).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np
from qiskit.quantum_info import SparsePauliOp

from backend.solvers.qubo.formulation import QUBOProblem


@dataclass
class IsingHamiltonian:
    """Sparse Ising Hamiltonian representation.

    H_C = constant*I + sum_i h_i*Z_i + sum_{i<j} J_ij * Z_i Z_j

    Attributes:
        num_qubits: Total qubit count (equals num_variables in the QUBO).
        constant: Scalar energy offset (coefficient of identity).
        h: Linear Ising coefficients (length num_qubits), h[i] is coefficient of Z_i.
        J: Upper-triangular coupling matrix (num_qubits x num_qubits), J[i,j] for i<j.
        variable_map: Same variable-to-qubit mapping as the source QUBO.
        pauli_op: Qiskit SparsePauliOp representation of H_C.
    """
    num_qubits: int
    constant: float
    h: np.ndarray
    J: np.ndarray
    variable_map: Dict[str, int]
    pauli_op: SparsePauliOp

    def evaluate_ising(self, bits: np.ndarray) -> float:
        """Evaluate Ising energy for a binary bit assignment z ∈ {0,1}^n.

        Converts z -> s via s_i = 1 - 2*z_i (so z=0 -> s=+1, z=1 -> s=-1),
        then computes: H = constant + sum_i h_i*s_i + sum_{i<j} J_ij * s_i * s_j

        Args:
            bits: Binary array of length num_qubits.
        Returns:
            Scalar Ising energy.
        """
        z = np.asarray(bits, dtype=float)
        s = 1.0 - 2.0 * z  # z=0 -> s=+1, z=1 -> s=-1
        energy = self.constant
        energy += float(np.dot(self.h, s))
        for i in range(self.num_qubits):
            for j in range(i + 1, self.num_qubits):
                energy += self.J[i, j] * s[i] * s[j]
        return energy

    def evaluate_ising_fast(self, bits: np.ndarray) -> float:
        """Vectorized Ising energy evaluator."""
        z = np.asarray(bits, dtype=float)
        s = 1.0 - 2.0 * z
        energy = self.constant + float(np.dot(self.h, s))
        energy += float(s @ np.triu(self.J, 1) @ s)
        return energy


def qubo_to_ising(qubo: QUBOProblem) -> IsingHamiltonian:
    """Convert a QUBOProblem to an Ising Hamiltonian represented as SparsePauliOp.

    Uses the substitution z_i = (1 - Z_i)/2:
        Linear QUBO term:   Q[i,i]*z_i   ->  Q[i,i]/2 - Q[i,i]/2 * Z_i
        Quadratic QUBO term: Q[i,j]*z_i*z_j (i<j) ->
            Q[i,j]/4 * (I - Z_i - Z_j + Z_i*Z_j)

    Args:
        qubo: Fully constructed QUBOProblem with symmetric Q matrix.
    Returns:
        IsingHamiltonian with constant, h coefficients, J matrix, and SparsePauliOp.
    """
    n = qubo.num_variables
    Q = qubo.Q  # symmetric n x n
    offset = qubo.offset

    h = np.zeros(n, dtype=float)
    J = np.zeros((n, n), dtype=float)
    constant = offset  # start with QUBO constant offset

    # Linear terms from diagonal: Q[i,i]*z_i = Q[i,i]/2 - Q[i,i]/2 * Z_i
    for i in range(n):
        constant += Q[i, i] / 2.0
        h[i] += -Q[i, i] / 2.0

    # Quadratic terms from upper triangle: Q[i,j]*z_i*z_j = Q[i,j]/4*(1 - Z_i - Z_j + Z_i*Z_j)
    for i in range(n):
        for j in range(i + 1, n):
            q_ij = Q[i, j]  # == Q[j,i] since symmetric
            if abs(q_ij) < 1e-14:
                continue
            constant += q_ij / 4.0
            h[i] += -q_ij / 4.0
            h[j] += -q_ij / 4.0
            J[i, j] += q_ij / 4.0

    # Build SparsePauliOp
    # Qiskit convention: Pauli string "ZIIIIZ..." has rightmost char = qubit 0
    # So for qubit q, the character position in the string is (n-1-q)
    pauli_list: List[Tuple[str, complex]] = []

    # Identity (constant) — only needed if non-zero; SparsePauliOp handles it via simplify
    if abs(constant) > 1e-14:
        pauli_list.append(("I" * n, complex(constant)))

    # Single-Z terms
    for i in range(n):
        if abs(h[i]) > 1e-14:
            s = ["I"] * n
            s[n - 1 - i] = "Z"  # qubit i maps to position (n-1-i) in Pauli string
            pauli_list.append(("".join(s), complex(h[i])))

    # ZZ coupling terms
    for i in range(n):
        for j in range(i + 1, n):
            if abs(J[i, j]) > 1e-14:
                s = ["I"] * n
                s[n - 1 - i] = "Z"
                s[n - 1 - j] = "Z"
                pauli_list.append(("".join(s), complex(J[i, j])))

    if not pauli_list:
        pauli_list.append(("I" * n, 0.0 + 0j))

    pauli_op = SparsePauliOp.from_list(pauli_list).simplify()

    return IsingHamiltonian(
        num_qubits=n,
        constant=constant,
        h=h,
        J=J,
        variable_map=qubo.variable_map,
        pauli_op=pauli_op,
    )

