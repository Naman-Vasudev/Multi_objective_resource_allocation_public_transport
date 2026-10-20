"""Stage 1 runner: data audit + cycle-time calibration -> processed CSVs, tables, figure, report."""
from __future__ import annotations

import logging

import pandas as pd

from src import calibration as C
from src import data as D
from src import params as P
from src import plots

log = logging.getLogger("stage1")

# Analyst explanations for routes flagged under S2 at 22 km/h (layover 0% or 10%).
# Written after inspecting the data; if the data changes and a new route is flagged,
# the report says "NO NOTE - investigate" instead of silently reusing stale text.
ROUTE_NOTES = {
    "37": ("Night service (21:10-03:50), 32 km, 50 min headway, 2 buses. Two buses can run a 50 min "
           "headway on a 64 km round trip only at about 38 km/h (no layover). That speed is possible on empty "
           "night roads, but it is far above 22 km/h. The sheet also lists only one direction. "
           "Either night speed is much higher, or 32 km is already the round trip. Needs CTU confirmation."),
    "76": ("ISBT-17 to Kurali, 31 km, 30-40 min headway, 4 buses, only 2 via-stops listed: a suburban "
           "or highway run with few stops. It needs about 23 km/h (no layover) or 26 km/h (10% layover), "
           "which is believable for a route with so few stops. Explained by speed, not an error."),
    "40": ("ISBT-17 to Khizrabad, 30.8 km, 60 min headway, 3 buses. Short only once 10% layover is added "
           "(needs 22.6 km/h vs 22). A marginal case: a slightly faster suburban speed or a shorter layover "
           "explains it."),
}


def _md_table(df: pd.DataFrame, floatfmt: str = ".2f") -> str:
    """Minimal markdown table (avoids needing the 'tabulate' package)."""
    cols = list(df.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, float):
                cells.append(format(v, floatfmt))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def run() -> dict:
    for p in (P.PROCESSED, P.OUT_FIG, P.OUT_TAB, P.OUT_LOG):
        p.mkdir(parents=True, exist_ok=True)

    log.info("loading %s", P.RAW_XLSX)
    d = D.load_all()
    D.write_processed(d)
    routes = d["routes"]
    log.info("routes=%d  sum(x_base)=%d  sum(d_r)=%.1f km  loops=%d  stops=%d",
             len(routes), routes.x_base.sum(), routes.d_r_km.sum(), routes.is_loop.sum(), len(d["stops"]))
    for w in d["warnings"]:
        log.warning(w)

    # --- Model Variables check
    mvi = d["mv_issues"].copy()
    if len(mvi):
        mvi["abs_diff"] = [abs(float(a) - float(b)) if isinstance(a, (int, float)) and b is not None else None
                           for a, b in zip(mvi.excel, mvi.ours)]
        mvi["explanation"] = ["typed value rounded to 2 dp" if (x is not None and x < 0.005) else "INVESTIGATE"
                              for x in mvi.abs_diff]
    mvi.to_csv(P.OUT_TAB / "model_variables_check.csv", index=False)

    # --- calibration grid
    grid = C.scenario_grid(routes)
    grid.to_csv(P.OUT_TAB / "calibration_scenarios.csv", index=False)
    plots.calibration_figure(grid, C.SCENARIO_LABELS, P.OUT_FIG / "calibration_N_need.png")

    per = {}
    for sc in ("S1", "S2"):
        for v in P.SPEEDS_KMH:
            for lay in P.LAYOVER_FRACS:
                per[(sc, v, lay)] = C.per_route(routes, sc, v, lay)
    rec = per[("S2", P.DEFAULT_SPEED_KMH, P.DEFAULT_LAYOVER_FRAC)]
    rec.to_csv(P.OUT_TAB / "per_route_S2_v22_lay10.csv", index=False)

    flagged = {}
    for lay in P.LAYOVER_FRACS:
        pr = per[("S2", 22.0, lay)]
        flagged[lay] = pr[pr.x_base < pr.need_fmin - 1e-9]
    pd.concat([f.assign(layover_frac=lay) for lay, f in flagged.items()]).to_csv(
        P.OUT_TAB / "routes_short_S2_v22.csv", index=False)

    write_report(d, grid, per, flagged, mvi)
    log.info("stage 1 done")
    return dict(data=d, grid=grid, per=per, flagged=flagged)


