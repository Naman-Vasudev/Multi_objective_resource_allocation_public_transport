"""Monte Carlo stress test of schedules against random demand. SYNTHETIC DEMAND, ILLUSTRATIVE.

Demand scenario n, active pair g:
    D[n, g] = Tri(L_g, M_g, U_g) * shock_n,   shock_n ~ Normal(1, sigma_shock)   [pax/h]
The shock is common to every pair in a scenario (correlated days: weather, events). All schedules are evaluated
on the SAME draws (common random numbers), so differences between schedules are not sampling noise.

Waiting: realised headways ~ Gamma(mean h, CV_h). For random passenger arrivals the expected wait is
    E[W] = (h/2)(1 + CV_h^2)        EWT = E[W] - h/2 = (h/2) CV_h^2        [min]
(tested against a direct gamma-headway simulation in tests/test_simulate.py).

Units: wait [pax*min/day], overflow [pax/day], vehicle-km [veh-km/day], LF [-].
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from src import goals as G
from src import metrics as MT
from src import model as MD
from src import params as P
from src import pareto as PA


# ======================================================================
# Demand draws
# ======================================================================


def tfn_arrays(inst: MD.Instance, dem: pd.DataFrame, widen: float = 1.0):
    """(L, M, U) [pax/h] per active pair in inst.active_pairs() order; widen > 1 stretches both spreads around M."""
    d = dem.set_index(["route_no", "period"])
    rows = [d.loc[(inst.route_no[i], t)] for i, t in inst.active_pairs()]
    M = np.array([r.M for r in rows], float)
    L = np.array([r.L for r in rows], float)
    U = np.array([r.U for r in rows], float)
    L = np.maximum(0.0, M - widen * (M - L))
    U = M + widen * (U - M)
    return L, M, U


def draw_demand(L, M, U, n: int = P.SIM_N, seed: int = P.SIM_SEED, shock_sd: float = P.SIM_SHOCK_SD) -> np.ndarray:
    """(n, G) demand matrix [pax/h]: triangular per pair times a common Normal(1, shock_sd) factor per scenario."""
    rng = np.random.default_rng(seed)
    tri = rng.triangular(np.broadcast_to(L, (n, len(M))), np.broadcast_to(M, (n, len(M))),
                         np.broadcast_to(np.maximum(U, M + 1e-12), (n, len(M))))
    shock = rng.normal(1.0, shock_sd, size=(n, 1))
    return np.maximum(0.0, tri * shock)


# ======================================================================
# Schedules
# ======================================================================


@dataclass
class Schedule:
    name: str
    f: np.ndarray        # [dep/h] per active pair
    x: np.ndarray        # [buses] per active pair
    alpha: float | None
    source: str


def baseline(inst) -> Schedule:
    xb, fb = MT.baseline_schedule(inst)
    pairs = inst.active_pairs()
    return Schedule("Baseline", np.array([fb[p] for p in pairs]), np.array([xb[p] for p in pairs]), None,
                    "published timetable (x0, mid frequency)")


PEAK_BASELINE = "Baseline (peak f_max)"


def baseline_peak(inst) -> Schedule:
    """Fairer published baseline (examiner fix 1): x0 buses, f_max in AM/PM peaks, f_min at midday.

    This is the Stage 2 fit rule. It may break C2 (f*tau <= x) on routes whose published buses cannot run f_max;
    it is evaluated as published, not repaired.
    """
    pairs = inst.active_pairs()
    f = np.array([inst.f_max[i] if t in ("AM", "PM") else inst.f_min[i] for i, t in pairs])
    return Schedule(PEAK_BASELINE, f, np.array([int(inst.x0[i]) for i, _ in pairs]), None,
                    "published timetable (x0, f_max in peaks, f_min midday)")


def from_gp(inst, name: str, sc: dict, kappa1: float, alpha: float, kappa3: float = 0.0) -> tuple[Schedule, str]:
    tg = G.make_targets(inst, kappa1, kappa3)
    out = G.run_scenario(inst, tg, sc)
    x, f = MD.schedule_to_arrays(inst, out["result"]["schedule"])
    pairs = inst.active_pairs()
    return Schedule(name, np.array([f[p] for p in pairs]), np.array([x[p] for p in pairs]), alpha,
                    f"goal programming ({sc['type']})"), out["status"]


def from_headways(inst, name: str, hw: list, alpha: float, source: str) -> Schedule:
    x, f, _ = PA.evaluate_headways(inst, hw)
    pairs = inst.active_pairs()
    return Schedule(name, np.array([f[p] for p in pairs]), np.array([x[p] for p in pairs]), alpha, source)


def knee_point(eps_csv, nsga_csv, payoff_csv) -> tuple[list, dict]:
    """Knee of the combined front = point closest (Euclidean) to the ideal in normalised objective space."""
    e, n, pay = pd.read_csv(eps_csv), pd.read_csv(nsga_csv), pd.read_csv(payoff_csv)
    allp = pd.concat([e[["Z1", "Z2", "Z3", "headways"]].assign(src="AUGMECON"),
                      n[["Z1", "Z2", "Z3", "headways"]].assign(src="NSGA-II")], ignore_index=True)
    allp = allp[PA.nondominated(allp[["Z1", "Z2", "Z3"]].to_numpy())].reset_index(drop=True)
    ideal = {o: float(pay.loc[pay.minimised == o, o].iloc[0]) for o in PA.OBJ}
    nadir = {o: float(pay[o].max()) for o in PA.OBJ}
    Zn = PA.normalise(allp[["Z1", "Z2", "Z3"]].to_numpy(), ideal, nadir)
    k = int(np.argmin(np.sqrt((Zn ** 2).sum(1))))
    row = allp.iloc[k]
    return [float(v) for v in row.headways.split(";")], dict(Z1=row.Z1, Z2=row.Z2, Z3=row.Z3, src=row.src,
                                                             dist_to_ideal=float(np.sqrt((Zn[k] ** 2).sum())))


# ======================================================================
# Evaluation
# ======================================================================


def route_groups(inst):
    """Start index of each route's block of pairs (active_pairs is ordered by route) and the route labels."""
    pairs = inst.active_pairs()
    starts, labels = [], []
    for g, (i, _) in enumerate(pairs):
        if g == 0 or pairs[g - 1][0] != i:
            starts.append(g)
            labels.append(inst.route_no[i])
    return np.array(starts), labels


