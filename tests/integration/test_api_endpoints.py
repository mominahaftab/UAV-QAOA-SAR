"""Integration tests for all Phase 4 & 5 API endpoints using direct handler calls."""
import pytest
from backend.api.v1.router import (
    compare_solvers,
    get_canonical_scenario,
    get_history,
    get_rf_demonstration_scenario,
    list_scenarios,
    run_optimization,
    simulate_rf_scenario_endpoint,
)
from backend.db.session import Base, SessionLocal, engine
from backend.db.models import OptimizationRun  # ensure model is registered
from backend.models.schemas import (
    CompareRequestDTO,
    OptimizeRequestDTO,
    RFConfigDTO,
    RFSimulationRequestDTO,
)


@pytest.fixture(autouse=True)
def init_test_db():
    Base.metadata.create_all(bind=engine)
    yield


def test_list_scenarios():
    scenarios = list_scenarios()
    assert len(scenarios) >= 1
    assert any(s.id == "canonical" for s in scenarios)


def test_canonical_scenario_details():
    canonical = get_canonical_scenario()
    assert canonical.id == "canonical"
    assert len(canonical.target_ids) == 5
    assert len(canonical.waypoint_ids) == 6
    assert canonical.k_coverage == 3
    assert len(canonical.coverage_matrix) == 5
    assert len(canonical.coverage_matrix[0]) == 6


def test_optimize_endpoint_milp():
    db = SessionLocal()
    try:
        req = OptimizeRequestDTO(
            scenario_id="canonical",
            solver_name="milp",
        )
        res = run_optimization(req, db=db)
        assert res.status == "completed"
        assert res.result.feasible is True
        assert res.result.selected_waypoint_count == 4
        assert res.solver["name"] == "milp"
        assert res.run_id is not None
    finally:
        db.close()


def test_compare_endpoint():
    db = SessionLocal()
    try:
        req = CompareRequestDTO(
            scenario_id="canonical",
            solvers=["milp", "greedy"],
        )
        res = compare_solvers(req, db=db)
        assert res.scenario_name is not None
        assert len(res.results) == 2
        names = [r.solver["name"] for r in res.results]
        assert "milp" in names
        assert "greedy" in names
    finally:
        db.close()


def test_history_endpoint():
    db = SessionLocal()
    try:
        history = get_history(limit=5, offset=0, db=db)
        assert history.total >= 0
        assert isinstance(history.items, list)
    finally:
        db.close()


def test_rf_demonstration_scenario_endpoint():
    rf_demo = get_rf_demonstration_scenario()
    assert rf_demo.id == "rf-demonstration"
    assert len(rf_demo.target_ids) == 5
    assert len(rf_demo.waypoint_ids) == 6
    assert rf_demo.rf_config is not None
    assert rf_demo.rf_config.frequency_mhz == 2400.0
    assert rf_demo.rf_links is not None
    assert len(rf_demo.rf_links) == 30  # 5 targets * 6 waypoints


def test_rf_simulate_endpoint():
    req = RFSimulationRequestDTO(
        scenario_name="Test RF Sim",
        rf_config=RFConfigDTO(
            frequency_mhz=2400.0,
            tx_power_dbm=20.0,
            fade_margin_db=10.0,
        ),
        k_coverage=3,
    )
    res = simulate_rf_scenario_endpoint(req)
    assert res.scenario_name == "Test RF Sim"
    assert len(res.target_ids) == 5
    assert len(res.waypoint_ids) == 6
    assert len(res.coverage_matrix) == 5
    assert len(res.links) == 30


def test_optimize_endpoint_with_rf_scenario():
    db = SessionLocal()
    try:
        req = OptimizeRequestDTO(
            scenario_id="rf-demonstration",
            solver_name="milp",
            k_coverage=3,
        )
        res = run_optimization(req, db=db)
        assert res.status == "completed"
        assert res.result.feasible is True
        assert res.result.selected_waypoint_count >= 1
    finally:
        db.close()

