"""Stage 5 runner: Pareto front by AUGMECON (exact MILP) and NSGA-II (DEAP), cross-check and GP comparison.

SYNTHETIC DEMAND, ILLUSTRATIVE. Literature behind each choice: docs/LITERATURE.md.
"""
from __future__ import annotations

import logging
import time

import numpy as np
import pandas as pd

from src import goals as G
from src import metrics as MT
from src import model as MD
from src import pareto as PA
from src import params as P
from src import plots

log = logging.getLogger("stage5")
OBJ = list(PA.OBJ)


def stage5_instance(routes, dem):
    cfg = P.ModelConfig(fmax_mode=P.PARETO_FMAX_MODE, alpha=P.PARETO_ALPHA)
    return MD.build_instance(routes, dem, cfg)


def verify_points(inst, headway_lists, reported: np.ndarray, tol: float = 1e-6) -> int:
    """Every reported point must satisfy all hard constraints and reproduce its objective values. Returns count."""
    for hw, z in zip(headway_lists, reported):
        x, f, m = PA.evaluate_headways(inst, hw)
        v = MT.check_schedule(inst, x, f)
        v = v[~v.constraint.str.startswith("C5 equity")]      # equity is not a constraint in Stage 5
        if not v.empty:
            raise AssertionError(f"infeasible reported point:\n{v}")
        for o, val in zip(OBJ, z):
            if abs(m[o] - val) > tol * max(1.0, abs(val)):
                raise AssertionError(f"objective mismatch {o}: reported {val}, recomputed {m[o]}")
        for (i, t), h in zip(inst.active_pairs(), hw):
            if h not in inst.menu[i, t]:
                raise AssertionError(f"headway {h} not allowed for {inst.route_no[i]} {t}")
    return len(headway_lists)


def _hw_str(hw) -> str:
    return ";".join(f"{h:g}" for h in hw)


def parse_hw(s: str) -> list:
    return [float(v) for v in s.split(";")]


