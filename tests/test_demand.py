"""Stage 2 tests: periods, TFNs, alpha-cuts, and the Synthetic Demand sheet requirement."""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

from src import data as D
from src import demand as DM
from src import params as P

T = dt.time


# ---------------------------------------------------------------- periods
def test_periods_in_sync_with_sheet(loaded):
    assert loaded["periods"] == P.PERIODS
    assert {t: e - s for t, (s, e) in P.PERIODS.items()} == {"AM": 3.0, "Midday": 6.0, "PM": 3.0}


@pytest.fixture(scope="module")
def per(loaded):
    return DM.period_table(loaded["ow"], loaded["periods"])


def test_active_counts_match_sheet_totals(per):
    # Operating Windows row 75 ("Routes active") shows 64 / 65 / 62
    assert per.groupby("period").active.sum().to_dict() == {"AM": 64, "Midday": 65, "PM": 62}


def test_specific_routes(per):
    a = per.set_index(["route_no", "period"]).active
    assert [a["11A", t] for t in ("AM", "Midday", "PM")] == [0, 1, 0]     # 10:10-15:50
    for night in ("24A", "24C", "37"):
        assert [a[night, t] for t in ("AM", "Midday", "PM")] == [0, 0, 0]
    assert [a["38AB", t] for t in ("AM", "Midday", "PM")] == [1, 1, 1]


def test_overlap_hours():
    assert D.period_overlap_hours(T(6, 10), T(18, 40), 16, 19) == pytest.approx(2 + 40 / 60)
    assert D.period_overlap_hours(T(8, 30), T(14, 20), 7, 10) == pytest.approx(1.5)
    assert D.period_overlap_hours(T(22, 0), T(4, 40), 7, 10) == 0.0
    assert D.period_overlap_hours(T(5, 0), T(23, 0), 10, 16) == pytest.approx(6.0)
    assert D.period_overlap_hours(T(0, 40), T(23, 30), 7, 10) == pytest.approx(3.0)


def test_period_mismatch_fails_loudly(loaded, monkeypatch):
    monkeypatch.setattr(P, "PERIODS", {"AM": (6.0, 10.0), "Midday": (10.0, 16.0), "PM": (16.0, 19.0)})
    with pytest.raises(D.DataError):
        D.read_period_boundaries(loaded["wb_v"])


# ---------------------------------------------------------------- TFN and alpha-cuts
def test_tfn_defaults():
    L, M, U = DM.tfn_from_modal(100.0)
    assert (float(L), float(M), float(U)) == pytest.approx((80.0, 100.0, 135.0))


def test_alpha_one_gives_modal_alpha_zero_gives_support():
    L, M, U = DM.tfn_from_modal(np.array([50.0, 200.0]))
    np.testing.assert_allclose(DM.alpha_cut_upper(U, M, 1.0), M)
    np.testing.assert_allclose(DM.alpha_cut_lower(L, M, 1.0), M)
    np.testing.assert_allclose(DM.alpha_cut_upper(U, M, 0.0), U)   # most conservative
    np.testing.assert_allclose(DM.alpha_cut_lower(L, M, 0.0), L)


def test_upper_cut_is_U_minus_alpha_spread_not_old_formula():
    L, M, U = 80.0, 100.0, 135.0
    assert DM.alpha_cut_upper(U, M, 0.5) == pytest.approx(117.5)
    # the synopsis' original L + (1 - alpha)(M - L) would give 90 here: a lower bound, wrong side
    assert DM.alpha_cut_upper(U, M, 0.5) != pytest.approx(L + 0.5 * (M - L))


def test_alpha_cut_monotone_and_on_membership():
    L, M, U = 80.0, 100.0, 135.0
    al = np.linspace(0, 1, 11)
    up, low = DM.alpha_cut_upper(U, M, al), DM.alpha_cut_lower(L, M, al)
    assert (np.diff(up) <= 0).all() and (np.diff(low) >= 0).all()
    np.testing.assert_allclose(DM.membership(up, L, M, U), al, atol=1e-12)
    np.testing.assert_allclose(DM.membership(low, L, M, U), al, atol=1e-12)


