# Stage 6: Simulation of improvements and trade-offs

> **Synthetic demand, illustrative.** 2000 demand scenarios: triangular (L, M, U) per route-period × a common
> Normal(1, 0.05) shock, seed 2026. Gamma headways with CV 0.3. Every schedule is
> evaluated on the same draws. Optimised schedules use f_max = relaxed. The numbers below are read
> from the CSVs in `outputs/`.

## Top 5 findings
**1. Waiting.** The best schedule for expected wait is **P-PASSENGER (α=0.5)**: 17.30 min per passenger vs 17.94 min for the baseline (-3.6%; 90% band 17.19-17.41 min). It runs on 357 buses vs 385 (-7.3%) and -2.5% vehicle-km. In this synthetic setting the gain comes with fewer vehicles, not more.

**2. Crowding risk.** Baseline overflow averages 2249 pax/day, and P(overflow > 5% of demand) = 65.6%. The lowest-risk optimised schedule is **P-PASSENGER (α=0.5)**: 1535 pax/day (-31.7%), probability 1.5%.

**3. Priorities trade equity for crowding.** P-EQUITY (α=0.5) has 0 min of headway above the caps vs 100 for P-PASSENGER. Its overflow is 1586 vs 1535 pax/day and its expected wait 17.34 vs 17.30 min.

**4. Price of robustness (P-BALANCED).** Moving from α=1 (plan for modal demand) to α=0 (plan for the upper bound U) changes P(overflow > 5%) from 3.1% to 2.7%, vehicle-km from 77,084 to 76,975, and expected wait from 17.35 to 17.32 min.

**5. Sensitivity and fleet.** The wait improvement is most sensitive to **speed v** (range 3.3% to 7.6%). 4 setting(s) are infeasible, all because the published minimum frequencies need more buses than B_eff: speed v = 18, spare ratio s = 0.1, spare ratio s = 0.2, layover = 0.15. Fleet experiment: the optimised schedule beats the baseline at B_eff = 357 (+3.3% wait). Cutting it further to 339, 321 is infeasible. Out of sample (spreads ×1.5, shock sd 0.1): P(overflow > 5%) rises from 65.6% to 70.3% for the baseline and from 1.5% to 24.1% for P-PASSENGER (α=0.5). The robust variant **P-BALANCED ROBUST (α=0, spreads ×1.5)** goes from 6.6% to 33.4%, with expected wait 17.35 min and 76,881 vehicle-km.

## Trade-off table (means over scenarios; % vs baseline)
| schedule | mean_wait_min | pct_mean_wait_min | overflow_pax | pct_overflow_pax | vehicle_km | pct_vehicle_km | fleet_used | pct_fleet_used | gini_LF | equity_excess_min | P_overflow_gt_5pct |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Baseline | 17.94 | 0.00 | 2248.81 | 0.00 | 79478.29 | 0.00 | 385.00 | 0.00 | 0.40 | 210.00 | 0.66 |
| Baseline (peak f_max) | 17.94 | 0.00 | 2230.32 | -0.82 | 79464.78 | -0.02 | 385.00 | 0.00 | 0.40 | 210.00 | 0.63 |
| P-PASSENGER (α=0.5) | 17.30 | -3.56 | 1535.19 | -31.73 | 77466.11 | -2.53 | 357.00 | -7.27 | 0.37 | 100.00 | 0.01 |
| P-OPERATOR (α=0.5) | 17.35 | -3.28 | 1535.19 | -31.73 | 77087.87 | -3.01 | 357.00 | -7.27 | 0.37 | 100.00 | 0.01 |
| P-EQUITY (α=0.5) | 17.34 | -3.33 | 1586.31 | -29.46 | 77041.44 | -3.07 | 357.00 | -7.27 | 0.37 | 0.00 | 0.03 |
| P-BALANCED (α=0.5) | 17.34 | -3.31 | 1586.31 | -29.46 | 77045.46 | -3.06 | 357.00 | -7.27 | 0.37 | 0.00 | 0.03 |
| P-PASSENGER (α=0) | 17.38 | -3.09 | 1637.96 | -27.16 | 77724.38 | -2.21 | 357.00 | -7.27 | 0.38 | 140.00 | 0.03 |
| P-OPERATOR (α=0) | 17.47 | -2.59 | 1637.96 | -27.16 | 77081.74 | -3.02 | 357.00 | -7.27 | 0.38 | 140.00 | 0.03 |
| P-EQUITY (α=0) | 17.32 | -3.44 | 1583.41 | -29.59 | 76992.90 | -3.13 | 357.00 | -7.27 | 0.37 | 0.00 | 0.03 |
| P-BALANCED (α=0) | 17.32 | -3.45 | 1583.41 | -29.59 | 76975.14 | -3.15 | 357.00 | -7.27 | 0.37 | 0.00 | 0.03 |
| P-BALANCED ROBUST (α=0, spreads ×1.5) | 17.35 | -3.27 | 1696.94 | -24.54 | 76881.09 | -3.27 | 357.00 | -7.27 | 0.37 | 0.00 | 0.07 |
| KNEE (Pareto front) | 17.68 | -1.45 | 1553.12 | -30.94 | 75564.23 | -4.92 | 357.00 | -7.27 | 0.37 | 30.00 | 0.03 |