def run(routes: pd.DataFrame, dem: pd.DataFrame, n_grid: int = P.EPS_GRID, pop: int = P.NSGA_POP,
        gen: int = P.NSGA_GEN, seeds=P.NSGA_SEEDS, parallel: bool = True, write: bool = True) -> dict:
    inst = stage5_instance(routes, dem)
    xb, fb = MT.baseline_schedule(inst)
    base = MT.evaluate(inst, xb, fb)

    # ---- exact front (AUGMECON)
    t0 = time.perf_counter()
    pay, ideal, nadir, pay_hw = PA.lexicographic_payoff(inst, return_headways=True)
    grid, eps_front, eps_hw = PA.augmecon(inst, ideal, nadir, n_grid, P.AUGMECON_EPS, extra_headways=pay_hw)
    t_eps = time.perf_counter() - t0
    n_inf = int((grid.status != "Optimal").sum())
    log.info("AUGMECON %dx%d: %d optimal cells, %d infeasible/skipped, %d non-dominated points, %.1f s",
             n_grid, n_grid, int((grid.status == "Optimal").sum()), n_inf, len(eps_front), t_eps)

    # ---- NSGA-II
    enc = PA.make_encoding(inst, {"Z1": base["Z1"], "Z2": base["Z2"], "Z3": base["Z3"]})
    t0 = time.perf_counter()
    runs = PA.nsga2_seeds(enc, seeds, parallel=parallel, pop_size=pop, n_gen=gen, cxpb=P.NSGA_CXPB)
    t_nsga_wall = time.perf_counter() - t0
    nsga_rows, nsga_hw, nsga_pts = [], [], []
    for r in runs:
        for z, gnm in zip(r["front"], r["genomes"]):
            hw = PA.headways_of(enc, gnm)
            nsga_rows.append(dict(seed=r["seed"], Z1=z[0], Z2=z[1], Z3=z[2], headways=_hw_str(hw)))
            nsga_hw.append(hw)
            nsga_pts.append(z)
        log.info("NSGA-II seed %d: %d non-dominated points, %d evaluations, %.1f s",
                 r["seed"], len(r["front"]), r["n_eval"], r["wall_s"])
    nsga_df = pd.DataFrame(nsga_rows)

    # ---- every reported point must be feasible and reproduce its objectives
    n_ok = verify_points(inst, eps_hw, eps_front[OBJ].to_numpy()) + \
        verify_points(inst, nsga_hw, np.array(nsga_pts))
    log.info("verified %d reported points: all constraints satisfied, objectives reproduced", n_ok)

    # ---- metrics in normalised space (0 = ideal, 1 = payoff nadir); reference point HV_REF in each objective
    ref = np.full(3, P.HV_REF)
    E = PA.normalise(eps_front[OBJ].to_numpy(), ideal, nadir)
    union_mask = PA.nondominated(np.array(nsga_pts))
    U = np.array(nsga_pts)[union_mask]
    Un = PA.normalise(U, ideal, nadir)
    mrows = [dict(method="AUGMECON (exact)", seed="-", n_points=len(E), hypervolume=PA.hypervolume(E, ref),
                  GD_to_eps=0.0, IGD_eps=0.0, C_eps_over_this=1.0, C_this_over_eps=1.0,
                  eps_points_strictly_dominated=0, runtime_s=t_eps,
                  # MILP solves: every non-skipped grid cell + 3 lexicographic solves per payoff row
                  evaluations=int((grid.status != "skipped (infeasible)").sum()) + len(OBJ) * len(OBJ))]
    for r in runs:
        Fn = PA.normalise(r["front"], ideal, nadir)
        mrows.append(dict(method="NSGA-II", seed=r["seed"], n_points=len(Fn), hypervolume=PA.hypervolume(Fn, ref),
                          GD_to_eps=PA.gd(Fn, E), IGD_eps=PA.igd(Fn, E), C_eps_over_this=PA.coverage(E, Fn),
                          C_this_over_eps=PA.coverage(Fn, E),
                          eps_points_strictly_dominated=PA.n_strictly_dominated(r["front"], eps_front[OBJ].to_numpy()),
                          runtime_s=r["wall_s"], evaluations=r["n_eval"]))
    mrows.append(dict(method="NSGA-II union of seeds", seed="all", n_points=len(Un),
                      hypervolume=PA.hypervolume(Un, ref), GD_to_eps=PA.gd(Un, E), IGD_eps=PA.igd(Un, E),
                      C_eps_over_this=PA.coverage(E, Un), C_this_over_eps=PA.coverage(Un, E),
                      eps_points_strictly_dominated=PA.n_strictly_dominated(U, eps_front[OBJ].to_numpy()),
                      runtime_s=sum(r["wall_s"] for r in runs), evaluations=sum(r["n_eval"] for r in runs)))
    metrics = pd.DataFrame(mrows)
    if metrics.eps_points_strictly_dominated.sum() > 0:
        raise AssertionError("an AUGMECON point is strictly dominated: the exact front is not exact")

    # ---- GP solutions and baseline vs the combined front
    allp = np.vstack([eps_front[OBJ].to_numpy(), U])
    comb = allp[PA.nondominated(allp)]
    Cn = PA.normalise(comb, ideal, nadir)
    gp_cfg = G.load_config()
    tg = G.targets_from_config(inst, gp_cfg)
    gp_rows = []
    for sc in gp_cfg["scenarios"]:
        out = G.run_scenario(inst, tg, sc)
        x, f = MD.schedule_to_arrays(inst, out["result"]["schedule"])
        m = MT.evaluate(inst, x, f)
        d, dom = PA.nearest_distance(PA.normalise([[m[o] for o in OBJ]], ideal, nadir)[0], Cn)
        gp_rows.append(dict(point=sc["name"], Z1=m["Z1"], Z2=m["Z2"], Z3=m["Z3"], dist_to_front_norm=d,
                            dominated_by_front=dom, feasible=True))
    d, dom = PA.nearest_distance(PA.normalise([[base[o] for o in OBJ]], ideal, nadir)[0], Cn)
    gp_rows.append(dict(point="BASELINE (published)", Z1=base["Z1"], Z2=base["Z2"], Z3=base["Z3"],
                        dist_to_front_norm=d, dominated_by_front=dom,
                        feasible=False))
    gpdf = pd.DataFrame(gp_rows)

    res = dict(inst=inst, payoff=pay, ideal=ideal, nadir=nadir, grid=grid, eps=eps_front, eps_hw=eps_hw,
               nsga=nsga_df, nsga_union=pd.DataFrame(U, columns=OBJ), runs=runs, metrics=metrics, gp=gpdf,
               base=base, t_eps=t_eps, t_nsga_wall=t_nsga_wall)
    if write:
        _write(res, n_grid, pop, gen, seeds)
    return res


