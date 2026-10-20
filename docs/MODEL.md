# MODEL: corrected multi-objective frequency-setting MILP

Code: `src/model.py` (build and solve), `src/metrics.py` (evaluate any schedule). Knobs: `ModelConfig` in
`src/params.py`. Demand is **synthetic demand, illustrative** (Stage 2).

## Sets
- r ∈ R: 68 routes. t ∈ T = {AM, Midday, PM}. A_rt = 1 if route r runs in period t (Operating Windows).
- K = {10, 12, 15, 20, 25, 30, 40, 45, 60, 90} min. **Route menu** K_r = K ∪ {h_lo_r, h_hi_r}, where h_lo_r and h_hi_r are
  the published headways (DECISIONS D21). f_k = 60 / h_k [dep/h].
- Allowed set K_rt ⊆ K_r (C4, C5 equity):
  - "published": h_lo_r ≤ h ≤ h_hi_r.
  - "relaxed": the lower limit becomes the 2nd level of K below h_lo_r, i.e. two menu levels above f_max.
  - Hard equity additionally requires h ≤ Hcap_t.

## Parameters (units)
| Symbol | Value / source | Unit |
|---|---|---|
| B_eff | floor((1 − s)·B), s = 0.08 → 357 (D22) | buses |
| C | 60 (D23) | pax/bus |
| τ_r | L_r/v·(1 + l), with S2, v = 22, l = 0.10 (Stage 1) | h |
| d_cycle_r | km per bus cycle = 2·d_r for non-loop routes, d_r for loops (D24) | km |
| H_rt | service hours of r inside t (overlap), or H_t in "full" mode (D20) | h |
| M_rt, D_α,rt | modal demand; upper α-cut U − α(U − M), α = 0.5 | pax/h |
| x0_r, f0_r | published buses; mid of published frequency range | buses, dep/h |
| [lb_r, ub_r] | C5 practicality bounds on x | buses |

**Frequency convention.** f_rt counts departures per hour *in each direction* (from each terminal). For loops it is
departures per hour around the loop. One bus cycle produces one departure in each direction. Therefore:
- buses needed = f·τ;
- vehicle-km per hour = f·d_cycle;
- capacity per direction = C·f.

D_rt is the busiest-direction, busiest-section flow.

## Decision variables (active (r, t) only)
- y_rtk ∈ {0, 1} for k ∈ K_rt, with Σ_k y_rtk = 1.
- f_rt = Σ_k f_k·y_rtk and h_rt = Σ_k h_k·y_rtk. Both are linear in y.
- x_rt ∈ ℤ, lb_r ≤ x_rt ≤ ub_r.
- o_rt ≥ 0 [pax/h].

## Constraints
- (C1) Fleet: Σ_r x_rt ≤ B_eff for each t.
- (C2) Frequency-fleet: τ_r·Σ_k f_k·y_rtk ≤ x_rt. Because x_rt is an integer, this is the same as
  x_rt ≥ ⌈f_rt·τ_r⌉.
- (C3) Overflow: o_rt ≥ D_α,rt − C·f_rt, with o_rt ≥ 0.
- (C4) Service bounds: f_min_r ≤ f_rt ≤ f_max_opt_r. This is enforced through the menu K_rt (no extra rows).
- (C5a) Practicality: |x_rt − x0_r| ≤ dev_r, with dev_r = max(pract_min, min(3, 0.3·x0_r)) and pract_min = 1 (D25).
  Applied as integer bounds on x.
- (C5b) Equity: h_rt ≤ Hcap_t, where Hcap = 60 min (AM, PM) and 90 min (Midday).
  - "hard": headways above the cap are removed from K_rt.
  - "soft" (default): the term w_eq·Σ_rtk max(0, h_k − Hcap_t)·y_rtk is added to the objective. The excess for each k is a
    constant, so the penalty is linear.
- (C6) Inactive (r, t): no variables, so f = x = o = 0.

## Objectives (all linear)
- Z1 = Σ_rt M_rt·Σ_k (h_k/2)·y_rtk [pax·min/h]. This is the demand-weighted waiting rate under random arrivals
  (mean wait = h/2). The code also reports Z1_daily = Σ M·(h/2)·H.
- Z2 = Σ_rt d_cycle_r·H_rt·f_rt [veh-km/day]. This replaces the synopsis' d_r·x_rt, which counts buses, not kilometres.
- Z3 = Σ_rt o_rt·H_rt [pax/day]. Passengers above capacity.

**Why M in Z1 but D_α in C3.** Z1 estimates the *expected* passenger experience, so it uses the most plausible
demand. C3 is a safety requirement on capacity, so it uses the conservative upper cut. Using D_α in Z1 would inflate
the weight of uncertain routes without improving service.

The single-objective run (Stage 3) minimises Z3 plus the soft-equity penalty, plus tie-breaks of
1e-6·Z2 + 1e-4·Σx. The tie-breaks pick the cheapest schedule among the ones with equal Z3.

## Evaluation metrics (not optimised): `src/metrics.py`
- Fleet used = max_t Σ_r x_rt.
- Mean wait (demand-weighted) and max wait = h/2 [min].
- Mean load factor LF = M/(C·f), number of pairs with LF > 1, and the Gini coefficient of LF.
- Excess Wait Time: E[W] − h/2 = (h/2)(1 + CV_h²) − h/2 = (h/2)·CV_h², with CV_h = 0.3 (assumed; D27).

## Corrections relative to the synopsis
1. Z1 = Σ D·30/f is nonlinear in f. It becomes linear in the binary headway choice y.
2. Z2 is vehicle-km, d_cycle·f·H, not d·x.
3. Overflow is o ≥ D − C·f. Capacity per hour is C·f, not C·x.
4. Defuzzification uses the upper α-cut U − α(U − M).
