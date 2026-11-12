"""Unit tests for RF propagation, link budget calculation, and coverage generation."""
import math
import pytest

from backend.sar.rf_propagation import (
    DEFAULT_EXCESS_LOSS_DB,
    EnvironmentType,
    RFConfig,
    RFInputValidationError,
    RFTarget,
    RFWaypoint,
    calculate_3d_distance,
    calculate_fspl,
    calculate_link_budget,
    get_deterministic_rf_demonstration_scenario,
    simulate_rf_scenario,
)


def test_rf_input_validation_valid():
    cfg = RFConfig(frequency_mhz=2400.0, tx_power_dbm=20.0)
    assert cfg.frequency_mhz == 2400.0
    assert cfg.rx_threshold_dbm == -90.0  # -100 + 10


def test_rf_input_validation_zero_negative_frequency():
    with pytest.raises(RFInputValidationError, match="Carrier frequency must be strictly positive"):
        RFConfig(frequency_mhz=0.0)

    with pytest.raises(RFInputValidationError, match="Carrier frequency must be strictly positive"):
        RFConfig(frequency_mhz=-100.0)


def test_rf_input_validation_negative_losses():
    with pytest.raises(RFInputValidationError, match="System loss cannot be negative"):
        RFConfig(system_loss_db=-1.0)

    with pytest.raises(RFInputValidationError, match="Fade margin cannot be negative"):
        RFConfig(fade_margin_db=-5.0)

    with pytest.raises(RFInputValidationError, match="Excess environmental loss cannot be negative"):
        RFConfig(excess_loss_db=-2.0)


def test_rf_target_and_waypoint_validation():
    with pytest.raises(RFInputValidationError, match="Target id cannot be empty"):
        RFTarget(id="", x=0, y=0)

    with pytest.raises(RFInputValidationError, match="Target height cannot be negative"):
        RFTarget(id="T1", x=0, y=0, height_m=-1.0)

    with pytest.raises(RFInputValidationError, match="Waypoint id cannot be empty"):
        RFWaypoint(id="", x=0, y=0)

    with pytest.raises(RFInputValidationError, match="UAV altitude cannot be negative"):
        RFWaypoint(id="W1", x=0, y=0, altitude_m=-10.0)


def test_3d_distance_calculation():
    target = RFTarget(id="T1", x=0.0, y=0.0, height_m=0.0)
    waypoint = RFWaypoint(id="W1", x=300.0, y=400.0, altitude_m=0.0)
    dist = calculate_3d_distance(target, waypoint)
    assert pytest.approx(dist, rel=1e-5) == 500.0

    # With vertical difference: dx=300, dy=400, dz=1200 -> sqrt(300^2 + 400^2 + 1200^2) = 1300
    waypoint_high = RFWaypoint(id="W2", x=300.0, y=400.0, altitude_m=1201.5)
    target_ground = RFTarget(id="T2", x=0.0, y=0.0, height_m=1.5)
    dist_high = calculate_3d_distance(target_ground, waypoint_high)
    assert pytest.approx(dist_high, rel=1e-5) == 1300.0


def test_fspl_exact_formula():
    # FSPL(dB) = 32.44 + 20 log10(d_km) + 20 log10(f_MHz)
    # At d = 1 km (1000m) and f = 1000 MHz:
    # FSPL = 32.44 + 20*0 + 20*3 = 32.44 + 60 = 92.44 dB
    fspl = calculate_fspl(distance_m=1000.0, frequency_mhz=1000.0)
    assert pytest.approx(fspl, rel=1e-4) == 92.44


def test_fspl_near_zero_distance_clamping():
    # Should not raise math domain error on distance 0
    fspl_zero = calculate_fspl(distance_m=0.0, frequency_mhz=2400.0)
    fspl_clamp = calculate_fspl(distance_m=0.1, frequency_mhz=2400.0)
    assert pytest.approx(fspl_zero, abs=1e-3) == fspl_clamp


