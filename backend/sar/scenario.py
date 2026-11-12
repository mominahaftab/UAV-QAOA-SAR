"""SAR Scenario and Coverage Model.

Defines the mathematical problem representation for k-coverage waypoint selection:
- Target locations: Points requiring observation.
- Candidate waypoints: Locations where a UAV can collect observations.
- Binary coverage matrix A in {0, 1}^(M x N), where A[j][i] == 1 if waypoint i covers target j.

IMPORTANT: Target locations and navigable UAV waypoint locations are separate concepts.
Coverage is an abstract sensing assumption and does not represent real RF measurements
or guarantee physical victim localization.
"""
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

from backend.solvers.base import OptimizationProblem


class ScenarioValidationError(ValueError):
    """Raised when scenario parameters or coverage matrix fail validation."""
    pass


@dataclass
class SARScenario:
    """Represents a discrete k-coverage Search and Rescue mission scenario.

    Attributes:
        name: Identifier for the scenario.
        target_ids: List of unique target identifiers (M targets).
        waypoint_ids: List of unique candidate waypoint identifiers (N waypoints).
        coverage_matrix: M x N matrix where row j corresponds to target_ids[j]
                         and column i corresponds to waypoint_ids[i].
        k_coverage: Minimum required sensing observations per target (k >= 1).
        waypoint_costs: Optional per-waypoint costs (default 1.0 each).
    """
    name: str
    target_ids: List[str]
    waypoint_ids: List[str]
    coverage_matrix: List[List[int]]
    k_coverage: int
    waypoint_costs: Optional[List[float]] = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate scenario consistency, dimensions, and matrix values."""
        if not self.name or not self.name.strip():
            raise ScenarioValidationError("Scenario name cannot be empty.")

        if self.k_coverage < 1:
            raise ScenarioValidationError(f"k_coverage must be >= 1, got {self.k_coverage}.")

        if not self.target_ids:
            raise ScenarioValidationError("target_ids must contain at least one target.")

        if not self.waypoint_ids:
            raise ScenarioValidationError("waypoint_ids must contain at least one candidate waypoint.")

        # Check uniqueness
        if len(set(self.target_ids)) != len(self.target_ids):
            raise ScenarioValidationError("target_ids contains duplicate identifiers.")

        if len(set(self.waypoint_ids)) != len(self.waypoint_ids):
            raise ScenarioValidationError("waypoint_ids contains duplicate identifiers.")

        num_targets = len(self.target_ids)
        num_waypoints = len(self.waypoint_ids)

        # Check matrix dimensions
        if len(self.coverage_matrix) != num_targets:
            raise ScenarioValidationError(
                f"Coverage matrix row count ({len(self.coverage_matrix)}) does not match "
                f"target count ({num_targets})."
            )

        for row_idx, row in enumerate(self.coverage_matrix):
            if len(row) != num_waypoints:
                raise ScenarioValidationError(
                    f"Row {row_idx} length ({len(row)}) does not match "
                    f"waypoint count ({num_waypoints})."
                )
            for col_idx, val in enumerate(row):
                if val not in (0, 1):
                    raise ScenarioValidationError(
                        f"Coverage matrix entries must be binary (0 or 1). "
                        f"Found {val} at row {row_idx}, col {col_idx}."
                    )

        if self.waypoint_costs is not None:
            if len(self.waypoint_costs) != num_waypoints:
                raise ScenarioValidationError(
                    f"waypoint_costs length ({len(self.waypoint_costs)}) does not match "
                    f"waypoint count ({num_waypoints})."
                )
            for c in self.waypoint_costs:
                if c < 0:
                    raise ScenarioValidationError(f"Waypoint cost cannot be negative: {c}")

    @property
    def num_targets(self) -> int:
        return len(self.target_ids)

    @property
    def num_waypoints(self) -> int:
        return len(self.waypoint_ids)

    def _normalize_waypoint_indices(self, selected: Iterable[Union[int, str]]) -> List[int]:
        """Convert a mix of waypoint IDs or integer indices into valid integer column indices."""
        indices: Set[int] = set()
        waypoint_to_idx = {wp_id: idx for idx, wp_id in enumerate(self.waypoint_ids)}

        for item in selected:
            if isinstance(item, int):
                if item < 0 or item >= self.num_waypoints:
                    raise IndexError(f"Waypoint index {item} out of range [0, {self.num_waypoints - 1}].")
                indices.add(item)
            elif isinstance(item, str):
                if item not in waypoint_to_idx:
                    raise KeyError(f"Waypoint ID '{item}' not found in scenario.")
                indices.add(waypoint_to_idx[item])
            else:
                raise TypeError(f"Selected item must be int or str, got {type(item)}.")

        return sorted(indices)

    def get_coverage_counts(self, selected: Iterable[Union[int, str]]) -> Dict[str, int]:
        """Compute the number of selected waypoints covering each target.

        Returns:
            Dict mapping target_id -> count of covering waypoints.
        """
        selected_indices = self._normalize_waypoint_indices(selected)
        counts: Dict[str, int] = {}
        for j, t_id in enumerate(self.target_ids):
            count = sum(self.coverage_matrix[j][i] for i in selected_indices)
            counts[t_id] = count
        return counts

    def get_deficits(self, selected: Iterable[Union[int, str]]) -> Dict[str, int]:
        """Compute remaining coverage deficit per target: max(0, k - coverage_count).

        Returns:
            Dict mapping target_id -> deficit count (0 means target requirement met).
        """
        counts = self.get_coverage_counts(selected)
        return {t_id: max(0, self.k_coverage - counts[t_id]) for t_id in self.target_ids}

    def is_feasible(self, selected: Iterable[Union[int, str]]) -> bool:
        """Return True if all targets receive at least k coverage."""
        deficits = self.get_deficits(selected)
        return all(deficit == 0 for deficit in deficits.values())

    def calculate_coverage_ratio(self, selected: Iterable[Union[int, str]]) -> float:
        """Percentage of targets meeting the k-coverage threshold (0.0 to 1.0)."""
        deficits = self.get_deficits(selected)
        satisfied = sum(1 for d in deficits.values() if d == 0)
        return satisfied / self.num_targets

    def calculate_objective(self, selected: Iterable[Union[int, str]]) -> float:
        """Calculate total objective value (sum of costs, or total selected waypoints)."""
        selected_indices = self._normalize_waypoint_indices(selected)
        if self.waypoint_costs is not None:
            return sum(self.waypoint_costs[i] for i in selected_indices)
        return float(len(selected_indices))

    def to_optimization_problem(self) -> OptimizationProblem:
        """Convert scenario into domain OptimizationProblem for solver consumption."""
        return OptimizationProblem(
            num_targets=self.num_targets,
            num_waypoints=self.num_waypoints,
            sensing_matrix=[row[:] for row in self.coverage_matrix],
            k_coverage=self.k_coverage,
            waypoint_costs=self.waypoint_costs[:] if self.waypoint_costs else None,
        )


def get_canonical_benchmark_scenario() -> SARScenario:
    """Return the exact, deterministic canonical benchmark scenario.

    5 targets, 6 candidate waypoints, k = 3.

    Coverage matrix (rows = targets T1..T5, columns = waypoints W1..W6):
    T1: [0, 1, 1, 1, 1, 1]
    T2: [1, 0, 1, 1, 1, 1]
    T3: [1, 1, 0, 1, 1, 1]
    T4: [1, 1, 1, 0, 1, 1]
    T5: [1, 1, 1, 1, 0, 0]

    Expected independently verifiable properties:
    - Minimum selected waypoints = 4.
    - Number of optimal combinations = 9.
    - Every optimal combination satisfies all 5 coverage constraints (k >= 3).
    """
    target_ids = ["T1", "T2", "T3", "T4", "T5"]
    waypoint_ids = ["W1", "W2", "W3", "W4", "W5", "W6"]
    coverage_matrix = [
        [0, 1, 1, 1, 1, 1],  # T1 covered by W2, W3, W4, W5, W6 (5 covers)
        [1, 0, 1, 1, 1, 1],  # T2 covered by W1, W3, W4, W5, W6 (5 covers)
        [1, 1, 0, 1, 1, 1],  # T3 covered by W1, W2, W4, W5, W6 (5 covers)
        [1, 1, 1, 0, 1, 1],  # T4 covered by W1, W2, W3, W5, W6 (5 covers)
        [1, 1, 1, 1, 0, 0],  # T5 covered by W1, W2, W3, W4         (4 covers)
    ]
    return SARScenario(
        name="Canonical-5T-6W-k3",
        target_ids=target_ids,
        waypoint_ids=waypoint_ids,
        coverage_matrix=coverage_matrix,
        k_coverage=3,
    )

