"""Stage 4 runner: goal programming with priorities. SYNTHETIC DEMAND, ILLUSTRATIVE."""
from __future__ import annotations

import logging
import math

import numpy as np
import pandas as pd

from src import goals as G
from src import metrics as MT
from src import model as MD
from src import params as P
from src import plots

log = logging.getLogger("stage4")
METRIC_COLS = ["Z1", "Z2", "Z3", "fleet_used", "mean_wait_min", "max_wait_min", "ewt_min", "mean_LF",
               "n_LF_gt_1", "gini_LF", "equity_excess_min", "n_over_cap"]


def _achieved(dev: float, scale: float) -> bool:
    return dev <= 1e-6 * scale + 1e-6


def lexicographic_ok(inst, tg, levels, level_rows, m) -> bool:
    """A later level never worsens an earlier one: final true deviations <= locked level values (+ tolerance)."""
    dv = G.deviations_of(inst, tg, m)
    for lv, row in zip(levels, level_rows):
        v = sum(dv[g] / tg.scale[g] for g in lv) if len(lv) > 1 else dv[lv[0]]
        if v > row["achieved_dev"] + 1e-6 + 1e-6 * abs(row["achieved_dev"]):
            return False
    return True


def route_changes(inst, sched: pd.DataFrame, k: int = 10) -> pd.DataFrame:
    """Top-k routes gaining and losing buses (route fleet = max over periods of x_rt) with a demand/supply reason."""
    C = inst.cfg.C
    rows = []
    s = sched.set_index(["route_no", "period"])
    for i, rn in enumerate(inst.route_no):
        act = [t for t in inst.periods if inst.active[i, t]]
        if not act:
            continue
        x_new = max(int(s.at[(rn, t), "x"]) for t in act)
        # reference period = the one that sets the route's bus count (first such period in AM, Midday, PM order)
        ref = next(t for t in act if int(s.at[(rn, t), "x"]) == x_new)
        h0, h1 = 60.0 / inst.f0[i], float(s.at[(rn, ref), "headway_min"])
        peak = [t for t in act if t in ("AM", "PM")] or act
        lf0 = max(inst.M[i, t] / (C * inst.f0[i]) for t in peak)
        need0 = inst.f0[i] * inst.tau[i]
        rows.append(dict(route_no=rn, x0=int(inst.x0[i]), x_new=x_new, delta=x_new - int(inst.x0[i]),
                         ref_period=ref, headway_base=h0, headway_new=h1, peak_LF_base=lf0,
                         need_base=need0, M_ref=inst.M[i, ref]))
    df = pd.DataFrame(rows)

    def reason(r):
        if r.delta > 0:
            if r.x0 < r.need_base - 1e-9:
                return "supply", f"baseline short of buses for its own timetable (f·τ = {r.need_base:.2f} > {r.x0})"
            if r.peak_LF_base > 1:
                return "demand", f"overcrowded at baseline (peak LF {r.peak_LF_base:.2f}): headway {r.headway_base:.0f}→{r.headway_new:.0f} min"
            if r.headway_new < r.headway_base - 1e-9:
                return "demand", f"busy route (M = {r.M_ref:.0f} pax/h): headway {r.headway_base:.0f}→{r.headway_new:.0f} min cuts waiting"
            return "supply", "extra buses at the same headway (fleet slack)"
        if r.delta < 0:
            if r.peak_LF_base < 0.5 and r.headway_new > r.headway_base + 1e-9:
                return "demand", f"spare capacity (peak LF {r.peak_LF_base:.2f}): headway {r.headway_base:.0f}→{r.headway_new:.0f} min"
            if r.x0 > math.ceil(r.need_base - 1e-9):
                return "supply", f"surplus buses: x0 = {r.x0} vs f·τ = {r.need_base:.2f} at baseline frequency"
            return "supply", "buses released to meet the fleet limit for higher-priority routes"
        return "none", "no change"

    df[["reason_type", "reason"]] = df.apply(lambda r: pd.Series(reason(r)), axis=1)
    gain = df[df.delta > 0].sort_values(["delta", "peak_LF_base"], ascending=[False, False]).head(k).assign(direction="gain")
    lose = df[df.delta < 0].sort_values(["delta", "peak_LF_base"], ascending=[True, True]).head(k).assign(direction="lose")
    return pd.concat([gain, lose], ignore_index=True)


