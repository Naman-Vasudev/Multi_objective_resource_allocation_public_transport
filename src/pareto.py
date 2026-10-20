"""Pareto fronts for (Z1, Z2, Z3): exact AUGMECON epsilon-constraint (MILP) and NSGA-II (DEAP), plus front metrics.

All three objectives are minimised. Units: Z1 [pax*min/h], Z2 [veh-km/day], Z3 [pax/day]. Demand is SYNTHETIC.

References (see docs/LITERATURE.md): AUGMECON - Mavrotas (2009); AUGMECON2 - Mavrotas & Florios;
NSGA-II - Deb et al. (2002); hypervolume and coverage C - Zitzler & Thiele (1999);
indicator surveys - Riquelme et al. (2015), Audet et al.
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
import pulp

from src import metrics as MT
from src import model as MD

OBJ = ("Z1", "Z2", "Z3")
GAP_REL = 1e-6


# ======================================================================
# Shared helpers
# ======================================================================


def minimal_x(inst: MD.Instance, f: dict) -> dict:
    """Fewest buses that run frequency f: x = max(C5 lower bound, ceil(f * tau)). Buses are not in Z1-Z3."""
    return {p: max(int(inst.x_lb[p[0]]), math.ceil(f[p] * inst.tau[p[0]] - 1e-9)) for p in f}


def nondominated(points: np.ndarray, tol: float = 1e-9) -> np.ndarray:
    """Boolean mask of non-dominated rows (minimisation); exact duplicates keep their first occurrence."""
    P_ = np.asarray(points, float)
    n = len(P_)
    keep = np.ones(n, bool)
    for i in range(n):
        if not keep[i]:
            continue
        dom = np.all(P_ <= P_[i] + tol, axis=1) & np.any(P_ < P_[i] - tol, axis=1)
        if dom.any():
            keep[i] = False
            continue
        dup = np.all(np.abs(P_ - P_[i]) <= tol, axis=1)
        dup[: i + 1] = False
        keep[dup] = False
    return keep


def evaluate_headways(inst: MD.Instance, headways: list) -> tuple[dict, dict, dict]:
    """Headways in active_pairs() order -> (x, f, metrics) with minimal buses."""
    pairs = inst.active_pairs()
    f = {p: 60.0 / h for p, h in zip(pairs, headways)}
    x = minimal_x(inst, f)
    return x, f, MT.evaluate(inst, x, f)


# ======================================================================
# Payoff table (lexicographic) and AUGMECON
# ======================================================================


def _schedule_headways(inst, b: MD.Built) -> list:
    out = []
    for i, t in inst.active_pairs():
        out.append(next(h for h in inst.menu[i, t] if b.y[i, t, h].value() > 0.5))
    return out


def lexicographic_payoff(inst: MD.Instance, time_limit: float = 60.0, return_headways: bool = False):
    """Payoff table by lexicographic optimisation (Mavrotas 2009): for each k, min Z_k, lock it, then min the others
    in order. This avoids weakly efficient rows. ideal = diagonal, nadir = column max (payoff-table estimate).
    Each row is itself a Pareto-efficient schedule; with return_headways its headway vectors are returned too."""
    rows, hws = [], []
    for k in OBJ:
        b = MD.build_core(inst, name=f"lex_{k}")
        order = [k] + [o for o in OBJ if o != k]
        for j, o in enumerate(order):
            b.prob.setObjective(b.Z[o])
            res = MD.solve(b, time_limit=time_limit, gap_rel=GAP_REL)
            v = float(res["objective"])
            b.prob += b.Z[o] <= v + 1e-6 + 1e-7 * abs(v), f"lexlock_{o}"
        hw = _schedule_headways(inst, b)
        _, _, m = evaluate_headways(inst, hw)
        rows.append(dict(minimised=k, **{o: m[o] for o in OBJ}))
        hws.append(hw)
    pay = pd.DataFrame(rows)
    ideal = {o: float(pay.loc[pay.minimised == o, o].iloc[0]) for o in OBJ}
    nadir = {o: float(pay[o].max()) for o in OBJ}
    return (pay, ideal, nadir, hws) if return_headways else (pay, ideal, nadir)


def augmecon(inst: MD.Instance, ideal: dict, nadir: dict, n_grid: int = 10, eps: float = 1e-3,
             time_limit: float = 60.0, extra_headways: list | None = None) -> tuple[pd.DataFrame, pd.DataFrame, list]:
    """AUGMECON: min Z3/r3 - eps (s1/r1 + s2/r2) s.t. Z1 + s1 = e1, Z2 + s2 = e2, s >= 0, on an n x n grid.

    The objective is normalised by the ranges r so that the MIP gap (1e-6) is far below the augmentation term.
    Early exit (AUGMECON idea): for fixed e1, e2 runs from loose to tight; once infeasible, every tighter e2 is
    infeasible too and is recorded as 'skipped (infeasible)'.
    extra_headways: already-efficient schedules (the lexicographic payoff rows) added to the exact set.
    Returns (grid log, non-dominated points, list of headway vectors for those points).
    """
    r = {o: max(nadir[o] - ideal[o], 1e-9) for o in OBJ}
    e1s = np.linspace(nadir["Z1"], ideal["Z1"], n_grid)
    e2s = np.linspace(nadir["Z2"], ideal["Z2"], n_grid)
    log, pts, hws = [], [], []
    b = MD.build_core(inst, name="augmecon")
    s1, s2 = b.prob.add_variable("s1", 0, None), b.prob.add_variable("s2", 0, None)
    # epsilon right-hand sides are variables whose bounds are pinned to (e, e) per grid cell
    E1, E2 = b.prob.add_variable("E1", 0, None), b.prob.add_variable("E2", 0, None)
    b.prob += b.Z["Z1"] + s1 == E1, "eps_Z1"
    b.prob += b.Z["Z2"] + s2 == E2, "eps_Z2"
    b.prob.setObjective(b.Z["Z3"] / r["Z3"] - eps * (s1 / r["Z1"] + s2 / r["Z2"]))
    for a, e1 in enumerate(e1s):
        infeasible_from = None
        for c, e2 in enumerate(e2s):
            if infeasible_from is not None:
                log.append(dict(i=a, j=c, e1=e1, e2=e2, status="skipped (infeasible)", wall_s=0.0))
                continue
            # tiny relative slack on the corners for numerical safety
            v1, v2 = e1 + 1e-7 * abs(e1), e2 + 1e-7 * abs(e2)
            E1.bounds(v1, v1)
            E2.bounds(v2, v2)
            t0 = time.perf_counter()
            st = b.prob.solve(MD._solver("highs", time_limit, False, GAP_REL))
            wall = time.perf_counter() - t0
            status = st.status.name
            if status == "Optimal":
                hw = _schedule_headways(inst, b)
                _, _, m = evaluate_headways(inst, hw)
                pts.append([m[o] for o in OBJ])
                hws.append(hw)
                log.append(dict(i=a, j=c, e1=e1, e2=e2, status=status, wall_s=wall, **{o: m[o] for o in OBJ}))
            else:
                infeasible_from = c
                log.append(dict(i=a, j=c, e1=e1, e2=e2, status=status, wall_s=wall))
    grid = pd.DataFrame(log)
    for hw in extra_headways or []:
        _, _, m = evaluate_headways(inst, hw)
        pts.append([m[o] for o in OBJ])
        hws.append(hw)
    P_ = np.array(pts) if pts else np.zeros((0, 3))
    mask = nondominated(P_) if len(P_) else np.zeros(0, bool)
    front = pd.DataFrame(P_[mask], columns=list(OBJ))
    front_hw = [hws[k] for k in np.flatnonzero(mask)]
    return grid, front, front_hw


# ======================================================================
# NSGA-II (DEAP)
# ======================================================================


@dataclass
class Encoding:
    """Gene g = one active (route, period); allele = index into that pair's sorted headway menu (0 = shortest)."""
    pairs: list
    n_opt: np.ndarray        # options per gene
    h: np.ndarray            # [g, k] headway [min] (padded with the last option)
    xneed: np.ndarray        # [g, k] minimal buses
    ok: np.ndarray           # [g, k] xneed <= C5 upper bound
    z1: np.ndarray           # [g, k] contribution to Z1
    z2: np.ndarray
    z3: np.ndarray
    period: np.ndarray       # [g] period index
    B_eff: int
    scale: np.ndarray        # (s1, s2, s3) for the repair's marginal-benefit rule
    fix: np.ndarray = None   # [g, k] smallest k' >= k with ok (C5/C2 repair)
    nxt: np.ndarray = None   # [g, k] next longer headway that needs fewer buses (-1 if none)
    mcost: np.ndarray = None  # [g, k] normalised loss per bus released by moving k -> nxt (inf if none)


