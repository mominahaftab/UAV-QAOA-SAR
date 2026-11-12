"""Scenario management and registry service with RF link-budget simulation."""
from __future__ import annotations

from typing import Dict, List, Optional

from backend.models.schemas import (
    RFConfigDTO,
    RFLinkResultDTO,
    RFSimulationRequestDTO,
    RFSimulationResponseDTO,
    ScenarioDetailDTO,
    ScenarioSummaryDTO,
    TargetPoint,
    WaypointPoint,
)
from backend.sar.rf_propagation import (
    EnvironmentType,
    RFConfig,
    RFLinkResult,
    RFSimulationResult,
    RFTarget,
    RFWaypoint,
    get_deterministic_rf_demonstration_scenario,
    simulate_rf_scenario,
)
from backend.sar.scenario import SARScenario, get_canonical_benchmark_scenario

# Canonical schematic coordinate placement for visualization
CANONICAL_TARGET_COORDS = [
    TargetPoint(id="T1", x=220.0, y=380.0, height_m=1.5, priority=1.0),
    TargetPoint(id="T2", x=460.0, y=490.0, height_m=1.5, priority=1.2),
    TargetPoint(id="T3", x=700.0, y=370.0, height_m=1.5, priority=1.0),
    TargetPoint(id="T4", x=340.0, y=210.0, height_m=1.5, priority=1.5),
    TargetPoint(id="T5", x=540.0, y=230.0, height_m=1.5, priority=1.0),
]

CANONICAL_WAYPOINT_COORDS = [
    WaypointPoint(id="W1", x=240.0, y=270.0, altitude_m=60.0, cost=1.0),
    WaypointPoint(id="W2", x=330.0, y=430.0, altitude_m=60.0, cost=1.0),
    WaypointPoint(id="W3", x=580.0, y=440.0, altitude_m=60.0, cost=1.0),
    WaypointPoint(id="W4", x=630.0, y=260.0, altitude_m=60.0, cost=1.0),
    WaypointPoint(id="W5", x=440.0, y=340.0, altitude_m=60.0, cost=1.0),
    WaypointPoint(id="W6", x=510.0, y=530.0, altitude_m=60.0, cost=1.0),
]


