"""Calibration tests: reproduce the earlier hand checks and pin down units."""
import numpy as np
import pytest

from src import calibration as C


def test_cycle_time_units():
    # 24 km one-way, non-loop, 22 km/h, no layover -> 48 km / 22 km/h = 2.1818 h
    assert C.cycle_time_h([24.0], [False], "S2", 22.0, 0.0)[0] == pytest.approx(48 / 22)
    # same route under S1 reading -> 24/22 h
    assert C.cycle_time_h([24.0], [False], "S1", 22.0, 0.0)[0] == pytest.approx(24 / 22)
    # loop is never doubled
    assert C.cycle_time_h([38.3], [True], "S2", 22.0, 0.0)[0] == pytest.approx(38.3 / 22)
    # 10% layover multiplies running time
    assert C.cycle_time_h([24.0], [False], "S2", 22.0, 0.10)[0] == pytest.approx(48 / 22 * 1.1)


def test_hand_check_S1_about_172(routes):
    assert C.buses_needed(routes, "S1", 22.0, 0.0) == pytest.approx(171.9, abs=0.1)


def test_hand_check_S2_about_310(routes):
    assert C.buses_needed(routes, "S2", 22.0, 0.0) == pytest.approx(309.9, abs=0.1)


def test_hand_check_S2_layover_about_340(routes):
    assert C.buses_needed(routes, "S2", 22.0, 0.10) == pytest.approx(340.9, abs=0.1)


def test_S3_is_S2_plus_spares(routes):
    assert C.buses_needed(routes, "S3", 22.0, 0.10) == pytest.approx(1.1 * C.buses_needed(routes, "S2", 22.0, 0.10))


def test_need_scales_inverse_with_speed(routes):
    a, b = C.buses_needed(routes, "S2", 18.0, 0.0), C.buses_needed(routes, "S2", 36.0, 0.0)
    assert a == pytest.approx(2 * b)


def test_short_routes_S2_22(routes):
    pr0 = C.per_route(routes, "S2", 22.0, 0.0)
    pr1 = C.per_route(routes, "S2", 22.0, 0.10)
    assert set(pr0.route_no[pr0.x_base < pr0.need_fmin]) == {"37", "76"}
    assert set(pr1.route_no[pr1.x_base < pr1.need_fmin]) == {"37", "40", "76"}


def test_grid_shape_and_band(routes):
    g = C.scenario_grid(routes)
    assert len(g) == 3 * 3 * 2
    rec = g[(g.scenario == "S3") & (g.v_kmh == 22.0) & (g.layover_frac == 0.10)].iloc[0]
    assert rec.in_band and 0.95 < rec.utilisation < 0.97
    assert not g[g.scenario == "S1"].in_band.any()


def test_implied_speed_consistent(routes):
    v = C.implied_uniform_speed(routes, "S2", 0.10, 389)
    assert C.buses_needed(routes, "S2", v, 0.10) == pytest.approx(389)
    assert np.isfinite(v) and 18 < v < 22