def make_encoding(inst: MD.Instance, scale: dict) -> Encoding:
    pairs = inst.active_pairs()
    K = max(len(inst.menu[p]) for p in pairs)
    G_ = len(pairs)
    h = np.zeros((G_, K)); xneed = np.zeros((G_, K), int); ok = np.zeros((G_, K), bool)
    z1 = np.zeros((G_, K)); z2 = np.zeros((G_, K)); z3 = np.zeros((G_, K))
    n_opt = np.zeros(G_, int)
    per = np.array([inst.periods.index(t) for _, t in pairs])
    C = inst.cfg.C
    for g, (i, t) in enumerate(pairs):
        menu = sorted(inst.menu[i, t])
        n_opt[g] = len(menu)
        menu = menu + [menu[-1]] * (K - len(menu))
        for k, hk in enumerate(menu):
            f = 60.0 / hk
            h[g, k] = hk
            xneed[g, k] = max(int(inst.x_lb[i]), math.ceil(f * inst.tau[i] - 1e-9))
            ok[g, k] = xneed[g, k] <= inst.x_ub[i]
            z1[g, k] = inst.M[i, t] * hk / 2.0
            z2[g, k] = inst.d_cycle[i] * inst.H[i, t] * f
            z3[g, k] = max(0.0, inst.D_alpha[i, t] - C * f) * inst.H[i, t]
    enc = Encoding(pairs, n_opt, h, xneed, ok, z1, z2, z3, per, inst.cfg.B_eff,
                   np.array([scale["Z1"], scale["Z2"], scale["Z3"]]))
    # static repair tables (they depend only on the gene and its current option)
    fix = np.zeros((G_, K), int); nxt = -np.ones((G_, K), int); mcost = np.full((G_, K), np.inf)
    for g in range(G_):
        for k in range(n_opt[g]):
            kk = k
            while kk < n_opt[g] - 1 and not ok[g, kk]:
                kk += 1
            fix[g, k] = kk
            for nk in range(k + 1, n_opt[g]):
                if xneed[g, nk] < xneed[g, k]:
                    d = ((z1[g, nk] - z1[g, k]) / enc.scale[0] + (z3[g, nk] - z3[g, k]) / enc.scale[2]
                         + (z2[g, nk] - z2[g, k]) / enc.scale[1])
                    nxt[g, k], mcost[g, k] = nk, d / (xneed[g, k] - xneed[g, nk])
                    break
    enc.fix, enc.nxt, enc.mcost = fix, nxt, mcost
    return enc


