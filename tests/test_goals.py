"""Stage 4 tests: preemptive GP is lexicographic (toy brute force + real instance), priorities matter, configs load."""
import dataclasses
import itertools
import json
import math

import pytest

from src import demand as DM
from src import goals as G
from src import metrics as MT
from src import model as MD
from src import params as P
from src import stage4
from test_model import toy_instance


def toy_with_caps():
    inst = toy_instance()
    cfg = dataclasses.replace(inst.cfg, equity_cap_min={"AM": 12, "Midday": 20, "PM": 12})
    return dataclasses.replace(inst, cfg=cfg)


def brute_lexicographic(inst, tg, levels, tol=1e-6):
    """Enumerate every headway choice and return the lexicographic minimum of the level deviations."""
    pairs = inst.active_pairs()
    vecs = []
    for choice in itertools.product(*[inst.menu[p] for p in pairs]):
        f = {p: 60.0 / h for p, h in zip(pairs, choice)}
        x = {p: max(int(inst.x_lb[p[0]]), math.ceil(f[p] * inst.tau[p[0]] - 1e-9)) for p in pairs}
        if any(x[p] > inst.x_ub[p[0]] for p in pairs):
            continue
        if any(sum(x[p] for p in pairs if p[1] == t) > inst.cfg.B_eff for t in inst.periods):
            continue
        dv = G.deviations_of(inst, tg, MT.evaluate(inst, x, f))
        vecs.append([sum(dv[g] / tg.scale[g] for g in lv) if len(lv) > 1 else dv[lv[0]] for lv in levels])
    best = []
    for k in range(len(levels)):
        m = min(v[k] for v in vecs)
        best.append(m)
        vecs = [v for v in vecs if v[k] <= m + tol * max(1.0, abs(m))]
    return best


@pytest.mark.parametrize("order", [["G2", "G1", "G4", "G3"], ["G3", "G2", "G1", "G4"],
                                   ["G4", "G2", "G1", "G3"], ["G1", "G3", "G2", "G4"]])
def test_toy_preemptive_equals_brute_force_lexicographic(order):
    inst = toy_with_caps()
    tg = G.make_targets(inst, kappa1=0.15)
    levels = [[g] for g in order]
    out = G.solve_preemptive(inst, tg, levels)
    got = [r["achieved_dev"] for r in out["levels"]]
    want = brute_lexicographic(inst, tg, levels)
    assert got == pytest.approx(want, rel=1e-6, abs=1e-5)
    x, f = MD.schedule_to_arrays(inst, out["result"]["schedule"])
    assert stage4.lexicographic_ok(inst, tg, levels, out["levels"], MT.evaluate(inst, x, f))


@pytest.fixture(scope="module")
def relaxed(loaded):
    _, dem, _ = DM.demand_table(loaded)
    inst = MD.build_instance(loaded["routes"], dem, P.ModelConfig(fmax_mode="relaxed"))
    return inst, G.make_targets(inst, 0.15)


def _run(inst, tg, sc):
    out = G.run_scenario(inst, tg, sc)
    x, f = MD.schedule_to_arrays(inst, out["result"]["schedule"])
    m = MT.evaluate(inst, x, f)
    return out, m, G.deviations_of(inst, tg, m)


def test_real_lexicographic_and_first_level_is_ideal(relaxed):
    inst, tg = relaxed
    _, ideal, _ = G.payoff_table(inst)
    for name, order, first_key in (("P-PASSENGER", ["G2", "G1", "G4", "G3"], "Z3"),
                                   ("P-EQUITY", ["G4", "G2", "G1", "G3"], "equity_excess_min")):
        levels = [[g] for g in order]
        out, m, _ = _run(inst, tg, {"name": name, "type": "preemptive", "levels": levels})
        assert out["status"] == "Optimal"
        assert stage4.lexicographic_ok(inst, tg, levels, out["levels"], m)
        assert out["levels"][0]["achieved_dev"] == pytest.approx(ideal[first_key], rel=1e-6, abs=1e-6)


def test_priorities_change_the_answer(relaxed):
    inst, tg = relaxed
    _, _, d_pax = _run(inst, tg, {"type": "preemptive", "levels": [["G2"], ["G1"], ["G4"], ["G3"]]})
    _, _, d_eq = _run(inst, tg, {"type": "preemptive", "levels": [["G4"], ["G2"], ["G1"], ["G3"]]})
    assert d_eq["G4"] <= d_pax["G4"] + 1e-6 and d_pax["G2"] <= d_eq["G2"] + 1e-6
    assert d_eq["G4"] < d_pax["G4"] - 1           # a real trade-off exists in relaxed mode


def test_weighted_objective_matches_evaluation(relaxed):
    inst, tg = relaxed
    w = {"G1": 1, "G2": 1, "G3": 1, "G4": 1}
    out, _, dv = _run(inst, tg, {"type": "weighted", "weights": w})
    assert out["levels"][0]["achieved_dev"] == pytest.approx(sum(dv[g] / tg.scale[g] for g in w), rel=1e-5)


def test_chebyshev_minimises_the_largest_normalised_deviation(relaxed):
    inst, tg = relaxed
    w = {"G1": 1, "G2": 1, "G3": 1, "G4": 1}
    _, _, dc = _run(inst, tg, {"type": "chebyshev", "weights": w})
    _, _, dw = _run(inst, tg, {"type": "weighted", "weights": w})
    mx = lambda d: max(d[g] / tg.scale[g] for g in w)  # noqa: E731
    assert mx(dc) <= mx(dw) + 1e-6


def test_targets_and_deviation_signs(relaxed):
    inst, tg = relaxed
    assert tg.T1 == pytest.approx(0.85 * tg.baseline["Z1"]) and tg.T3 == pytest.approx(tg.baseline["Z2"])
    assert tg.T2 == 0.0
    dv = G.deviations_of(inst, tg, tg.baseline)
    assert dv["G3"] == 0.0 and dv["G1"] > 0       # baseline meets its own vehicle-km, not the 15% wait cut


def test_config_loading(tmp_path):
    cfg = G.load_config()
    assert [s["name"] for s in cfg["scenarios"]][:3] == ["P-PASSENGER", "P-OPERATOR", "P-EQUITY"]
    assert cfg["scenarios"][0]["levels"] == [["G2"], ["G1"], ["G4"], ["G3"]]
    p = tmp_path / "c.json"
    p.write_text(json.dumps({**cfg, "scenarios": [{"name": "TIE", "type": "preemptive", "order": [["G1", "G2"], "G3"]}]}))
    assert G.load_config(p)["scenarios"][0]["levels"] == [["G1", "G2"], ["G3"]]
    p.write_text(json.dumps({**cfg, "scenarios": [{"name": "BAD", "type": "preemptive", "order": ["G9"]}]}))
    with pytest.raises(ValueError):
        G.load_config(p)
