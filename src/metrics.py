"""Evaluate ANY schedule (x_rt, f_rt) on the model's objectives and service metrics, and check constraints.

Schedule format: dicts keyed by (route index i, period t) for ACTIVE pairs only.
    x[(i,t)] buses [buses]     f[(i,t)] frequency [dep/h] (need not be a menu value; baseline uses f_mid)
Demand is SYNTHETIC.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.model import Instance


def gini(values) -> float:
    """Gini coefficient of non-negative values (0 = all equal, -> 1 = concentrated)."""
    v = np.sort(np.asarray(values, dtype=float))
    if len(v) == 0 or v.sum() == 0:
        return 0.0
    n = len(v)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(v) / (n * v.sum()))


def evaluate(inst: Instance, x: dict, f: dict) -> dict:
    """Objectives and metrics for a schedule.

    Z1  sum M_rt * h_rt / 2                [pax*min/h]  (demand-weighted wait rate, modal demand)
    Z1_daily = sum M_rt * h_rt / 2 * H_rt  [pax*min/day]
    Z2  sum d_cycle_r * H_rt * f_rt        [veh-km/day]
    Z3  sum max(0, D_alpha - C f) * H_rt   [pax/day]
    fleet_used = max_t sum_r x_rt          [buses]
    wait: demand-weighted mean and max of h/2 [min]; EWT = (h/2)(1 + CV^2) - h/2 = (h/2) CV^2 [min]
    load factor LF_rt = M_rt / (C f_rt)    [-]
    equity: equity_excess_min = sum max(0, h - Hcap_t) [min], n_over_cap = pairs above the cap
    """
    cfg = inst.cfg
    pairs = inst.active_pairs()
    M = np.array([inst.M[p] for p in pairs])
    Da = np.array([inst.D_alpha[p] for p in pairs])
    H = np.array([inst.H[p] for p in pairs])
    fr = np.array([f[p] for p in pairs], dtype=float)
    hw = 60.0 / fr
    dc = np.array([inst.d_cycle[i] for i, _ in pairs])
    wait = hw / 2.0
    lf = M / (cfg.C * fr)
    over = np.maximum(0.0, Da - cfg.C * fr)
    fleet_t = {t: int(sum(x[p] for p in pairs if p[1] == t)) for t in inst.periods}
    cap = np.array([cfg.equity_cap_min[t] for _, t in pairs])
    excess = np.maximum(0.0, hw - cap)
    w = M / M.sum()
    return dict(
        Z1=float((M * wait).sum()),
        Z1_daily=float((M * wait * H).sum()),
        Z2=float((dc * H * fr).sum()),
        Z3=float((over * H).sum()),
        fleet_used=max(fleet_t.values()),
        **{f"fleet_{t}": n for t, n in fleet_t.items()},
        mean_wait_min=float((w * wait).sum()),
        max_wait_min=float(wait.max()),
        ewt_min=float((w * wait * cfg.headway_cv ** 2).sum()),
        mean_LF=float(lf.mean()),
        n_LF_gt_1=int((lf > 1).sum()),
        gini_LF=gini(lf),
        equity_excess_min=float(excess.sum()),
        n_over_cap=int((excess > 1e-9).sum()),
        n_pairs=len(pairs),
    )


def check_schedule(inst: Instance, x: dict, f: dict, tol: float = 1e-9) -> pd.DataFrame:
    """Every constraint violation of a schedule, with the amount. Empty frame = feasible.

    Columns: constraint, route_no, period, lhs, rhs, excess (lhs - rhs > 0 means violated), unit.
    """
    cfg = inst.cfg
    out = []
    pairs = inst.active_pairs()
    for t in inst.periods:
        s = sum(x[p] for p in pairs if p[1] == t)
        if s > cfg.B_eff + tol:
            out.append(("C1 fleet", "ALL", t, s, cfg.B_eff, s - cfg.B_eff, "buses"))
    for i, t in pairs:
        rn = inst.route_no[i]
        need = f[i, t] * inst.tau[i]
        if need > x[i, t] + tol:
            out.append(("C2 f*tau <= x", rn, t, need, x[i, t], need - x[i, t], "buses"))
        if f[i, t] < inst.f_min[i] - tol:
            out.append(("C4 f >= f_min", rn, t, inst.f_min[i], f[i, t], inst.f_min[i] - f[i, t], "dep/h"))
        if x[i, t] < inst.x_lb[i] or x[i, t] > inst.x_ub[i]:
            bound = inst.x_lb[i] if x[i, t] < inst.x_lb[i] else inst.x_ub[i]
            out.append(("C5 practicality", rn, t, x[i, t], bound, abs(x[i, t] - bound), "buses"))
        cap = cfg.equity_cap_min[t]
        if cfg.equity_mode != "off" and 60.0 / f[i, t] > cap + tol:
            out.append((f"C5 equity ({cfg.equity_mode})", rn, t, 60.0 / f[i, t], cap, 60.0 / f[i, t] - cap, "min"))
    return pd.DataFrame(out, columns=["constraint", "route_no", "period", "lhs", "rhs", "excess", "unit"])


def baseline_schedule(inst: Instance):
    """Published schedule: x0_r buses and f0_r = mid of published frequency range in every active period."""
    pairs = inst.active_pairs()
    return {p: int(inst.x0[p[0]]) for p in pairs}, {p: float(inst.f0[p[0]]) for p in pairs}