def repair(enc: Encoding, genome: list) -> np.ndarray:
    """Make a genome feasible for C5/C2 and C1 (in place semantics returned as array).

    1. Clip to the menu; if a pair's buses exceed its C5 upper bound, lengthen its headway until they fit.
    2. Fleet C1 per period: while buses > B_eff, lengthen the headway of the pair with the LOWEST marginal benefit,
       i.e. the smallest normalised loss (dZ1/s1 + dZ3/s3 - Z2 saving/s2) per bus released.
    """
    g_idx = np.arange(len(enc.n_opt))
    k = np.clip(np.asarray(genome, int), 0, enc.n_opt - 1)
    k = enc.fix[g_idx, k]                  # C5/C2: presolve guarantees the longest headway is feasible
    for t in np.unique(enc.period):
        gs = np.flatnonzero(enc.period == t)
        excess = int(enc.xneed[gs, k[gs]].sum()) - enc.B_eff
        while excess > 0:
            c = enc.mcost[gs, k[gs]]
            j = int(np.argmin(c))
            if not np.isfinite(c[j]):
                raise RuntimeError("repair failed: fleet limit cannot be met in this period")
            g = gs[j]
            nk = enc.nxt[g, k[g]]
            excess -= int(enc.xneed[g, k[g]] - enc.xneed[g, nk])
            k[g] = nk
    return k


