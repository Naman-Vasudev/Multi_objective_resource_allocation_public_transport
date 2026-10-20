"""Stage 5 tests: front metrics, repair feasibility, NSGA-II reproducibility, AUGMECON efficiency, saved outputs."""
import numpy as np
import pandas as pd
import pytest

from src import demand as DM
from src import metrics as MT
from src import params as P
from src import pareto as PA
from src import stage5


# ---------------------------------------------------------------- metrics (pure)
def test_hypervolume_simple_cases():
    ref = [1, 1, 1]
    assert PA.hypervolume([[0, 0, 0]], ref) == pytest.approx(1.0)
    assert PA.hypervolume([[0.5, 0.5, 0.5]], ref) == pytest.approx(0.125)
    # two boxes [0,1]x[0.5,1]x[0,1] and [0.5,1]x[0,1]x[0,1] overlap in [0.5,1]x[0.5,1]x[0,1]
    assert PA.hypervolume([[0, 0.5, 0], [0.5, 0, 0]], ref) == pytest.approx(0.5 + 0.5 - 0.25)
    assert PA.hypervolume([[1.2, 0, 0]], ref) == 0.0                       # outside the reference box
    assert PA.hypervolume([[0, 0, 0], [0.5, 0.5, 0.5]], ref) == pytest.approx(1.0)  # dominated point adds nothing


def test_hypervolume_matches_monte_carlo():
    rng = np.random.default_rng(0)
    pts = rng.random((25, 3))
    hv = PA.hypervolume(pts, [1, 1, 1])
    s = rng.random((200_000, 3))
    mc = np.mean([np.any(np.all(pts <= q, axis=1)) for q in s[:20_000]])
    assert hv == pytest.approx(mc, abs=0.01)


def test_nondominated_gd_igd_coverage():
    pts = np.array([[1, 2, 3], [2, 1, 3], [2, 2, 3], [1, 2, 3]])
    assert PA.nondominated(pts).tolist() == [True, True, False, False]   # dominated + duplicate removed
    A = np.array([[0.0, 0, 0]]); B = np.array([[3.0, 4, 0]])
    assert PA.gd(B, A) == pytest.approx(5.0) and PA.igd(B, A) == pytest.approx(5.0)
    assert PA.coverage(A, B) == 1.0 and PA.coverage(B, A) == 0.0
    assert PA.n_strictly_dominated(A, B) == 1 and PA.n_strictly_dominated(A, A) == 0
    d, dom = PA.nearest_distance([1, 1, 1], A)
    assert d == pytest.approx(np.sqrt(3)) and dom


# ---------------------------------------------------------------- real instance
@pytest.fixture(scope="module")
def inst(loaded):
    _, dem, _ = DM.demand_table(loaded)
    return stage5.stage5_instance(loaded["routes"], dem)


@pytest.fixture(scope="module")
def enc(inst):
    xb, fb = MT.baseline_schedule(inst)
    b = MT.evaluate(inst, xb, fb)
    return PA.make_encoding(inst, {"Z1": b["Z1"], "Z2": b["Z2"], "Z3": b["Z3"]})


def test_repair_always_feasible_and_objectives_consistent(inst, enc):
    rng = np.random.default_rng(1)
    for _ in range(30):
        g = [int(rng.integers(0, m)) for m in enc.n_opt]
        if rng.random() < 0.5:
            g = [0] * len(g)                                              # all-shortest headways: worst case
        k = PA.repair(enc, g)
        hw = PA.headways_of(enc, k)
        x, f, m = PA.evaluate_headways(inst, hw)
        v = MT.check_schedule(inst, x, f)
        assert v[~v.constraint.str.startswith("C5 equity")].empty
        z = PA.objectives(enc, k)
        assert z == pytest.approx((m["Z1"], m["Z2"], m["Z3"]), rel=1e-9)


def test_nsga2_reproducible_with_fixed_seed(inst, enc):
    a = PA.nsga2(enc, seed=7, pop_size=20, n_gen=4)
    b = PA.nsga2(enc, seed=7, pop_size=20, n_gen=4)
    c = PA.nsga2(enc, seed=8, pop_size=20, n_gen=4)
    np.testing.assert_allclose(a["front"], b["front"])
    assert a["genomes"] == b["genomes"]
    assert not (a["front"].shape == c["front"].shape and np.allclose(a["front"], c["front"]))
    assert a["n_eval"] == 20 * 5
    stage5.verify_points(inst, [PA.headways_of(enc, g) for g in a["genomes"]], a["front"])


def test_augmecon_small_grid_is_efficient_and_within_bounds(inst):
    pay, ideal, nadir, pay_hw = PA.lexicographic_payoff(inst, return_headways=True)
    assert ideal["Z3"] == pytest.approx(pay.loc[pay.minimised == "Z3", "Z3"].iloc[0])
    grid, front, hws = PA.augmecon(inst, ideal, nadir, n_grid=3, extra_headways=pay_hw)
    assert len(grid) == 9 and len(front) >= 3
    stage5.verify_points(inst, hws, front[list(PA.OBJ)].to_numpy())
    ok = grid[grid.status == "Optimal"]
    assert (ok.Z1 <= ok.e1 * (1 + 1e-6) + 1e-6).all() and (ok.Z2 <= ok.e2 * (1 + 1e-6) + 1e-6).all()
    F = front[list(PA.OBJ)].to_numpy()
    assert PA.nondominated(F).all()
    for p in pay[list(PA.OBJ)].to_numpy():                               # payoff rows are on the front
        assert np.any(np.all(np.abs(F - p) <= 1e-6 * np.abs(p) + 1e-6, axis=1))


# ---------------------------------------------------------------- saved outputs (after `python run_all.py`)
@pytest.mark.parametrize("fname", ["pareto_eps.csv", "pareto_nsga2.csv"])
def test_every_saved_point_satisfies_all_constraints(inst, fname):
    path = P.OUT / fname
    if not path.exists():
        pytest.skip("run `python run_all.py` first")
    df = pd.read_csv(path)
    hws = [stage5.parse_hw(s) for s in df.headways]
    assert stage5.verify_points(inst, hws, df[["Z1", "Z2", "Z3"]].to_numpy()) == len(df)


def test_saved_metrics_show_exact_points_not_dominated():
    path = P.OUT_TAB / "pareto_metrics.csv"
    if not path.exists():
        pytest.skip("run `python run_all.py` first")
    m = pd.read_csv(path)
    assert (m.eps_points_strictly_dominated == 0).all()
    assert (m[m.method == "NSGA-II"].seed.astype(int).tolist() == list(P.NSGA_SEEDS))
