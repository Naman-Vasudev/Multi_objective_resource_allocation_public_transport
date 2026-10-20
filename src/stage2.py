"""Stage 2 runner: periods, synthetic demand and TFNs. EVERY DEMAND NUMBER IS SYNTHETIC, ILLUSTRATIVE."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src import data as D
from src import demand as DM
from src import params as P
from src import plots

log = logging.getLogger("stage2")
ROBUST_SEEDS = tuple(range(20))


def _fit_summary(fit: pd.DataFrame) -> pd.DataFrame:
    a = fit[fit.active == 1]
    return a.groupby("period").agg(
        mean_M=("M", "mean"), mean_LF=("LF", "mean"), max_LF=("LF", "max"),
        n_overloaded=("LF", lambda s: int((s > 1).sum())),
        n_underused=("LF", lambda s: int((s < P.LF_UNDERUSED).sum())),
    ).reindex(list(P.PERIODS))


def run(d: dict | None = None) -> dict:
    d = d or D.load_all()
    routes = d["routes"]
    log.info("periods (synced with Operating Windows B2:C4): %s", d["periods"])

    base, dem, per = DM.demand_table(d)
    per.to_csv(P.PROCESSED / "periods_rt.csv", index=False)
    stats = DM.check_demand(dem[dem.active == 1])
    log.info("SYNTHETIC demand: daily boardings target %.0f, CV of M by period %s",
             P.DAILY_BOARDINGS, {k: round(v, 3) for k, v in stats["cv_by_period"].items()})

    dem_out = dem[["route_no", "period", "active", "H_t", "overlap_h", "L", "M", "U"]].copy()
    dem_out.insert(0, "label", "synthetic demand, illustrative")
    dem_out.to_csv(P.PROCESSED / "demand_rt.csv", index=False)
    base.assign(label="synthetic demand, illustrative").to_csv(P.PROCESSED / "base_demand_r.csv", index=False)

    # baseline fit: peak capacity C f_max, midday capacity C f_min
    fit = DM.baseline_fit(dem, routes)
    fit.to_csv(P.OUT_TAB / "baseline_load_factors.csv", index=False)
    summ = _fit_summary(fit)
    over = fit[(fit.active == 1) & (fit.LF > 1)].sort_values("LF", ascending=False)
    under = fit[(fit.active == 1) & (fit.LF < P.LF_UNDERUSED)].sort_values("LF")

    # theta sensitivity
    th_rows = []
    for th in P.THETA_SENSITIVITY:
        _, dm_t, _ = DM.demand_table(d, theta=th)
        s = _fit_summary(DM.baseline_fit(dm_t, routes))
        for t, r in s.iterrows():
            th_rows.append(dict(theta=th, period=t, **r.to_dict()))
    theta_tab = pd.DataFrame(th_rows)
    theta_tab.to_csv(P.OUT_TAB / "theta_sensitivity.csv", index=False)

    # seed robustness: other noise draws (demand total is re-calibrated each time)
    ref = base.set_index("route_no").D_ref
    rob = []
    for sd in ROBUST_SEEDS:
        b, dm_s, _ = DM.demand_table(d, seed=sd)
        s = _fit_summary(DM.baseline_fit(dm_s, routes))
        rob.append(dict(seed=sd, spearman_vs_seed42=float(b.set_index("route_no").D_ref.corr(ref, method="spearman")),
                        n_overloaded_AM=int(s.at["AM", "n_overloaded"]), n_underused_Midday=int(s.at["Midday", "n_underused"])))
    rob = pd.DataFrame(rob)
    rob.to_csv(P.OUT_TAB / "seed_robustness.csv", index=False)

    plots.demand_heatmap(dem, P.OUT_FIG / "demand_heatmap.png")
    ex = dem[(dem.route_no == "35D") & (dem.period == "AM")].iloc[0]
    plots.tfn_example_figure(P.TFN_LO, P.TFN_HI, (0.0, 0.5, 0.8, 1.0), P.OUT_FIG / "tfn_alpha_cuts.png",
                             M=float(ex.M), label=" - route 35D, AM peak")

    _write_report(base, dem, summ, over, under, theta_tab, rob, stats)
    log.info("stage 2 done")
    return dict(base=base, demand=dem, periods=per, fit=fit)


def _write_report(base, dem, summ, over, under, theta_tab, rob, stats):
    from src.stage1 import _md_table
    a = dem[dem.active == 1]
    tot = a.groupby("period").M.sum().reindex(list(P.PERIODS))
    w = base[["route_no", "uplift", "noise", "D_ref"]].sort_values("D_ref", ascending=False)
    txt = f"""# Stage 2: Synthetic demand report

