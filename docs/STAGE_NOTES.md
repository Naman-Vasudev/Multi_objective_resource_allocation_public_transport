# STAGE NOTES

## Stage 1: Data audit and calibration (2026-10-15)

**Run:** `python run_all.py` (or `make all`). **Tests:** `python -m pytest` (39 tests).

**Produced**
- `data/raw/CTU_Routes_Structured.xlsx`: an unchanged copy of the source workbook.
- `data/processed/routes.csv`: 68 routes, the clean parameter table. It also carries service_type, overnight and
  active AM/Midday/PM flags for later stages.
- `data/processed/stops.csv`, `route_stops.csv`, `route_features.csv`: the stop network.
- `outputs/tables/calibration_scenarios.csv`: 18 combinations (3 scenarios × 3 speeds × 2 layovers).
- `outputs/tables/per_route_S2_v22_lay10.csv`, `routes_short_S2_v22.csv`, `model_variables_check.csv`.
- `outputs/figures/calibration_N_need.png`, `outputs/calibration_report.md`, `outputs/logs/run_all.log`.

**Findings**
- All data assertions pass: 68 routes, B = 389, Σd = 1662 km, and 68 of 68 PDF Verification rows are OK. The
  Route Master text and the Operating Windows cells agree for every route.
- The brief's "651 stops" is really 649 stops plus 1 blank row and 1 note row.
- A second footer row ("Routes active") sits under Operating Windows; it is excluded.
- 17 Model Variables cells are 2-dp roundings (≤ 0.0043 dep/h); we use exact values.
- Hand checks reproduced: S1 = 171.9, S2 = 309.9, S2 + 10% layover = 340.9 buses.
- S1 is rejected. The recommended default is S2 + 22 km/h + 10% layover + 10% spares, giving 375.0 buses
  (96.4% of B). It is PENDING STUDENT CONFIRMATION.
- Short routes at 22 km/h: 37 (night, needs about 38-42 km/h), 76 (few stops, needs 23-26 km/h) and 40 (marginal).

**Code layout note:** Stage 1 adds `src/calibration.py` (cycle-time maths) and `src/stage1.py` (stage runner and
report) next to the planned modules.

## Stage 2: Periods, synthetic demand, TFNs (2026-10-15)

- `PERIODS` and multipliers in `params.py`. Period boundaries are asserted equal to Operating Windows B2:C4.
  Active routes: AM 64, Midday 65, PM 62. 21 pairs are only partially active.
- The workbook has no "Synthetic Demand" sheet. The student authorised us to make the assumptions, so demand is
  generated in `src/demand.py` (DECISIONS D19). Daily boardings are calibrated to 81,326, with seed 42.
- Outputs:
  - `data/processed/demand_rt.csv` (L, M, U), `base_demand_r.csv`, `periods_rt.csv`;
  - `outputs/demand_report.md`;
  - tables: baseline load factors, θ sensitivity, seed robustness;
  - heatmap and TFN figures, both titled "(synthetic demand)".
- Baseline fit at θ = 1.8 (capacity C·f_max in the peaks, C·f_min midday):
  - mean load factor: AM 0.63, Midday 0.38, PM 0.59;
  - overloaded pairs: 11 AM, 3 Midday, 10 PM, mostly long routes with 75-90 min headways;
  - CV of M across routes: about 0.39-0.41.

## Stage 3: Corrected MILP and baseline evaluation (2026-10-15)

- The model math is in `docs/MODEL.md`; code in `src/model.py` (PuLP 4 + HiGHS) and `src/metrics.py`.
- Feasibility fixes, all documented:
  - D21: route menus include the published headways;
  - D22: s = 0.08, B_eff = 357, because 10% is provably infeasible (352/353 > 350);
  - D25: a practicality floor of ±1 bus;
  - D26: the equity cap is soft.
- The min-Z3 run solves to optimality in about 0.06 s (651 variables, 576 constraints).
- Published baseline vs min Z3, all synthetic demand:

  | | Baseline | Min Z3 | Min Z3, relaxed f_max |
  |---|---|---|---|
  | Fleet used (buses) | 385 | 355 | 357 |
  | Z3 (pax/day) | 3,086 | 3,067 | 2,210 |
  | Z2 (veh-km/day) | 79,478 | 75,035 | 75,677 |

- With the published f_max, overflow cannot drop much because the overloaded routes are already at their f_max.
- The baseline violates C1 by 27/28/23 buses (AM/Midday/PM). It violates C2 on routes 40, 76 and 25/25A
  (by up to 1.43 buses) and the soft equity cap on 10 pairs. All of this is in `outputs/tables/baseline_violations.csv`.
- Tests: 73 pass. They include a toy MILP checked against brute force (4 objective weightings), units, the precise
  baseline violation report, the 10%-spares infeasibility check, a solve time under 60 s, and Z3 monotone in C.

## Stage 4: Goal programming with priorities (2026-10-15)

- `src/goals.py` and `src/stage4.py`, with scenarios in `config/gp_scenarios.json`.
  - Methods: preemptive (P-PASSENGER, P-OPERATOR, P-EQUITY), weighted (P-BALANCED) and Chebyshev.
  - The sweep covers 5 values of α (0, 0.25, 0.5, 0.75, 1) × 2 f_max modes. All 50 runs solve to optimality,
    in about 16 s in total.
- Outputs:
  - `outputs/gp_results.csv` and `outputs/gp_report.md`;
  - tables: `gp_goal_achievement.csv`, `gp_levels.csv`, `gp_payoff_ideal_nadir.csv`, `gp_route_changes.csv`;
  - figure: `outputs/figures/gp_pct_change.png`.
