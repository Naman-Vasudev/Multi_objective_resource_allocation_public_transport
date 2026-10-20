# Stage 3: Baseline evaluation and single-objective run

> **Synthetic demand, illustrative.** These numbers show how the model behaves; they are not CTU results.

Config: B_eff = 357, C = 60, α = 0.5, f_max mode = published, equity = soft,
hours = overlap. MILP: 651 variables, 576 constraints, solved Optimal in 0.05 s (HiGHS).

| metric | published baseline | min Z3 (MILP) |
|---|---|---|
| Z1 | 184776.57 | 191482.10 |
| Z1_daily | 664533.46 | 690766.11 |
| Z2 | 79478.29 | 75034.88 |
| Z3 | 3086.20 | 3066.56 |
| fleet_used | 385.00 | 355.00 |
| fleet_AM | 384.00 | 355.00 |
| fleet_Midday | 385.00 | 353.00 |
| fleet_PM | 380.00 | 349.00 |
| mean_wait_min | 16.61 | 17.21 |
| max_wait_min | 45.00 | 45.00 |
| ewt_min | 1.49 | 1.55 |
| mean_LF | 0.54 | 0.56 |
| n_LF_gt_1 | 24.00 | 24.00 |
| gini_LF | 0.40 | 0.39 |

## Published baseline vs model constraints
| constraint | n | max_excess | unit |
|---|---|---|---|
| C1 fleet | 3 | 28.000 | buses |
| C2 f*tau <= x | 9 | 1.425 | buses |
| C5 equity (soft) | 10 | 30.000 | min |

**Why min Z3 barely moves Z3 under published bounds:** most overflow sits on long-headway routes (31, 28A, 101, 8,
23B) that already run at their published f_max. If f_max is relaxed by two menu levels, min Z3 reaches
2209.9 pax/day. The published frequency range, not the fleet, is the binding limit on crowding.

Details are in `outputs/tables/baseline_violations.csv`. C1: the published allocation keeps 380-385 buses on the road
in each period, more than B_eff = 357, because it holds almost no spares. C2: routes 40, 76 and 25/25A cannot
run their mid frequency with their own buses at the assumed 22 km/h.
