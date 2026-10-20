"""Stage 3 tests: brute-force toy check, units, baseline constraint report, monotonicity in C."""
import itertools
import math

import numpy as np
import pytest

from src import demand as DM
from src import metrics as MT
from src import model as MD
from src import params as P


# ---------------------------------------------------------------- toy instance
def toy_instance(C=60.0, fleet_B=12, spare=0.0):
    cfg = P.ModelConfig(C=C, spare_ratio=spare, fleet_B=fleet_B, equity_mode="off",
                        pract_abs=10, pract_rel=10, pract_min=10, menu_min=(10, 15, 20, 30))
    periods = list(P.PERIODS)
    n = 3
    tau = np.array([1.0, 1.5, 0.8])            # [h]
    d_cycle = np.array([20.0, 30.0, 16.0])     # [km]
    x0 = np.array([4, 4, 3])
    h_lo, h_hi = np.array([10.0, 15.0, 15.0]), np.array([20.0, 30.0, 30.0])
    f_min, f_max = 60 / h_hi, 60 / h_lo
    M = {(0, "AM"): 300, (0, "Midday"): 120, (0, "PM"): 250,
         (1, "AM"): 200, (1, "Midday"): 90, (1, "PM"): 210,
         (2, "AM"): 150, (2, "Midday"): 60, (2, "PM"): 0}
    active = {(i, t): not (i == 2 and t == "PM") for i in range(n) for t in periods}
    H = {(i, t): (P.PERIODS[t][1] - P.PERIODS[t][0]) if active[i, t] else 0.0 for i in range(n) for t in periods}
    Da = {k: float(DM.alpha_cut_upper(1.35 * v, v, 0.5)) for k, v in M.items()}
    menu = {(i, t): MD.route_menu(h_lo[i], h_hi[i], cfg, t) if active[i, t] else []
            for i in range(n) for t in periods}
    lb, ub = MD.practicality_bounds(x0, cfg)
    return MD.Instance(["A", "B", "C"], periods, tau, d_cycle, x0, (f_min + f_max) / 2, f_min, f_max,
                       h_lo, h_hi, active, H, {k: float(v) for k, v in M.items()}, Da, menu, lb, ub, cfg)


def brute_force(inst, weights):
    """Enumerate every headway choice; x = smallest feasible integer (x does not enter Z1-Z3)."""
    pairs = inst.active_pairs()
    best = math.inf
    for choice in itertools.product(*[inst.menu[p] for p in pairs]):
        f = {p: 60.0 / h for p, h in zip(pairs, choice)}
        x = {p: max(int(inst.x_lb[p[0]]), math.ceil(f[p] * inst.tau[p[0]] - 1e-9)) for p in pairs}
        if any(x[p] > inst.x_ub[p[0]] for p in pairs):
            continue
        if any(sum(x[p] for p in pairs if p[1] == t) > inst.cfg.B_eff for t in inst.periods):
            continue
        m = MT.evaluate(inst, x, f)
        best = min(best, sum(w * m[k] for k, w in weights.items()))
    return best


@pytest.mark.parametrize("weights", [{"Z3": 1.0}, {"Z1": 1.0}, {"Z2": 1.0},
                                     {"Z1": 1.0, "Z2": 0.5, "Z3": 10.0}])
def test_toy_milp_matches_brute_force(weights):
    inst = toy_instance()
    res = MD.solve(MD.build_model(inst, weights))
    assert res["objective"] == pytest.approx(brute_force(inst, weights), rel=1e-7, abs=1e-6)
    x, f = MD.schedule_to_arrays(inst, res["schedule"])
    assert MT.check_schedule(inst, x, f).empty


def test_toy_fleet_binds():
    loose, tight = toy_instance(fleet_B=40), toy_instance(fleet_B=12)
    z_loose = MD.solve(MD.build_model(loose, {"Z3": 1}))["objective"]
    z_tight = MD.solve(MD.build_model(tight, {"Z3": 1}))["objective"]
    assert z_tight >= z_loose - 1e-6
    assert z_tight == pytest.approx(brute_force(tight, {"Z3": 1}))


