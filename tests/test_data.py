"""Validation of the clean route table and stop network built from the workbook."""
import math

import pandas as pd
import pytest

from src import data as D
from src import params as P


def test_route_counts_and_totals(routes):
    assert len(routes) == P.N_ROUTES == 68
    assert routes.route_no.is_unique
    assert int(routes.x_base.sum()) == P.FLEET_B == 389
    assert math.isclose(routes.d_r_km.sum(), 1662)
    assert "TOTAL" not in set(routes.route_no)


def test_route_no_is_string_and_25_25A_present(routes):
    assert all(isinstance(r, str) for r in routes.route_no)
    assert "25/25A" in set(routes.route_no)
    assert "1" in set(routes.route_no)


def test_frequency_units(routes):
    # f [dep/h] = 60 / headway [min]; f_min comes from the LONGEST headway
    assert ((routes.f_min - 60 / routes.headway_min_hi).abs() < 1e-12).all()
    assert ((routes.f_max - 60 / routes.headway_min_lo).abs() < 1e-12).all()
    assert (routes.f_min <= routes.f_mid).all() and (routes.f_mid <= routes.f_max).all()
    assert routes.f_max.max() <= 6.0 and routes.f_min.min() > 0.5   # 10..90 min headways
    r = routes.set_index("route_no")
    assert (r.at["5A", "f_min"], r.at["5A", "f_max"]) == (2.0, 4.0)   # "15-30"


def test_operating_windows(routes, loaded):
    assert loaded["ow_from_cache"]
    r = routes.set_index("route_no")
    assert (r.at["1", "first_departure"], r.at["1", "last_departure"]) == ("06:10", "18:40")
    assert r.at["1", "span_hours"] == pytest.approx(12.5)
    assert r.at["24A", "overnight"] and r.at["24A", "span_hours"] == pytest.approx(6 + 40 / 60)
    assert ((routes.span_hours > 0) & (routes.span_hours <= 24)).all()


def test_cached_windows_equal_recomputed(loaded):
    ow = loaded["ow"]
    assert (ow.first_departure == ow.first_recomputed).all()
    assert (ow.last_departure == ow.last_recomputed).all()
    assert ((ow.span_hours - ow.span_recomputed).abs() < 1e-6).all()


def test_loops(routes):
    loops = set(routes.route_no[routes.is_loop])
    assert loops == {"2A", "2C", "4A", "4C", "5A", "5C", "9A", "9C"}


def test_no_cross_check_warnings(loaded):
    assert loaded["warnings"] == []


def test_pdf_verification_all_ok(loaded):
    pdf = loaded["pdf"]
    assert len(pdf) == 68 and (pdf.match == "OK").all()


def test_model_variables_only_rounding_differences(loaded):
    mv = loaded["mv_issues"]
    diffs = (mv.excel.astype(float) - mv.ours.astype(float)).abs()
    assert (diffs < 0.005).all()                       # 2-decimal rounding only
    assert set(mv.field) <= {"f_min", "f_max", "f_mid"}  # tau = d/22 and x/tau match exactly


def test_stop_network(loaded, routes):
    assert len(loaded["stops"]) == P.N_STOPS == 649
    f = loaded["features"]
    assert list(f.route_no) == list(routes.route_no)
    assert (f.n_stops >= 1).all() and (f.centrality_mean >= 1).all()
    rs = loaded["route_stops"]
    assert "25/25A" in set(rs.route_no)
    assert set(rs.route_no) <= set(routes.route_no)
    isbt17 = loaded["stops"].set_index("stop").at["ISBT-17", "n_routes_serving"]
    assert isbt17 == 47


def test_wrong_totals_fail_loudly(loaded):
    rm = D.read_route_master(D._open()[1])
    bad = rm.copy()
    bad.loc[0, "x_base"] += 1
    with pytest.raises(D.DataError):
        D.build_routes(bad, loaded["ow"])
    with pytest.raises(D.DataError):
        D.build_routes(rm.iloc[:-1], loaded["ow"])


def test_routes_csv_round_trip(tmp_path, loaded):
    p = tmp_path / "routes.csv"
    loaded["routes"].to_csv(p, index=False)
    back = D.read_routes_csv(p)
    assert back.route_no.tolist() == loaded["routes"].route_no.tolist()
    assert isinstance(back.route_no.iloc[0], str)
