"""Greedy Heuristic Solver for Minimum k-Coverage Waypoint Selection.

NOTE: The greedy algorithm is a fast polynomial-time approximation heuristic.
It does NOT guarantee global optimality for the NP-hard k-coverage problem.
"""
import time
from typing import List, Set

import numpy as np

from backend.solvers.base import BaseSolver, OptimizationProblem, OptimizationResult


class GreedySolver(BaseSolver):
    """Greedy multi-coverage heuristic solver.

    At each iteration:
    1. Computes remaining coverage deficit for every target:
       deficit[j] = max(0, k - current_coverage[j])
    2. Identifies unselected waypoint i that maximizes reduction in total deficit:
       reduction[i] = sum_{j=1}^M min(A[j][i], deficit[j])
    3. Breaks ties deterministically by selecting the smallest waypoint index i.
    4. Terminates when total deficit reaches 0 (feasible) or when no remaining
       waypoint can reduce deficit (infeasible).
    """

    @property
    def name(self) -> str:
        return "greedy"

    def solve(self, problem: OptimizationProblem) -> OptimizationResult:
        start_time = time.perf_counter()

        m = problem.num_targets
        n = problem.num_waypoints
        k = problem.k_coverage

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
                metadata={"status": "invalid_input"},
            )

        a_matrix = np.array(problem.sensing_matrix, dtype=int)
        current_coverage = np.zeros(m, dtype=int)
        selected_waypoints: List[int] = []
        unselected_indices: Set[int] = set(range(n))

        step_history = []

        while unselected_indices:
            # Deficit per target
            deficits = np.maximum(0, k - current_coverage)
            total_deficit = int(np.sum(deficits))

            if total_deficit == 0:
                # All targets have >= k coverage
                break

            best_waypoint: int = -1
            max_reduction: int = 0

            # Deterministic scan in ascending index order
            for i in sorted(unselected_indices):
                # How much does adding waypoint i reduce total deficit?
                # A target can only reduce deficit by at most A[j, i], capped by deficit[j]
                waypoint_cover = a_matrix[:, i]
                reduction = int(np.sum(np.minimum(waypoint_cover, deficits)))

                # Strictly greater ensures deterministic tie-breaking by smallest index
                if reduction > max_reduction:
                    max_reduction = reduction
                    best_waypoint = i

            if best_waypoint == -1 or max_reduction == 0:
                # No remaining candidate waypoint can cover any target with deficit
                break

            # Select the chosen waypoint
            selected_waypoints.append(best_waypoint)
            unselected_indices.remove(best_waypoint)
            current_coverage += a_matrix[:, best_waypoint]

            step_history.append({
                "step": len(selected_waypoints),
                "selected_waypoint": best_waypoint,
                "deficit_reduction": max_reduction,
                "remaining_deficit": int(np.sum(np.maximum(0, k - current_coverage))),
            })

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        final_deficits = np.maximum(0, k - current_coverage)
        satisfied = int(np.sum(final_deficits == 0))
        coverage_achieved = satisfied / m
        is_feasible = (satisfied == m)

        cost = (
            sum(problem.waypoint_costs[i] for i in selected_waypoints)
            if problem.waypoint_costs
            else float(len(selected_waypoints))
        )

        return OptimizationResult(
            solver_name=self.name,
            selected_waypoints=selected_waypoints,
            num_selected=len(selected_waypoints),
            is_feasible=is_feasible,
            coverage_achieved=coverage_achieved,
            execution_time_ms=elapsed_ms,
            cost=cost if is_feasible else float("inf"),
            metadata={
                "step_history": step_history,
                "final_coverage_counts": current_coverage.tolist(),
                "final_deficits": final_deficits.tolist(),
                "is_heuristic": True,
            },
        )