def objectives(enc: Encoding, k: np.ndarray) -> tuple[float, float, float]:
    g = np.arange(len(k))
    return float(enc.z1[g, k].sum()), float(enc.z2[g, k].sum()), float(enc.z3[g, k].sum())


def headways_of(enc: Encoding, k) -> list:
    return [float(enc.h[g, kk]) for g, kk in enumerate(k)]


def nsga2(enc: Encoding, seed: int, pop_size: int = 200, n_gen: int = 300, cxpb: float = 0.9,
          mutpb_gene: float | None = None) -> dict:
    """NSGA-II with DEAP: uniform crossover (prob cxpb), per-gene reset mutation (prob 1/n_genes), Lamarckian repair."""
    from deap import base, creator, tools

    if not hasattr(creator, "FitMin3"):
        creator.create("FitMin3", base.Fitness, weights=(-1.0, -1.0, -1.0))
        creator.create("Ind3", list, fitness=creator.FitMin3)
    rng = random.Random(seed)
    n = len(enc.n_opt)
    pm = mutpb_gene if mutpb_gene is not None else 1.0 / n
    assert pop_size % 4 == 0, "selTournamentDCD needs a population size divisible by 4"
    n_eval = 0

    def new_ind():
        return creator.Ind3([rng.randrange(int(m)) for m in enc.n_opt])

    def evaluate(ind):
        nonlocal n_eval
        k = repair(enc, ind)
        ind[:] = [int(v) for v in k]          # Lamarckian: write the repaired genome back
        n_eval += 1
        return objectives(enc, k)

    def mutate(ind):
        for g in range(n):
            if rng.random() < pm:
                ind[g] = rng.randrange(int(enc.n_opt[g]))
        return (ind,)

    def cx_uniform(a, b):
        for g in range(n):
            if rng.random() < 0.5:
                a[g], b[g] = b[g], a[g]
        return a, b

    random.seed(seed)                          # DEAP's selection operators use the global random module
    t0 = time.perf_counter()
    pop = [new_ind() for _ in range(pop_size)]
    for ind in pop:
        ind.fitness.values = evaluate(ind)
    pop = tools.selNSGA2(pop, pop_size, nd="log")   # assigns crowding distance
    for _ in range(n_gen):
        off = [creator.Ind3(list(i)) for i in tools.selTournamentDCD(pop, pop_size)]
        for a, b in zip(off[::2], off[1::2]):
            if rng.random() < cxpb:
                cx_uniform(a, b)
            mutate(a)
            mutate(b)
        for ind in off:
            ind.fitness.values = evaluate(ind)
        pop = tools.selNSGA2(pop + off, pop_size, nd="log")
    wall = time.perf_counter() - t0
    first = tools.sortNondominated(pop, pop_size, first_front_only=True)[0]
    F = np.array([ind.fitness.values for ind in first])
    mask = nondominated(F)
    keep = [first[i] for i in np.flatnonzero(mask)]
    return dict(seed=seed, front=F[mask], genomes=[list(map(int, i)) for i in keep], wall_s=wall, n_eval=n_eval)


