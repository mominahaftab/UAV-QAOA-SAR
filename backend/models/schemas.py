"""Pydantic request and response schemas for UAV-QAOA-SAR API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class TargetPoint(BaseModel):
    id: str
    x: float
    y: float
    height_m: float = 1.5
    priority: float = 1.0


class WaypointPoint(BaseModel):
    id: str
    x: float
    y: float
    altitude_m: float = 60.0
    cost: float = 1.0


class RFConfigDTO(BaseModel):
    frequency_mhz: float = Field(default=2400.0, gt=0, description="Carrier frequency in MHz (> 0)")
    tx_power_dbm: float = Field(default=20.0, description="Transmitter power in dBm")
    tx_antenna_gain_dbi: float = Field(default=2.0, description="Transmitter antenna gain in dBi")
    rx_antenna_gain_dbi: float = Field(default=2.0, description="UAV receiver antenna gain in dBi")
    rx_sensitivity_dbm: float = Field(default=-100.0, description="Receiver sensitivity in dBm")
    system_loss_db: float = Field(default=3.0, ge=0, description="System/cable losses in dB (>= 0)")
    fade_margin_db: float = Field(default=10.0, ge=0, description="Fade margin in dB (>= 0)")
    environment: str = Field(default="open", description="open | suburban | urban")
    excess_loss_db: Optional[float] = Field(default=None, ge=0, description="Explicit excess environmental loss in dB")
    uav_altitude_m: float = Field(default=60.0, ge=0, description="UAV altitude in metres (>= 0)")
    target_height_m: float = Field(default=1.5, ge=0, description="Target transmitter height in metres (>= 0)")


class RFLinkResultDTO(BaseModel):
    target_id: str
    waypoint_id: str
    distance_3d_m: float
    distance_km: float
    fspl_db: float
    received_power_dbm: float
    threshold_dbm: float
    link_margin_db: float
    is_covered: bool


class ScenarioSummaryDTO(BaseModel):
    id: str
    name: str
    target_count: int
    waypoint_count: int
    k_coverage: int
    description: str = ""
    scenario_type: str = "synthetic"  # "synthetic" | "rf_simulation"


class ScenarioDetailDTO(BaseModel):
    id: str
    name: str
    target_ids: List[str]
    waypoint_ids: List[str]
    coverage_matrix: List[List[int]]
    k_coverage: int
    targets: Optional[List[TargetPoint]] = None
    waypoints: Optional[List[WaypointPoint]] = None
    rf_config: Optional[RFConfigDTO] = None
    rf_links: Optional[List[RFLinkResultDTO]] = None
    scenario_type: str = "synthetic"


class RFSimulationRequestDTO(BaseModel):
    scenario_name: Optional[str] = "RF Simulation Scenario"
    rf_config: RFConfigDTO = Field(default_factory=RFConfigDTO)
    k_coverage: int = Field(default=3, ge=1, le=10)
    targets: Optional[List[TargetPoint]] = None
    waypoints: Optional[List[WaypointPoint]] = None


class RFSimulationResponseDTO(BaseModel):
    scenario_name: str
    rf_config: RFConfigDTO
    k_coverage: int
    target_ids: List[str]
    waypoint_ids: List[str]
    coverage_matrix: List[List[int]]
    coverage_counts: Dict[str, int]
    unsatisfied_targets: List[str]
    is_feasible: bool
    links: List[RFLinkResultDTO]
    targets: List[TargetPoint]
    waypoints: List[WaypointPoint]


class OptimizeRequestDTO(BaseModel):
    scenario_id: Optional[str] = "canonical"
    target_ids: Optional[List[str]] = None
    waypoint_ids: Optional[List[str]] = None
    coverage_matrix: Optional[List[List[int]]] = None
    k_coverage: Optional[int] = Field(default=3, ge=1, le=10)
    solver_name: str = Field(default="qaoa", description="milp | brute_force | greedy | qaoa")
    qaoa_depth: int = Field(default=1, ge=1, le=5)
    shots: int = Field(default=500, ge=50, le=10000)
    penalty: float = Field(default=7.0, gt=0)
    max_iterations: int = Field(default=50, ge=5, le=500)
    random_seed: int = Field(default=42)
    rf_config: Optional[RFConfigDTO] = None

    @field_validator("solver_name")
    @classmethod
    def validate_solver_name(cls, v: str) -> str:
        clean = v.lower().strip()
        allowed = {"milp", "scipy_milp", "brute_force", "enumeration", "greedy", "qaoa"}
        if clean not in allowed:
            raise ValueError(f"Unknown solver '{v}'. Allowed: milp, brute_force, greedy, qaoa")
        # Normalize
        if clean == "scipy_milp":
            return "milp"
        if clean == "enumeration":
            return "brute_force"
        return clean


class OptimizeResultDetails(BaseModel):
    selected_waypoint_ids: List[str]
    selected_waypoint_count: int
    coverage_counts: Dict[str, int]
    feasible: bool
    objective_value: float
    runtime_seconds: float


class OptimizationResponseDTO(BaseModel):
    run_id: str
    status: str  # "completed" | "no_feasible_solution" | "failed"
    scenario: Dict[str, Any]
    solver: Dict[str, Any]
    result: OptimizeResultDetails
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CompareRequestDTO(BaseModel):
    scenario_id: Optional[str] = "canonical"
    target_ids: Optional[List[str]] = None
    waypoint_ids: Optional[List[str]] = None
    coverage_matrix: Optional[List[List[int]]] = None
    k_coverage: Optional[int] = Field(default=3, ge=1, le=10)
    solvers: List[str] = Field(default_factory=lambda: ["milp", "greedy", "qaoa"])
    qaoa_options: Optional[Dict[str, Any]] = None
    rf_config: Optional[RFConfigDTO] = None


class CompareResponseDTO(BaseModel):
    scenario_name: str
    results: List[OptimizationResponseDTO]


class HistoryItemDTO(BaseModel):
    id: int
    run_id: str
    created_at: str
    scenario_name: str
    solver_name: str
    status: str
    feasible: Optional[bool]
    selected_waypoint_count: Optional[int]
    objective_value: Optional[float]
    runtime_seconds: Optional[float]


class HistoryListDTO(BaseModel):
    items: List[HistoryItemDTO]
    total: int
    limit: int
    offset: int
