"""RF Propagation and Link-Budget Simulation for UAV Search-and-Rescue.

Computes wireless link budgets between ground targets (hypothetical beacon transmitters)
and UAV candidate waypoints (hypothetical RF receivers) using the Free-Space Path Loss (FSPL)
model and configurable excess environmental loss assumptions.

IMPORTANT SCIENTIFIC DISCLAIMER:
This module is a simplified simulation for mathematical optimization benchmarking.
It does NOT measure real radio-frequency signals, model physical antenna patterns,
multipath fading, terrain blockage, atmospheric ducting, or control physical UAVs.
Suburban and urban excess loss values are user-configurable assumptions, not certified
empirical channel propagation measurements.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from backend.sar.scenario import SARScenario, ScenarioValidationError


class EnvironmentType(str, Enum):
    """Propagation environment assumptions."""
    OPEN = "open"
    SUBURBAN = "suburban"
    URBAN = "urban"


# Default excess loss assumptions (in dB) per environment.
# These are clearly labelled simulation assumptions, not empirical channel measurements.
DEFAULT_EXCESS_LOSS_DB: Dict[EnvironmentType, float] = {
    EnvironmentType.OPEN: 0.0,
    EnvironmentType.SUBURBAN: 5.0,
    EnvironmentType.URBAN: 12.0,
}


class RFInputValidationError(ValueError):
    """Raised when RF simulation input parameters fail physical validation."""
    pass


@dataclass(frozen=True)
class RFTarget:
    """Ground search target with an RF beacon transmitter.
    
    Coordinates in local Cartesian metres.
    """
    id: str
    x: float
    y: float
    height_m: float = 1.5

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise RFInputValidationError("Target id cannot be empty.")
        if self.height_m < 0:
            raise RFInputValidationError(f"Target height cannot be negative: {self.height_m}")


@dataclass(frozen=True)
class RFWaypoint:
    """Candidate UAV sensing waypoint with an RF receiver.
    
    Coordinates in local Cartesian metres.
    """
    id: str
    x: float
    y: float
    altitude_m: float = 60.0
    cost: float = 1.0

    def __post_init__(self) -> None:
        if not self.id or not self.id.strip():
            raise RFInputValidationError("Waypoint id cannot be empty.")
        if self.altitude_m < 0:
            raise RFInputValidationError(f"UAV altitude cannot be negative: {self.altitude_m}")
        if self.cost < 0:
            raise RFInputValidationError(f"Waypoint cost cannot be negative: {self.cost}")


@dataclass
class RFConfig:
    """Configurable RF link budget and propagation parameters.
    
    All inputs have explicit units and strict physical bounds.
    """
    frequency_mhz: float = 2400.0           # Carrier frequency in MHz (> 0)
    tx_power_dbm: float = 20.0             # Transmitter power in dBm
    tx_antenna_gain_dbi: float = 2.0       # Transmitter antenna gain in dBi
    rx_antenna_gain_dbi: float = 2.0       # UAV receiver antenna gain in dBi
    rx_sensitivity_dbm: float = -100.0     # Receiver sensitivity in dBm
    system_loss_db: float = 3.0            # Additional system/cable losses in dB (>= 0)
    fade_margin_db: float = 10.0           # Fade margin in dB (>= 0)
    environment: EnvironmentType = EnvironmentType.OPEN
    excess_loss_db: Optional[float] = None # Configurable excess loss in dB (>= 0)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.frequency_mhz <= 0:
            raise RFInputValidationError(
                f"Carrier frequency must be strictly positive (> 0 MHz), got {self.frequency_mhz}"
            )
        if self.system_loss_db < 0:
            raise RFInputValidationError(
                f"System loss cannot be negative (>= 0 dB), got {self.system_loss_db}"
            )
        if self.fade_margin_db < 0:
            raise RFInputValidationError(
                f"Fade margin cannot be negative (>= 0 dB), got {self.fade_margin_db}"
            )
        if self.excess_loss_db is not None and self.excess_loss_db < 0:
            raise RFInputValidationError(
                f"Excess environmental loss cannot be negative (>= 0 dB), got {self.excess_loss_db}"
            )

    @property
    def effective_excess_loss_db(self) -> float:
        """Return configured excess loss or default assumption for the environment."""
        if self.excess_loss_db is not None:
            return float(self.excess_loss_db)
        return DEFAULT_EXCESS_LOSS_DB.get(self.environment, 0.0)

    @property
    def rx_threshold_dbm(self) -> float:
        """Received power required to declare reliable coverage:
        
        P_threshold = rx_sensitivity + fade_margin
        """
        return self.rx_sensitivity_dbm + self.fade_margin_db


@dataclass
class RFLinkResult:
    """Detailed link-budget calculation for a single target-waypoint pair."""
    target_id: str
    waypoint_id: str
    distance_3d_m: float
    distance_km: float
    fspl_db: float
    received_power_dbm: float
    threshold_dbm: float
    link_margin_db: float
    is_covered: bool


@dataclass
class RFSimulationResult:
    """Complete results from an RF scenario simulation."""
    scenario_name: str
    rf_config: RFConfig
    targets: List[RFTarget]
    waypoints: List[RFWaypoint]
    k_coverage: int
    links: List[RFLinkResult]
    coverage_matrix: List[List[int]]
    coverage_counts: Dict[str, int]
    unsatisfied_targets: List[str]
    is_feasible: bool

    def to_sar_scenario(self) -> SARScenario:
        """Convert simulation into a SARScenario for solver execution."""
        return SARScenario(
            name=self.scenario_name,
            target_ids=[t.id for t in self.targets],
            waypoint_ids=[w.id for w in self.waypoints],
            coverage_matrix=[row[:] for row in self.coverage_matrix],
            k_coverage=self.k_coverage,
            waypoint_costs=[w.cost for w in self.waypoints],
        )


def calculate_3d_distance(target: RFTarget, waypoint: RFWaypoint) -> float:
    """Calculate 3D Euclidean distance in metres between target and UAV waypoint.
    
    distance = sqrt((x_t - x_w)^2 + (y_t - y_w)^2 + (alt_w - h_t)^2)
    """
    dx = target.x - waypoint.x
    dy = target.y - waypoint.y
    dz = waypoint.altitude_m - target.height_m
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def calculate_fspl(distance_m: float, frequency_mhz: float) -> float:
    """Calculate Free-Space Path Loss in dB.
    
    FSPL(dB) = 32.44 + 20 * log10(distance_km) + 20 * log10(frequency_MHz)
    
    If distance is near zero, clamps to 0.1m to avoid mathematical singularity.
    """
    if frequency_mhz <= 0:
        raise RFInputValidationError(f"frequency_mhz must be > 0, got {frequency_mhz}")
    effective_dist_m = max(0.1, distance_m)
    distance_km = effective_dist_m / 1000.0
    return 32.44 + 20.0 * math.log10(distance_km) + 20.0 * math.log10(frequency_mhz)


def calculate_link_budget(
    target: RFTarget,
    waypoint: RFWaypoint,
    rf_config: RFConfig,
) -> RFLinkResult:
    """Compute the full link-budget between a target and a waypoint."""
    dist_3d = calculate_3d_distance(target, waypoint)
    dist_km = dist_3d / 1000.0
    fspl = calculate_fspl(dist_3d, rf_config.frequency_mhz)

    # Pr(dBm) = Pt + Gt + Gr - FSPL - Lsystem - Lexcess
    pr = (
        rf_config.tx_power_dbm
        + rf_config.tx_antenna_gain_dbi
        + rf_config.rx_antenna_gain_dbi
        - fspl
        - rf_config.system_loss_db
        - rf_config.effective_excess_loss_db
    )

    threshold = rf_config.rx_threshold_dbm
    margin = pr - threshold
    is_covered = pr >= threshold

    return RFLinkResult(
        target_id=target.id,
        waypoint_id=waypoint.id,
        distance_3d_m=round(dist_3d, 2),
        distance_km=round(dist_km, 4),
        fspl_db=round(fspl, 2),
        received_power_dbm=round(pr, 2),
        threshold_dbm=round(threshold, 2),
        link_margin_db=round(margin, 2),
        is_covered=is_covered,
    )


def simulate_rf_scenario(
    name: str,
    targets: List[RFTarget],
    waypoints: List[RFWaypoint],
    rf_config: RFConfig,
    k_coverage: int = 3,
) -> RFSimulationResult:
    """Simulate RF propagation for all target-waypoint pairs and produce a coverage matrix."""
    if not targets:
        raise RFInputValidationError("Target list cannot be empty.")
    if not waypoints:
        raise RFInputValidationError("Waypoint list cannot be empty.")
    if k_coverage < 1:
        raise RFInputValidationError(f"k_coverage must be >= 1, got {k_coverage}")

    links: List[RFLinkResult] = []
    coverage_matrix: List[List[int]] = []
    coverage_counts: Dict[str, int] = {t.id: 0 for t in targets}

    for target in targets:
        row: List[int] = []
        for waypoint in waypoints:
            link = calculate_link_budget(target, waypoint, rf_config)
            links.append(link)
            val = 1 if link.is_covered else 0
            row.append(val)
            if link.is_covered:
                coverage_counts[target.id] += 1
        coverage_matrix.append(row)

    unsatisfied = [t_id for t_id, cnt in coverage_counts.items() if cnt < k_coverage]
    is_feasible = len(unsatisfied) == 0

    return RFSimulationResult(
        scenario_name=name,
        rf_config=rf_config,
        targets=targets,
        waypoints=waypoints,
        k_coverage=k_coverage,
        links=links,
        coverage_matrix=coverage_matrix,
        coverage_counts=coverage_counts,
        unsatisfied_targets=unsatisfied,
        is_feasible=is_feasible,
    )


def get_deterministic_rf_demonstration_scenario(
    rf_config: Optional[RFConfig] = None,
    k_coverage: int = 3,
) -> RFSimulationResult:
    """Return the deterministic RF demonstration scenario defined in Section 3.
    
    Targets (transmitter positions, height = 1.5m):
        T1: (300, 300, 1.5)
        T2: (900, 350, 1.5)
        T3: (1500, 400, 1.5)
        T4: (600, 1200, 1.5)
        T5: (1300, 1250, 1.5)
        
    Candidate UAV waypoints (altitude = 60m):
        W1: (200, 200, 60)
        W2: (800, 250, 60)
        W3: (1400, 300, 60)
        W4: (400, 1100, 60)
        W5: (1100, 1100, 60)
        W6: (1550, 1350, 60)
        
    Illustrative default parameters:
        Frequency: 2400 MHz
        Tx Power: 20 dBm
        Tx Antenna Gain: 2 dBi
        UAV Rx Antenna Gain: 2 dBi
        Rx Sensitivity: -100 dBm
        System Loss: 3 dB
        Fade Margin: 10 dB
        Environment: Open / line-of-sight
        k = 3
    """
    targets = [
        RFTarget(id="T1", x=300.0, y=300.0, height_m=1.5),
        RFTarget(id="T2", x=900.0, y=350.0, height_m=1.5),
        RFTarget(id="T3", x=1500.0, y=400.0, height_m=1.5),
        RFTarget(id="T4", x=600.0, y=1200.0, height_m=1.5),
        RFTarget(id="T5", x=1300.0, y=1250.0, height_m=1.5),
    ]

    waypoints = [
        RFWaypoint(id="W1", x=200.0, y=200.0, altitude_m=60.0, cost=1.0),
        RFWaypoint(id="W2", x=800.0, y=250.0, altitude_m=60.0, cost=1.0),
        RFWaypoint(id="W3", x=1400.0, y=300.0, altitude_m=60.0, cost=1.0),
        RFWaypoint(id="W4", x=400.0, y=1100.0, altitude_m=60.0, cost=1.0),
        RFWaypoint(id="W5", x=1100.0, y=1100.0, altitude_m=60.0, cost=1.0),
        RFWaypoint(id="W6", x=1550.0, y=1350.0, altitude_m=60.0, cost=1.0),
    ]

    if rf_config is None:
        rf_config = RFConfig(
            frequency_mhz=2400.0,
            tx_power_dbm=20.0,
            tx_antenna_gain_dbi=2.0,
            rx_antenna_gain_dbi=2.0,
            rx_sensitivity_dbm=-100.0,
            system_loss_db=3.0,
            fade_margin_db=10.0,
            environment=EnvironmentType.OPEN,
            excess_loss_db=0.0,
        )

    return simulate_rf_scenario(
        name="RF Search-and-Rescue Demonstration — Synthetic Coordinates",
        targets=targets,
        waypoints=waypoints,
        rf_config=rf_config,
        k_coverage=k_coverage,
    )

