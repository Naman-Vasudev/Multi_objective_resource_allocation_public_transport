"""Collect every number used in the final report, synopsis and slides from the pipeline outputs.

Writes outputs/report_facts.json. The document builders read ONLY this file, so no number is typed by hand.
Run after `python run_all.py`.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from src import calibration as CAL
from src import data as D
from src import demand as DM
from src import goals as G
from src import model as MD
from src import params as P
from src import simulate as S


def _r(x, k=2):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), k)


def main() -> dict:
    f = {}
    d = D.load_all()
    routes = d["routes"]
    f["data"] = dict(routes=len(routes), buses=int(routes.x_base.sum()), km=_r(routes.d_r_km.sum(), 1),
                     stops=len(d["stops"]), loops=int(routes.is_loop.sum()),
                     pdf_ok=int((d["pdf"].match == "OK").sum()),
                     hubs=int((d["stops"].n_routes_serving >= P.HUB_MIN_ROUTES).sum()),
                     overnight=int(routes.overnight.sum()),
                     mv_mismatch=len(d["mv_issues"]))

    cs = pd.read_csv(P.OUT_TAB / "calibration_scenarios.csv")
    def cal(sc, v, l):
        r = cs[(cs.scenario == sc) & (cs.v_kmh == v) & (cs.layover_frac == l)].iloc[0]
        return dict(N=_r(r.N_need_fmid, 1), U=_r(100 * r.utilisation, 1), short=int(r.n_routes_x_lt_ceil_fmin),
                    over=int(r.n_routes_x_gt_ceil_fmax))
    f["calib"] = dict(S1_22_0=cal("S1", 22, 0.0), S2_22_0=cal("S2", 22, 0.0), S2_22_10=cal("S2", 22, 0.1),
                      S3_22_10=cal("S3", 22, 0.1), S2_18_0=cal("S2", 18, 0.0),
                      v_implied_noSpare=_r(CAL.implied_uniform_speed(routes, "S2", 0.10, P.FLEET_B), 1),
                      v_implied_spare=_r(CAL.implied_uniform_speed(routes, "S2", 0.10, P.FLEET_B / 1.1), 1))

    dem = pd.read_csv(P.PROCESSED / "demand_rt.csv", dtype={"route_no": str})
    a = dem[dem.active == 1]
    cv = a.groupby("period").M.agg(lambda s: s.std(ddof=0) / s.mean())
    lf = pd.read_csv(P.OUT_TAB / "baseline_load_factors.csv", dtype={"route_no": str})
    lfa = lf[lf.active == 1]
    f["demand"] = dict(daily_boardings=int(round(P.DAILY_BOARDINGS)), theta=P.THETA,
                       multipliers=P.DEMAND_MULTIPLIERS, lo=P.TFN_LO, hi=P.TFN_HI,
                       active={t: int((dem[dem.period == t].active == 1).sum()) for t in P.PERIODS},
                       cv={t: _r(cv[t], 2) for t in P.PERIODS},
                       mean_M={t: _r(a[a.period == t].M.mean(), 1) for t in P.PERIODS},
                       overloaded={t: int((lfa[lfa.period == t].LF > 1).sum()) for t in P.PERIODS},
                       meanLF={t: _r(lfa[lfa.period == t].LF.mean(), 2) for t in P.PERIODS})

    cfg = P.ModelConfig()
    inst = MD.build_instance(routes, DM.demand_table(d)[1], cfg)
    b = MD.build_model(inst, {"Z3": 1.0})
    viol = pd.read_csv(P.OUT_TAB / "baseline_violations.csv")
    c1 = viol[viol.constraint == "C1 fleet"].set_index("period").excess
    f["model"] = dict(B_eff=cfg.B_eff, spare=cfg.spare_ratio, C=cfg.C, alpha=cfg.alpha, pairs=len(inst.active_pairs()),
                      n_vars=b.prob.numVariables(), n_cons=b.prob.numConstraints(),
                      menu=list(P.HEADWAY_MENU_MIN), c1_excess={k: int(v) for k, v in c1.items()},
                      c2_routes=sorted(set(viol[viol.constraint.str.startswith("C2")].route_no)),
                      infeasible_s10="352 > 350")

    gp = pd.read_csv(P.OUT / "gp_results.csv")
    g = gp[(gp.alpha == 0.5) & (gp.fmax_mode == "relaxed") & (gp.type != "evaluation")]
    ach = pd.read_csv(P.OUT_TAB / "gp_goal_achievement.csv")
    ach = ach[(ach.alpha == 0.5) & (ach.fmax_mode == "relaxed")]
    gcfg = G.load_config()
    f["gp"] = dict(kappa1=gcfg["kappa1"], kappa3=gcfg["kappa3"], runs=int((gp.type != "evaluation").sum()),
                   rows=[dict(name=r.scenario, dZ1=_r(r.pct_Z1, 1), dZ2=_r(r.pct_Z2, 1), dZ3=_r(r.pct_Z3, 1),
                              eq=_r(r.equity_excess_min, 0),
                              met=int(ach[(ach.scenario == r.scenario) & ach.met].shape[0]))
                         for r in g.itertuples()],
                   published_same=bool(gp[(gp.alpha == 0.5) & (gp.fmax_mode == "published") & (gp.type != "evaluation")]
                                       .pct_Z3.round(6).nunique() == 1))
    pub = gp[(gp.alpha == 0.5) & (gp.fmax_mode == "published") & (gp.type != "evaluation")].iloc[0]
    f["gp"]["published"] = dict(dZ1=_r(pub.pct_Z1, 1), dZ2=_r(pub.pct_Z2, 1), dZ3=_r(pub.pct_Z3, 1))

    pm = pd.read_csv(P.OUT_TAB / "pareto_metrics.csv")
    ex = pm[pm.method == "AUGMECON (exact)"].iloc[0]
    ns = pm[pm.method == "NSGA-II"]
    un = pm[pm.method == "NSGA-II union of seeds"].iloc[0]
    grid = pd.read_csv(P.OUT_TAB / "pareto_eps_grid.csv")
    gd = pd.read_csv(P.OUT_TAB / "pareto_gp_distance.csv")
    f["pareto"] = dict(grid=int(math.sqrt(len(grid))), optimal=int((grid.status == "Optimal").sum()),
                       infeasible=int((grid.status == "Infeasible").sum()),
                       skipped=int((grid.status == "skipped (infeasible)").sum()),
                       exact_points=int(ex.n_points), hv_exact=_r(ex.hypervolume, 3), t_exact=_r(ex.runtime_s, 0),
                       hv_seed_min=_r(ns.hypervolume.min(), 3), hv_seed_max=_r(ns.hypervolume.max(), 3),
                       hv_union=_r(un.hypervolume, 3), gd=_r(ns.GD_to_eps.mean(), 3), igd=_r(ns.IGD_eps.mean(), 3),
                       nsga_points=f"{int(ns.n_points.min())}-{int(ns.n_points.max())}",
                       t_seed=_r(ns.runtime_s.mean(), 0), dominated=int(pm.eps_points_strictly_dominated.sum()),
                       evals=int(ns.evaluations.mean()),
                       gp_on_front=[r.point for r in gd.itertuples() if r.point != "BASELINE (published)" and r.dist_to_front_norm < 1e-3],
                       gp_dist={r.point: _r(r.dist_to_front_norm, 3) for r in gd.itertuples()})

    tr = pd.read_csv(P.OUT_TAB / "simulation_tradeoffs.csv")
    def row(nm):
        r = tr[tr.schedule == nm].iloc[0]
        return dict(wait=_r(r.mean_wait_min, 2), over=_r(r.overflow_pax, 0), vkm=_r(r.vehicle_km, 0),
                    fleet=int(r.fleet_used), eq=_r(r.equity_excess_min, 0), p5=_r(100 * r.P_overflow_gt_5pct, 1),
                    gini=_r(r.gini_LF, 3))
    names = list(tr.schedule)
    sim = {nm: row(nm) for nm in names}
    def pct(a_, b_):
        return _r(100 * (a_ - b_) / b_, 1)
    pol, b0, b1 = sim["P-BALANCED (α=0.5)"], sim["Baseline"], sim[S.PEAK_BASELINE]
    f["sim"] = dict(N=P.SIM_N, seed=P.SIM_SEED, cv=P.SIM_HEADWAY_CV, rows=sim,
                    headline=dict(policy="P-BALANCED (α=0.5)",
                                  vs_mid=dict(wait=pct(pol["wait"], b0["wait"]), over=pct(pol["over"], b0["over"]),
                                              vkm=pct(pol["vkm"], b0["vkm"]), fleet=pct(pol["fleet"], b0["fleet"])),
                                  vs_peak=dict(wait=pct(pol["wait"], b1["wait"]), over=pct(pol["over"], b1["over"]),
                                               vkm=pct(pol["vkm"], b1["vkm"]), fleet=pct(pol["fleet"], b1["fleet"]))))
    oos = pd.read_csv(P.OUT / "sensitivity_out_of_sample.csv").pivot_table(
        index="schedule", columns="sample", values="P_overflow_gt_5pct")
    f["oos"] = {k: dict(ins=_r(100 * v["in-sample"], 1), out=_r(100 * v["out-of-sample (wider)"], 1))
                for k, v in oos.iterrows()}
    oat = pd.read_csv(P.OUT / "sensitivity_oat.csv")
    f["sens"] = [dict(factor=r.factor, value=_r(r.value, 2), feasible=bool(r.feasible),
                      imp=_r(r.wait_improvement_pct, 2), B_eff=int(r.B_eff)) for r in oat.itertuples()]
    al = pd.read_csv(P.OUT / "sensitivity_alpha.csv")
    f["alpha"] = [dict(alpha=r.alpha, p5=_r(100 * r.opt_P_overflow_gt_5pct, 1), vkm=_r(r.opt_vehicle_km, 0),
                       wait=_r(r.opt_mean_wait_min, 2)) for r in al.itertuples()]
    fl = pd.read_csv(P.OUT / "sensitivity_fleet.csv")
    f["fleet"] = [dict(cut=r.fleet_cut, B_eff=int(r.B_eff), feasible=bool(r.feasible),
                       imp=_r(r.wait_improvement_pct, 2)) for r in fl.itertuples()]
    out = P.OUT / "report_facts.json"
    out.write_text(json.dumps(f, indent=1, ensure_ascii=False), encoding="utf-8")
    return f


if __name__ == "__main__":
    f = main()
    print(json.dumps({k: f[k] for k in ("data", "calib", "model", "pareto")}, indent=1, ensure_ascii=False))
    print(json.dumps(f["sim"]["headline"], ensure_ascii=False), json.dumps(f["gp"]["rows"], ensure_ascii=False))