class ScenarioService:
    """Provides access to benchmark, RF-simulated, and custom mission scenarios."""

    @staticmethod
    def get_canonical_scenario() -> ScenarioDetailDTO:
        scenario = get_canonical_benchmark_scenario()
        return ScenarioDetailDTO(
            id="canonical",
            name=scenario.name,
            target_ids=scenario.target_ids,
            waypoint_ids=scenario.waypoint_ids,
            coverage_matrix=scenario.coverage_matrix,
            k_coverage=scenario.k_coverage,
            targets=CANONICAL_TARGET_COORDS,
            waypoints=CANONICAL_WAYPOINT_COORDS,
            scenario_type="synthetic",
        )

    @staticmethod
    def get_rf_demonstration_scenario(rf_config_dto: Optional[RFConfigDTO] = None) -> ScenarioDetailDTO:
        rf_cfg: Optional[RFConfig] = None
        if rf_config_dto:
            rf_cfg = RFConfig(
                frequency_mhz=rf_config_dto.frequency_mhz,
                tx_power_dbm=rf_config_dto.tx_power_dbm,
                tx_antenna_gain_dbi=rf_config_dto.tx_antenna_gain_dbi,
                rx_antenna_gain_dbi=rf_config_dto.rx_antenna_gain_dbi,
                rx_sensitivity_dbm=rf_config_dto.rx_sensitivity_dbm,
                system_loss_db=rf_config_dto.system_loss_db,
                fade_margin_db=rf_config_dto.fade_margin_db,
                environment=EnvironmentType(rf_config_dto.environment.lower()),
                excess_loss_db=rf_config_dto.excess_loss_db,
            )

        sim_res = get_deterministic_rf_demonstration_scenario(rf_cfg)

        target_points = [
            TargetPoint(id=t.id, x=t.x, y=t.y, height_m=t.height_m, priority=1.0)
            for t in sim_res.targets
        ]
        waypoint_points = [
            WaypointPoint(id=w.id, x=w.x, y=w.y, altitude_m=w.altitude_m, cost=w.cost)
            for w in sim_res.waypoints
        ]

        cfg_dto = RFConfigDTO(
            frequency_mhz=sim_res.rf_config.frequency_mhz,
            tx_power_dbm=sim_res.rf_config.tx_power_dbm,
            tx_antenna_gain_dbi=sim_res.rf_config.tx_antenna_gain_dbi,
            rx_antenna_gain_dbi=sim_res.rf_config.rx_antenna_gain_dbi,
            rx_sensitivity_dbm=sim_res.rf_config.rx_sensitivity_dbm,
            system_loss_db=sim_res.rf_config.system_loss_db,
            fade_margin_db=sim_res.rf_config.fade_margin_db,
            environment=sim_res.rf_config.environment.value,
            excess_loss_db=sim_res.rf_config.excess_loss_db,
            uav_altitude_m=waypoint_points[0].altitude_m if waypoint_points else 60.0,
            target_height_m=target_points[0].height_m if target_points else 1.5,
        )

        link_dtos = [
            RFLinkResultDTO(
                target_id=link.target_id,
                waypoint_id=link.waypoint_id,
                distance_3d_m=link.distance_3d_m,
                distance_km=link.distance_km,
                fspl_db=link.fspl_db,
                received_power_dbm=link.received_power_dbm,
                threshold_dbm=link.threshold_dbm,
                link_margin_db=link.link_margin_db,
                is_covered=link.is_covered,
            )
            for link in sim_res.links
        ]

        return ScenarioDetailDTO(
            id="rf-demonstration",
            name=sim_res.scenario_name,
            target_ids=[t.id for t in sim_res.targets],
            waypoint_ids=[w.id for w in sim_res.waypoints],
            coverage_matrix=sim_res.coverage_matrix,
            k_coverage=sim_res.k_coverage,
            targets=target_points,
            waypoints=waypoint_points,
            rf_config=cfg_dto,
            rf_links=link_dtos,
            scenario_type="rf_simulation",
        )

    @staticmethod
    def simulate_rf(req: RFSimulationRequestDTO) -> RFSimulationResponseDTO:
        rf_cfg = RFConfig(
            frequency_mhz=req.rf_config.frequency_mhz,
            tx_power_dbm=req.rf_config.tx_power_dbm,
            tx_antenna_gain_dbi=req.rf_config.tx_antenna_gain_dbi,
            rx_antenna_gain_dbi=req.rf_config.rx_antenna_gain_dbi,
            rx_sensitivity_dbm=req.rf_config.rx_sensitivity_dbm,
            system_loss_db=req.rf_config.system_loss_db,
            fade_margin_db=req.rf_config.fade_margin_db,
            environment=EnvironmentType(req.rf_config.environment.lower()),
            excess_loss_db=req.rf_config.excess_loss_db,
        )

        if req.targets:
            targets = [
                RFTarget(id=t.id, x=t.x, y=t.y, height_m=t.height_m)
                for t in req.targets
            ]
        else:
            demo = get_deterministic_rf_demonstration_scenario(rf_cfg)
            targets = demo.targets

        if req.waypoints:
            waypoints = [
                RFWaypoint(id=w.id, x=w.x, y=w.y, altitude_m=w.altitude_m, cost=w.cost)
                for w in req.waypoints
            ]
        else:
            demo = get_deterministic_rf_demonstration_scenario(rf_cfg)
            waypoints = demo.waypoints

        sim_res = simulate_rf_scenario(
            name=req.scenario_name or "Custom RF Simulation",
            targets=targets,
            waypoints=waypoints,
            rf_config=rf_cfg,
            k_coverage=req.k_coverage,
        )

        target_dtos = [
            TargetPoint(id=t.id, x=t.x, y=t.y, height_m=t.height_m, priority=1.0)
            for t in targets
        ]
        waypoint_dtos = [
            WaypointPoint(id=w.id, x=w.x, y=w.y, altitude_m=w.altitude_m, cost=w.cost)
            for w in waypoints
        ]

        link_dtos = [
            RFLinkResultDTO(
                target_id=link.target_id,
                waypoint_id=link.waypoint_id,
                distance_3d_m=link.distance_3d_m,
                distance_km=link.distance_km,
                fspl_db=link.fspl_db,
                received_power_dbm=link.received_power_dbm,
                threshold_dbm=link.threshold_dbm,
                link_margin_db=link.link_margin_db,
                is_covered=link.is_covered,
            )
            for link in sim_res.links
        ]

        return RFSimulationResponseDTO(
            scenario_name=sim_res.scenario_name,
            rf_config=req.rf_config,
            k_coverage=sim_res.k_coverage,
            target_ids=[t.id for t in sim_res.targets],
            waypoint_ids=[w.id for w in sim_res.waypoints],
            coverage_matrix=sim_res.coverage_matrix,
            coverage_counts=sim_res.coverage_counts,
            unsatisfied_targets=sim_res.unsatisfied_targets,
            is_feasible=sim_res.is_feasible,
            links=link_dtos,
            targets=target_dtos,
            waypoints=waypoint_dtos,
        )

    @staticmethod
    def list_scenarios() -> List[ScenarioSummaryDTO]:
        canonical = ScenarioService.get_canonical_scenario()
        rf_demo = ScenarioService.get_rf_demonstration_scenario()
        return [
            ScenarioSummaryDTO(
                id="canonical",
                name="Canonical 5T-6W-k3 Synthetic Benchmark",
                target_count=len(canonical.target_ids),
                waypoint_count=len(canonical.waypoint_ids),
                k_coverage=canonical.k_coverage,
                description="Deterministic synthetic benchmark for quantum solver regression verification (5 targets, 6 waypoints, k=3).",
                scenario_type="synthetic",
            ),
            ScenarioSummaryDTO(
                id="rf-demonstration",
                name="RF Search-and-Rescue Demonstration — Synthetic Coordinates",
                target_count=len(rf_demo.target_ids),
                waypoint_count=len(rf_demo.waypoint_ids),
                k_coverage=rf_demo.k_coverage,
                description="Simulated RF link-budget coverage model with local Cartesian coordinates in metres (2400 MHz, FSPL).",
                scenario_type="rf_simulation",
            ),
        ]

    @staticmethod
    def get_scenario_by_id(scenario_id: str) -> Optional[ScenarioDetailDTO]:
        clean = scenario_id.lower().strip()
        if clean in ("canonical", "canonical-5t-6w-k3"):
            return ScenarioService.get_canonical_scenario()
        if clean in ("rf-demonstration", "rf_demonstration", "rf-demo"):
            return ScenarioService.get_rf_demonstration_scenario()
        return None
