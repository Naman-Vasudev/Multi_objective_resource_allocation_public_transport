# DECISIONS

Every modelling assumption, with its value, reason, how to change it and what it affects.
Status tags: **CONFIRMED** (fact from the data), **PENDING STUDENT CONFIRMATION** (recommended, needs the
student's sign-off), **ASSUMPTION** (judgement call, documented so it can be challenged).

No ridership data exists. Any demand introduced in later stages is **synthetic demand, illustrative**.

---

## D1. Rows used from the workbook (CONFIRMED)
- **Assumption:** real data rows end at the first blank cell or footer label ("TOTAL" in Route Master,
  "Routes active" in Operating Windows, blank row then note in Stop Coverage and Model Variables).
- **Value:** 68 routes, B = 389 buses, Σd_r = 1662 km, 649 stops. The brief said 651 stops; the sheet has
  649 stops plus 1 blank row and 1 note row, and Network Summary also says 649.
- **Reason:** footer rows are sums or notes, not routes.
- **How to change:** `FOOTER_LABELS` in `src/data.py`; expected counts in `src/params.py`.
- **Affects:** everything. The counts are asserted, so a wrong row selection fails loudly.

## D2. Meaning of the published route length d_r: scenario S2 (PENDING STUDENT CONFIRMATION)
- **Assumption:** d_r is the **one-way** length for non-loop routes, so a bus covers 2·d_r per cycle. For the 8
  loop routes (origin = destination: 2A, 2C, 4A, 4C, 5A, 5C, 9A, 9C), d_r is the full cycle.
- **Value:** `DEFAULT_SCENARIO = "S2"`.
- **Reason:** under S1 (d_r = full cycle), only 37-59% of the fleet would be needed, and 49-63 of 68 routes
  would hold more buses than even their highest published frequency needs. Under S2 at 22 km/h with 10% layover,
  baseline use is 87.6% (96.4% with spares) and only 3 routes look short. See `outputs/calibration_report.md`.
- **How to change:** `DEFAULT_SCENARIO` in `src/params.py`; scenario logic in `src/calibration.py::cycle_distance_km`.
- **Affects:** τ_r for every route, the fleet constraint, Z2 (vehicle-km) in all later stages, and every result.
- **To confirm with CTU:** whether the timetable "Route Length (km)" is one-way.

## D3. Average commercial speed v (PENDING STUDENT CONFIRMATION)
- **Assumption:** one uniform network speed of 22 km/h, including dwell time at stops.
- **Value:** `DEFAULT_SPEED_KMH = 22.0`. Tested values are 18, 22 and 26 km/h.
- **Reason:** 22 km/h is the workbook's own stated assumption, not a measured value. At 18 km/h, 23 routes cannot
  run their published minimum frequency; at 26 km/h, use falls to 74% or less. The implied uniform speed that
  exactly fills 389 / 1.1 buses in service is 21.2 km/h.
- **How to change:** `DEFAULT_SPEED_KMH` and `SPEEDS_KMH` in `src/params.py`.
- **Affects:** τ_r, the fleet constraint and max feasible frequency. Routes 37 and 76 (and 40 with layover) are
  short at 22 km/h; route-specific speeds would fix this but need data we do not have.

## D4. Layover / recovery time (PENDING STUDENT CONFIRMATION)
- **Assumption:** layover equals 10% of running time and is added to every cycle.
- **Value:** `DEFAULT_LAYOVER_FRAC = 0.10`. Tested values are 0 and 0.10.
- **Reason:** drivers need terminal time and schedules need slack. Zero layover is physically unrealistic. 10% is
  a round planning value; it is not taken from CTU data.
- **How to change:** `DEFAULT_LAYOVER_FRAC` and `LAYOVER_FRACS` in `src/params.py`.
- **Affects:** τ_r (×1.10), the fleet constraint and the list of short routes (adds route 40).

## D5. Spare ratio and how it enters the fleet constraint (PENDING STUDENT CONFIRMATION)
- **Assumption:** spare ratio s = 10%, defined as spares ÷ buses in service. The total fleet needed is
  N_total = N_in_service × (1 + s). The fleet constraint in the model is therefore
  Σ_r f_r · τ_r ≤ B / (1 + s) = 353.6.
- **Value:** `SPARE_RATIO = 0.10`.
- **Reason:** 389 allocated buses vs 340.9 needed in service (S2, 22 km/h, 10% layover) leaves 48 buses. That is
  consistent with spares and maintenance reserve. Whether the 389 already excludes spares is **not determinable from
  the files**.
- **How to change:** `SPARE_RATIO` in `src/params.py`. Use 0 if CTU confirms the 389 are all in service.
  The other common definition, in-service = B × (1 − s), gives 350.1 instead of 353.6.
- **Affects:** the right-hand side of the fleet constraint, and therefore how much room the optimiser has to add
  frequency.

## D6. "Plausible baseline" utilisation band (ASSUMPTION)
- **Value:** 85-100% of B (`UTIL_BAND`).
- **Reason:** a judgement call used only to rank calibration scenarios. An operator would not keep about 50% of its
  fleet idle, and cannot run more than 100%.
- **How to change:** `UTIL_BAND` in `src/params.py`.
- **Affects:** only the "in band" flag in the calibration table.

## D7. Mid frequency f_mid (ASSUMPTION)
- **Value:** f_mid = (f_min + f_max) / 2 [dep/h], the same as the workbook.
- **Reason:** the timetable gives a single all-day range, not per-period values. This is used only as the
  baseline for calibration. Note that 60 / mid-headway is a different number; for "15-30", the arithmetic mean
  gives 3.0 dep/h but a 22.5 min headway gives 2.67 dep/h.
- **How to change:** `per_route` / `buses_needed(freq_col=...)` in `src/calibration.py`.
- **Affects:** baseline N_need only. The optimiser chooses its own frequency within [f_min, f_max].

## D8. Exact frequencies, not the workbook's typed values (CONFIRMED)
- **Value:** f = 60 / headway exactly.
- **Reason:** 17 Model Variables cells are typed values rounded to 2 dp (routes 213, 214, 23B, 24C, 26 and 79;
  largest error 0.0043 dep/h). τ = d/22 and x/τ match exactly.
- **How to change:** not applicable. The comparison is in `outputs/tables/model_variables_check.csv`.
- **Affects:** negligible numerically; avoids inconsistent inputs.

## D9. Route allocations treated as separate (ASSUMPTION)
- **Assumption:** each route's buses are its own; there is no sharing between day, night and short-span routes.
- **Reason:** 4 routes (11A, 24A, 24C, 37; 5 buses) are not active in the AM peak. Sharing them would lower the
  simultaneous need only from 340.9 to 334.9.
- **How to change:** use `calibration.am_peak_need` or the per-period fleet constraints introduced in later stages.
- **Affects:** the baseline fleet check only.

## D10. Operating windows read from Excel cached values (CONFIRMED)
- **Value:** first and last departure and span come from the Operating Windows cached formula results. If cached
  values are missing, they are recomputed from the typed time cells with the same rule. A test asserts that both
  agree.
- **Reason:** the brief says not to re-parse the Route Master text. The text is parsed only as a cross-check, and
  it matches for all 68 routes.
- **How to change:** `read_operating_windows` in `src/data.py`.
- **Affects:** span_hours, overnight flags and active-period flags, which later feed the per-period demand H_t.

## D11. Stop-network features (ASSUMPTION)
- **Value:** a hub is a stop served by at least 10 routes (`HUB_MIN_ROUTES`); there are 10 hubs.
  "Centrality" is the sum or mean of "routes serving" over a route's stops, counting the route itself.
- **Reason:** a simple, transparent proxy. Stop names are verbatim, so "22/17" and "17/22" may be the same junction.
  This is a coverage map, not a stop registry.
- **How to change:** `HUB_MIN_ROUTES` in `src/params.py`; `build_stop_network` in `src/data.py`.
- **Affects:** only the synthetic-demand generator in later stages, if it uses these features.

## D12. Loop detection (CONFIRMED)
- **Value:** is_loop is true when origin equals destination after lower-casing and removing spaces and punctuation,
  so "Mani Majra" = "Manimajra". It matches the sheet's "Loop (single direction)" label for all 68 routes.
- **How to change:** `_place_key` in `src/data.py`.
- **Affects:** τ_r under S2 and S3.

---

# Stage 2: periods, synthetic demand, fuzzy demand

## D13. Time periods (CONFIRMED setting, ASSUMPTION in content)
- **Value:** AM peak 07:00-10:00 (H = 3 h), Midday 10:00-16:00 (6 h), PM peak 16:00-19:00 (3 h).
  These are `PERIODS` in `src/params.py`.
- **Reason:** they match the editable cells B2:C4 of the Operating Windows sheet, where the sheet itself labels them
  "assumption, editable". They are not from the PDF.
- **Sync rule:** `src/data.py::read_period_boundaries` stops the run if the sheet and `params.py` differ. Edit both
  together. If you edit the sheet, re-save it in Excel so the cached Active flags are recalculated.
- **Activity:** a route is active in t when its daily window [first, last departure] overlaps t. The sheet's flags are
  read, and the code asserts that they equal our overlap computation. Active routes: AM 64, Midday 65, PM 62.
- **Affects:** which (r, t) pairs exist in the model, H_t in Z2 (vehicle-km) and per-period demand.

## D14. Time-of-day multipliers m_t (ASSUMPTION, NOT DATA)
- **Value:** AM 1.4, Midday 0.8, PM 1.3 (`DEMAND_MULTIPLIERS`).
- **Reason:** a stylised peaked profile that encodes the usual commuter shape. **No CTU data supports these numbers.**
- **Source of truth:** the Synthetic Demand sheet once it is available; `params.py` holds defaults asserted equal to it.
- **How to change:** in the sheet, then the same values in `params.py`.
- **Affects:** every synthetic D_rt and therefore Z1 and Z3.

## D15. Routes 216 and 241: nominal frequency (CONFIRMED)
- **Fact:** the PDF lists fixed departure times for these routes, not a uniform headway. The "20 min" is nominal.
  (Operating Windows notes; `NOMINAL_FREQUENCY_ROUTES`.)
- **Treatment:** they are modelled as uniform 20 min (3 dep/h). Waiting time for fixed timetables depends on the
  actual departure pattern, so Z1 for these two routes is approximate.
- **Affects:** Z1 and the frequency bounds for 216 and 241 (16 buses in total).

## D16. Routes 20 and 242: extra short trips ignored (ASSUMPTION)
- **Fact:** route 20 has extra fixed trips (ISBT-17 to ISBT-43 at 05.45, 06.45 and 07.45; Kharar to ISBT-43 at 19.00-21.20).
  Route 242 has extra PGI to ISBT-43 short trips from 14.35 to 20.40 (Operating Windows notes).
- **Treatment:** ignored in the base model (`EXTRA_TRIPS_IGNORED_ROUTES`). This may help explain why these routes
  hold more buses than their headway needs.
- **Affects:** baseline vehicle-km and the per-route bus balance for 20 and 242.

## D17. Triangular fuzzy demand spreads (ASSUMPTION)
- **Value:** L = (1 − lo)·M and U = (1 + hi)·M, with lo = 0.20 and hi = 0.35 (`TFN_LO`, `TFN_HI`).
  Per-route overrides go in `TFN_ROUTE_OVERRIDES`.
- **Reason:** right-skewed because demand surges (events, rain, exams) are larger than dips. The values are judgement,
  not estimated from data.
- **How to change:** `params.py`; per route via the overrides dict.
- **Affects:** U, and therefore D_α for every α < 1.

## D18. Defuzzification by upper α-cut (CONFIRMED correction of the synopsis)
- **Value:** D_α = U − α(U − M). α = 1 gives modal demand M; α = 0 gives the most conservative value, U.
- **Reason:** capacity is planned for the high side of demand. The synopsis formula L + (1 − α)(M − L) is the LOWER
  cut and would under-provide capacity.
- **How to change:** `src/demand.py::alpha_cut_upper`. The α value itself is chosen in the optimisation stage.
- **Affects:** the demand used in the overflow constraint o_rt ≥ D_α,rt − C·f_rt.

## D19. Synthetic base demand: generated in code (ASSUMPTION; the student authorised the assumptions)
- **Status:** the workbook has no "Synthetic Demand" sheet. The student told us to make the assumptions ourselves, so the
  demand set is generated in `src/demand.py::base_demand`. All parameters are in `src/params.py`.
- **Formula:** score_r = d_r × (1 + 0.6·serves PGI + 0.4·serves ISBT-43 + 0.3·serves ISBT-17 + 0.3·outskirts
  + 0.3·Derabassi + 0.05·n_hub_stops) × noise_r.
  - noise_r ~ LogNormal(0, 0.15), drawn with numpy `default_rng(42)` in route order.
  - "Serves" means the stop appears in Stop Coverage; "(Express)"-style notes are ignored, so "PGI (Express)" counts as PGI.
  - "Outskirts" means a terminal in `OUTSKIRTS_TERMINALS`, the tri-city belt, classified by place name; please check it
    against a map.
- **Calibration:** D_ref_r = λ·score_r [pax/h at the busiest section], with λ set so that θ·Σ D_ref_r·span_r = 81,326
  boardings/day. θ = 1.8 is a turnover factor (boardings per unit of busiest-section load). A larger θ means less crowded.
  The sensitivity for θ ∈ {1.2, 1.8, 2.5} is in `outputs/tables/theta_sensitivity.csv`.
- **Anchor (UNVERIFIED):** 143,000 CTU-wide daily riders and 684 buses, which the student attributes to Tribune India
  reports. It is a **CTU-wide** figure scaled **pro-rata by fleet**: 143,000 × 389 / 684 ≈ 81,326. This project has not
  checked the source; add the article URL and date before quoting it.
- **Robustness:** across 20 other seeds, the Spearman rank correlation of D_ref with seed 42 is 0.86-0.94, and the
  number of overloaded AM pairs is 8-10 (11 with seed 42) (`outputs/tables/seed_robustness.csv`).
- **How to change:** the parameters in `params.py`, or replace `base_demand` with real data (`docs/REAL_DEMAND_DATA.md`).
- **Every demand number is synthetic and illustrative.** None of it is CTU ridership.

## D20. Partial-period service (DECIDED: overlap hours)
- **Fact:** 21 active (r, t) pairs run for only part of the period. For example, route 11 runs 0.67 h of the 3 h PM
  peak, and 2G and 14 run 1.5 h of the AM peak (`data/processed/periods_rt.csv`, column overlap_h).
- **Decision:** the model uses overlap_h_rt as H_rt in Z2 and Z3 (`ModelConfig.hours_mode = "overlap"`). Using the full
  H_t would overstate both by up to about 4.5× for these pairs. `hours_mode = "full"` reproduces the brief literally.
- **Affects:** Z2, Z3 and Z1_daily.

---

# Stage 3: optimisation model (docs/MODEL.md)

## D21. Route-specific headway menu (ASSUMPTION, needed for feasibility)
- **Value:** K_r = K ∪ {published shortest headway, published longest headway}.
- **Reason:** with K = {10, …, 90} alone, routes with a single published headway of 35, 50, 55, 75 or 80 min (26, 214,
  2G, 37, 213, 8, 28A, 24A, 101, 31) have no menu value inside [f_min, f_max]. C4 would then make the model infeasible,
  and the published schedule could not be represented.
- **How to change:** `ModelConfig.menu_min`; the published values are always added (`model.route_menu`).
- **Affects:** C4 and the set of available frequencies.

## D22. Spare ratio in the model: s = 0.08, B_eff = 357 (ASSUMPTION; s = 0.10 is infeasible)
- **Definition (from the Stage 3 brief):** B_eff = floor((1 − s)·389). This replaces the Stage 1 D5 convention of B/(1 + s).
- **Why not 10%:** B_eff would be 350. The published minimum frequencies with integer buses (Σ⌈f_min·τ⌉) already need
  343-344 buses. Adding the C5 practicality bounds raises this to **352 (AM) and 353 (Midday) > 350**, so the model has
  no feasible solution. This is tested.
  The published allocation itself keeps 380-385 buses on the road, which implies only about 1% spares.
- **How to change:** `ModelConfig.spare_ratio`. `model.presolve_report` explains any infeasibility.
- **Affects:** C1 and how much room the optimiser has.

## D23. Bus capacity C = 60 pax/bus (ASSUMPTION)
- Seated plus standing for a standard 12 m bus at a comfortable load. CTU fleet specifications are not in the files.
  Change with `BUS_CAPACITY` / `ModelConfig.C`. It affects Z3 and the load factors.

## D24. Vehicle-km convention (CONFIRMED by the Stage 1 calibration)
- f_rt counts departures per hour in each direction, and a bus cycle gives one departure each way.
  d_cycle_r = 2·d_r for non-loop routes and d_r for loops. Z2 = Σ d_cycle·H·f [veh-km/day].

## D25. Practicality bound with a minimum of ±1 bus (ASSUMPTION, deviation from the brief)
- **Brief:** |x − x0| ≤ min(3, 0.3·x0). With integer x, this freezes every route with x0 ≤ 3. Route 40 then needs 4 buses
  at f_min (τ = 3.08 h) but may hold only 3, so the model is infeasible.
- **Value:** dev = max(1, min(3, 0.3·x0)) (`pract_min = 1`). `pract_min = 0` gives the brief's literal rule.
- **Affects:** C5 and feasibility.

## D26. Equity cap soft by default (ASSUMPTION)
- Hard caps of 60 min in the peaks conflict with published headways of 75-90 min (8, 23B, 28A, 31, 101) under the
  published f_max. Soft mode adds 1 unit of penalty per minute above the cap. Hard mode is feasible only with
  `fmax_mode = "relaxed"`. Change with `ModelConfig.equity_mode` / `equity_weight`.

## D27. Defaults: α = 0.5, headway CV = 0.3 (ASSUMPTION)
- α = 0.5 plans capacity for D_α = 1.175·M. The Pareto stage will vary it.
- CV_h = 0.3 is used only for Excess Wait Time. There is no AVL data, so it is not measured.

## D28. Solver: PuLP 4.0.1 + HiGHS (CONFIRMED)
- PuLP 4 no longer bundles CBC. HiGHS (`highspy`) is used. The full model (651 variables, 576 constraints) solves in
  under 0.1 s. CBC is still selectable if a `cbc` executable is installed.

## Future work (out of scope for now)
- **Zimmermann-style fuzzy goal programming:** linear membership functions for aspiration levels of Z1-Z3, then
  maximise the minimum satisfaction λ. This is noted only; it is not implemented.

---

# Stage 4: goal programming (docs/GOAL_PROGRAMMING.md)

## D29. Goal targets and normalisation (ASSUMPTION; brief defaults)
- **Targets:** T1 = 0.85·Z1_base, T2 = 0, T3 = Z2_base, and G4 = 0 minutes above the caps. The baseline is the published
  schedule evaluated at the same α and f_max mode. κ1 is set in `config/gp_scenarios.json`.
- **Scales** for the weighted and Chebyshev methods are the baseline values (Z1, Z3, Z2, equity excess = 210 min).
- **Affects:** every Stage 4 result. G3 is never binding: the hard fleet limit (357 vs 385 buses today) already cuts
  vehicle-km by about 2.3%. So P-OPERATOR gives the same schedule as P-PASSENGER. A tighter T3 would create a real
  operator trade-off.

## D30. Lock tolerance and MIP gap (CONFIRMED technical choice)
- Each priority level is locked with dev ≤ achieved + 1e-6 + 1e-7·|achieved|. The relative part is needed because Z1
  is about 1.8e5. Solves use HiGHS with gapRel = 1e-6, so locked values are true optima, not 1e-4-gap approximations.

## D31. "Tidy" solve (ASSUMPTION)
- After the goal levels, one more solve minimises Σx with all goals locked. Buses do not enter Z1-Z3, so without
  this step the fleet in the outputs would be arbitrary.

## D32. Both f_max modes are reported (DECISION for transparency)
- With published f_max bounds, every scenario gives the same schedule. No goal conflicts, because the overloaded
  routes are already at their maximum frequency. With relaxed f_max (two more menu levels), G2 and G4 conflict and
  the priorities change the answer. The brief's question "which priority?" only has content in relaxed mode.

---

# Stage 5: Pareto front (docs/LITERATURE.md)

## D33. Front computed in relaxed f_max mode, α = 0.5 (DECISION)
- With published bounds the objectives barely conflict (Stage 4), so there would be almost no front.
  Change with `PARETO_FMAX_MODE` / `PARETO_ALPHA` in `src/params.py`.

## D34. AUGMECON settings (CONFIRMED method; Mavrotas 2009)
- Lexicographic payoff table. The grid is 10 × 10 over Z1 and Z2 from nadir to ideal. The objective is
  Z3/r3 − 1e-3·(s1/r1 + s2/r2), normalised so that the 1e-6 MIP gap is far below the augmentation term.
- Early exit: once a cell is infeasible, tighter e2 values are skipped and logged.
- The 3 payoff rows are added to the exact set, since they are efficient by construction.
- Nadir is the payoff-table estimate (it may underestimate the true nadir; Nikas et al. 2020 discuss this).

## D35. NSGA-II settings (brief; Deb et al. 2002)
- DEAP 1.4, population 200, 300 generations, uniform crossover p = 0.9, per-gene reset mutation p = 1/191,
  seeds 1-5. Non-dominated sorting uses `nd="log"`. Seeds run in parallel processes; each is deterministic.
- Encoding: index into the route-period headway menu. Repair: first C5 (and with it C2), then C1 per period, by
  lengthening the headway with the smallest normalised loss (ΔZ1/s1 + ΔZ3/s3 + ΔZ2/s2) per bus released.
  Scales s are the baseline values. The repaired genome is written back (Lamarckian).
- Buses are set to their minimum, max(C5 lower bound, ⌈f·τ⌉), for every reported point of both methods.

## D36. Front metrics (CONFIRMED; Zitzler & Thiele 1999, Riquelme et al. 2015, Jiang et al. 2014)
- Normalisation: 0 = ideal, 1 = payoff nadir. The hypervolume reference point is 1.1 in every objective (exact
  3-D slicing algorithm).
- GD and IGD use the mean-distance form (p = 1). C(A, B) uses weak dominance.
- An added strict-dominance count shows that NSGA-II never strictly dominates an AUGMECON point; the run aborts if it does.

---

# Stage 6: simulation and sensitivity

## D37. Monte Carlo design (ASSUMPTION; brief defaults)
- N = 2000 scenarios, seed 2026. D = Triangular(L, M, U) × shock, with shock ~ Normal(1, 0.05) common to all
  route-periods in a scenario.
- Common random numbers: every schedule sees the same draws. Change with `SIM_*` in `src/params.py`.

## D38. Waiting under irregular headways (CONFIRMED formula)
- Gamma headways with CV 0.3. E[W] = (h/2)(1 + CV²) for random arrivals; tested against a direct gamma simulation.
  Bunching changes waiting only, not capacity (stated limitation).

## D39. Schedules compared (DECISION)
- Baseline (x0, mid frequency), and the 4 GP priority scenarios at α = 0.5 and α = 0 with f_max relaxed (as in Stage 5).
- The knee is the point of the combined AUGMECON ∪ NSGA-II front closest to the ideal in normalised space
  (L2 compromise).

## D40. Sensitivity policy and infeasible settings (DECISION)
- The tornado and one-factor-at-a-time analysis use P-BALANCED (`SIM_POLICY`), re-optimised at every setting.
  The baseline is the same published schedule, evaluated under each setting.
- Infeasible settings (v = 18; s = 0.1 or 0.2; fleet cuts of 5% or 10%) are reported with the presolve reason. In all
  of them the published minimum frequencies need more buses than B_eff. They are not hidden or relaxed.

## D41. Out-of-sample test (ASSUMPTION)
- Optimise with the design TFN (lo = 0.20, hi = 0.35, α-cut). Evaluate on demand with both spreads × 1.5 and a
  shock sd of 0.10, with a different seed.

---

# Judgment calls on the open decisions (2026-10-15)

The student asked for these decisions to be made from literature and data. Each entry gives the decision, the
evidence (references are numbered as in `docs/LITERATURE.md`, not yet LibKey-verified), and its effect. They replace
the "PENDING STUDENT CONFIRMATION" status of D2-D5, D20, D22, D25, D33 and the open questions of Stages 4-6.
**CTU confirmation is still the real test for D42-D45.**

## D42. Calibration: S2 one-way reading, v = 22 km/h, layover 10% (DECIDED)
- **Evidence, data:** under S1, 57 of 68 routes would hold more buses than their highest published frequency needs,
  and about 55% of the fleet would be idle. Only S2 makes the published timetable consistent with the allocation.
  CTU actually runs these frequencies with 389 buses, so the effective network speed must be at least 19.3 km/h
  (10% layover, no spares); 18 km/h contradicts the timetable.
- **Evidence, literature:** GPS studies of Indian city buses report 17.8 km/h in the peak and 21.5 km/h off-peak in
  Chennai [14], with more than 90% of trips below 30 km/h [15]. Chandigarh's planned sector grid makes the upper end
  plausible, so 22 km/h is at the top of the Indian range, and 26 km/h is an optimistic upper case.
- **Effect:** the speed result is reported as a range: 18 km/h infeasible, 26 km/h raises the wait improvement from
  3.3% to 7.6%.

## D43. One network-wide speed, no route-specific speeds (DECIDED)
- Speeds vary strongly by place and time [16], but there are no route-level running-time data. Route-specific values
  would be invented, so the uniform speed stays, stated as a limitation. Routes 40 and 76 are explained in Stage 1.

## D44. Route 37 (DECIDED: no action)
- It is a night service (21:10-03:50), active in none of the modelled periods, so it never enters the optimisation.
  Its odd speed requirement stays documented as a data note.

## D45. Spares and the meaning of 389 (DECIDED)
- The 389 buses are route allocations, i.e. scheduled buses. Spare ratios are agency-specific and should follow the
  maintenance policy [17][18], and the files contain no CTU maintenance data.
- **Headline:** s = 0.08 and B_eff = floor(0.92·389) = 357, with the brief's (1 − s)·B definition (D22). This is the
  conservative reading: the optimiser gets 28 fewer buses than the published schedule uses, so any gain comes
  "without additional vehicles".
- s = 0 is the optimistic bound (wait improvement 3.7%). s ≥ 0.10 is infeasible.

## D46. Layover kept at 10%, tested at 5-15% (DECIDED)
- Running-time reliability depends on departure delays, signals and stop spacing [19][20], so recovery time is
  needed. Its size is uncertain, so it is tested.
- **New finding:** at 15% layover the model is infeasible (minimum buses exceed 357), and at 5% the wait improvement
  rises to 5.9%. The 10% assumption sits close to the fleet's feasibility edge, which is a key caveat.

## D47. Robust variant tested and rejected (DECIDED)
- Following the price-of-robustness idea of adjustable conservatism [21], P-BALANCED was re-planned at α = 0 on an
  uncertainty set 1.5 times wider.
- It did worse: P(overflow > 5%) was 6.6% in-sample vs 2.8%, and 33.4% out-of-sample vs 28.8% for plain P-BALANCED.
  With the fleet fixed, inflating every route's design demand cannot add capacity. It also inflates the
  baseline-normalised overflow scale, which lowers the effective weight on overflow (the normalisation effect
  described in [25]).
- **Conclusion:** robustness here must come from capacity (fleet or bus size) or real demand data, not from a more
  pessimistic α. The variant stays in the outputs as a negative result.

## D48. G1 target κ1 = 0.04 (DECIDED; was 0.15)
- GP targets should be attainable aspiration levels, and how targets and weights are assigned shapes the answer [25].
  The best possible waiting cut (ideal) is −4.9% with relaxed f_max, so 15% made G1 a plain "minimise" goal in every
  run. At 4% the target lies inside the attainable range: P-BALANCED and P-EQUITY now meet it.

## D49. G3 target κ3 = 0.03 (DECIDED; was 0)
- "No more vehicle-km than today" never bound, because the fleet limit already cuts vehicle-km by about 2.5%.
  At −3% (the ideal is −6.3%) the operator priority now matters: P-OPERATOR meets G3 at −3.0% vehicle-km, while
  P-PASSENGER does not.

## D50. Headline f_max mode: relaxed; published kept as "today's rules" check (DECIDED)
- Only relaxed mode has real trade-offs (Stages 4-5). Relaxing allows up to two menu levels shorter than the published
  minimum headway, which would need CTU approval. Terminal and stop capacity at those headways is not checked.

## D51. Headline policy: P-BALANCED (DECIDED)
- **Evidence:** waiting time is valued at about 1.9 times in-vehicle time [23], and standing at about 2.3 times seated
  time [22]. Waiting (Z1) and crowding (Z3) are both first-order concerns, so ranking one strictly above the other
  has no evidential basis. Crowding values also do not transfer cleanly between cities [24], so equal
  baseline-normalised weights are the most defensible choice.
- **Result:** P-BALANCED meets 3 of 4 goals (G1, G3, G4; G2 = 0 overflow is unattainable by design). With α = 0.5 it
  gives, in simulation, 3.3% less waiting, 29.5% less overflow, 3.1% fewer vehicle-km, no headways above the cap,
  P(overflow > 5%) = 2.8%, on 357 vs 385 buses.
- **Alternative to report:** P-PASSENGER (lowest crowding risk, 1.4%, but 100 minutes above the equity caps).
- **Caveat:** P-BALANCED is dominated in the 3-objective (Z1, Z2, Z3) space (distance 0.068). It buys full equity
  (the 4th criterion) with a little overflow, which should be stated in the viva.

## D52. Pareto settings: 20 × 20 AUGMECON grid; no published-bounds front (DECIDED)
- AUGMECON2 shows that grid density determines how completely the exact Pareto set of an integer programme is
  recovered [2]. The 20 × 20 grid raises the exact front from 18 to 46 efficient points, and its hypervolume from
  0.889 to 0.946, in 60 s.
- The published-bounds front is not computed: Stage 4 showed the objectives barely conflict there.

## D53. No relaxed-minimum-frequency fleet-cut run (DECIDED)
- The published minimum frequencies are service commitments. Cutting them to free buses would mainly hurt
  low-demand, long-headway routes, which contradicts the equity goal (G4). Fleet cuts beyond 357 are therefore
  reported as infeasible, a boundary of the result, and not "solved" by lowering service.

## D54. Overflow treatment unchanged (DECIDED)
- Z3 counts passengers above C = 60. It is not converted to money with crowding multipliers, because European
  multipliers [22][23] do not transfer to Chandigarh [24].

## D55. Still open, outside the model's control
- LibKey verification of every reference (connector authorisation needed).
- The source URL and date of the Tribune anchor (143,000 riders, 684 buses); it remains unverified.
- CTU confirmation that route length is one-way (D2/D42) and what the 389 buses include (D45).
- Real ridership (`docs/REAL_DEMAND_DATA.md`); without it, every result stays synthetic and illustrative.
