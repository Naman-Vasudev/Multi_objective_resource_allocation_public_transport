"""Corrected multi-objective bus frequency model (MILP, PuLP + HiGHS). Math: docs/MODEL.md.

Units: f [dep/h], headway h [min], tau [h], d_cycle [km], H [h], D [pax/h], C [pax/bus], x [buses].
Demand is SYNTHETIC (Stage 2).

Decision variables, for every ACTIVE route-period (r, t):
    y[r,t,k] in {0,1}   route r runs headway k in period t,  sum_k y = 1
    f_rt = sum_k (60 / h_k) y[r,t,k]                         [dep/h]  (linear in y)
    x[r,t]  integer >= 0                                     [buses]
    o[r,t]  >= 0                                             [pax/h] demand above capacity
Inactive (r, t) have no variables (C6: they are fixed to zero).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
import pulp

from src import calibration as CAL
from src import demand as DM
from src import params as P


@dataclass
class Instance:
    """All data the MILP needs, indexed by route position i and period name t."""
    route_no: list
    periods: list
    tau: np.ndarray          # [h] cycle time per route
    d_cycle: np.ndarray      # [km] per bus cycle (= per departure from each end)
    x0: np.ndarray           # [buses] published allocation
    f0: np.ndarray           # [dep/h] published mid frequency
    f_min: np.ndarray        # [dep/h]
    f_max: np.ndarray        # [dep/h]
    h_lo: np.ndarray         # [min] shortest published headway
    h_hi: np.ndarray         # [min] longest published headway
    active: dict             # (i, t) -> bool
    H: dict                  # (i, t) -> hours counted in Z2, Z3 [h]
    M: dict                  # (i, t) -> modal demand [pax/h]
    D_alpha: dict            # (i, t) -> upper alpha-cut demand [pax/h]
    menu: dict               # (i, t) -> list of allowed headways [min]
    x_lb: np.ndarray         # [buses] practicality lower bound (C5)
    x_ub: np.ndarray         # [buses] practicality upper bound (C5)
    cfg: P.ModelConfig

    @property
    def n(self) -> int:
        return len(self.route_no)

    def active_pairs(self):
        return [(i, t) for i in range(self.n) for t in self.periods if self.active[i, t]]


# ======================================================================
# Building the instance
# ======================================================================


def route_menu(h_lo: float, h_hi: float, cfg: P.ModelConfig, period: str) -> list:
    """Allowed headways [min] for one route-period under C4 (and C5 equity if hard).

    The route's own published headways are always added to K, so the published schedule is representable.
    "relaxed": the shortest allowed headway becomes the 2nd menu level below h_lo (= two levels above f_max).
    """
    base = sorted(set(cfg.menu_min))
    menu = sorted(set(base) | {h_lo, h_hi})
    lo = h_lo
    if cfg.fmax_mode == "relaxed":
        shorter = [h for h in base if h < h_lo]
        if shorter:
            lo = shorter[-2] if len(shorter) >= 2 else shorter[-1]
    elif cfg.fmax_mode != "published":
        raise ValueError(f"fmax_mode must be 'published' or 'relaxed', got {cfg.fmax_mode!r}")
    allowed = [h for h in menu if lo - 1e-9 <= h <= h_hi + 1e-9]
    if cfg.equity_mode == "hard":
        allowed = [h for h in allowed if h <= cfg.equity_cap_min[period] + 1e-9]
    return allowed


def practicality_bounds(x0: np.ndarray, cfg: P.ModelConfig):
    """C5: integer bounds [ceil(x0 - dev), floor(x0 + dev)], dev = max(min, min(abs, rel * x0))."""
    dev = np.maximum(cfg.pract_min, np.minimum(cfg.pract_abs, cfg.pract_rel * x0))
    lb = np.maximum(0, np.ceil(x0 - dev - 1e-9)).astype(int)
    ub = np.floor(x0 + dev + 1e-9).astype(int)
    return lb, ub


def build_instance(routes: pd.DataFrame, dem: pd.DataFrame, cfg: P.ModelConfig | None = None) -> Instance:
    """routes: Stage 1 table; dem: Stage 2 demand_rt (route_no, period, active, H_t, overlap_h, L, M, U)."""
    cfg = cfg or P.ModelConfig()
    periods = list(P.PERIODS)
    tau = CAL.cycle_time_h(routes.d_r_km, routes.is_loop, cfg.scenario, cfg.speed_kmh, cfg.layover_frac)
    d_cycle = CAL.cycle_distance_km(routes.d_r_km, routes.is_loop, cfg.scenario)
    x0 = routes.x_base.to_numpy().astype(int)
    lb, ub = practicality_bounds(x0, cfg)
    idx = {r: i for i, r in enumerate(routes.route_no)}
    active, H, M, Da, menu = {}, {}, {}, {}, {}
    for row in dem.itertuples():
        i, t = idx[row.route_no], row.period
        active[i, t] = bool(row.active)
        if cfg.hours_mode == "overlap":
            H[i, t] = float(row.overlap_h)
        elif cfg.hours_mode == "full":
            H[i, t] = float(row.H_t) if row.active else 0.0
        else:
            raise ValueError(f"hours_mode must be 'overlap' or 'full', got {cfg.hours_mode!r}")
        M[i, t] = float(row.M)
        Da[i, t] = float(DM.alpha_cut_upper(row.U, row.M, cfg.alpha))
    for i in range(len(routes)):
        for t in periods:
            menu[i, t] = route_menu(routes.headway_min_lo.iloc[i], routes.headway_min_hi.iloc[i], cfg, t) \
                if active[i, t] else []
    return Instance(list(routes.route_no), periods, np.asarray(tau), np.asarray(d_cycle), x0,
                    routes.f_mid.to_numpy(), routes.f_min.to_numpy(), routes.f_max.to_numpy(),
                    routes.headway_min_lo.to_numpy(), routes.headway_min_hi.to_numpy(),
                    active, H, M, Da, menu, lb, ub, cfg)


def presolve_report(inst: Instance) -> list[str]:
    """Plain-language list of reasons the MILP must be infeasible (empty if none found)."""
    msgs = []
    need_lb = {t: 0 for t in inst.periods}
    for i, t in inst.active_pairs():
        rn = inst.route_no[i]
        if not inst.menu[i, t]:
            msgs.append(f"route {rn} {t}: no allowed headway (published range {inst.h_lo[i]:g}-{inst.h_hi[i]:g} min, "
                        f"equity cap {inst.cfg.equity_cap_min[t]} min, mode {inst.cfg.equity_mode})")
            continue
        f_low = min(60.0 / h for h in inst.menu[i, t])
        need = max(inst.x_lb[i], math.ceil(f_low * inst.tau[i] - 1e-9))
        if need > inst.x_ub[i]:
            msgs.append(f"route {rn} {t}: needs {need} buses at its lowest allowed frequency "
                        f"({f_low:.3f} dep/h x tau {inst.tau[i]:.3f} h) but C5 allows at most {inst.x_ub[i]} "
                        f"(x0 = {inst.x0[i]})")
        need_lb[t] += need
    for t, n in need_lb.items():
        if n > inst.cfg.B_eff:
            msgs.append(f"{t}: minimum buses {n} exceed B_eff = {inst.cfg.B_eff}")
    return msgs


# ======================================================================
# MILP
# ======================================================================


@dataclass
class Built:
    prob: pulp.LpProblem
    y: dict
    x: dict
    o: dict
    Z: dict          # name -> pulp affine expression
    inst: Instance
    f: dict = None   # (i, t) -> frequency expression [dep/h]
    hw: dict = None  # (i, t) -> headway expression [min]


def build_core(inst: Instance, name: str = "ctu") -> Built:
    """Variables, HARD constraints C1-C6 and the objective expressions Z1, Z2, Z3, fleet, equity_excess_min.

    No objective is set; build_model (Stage 3) and src/goals.py (Stage 4) add their own.
    equity_excess_min = sum_rtk max(0, h_k - Hcap_t) y_rtk [min] (exact, because y is binary).
    """
    cfg = inst.cfg
    prob = pulp.LpProblem(name, pulp.LpMinimize)
    y, x, o = {}, {}, {}
    pairs = inst.active_pairs()
    for i, t in pairs:
        for h in inst.menu[i, t]:
            y[i, t, h] = prob.add_variable(f"y_{i}_{t}_{h:g}".replace(".", "p"), 0, 1, cat="Binary")
        x[i, t] = prob.add_variable(f"x_{i}_{t}", int(inst.x_lb[i]), int(inst.x_ub[i]), cat="Integer")
        o[i, t] = prob.add_variable(f"o_{i}_{t}", 0, None, cat="Continuous")

    f = {(i, t): pulp.lpSum((60.0 / h) * y[i, t, h] for h in inst.menu[i, t]) for i, t in pairs}
    hw = {(i, t): pulp.lpSum(h * y[i, t, h] for h in inst.menu[i, t]) for i, t in pairs}

    for i, t in pairs:
        prob += pulp.lpSum(y[i, t, h] for h in inst.menu[i, t]) == 1, f"one_headway_{i}_{t}"
        prob += inst.tau[i] * f[i, t] <= x[i, t], f"C2_freq_fleet_{i}_{t}"
        prob += o[i, t] >= inst.D_alpha[i, t] - cfg.C * f[i, t], f"C3_overflow_{i}_{t}"
    for t in inst.periods:
        prob += pulp.lpSum(x[i, tt] for i, tt in pairs if tt == t) <= cfg.B_eff, f"C1_fleet_{t}"

    Z = {
        "Z1": pulp.lpSum(inst.M[i, t] * pulp.lpSum((h / 2.0) * y[i, t, h] for h in inst.menu[i, t]) for i, t in pairs),
        "Z2": pulp.lpSum(inst.d_cycle[i] * inst.H[i, t] * f[i, t] for i, t in pairs),
        "Z3": pulp.lpSum(o[i, t] * inst.H[i, t] for i, t in pairs),
        "fleet": pulp.lpSum(x.values()),
        "equity_excess_min": pulp.lpSum(max(0.0, h - cfg.equity_cap_min[t]) * y[i, t, h]
                                        for i, t in pairs for h in inst.menu[i, t]),
    }
    return Built(prob, y, x, o, Z, inst, f, hw)


def build_model(inst: Instance, weights: dict | None = None, name: str = "ctu") -> Built:
    """Build the MILP. weights: {"Z1": w1, "Z2": w2, "Z3": w3, "fleet": w4}; objective = sum w * Z (+ equity penalty)."""
    weights = weights or {"Z3": 1.0}
    b = build_core(inst, name)
    obj = pulp.lpSum(w * b.Z[k] for k, w in weights.items() if w)
    if inst.cfg.equity_mode == "soft":
        obj = obj + inst.cfg.equity_weight * b.Z["equity_excess_min"]
    b.prob += obj
    return b


def _solver(name: str, time_limit: float, msg: bool, gap_rel):
    if name == "highs":
        return pulp.HiGHS(msg=msg, timeLimit=time_limit, gapRel=gap_rel)
    if name == "cbc":  # PuLP 4 no longer bundles CBC; needs a cbc executable on PATH
        return pulp.COIN_CMD(msg=msg, timeLimit=time_limit, gapRel=gap_rel)
    raise ValueError(f"solver must be 'highs' or 'cbc', got {name!r}")


def solve(b: Built, time_limit: float = 60.0, msg: bool = False, solver: str = "highs",
          gap_rel: float | None = None) -> dict:
    """Solve the current objective (HiGHS default). gap_rel: MIP relative gap (solver default 1e-4 if None).

    Returns status, wall time, objective value, Z values and the schedule.
    """
    t0 = time.perf_counter()
    status = b.prob.solve(_solver(solver, time_limit, msg, gap_rel))
    wall = time.perf_counter() - t0
    st = status.status.name     # PuLP 4: solve() returns LpSolveStats
    if st != "Optimal":
        raise RuntimeError(f"solver status {st} after {wall:.1f}s")
    inst = b.inst
    rows = []
    for i, t in inst.active_pairs():
        hsel = [h for h in inst.menu[i, t] if b.y[i, t, h].value() > 0.5]
        assert len(hsel) == 1, (i, t, hsel)
        h = hsel[0]
        rows.append(dict(route_no=inst.route_no[i], period=t, headway_min=h, f=60.0 / h,
                         x=int(round(b.x[i, t].value())), o=float(b.o[i, t].value())))
    sched = pd.DataFrame(rows)
    return dict(status=st, wall_s=wall, objective=pulp.value(b.prob.objective), schedule=sched,
                Z={k: float(pulp.value(v)) for k, v in b.Z.items()})


def schedule_to_arrays(inst: Instance, sched: pd.DataFrame):
    """Schedule table -> dicts x[(i,t)], f[(i,t)] for metrics.evaluate."""
    idx = {r: i for i, r in enumerate(inst.route_no)}
    x = {(idx[r.route_no], r.period): r.x for r in sched.itertuples()}
    f = {(idx[r.route_no], r.period): r.f for r in sched.itertuples()}
    return x, f
