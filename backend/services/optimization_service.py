"""Optimization orchestrator connecting SAR domain problems to classical and quantum solvers."""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from backend.core.serialization import safe_json_serialize
from backend.db.models import OptimizationRun
from backend.models.schemas import (
    CompareRequestDTO,
    CompareResponseDTO,
    OptimizationResponseDTO,
    OptimizeRequestDTO,
    OptimizeResultDetails,
)
from backend.sar.scenario import SARScenario, get_canonical_benchmark_scenario
from backend.services.scenario_service import ScenarioService
from backend.solvers.base import OptimizationProblem, OptimizationResult
from backend.solvers.classical.greedy import GreedySolver
from backend.solvers.classical.milp import BruteForceEnumerationValidator, SciPyMILPSolver
from backend.solvers.qaoa.solver import QAOASolver


class OptimizationService:
    """Orchestrates solver invocation, result normalization, and database persistence."""

    @staticmethod
    def _build_scenario(req: OptimizeRequestDTO) -> SARScenario:
        """Resolve scenario from custom inputs, RF demonstration, or canonical default."""
        if req.coverage_matrix is not None and req.target_ids and req.waypoint_ids:
            return SARScenario(
                name=req.scenario_id or "CustomScenario",
                target_ids=req.target_ids,
                waypoint_ids=req.waypoint_ids,
                coverage_matrix=req.coverage_matrix,
                k_coverage=req.k_coverage or 3,
            )
        elif req.scenario_id and req.scenario_id.lower().strip() in ("rf-demonstration", "rf_demonstration", "rf-demo"):
            rf_demo = ScenarioService.get_rf_demonstration_scenario(req.rf_config)
            return SARScenario(
                name=rf_demo.name,
                target_ids=rf_demo.target_ids,
                waypoint_ids=rf_demo.waypoint_ids,
                coverage_matrix=rf_demo.coverage_matrix,
                k_coverage=req.k_coverage or rf_demo.k_coverage,
            )
        else:
            canonical = ScenarioService.get_canonical_scenario()
            return SARScenario(
                name="Canonical-5T-6W-k3",
                target_ids=canonical.target_ids,
                waypoint_ids=canonical.waypoint_ids,
                coverage_matrix=canonical.coverage_matrix,
                k_coverage=req.k_coverage or canonical.k_coverage,
            )

    @staticmethod
    def run_optimization(req: OptimizeRequestDTO, db: Optional[Session] = None) -> OptimizationResponseDTO:
        run_id = str(uuid.uuid4())
        scenario = OptimizationService._build_scenario(req)
        problem = scenario.to_optimization_problem()

        solver_name = req.solver_name.lower().strip()
        t_start = time.perf_counter()

        status = "completed"
        error_msg: Optional[str] = None
        result_details: OptimizeResultDetails
        metadata: Dict[str, Any] = {}

        try:
            if solver_name == "milp":
                solver = SciPyMILPSolver()
                opt_res = solver.solve(problem)
                runtime_sec = opt_res.execution_time_ms / 1000.0
                selected_wp_ids = [scenario.waypoint_ids[i] for i in opt_res.selected_waypoints]
                counts = scenario.get_coverage_counts(selected_wp_ids)
                status = "completed" if opt_res.is_feasible else "no_feasible_solution"
                result_details = OptimizeResultDetails(
                    selected_waypoint_ids=selected_wp_ids,
                    selected_waypoint_count=opt_res.num_selected,
                    coverage_counts=counts,
                    feasible=opt_res.is_feasible,
                    objective_value=float(opt_res.num_selected),
                    runtime_seconds=runtime_sec,
                )
                metadata = {
                    "solver_type": "exact_bilp",
                    "optimality_proven": True,
                    "method": "Branch-and-cut (HiGHS via SciPy)",
                    **opt_res.metadata,
                }

            elif solver_name == "brute_force":
                validator = BruteForceEnumerationValidator()
                enum_res = validator.validate(problem)
                runtime_sec = enum_res.execution_time_ms / 1000.0
                if enum_res.is_feasible and enum_res.optimal_combinations:
                    best_combo = enum_res.optimal_combinations[0]
                    selected_wp_ids = [scenario.waypoint_ids[i] for i in best_combo]
                    counts = scenario.get_coverage_counts(selected_wp_ids)
                    status = "completed"
                    result_details = OptimizeResultDetails(
                        selected_waypoint_ids=selected_wp_ids,
                        selected_waypoint_count=enum_res.min_waypoints,
                        coverage_counts=counts,
                        feasible=True,
                        objective_value=float(enum_res.min_waypoints),
                        runtime_seconds=runtime_sec,
                    )
                else:
                    status = "no_feasible_solution"
                    result_details = OptimizeResultDetails(
                        selected_waypoint_ids=[],
                        selected_waypoint_count=0,
                        coverage_counts={t: 0 for t in scenario.target_ids},
                        feasible=False,
                        objective_value=float("inf"),
                        runtime_seconds=runtime_sec,
                    )
                metadata = {
                    "solver_type": "exhaustive_enumeration",
                    "optimality_proven": True,
                    "num_optimal_combinations": enum_res.num_optimal_combinations,
                    "total_subsets_evaluated": enum_res.total_evaluated,
                }

            elif solver_name == "greedy":
                solver = GreedySolver()
                opt_res = solver.solve(problem)
                runtime_sec = opt_res.execution_time_ms / 1000.0
                selected_wp_ids = [scenario.waypoint_ids[i] for i in opt_res.selected_waypoints]
                counts = scenario.get_coverage_counts(selected_wp_ids)
                status = "completed" if opt_res.is_feasible else "no_feasible_solution"
                result_details = OptimizeResultDetails(
                    selected_waypoint_ids=selected_wp_ids,
                    selected_waypoint_count=opt_res.num_selected,
                    coverage_counts=counts,
                    feasible=opt_res.is_feasible,
                    objective_value=float(opt_res.num_selected),
                    runtime_seconds=runtime_sec,
                )
                metadata = {
                    "solver_type": "greedy_heuristic",
                    "optimality_proven": False,
                    "is_heuristic": True,
                    **opt_res.metadata,
                }

            elif solver_name == "qaoa":
                solver = QAOASolver(
                    qaoa_depth=req.qaoa_depth,
                    shots=req.shots,
                    penalty=req.penalty,
                    optimizer="COBYLA",
                    max_iterations=req.max_iterations,
                    random_seed=req.random_seed,
                    classical_optimum=4.0,
                )
                qaoa_res = solver.solve_qaoa(problem)
                runtime_sec = qaoa_res.total_runtime_ms / 1000.0
                selected_wp_ids = [scenario.waypoint_ids[i] for i in qaoa_res.selected_waypoints]
                counts = scenario.get_coverage_counts(selected_wp_ids) if selected_wp_ids else {t: 0 for t in scenario.target_ids}
                status = "completed" if qaoa_res.is_feasible else "no_feasible_solution"
                result_details = OptimizeResultDetails(
                    selected_waypoint_ids=selected_wp_ids,
                    selected_waypoint_count=qaoa_res.num_selected,
                    coverage_counts=counts,
                    feasible=qaoa_res.is_feasible,
                    objective_value=float(qaoa_res.num_selected) if qaoa_res.is_feasible else float("inf"),
                    runtime_seconds=runtime_sec,
                )
                metadata = {
                    "solver_type": "quantum_approximate_optimization_algorithm",
                    "simulator_name": qaoa_res.simulator_name,
                    "is_quantum_simulation": True,
                    "quantum_advantage_claimed": False,
                    "optimality_proven": False,
                    "qaoa_depth": qaoa_res.qaoa_depth_p,
                    "shots": qaoa_res.shots,
                    "feasible_sample_count": qaoa_res.feasible_sample_count,
                    "infeasible_sample_count": qaoa_res.infeasible_sample_count,
                    "feasible_rate": qaoa_res.feasible_rate,
                    "qubo_energy_best": qaoa_res.qubo_energy_best,
                    "ising_expectation": qaoa_res.ising_expectation,
                    "optimality_gap": qaoa_res.optimality_gap,
                    "gamma": qaoa_res.gamma,
                    "beta": qaoa_res.beta,
                    "warnings": qaoa_res.warnings,
                }
            else:
                raise ValueError(f"Unsupported solver '{req.solver_name}'")

        except Exception as e:
            runtime_sec = (time.perf_counter() - t_start)
            status = "failed"
            error_msg = str(e)
            result_details = OptimizeResultDetails(
                selected_waypoint_ids=[],
                selected_waypoint_count=0,
                coverage_counts={t: 0 for t in scenario.target_ids},
                feasible=False,
                objective_value=float("inf"),
                runtime_seconds=runtime_sec,
            )
            metadata = {"error": error_msg}

        response = OptimizationResponseDTO(
            run_id=run_id,
            status=status,
            scenario={
                "name": scenario.name,
                "target_count": scenario.num_targets,
                "waypoint_count": scenario.num_waypoints,
                "required_coverage": scenario.k_coverage,
            },
            solver={"name": req.solver_name},
            result=result_details,
            metadata=safe_json_serialize(metadata),
        )

        # Persist to database if db session provided
        if db is not None:
            try:
                db_record = OptimizationRun(
                    run_id=run_id,
                    scenario_name=scenario.name,
                    solver_name=req.solver_name,
                    status=status,
                    request_data=safe_json_serialize(req.model_dump()),
                    result_data=safe_json_serialize(response.model_dump()),
                    selected_waypoint_count=result_details.selected_waypoint_count,
                    feasible=result_details.feasible,
                    objective_value=result_details.objective_value if result_details.feasible else None,
                    runtime_seconds=result_details.runtime_seconds,
                    error_message=error_msg,
                )
                db.add(db_record)
                db.commit()
            except Exception as db_err:
                db.rollback()
                # Log but do not crash the API response
                print(f"[WARN] Failed to persist optimization run: {db_err}")

        return response

    @staticmethod
    def run_comparison(req: CompareRequestDTO, db: Optional[Session] = None) -> CompareResponseDTO:
        results: List[OptimizationResponseDTO] = []
        for solver_name in req.solvers:
            opt_req = OptimizeRequestDTO(
                scenario_id=req.scenario_id,
                target_ids=req.target_ids,
                waypoint_ids=req.waypoint_ids,
                coverage_matrix=req.coverage_matrix,
                k_coverage=req.k_coverage,
                solver_name=solver_name,
                **(req.qaoa_options or {}),
            )
            res = OptimizationService.run_optimization(opt_req, db=db)
            results.append(res)

        return CompareResponseDTO(
            scenario_name=req.scenario_id or "Canonical-5T-6W-k3",
            results=results,
        )

