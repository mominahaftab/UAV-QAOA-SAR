"""Abstract Base Solver interface for UAV SAR Optimization.

Independent of web frameworks (FastAPI) and quantum libraries (Qiskit).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class OptimizationProblem:
    """Mathematical definition of the k-coverage waypoint selection problem.

    Attributes:
        num_targets: Number of ground targets M.
        num_waypoints: Number of candidate sensing waypoints N.
        sensing_matrix: M x N binary matrix where matrix[i][j] == 1 if waypoint j covers target i.
        k_coverage: Minimum required coverage redundancy per target.
        waypoint_costs: Optional cost weight for each waypoint.
    """
    num_targets: int
    num_waypoints: int
    sensing_matrix: List[List[int]]
    k_coverage: int
    waypoint_costs: Optional[List[float]] = None


@dataclass
class OptimizationResult:
    """Standardized result returned by all solvers.

    Attributes:
        solver_name: Identifier of the solver used.
        selected_waypoints: Indices of the selected waypoints.
        num_selected: Total count of selected waypoints.
        is_feasible: Whether all targets satisfy >= k coverage.
        coverage_achieved: Percentage of targets meeting >= k coverage (0.0 to 1.0).
        execution_time_ms: Solver runtime in milliseconds.
        cost: Total cost / objective value (e.g. number of waypoints chosen).
        metadata: Solver-specific diagnostic data (e.g., QAOA optimal angles, circuit depth).
    """
    solver_name: str
    selected_waypoints: List[int]
    num_selected: int
    is_feasible: bool
    coverage_achieved: float
    execution_time_ms: float
    cost: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseSolver(ABC):
    """Abstract solver interface ensuring uniform interaction across QAOA and classical solvers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the solver."""
        pass

    @abstractmethod
    def solve(self, problem: OptimizationProblem) -> OptimizationResult:
        """Execute optimization and return structured result."""
        pass