# ---------------------------------------------------------------- units
def test_units_single_route():
    inst = toy_instance()
    p = (0, "AM")
    x, f = {q: 10 for q in inst.active_pairs()}, {q: 3.0 for q in inst.active_pairs()}  # 20-min headway
    m = MT.evaluate(inst, x, f)
    pairs = inst.active_pairs()
    # Z2 [veh-km/day] = sum d_cycle [km] * H [h] * f [dep/h]
    assert m["Z2"] == pytest.approx(sum(inst.d_cycle[i] * inst.H[i, t] * 3.0 for i, t in pairs))
    # Z1 [pax*min/h] = sum M [pax/h] * h/2 [min], h = 60/3 = 20 min
    assert m["Z1"] == pytest.approx(sum(inst.M[q] * 10.0 for q in pairs))
    # Z3 [pax/day] = sum max(0, D_alpha - C f) * H; capacity 60 * 3 = 180 pax/h
    assert m["Z3"] == pytest.approx(sum(max(0, inst.D_alpha[q] - 180) * inst.H[q] for q in pairs))
    assert m["mean_wait_min"] == pytest.approx(10.0) and m["max_wait_min"] == pytest.approx(10.0)
    assert m["ewt_min"] == pytest.approx(10.0 * 0.3 ** 2)   # (h/2) CV^2
    assert inst.D_alpha[p] == pytest.approx(300 * 1.175)


def test_menu_contains_published_headways_and_modes():
    cfg = P.ModelConfig()
    assert MD.route_menu(80, 80, cfg, "Midday") == [80]                 # not in K, still allowed
    assert MD.route_menu(20, 40, cfg, "AM") == [20, 25, 30, 40]
    assert MD.route_menu(20, 25, P.ModelConfig(fmax_mode="relaxed"), "AM") == [12, 15, 20, 25]
    assert MD.route_menu(90, 90, P.ModelConfig(equity_mode="hard"), "AM") == []
    assert MD.route_menu(90, 90, P.ModelConfig(equity_mode="hard", fmax_mode="relaxed"), "AM") == [45, 60]


def test_practicality_bounds():
    lb, ub = MD.practicality_bounds(np.array([1, 3, 4, 10, 14]), P.ModelConfig())
    assert lb.tolist() == [0, 2, 3, 7, 11] and ub.tolist() == [2, 4, 5, 13, 17]
    lb0, ub0 = MD.practicality_bounds(np.array([1, 3, 4]), P.ModelConfig(pract_min=0))
    assert lb0.tolist() == [1, 3, 3] and ub0.tolist() == [1, 3, 5]      # brief's literal rule


def test_gini():
    assert MT.gini([1, 1, 1, 1]) == pytest.approx(0.0)
    assert MT.gini([0, 0, 0, 1]) == pytest.approx(0.75)


# ---------------------------------------------------------------- real instance
@pytest.fixture(scope="module")
def real(loaded):
    _, dem, _ = DM.demand_table(loaded)
    return loaded["routes"], dem


def test_B_eff():
    assert P.ModelConfig().B_eff == 357
    assert P.ModelConfig(spare_ratio=0.10).B_eff == 350


def test_baseline_constraint_report_is_precise(real):
    routes, dem = real
    inst = MD.build_instance(routes, dem)
    x, f = MT.baseline_schedule(inst)
    v = MT.check_schedule(inst, x, f)
    c1 = v[v.constraint == "C1 fleet"].set_index("period").excess
    assert c1.to_dict() == {"AM": 384 - 357, "Midday": 385 - 357, "PM": 380 - 357}
    c2 = v[v.constraint == "C2 f*tau <= x"]
    assert set(c2.route_no) == {"40", "76", "25/25A"}
    r76 = c2[(c2.route_no == "76") & (c2.period == "AM")].iloc[0]
    assert r76.excess == pytest.approx(1.75 * 2 * 31 / 22 * 1.1 - 4)
    assert not v.constraint.str.startswith("C4").any()


def test_spare_10pct_reported_infeasible(real):
    routes, dem = real
    msgs = MD.presolve_report(MD.build_instance(routes, dem, P.ModelConfig(spare_ratio=0.10)))
    assert "AM: minimum buses 352 exceed B_eff = 350" in msgs
    assert "Midday: minimum buses 353 exceed B_eff = 350" in msgs
    assert MD.presolve_report(MD.build_instance(routes, dem)) == []


def test_full_model_solves_fast_and_feasible(real):
    routes, dem = real
    inst = MD.build_instance(routes, dem)
    res = MD.solve(MD.build_model(inst, {"Z3": 1.0}), time_limit=60)
    assert res["wall_s"] < 60
    x, f = MD.schedule_to_arrays(inst, res["schedule"])
    v = MT.check_schedule(inst, x, f)
    assert v[~v.constraint.str.startswith("C5 equity")].empty


def test_Z3_monotone_in_capacity(real):
    routes, dem = real
    z = []
    for C in (50, 60, 70, 80):
        inst = MD.build_instance(routes, dem, P.ModelConfig(C=C, equity_mode="off"))
        z.append(MD.solve(MD.build_model(inst, {"Z3": 1.0}))["Z"]["Z3"])
    assert all(b <= a + 1e-6 for a, b in zip(z, z[1:])), z
