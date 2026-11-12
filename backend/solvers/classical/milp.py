"""Exact Classical Solvers for Minimum k-Coverage Waypoint Selection.

Implements:
1. SciPyMILPSolver: General scalable exact solver using scipy.optimize.milp.
2. BruteForceEnumerationValidator: Exhaustive validation solver for small instances (N <= 12).
"""
import itertools
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from backend.solvers.base import BaseSolver, OptimizationProblem, OptimizationResult


class SciPyMILPSolver(BaseSolver):
    """Exact solver formulating minimum k-coverage as a Binary Integer Linear Program (BILP).

    Mathematical Formulation:
        Minimize:
            sum_{i=1}^N c_i * x_i
        Subject to:
            sum_{i=1}^N A[j][i] * x_i >= k,   for all j in {1, ..., M}
            x_i in {0, 1},                     for all i in {1, ..., N}

    Utilizes `scipy.optimize.milp` with exact branch-and-cut.
    """

    @property
    def name(self) -> str:
        return "scipy_milp"

    def solve(self, problem: OptimizationProblem) -> OptimizationResult:
        start_time = time.perf_counter()

        m = problem.num_targets
        n = problem.num_waypoints
        k = problem.k_coverage

        # Validate basic problem dimensions
        if m == 0 or n == 0 or k < 1:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return OptimizationResult(
                solver_name=self.name,
                selected_waypoints=[],
                num_selected=0,
                is_feasible=False,
                coverage_achieved=0.0,
                execution_time_ms=elapsed_ms,
                cost=float("inf"),
                metadata={"status": "invalid_input", "message": "Empty targets, waypoints, or k < 1"},
            )

        # Objective coefficients (default unweighted: 1.0 per waypoint)
        if problem.waypoint_costs is not None and len(problem.waypoint_costs) == n:
            c = np.array(problem.waypoint_costs, dtype=np.float64)
        else:
            c = np.ones(n, dtype=np.float64)

        # Constraint matrix A (M x N)
        a_matrix = np.array(problem.sensing_matrix, dtype=np.float64)

        # Constraints: A @ x >= k  <=>  k <= A @ x <= inf
        lb = np.full(m, k, dtype=np.float64)
        ub = np.full(m, np.inf, dtype=np.float64)
        constraints = LinearConstraint(a_matrix, lb=lb, ub=ub)

        # Bounds: 0 <= x_i <= 1
        bounds = Bounds(lb=0.0, ub=1.0)

        # Integrality: 1 indicates integer (binary since bounds are [0, 1])
        integrality = np.ones(n, dtype=np.int8)

        # Run SciPy MILP
        res = milp(c=c, integrality=integrality, bounds=bounds, constraints=constraints)

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        if res.success and res.x is not None:
            # Round numerical solutions to exact binary integers
            x_sol = np.round(res.x).astype(int)
            selected = [i for i, val in enumerate(x_sol) if val == 1]

            # Verify coverage satisfaction independently
            counts = a_matrix @ x_sol
            satisfied = int(np.sum(counts >= k))
            coverage_achieved = satisfied / m
            is_feasible = (satisfied == m)

            return OptimizationResult(
                solver_name=self.name,
                selected_waypoints=selected,
                num_selected=len(selected),
                is_feasible=is_feasible,
                coverage_achieved=coverage_achieved,
                execution_time_ms=elapsed_ms,
                cost=float(res.fun),
                metadata={
                    "status_code": res.status,
                    "status_message": res.message,
                    "target_coverage_counts": counts.tolist(),
                },
            )
        else:
            # Infeasible or solver failure
            return OptimizationResult(
                solver_name=self.name,
                selected_waypoints=[],
                num_selected=0,
                is_feasible=False,
                coverage_achieved=0.0,
                execution_time_ms=elapsed_ms,
                cost=float("inf"),
                metadata={
                    "status_code": res.status,
                    "status_message": res.message,
                },
            )


@dataclass
class EnumerationResult:
    """Detailed output from brute-force combinatorial validation."""
    min_waypoints: int
    num_optimal_combinations: int
    optimal_combinations: List[List[int]]
    is_feasible: bool
    total_evaluated: int
    execution_time_ms: float


class BruteForceEnumerationValidator:
    """Independent brute-force validator for small problem instances (N <= 12).

    Exhaustively searches all 2^N waypoint subsets to identify all globally
    optimal combinations, verifying MILP results and canonical benchmarks.
    """

    def validate(self, problem: OptimizationProblem) -> EnumerationResult:
        start_time = time.perf_counter()
        m = problem.num_targets
        n = problem.num_waypoints
        k = problem.k_coverage

        if n > 16:
            raise ValueError(f"Enumeration validator only supports up to 16 waypoints, got {n}.")

        a_matrix = np.array(problem.sensing_matrix, dtype=int)
        min_opt_size = n + 1
        optimal_subsets: List[List[int]] = []
        total_evaluated = 0

        # Search by subset size from 0 to n
        for size in range(n + 1):
            if optimal_subsets and size > min_opt_size:
                # We already found the minimum cardinality optimal subsets
                break

            for combo in itertools.combinations(range(n), size):
                total_evaluated += 1
                if size == 0:
                    coverage = np.zeros(m, dtype=int)
                else:
                    coverage = np.sum(a_matrix[:, list(combo)], axis=1)

                if np.all(coverage >= k):
                    if size < min_opt_size:
                        min_opt_size = size
                        optimal_subsets = [list(combo)]
                    elif size == min_opt_size:
                        optimal_subsets.append(list(combo))

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        if optimal_subsets:
            return EnumerationResult(
                min_waypoints=min_opt_size,
                num_optimal_combinations=len(optimal_subsets),
                optimal_combinations=optimal_subsets,
                is_feasible=True,
                total_evaluated=total_evaluated,
                execution_time_ms=elapsed_ms,
            )
        else:
            return EnumerationResult(
                min_waypoints=-1,
                num_optimal_combinations=0,
                optimal_combinations=[],
                is_feasible=False,
                total_evaluated=total_evaluated,
                execution_time_ms=elapsed_ms,
            )