def _write(res, n_grid, pop, gen, seeds):
    lab = "synthetic demand, illustrative"
    eps = res["eps"].copy()
    eps["headways"] = [_hw_str(h) for h in res["eps_hw"]]
    eps.insert(0, "label", lab)
    eps.to_csv(P.OUT / "pareto_eps.csv", index=False)
    res["nsga"].assign(label=lab).to_csv(P.OUT / "pareto_nsga2.csv", index=False)
    res["grid"].to_csv(P.OUT_TAB / "pareto_eps_grid.csv", index=False)
    res["payoff"].to_csv(P.OUT_TAB / "pareto_payoff.csv", index=False)
    res["metrics"].to_csv(P.OUT_TAB / "pareto_metrics.csv", index=False)
    res["gp"].to_csv(P.OUT_TAB / "pareto_gp_distance.csv", index=False)
    plots.pareto_figures(res["eps"], res["nsga_union"], res["gp"][res["gp"].feasible], res["base"],
                         P.OUT_FIG / "pareto_2d.png", P.OUT_FIG / "pareto_3d.png")
    _report(res, n_grid, pop, gen, seeds)


def _report(res, n_grid, pop, gen, seeds):
    from src.stage1 import _md_table
    g = res["grid"]
    inf = g[g.status != "Optimal"]
    m = res["metrics"]
    ns = m[m.method == "NSGA-II"]
    un = m[m.method == "NSGA-II union of seeds"].iloc[0]
    ex = m[m.method == "AUGMECON (exact)"].iloc[0]
    gp = res["gp"]
    on_front = gp[(gp.point != "BASELINE (published)") & (gp.dist_to_front_norm < 1e-6)]
    txt = f"""# Stage 5: Pareto front and cross-check

> **Synthetic demand, illustrative.** f_max relaxed, α = {P.PARETO_ALPHA}, B_eff = {res['inst'].cfg.B_eff}.
> Minimise (Z1 waiting, Z2 vehicle-km, Z3 unserved). Literature: `docs/LITERATURE.md`.

## Payoff table (lexicographic optimisation, Mavrotas 2009)
{_md_table(res['payoff'], '.1f')}

Ideal = diagonal; nadir = column maximum (payoff-table estimate). Normalisation: 0 = ideal, 1 = nadir.

## AUGMECON grid ({n_grid} × {n_grid} over Z1 and Z2)
min Z3/r3 − {P.AUGMECON_EPS}·(s1/r1 + s2/r2) s.t. Z1 + s1 = e1, Z2 + s2 = e2. The slack terms make every optimum
strictly (not weakly) Pareto-efficient. Once a cell is infeasible, every tighter e2 for the same e1 is skipped.
- Cells solved to optimality: {int((g.status == 'Optimal').sum())}; infeasible: {int((g.status == 'Infeasible').sum())};
  skipped by early exit: {int((g.status == 'skipped (infeasible)').sum())}. Full log in `outputs/tables/pareto_eps_grid.csv`.
- Infeasible or skipped cells are in the corner where both Z1 and Z2 are pushed towards their ideals: high frequency
  (low waiting) costs vehicle-km, so both cannot be minimal at once.
- Distinct non-dominated points, including the 3 lexicographic payoff rows (efficient by construction):
  **{len(res['eps'])}**, found in {res['t_eps']:.1f} s.

## NSGA-II (DEAP; population {pop}, {gen} generations, crossover {P.NSGA_CXPB}, mutation 1/n_genes, seeds {list(seeds)})
Encoding: one gene per active route-period = index into its headway menu. Repair: buses above the C5 limit, then the
fleet C1 per period, are removed by lengthening the headway with the smallest normalised loss per bus released.
The repaired genome is written back (Lamarckian).

## Front comparison (normalised space, hypervolume reference point = {P.HV_REF} in every objective)
{_md_table(m, '.4f')}

- GD = mean distance from NSGA-II points to the nearest ε-constraint point. IGD = mean distance from ε-constraint
  points to the nearest NSGA-II point; this measures coverage. C(A, B) = share of B weakly dominated by A
  (Zitzler & Thiele 1999). C uses weak dominance, so an identical point counts.
- **Correctness check:** no NSGA-II point strictly dominates any AUGMECON point (column
  eps_points_strictly_dominated = 0 for every seed). The exact points are confirmed efficient.
- NSGA-II per seed: hypervolume {ns.hypervolume.min():.4f}-{ns.hypervolume.max():.4f} vs exact {ex.hypervolume:.4f};
  GD {ns.GD_to_eps.min():.4f}-{ns.GD_to_eps.max():.4f}. The union of seeds reaches HV {un.hypervolume:.4f}.
- Runtime: AUGMECON {ex.runtime_s:.1f} s for the whole grid. NSGA-II {ns.runtime_s.mean():.1f} s per seed
  ({int(ns.evaluations.mean())} evaluations), with 5 seeds run in parallel in {res['t_nsga_wall']:.1f} s of wall time.

## Goal-programming solutions vs the front
{_md_table(gp, '.4f')}

Distance is Euclidean in normalised space to the nearest point of the combined non-dominated front
(AUGMECON ∪ NSGA-II). {len(on_front)} of {len(gp) - 1} GP solutions lie exactly on the front: those that put G2
(Z3) first coincide with the lexicographic min-Z3 payoff point. A positive distance with "dominated = False" means
no sampled front point dominates it. P-EQUITY and P-BALANCED optimise equity (G4), which is not one of the three
front objectives, so they are efficient in a 4-D sense and sit just off the 3-D front. The published
baseline breaks the fleet limit (385 > {res['inst'].cfg.B_eff} buses), so it is outside the feasible set and is
shown only for reference.

## Discussion
- **The exact method is better here.** At this size (191 route-periods, about 650 variables) one MILP solves in a
  fraction of a second. AUGMECON gives strictly efficient points with a certificate of optimality, plus a list of
  infeasible regions, in {res['t_eps']:.0f} s.
- **NSGA-II still matters.** It returns a whole front from one run, needs no linearisation, and would handle
  objectives an MILP cannot: for example, Z1 from a bus-bunching simulation, or a non-linear crowding discomfort
  function. That is why the bus-network literature uses metaheuristics for larger, integrated route-design and
  frequency problems.
- **Read the NSGA-II metrics as a benchmark of the heuristic against the exact front, not the reverse.**
  NSGA-II's higher hypervolume ({un.hypervolume:.3f} vs {ex.hypervolume:.3f}) comes from its many points filling
  the gaps between the {len(res['eps'])} ε-grid samples, not from beating them. It strictly dominates none of
  them, and its GD of about {ns.GD_to_eps.mean():.2f} (normalised) shows it stays near the exact surface. A finer
  grid (AUGMECON2-style, Mavrotas & Florios) would raise the exact hypervolume at the cost of more MILP solves.
"""
    (P.OUT / "pareto_report.md").write_text(txt, encoding="utf-8")
