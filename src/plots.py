"""Figures. Palette: validated categorical slots 1-3 (blue, orange, aqua), light surface."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # file output only, no window
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src import params as P  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
SERIES = {"S1": "#2a78d6", "S2": "#eb6834", "S3": "#1baf7a"}


def save_fig(fig, path, **kw) -> None:
    """Save a figure robustly: write a temp file, then atomically replace the target, retrying while a sync
    client (OneDrive) briefly locks the old file."""
    import os
    import time
    from pathlib import Path
    path = Path(path)
    tmp = path.with_name(path.stem + ".tmp" + path.suffix)
    fig.savefig(tmp, **kw)
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except OSError:
            time.sleep(0.5)
    raise OSError(f"could not replace {path} (file locked)")


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _sched_color(name: str) -> str:
    if name.startswith("Baseline"):
        return INK
    if name.startswith("KNEE"):
        return SERIES["S3"]
    if "ROBUST" in name:
        return "#eda100"          # categorical slot 4 (yellow); always shown with a text label
    return SERIES["S2"] if "α=0)" in name else SERIES["S1"]


def _title(fig, text, sub=None):
    fig.suptitle(f"{text} {P.SYNTHETIC_LABEL}", x=0.01, ha="left", fontsize=11, color=INK)
    if sub:
        fig.text(0.01, 0.925, sub, fontsize=8, color=INK_2)


def sim_tradeoff_bars(trade: pd.DataFrame, key: dict, path) -> None:
    """Small multiples: % change vs baseline per metric (one panel each), one bar per optimised schedule."""
    t = trade[trade.schedule != "Baseline"].reset_index(drop=True)   # peak baseline stays: its % shows the gap
    fig, axes = plt.subplots(1, len(key), figsize=(15, 5.2), sharey=True, facecolor=SURFACE)
    y = np.arange(len(t))
    for ax, (k, lab) in zip(axes, key.items()):
        _style(ax)
        ax.yaxis.grid(False)
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
        ax.barh(y, t[f"pct_{k}"], color=[_sched_color(s) for s in t.schedule], height=0.62,
                edgecolor=SURFACE, linewidth=2, zorder=2)
        ax.axvline(0, color=INK, linewidth=1, zorder=3)
        ax.set_title(lab, fontsize=9, color=INK, loc="left")
        ax.set_xlabel("% vs baseline", fontsize=8, color=INK_2)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(t.schedule, fontsize=8, color=INK_2)
    axes[0].invert_yaxis()
    _title(fig, "Simulated trade-offs: % change vs published baseline (lower is better)",
           "Blue: optimised at α = 0.5; orange: α = 0; yellow: robust variant; aqua: knee of the Pareto front. "
           "Means over 2000 demand scenarios.")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    save_fig(fig, path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def sim_wait_vs_vkm(trade: pd.DataFrame, path) -> None:
    """Expected wait vs vehicle-km; marker area proportional to mean overflow."""
    fig, ax = plt.subplots(figsize=(9, 6), facecolor=SURFACE)
    _style(ax)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    size = 40 + 600 * trade.overflow_pax / trade.overflow_pax.max()
    ax.scatter(trade.vehicle_km, trade.mean_wait_min, s=size, c=[_sched_color(s) for s in trade.schedule],
               alpha=0.85, edgecolors=SURFACE, linewidths=2, zorder=3)
    for r in trade.itertuples():
        ax.annotate(r.schedule, (r.vehicle_km, r.mean_wait_min), xytext=(8, 4), textcoords="offset points",
                    fontsize=7.5, color=INK)
    ax.set_xlabel("vehicle-km per day", fontsize=9, color=INK_2)
    ax.set_ylabel("expected wait per passenger [min]", fontsize=9, color=INK_2)
    ax.ticklabel_format(style="plain", useOffset=False, axis="x")
    _title(fig, "Expected wait vs vehicle-km (marker area = mean overflow)",
           "Lower-left is better on both axes; smaller markers mean less crowding.")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    save_fig(fig, path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def sim_overflow_box(samples: dict, thr: float, path) -> None:
    """Distribution of the overflow share of demand per schedule across scenarios."""
    names = list(samples)
    fig, ax = plt.subplots(figsize=(9.5, 5.5), facecolor=SURFACE)
    _style(ax)
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    bp = ax.boxplot([100 * samples[n] for n in names], vert=False, whis=(5, 95), showfliers=False,
                    patch_artist=True, widths=0.55)
    for patch, n in zip(bp["boxes"], names):
        patch.set_facecolor(_sched_color(n)); patch.set_alpha(0.75); patch.set_edgecolor(SURFACE)
    for k in ("whiskers", "caps", "medians"):
        for line in bp[k]:
            line.set_color(INK_2)
    ax.axvline(100 * thr, color=INK, linewidth=1.2, linestyle="--")
    ax.text(100 * thr, len(names) + 0.6, f" {thr:.0%} threshold", fontsize=8, color=INK, va="center")
    ax.set_yticks(range(1, len(names) + 1))
    ax.set_yticklabels(names, fontsize=8, color=INK_2)
    ax.invert_yaxis()
    ax.set_xlabel("overflow as % of daily demand", fontsize=9, color=INK_2)
    _title(fig, "Overflow risk across 2000 demand scenarios", "Box = 25-75%, whiskers = 5-95%.")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    save_fig(fig, path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def tornado(oat: pd.DataFrame, alpha: pd.DataFrame, path) -> None:
    """Tornado on the policy's expected-wait improvement vs baseline; infeasible ends are labelled, not drawn."""
    base = oat[(oat.factor == "demand level") & (oat.value == 1.0)].wait_improvement_pct.iloc[0]
    spec = [("demand level", 0.8, 1.2, "demand ×"), ("capacity C", 50, 80, "C ="), ("speed v", 18, 26, "v ="),
            ("spare ratio s", 0.0, 0.2, "s ="), ("layover", 0.05, 0.15, "layover =")]
    rows = []
    for f_, lo, hi, lab in spec:
        g = oat[oat.factor == f_].set_index("value")
        rows.append((f_, lab, lo, hi, g.loc[lo], g.loc[hi]))
    ga = alpha.set_index("alpha")
    rows.append(("alpha", "α =", 0.0, 1.0, ga.loc[0.0], ga.loc[1.0]))

    def val(r):
        return r.wait_improvement_pct if bool(r.feasible) else None

    rows.sort(key=lambda r: -max(abs((val(r[4]) if val(r[4]) is not None else base) - base),
                                 abs((val(r[5]) if val(r[5]) is not None else base) - base)))
    fig, ax = plt.subplots(figsize=(9.5, 5), facecolor=SURFACE)
    _style(ax)
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    for j, (f_, lab, lo, hi, rlo, rhi) in enumerate(rows):
        # upper half of the row = low value (blue), lower half = high value (orange): labels never collide
        for r, v, c, dy in ((rlo, lo, SERIES["S1"], -0.17), (rhi, hi, SERIES["S2"], 0.17)):
            w = val(r)
            y = j + dy
            if w is None:
                ax.text(base + 0.05, y, f"{lab} {v:g}: infeasible", ha="left", va="center", fontsize=8,
                        color=INK_2, style="italic")
                continue
            ax.barh(y, w - base, left=base, color=c, height=0.3, edgecolor=SURFACE, linewidth=1.5, zorder=2)
            ax.text(w + (0.05 if w >= base else -0.05), y, f"{lab} {v:g}  ({w:.2f}%)",
                    ha="left" if w >= base else "right", va="center", fontsize=8, color=INK)
    ax.axvline(base, color=INK, linewidth=1.2)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows], fontsize=9, color=INK_2)
    ax.invert_yaxis()
    ax.set_xlabel(f"expected-wait improvement vs baseline [%] (base case {base:.2f}%)", fontsize=9, color=INK_2)
    xs = [val(r) for row in rows for r in row[4:] if val(r) is not None] + [base]
    pad = max(0.6, (max(xs) - min(xs)) * 0.45)
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    _title(fig, f"Sensitivity of the wait improvement, policy {P.SIM_POLICY}",
           "Blue (upper bar): low value of the factor; orange (lower bar): high value. One factor at a time.")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    save_fig(fig, path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def price_of_robustness(alpha: pd.DataFrame, path) -> None:
    """Policy vs baseline across alpha: P(overflow > 5%), vehicle-km and expected wait (three panels, no dual axis)."""
    a = alpha[alpha.feasible.astype(bool)].sort_values("alpha")
    spec = [("P_overflow_gt_5pct", "P(overflow > 5% of demand)", 100, "%"),
            ("vehicle_km", "vehicle-km per day", 1, ""), ("mean_wait_min", "expected wait [min]", 1, "")]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.3), facecolor=SURFACE)
    for ax, (k, lab, mult, unit) in zip(axes, spec):
        _style(ax)
        ax.plot(a.alpha, mult * a[f"opt_{k}"], color=SERIES["S1"], linewidth=2, marker="o", markersize=7,
                label=f"{P.SIM_POLICY} (re-optimised at each α)")
        ax.plot(a.alpha, mult * a[f"base_{k}"], color=INK_2, linewidth=1.5, linestyle="--", label="published baseline")
        ax.set_xlabel("α (1 = plan for modal demand, 0 = plan for upper bound U)", fontsize=8, color=INK_2)
        ax.set_title(lab, fontsize=9, color=INK, loc="left")
        ax.ticklabel_format(style="plain", useOffset=False, axis="y")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=2, frameon=False, fontsize=9, labelcolor=INK)
    _title(fig, "Price of robustness: choosing α")
    fig.tight_layout(rect=(0, 0.07, 1, 0.93))
    save_fig(fig, path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def fleet_reduction(fleet: pd.DataFrame, path) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor=SURFACE)
    _style(ax)
    xs = np.arange(len(fleet))
    for j, r in enumerate(fleet.itertuples()):
        if bool(r.feasible):
            ax.bar(j, r.wait_improvement_pct, color=SERIES["S1"], width=0.55, edgecolor=SURFACE, linewidth=2, zorder=2)
            ax.text(j, r.wait_improvement_pct, f"{r.wait_improvement_pct:+.2f}%", ha="center",
                    va="bottom" if r.wait_improvement_pct >= 0 else "top", fontsize=9, color=INK)
        else:
            ax.text(j, 0, "infeasible:\nminimum frequencies\nneed more buses", ha="center", va="bottom",
                    fontsize=8, color=INK_2)
    ax.axhline(0, color=INK, linewidth=1)
    ax.set_xticks(xs)
    ax.set_xticklabels([f"B_eff = {r.B_eff:.0f}\n(cut {r.fleet_cut:.0%})" for r in fleet.itertuples()],
                       fontsize=8, color=INK_2)
    ax.set_ylabel("expected-wait improvement vs baseline [%]", fontsize=9, color=INK_2)
    _title(fig, f"Fleet reduction: does {P.SIM_POLICY} still beat the baseline (385 buses)?")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save_fig(fig, path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def out_of_sample(oos: pd.DataFrame, path) -> None:
    piv = oos.pivot_table(index="schedule", columns="sample", values="P_overflow_gt_5pct", sort=False)
    fig, ax = plt.subplots(figsize=(9.5, 5.5), facecolor=SURFACE)
    _style(ax)
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    y = np.arange(len(piv))
    ax.barh(y - 0.2, 100 * piv["in-sample"], height=0.38, color=SERIES["S1"], label="in-sample (design distribution)",
            edgecolor=SURFACE, linewidth=2)
    ax.barh(y + 0.2, 100 * piv["out-of-sample (wider)"], height=0.38, color=SERIES["S2"],
            label=f"out-of-sample (spreads ×{P.OOS_WIDEN}, shock sd {P.OOS_SHOCK_SD})", edgecolor=SURFACE, linewidth=2)
    ax.set_yticks(y)
    ax.set_yticklabels(piv.index, fontsize=8, color=INK_2)
    ax.invert_yaxis()
    ax.set_xlabel("P(overflow > 5% of demand) [%]", fontsize=9, color=INK_2)
    ax.legend(loc="lower right", frameon=False, fontsize=8, labelcolor=INK)
    _title(fig, "Out-of-sample test: overflow risk when demand is more uncertain than planned")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save_fig(fig, path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def route_lf(rt: pd.DataFrame, policy: str, path, k: int = 20) -> None:
    """Dumbbell: 95th-percentile peak load factor per route, baseline vs one policy (top-k routes by baseline)."""
    b = rt[rt.schedule == "Baseline"].set_index("route_no").p95_peak_LF
    p = rt[rt.schedule == policy].set_index("route_no").p95_peak_LF
    top = b.sort_values(ascending=False).head(k).index
    fig, ax = plt.subplots(figsize=(8, 7), facecolor=SURFACE)
    _style(ax)
    ax.yaxis.grid(False)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    y = np.arange(len(top))
    ax.hlines(y, p.loc[top], b.loc[top], color=GRID, linewidth=2, zorder=1)
    ax.scatter(b.loc[top], y, color=INK_2, s=40, label="baseline", zorder=3)
    ax.scatter(p.loc[top], y, color=SERIES["S1"], s=55, label=policy, zorder=4)
    ax.axvline(1.0, color=INK, linewidth=1, linestyle="--")
    ax.set_yticks(y)
    ax.set_yticklabels(top, fontsize=8, color=INK_2)
    ax.invert_yaxis()
    ax.set_xlabel("95th-percentile peak load factor (1 = full)", fontsize=9, color=INK_2)
    ax.legend(loc="lower right", frameon=False, fontsize=8, labelcolor=INK)
    _title(fig, f"Most crowded routes: baseline vs {policy}")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save_fig(fig, path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


PARETO_STYLE = {
    "eps": dict(color=SERIES["S1"], marker="o", s=46, label="ε-constraint (AUGMECON, exact)", zorder=4),
    "nsga": dict(color=SERIES["S2"], marker="^", s=22, label="NSGA-II (5 seeds, non-dominated union)", zorder=3,
                 alpha=0.85),
    "gp": dict(color=SERIES["S3"], marker="D", s=60, label="goal-programming solutions", zorder=5,
               edgecolors=SURFACE, linewidths=1.5),
    "base": dict(color=INK, marker="*", s=150, label="published baseline (breaks fleet limit)", zorder=6),
}


def pareto_figures(eps: pd.DataFrame, nsga: pd.DataFrame, gp: pd.DataFrame, base: dict, path2d, path3d) -> None:
    """2-D projections (Z1-Z2, Z1-Z3, Z2-Z3) and a 3-D scatter of both fronts, GP points and the baseline."""
    lab = {"Z1": "Z1 waiting [pax·min/h]", "Z2": "Z2 vehicle-km [veh-km/day]", "Z3": "Z3 unserved [pax/day]"}
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.8), facecolor=SURFACE)
    for ax, (a, b) in zip(axes, (("Z1", "Z2"), ("Z1", "Z3"), ("Z2", "Z3"))):
        _style(ax)
        ax.xaxis.grid(True, color=GRID, linewidth=0.8)
        ax.scatter(nsga[a], nsga[b], **PARETO_STYLE["nsga"])
        ax.scatter(eps[a], eps[b], **PARETO_STYLE["eps"], edgecolors=SURFACE, linewidths=1)
        ax.scatter(gp[a], gp[b], **PARETO_STYLE["gp"])
        ax.scatter([base[a]], [base[b]], **PARETO_STYLE["base"])
        ax.set_xlabel(lab[a], fontsize=9, color=INK_2)
        ax.set_ylabel(lab[b], fontsize=9, color=INK_2)
        ax.ticklabel_format(style="plain", useOffset=False)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=9, labelcolor=INK)
    fig.suptitle(f"Pareto front projections, f_max relaxed, α = 0.5 {P.SYNTHETIC_LABEL}", x=0.01, ha="left",
                 fontsize=11, color=INK)
    fig.text(0.01, 0.905, "All objectives are minimised. 2-D projections of a 3-objective front: a point can look "
             "dominated here and still be efficient in 3-D.", fontsize=8, color=INK_2)
    fig.tight_layout(rect=(0, 0.08, 1, 0.9))
    save_fig(fig, path2d, dpi=160, facecolor=SURFACE)
    plt.close(fig)

    fig = plt.figure(figsize=(8, 6.5), facecolor=SURFACE)
    ax = fig.add_subplot(projection="3d")
    ax.set_facecolor(SURFACE)
    for key, df in (("nsga", nsga), ("eps", eps), ("gp", gp)):
        st = {k: v for k, v in PARETO_STYLE[key].items() if k != "zorder"}
        ax.scatter(df.Z1, df.Z2, df.Z3, **st, depthshade=False)
    st = {k: v for k, v in PARETO_STYLE["base"].items() if k != "zorder"}
    ax.scatter([base["Z1"]], [base["Z2"]], [base["Z3"]], **st, depthshade=False)
    for axis, k in ((ax.set_xlabel, "Z1"), (ax.set_ylabel, "Z2"), (ax.set_zlabel, "Z3")):
        axis(lab[k], fontsize=8, color=INK_2)
    ax.tick_params(labelsize=7, colors=INK_2)
    ax.view_init(elev=22, azim=-58)
    ax.legend(loc="upper left", fontsize=8, frameon=False, labelcolor=INK)
    ax.set_title(f"Pareto front in 3-D {P.SYNTHETIC_LABEL}", loc="left", fontsize=10, color=INK)
    fig.tight_layout()
    save_fig(fig, path3d, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def gp_change_figure(res: pd.DataFrame, path, alpha: float) -> None:
    """Grouped bars: % change vs published baseline of Z1, Z2, Z3 per GP scenario; one panel per f_max mode."""
    modes = list(dict.fromkeys(res.fmax_mode))
    scen = list(dict.fromkeys(res.scenario))
    series = [("pct_Z1", "Z1 waiting"), ("pct_Z2", "Z2 vehicle-km"), ("pct_Z3", "Z3 unserved")]
    colors = [SERIES["S1"], SERIES["S2"], SERIES["S3"]]
    sub = res[np.isclose(res.alpha, alpha)]
    lo = min(-5.0, sub[[c for c, _ in series]].min().min() * 1.15)
    hi = max(5.0, sub[[c for c, _ in series]].max().max() * 1.15)
    fig, axes = plt.subplots(1, len(modes), figsize=(11, 4.6), sharey=True, facecolor=SURFACE)
    axes = np.atleast_1d(axes)
    w = 0.26
    for ax, mode in zip(axes, modes):
        _style(ax)
        s = sub[sub.fmax_mode == mode].set_index("scenario").loc[scen]
        xs = np.arange(len(scen))
        for j, ((col, lab), c) in enumerate(zip(series, colors)):
            ax.bar(xs + (j - 1) * (w + 0.02), s[col], width=w, color=c, edgecolor=SURFACE, linewidth=2,
                   label=lab, zorder=2)
        ax.axhline(0, color=INK, linewidth=1, zorder=3)
        ax.set_xticks(xs)
        ax.set_xticklabels(scen, fontsize=8, color=INK_2)
        ax.set_ylim(lo, hi)
        ax.set_title(f"f_max: {mode}", loc="left", fontsize=10, color=INK)
    axes[0].set_ylabel("% change vs published baseline (lower is better)", fontsize=9, color=INK_2)
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=3, frameon=False, fontsize=9, labelcolor=INK)
    fig.suptitle(f"Goal-programming scenarios vs baseline, α = {alpha:g} {P.SYNTHETIC_LABEL}",
                 x=0.01, ha="left", fontsize=11, color=INK)
    fig.tight_layout(rect=(0, 0.07, 1, 0.95))
    save_fig(fig, path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def demand_heatmap(dem: pd.DataFrame, path) -> None:
    """Heatmap of modal demand M [pax/h] by route (rows, sorted by AM) and period. Grey = inactive."""
    piv = dem.pivot(index="route_no", columns="period", values="M")[list(P.PERIODS)]
    act = dem.pivot(index="route_no", columns="period", values="active")[list(P.PERIODS)]
    order = piv.sort_values(["AM", "PM"], ascending=False).index
    piv, act = piv.loc[order], act.loc[order]
    vals = np.ma.masked_where(act.to_numpy() == 0, piv.to_numpy())
    cmap = matplotlib.colormaps["Blues"].copy()
    cmap.set_bad("#e4e3df")
    fig, ax = plt.subplots(figsize=(5.2, 13), facecolor=SURFACE)
    im = ax.imshow(vals, aspect="auto", cmap=cmap, vmin=0, interpolation="nearest")
    ax.set_xticks(range(len(P.PERIODS)))
    ax.set_xticklabels([f"{t}\n{s:02.0f}-{e:02.0f} h" for t, (s, e) in P.PERIODS.items()], fontsize=8, color=INK_2)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, fontsize=6.5, color=INK_2)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    cb = fig.colorbar(im, ax=ax, fraction=0.05, pad=0.03)
    cb.set_label("modal demand M [pax/h, busiest section]", fontsize=8, color=INK_2)
    cb.ax.tick_params(labelsize=7, colors=INK_2)
    cb.outline.set_visible(False)
    ax.set_title(f"Modal demand by route and period\n{P.SYNTHETIC_LABEL}", loc="left", fontsize=10, color=INK)
    fig.text(0.02, 0.005, "Grey: route not running in that period. Sorted by AM demand.", fontsize=7, color=INK_2)
    fig.tight_layout(rect=(0, 0.01, 1, 1))
    save_fig(fig, path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def tfn_example_figure(lo: float, hi: float, alphas, path, M: float = 1.0, label: str = "") -> None:
    """One triangular fuzzy number (L, M, U) with horizontal alpha-cuts; x in units of M unless M given."""
    L, U = (1 - lo) * M, (1 + hi) * M
    fig, ax = plt.subplots(figsize=(7.5, 4.2), facecolor=SURFACE)
    _style(ax)
    ax.plot([L, M, U], [0, 1, 0], color=SERIES["S1"], linewidth=2, zorder=3)
    for a in alphas:
        lo_a, up_a = L + a * (M - L), U - a * (U - M)
        ax.plot([lo_a, up_a], [a, a], color=INK_2, linewidth=1, zorder=2)
        ax.plot([up_a], [a], marker="o", markersize=6, color=SERIES["S2"], zorder=4)
        ax.text(up_a + 0.012 * M, a, f"α={a:g}: upper = {up_a / M:.3f}·M", va="center", fontsize=8, color=INK)
    for x, name in ((L, f"L = {1 - lo:.2f}·M"), (M, "M"), (U, f"U = {1 + hi:.2f}·M")):
        ax.text(x, -0.09, name, ha="center", va="top", fontsize=8, color=INK_2)
    ax.set_ylim(-0.18, 1.12)
    ax.set_xlim(L - 0.08 * M, U + 0.32 * M)
    ax.set_xticks([])
    ax.set_ylabel("membership μ(D)", color=INK_2, fontsize=9)
    ax.set_xlabel("demand D, relative to modal demand M" if M == 1.0 else "demand D [pax/h]",
                  color=INK_2, fontsize=9)
    ax.set_title(f"Triangular fuzzy demand and α-cuts{label} {P.SYNTHETIC_LABEL}",
                 loc="left", fontsize=10, color=INK)
    fig.text(0.01, 0.01, f"lo = {lo:.2f}, hi = {hi:.2f}. Orange dots: upper α-cut D_α = U − α(U − M), "
             "used by the optimisation.", fontsize=8, color=INK_2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    save_fig(fig, path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def calibration_figure(grid: pd.DataFrame, labels: dict, path) -> None:
    """Bars: N_need at f_mid [buses] per scenario x speed, one panel per layover.

    Whiskers span N_need at f_min .. f_max. Line: fleet B. Band: 85-100% utilisation.
    """
    lays = sorted(grid.layover_frac.unique())
    speeds = sorted(grid.v_kmh.unique())
    scen = ["S1", "S2", "S3"]
    fig, axes = plt.subplots(1, len(lays), figsize=(11, 4.8), sharey=True, facecolor=SURFACE)
    width = 0.26
    ymax = max(grid.N_need_fmax.max(), P.FLEET_B) * 1.18
    for ax, lay in zip(axes, lays):
        _style(ax)
        lo, hi = P.UTIL_BAND[0] * P.FLEET_B, P.UTIL_BAND[1] * P.FLEET_B
        ax.axhspan(lo, hi, color="#efeee9", zorder=0)
        ax.axhline(P.FLEET_B, color=INK, linewidth=1.2, zorder=3)
        xr = len(speeds) - 0.5
        ax.text(xr, ymax * 0.985, f"B = {P.FLEET_B} buses (line)\n"
                f"shaded: {P.UTIL_BAND[0]:.0%}-{P.UTIL_BAND[1]:.0%} of B",
                ha="right", va="top", color=INK_2, fontsize=8)
        for i, sc in enumerate(scen):
            sub = grid[(grid.scenario == sc) & (grid.layover_frac == lay)].set_index("v_kmh").loc[speeds]
            x = np.arange(len(speeds)) + (i - 1) * (width + 0.02)
            ax.bar(x, sub.N_need_fmid, width=width, color=SERIES[sc], edgecolor=SURFACE, linewidth=2,
                   label=labels[sc], zorder=2)
            ax.vlines(x, sub.N_need_fmin, sub.N_need_fmax, color=INK_2, linewidth=1, zorder=4)
            for xi, n, top, ok in zip(x, sub.N_need_fmid, sub.N_need_fmax, sub.in_band):
                if ok:  # selective direct labels: only the in-band combinations, above the whisker
                    ax.text(xi, top + 6, f"{n:.0f}", ha="center", va="bottom", fontsize=8, color=INK)
        ax.set_xticks(np.arange(len(speeds)))
        ax.set_xticklabels([f"{v:.0f} km/h" for v in speeds])
        ax.set_title(f"Layover {lay:.0%} of running time", fontsize=10, color=INK, loc="left")
        ax.set_ylim(0, ymax)
    axes[0].set_ylabel("Buses needed at mid frequency, N_need", color=INK_2, fontsize=9)
    handles, labs = axes[0].get_legend_handles_labels()
    fig.legend(handles, labs, loc="lower center", ncol=3, frameon=False, fontsize=9, labelcolor=INK)
    fig.suptitle("Buses needed to run the published CTU timetable vs allocated fleet "
                 "(timetable only, no demand data)", x=0.01, ha="left", fontsize=11, color=INK)
    fig.text(0.01, 0.905, "Whiskers: range from lowest to highest published frequency.",
             fontsize=8, color=INK_2)
    fig.tight_layout(rect=(0, 0.08, 1, 0.9))
    save_fig(fig, path, dpi=160, facecolor=SURFACE)
    plt.close(fig)