def run(routes: pd.DataFrame, dem: pd.DataFrame, gp_cfg: dict | None = None, base_cfg: P.ModelConfig | None = None) -> dict:
    gp_cfg = gp_cfg or G.load_config()
    base_cfg = base_cfg or P.ModelConfig()
    res_rows, ach_rows, lvl_rows, pay_rows, chg = [], [], [], [], []
    for mode in gp_cfg["fmax_modes"]:
        for alpha in gp_cfg["alphas"]:
            cfg = P.ModelConfig(**{**base_cfg.__dict__, "fmax_mode": mode, "alpha": alpha})
            inst = MD.build_instance(routes, dem, cfg)
            tg = G.targets_from_config(inst, gp_cfg)
            bm = tg.baseline
            prows, ideal, nadir = G.payoff_table(inst)
            for r in prows:
                pay_rows.append(dict(fmax_mode=mode, alpha=alpha, **r))
            res_rows.append(dict(scenario="BASELINE (published)", type="evaluation", fmax_mode=mode, alpha=alpha,
                                 status="n/a", wall_s=0.0, lex_ok=None, **{c: bm[c] for c in METRIC_COLS},
                                 pct_Z1=0.0, pct_Z2=0.0, pct_Z3=0.0))
            for sc in gp_cfg["scenarios"]:
                out = G.run_scenario(inst, tg, sc)
                x, f = MD.schedule_to_arrays(inst, out["result"]["schedule"])
                m = MT.evaluate(inst, x, f)
                hard = MT.check_schedule(inst, x, f)
                hard = hard[~hard.constraint.str.startswith("C5 equity")]
                assert hard.empty, (sc["name"], hard)
                lex = lexicographic_ok(inst, tg, sc["levels"], out["levels"], m) if sc["type"] == "preemptive" else None
                if lex is False:
                    raise AssertionError(f"lexicographic order violated: {sc['name']} {mode} alpha={alpha}")
                res_rows.append(dict(scenario=sc["name"], type=sc["type"], fmax_mode=mode, alpha=alpha,
                                     status=out["status"], wall_s=out["wall_s"], lex_ok=lex,
                                     **{c: m[c] for c in METRIC_COLS},
                                     **{f"pct_{z}": 100 * (m[z] - bm[z]) / bm[z] for z in ("Z1", "Z2", "Z3")}))
                dv = G.deviations_of(inst, tg, m)
                ach_val = {"G1": m["Z1"], "G2": m["Z3"], "G3": m["Z2"], "G4": m["equity_excess_min"]}
                tgt = {"G1": tg.T1, "G2": tg.T2, "G3": tg.T3, "G4": 0.0}
                ideal_g = {"G1": ideal["Z1"], "G2": ideal["Z3"], "G3": ideal["Z2"], "G4": ideal["equity_excess_min"]}
                prio = {g: k for k, lv in enumerate(sc.get("levels", []), 1) for g in lv}
                for g in G.GOALS:
                    ach_rows.append(dict(scenario=sc["name"], fmax_mode=mode, alpha=alpha, goal=g,
                                         description=G.GOAL_INFO[g][0], unit=G.GOAL_INFO[g][1],
                                         priority=prio.get(g, "weighted" if sc["type"] != "preemptive" else ""),
                                         target=tgt[g], achieved=ach_val[g], unwanted_dev=dv[g],
                                         met=_achieved(dv[g], tg.scale[g]),
                                         best_possible=ideal_g[g],
                                         reason_if_unmet=("" if _achieved(dv[g], tg.scale[g]) else
                                                          "target beyond the best possible value (ideal)"
                                                          if ideal_g[g] - tgt[g] > 1e-6 * tg.scale[g] else
                                                          "traded off for a higher-priority goal")))
                for lv in out["levels"]:
                    lvl_rows.append(dict(scenario=sc["name"], fmax_mode=mode, alpha=alpha, **lv))
                if math.isclose(alpha, gp_cfg["report_alpha"]):
                    rc = route_changes(inst, out["result"]["schedule"])
                    chg.append(rc.assign(scenario=sc["name"], fmax_mode=mode, alpha=alpha))
            log.info("GP %s alpha=%.2f: %d scenarios solved", mode, alpha, len(gp_cfg["scenarios"]))

    res = pd.DataFrame(res_rows)
    res.insert(0, "label", "synthetic demand, illustrative")
    res.to_csv(P.OUT / "gp_results.csv", index=False)
    ach = pd.DataFrame(ach_rows)
    ach.to_csv(P.OUT_TAB / "gp_goal_achievement.csv", index=False)
    pd.DataFrame(lvl_rows).to_csv(P.OUT_TAB / "gp_levels.csv", index=False)
    pay = pd.DataFrame(pay_rows)
    pay.to_csv(P.OUT_TAB / "gp_payoff_ideal_nadir.csv", index=False)
    chg = pd.concat(chg, ignore_index=True)
    chg.to_csv(P.OUT_TAB / "gp_route_changes.csv", index=False)
    plots.gp_change_figure(res[res.type != "evaluation"], P.OUT_FIG / "gp_pct_change.png", gp_cfg["report_alpha"])
    _write_report(res, ach, pay, chg, gp_cfg)
    log.info("stage 4 done: %d scenario solves, all lexicographic checks passed",
             int((res.type != "evaluation").sum()))
    return dict(results=res, achievement=ach, payoff=pay, changes=chg)


