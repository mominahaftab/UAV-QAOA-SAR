"""SAR (Search and Rescue) sensing and geometry domain logic."""
from backend.sar.rf_propagation import (
    DEFAULT_EXCESS_LOSS_DB,
    EnvironmentType,
    RFConfig,
    RFInputValidationError,
    RFLinkResult,
    RFSimulationResult,
    RFTarget,
    RFWaypoint,
    calculate_3d_distance,
    calculate_fspl,
    calculate_link_budget,
    get_deterministic_rf_demonstration_scenario,
    simulate_rf_scenario,
)
from backend.sar.scenario import (
    SARScenario,
    ScenarioValidationError,
    get_canonical_benchmark_scenario,
)
from backend.sar.spatial import (
    SpatialTarget,
    SpatialWaypoint,
    generate_spatial_scenario,
)

__all__ = [
    "SARScenario",
    "ScenarioValidationError",
    "get_canonical_benchmark_scenario",
    "SpatialTarget",
    "SpatialWaypoint",
    "generate_spatial_scenario",
    "EnvironmentType",
    "DEFAULT_EXCESS_LOSS_DB",
    "RFInputValidationError",
    "RFTarget",
    "RFWaypoint",
    "RFConfig",
    "RFLinkResult",
    "RFSimulationResult",
    "calculate_3d_distance",
    "calculate_fspl",
    "calculate_link_budget",
    "simulate_rf_scenario",
    "get_deterministic_rf_demonstration_scenario",
]