Full distributions (mean, sd, 5th and 95th percentiles) are in `outputs/simulation_summary.csv`; route-level load
factors are in `outputs/tables/simulation_route_LF.csv`.

## Sensitivity (policy P-BALANCED, one factor at a time)
| factor | value | B_eff | feasible | wait_improvement_pct | opt_P_overflow_gt_5pct | base_P_overflow_gt_5pct |
|---|---|---|---|---|---|---|
| demand level | 0.80 | 357 | True | 3.25 | 0.00 | 0.00 |
| demand level | 0.90 | 357 | True | 3.31 | 0.00 | 0.08 |
| demand level | 1.00 | 357 | True | 3.31 | 0.03 | 0.66 |
| demand level | 1.10 | 357 | True | 3.37 | 0.43 | 0.97 |
| demand level | 1.20 | 357 | True | 3.31 | 0.92 | 1.00 |
| capacity C | 50.00 | 357 | True | 3.36 | 0.92 | 1.00 |
| capacity C | 60.00 | 357 | True | 3.31 | 0.03 | 0.66 |
| capacity C | 70.00 | 357 | True | 3.30 | 0.00 | 0.01 |
| capacity C | 80.00 | 357 | True | 3.25 | 0.00 | 0.00 |
| speed v | 18.00 | 357 | False |  |  |  |
| speed v | 22.00 | 357 | True | 3.31 | 0.03 | 0.66 |
| speed v | 26.00 | 357 | True | 7.55 | 0.00 | 0.66 |
| spare ratio s | 0.00 | 389 | True | 3.69 | 0.00 | 0.66 |
| spare ratio s | 0.08 | 357 | True | 3.31 | 0.03 | 0.66 |
| spare ratio s | 0.10 | 350 | False |  |  |  |
| spare ratio s | 0.20 | 311 | False |  |  |  |
| layover | 0.05 | 357 | True | 5.91 | 0.00 | 0.66 |
| layover | 0.10 | 357 | True | 3.31 | 0.03 | 0.66 |
| layover | 0.15 | 357 | False |  |  |  |

Infeasible settings, with the solver-free presolve reason:
- speed v = 18: route 76 AM: needs 6 buses at its lowest allowed frequency (1.500 dep/h x tau 3.789 h) but C5 allows at most 5 (x0 = 4); route 76 Midday: needs 6 buses at its lowest allowed frequency (1.500 dep/h x tau 3.789 h) but C5 allows at most 5 (x0 = 4); route 76 PM: needs 6 buses at its lowest allowed frequency (1.500 dep/h x tau 3.789 h) but C5 allows at most 5 (x0 = 4); AM: minimum buses 418 exceed B_eff = 357; Midday: minimum buses 419 exceed B_eff = 357; PM: minimum buses 413 exceed B_eff = 357
- spare ratio s = 0.1: AM: minimum buses 352 exceed B_eff = 350; Midday: minimum buses 353 exceed B_eff = 350
- spare ratio s = 0.2: AM: minimum buses 352 exceed B_eff = 311; Midday: minimum buses 353 exceed B_eff = 311; PM: minimum buses 348 exceed B_eff = 311
- layover = 0.15: AM: minimum buses 367 exceed B_eff = 357; Midday: minimum buses 368 exceed B_eff = 357; PM: minimum buses 363 exceed B_eff = 357

## Figures
![](figures/sim_tradeoff_bars.png)
![](figures/sim_wait_vs_vkm.png)
![](figures/sim_overflow_distribution.png)
![](figures/sensitivity_tornado.png)
![](figures/sensitivity_alpha.png)
![](figures/sensitivity_fleet.png)
![](figures/sensitivity_out_of_sample.png)
![](figures/sim_route_p95_LF.png)

## Limitations
- **Demand is synthetic.** How it is spread across routes (length, PGI/ISBT flags, noise) drives where the
  gains appear, so none of these numbers are CTU results.
- **Travel times are constant** (one speed, fixed layover), with no congestion or timetable-dependent running times.
- **No transfers and no passenger route choice:** demand per route does not react to frequency.
- **No depot constraints** (buses can move between routes freely) and **no driver-shift or crew modelling.**
- **One-day horizon** with three periods. Early-morning and late-evening service outside 07-19 h is not optimised.
- **Headway irregularity** enters only through the gamma CV formula. Bunching does not change capacity.
