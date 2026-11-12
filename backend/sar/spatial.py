"""Abstract Spatial Sensing-Disk Coverage Generator (Optional).

This module provides an optional geometric method to generate coverage matrices
based on Euclidean distance and an abstract sensing radius:
    A[j][i] = 1 if EuclideanDistance(target_j, waypoint_i) <= sensor_radius else 0

IMPORTANT DISCLAIMER:
This spatial generator uses an idealized geometric 2D line-of-sight disk model.
It is an abstract sensing abstraction and does NOT represent real RF propagation,
antenna patterns, path loss, multipath fading, or physical localization certainty.
It is kept strictly separate from the canonical benchmark dataset.
"""
import math
from dataclasses import dataclass
from typing import List, Optional

from backend.sar.scenario import SARScenario, ScenarioValidationError


@dataclass(frozen=True)
class SpatialTarget:
    """Target location requiring multi-coverage observation."""
    id: str
    x: float
    y: float
    priority: float = 1.0


@dataclass(frozen=True)
class SpatialWaypoint:
    """Candidate UAV sensing location."""
    id: str
    x: float
    y: float
    cost: float = 1.0


def generate_spatial_scenario(
    name: str,
    targets: List[SpatialTarget],
    waypoints: List[SpatialWaypoint],
    sensor_radius: float,
    k_coverage: int,
) -> SARScenario:
    """Construct a discrete SARScenario from 2D points using an abstract disk model.

    Args:
        name: Name of the generated scenario.
        targets: List of SpatialTarget instances.
        waypoints: List of SpatialWaypoint instances.
        sensor_radius: Idealized maximum sensing range (Euclidean distance).
        k_coverage: Required coverage redundancy per target (>= 1).

    Returns:
        Validated SARScenario instance.
    """
    if sensor_radius <= 0:
        raise ScenarioValidationError(f"sensor_radius must be positive, got {sensor_radius}")

    target_ids = [t.id for t in targets]
    waypoint_ids = [w.id for w in waypoints]
    waypoint_costs = [w.cost for w in waypoints]

    # Build binary sensing matrix A[j][i]
    coverage_matrix: List[List[int]] = []
    radius_sq = sensor_radius * sensor_radius

    for target in targets:
        row: List[int] = []
        for waypoint in waypoints:
            dx = target.x - waypoint.x
            dy = target.y - waypoint.y
            dist_sq = dx * dx + dy * dy
            is_covered = 1 if dist_sq <= radius_sq else 0
            row.append(is_covered)
        coverage_matrix.append(row)

    return SARScenario(
        name=name,
        target_ids=target_ids,
        waypoint_ids=waypoint_ids,
        coverage_matrix=coverage_matrix,
        k_coverage=k_coverage,
        waypoint_costs=waypoint_costs,
    )