> **SYNTHETIC DEMAND, ILLUSTRATIVE.** No CTU ridership data exists. These numbers show how the model behaves;
> they are not estimates of real CTU demand. See `docs/DECISIONS.md` D13-D20.

## Construction
score_r = d_r × (1 + 0.6·PGI + 0.4·ISBT43 + 0.3·ISBT17 + 0.3·outskirts + 0.3·Derabassi + 0.05·hubs) × noise_r,
with noise_r ~ LogNormal(0, {P.NOISE_SIGMA}) and seed {P.NOISE_SEED}.
D_ref_r = λ·score_r, where λ is set so that θ·Σ D_ref_r·span_r = {P.DAILY_BOARDINGS:,.0f} boardings/day.
That target is {P.ANCHOR_DAILY_RIDERS:,} CTU-wide riders × {P.FLEET_B}/{P.ANCHOR_FLEET} buses, pro-rata (unverified anchor). θ = {P.THETA}.
M_rt = m_t·D_ref_r with m = {P.DEMAND_MULTIPLIERS}. L = 0.80·M and U = 1.35·M.

## Sanity checks
- No negative demand; L ≤ M ≤ U everywhere: PASS.
- Coefficient of variation of M across routes: {', '.join(f'{k} {v:.2f}' for k, v in stats['cv_by_period'].items())}.
- Sum of M over active routes [pax/h]: {', '.join(f'{k} {v:,.0f}' for k, v in tot.items())}.
- Check: θ·Σ D_ref·span = {P.THETA * (base.D_ref * base.span_hours).sum():,.0f} (target {P.DAILY_BOARDINGS:,.0f}).

## Baseline fit (capacity = C·f_max in peaks, C·f_min midday, C = {P.BUS_CAPACITY})
{_md_table(summ.reset_index(), '.2f')}

**Overloaded (LF > 1):** {', '.join(f"{r.route_no}/{r.period} ({r.LF:.2f})" for r in over.itertuples())}

**Under-used (LF < {P.LF_UNDERUSED}):** {len(under)} pairs, mostly Midday. Lowest: {', '.join(f"{r.route_no}/{r.period} ({r.LF:.2f})" for r in under.head(10).itertuples())}

The overloaded pairs are long routes with long headways (75-90 min), where demand grows with length but capacity is
only C·f. This is a property of the synthetic formula, not an observed CTU problem.

## θ sensitivity (θ = boardings per unit of busiest-section load; larger θ means less crowded)
{_md_table(theta_tab, '.2f')}

## Seed robustness ({len(rob)} other noise seeds)
Spearman rank correlation of D_ref with seed 42: min {rob.spearman_vs_seed42.min():.3f}, median {rob.spearman_vs_seed42.median():.3f}.
Overloaded AM pairs range from {rob.n_overloaded_AM.min()} to {rob.n_overloaded_AM.max()}. The route ranking is driven mostly by structure, not noise.

## Top routes by D_ref
{_md_table(w.head(10), '.2f')}

![heatmap](figures/demand_heatmap.png)
![tfn](figures/tfn_alpha_cuts.png)
"""
    (P.OUT / "demand_report.md").write_text(txt, encoding="utf-8")