def test_received_signal_power_and_link_margin():
    target = RFTarget(id="T1", x=0.0, y=0.0, height_m=1.5)
    waypoint = RFWaypoint(id="W1", x=1000.0, y=0.0, altitude_m=1.5)
    cfg = RFConfig(
        frequency_mhz=1000.0,
        tx_power_dbm=20.0,
        tx_antenna_gain_dbi=2.0,
        rx_antenna_gain_dbi=2.0,
        rx_sensitivity_dbm=-100.0,
        system_loss_db=3.0,
        fade_margin_db=10.0,
        environment=EnvironmentType.OPEN,
        excess_loss_db=0.0,
    )
    link = calculate_link_budget(target, waypoint, cfg)
    # d = 1000m = 1km -> FSPL = 92.44 dB
    # Pr = 20 + 2 + 2 - 92.44 - 3 - 0 = -71.44 dBm
    # P_thresh = -100 + 10 = -90.0 dBm
    # Margin = -71.44 - (-90.0) = +18.56 dB -> Covered!
    assert pytest.approx(link.distance_3d_m, abs=0.1) == 1000.0
    assert pytest.approx(link.fspl_db, abs=0.1) == 92.44
    assert pytest.approx(link.received_power_dbm, abs=0.1) == -71.44
    assert link.threshold_dbm == -90.0
    assert pytest.approx(link.link_margin_db, abs=0.1) == 18.56
    assert link.is_covered is True


def test_extreme_signals():
    target = RFTarget(id="T1", x=0.0, y=0.0, height_m=1.5)
    waypoint = RFWaypoint(id="W1", x=50000.0, y=0.0, altitude_m=1.5)  # 50 km away
    cfg = RFConfig(
        frequency_mhz=5800.0,
        tx_power_dbm=0.0,
        rx_sensitivity_dbm=-80.0,
        fade_margin_db=10.0,
    )
    link = calculate_link_budget(target, waypoint, cfg)
    assert link.is_covered is False
    assert link.link_margin_db < 0.0


def test_environmental_excess_loss():
    target = RFTarget(id="T1", x=0.0, y=0.0, height_m=1.5)
    waypoint = RFWaypoint(id="W1", x=1000.0, y=0.0, altitude_m=1.5)
    
    cfg_open = RFConfig(environment=EnvironmentType.OPEN)
    cfg_suburban = RFConfig(environment=EnvironmentType.SUBURBAN)
    cfg_urban = RFConfig(environment=EnvironmentType.URBAN)

    link_open = calculate_link_budget(target, waypoint, cfg_open)
    link_suburban = calculate_link_budget(target, waypoint, cfg_suburban)
    link_urban = calculate_link_budget(target, waypoint, cfg_urban)

    assert pytest.approx(link_open.received_power_dbm - link_suburban.received_power_dbm, abs=0.01) == 5.0
    assert pytest.approx(link_open.received_power_dbm - link_urban.received_power_dbm, abs=0.01) == 12.0


def test_deterministic_rf_demonstration_scenario():
    sim_res = get_deterministic_rf_demonstration_scenario()
    assert len(sim_res.targets) == 5
    assert len(sim_res.waypoints) == 6
    assert sim_res.k_coverage == 3
    assert len(sim_res.coverage_matrix) == 5
    assert len(sim_res.coverage_matrix[0]) == 6

    # Verify that T1-T5 coordinates match Section 3 specification
    assert sim_res.targets[0].id == "T1"
    assert (sim_res.targets[0].x, sim_res.targets[0].y, sim_res.targets[0].height_m) == (300.0, 300.0, 1.5)
    assert (sim_res.targets[4].x, sim_res.targets[4].y, sim_res.targets[4].height_m) == (1300.0, 1250.0, 1.5)

    # Verify W1-W6 coordinates match Section 3 specification
    assert sim_res.waypoints[0].id == "W1"
    assert (sim_res.waypoints[0].x, sim_res.waypoints[0].y, sim_res.waypoints[0].altitude_m) == (200.0, 200.0, 60.0)
    assert (sim_res.waypoints[5].x, sim_res.waypoints[5].y, sim_res.waypoints[5].altitude_m) == (1550.0, 1350.0, 60.0)

    # In open environment with default illustrative settings, all pairs receive Pr >= -90 dBm
    assert sim_res.is_feasible is True
    for row in sim_res.coverage_matrix:
        assert all(val in (0, 1) for val in row)


def test_rf_scenario_conversion_to_sar_scenario():
    sim_res = get_deterministic_rf_demonstration_scenario()
    sar = sim_res.to_sar_scenario()
    assert sar.num_targets == 5
    assert sar.num_waypoints == 6
    assert sar.k_coverage == 3
    assert sar.is_feasible([0, 1, 2, 3]) is True

