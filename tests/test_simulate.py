"""Stage 6 tests: waiting formula, demand sampling, deterministic consistency with the model, schedule feasibility."""
import numpy as np
import pandas as pd
import pytest

from src import demand as DM
from src import metrics as MT
from src import model as MD
from src import params as P
from src import simulate as S
from src import stage6


def test_gamma_headway_wait_formula():
    """Random arrivals on a gamma headway process: E[W] = E[H^2] / (2 E[H]) = (h/2)(1 + CV^2)."""
    rng = np.random.default_rng(0)
    for h, cv in ((10.0, 0.3), (20.0, 0.5), (60.0, 0.1)):
        H = rng.gamma(shape=1 / cv ** 2, scale=h * cv ** 2, size=400_000)
        assert H.mean() == pytest.approx(h, rel=0.01)
        assert (H ** 2).sum() / (2 * H.sum()) == pytest.approx(h / 2 * (1 + cv ** 2), rel=0.01)


def test_triangular_and_shock_moments():
    L, M, U = np.array([80.0, 0.0]), np.array([100.0, 10.0]), np.array([135.0, 13.5])
    D = S.draw_demand(L, M, U, n=200_000, seed=3, shock_sd=0.05)
    np.testing.assert_allclose(D.mean(0), (L + M + U) / 3, rtol=0.01)   # E[shock] = 1, independent
    assert (D >= 0).all()
    np.testing.assert_array_equal(D, S.draw_demand(L, M, U, n=200_000, seed=3, shock_sd=0.05))
    # the shock is common: pairs are positively correlated
    assert np.corrcoef(D[:, 0], D[:, 1])[0, 1] > 0.05


def test_widen_keeps_mode_and_stretches_spreads():
    dem = pd.DataFrame({"route_no": ["1"], "period": ["AM"], "L": [80.0], "M": [100.0], "U": [135.0]})

    class Fake:  # minimal stand-in exposing what tfn_arrays needs
        route_no = ["1"]

        def active_pairs(self):
            return [(0, "AM")]
    L, M, U = S.tfn_arrays(Fake(), dem, widen=1.5)
    assert (L[0], M[0], U[0]) == pytest.approx((70.0, 100.0, 152.5))


@pytest.fixture(scope="module")
def setup(loaded):
    _, dem, _ = DM.demand_table(loaded)
    inst = MD.build_instance(loaded["routes"], dem, stage6._cfg())
    return inst, dem


def test_deterministic_simulation_matches_model_metrics(setup):
    inst, dem = setup
    b = S.baseline(inst)
    pairs = inst.active_pairs()
    Dm = np.array([[inst.M[p] for p in pairs]])
    per, _ = S.simulate(inst, b, Dm, cv=0.0)
    xb, fb = MT.baseline_schedule(inst)
    m = MT.evaluate(inst, xb, fb)
    assert per["total_wait_pax_min"][0] == pytest.approx(m["Z1_daily"])
    assert per["vehicle_km"][0] == pytest.approx(m["Z2"])
    assert per["fleet_used"][0] == m["fleet_used"]
    assert per["equity_excess_min"][0] == pytest.approx(m["equity_excess_min"])
    Da = np.array([[inst.D_alpha[p] for p in pairs]])
    assert S.simulate(inst, b, Da)[0]["overflow_pax"][0] == pytest.approx(m["Z3"])
    # EWT = (h/2) CV^2 per passenger
    per3, _ = S.simulate(inst, b, Dm, cv=0.3)
    assert per3["ewt_min"][0] == pytest.approx(per3["mean_wait_min"][0] * 0.09 / 1.09)


def test_more_capacity_never_increases_overflow(setup):
    inst, dem = setup
    b = S.baseline(inst)
    L, M, U = S.tfn_arrays(inst, dem)
    D = S.draw_demand(L, M, U, n=300)
    o = [S.simulate(inst, b, D, C=c)[0]["overflow_pax"] for c in (50, 60, 70)]
    assert (o[0] >= o[1] - 1e-9).all() and (o[1] >= o[2] - 1e-9).all()


def test_optimised_schedules_are_feasible(setup, loaded):
    inst, dem = setup
    scs = stage6._scenarios()
    s, st = S.from_gp(inst, "P-BALANCED", scs["P-BALANCED"], 0.15, 0.5)
    assert st == "Optimal"
    pairs = inst.active_pairs()
    x = {p: int(v) for p, v in zip(pairs, s.x)}
    f = {p: float(v) for p, v in zip(pairs, s.f)}
    v = MT.check_schedule(inst, x, f)
    assert v[~v.constraint.str.startswith("C5 equity")].empty
    assert s.x.reshape(-1).sum() > 0


def test_infeasible_settings_are_reported_not_hidden(setup, loaded):
    inst, dem = setup
    r = stage6.policy_vs_baseline(loaded["routes"], dem, stage6._cfg(spare_ratio=0.10))
    assert r["feasible"] is False and "352 exceed B_eff = 350" in r["reason"]


def test_saved_outputs_have_synthetic_label_and_required_rows():
    path = P.OUT / "simulation_summary.csv"
    if not path.exists():
        pytest.skip("run `python run_all.py` first")
    s = pd.read_csv(path)
    assert (s.label == "synthetic demand, illustrative").all()
    names = set(s.schedule)
    assert "Baseline" in names and "KNEE (Pareto front)" in names
    for nm in stage6.GP_NAMES:
        for a in P.SIM_ALPHAS:
            assert f"{nm} (α={a:g})" in names
    assert s.metric.str.startswith("P(overflow").any()
    for stat in ("mean", "sd", "p5", "p95"):
        assert stat in s.columns
