"""Goal programming on top of the Stage 3 MILP (plain-language guide: docs/GOAL_PROGRAMMING.md).

Goals (targets relative to the published baseline evaluated at the same alpha):
    G1 waiting      Z1 + n1 - p1 = T1 = (1 - kappa1) Z1_base     unwanted p1   [pax*min/h]
    G2 unserved     Z3 + n2 - p2 = 0                             unwanted p2   [pax/day]
    G3 vehicle-km   Z2 + n3 - p3 = T3 = (1 - kappa3) Z2_base     unwanted p3   [veh-km/day]
    G4 equity       h_rt - Hcap_t <= p4_rt, p4_rt >= 0           unwanted sum p4_rt [min]
Hard constraints C1-C6 (fleet, frequency-fleet, ...) stay hard. Demand is SYNTHETIC.

Methods
    preemptive  minimise each priority level in order, locking earlier levels at their achieved value
    weighted    one solve, minimise sum_i w_i dev_i / scale_i  (scale_i = baseline value)
    chebyshev   one min-max solve, min lambda s.t. w_i dev_i / scale_i <= lambda (then tidy up)
Every method ends with a "tidy" solve that minimises total buses with all goal results locked, so the reported
fleet is not arbitrary (buses do not enter Z1-Z3).
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import pulp

from src import metrics as MT
from src import model as MD
from src import params as P

GOALS = ("G1", "G2", "G3", "G4")
GOAL_INFO = {
    "G1": ("passenger waiting Z1", "pax*min/h"),
    "G2": ("unserved demand Z3", "pax/day"),
    "G3": ("vehicle-km Z2", "veh-km/day"),
    "G4": ("equity: headway above cap", "min"),
}
CONFIG_PATH = P.ROOT / "config" / "gp_scenarios.json"
GAP_REL = 1e-6          # tight MIP gap so locked levels are true optima
LOCK_ABS = 1e-6         # lock tolerance: dev <= achieved + LOCK_ABS + LOCK_REL * achieved
LOCK_REL = 1e-7


def load_config(path: Path | None = None) -> dict:
    """Read the scenario file (config/gp_scenarios.json); user-defined orderings go there."""
    cfg = json.loads(Path(path or CONFIG_PATH).read_text(encoding="utf-8"))
    for s in cfg["scenarios"]:
        if s["type"] == "preemptive":
            levels = [[g] if isinstance(g, str) else list(g) for g in s["order"]]
            bad = [g for lv in levels for g in lv if g not in GOALS]
            if bad:
                raise ValueError(f"scenario {s['name']}: unknown goals {bad}")
            s["levels"] = levels
        elif s["type"] in ("weighted", "chebyshev"):
            if set(s["weights"]) - set(GOALS):
                raise ValueError(f"scenario {s['name']}: unknown goals in weights")
        else:
            raise ValueError(f"scenario {s['name']}: unknown type {s['type']!r}")
    return cfg


# ======================================================================
# Targets and the goal model
# ======================================================================


@dataclass
class Targets:
    T1: float
    T2: float
    T3: float
    scale: dict          # goal -> normalisation constant (baseline value, or 1 if the baseline is 0)
    baseline: dict = field(default_factory=dict)


def make_targets(inst: MD.Instance, kappa1: float = 0.15, kappa3: float = 0.0) -> Targets:
    """Targets and scales from the published baseline schedule evaluated on this instance (same alpha).

    T1 = (1 - kappa1) Z1_base (waiting cut), T3 = (1 - kappa3) Z2_base (vehicle-km cut; 0 = "no more than today").
    """
    xb, fb = MT.baseline_schedule(inst)
    m = MT.evaluate(inst, xb, fb)
    scale = {"G1": m["Z1"], "G2": m["Z3"], "G3": m["Z2"], "G4": m["equity_excess_min"]}
    scale = {k: (v if v > 1e-9 else 1.0) for k, v in scale.items()}
    return Targets(T1=(1 - kappa1) * m["Z1"], T2=0.0, T3=(1 - kappa3) * m["Z2"], scale=scale, baseline=m)


def targets_from_config(inst: MD.Instance, cfg: dict | None = None) -> Targets:
    """Targets using kappa1 / kappa3 from config/gp_scenarios.json (single source for every stage)."""
    cfg = cfg or load_config()
    return make_targets(inst, cfg["kappa1"], cfg.get("kappa3", 0.0))


@dataclass
class GoalModel:
    b: MD.Built
    dev: dict            # goal -> unwanted-deviation expression
    targets: Targets


def build_goal_model(inst: MD.Instance, tg: Targets) -> GoalModel:
    """Stage 3 core (hard constraints) + goal constraints with deviation variables."""
    b = MD.build_core(inst, name="gp")
    pr = b.prob
    n1, p1 = pr.add_variable("n1", 0, None), pr.add_variable("p1", 0, None)
    n2, p2 = pr.add_variable("n2", 0, None), pr.add_variable("p2", 0, None)
    n3, p3 = pr.add_variable("n3", 0, None), pr.add_variable("p3", 0, None)
    pr += b.Z["Z1"] + n1 - p1 == tg.T1, "G1_waiting"
    pr += b.Z["Z3"] + n2 - p2 == tg.T2, "G2_unserved"
    pr += b.Z["Z2"] + n3 - p3 == tg.T3, "G3_vehkm"
    p4 = {}
    for i, t in inst.active_pairs():
        p4[i, t] = pr.add_variable(f"p4_{i}_{t}", 0, None)
        pr += b.hw[i, t] - inst.cfg.equity_cap_min[t] <= p4[i, t], f"G4_equity_{i}_{t}"
    dev = {"G1": p1, "G2": p2, "G3": p3, "G4": pulp.lpSum(p4.values())}
    return GoalModel(b, dev, tg)


def deviations_of(inst: MD.Instance, tg: Targets, m: dict) -> dict:
    """True unwanted deviations of an evaluated schedule (metrics dict from metrics.evaluate)."""
    return {"G1": max(0.0, m["Z1"] - tg.T1), "G2": max(0.0, m["Z3"] - tg.T2),
            "G3": max(0.0, m["Z2"] - tg.T3), "G4": m["equity_excess_min"]}


def _lock(gm: GoalModel, expr, value: float, name: str):
    gm.b.prob += expr <= value + LOCK_ABS + LOCK_REL * abs(value), name


def _solve(gm: GoalModel, objective, time_limit: float):
    gm.b.prob.setObjective(objective)
    return MD.solve(gm.b, time_limit=time_limit, gap_rel=GAP_REL)


def _tidy(gm: GoalModel, time_limit: float):
    """Final solve: fewest buses with every goal result already locked."""
    return _solve(gm, gm.b.Z["fleet"], time_limit)


# ======================================================================
# Methods
# ======================================================================


def solve_preemptive(inst, tg: Targets, levels: list, time_limit: float = 60.0) -> dict:
    """Lexicographic GP. levels = [["G2"], ["G1"], ...]. Returns schedule, per-level table, timing, status."""
    gm = build_goal_model(inst, tg)
    t0, rows, statuses = time.perf_counter(), [], []
    for k, lv in enumerate(levels, start=1):
        expr = pulp.lpSum(gm.dev[g] / tg.scale[g] for g in lv) if len(lv) > 1 else gm.dev[lv[0]]
        res = _solve(gm, expr, time_limit)
        statuses.append(res["status"])
        val = float(res["objective"])
        rows.append(dict(level=k, goals="+".join(lv), achieved_dev=val))
        _lock(gm, expr, val, f"lock_level_{k}")
    res = _tidy(gm, time_limit)
    statuses.append(res["status"])
    return dict(gm=gm, result=res, levels=rows, wall_s=time.perf_counter() - t0,
                status="Optimal" if all(s == "Optimal" for s in statuses) else ",".join(statuses))


def solve_weighted(inst, tg: Targets, weights: dict, time_limit: float = 60.0) -> dict:
    """Weighted GP: min sum_i w_i dev_i / scale_i (normalised by the baseline values)."""
    gm = build_goal_model(inst, tg)
    t0 = time.perf_counter()
    expr = pulp.lpSum(w * gm.dev[g] / tg.scale[g] for g, w in weights.items() if w)
    res = _solve(gm, expr, time_limit)
    _lock(gm, expr, float(res["objective"]), "lock_weighted")
    res2 = _tidy(gm, time_limit)
    return dict(gm=gm, result=res2, levels=[dict(level=1, goals="weighted", achieved_dev=float(res["objective"]))],
                wall_s=time.perf_counter() - t0,
                status="Optimal" if res["status"] == res2["status"] == "Optimal" else f"{res['status']},{res2['status']}")


def solve_chebyshev(inst, tg: Targets, weights: dict, time_limit: float = 60.0) -> dict:
    """Min-max GP: min lambda s.t. w_i dev_i / scale_i <= lambda; then the normalised sum, then buses."""
    gm = build_goal_model(inst, tg)
    t0 = time.perf_counter()
    lam = gm.b.prob.add_variable("lambda", 0, None)
    for g, w in weights.items():
        if w:
            gm.b.prob += w * gm.dev[g] / tg.scale[g] <= lam, f"cheb_{g}"
    r1 = _solve(gm, lam, time_limit)
    _lock(gm, lam, float(r1["objective"]), "lock_lambda")
    s = pulp.lpSum(w * gm.dev[g] / tg.scale[g] for g, w in weights.items() if w)
    r2 = _solve(gm, s, time_limit)
    _lock(gm, s, float(r2["objective"]), "lock_sum")
    r3 = _tidy(gm, time_limit)
    ok = all(r["status"] == "Optimal" for r in (r1, r2, r3))
    return dict(gm=gm, result=r3, levels=[dict(level=1, goals="max normalised dev", achieved_dev=float(r1["objective"])),
                                          dict(level=2, goals="sum normalised dev", achieved_dev=float(r2["objective"]))],
                wall_s=time.perf_counter() - t0, status="Optimal" if ok else "check")


def run_scenario(inst, tg: Targets, sc: dict, time_limit: float = 60.0) -> dict:
    if sc["type"] == "preemptive":
        return solve_preemptive(inst, tg, sc["levels"], time_limit)
    if sc["type"] == "weighted":
        return solve_weighted(inst, tg, sc["weights"], time_limit)
    return solve_chebyshev(inst, tg, sc["weights"], time_limit)


# ======================================================================
# Ideal / nadir
# ======================================================================


def payoff_table(inst, tie_eps: float = 1e-4, time_limit: float = 60.0):
    """Minimise each objective alone (with a tiny normalised tie-break on the others, so the point is efficient).

    Returns (rows, ideal, nadir): ideal = best value of each objective; nadir = its worst value over the
    other single-objective optima (payoff-table estimate).
    """
    tg = make_targets(inst)
    names = {"Z1": "G1", "Z3": "G2", "Z2": "G3", "equity_excess_min": "G4"}
    rows = []
    for k in names:
        b = MD.build_core(inst, name=f"ideal_{k}")
        others = pulp.lpSum(b.Z[o] / tg.scale[names[o]] for o in names if o != k)
        b.prob.setObjective(b.Z[k] + tie_eps * tg.scale[names[k]] * others)
        res = MD.solve(b, time_limit=time_limit, gap_rel=GAP_REL)
        x, f = MD.schedule_to_arrays(inst, res["schedule"])
        m = MT.evaluate(inst, x, f)
        rows.append(dict(minimised=k, **{o: m[o] for o in names}, fleet_used=m["fleet_used"]))
    ideal = {k: rows[i][k] for i, k in enumerate(names)}
    nadir = {k: max(r[k] for r in rows) for k in names}
    return rows, ideal, nadir