def _write_report(res, ach, pay, chg, gp_cfg):
    from src.stage1 import _md_table
    a = gp_cfg["report_alpha"]
    r = res[np.isclose(res.alpha, a)]
    cols = ["scenario", "fmax_mode", "Z1", "Z2", "Z3", "fleet_used", "mean_wait_min", "equity_excess_min",
            "pct_Z1", "pct_Z2", "pct_Z3", "status", "wall_s"]
    ac = ach[np.isclose(ach.alpha, a)][["scenario", "fmax_mode", "goal", "priority", "target", "achieved",
                                        "unwanted_dev", "met", "best_possible", "reason_if_unmet"]]
    pa = pay[np.isclose(pay.alpha, a)]
    unmet = ach[~ach.met].groupby(["goal", "reason_if_unmet"]).size().reset_index(name="n_runs")
    ch_md = []
    for (sc, mode), g in chg.groupby(["scenario", "fmax_mode"], sort=False):
        if mode != "relaxed":
            continue
        ch_md.append(f"\n**{sc} (f_max relaxed)**\n")
        ch_md.append(_md_table(g[["direction", "route_no", "x0", "x_new", "delta", "ref_period", "headway_base",
                                  "headway_new", "reason_type", "reason"]], ".0f"))
    alpha_tab = res[res.type != "evaluation"].pivot_table(index=["fmax_mode", "scenario"], columns="alpha",
                                                          values="pct_Z3").round(1).reset_index()
    alpha_tab.columns = [str(c) for c in alpha_tab.columns]
    txt = f"""# Stage 4: Goal programming with priorities

> **Synthetic demand, illustrative.** Targets are relative to the published baseline evaluated with the same α.

Targets: G1 waiting Z1 ≤ (1 − {gp_cfg['kappa1']})·baseline; G2 unserved Z3 = 0;
G3 vehicle-km Z2 ≤ (1 − {gp_cfg.get('kappa3', 0.0)})·baseline;
G4 headways ≤ caps (60/90/60 min). The fleet limit (B_eff = {P.ModelConfig().B_eff}) and the frequency-fleet link are hard.
Scenarios come from `config/gp_scenarios.json`.

## Results at α = {a:g}
{_md_table(r[cols], '.1f')}

![GP % change](figures/gp_pct_change.png)

## Goal achievement at α = {a:g}
{_md_table(ac, '.1f')}

**Goals not met, counted over all runs (scenarios × α × f_max modes):**
{_md_table(unmet, '.0f')}

## Ideal and nadir (payoff table at α = {a:g})
Each objective was minimised alone, with a 1e-4 normalised tie-break on the others. The ideal is the diagonal;
the nadir is the worst value of each objective across those single-objective optima.
{_md_table(pa.drop(columns=["alpha"]), '.1f')}

## Z3 % change vs baseline across α
{_md_table(alpha_tab, '.1f')}

## Route-level changes (α = {a:g}, relaxed f_max; all modes in `outputs/tables/gp_route_changes.csv`)
Route fleet = max over periods of x_rt. Headways are shown for the period that sets the route's bus count (ref_period).
"Demand" reasons come from baseline load and waiting; "supply" reasons come from buses vs cycle time.
{chr(10).join(ch_md)}

## Lexicographic check
For every preemptive run, the final schedule's deviation at each priority level is ≤ the value locked at that level.
Status: {'PASS for all runs' if res.lex_ok.dropna().all() else 'FAILED (see gp_results.csv)'}.
"""
    (P.OUT / "gp_report.md").write_text(txt, encoding="utf-8")