@pytest.mark.parametrize("alpha", [-0.1, 1.1])
def test_alpha_out_of_range(alpha):
    with pytest.raises(ValueError):
        DM.alpha_cut_upper(135.0, 100.0, alpha)


def test_bad_spreads_rejected():
    with pytest.raises(ValueError):
        DM.tfn_from_modal(1.0, lo=1.0)
    with pytest.raises(ValueError):
        DM.tfn_from_modal(1.0, hi=-0.1)
    with pytest.raises(ValueError):
        DM.tfn_from_modal(-1.0)


def test_route_override_and_checks():
    df = pd.DataFrame({"route_no": ["1", "38AB", "1", "38AB"], "period": ["AM", "AM", "PM", "PM"],
                       "M": [100.0, 40.0, 90.0, 30.0]})
    out = DM.add_tfn(df, overrides={"38AB": (0.10, 0.50)})
    r = out.set_index(["route_no", "period"])
    assert (r.at[("1", "AM"), "L"], r.at[("1", "AM"), "U"]) == pytest.approx((80.0, 135.0))
    assert (r.at[("38AB", "AM"), "L"], r.at[("38AB", "AM"), "U"]) == pytest.approx((36.0, 60.0))
    stats = DM.check_demand(out)
    assert all(v > 0 for v in stats["cv_by_period"].values())


def test_check_demand_rejects_bad_tables():
    bad = pd.DataFrame({"route_no": ["1", "2"], "period": ["AM", "AM"],
                        "L": [10.0, -1.0], "M": [20.0, 5.0], "U": [30.0, 6.0]})
    with pytest.raises(D.DataError):
        DM.check_demand(bad)
    flat = pd.DataFrame({"route_no": ["1", "2"], "period": ["AM", "AM"],
                         "L": [8.0, 8.0], "M": [10.0, 10.0], "U": [13.5, 13.5]})
    with pytest.raises(D.DataError):
        DM.check_demand(flat)


# ---------------------------------------------------------------- synthetic demand
@pytest.fixture(scope="module")
def demand(loaded):
    return DM.demand_table(loaded)


def test_daily_boardings_calibration(demand):
    base, _, _ = demand
    assert P.DAILY_BOARDINGS == pytest.approx(143_000 * 389 / 684)
    assert P.THETA * (base.D_ref * base.span_hours).sum() == pytest.approx(P.DAILY_BOARDINGS)


def test_demand_sanity(demand):
    _, dem, _ = demand
    assert len(dem) == 68 * 3
    a = dem[dem.active == 1]
    assert (a.M > 0).all() and (dem[dem.active == 0].M == 0).all()
    stats = DM.check_demand(a)
    assert all(0.1 < cv < 2 for cv in stats["cv_by_period"].values())
    np.testing.assert_allclose(a.L, 0.8 * a.M)
    np.testing.assert_allclose(a.U, 1.35 * a.M)


def test_multipliers_applied(demand):
    _, dem, _ = demand
    r = dem[dem.route_no == "38AB"].set_index("period").M   # active in all three periods
    assert r["AM"] / r["Midday"] == pytest.approx(1.4 / 0.8)
    assert r["PM"] / r["Midday"] == pytest.approx(1.3 / 0.8)


def test_noise_reproducible_and_seed_dependent():
    np.testing.assert_array_equal(DM.noise_factors(68, 42), DM.noise_factors(68, 42))
    assert not np.allclose(DM.noise_factors(68, 42), DM.noise_factors(68, 7))


def test_theta_scales_demand_inversely(loaded):
    b1, _, _ = DM.demand_table(loaded, theta=1.2)
    b2, _, _ = DM.demand_table(loaded, theta=2.4)
    np.testing.assert_allclose(b1.D_ref, 2 * b2.D_ref)


def test_flags(loaded):
    fl = DM.route_flags(loaded["routes"], loaded["route_stops"], loaded["features"]).set_index("route_no")
    assert fl.at["32", "derabassi"] == 1 and fl.at["32", "outskirts"] == 1
    assert fl.at["551", "serves_PGI"] == 1 and fl.at["551", "serves_ISBT-43"] == 1