def write_report(d, grid, per, flagged, mvi) -> None:
    routes = d["routes"]
    g = grid.copy()
    g["layover"] = g.layover_frac.map(lambda x: f"{x:.0%}")
    g["U = N/B"] = g.utilisation.map(lambda x: f"{x:.1%}")
    g["85-100%?"] = g.in_band.map({True: "**yes**", False: "no"})
    show = g[["scenario", "v_kmh", "layover", "N_need_fmin", "N_need_fmid", "N_need_fmax", "U = N/B", "85-100%?",
              "n_routes_x_lt_ceil_fmin", "n_routes_x_gt_ceil_fmax"]].rename(columns={
        "v_kmh": "v (km/h)", "N_need_fmin": "N @f_min", "N_need_fmid": "N @f_mid", "N_need_fmax": "N @f_max",
        "n_routes_x_lt_ceil_fmin": "#routes x<ceil(f_min·τ)", "n_routes_x_gt_ceil_fmax": "#routes x>ceil(f_max·τ)"})
    show["v (km/h)"] = show["v (km/h)"].map(lambda x: f"{x:.0f}")

    s2 = lambda v, l: grid[(grid.scenario == "S2") & (grid.v_kmh == v) & (grid.layover_frac == l)].iloc[0]  # noqa
    s3 = lambda v, l: grid[(grid.scenario == "S3") & (grid.v_kmh == v) & (grid.layover_frac == l)].iloc[0]  # noqa
    s1 = lambda v, l: grid[(grid.scenario == "S1") & (grid.v_kmh == v) & (grid.layover_frac == l)].iloc[0]  # noqa
    rec_row = s3(P.DEFAULT_SPEED_KMH, P.DEFAULT_LAYOVER_FRAC)
    v_389 = C.implied_uniform_speed(routes, "S2", 0.10, P.FLEET_B)
    v_389s = C.implied_uniform_speed(routes, "S2", 0.10, P.FLEET_B / (1 + P.SPARE_RATIO))
    am = C.am_peak_need(routes, "S2", 22.0, 0.10)
    not_am = routes[routes.active_am == 0]

    flag_md = []
    for lay, f in flagged.items():
        flag_md.append(f"\n**Layover {lay:.0%}:** {len(f)} route(s)\n")
        t = f[["route_no", "d_r_km", "x_base", "headway_min_hi", "f_min", "tau_h", "need_fmin",
               "v_needed_for_fmin_kmh", "service_type"]].rename(columns={
            "headway_min_hi": "longest headway (min)", "need_fmin": "f_min·τ", "tau_h": "τ (h)",
            "v_needed_for_fmin_kmh": "speed needed (km/h)"})
        flag_md.append(_md_table(t))
    notes_md = []
    all_flagged = sorted(set().union(*[set(f.route_no) for f in flagged.values()]))
    for rn in all_flagged:
        notes_md.append(f"- **Route {rn}.** {ROUTE_NOTES.get(rn, 'NO NOTE - investigate before using results.')}")

    pr_rec = per[("S2", 22.0, 0.10)]
    over = pr_rec[pr_rec.x_base > pr_rec.ceil_fmax]
    under = pr_rec[pr_rec.x_base < pr_rec.ceil_fmin]
    over_list = ", ".join(over.route_no)
    under_list = ", ".join(under.route_no)
    s1_over = per[("S1", 22.0, 0.0)]
    s1_over_n = int((s1_over.x_base > s1_over.ceil_fmax).sum())

    f = d["features"]
    top = f.sort_values("centrality_sum", ascending=False).head(8)[
        ["route_no", "n_stops", "centrality_sum", "centrality_mean", "n_hub_stops"]]
    n_hubs = int((d["stops"].n_routes_serving >= P.HUB_MIN_ROUTES).sum())
    fl = f.merge(routes[["route_no", "is_loop"]], on="route_no")
    rng = lambda s: f"{int(s.min())} to {int(s.max())}"  # noqa: E731
    fv_nonloop = rng(fl.n_stops_minus_via[~fl.is_loop])
    fv_loop = rng(fl.n_stops_minus_via[fl.is_loop])

    mv_note = ("All Model Variables values match our recomputation." if len(mvi) == 0 else
               f"{len(mvi)} cell(s) differ; see `outputs/tables/model_variables_check.csv`. Largest absolute "
               f"difference {mvi.abs_diff.max():.4f} dep/h. Every one is labelled "
               f"'{mvi.explanation.mode().iloc[0]}' (fields: {', '.join(sorted(mvi.field.unique()))}; "
               f"routes: {', '.join(sorted(mvi.route_no.unique()))}). The rounded values are typed into the sheet, "
               "not computed by formula. **We use the exact 60/headway everywhere.** tau = d/22 and x/tau match exactly.")

    warn_md = "\n".join(f"- {w}" for w in d["warnings"]) or "- none"

    txt = f"""# Stage 1: Data audit and cycle-time calibration

> **No passenger demand is used in this stage.** Every number below comes from the published CTU timetable
> (as on 25.07.2026) plus the clearly labelled assumptions in `docs/DECISIONS.md` (speed, layover, spares).
> This report does not claim any real CTU improvement.

Generated by `python run_all.py`. Source: `data/raw/CTU_Routes_Structured.xlsx`.

## 1. Data audit

| Check | Result |
|---|---|
| Routes (TOTAL and blank rows dropped) | {len(routes)} (expected {P.N_ROUTES}) |
| Sum of buses allocated, B | {routes.x_base.sum()} (expected {P.FLEET_B}) |
| Sum of route lengths | {routes.d_r_km.sum():.1f} km (expected {P.TOTAL_LENGTH_KM}) |
| PDF Verification rows marked OK | {(d['pdf'].match == 'OK').sum()} of {len(d['pdf'])} |
| Loop routes (origin = destination) | {int(routes.is_loop.sum())}: {', '.join(routes.route_no[routes.is_loop])} |
| Overnight services (last departure < first) | {int(routes.overnight.sum())}: {', '.join(routes.route_no[routes.overnight])} |
| First/last/span read from Excel cached values | {'yes' if d['ow_from_cache'] else 'NO: recomputed from typed time cells'} |
| Stops in Stop Coverage | {len(d['stops'])} (the brief said 651; the sheet has 649 stops plus 1 blank row and 1 note row) |

**Cross-checks that raised warnings:**
{warn_md}

These cross-checks found no discrepancies when the list above says "none":
- the Route Master operating-hours text matches the Operating Windows time cells;
- the Route Master headway text matches the Freq Min/Max columns;
- the origin = destination loop test matches the "Loop (single direction)" label;
- every Stop Coverage route count and buses-passing total matches the route table.

**Model Variables vs recomputation.** {mv_note}

**Frequency convention.** f_max = 60 / shortest headway and f_min = 60 / LONGEST headway. For example "15-30 min" gives
f_min = 2, f_max = 4 dep/h.

## 2. Calibration: buses needed vs fleet

N_need = Σ_r f_r · τ_r (buses = departures/hour × cycle hours). τ_r = L_r / v × (1 + layover), where L_r = d_r (S1)
or 2·d_r for non-loop routes (S2). S3 = S2 × (1 + {P.SPARE_RATIO:.0%} spares). B = {P.FLEET_B}.

{_md_table(show, '.1f')}

![N_need across scenarios](figures/calibration_N_need.png)

**Hand checks reproduced (also unit tests):** S1 at 22 km/h, no layover: {s1(22, 0)['N_need_fmid']:.1f} (expected ≈172).
S2 at 22 km/h, no layover: {s2(22, 0)['N_need_fmid']:.1f} (expected ≈310). S2 at 22 km/h, 10% layover: {s2(22, 0.1)['N_need_fmid']:.1f} (expected ≈340).

**Combinations giving 85-100% utilisation at baseline:**
{chr(10).join(f"- {r.scenario}, {r.v_kmh:.0f} km/h, layover {r.layover_frac:.0%}: N = {r.N_need_fmid:.1f}, U = {r.utilisation:.1%}, routes short at f_min = {r.n_routes_x_lt_ceil_fmin}" for r in grid[grid.in_band].itertuples())}

**Implied uniform speed.** Under S2 with 10% layover, the timetable uses exactly 389 buses at v = {v_389:.1f} km/h.
It uses 389 / 1.1 = {P.FLEET_B / 1.1:.1f} buses in service (the rest as spares) at v = {v_389s:.1f} km/h.

## 3. Routes where x_base < f_min · τ_r (S2, 22 km/h)
{chr(10).join(flag_md)}

"Speed needed" is the uniform speed at which the allocated buses exactly deliver the lowest published frequency.

**Explanations:**
{chr(10).join(notes_md)}

## 4. Integer check: x_base vs ceil(f·τ)

`x_base < ceil(f_min·τ)` means the route cannot run even its slowest published frequency with its own buses at the
assumed speed. `x_base > ceil(f_max·τ)` means it has more buses than its fastest published frequency needs.
The counts for every combination are in the table above. Read across scenarios:

- **S1 (d_r = full cycle) is implausible.** At 22 km/h, {s1_over_n} of 68 routes would hold more buses than needed
  even at their highest frequency, and only {s1(22, 0)['utilisation']:.0%} of the fleet would be in use. A transit
  operator does not leave about half its fleet idle. This is strong evidence that d_r is a one-way length.
- **S2 at 18 km/h** fills the fleet (with no layover) but leaves {s2(18, 0)['n_routes_x_lt_ceil_fmin']} routes unable to run their published
  minimum frequency, which contradicts the timetable CTU actually operates. 18 km/h is too slow as a network-wide speed.
- **S2 at 22 km/h with 10% layover** (recommended): {len(under)} route(s) short ({under_list}) and {len(over)} route(s) with
  surplus buses ({over_list}). Surplus buses are expected. They usually mean the route is slower than average (city
  core, ISBT and PGI approaches), has longer terminal layovers, runs extra short trips not in the headway
  (the sheet notes these for routes 20 and 242), or carries the depot's peak and spare buses. A route-level speed
  would remove most of these; that needs CTU data we do not have.

**Short-span and night routes.** {len(not_am)} routes are not active in the AM peak ({', '.join(not_am.route_no)};
{int(not_am.x_base.sum())} buses). If their buses were shared with day routes, the simultaneous requirement under S2 at 22 km/h with 10% layover would
be {am:.1f} instead of {s2(22, 0.1)['N_need_fmid']:.1f}. The difference is small, so the model treats route allocations as separate.

## 5. Stop-network features (from Stop Coverage)

`data/processed/route_features.csv`: n_stops, centrality_sum (sum over the route's stops of "routes serving",
counting the route itself), centrality_mean, n_hub_stops (stops served by ≥ {P.HUB_MIN_ROUTES} routes; {n_hubs} such
hubs in the network). n_stops − n_via_stops is {fv_nonloop} for non-loop routes, because Stop Coverage also
lists the terminals. For loop routes it is {fv_loop}: a loop starts and ends at one stop and can pass the same stop
twice, and Stop Coverage counts it once. The sheet's own caveat applies: stop names are verbatim, so "22/17" and "17/22"
may be the same junction. This is a first-pass coverage map, not a stop registry.

Top routes by centrality_sum:

{_md_table(top, '.2f')}

## 6. Recommendation (PENDING STUDENT CONFIRMATION)

Use **S2 distance reading + v = 22 km/h + 10% layover + 10% spares** (S3 at 22 km/h, 10%):
N_total = {rec_row.N_need_fmid:.1f} buses = {rec_row.utilisation:.1%} of B. Evidence:
1. It is in the 85-100% band, as an operator's baseline should be.
2. Among the in-band options it has the fewest per-route contradictions ({rec_row.n_routes_x_lt_ceil_fmin} routes), except S3 with
   no layover, which is physically unrealistic because drivers need terminal time.
3. It keeps the workbook's own 22 km/h assumption, so it is consistent with the existing sheet.
4. S1 leaves about half the fleet idle and over-allocates most routes, so it is rejected.

In the optimisation model this means τ_r = (2·d_r if non-loop else d_r) / 22 × 1.10 [h], with fleet constraint
Σ_r f_r · τ_r ≤ B / (1 + s) = {P.FLEET_B / (1 + P.SPARE_RATIO):.1f} buses in service. See `docs/DECISIONS.md` D2-D6.
"""
    (P.OUT / "calibration_report.md").write_text(txt, encoding="utf-8")
