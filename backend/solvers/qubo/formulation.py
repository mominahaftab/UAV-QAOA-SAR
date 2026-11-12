"""QUBO Formulation for the k-Coverage Waypoint Selection Problem.

Converts the k-coverage ILP into a Quadratic Unconstrained Binary Optimization (QUBO).

Variable ordering (canonical 5T-6W-k3 instance: 16 total qubits):
    Indices 0..N-1  : waypoint decision variables x_0, ..., x_{N-1}
    Indices N..N+2*M-1: slack variables  b_j0, b_j1 for target j=0..M-1
        b_j0 at index N + 2*j
        b_j1 at index N + 2*j + 1
    s_j = b_j0 + 2*b_j1  captures excess coverage 0,1,2,3

Coverage constraint for target j:
    sum_i A[j][i] * x_i - k - b_j0 - 2*b_j1 = 0

QUBO objective (upper-triangular convention, diagonal = linear terms):
    F(z) = sum_i x_i  +  penalty * sum_j (sum_i A[j][i]*x_i - k - b_j0 - 2*b_j1)^2

The Q matrix is symmetric; off-diagonal entries Q[p][q] (p<q) represent interactions z_p*z_q.
Diagonal entries Q[i][i] represent linear z_i terms (after applying z_i^2 = z_i).

References:
    Lucas (2014), Ising formulations of many NP problems.
    doi:10.3389/fphy.2014.00005
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import numpy as np


class QUBOFormulationError(ValueError):
    """Raised when QUBO inputs are invalid."""
    pass


@dataclass
class QUBOProblem:
    """Container for a fully-specified QUBO problem.

    Attributes:
        num_variables: Total binary variables (waypoints + slack).
        num_waypoints: N — waypoint decision variables (first N indices).
        num_targets: M — target coverage constraints.
        k_coverage: Required coverage per target.
        penalty: Penalty coefficient A_penalty for constraint violations.
        Q: Symmetric N_vars x N_vars QUBO coefficient matrix.
            F(z) = z^T Q z  where Q is symmetric and diagonal stores linear terms.
            Equivalently F = sum_{i<=j} Q[i][j] * z_i * z_j  (using binary identity z_i^2=z_i
            absorbed into diagonal).
        offset: Constant energy offset from constraint expansion.
        variable_map: Maps variable name strings to column indices.
    """
    num_variables: int
    num_waypoints: int
    num_targets: int
    k_coverage: int
    penalty: float
    Q: np.ndarray  # shape (num_variables, num_variables), symmetric
    offset: float
    variable_map: Dict[str, int]

    def variable_names(self) -> List[str]:
        """Return variable names in index order."""
        return sorted(self.variable_map, key=lambda k: self.variable_map[k])

    def evaluate(self, bits: np.ndarray) -> float:
        """Evaluate QUBO energy for a binary assignment.

        Uses z^T Q z convention with symmetric Q (but sums over all i,j to avoid 
        double-counting off-diagonal terms the matrix is stored symmetrically, 
        so we use z @ Q @ z / 1 is NOT correct for symmetric Q; we use the 
        upper-triangle convention):
            F = sum_i Q[i,i]*z_i + sum_{i<j} Q[i,j]*z_i*z_j

        Args:
            bits: Binary array of length num_variables.
        Returns:
            Scalar QUBO energy.
        """
        z = np.asarray(bits, dtype=float)
        # Linear terms (diagonal)
        energy = float(np.dot(np.diag(self.Q), z))
        # Quadratic terms (strict upper triangle, stored symmetrically)
        n = self.num_variables
        for i in range(n):
            for j in range(i + 1, n):
                energy += self.Q[i, j] * z[i] * z[j]
        return energy + self.offset

    def evaluate_fast(self, bits: np.ndarray) -> float:
        """Vectorized QUBO energy evaluator (upper-triangle convention).
        
        F = diag(Q)·z + (z outer z upper-tri without diagonal)·Q upper-tri
        Equivalent to: diag(Q)·z + z^T * triu(Q,1) * z
        """
        z = np.asarray(bits, dtype=float)
        Q_upper = np.triu(self.Q, 1)
        return float(np.dot(np.diag(self.Q), z) + z @ Q_upper @ z) + self.offset

    def evaluate_direct_penalty(self, bits: np.ndarray, A: np.ndarray) -> float:
        """Evaluate the original penalty expression directly (ground truth for testing).

        F_direct = sum_i x_i + penalty * sum_j (sum_i A[j,i]*x_i - k - b_j0 - 2*b_j1)^2

        Args:
            bits: Full binary assignment (length num_variables).
            A: Coverage matrix M x N (numpy int array).
        Returns:
            Scalar energy from direct expression.
        """
        N = self.num_waypoints
        M = self.num_targets
        k = self.k_coverage
        x = bits[:N].astype(float)
        objective = float(np.sum(x))
        penalty_sum = 0.0
        for j in range(M):
            b0 = bits[N + 2 * j]
            b1 = bits[N + 2 * j + 1]
            coverage = float(np.dot(A[j], x))
            residual = coverage - k - b0 - 2 * b1
            penalty_sum += residual * residual
        return objective + self.penalty * penalty_sum


def build_qubo(
    coverage_matrix: List[List[int]],
    k_coverage: int,
    penalty: float = 7.0,
) -> QUBOProblem:
    """Build the QUBO matrix for the k-coverage problem.

    Variable layout:
        [x_0, ..., x_{N-1}, b_00, b_01, b_10, b_11, ..., b_{M-1,0}, b_{M-1,1}]

    Total variables: N + 2*M.

    The QUBO is derived by expanding the squared penalty terms and collecting
    coefficients, applying z_i^2 = z_i to reduce all squared terms.

    The resulting matrix Q is symmetric with:
        Q[i,i]  = linear coefficient of z_i  (from objective + penalty expansion)
        Q[i,j]  = Q[j,i] = coefficient of z_i*z_j  (from penalty cross terms)
    
    The energy is evaluated as:
        F = sum_i Q[i,i]*z_i + sum_{i<j} Q[i,j]*z_i*z_j + offset

    Args:
        coverage_matrix: M x N binary sensing matrix (A[j][i]=1 if waypoint i covers target j).
        k_coverage: Required coverage per target k >= 1.
        penalty: Penalty coefficient (default 7.0 for canonical 5T-6W-k3 instance).

    Returns:
        QUBOProblem instance with fully constructed Q matrix, offset, and variable map.

    Raises:
        QUBOFormulationError: On invalid inputs.
    """
    A = np.array(coverage_matrix, dtype=float)
    if A.ndim != 2:
        raise QUBOFormulationError("coverage_matrix must be 2D.")
    M, N = A.shape
    if M == 0 or N == 0:
        raise QUBOFormulationError("Coverage matrix must have at least one target and waypoint.")
    if k_coverage < 1:
        raise QUBOFormulationError(f"k_coverage must be >= 1, got {k_coverage}.")
    if penalty <= 0:
        raise QUBOFormulationError(f"Penalty must be positive, got {penalty}.")
    if not np.all((A == 0) | (A == 1)):
        raise QUBOFormulationError("Coverage matrix must be binary (0 or 1).")

    # Number of slack variables: 2 per target (b_j0, b_j1 encoding excess 0..3)
    num_slack = 2 * M
    num_vars = N + num_slack

    # Build variable name map
    variable_map: Dict[str, int] = {}
    for i in range(N):
        variable_map[f"x_{i}"] = i
    for j in range(M):
        variable_map[f"b_{j}_0"] = N + 2 * j
        variable_map[f"b_{j}_1"] = N + 2 * j + 1

    # Initialize Q matrix and offset accumulator
    Q = np.zeros((num_vars, num_vars), dtype=float)
    offset = 0.0

    # --- Objective term: sum_i x_i ---
    for i in range(N):
        Q[i, i] += 1.0

    # --- Penalty terms: penalty * sum_j (R_j)^2 ---
    # For target j: R_j = sum_i A[j,i]*x_i - k - b_j0 - 2*b_j1
    # Expanding (R_j)^2:
    #   = (sum_i A[j,i]*x_i)^2  (waypoint-waypoint cross terms)
    #   - 2k * (sum_i A[j,i]*x_i)  (k times linear waypoint terms)
    #   - 2 * b_j0 * (sum_i A[j,i]*x_i)  (b0-waypoint cross)
    #   - 4 * b_j1 * (sum_i A[j,i]*x_i)  (b1-waypoint cross, coeff 2 for b_j1)
    #   + k^2  (constant)
    #   + 2k * b_j0 + 4k * b_j1  (k-slack cross terms)
    #   + b_j0^2 + 4*b_j1^2 + 4*b_j0*b_j1  (slack-slack)
    #
    # Using z^2 = z for binary variables:
    #   b_j0^2 -> b_j0,  b_j1^2 -> b_j1
    #   x_i^2 -> x_i,    A[j,i]^2*x_i^2 -> A[j,i]^2*x_i = A[j,i]*x_i (since A binary)

    for j in range(M):
        b0_idx = N + 2 * j
        b1_idx = N + 2 * j + 1

        # Constant from k^2
        offset += penalty * float(k_coverage * k_coverage)

        # 1. Diagonal terms from (sum_i A[j,i]*x_i)^2: A[j,i]^2*x_i -> A[j,i]*x_i
        for i in range(N):
            # A[j,i]^2 * x_i^2 = A[j,i] * x_i  (since A binary and z^2=z)
            Q[i, i] += penalty * A[j, i]

        # 2. Cross terms x_i * x_l (i < l)
        for i in range(N):
            for l in range(i + 1, N):
                # 2 * A[j,i] * A[j,l] * x_i * x_l (factor 2 from symmetric expansion)
                Q[i, l] += penalty * 2.0 * A[j, i] * A[j, l]

        # 3. Linear: -2k * sum_i A[j,i] * x_i
        for i in range(N):
            Q[i, i] += penalty * (-2.0 * k_coverage) * A[j, i]

        # 4. Cross: -2 * b_j0 * sum_i A[j,i] * x_i
        for i in range(N):
            # b0_idx < i or b0_idx > i; use symmetric storage
            p, q = (i, b0_idx) if i < b0_idx else (b0_idx, i)
            Q[p, q] += penalty * (-2.0) * A[j, i]

        # 5. Cross: -4 * b_j1 * sum_i A[j,i] * x_i  (coefficient of b_j1 in R_j is -2)
        for i in range(N):
            p, q = (i, b1_idx) if i < b1_idx else (b1_idx, i)
            Q[p, q] += penalty * (-4.0) * A[j, i]

        # 6. +2k * b_j0  (from -2*k * -b_j0 = +2k*b_j0)
        Q[b0_idx, b0_idx] += penalty * 2.0 * k_coverage

        # 7. +4k * b_j1
        Q[b1_idx, b1_idx] += penalty * 4.0 * k_coverage

        # 8. b_j0^2 -> b_j0 (diagonal)
        Q[b0_idx, b0_idx] += penalty * 1.0

        # 9. 4*b_j1^2 -> 4*b_j1 (diagonal), since b_j1^2 = b_j1
        Q[b1_idx, b1_idx] += penalty * 4.0

        # 10. 4*b_j0*b_j1 (off-diagonal)
        Q[b0_idx, b1_idx] += penalty * 4.0

    # Symmetrize Q (upper triangle was set; mirror to lower)
    Q = Q + Q.T - np.diag(np.diag(Q))
    # But we evaluate using upper-triangle only convention, so the symmetrization
    # is just for reference — the evaluate_fast method uses triu(Q,1) for off-diagonal.

    return QUBOProblem(
        num_variables=num_vars,
        num_waypoints=N,
        num_targets=M,
        k_coverage=k_coverage,
        penalty=penalty,
        Q=Q,
        offset=offset,
        variable_map=variable_map,
    )