- Findings at α = 0.5 (synthetic demand):
  - **Published f_max:** all 5 scenarios give the same schedule. Z1 is +0.8%, Z2 −2.3% and Z3 −0.6% vs the baseline.
    There is no conflict to prioritise.
  - **Relaxed f_max:** P-PASSENGER, P-OPERATOR and CHEBYSHEV give Z3 −29.6%, Z1 −4.0%, with 100 minutes still above
    the cap. P-EQUITY and P-BALANCED give equity 0 (target met), Z3 −26.4%, Z1 −4.8%. Priorities trade about 3 points
    of overflow reduction for full equity.
  - **G1** (−15% waiting) is unreachable in every run: the best possible is −4.9% (relaxed) or +0.8% (published),
    because B_eff = 357 < 385 buses today.
  - **G2** (zero overflow) is unreachable in every run. **G3** is always met, and never binds.
  - **Routes:** buses move from routes with surplus or low loads (32, 551, 206, 10, 20, 38AB, 5A/5C, 2F, 242) to
    overcrowded long-headway routes (31, 28A, 101, 8, 70A, 214, 20A) and to route 40, whose baseline is short of buses.
- Checks: every preemptive run is lexicographic. On the toy instance, preemptive GP equals brute-force lexicographic
  minimisation for 4 priority orders. Priorities change the answer in relaxed mode (test). 83 tests pass.
- **Why GP rather than a weighted sum:** targets and priorities are explicit, so they can be stated and signed off.
- **Known weakness:** the answer depends on the targets and the ordering. Here G3's loose target makes it irrelevant,
  and preemptive GP can ignore low-priority goals completely (see `docs/GOAL_PROGRAMMING.md`).

## Stage 5: Pareto front and cross-check (2026-10-15)

- Code: `src/pareto.py` (AUGMECON, NSGA-II with DEAP, HV/GD/IGD/C) and `src/stage5.py`. Literature: `docs/LITERATURE.md`.
  The references are not yet LibKey-resolved, because the connector needs authorisation.
- Results (relaxed f_max, α = 0.5, synthetic demand):
  - **AUGMECON:** 72 optimal cells, 9 infeasible, 19 skipped by early exit. 18 strictly efficient points in about 34 s.
  - **NSGA-II:** 187-194 non-dominated points per seed, 60,200 evaluations, about 77 s per seed; 5 seeds in
    parallel in about 87 s of wall time.
  - **Hypervolume (ref 1.1):** exact 0.889; NSGA-II 0.964-0.968 per seed, 0.980 for the union.
    GD about 0.095, IGD 0.035-0.051.
  - **No NSGA-II point strictly dominates any exact point.** NSGA-II's higher HV comes from filling the gaps
    between the 18 grid samples.
- GP vs front: P-PASSENGER, P-OPERATOR and CHEBYSHEV lie on the front (distance 0, the min-Z3 lexicographic point).
  P-EQUITY and P-BALANCED are not dominated (distance 0.047; equity is a 4th criterion).
- The published baseline is dominated (distance 1.09) and infeasible (it breaks C1).
- Verification: all 970 reported points re-checked against every hard constraint and their objective values.
  92 tests pass, in about 21 s.
- **Honest verdict:** at this size the exact MILP is the better method. It gives certified efficient points and
  infeasibility information quickly. NSGA-II gives a denser front from one run and would be the tool for non-linear
  or simulation-based objectives.

## Stage 6: Simulation and sensitivity (2026-10-15)

- Code: `src/simulate.py` (draws, gamma-headway waiting, per-scenario metrics) and `src/stage6.py` (comparison,
  sensitivity, out-of-sample, figures, findings).
- Outputs:
  - `outputs/simulation_summary.csv` (mean, sd, p5, p95 per schedule and metric, plus P(overflow > 5%));
  - `outputs/sensitivity_oat.csv`, `sensitivity_alpha.csv`, `sensitivity_fleet.csv`, `sensitivity_out_of_sample.csv`;
  - 8 figures;
  - `outputs/simulation_findings.md`. Its top-5 findings are generated from the CSVs. Read the numbers there; they
    are not copied into these notes, so they cannot go stale.
- Infeasible settings (speed 18 km/h, spares 10% or 20%, fleet cuts of 5% or 10%) are reported with the exact
  presolve reason.
- Tests: 100 pass, including the gamma waiting formula, sampling moments, deterministic consistency with the
  model's Z values, monotonicity in C, feasibility of optimised schedules, and that infeasibility is reported.
- Run: `python run_all.py` (about 4 min), or `python run_all.py --skip-pareto` (about 1 min) to reuse the Stage 5 fronts.

## Judgment calls on all open decisions (2026-10-15)

- All open questions from Stages 1-6 were decided from literature and project data: DECISIONS D42-D55, evidence in
  `docs/LITERATURE.md` [14]-[25].
- **Changes to the model:**
  - κ1 = 0.04 and κ3 = 0.03 (`config/gp_scenarios.json`);
  - AUGMECON grid 20 × 20;
  - layover tested at 5-15%;
  - a robust variant was tested and rejected (negative result).
- **Unchanged after review:** S2, 22 km/h, 10% layover, s = 0.08, uniform speed, f_max relaxed for headline results.
- **Headline policy:** P-BALANCED.
- The full pipeline was re-run; 100 tests pass. Every result file and report regenerates from `python run_all.py`.