def _nsga_worker(args):
    enc, seed, kw = args
    return nsga2(enc, seed, **kw)


def nsga2_seeds(enc: Encoding, seeds, parallel: bool = True, **kw) -> list:
    """Run NSGA-II for each seed (separate processes if parallel). Each seed's result is deterministic."""
    jobs = [(enc, s, kw) for s in seeds]
    if not parallel:
        return [_nsga_worker(j) for j in jobs]
    from concurrent.futures import ProcessPoolExecutor
    import os
    with ProcessPoolExecutor(max_workers=min(len(jobs), os.cpu_count() or 1)) as ex:
        return list(ex.map(_nsga_worker, jobs))


# ======================================================================
# Front quality metrics
# ======================================================================


def normalise(points, ideal: dict, nadir: dict) -> np.ndarray:
    lo = np.array([ideal[o] for o in OBJ]); hi = np.array([nadir[o] for o in OBJ])
    return (np.asarray(points, float) - lo) / np.maximum(hi - lo, 1e-12)


def hv2d(pts: np.ndarray, ref) -> float:
    """Exact 2-D hypervolume (minimisation) of points w.r.t. reference ref."""
    p = pts[np.all(pts < ref, axis=1)]
    if len(p) == 0:
        return 0.0
    p = p[np.lexsort((p[:, 1], p[:, 0]))]
    area, y_prev = 0.0, ref[1]
    for x, y in p:
        if y < y_prev:
            area += (ref[0] - x) * (y_prev - y)
            y_prev = y
    return area


def hypervolume(points, ref) -> float:
    """Exact 3-D hypervolume (minimisation) by slicing along the 3rd objective (HSO)."""
    P_ = np.asarray(points, float)
    ref = np.asarray(ref, float)
    P_ = P_[np.all(P_ < ref, axis=1)]
    if len(P_) == 0:
        return 0.0
    zs = np.unique(P_[:, 2])
    vol = 0.0
    for a, z in enumerate(zs):
        z_next = zs[a + 1] if a + 1 < len(zs) else ref[2]
        vol += (z_next - z) * hv2d(P_[P_[:, 2] <= z][:, :2], ref[:2])
    return vol


def gd(A, ref_front) -> float:
    """Generational distance (mean form, p = 1): mean distance from each point of A to the nearest ref point."""
    A = np.asarray(A, float); R = np.asarray(ref_front, float)
    d = np.sqrt(((A[:, None, :] - R[None, :, :]) ** 2).sum(-1)).min(1)
    return float(d.mean())


def igd(A, ref_front) -> float:
    """Inverted generational distance: mean distance from each ref point to the nearest point of A."""
    return gd(ref_front, A)


def n_strictly_dominated(A, B, tol: float = 1e-6) -> int:
    """How many points of B are STRICTLY dominated by some point of A (0 expected when B is an exact front)."""
    A = np.asarray(A, float); B = np.asarray(B, float)
    return int(sum(np.any(np.all(A <= b + tol, axis=1) & np.any(A < b - tol, axis=1)) for b in B))


def coverage(A, B, tol: float = 1e-9) -> float:
    """Zitzler's C(A, B): fraction of B weakly dominated by at least one point of A."""
    A = np.asarray(A, float); B = np.asarray(B, float)
    return float(np.mean([np.any(np.all(A <= b + tol, axis=1)) for b in B]))


def nearest_distance(p, front) -> tuple[float, bool]:
    """(Euclidean distance to the nearest front point, is p dominated by the front) in the given (normalised) space."""
    F = np.asarray(front, float); p = np.asarray(p, float)
    d = float(np.sqrt(((F - p) ** 2).sum(1)).min())
    dominated = bool(np.any(np.all(F <= p + 1e-9, axis=1) & np.any(F < p - 1e-9, axis=1)))
    return d, dominated
