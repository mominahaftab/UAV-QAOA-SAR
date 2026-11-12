"""API v1 router registering all endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.db.models import OptimizationRun
from backend.db.session import get_db
from backend.models.schemas import (
    CompareRequestDTO,
    CompareResponseDTO,
    HistoryItemDTO,
    HistoryListDTO,
    OptimizationResponseDTO,
    OptimizeRequestDTO,
    RFSimulationRequestDTO,
    RFSimulationResponseDTO,
    ScenarioDetailDTO,
    ScenarioSummaryDTO,
)
from backend.services.optimization_service import OptimizationService
from backend.services.scenario_service import ScenarioService

api_router = APIRouter()


# ------------------------------------------------------------------
# Health Endpoints
# ------------------------------------------------------------------
@api_router.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint to verify backend status."""
    return {"status": "ok", "service": "uav-qaoa-sar-backend"}


# ------------------------------------------------------------------
# Scenario Endpoints
# ------------------------------------------------------------------
@api_router.get("/scenarios", response_model=List[ScenarioSummaryDTO], tags=["Scenarios"])
def list_scenarios():
    """List all available SAR mission scenarios."""
    return ScenarioService.list_scenarios()


@api_router.get("/scenarios/canonical", response_model=ScenarioDetailDTO, tags=["Scenarios"])
def get_canonical_scenario():
    """Get the standard canonical 5-target, 6-waypoint, k=3 benchmark scenario."""
    return ScenarioService.get_canonical_scenario()


@api_router.get("/scenarios/rf-demonstration", response_model=ScenarioDetailDTO, tags=["Scenarios"])
def get_rf_demonstration_scenario():
    """Get the deterministic RF demonstration scenario with 3D link-budget calculations."""
    return ScenarioService.get_rf_demonstration_scenario()


@api_router.post("/scenarios/rf-simulate", response_model=RFSimulationResponseDTO, tags=["Scenarios"])
def simulate_rf_scenario_endpoint(req: RFSimulationRequestDTO):
    """Simulate RF link budget and generate a binary coverage matrix."""
    try:
        return ScenarioService.simulate_rf(req)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RF simulation error: {str(e)}")


@api_router.get("/scenarios/{scenario_id}", response_model=ScenarioDetailDTO, tags=["Scenarios"])
def get_scenario(scenario_id: str):
    """Retrieve details for a specific scenario by ID."""
    scenario = ScenarioService.get_scenario_by_id(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return scenario


# ------------------------------------------------------------------
# Optimization Endpoints
# ------------------------------------------------------------------
@api_router.post("/optimize", response_model=OptimizationResponseDTO, tags=["Optimization"])
def run_optimization(req: OptimizeRequestDTO, db: Session = Depends(get_db)):
    """Execute waypoint optimization using MILP, Brute-Force, Greedy, or QAOA."""
    try:
        return OptimizationService.run_optimization(req, db=db)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solver error: {str(e)}")


@api_router.post("/compare", response_model=CompareResponseDTO, tags=["Optimization"])
def compare_solvers(req: CompareRequestDTO, db: Session = Depends(get_db)):
    """Run multiple solvers against the same scenario for direct benchmarking."""
    try:
        return OptimizationService.run_comparison(req, db=db)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Comparison error: {str(e)}")


# ------------------------------------------------------------------
# History Endpoints
# ------------------------------------------------------------------
@api_router.get("/history", response_model=HistoryListDTO, tags=["History"])
def get_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """Retrieve past optimization runs, sorted newest first."""
    query = db.query(OptimizationRun).order_by(OptimizationRun.created_at.desc())
    total = query.count()
    records = query.offset(offset).limit(limit).all()

    items = [
        HistoryItemDTO(
            id=r.id,
            run_id=r.run_id,
            created_at=r.created_at.isoformat() if r.created_at else "",
            scenario_name=r.scenario_name,
            solver_name=r.solver_name,
            status=r.status,
            feasible=r.feasible,
            selected_waypoint_count=r.selected_waypoint_count,
            objective_value=r.objective_value,
            runtime_seconds=r.runtime_seconds,
        )
        for r in records
    ]
    return HistoryListDTO(items=items, total=total, limit=limit, offset=offset)


@api_router.get("/history/{run_id}", response_model=dict, tags=["History"])
def get_history_detail(run_id: str, db: Session = Depends(get_db)):
    """Retrieve the full request and result snapshot of a previous run."""
    record = db.query(OptimizationRun).filter(OptimizationRun.run_id == run_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return {
        "id": record.id,
        "run_id": record.run_id,
        "created_at": record.created_at.isoformat() if record.created_at else "",
        "scenario_name": record.scenario_name,
        "solver_name": record.solver_name,
        "status": record.status,
        "request_data": record.request_data,
        "result_data": record.result_data,
        "selected_waypoint_count": record.selected_waypoint_count,
        "feasible": record.feasible,
        "objective_value": record.objective_value,
        "runtime_seconds": record.runtime_seconds,
        "error_message": record.error_message,
    }


@api_router.delete("/history/{run_id}", tags=["History"])
def delete_history_item(run_id: str, db: Session = Depends(get_db)):
    """Delete a single historical optimization run."""
    record = db.query(OptimizationRun).filter(OptimizationRun.run_id == run_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    db.delete(record)
    db.commit()
    return {"status": "deleted", "run_id": run_id}