def _gini_rows(V: np.ndarray) -> np.ndarray:
    S = np.sort(V, axis=1)
    n = S.shape[1]
    w = 2 * np.arange(1, n + 1) - n - 1
    tot = S.sum(1)
    return np.where(tot > 0, (S * w).sum(1) / (n * np.where(tot > 0, tot, 1)), 0.0)


def simulate(inst: MD.Instance, s: Schedule, D: np.ndarray, cv: float = P.SIM_HEADWAY_CV, C: float | None = None):
    """Per-scenario metrics (dict of arrays, length N) and per-route load-factor table for one schedule."""
    C = inst.cfg.C if C is None else C
    pairs = inst.active_pairs()
    H = np.array([inst.H[p] for p in pairs])
    dc = np.array([inst.d_cycle[i] for i, _ in pairs])
    h = 60.0 / s.f
    cap = C * s.f
    pax = D * H                                   # passengers per pair-period [pax]
    demand = pax.sum(1)
    wait = (pax * (h / 2.0) * (1 + cv ** 2)).sum(1)
    ewt = (pax * (h / 2.0) * cv ** 2).sum(1)
    over = (np.maximum(0.0, D - cap) * H).sum(1)
    LF = D / cap
    starts, labels = route_groups(inst)
    rLF = np.maximum.reduceat(LF, starts, axis=1)  # peak (max over periods) load factor per route
    caps = np.array([inst.cfg.equity_cap_min[t] for _, t in pairs])
    fleet = max(int(s.x[[g for g, (_, t) in enumerate(pairs) if t == tt]].sum()) for tt in inst.periods)
    per = dict(
        total_wait_pax_min=wait,
        mean_wait_min=wait / demand,
        ewt_min=ewt / demand,
        overflow_pax=over,
        overflow_share=over / demand,
        demand_pax=demand,
        vehicle_km=np.full(len(D), float((dc * H * s.f).sum())),
        fleet_used=np.full(len(D), float(fleet)),
        mean_LF=LF.mean(1),
        n_routes_LF_gt_1=(rLF > 1).sum(1).astype(float),
        gini_LF=_gini_rows(LF),
        equity_excess_min=np.full(len(D), float(np.maximum(0.0, h - caps).sum())),
    )
    route_tab = pd.DataFrame({"route_no": labels, "mean_peak_LF": rLF.mean(0),
                              "p95_peak_LF": np.percentile(rLF, 95, axis=0),
                              "prob_LF_gt_1": (rLF > 1).mean(0)})
    return per, route_tab


def summarise(name: str, per: dict, threshold: float = P.SIM_OVERFLOW_THRESHOLD) -> pd.DataFrame:
    rows = [dict(schedule=name, metric=k, mean=float(v.mean()), sd=float(v.std(ddof=1)),
                 p5=float(np.percentile(v, 5)), p95=float(np.percentile(v, 95))) for k, v in per.items()]
    pr = float((per["overflow_share"] > threshold).mean())
    rows.append(dict(schedule=name, metric=f"P(overflow > {threshold:.0%} of demand)", mean=pr, sd=float("nan"),
                     p5=float("nan"), p95=float("nan")))
    return pd.DataFrame(rows)
