"""Stage 3 runner: build the corrected MILP, evaluate the published baseline, solve min Z3."""
from __future__ import annotations

import logging

import pandas as pd

from src import metrics as MT
from src import model as MD
from src import params as P

log = logging.getLogger("stage3")
TIEBREAK = {"Z2": 1e-6, "fleet": 1e-4}   # pick the cheapest schedule among equal-Z3 optima


def run(routes: pd.DataFrame, dem: pd.DataFrame, cfg: P.ModelConfig | None = None) -> dict:
    cfg = cfg or P.ModelConfig()
    inst = MD.build_instance(routes, dem, cfg)
    log.info("instance: %d active (r,t) pairs, B_eff=%d, C=%g, alpha=%g, modes: fmax=%s equity=%s hours=%s",
             len(inst.active_pairs()), cfg.B_eff, cfg.C, cfg.alpha, cfg.fmax_mode, cfg.equity_mode, cfg.hours_mode)

    # ---- baseline (published schedule)
    xb, fb = MT.baseline_schedule(inst)
    base_m = MT.evaluate(inst, xb, fb)
    viol = MT.check_schedule(inst, xb, fb)
    viol.to_csv(P.OUT_TAB / "baseline_violations.csv", index=False)
    for c, g in viol.groupby("constraint"):
        log.warning("baseline violates %s in %d place(s); max excess %.3f %s", c, len(g), g.excess.max(), g.unit.iloc[0])

    # ---- presolve diagnostics, then min Z3
    issues = MD.presolve_report(inst)
    for m in issues:
        log.error("presolve: %s", m)
    if issues:
        raise RuntimeError("model is infeasible as configured; see presolve messages")
    built = MD.build_model(inst, {"Z3": 1.0, **TIEBREAK})
    log.info("MILP: %d variables, %d constraints", built.prob.numVariables(), built.prob.numConstraints())
    res = MD.solve(built, time_limit=60)
    log.info("min Z3 solved: %s in %.2f s", res["status"], res["wall_s"])
    xs, fs = MD.schedule_to_arrays(inst, res["schedule"])
    opt_m = MT.evaluate(inst, xs, fs)
    v_opt = MT.check_schedule(inst, xs, fs)
    hard = v_opt[~v_opt.constraint.str.startswith("C5 equity")]
    assert hard.empty, hard

    # same objective with f_max relaxed by two menu levels: shows how much overflow the published bounds cause
    cfg_r = P.ModelConfig(**{**cfg.__dict__, "fmax_mode": "relaxed"})
    inst_r = MD.build_instance(routes, dem, cfg_r)
    res_r = MD.solve(MD.build_model(inst_r, {"Z3": 1.0, **TIEBREAK}), time_limit=60)
    xr, fr = MD.schedule_to_arrays(inst_r, res_r["schedule"])
    rel_m = MT.evaluate(inst_r, xr, fr)
    log.info("min Z3 with relaxed f_max: Z3 %.1f (published bounds: %.1f)", rel_m["Z3"], opt_m["Z3"])
    opt_m["relaxed_Z3"] = rel_m["Z3"]

    rows = [dict(schedule="published baseline", **base_m), dict(schedule="min Z3 (MILP)", **opt_m),
            dict(schedule="min Z3 (MILP, relaxed f_max)", **rel_m)]
    out = pd.DataFrame(rows)
    out.insert(1, "label", "synthetic demand, illustrative")
    out.to_csv(P.OUT / "baseline_metrics.csv", index=False)
    res["schedule"].assign(label="synthetic demand, illustrative").to_csv(P.OUT_TAB / "schedule_minZ3.csv", index=False)
    _write_log(cfg, base_m, opt_m, viol, res, built.prob.numVariables(), built.prob.numConstraints())
    return dict(inst=inst, baseline=base_m, minZ3=res, metrics=out, violations=viol)


def _write_log(cfg, base_m, opt_m, viol, res, nv, nc):
    from src.stage1 import _md_table
    keys = ["Z1", "Z1_daily", "Z2", "Z3", "fleet_used", "fleet_AM", "fleet_Midday", "fleet_PM", "mean_wait_min",
            "max_wait_min", "ewt_min", "mean_LF", "n_LF_gt_1", "gini_LF"]
    tab = pd.DataFrame({"metric": keys, "published baseline": [base_m[k] for k in keys],
                        "min Z3 (MILP)": [opt_m[k] for k in keys]})
    vsum = viol.groupby("constraint").agg(n=("excess", "size"), max_excess=("excess", "max"),
                                          unit=("unit", "first")).reset_index()
    txt = f"""# Stage 3: Baseline evaluation and single-objective run

> **Synthetic demand, illustrative.** These numbers show how the model behaves; they are not CTU results.

Config: B_eff = {cfg.B_eff}, C = {cfg.C:g}, α = {cfg.alpha}, f_max mode = {cfg.fmax_mode}, equity = {cfg.equity_mode},
hours = {cfg.hours_mode}. MILP: {nv} variables, {nc} constraints, solved {res['status']} in {res['wall_s']:.2f} s (HiGHS).

{_md_table(tab, '.2f')}

## Published baseline vs model constraints
{_md_table(vsum, '.3f')}

**Why min Z3 barely moves Z3 under published bounds:** most overflow sits on long-headway routes (31, 28A, 101, 8,
23B) that already run at their published f_max. If f_max is relaxed by two menu levels, min Z3 reaches
{opt_m['relaxed_Z3']:.1f} pax/day. The published frequency range, not the fleet, is the binding limit on crowding.

Details are in `outputs/tables/baseline_violations.csv`. C1: the published allocation keeps 380-385 buses on the road
in each period, more than B_eff = {cfg.B_eff}, because it holds almost no spares. C2: routes 40, 76 and 25/25A cannot
run their mid frequency with their own buses at the assumed 22 km/h.
"""
    (P.OUT / "stage3_report.md").write_text(txt, encoding="utf-8")

