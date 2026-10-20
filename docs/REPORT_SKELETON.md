# Optimization-Based Resource Allocation for Public Bus Fleet Scheduling under Demand Variability: A Case Study of Chandigarh Transport Undertaking

*B.Tech Mathematics & Computing minor project, PEC Chandigarh. Report skeleton.*

> **How to use this skeleton**
> - Every number is a placeholder of the form `⟦name | file → row filter → column⟧`. Fill it by reading that
>   cell after `python run_all.py`. **Never type a number from memory.**
> - Citation keys refer to `docs/LITERATURE_VERIFIED.md` (A# = candidate list, B# = additional papers). Cite nothing
>   marked UNVERIFIED.
> - Every demand-dependent result must carry the phrase **"synthetic demand, illustrative"**.

---

## Abstract (≈200 words; write last)
- **Problem:** allocating a fixed CTU bus fleet across 68 routes and three daily periods, under uncertain demand.
- **Method:**
  - a corrected multi-objective MILP over a discrete headway menu;
  - triangular fuzzy demand with α-cut capacity constraints;
  - preemptive and weighted goal programming;
  - an exact Pareto front (AUGMECON) cross-checked with NSGA-II;
  - Monte Carlo stress tests.
- **Data:** the published CTU timetable (68 routes, ⟦B | data/processed/routes.csv → sum x_base⟧ buses).
  Demand is **synthetic**.
- **Headline (illustrative):** the headline policy vs the published schedule:
  - waiting ⟦Δwait% | outputs/tables/simulation_tradeoffs.csv → schedule = "P-BALANCED (α=0.5)" → pct_mean_wait_min⟧;
  - overflow ⟦Δoverflow% | same row → pct_overflow_pax⟧;
  - vehicle-km ⟦Δvkm% | same row → pct_vehicle_km⟧;
  - buses ⟦fleet | same row → fleet_used⟧ vs ⟦fleet_base | schedule = "Baseline" → fleet_used⟧.
- **Caveat sentence (mandatory):** the results show the method's behaviour, not measured CTU improvements.

## 1. Introduction
- 1.1 Context: CTU, tri-city bus service, Depots II, III and IV. Peaks, spare capacity off-peak, and no ridership data
  in the public domain.
- 1.2 Why fleet allocation matters: waiting, crowding, operating effort and equity [A5, A1].
- 1.3 Objectives of the project (from the synopsis, restated after the corrections).
- 1.4 Contributions:
  1. a cleaned, verified CTU route dataset;
  2. a corrected linear formulation;
  3. a transparent synthetic-demand protocol;
  4. GP with explicit priorities;
  5. an exact-vs-heuristic Pareto cross-check;
  6. a stress test with honest infeasibility reporting.
- 1.5 Report outline.

## 2. Literature review (organised by theme)
- **2.1 Transit planning chain and frequency setting.** Decomposition into design, frequency, timetabling and
  scheduling [A2, A4, A5, A1]. Fleet-constrained frequency allocation across routes and periods [A3, B2]. MILP with
  discrete frequencies [B1].
- **2.2 Multi-objective transit optimisation.** User-operator trade-offs and Pareto fronts [B3, B4, B5]. Scalarisation
  methods [A11]. Exact ε-constraint / AUGMECON [A10; AUGMECON2]. NSGA-II [A9].
- **2.3 Goal programming.** Origins [A6]. Lexicographic vs weighted GP and normalisation [A7]. Target-setting pitfalls
  [A8].
  - **Gap (state carefully):** our search found no 2014-2026 peer-reviewed application of GP to bus frequency or
    fleet allocation. The GP-in-transportation work found treats the classical transportation problem (Rivaz et al.
    2020; Giri et al. 2014).
- **2.4 Demand uncertainty: stochastic vs fuzzy.** Stochastic programming [B6, B7]. Chance constraints [A16]. Fuzzy
  sets and fuzzy decision-making [A12, A13]. Possibilistic programming [A15, B9]. Fuzzy multi-objective LP [A14].
  Why fuzzy here: no data to fit distributions.
- **2.5 Service-quality measures.** Excess Wait Time (TfL definition [A18b]; Singapore BSRF [A19a]). The TCQSM [A17].
  Crowding valuation is context-specific [B12].
- **2.6 Indian city bus operations.** Measured speeds and their variability [B10, B11]; implications for calibration.
- **2.7 Positioning.** Fixed-route, fleet-constrained, fuzzy-demand GP with an exact Pareto cross-check, applied to a
  real Indian timetable with synthetic demand.

## 3. Problem statement
- Given:
  - 68 fixed routes and their published headway ranges;
  - route lengths and the buses allocated to each route;
  - three periods: AM 07-10, Midday 10-16, PM 16-19;
  - a fleet limit.
- Choose a headway and a bus count for each active route-period, to trade off waiting, vehicle-km, overflow and
  headway equity.
- State the assumptions in one list: fixed routes, constant travel times, no transfers or route choice, and a one-day
  horizon.

## 4. Data and calibration
- 4.1 Source: CTU timetable PDF (as on 25.07.2026) → `data/raw/CTU_Routes_Structured.xlsx`. Audit results:
  - routes ⟦68 | outputs/calibration_report.md → audit table⟧;
  - buses ⟦389 | routes.csv → sum x_base⟧;
  - length ⟦1662 km | routes.csv → sum d_r_km⟧;
  - PDF checks ⟦68/68 | calibration_report.md⟧;
  - stops ⟦649 | data/processed/stops.csv → row count⟧.
- 4.2 Cleaning rules: footer rows excluded; route numbers kept as strings ("25/25A"); exact 60/headway; the cross-checks
  performed.
- 4.3 Calibration of cycle times. Scenarios S1/S2/S3, speeds 18/22/26 km/h, layover 0/10%
  (table ⟦outputs/tables/calibration_scenarios.csv⟧, figure `outputs/figures/calibration_N_need.png`).
  - **Wording rule:** the one-way reading S2 is chosen because it makes the published timetable *consistent* with
    the allocation. It is not proven; CTU must confirm it (DECISIONS D2, D42).
- 4.4 Speed evidence: Indian measured bus speeds [B10, B11] vs the implied speed
  ⟦v_implied | calibration_report.md → "Implied uniform speed"⟧.
- 4.5 Stop-network features (`data/processed/route_features.csv`).

## 5. Model: corrected formulation
- 5.1 Sets, parameters, decision variables, constraints C1-C6, objectives Z1-Z3 (copy from `docs/MODEL.md`).
- 5.2 **Why the synopsis formulation was changed:**
  1. Z1 = Σ D·30/f is nonlinear in f. It becomes linear in binary headway choices.
  2. Z2 must be vehicle-km (d_cycle·f·H), not d·x.
  3. Capacity is C·f per hour, so overflow is o ≥ D − C·f.
  4. Defuzzification uses the **upper** α-cut U − α(U − M); the synopsis formula is the lower cut.
- 5.3 Feasibility adjustments, each with its reason:
  - route-specific menus (D21);
  - spare ratio 8%, since 10% is infeasible (D22);
  - practicality floor of ±1 bus (D25);
  - soft equity cap (D26).
- 5.4 Known modelling limitations, stated openly:
  - Z1 is a per-hour rate, not weighted by period length;
  - h/2 waiting overstates waiting at long headways;
  - there is no within-period peak-hour factor;
  - buses change routes freely between periods (interlining).

## 6. Fuzzy demand and the α-cut
- 6.1 Synthetic demand protocol (D19). Formula, parameters, seed, anchor (**unverified**:
  ⟦143,000 riders / 684 buses⟧, pro-rata ⟦81,326 | src/params.py → DAILY_BOARDINGS⟧).
- 6.2 Triangular fuzzy numbers: L = 0.80·M and U = 1.35·M (right-skewed). Route overrides.
- 6.3 α-cuts and the role of α. Figure `outputs/figures/tfn_alpha_cuts.png`.
- 6.4 Descriptive check (`outputs/demand_report.md`): CV across routes ⟦cv | demand_report.md⟧; baseline load
  factors; θ sensitivity (`outputs/tables/theta_sensitivity.csv`); seed robustness
  (`outputs/tables/seed_robustness.csv`).
- 6.5 How real data would replace this (`docs/REAL_DEMAND_DATA.md`).

## 7. Goal programming with priorities
- 7.1 Goals G1-G4: targets, unwanted deviations, normalisation (`docs/GOAL_PROGRAMMING.md`) [A7, A8].
- 7.2 Preemptive algorithm and locking; weighted GP; Chebyshev GP.
- 7.3 **Target setting (disclose):** κ1 = 0.04 and κ3 = 0.03 were set *after* the ideal values were known (D48-D49).
  Report the goal-achievement table as conditional on these targets.
- 7.4 Results (α = 0.5, f_max relaxed): table from `outputs/gp_results.csv` (rows: scenarios; columns Z1, Z2, Z3,
  equity_excess_min, pct_*). Goal achievement: `outputs/tables/gp_goal_achievement.csv`.
  Figure `outputs/figures/gp_pct_change.png`.
- 7.5 Ideal and nadir: `outputs/tables/gp_payoff_ideal_nadir.csv`.
- 7.6 Route-level reallocation: `outputs/tables/gp_route_changes.csv` (top gains and losses, with demand/supply reasons).
- 7.7 Published vs relaxed f_max: why priorities only matter in relaxed mode (D32, D50).

## 8. Pareto cross-check
- 8.1 AUGMECON settings: 20 × 20 grid, lexicographic payoff table (`outputs/tables/pareto_payoff.csv`). Infeasible and
  skipped cells (`outputs/tables/pareto_eps_grid.csv`).
- 8.2 NSGA-II settings: population 200, 300 generations, 5 seeds, encoding and repair.
- 8.3 Metrics (`outputs/tables/pareto_metrics.csv`):
  - hypervolume ⟦HV exact | method = "AUGMECON (exact)" → hypervolume⟧ vs ⟦HV NSGA union | method = "NSGA-II union of seeds" → hypervolume⟧;
  - GD and IGD;
  - strict-dominance check ⟦0 | eps_points_strictly_dominated⟧;
  - runtimes.
- 8.4 Where the GP solutions lie relative to the front (`outputs/tables/pareto_gp_distance.csv`).
- 8.5 Figures: `outputs/figures/pareto_2d.png`, `outputs/figures/pareto_3d.png`.
- 8.6 Honest comparison: exact vs heuristic at this problem size; when NSGA-II would be preferred.

## 9. Simulation design
- N = ⟦2000 | src/params.py → SIM_N⟧ scenarios.
- Demand: triangular × a common Normal(1, ⟦0.05⟧) shock; seed ⟦2026⟧; the same draws for every schedule.
- Waiting with gamma headways: E[W] = (h/2)(1 + CV²), CV = ⟦0.3⟧. Excess Wait Time (EWT) as in §2.5.
- Schedules compared; knee-point definition; out-of-sample design (spreads ×⟦1.5⟧, shock sd ⟦0.10⟧).

## 10. Results
*Each number below is tagged to its source. Every sub-section opens with "synthetic demand, illustrative".*
- **10.1 Baseline vs model constraints:** `outputs/tables/baseline_violations.csv`. The C1 excess is
  ⟦AM | constraint = "C1 fleet", period = AM → excess⟧ buses.
- **10.2 Main trade-off table:** `outputs/tables/simulation_tradeoffs.csv` (all schedules; pct_* columns).
  Figures `outputs/figures/sim_tradeoff_bars.png` and `outputs/figures/sim_wait_vs_vkm.png`.
- **10.3 Distributions and risk:** `outputs/simulation_summary.csv` (mean, sd, p5, p95), P(overflow > 5%).
  Figure `outputs/figures/sim_overflow_distribution.png`.
- **10.4 Sensitivity:** `outputs/sensitivity_oat.csv` and the tornado figure `outputs/figures/sensitivity_tornado.png`.
  List the infeasible settings with their presolve reasons (column `reason`).
- **10.5 Price of robustness:** `outputs/sensitivity_alpha.csv`; figure `outputs/figures/sensitivity_alpha.png`.
- **10.6 Fleet reduction:** `outputs/sensitivity_fleet.csv`; figure `outputs/figures/sensitivity_fleet.png`.
- **10.7 Out-of-sample test and the rejected robust variant:** `outputs/sensitivity_out_of_sample.csv`
  (robust row: schedule = "P-BALANCED ROBUST (α=0, spreads ×1.5)"); figure `outputs/figures/sensitivity_out_of_sample.png`.
- **10.8 Most crowded routes:** `outputs/tables/simulation_route_LF.csv`; figure `outputs/figures/sim_route_p95_LF.png`.
- **10.9 Top-5 findings:** copy from `outputs/simulation_findings.md`, which is generated from the CSVs.

## 11. Trade-offs and discussion
- 11.1 What the priorities buy:
  - crowding-first (P-PASSENGER) vs equity-first (P-EQUITY / P-BALANCED): ⟦equity_excess_min and overflow_pax rows⟧;
  - operator-first (P-OPERATOR) once G3 binds.
- 11.2 Why α matters little here: the coarse headway menu.
- 11.3 Where the gains come from, and which may be artefacts (from the examiner review):
  - the baseline runs mid frequency in all periods (straw-man risk);
  - uniform-speed calibration creates apparent surplus buses;
  - demand is proportional to route length;
  - targets were set after the ideal values were known.
  For each, either report the robustness test or flag it as untested.
- 11.4 Differences smaller than practical significance: waiting differences of about
  ⟦Δ | simulation_tradeoffs.csv → mean_wait_min spread across schedules⟧ minutes. Do not rank on these.
- 11.5 Exact vs heuristic methods: what NSGA-II would add with simulation-based objectives.

## 12. Limitations
- **Synthetic demand:** its distribution across routes (length, hub flags, noise) drives where the gains appear.
  No result is a CTU outcome.
- **Unverified anchor:** daily ridership and fleet size (Tribune India figures, no URL).
- **Calibration:** one uniform speed (22 km/h), 10% layover close to the feasibility edge, one-way route-length reading
  not confirmed by CTU.
- **Operations not modelled:** constant travel times, no transfers or route choice, no depot or interlining
  constraints, no driver-shift modelling, a one-day three-period horizon, no stop or terminal capacity check at
  relaxed headways.
- **Waiting model:** random arrivals (h/2) even at long headways; no within-period peak-hour factor.
- **Baseline definition:** mid-range frequency in every period.

## 13. Conclusion and future work
- 13.1 Conclusions, phrased as properties of the method, not of CTU.
- 13.2 Future work:
  - **real ridership:** CTU ETM ticket data and boarding counts at 5-10 hubs; estimate L/M/U as 10th/50th/90th
    percentiles (`docs/REAL_DEMAND_DATA.md`);
  - depot and interlining constraints;
  - driver duties and crew scheduling;
  - timetable-level scheduling (departure times, synchronisation at hubs);
  - route-specific running times from AVL/GPS;
  - demand prediction (gradient-boosted trees such as XGBoost, or similar) **once labelled ridership exists**, feeding
    predicted L/M/U into the same α-cut model;
  - Zimmermann max-min fuzzy GP [A14];
  - passenger assignment and route choice [B5].

## References
Use only verified entries from `docs/LITERATURE_VERIFIED.md`, in one consistent style (IEEE or APA). Resolve every DOI
through LibKey before submission. Replace synopsis references [2], [3] and [4] as listed there.

## Appendices
- A. Decision log: `docs/DECISIONS.md` (D1-D55).
- B. Glossary: `docs/GLOSSARY.md`.
- C. Reproducibility: `python run_all.py` (about 7 min), seeds, `requirements.txt`, test suite (`python -m pytest`).
- D. Examiner-style self-review and the fixes not yet done (prioritised fix list).
