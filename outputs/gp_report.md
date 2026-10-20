# Stage 4: Goal programming with priorities

> **Synthetic demand, illustrative.** Targets are relative to the published baseline evaluated with the same α.

Targets: G1 waiting Z1 ≤ (1 − 0.04)·baseline; G2 unserved Z3 = 0;
G3 vehicle-km Z2 ≤ (1 − 0.03)·baseline;
G4 headways ≤ caps (60/90/60 min). The fleet limit (B_eff = 357) and the frequency-fleet link are hard.
Scenarios come from `config/gp_scenarios.json`.

## Results at α = 0.5
| scenario | fmax_mode | Z1 | Z2 | Z3 | fleet_used | mean_wait_min | equity_excess_min | pct_Z1 | pct_Z2 | pct_Z3 | status | wall_s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BASELINE (published) | published | 184776.6 | 79478.3 | 3086.2 | 385 | 16.6 | 210.0 | 0.0 | 0.0 | 0.0 | n/a | 0.0 |
| P-PASSENGER | published | 186199.1 | 77684.1 | 3066.6 | 357 | 16.7 | 210.0 | 0.8 | -2.3 | -0.6 | Optimal | 0.1 |
| P-OPERATOR | published | 186641.2 | 77068.3 | 3066.6 | 357 | 16.8 | 210.0 | 1.0 | -3.0 | -0.6 | Optimal | 0.5 |
| P-EQUITY | published | 186199.1 | 77684.1 | 3066.6 | 357 | 16.7 | 210.0 | 0.8 | -2.3 | -0.6 | Optimal | 0.2 |
| P-BALANCED | published | 186582.9 | 77111.0 | 3066.6 | 357 | 16.8 | 210.0 | 1.0 | -3.0 | -0.6 | Optimal | 0.1 |
| CHEBYSHEV | published | 186582.9 | 77111.0 | 3066.6 | 357 | 16.8 | 210.0 | 1.0 | -3.0 | -0.6 | Optimal | 0.1 |
| BASELINE (published) | relaxed | 184776.6 | 79478.3 | 3086.2 | 385 | 16.6 | 210.0 | 0.0 | 0.0 | 0.0 | n/a | 0.0 |
| P-PASSENGER | relaxed | 177430.2 | 77466.1 | 2173.1 | 357 | 15.9 | 100.0 | -4.0 | -2.5 | -29.6 | Optimal | 0.4 |
| P-OPERATOR | relaxed | 177732.9 | 77087.9 | 2173.1 | 357 | 16.0 | 100.0 | -3.8 | -3.0 | -29.6 | Optimal | 0.4 |
| P-EQUITY | relaxed | 177349.8 | 77041.4 | 2269.9 | 357 | 15.9 | 0.0 | -4.0 | -3.1 | -26.4 | Optimal | 0.2 |
| P-BALANCED | relaxed | 177285.9 | 77045.5 | 2269.9 | 357 | 15.9 | 0.0 | -4.1 | -3.1 | -26.4 | Optimal | 0.1 |
| CHEBYSHEV | relaxed | 177686.9 | 77096.6 | 2173.1 | 357 | 16.0 | 100.0 | -3.8 | -3.0 | -29.6 | Optimal | 0.3 |

![GP % change](figures/gp_pct_change.png)

## Goal achievement at α = 0.5
| scenario | fmax_mode | goal | priority | target | achieved | unwanted_dev | met | best_possible | reason_if_unmet |
|---|---|---|---|---|---|---|---|---|---|
| P-PASSENGER | published | G1 | 2 | 177385.5 | 186199.1 | 8813.6 | False | 186199.1 | target beyond the best possible value (ideal) |
| P-PASSENGER | published | G2 | 1 | 0.0 | 3066.6 | 3066.6 | False | 3066.6 | target beyond the best possible value (ideal) |
| P-PASSENGER | published | G3 | 4 | 77093.9 | 77684.1 | 590.2 | False | 74501.1 | traded off for a higher-priority goal |
| P-PASSENGER | published | G4 | 3 | 0.0 | 210.0 | 210.0 | False | 210.0 | target beyond the best possible value (ideal) |
| P-OPERATOR | published | G1 | 3 | 177385.5 | 186641.2 | 9255.7 | False | 186199.1 | target beyond the best possible value (ideal) |
| P-OPERATOR | published | G2 | 2 | 0.0 | 3066.6 | 3066.6 | False | 3066.6 | target beyond the best possible value (ideal) |
| P-OPERATOR | published | G3 | 1 | 77093.9 | 77068.3 | 0.0 | True | 74501.1 |  |
| P-OPERATOR | published | G4 | 4 | 0.0 | 210.0 | 210.0 | False | 210.0 | target beyond the best possible value (ideal) |
| P-EQUITY | published | G1 | 3 | 177385.5 | 186199.1 | 8813.6 | False | 186199.1 | target beyond the best possible value (ideal) |
| P-EQUITY | published | G2 | 2 | 0.0 | 3066.6 | 3066.6 | False | 3066.6 | target beyond the best possible value (ideal) |
| P-EQUITY | published | G3 | 4 | 77093.9 | 77684.1 | 590.2 | False | 74501.1 | traded off for a higher-priority goal |
| P-EQUITY | published | G4 | 1 | 0.0 | 210.0 | 210.0 | False | 210.0 | target beyond the best possible value (ideal) |
| P-BALANCED | published | G1 | weighted | 177385.5 | 186582.9 | 9197.4 | False | 186199.1 | target beyond the best possible value (ideal) |
| P-BALANCED | published | G2 | weighted | 0.0 | 3066.6 | 3066.6 | False | 3066.6 | target beyond the best possible value (ideal) |
| P-BALANCED | published | G3 | weighted | 77093.9 | 77111.0 | 17.0 | False | 74501.1 | traded off for a higher-priority goal |
| P-BALANCED | published | G4 | weighted | 0.0 | 210.0 | 210.0 | False | 210.0 | target beyond the best possible value (ideal) |
| CHEBYSHEV | published | G1 | weighted | 177385.5 | 186582.9 | 9197.4 | False | 186199.1 | target beyond the best possible value (ideal) |
| CHEBYSHEV | published | G2 | weighted | 0.0 | 3066.6 | 3066.6 | False | 3066.6 | target beyond the best possible value (ideal) |
| CHEBYSHEV | published | G3 | weighted | 77093.9 | 77111.0 | 17.0 | False | 74501.1 | traded off for a higher-priority goal |
| CHEBYSHEV | published | G4 | weighted | 0.0 | 210.0 | 210.0 | False | 210.0 | target beyond the best possible value (ideal) |
| P-PASSENGER | relaxed | G1 | 2 | 177385.5 | 177430.2 | 44.7 | False | 175794.9 | traded off for a higher-priority goal |
| P-PASSENGER | relaxed | G2 | 1 | 0.0 | 2173.1 | 2173.1 | False | 2173.1 | target beyond the best possible value (ideal) |
| P-PASSENGER | relaxed | G3 | 4 | 77093.9 | 77466.1 | 372.2 | False | 74501.1 | traded off for a higher-priority goal |
| P-PASSENGER | relaxed | G4 | 3 | 0.0 | 100.0 | 100.0 | False | 0.0 | traded off for a higher-priority goal |
| P-OPERATOR | relaxed | G1 | 3 | 177385.5 | 177732.9 | 347.4 | False | 175794.9 | traded off for a higher-priority goal |
| P-OPERATOR | relaxed | G2 | 2 | 0.0 | 2173.1 | 2173.1 | False | 2173.1 | target beyond the best possible value (ideal) |
| P-OPERATOR | relaxed | G3 | 1 | 77093.9 | 77087.9 | 0.0 | True | 74501.1 |  |
| P-OPERATOR | relaxed | G4 | 4 | 0.0 | 100.0 | 100.0 | False | 0.0 | traded off for a higher-priority goal |
| P-EQUITY | relaxed | G1 | 3 | 177385.5 | 177349.8 | 0.0 | True | 175794.9 |  |
| P-EQUITY | relaxed | G2 | 2 | 0.0 | 2269.9 | 2269.9 | False | 2173.1 | target beyond the best possible value (ideal) |
| P-EQUITY | relaxed | G3 | 4 | 77093.9 | 77041.4 | 0.0 | True | 74501.1 |  |
| P-EQUITY | relaxed | G4 | 1 | 0.0 | 0.0 | 0.0 | True | 0.0 |  |
| P-BALANCED | relaxed | G1 | weighted | 177385.5 | 177285.9 | 0.0 | True | 175794.9 |  |
| P-BALANCED | relaxed | G2 | weighted | 0.0 | 2269.9 | 2269.9 | False | 2173.1 | target beyond the best possible value (ideal) |
| P-BALANCED | relaxed | G3 | weighted | 77093.9 | 77045.5 | 0.0 | True | 74501.1 |  |
| P-BALANCED | relaxed | G4 | weighted | 0.0 | 0.0 | 0.0 | True | 0.0 |  |
| CHEBYSHEV | relaxed | G1 | weighted | 177385.5 | 177686.9 | 301.4 | False | 175794.9 | traded off for a higher-priority goal |
| CHEBYSHEV | relaxed | G2 | weighted | 0.0 | 2173.1 | 2173.1 | False | 2173.1 | target beyond the best possible value (ideal) |
| CHEBYSHEV | relaxed | G3 | weighted | 77093.9 | 77096.6 | 2.6 | False | 74501.1 | traded off for a higher-priority goal |
| CHEBYSHEV | relaxed | G4 | weighted | 0.0 | 100.0 | 100.0 | False | 0.0 | traded off for a higher-priority goal |

**Goals not met, counted over all runs (scenarios × α × f_max modes):**
| goal | reason_if_unmet | n_runs |
|---|---|---|
| G1 | target beyond the best possible value (ideal) | 25 |
| G1 | traded off for a higher-priority goal | 12 |
| G2 | target beyond the best possible value (ideal) | 50 |
| G3 | traded off for a higher-priority goal | 26 |
| G4 | target beyond the best possible value (ideal) | 25 |
| G4 | traded off for a higher-priority goal | 15 |

## Ideal and nadir (payoff table at α = 0.5)
Each objective was minimised alone, with a 1e-4 normalised tie-break on the others. The ideal is the diagonal;
the nadir is the worst value of each objective across those single-objective optima.
| fmax_mode | minimised | Z1 | Z3 | Z2 | equity_excess_min | fleet_used |
|---|---|---|---|---|---|---|
| published | Z1 | 186199.1 | 3066.6 | 77684.1 | 210.0 | 357 |
| published | Z3 | 188544.6 | 3066.6 | 75855.8 | 210.0 | 357 |
| published | Z2 | 193752.9 | 3286.4 | 74501.1 | 210.0 | 354 |
| published | equity_excess_min | 189225.0 | 3081.8 | 75706.3 | 210.0 | 357 |
| relaxed | Z1 | 175794.9 | 2321.3 | 77440.1 | 0.0 | 357 |
| relaxed | Z3 | 178822.3 | 2173.1 | 76335.8 | 100.0 | 357 |
| relaxed | Z2 | 193752.9 | 3286.4 | 74501.1 | 210.0 | 355 |
| relaxed | equity_excess_min | 177291.5 | 2269.9 | 76282.5 | 0.0 | 357 |

## Z3 % change vs baseline across α
| fmax_mode | scenario | 0.0 | 0.25 | 0.5 | 0.75 | 1.0 |
|---|---|---|---|---|---|---|
| published | CHEBYSHEV | 0.4 | -0.3 | -0.6 | -0.8 | -1.1 |
| published | P-BALANCED | 0.4 | -0.3 | -0.6 | -0.8 | -1.1 |
| published | P-EQUITY | 0.4 | -0.3 | -0.6 | -0.8 | -1.1 |
| published | P-OPERATOR | 0.4 | -0.3 | -0.6 | -0.8 | -1.1 |
| published | P-PASSENGER | 0.4 | -0.3 | -0.6 | -0.8 | -1.1 |
| relaxed | CHEBYSHEV | -18.6 | -23.5 | -29.6 | -35.4 | -38.4 |
| relaxed | P-BALANCED | -14.7 | -20.6 | -26.4 | -31.9 | -35.0 |
| relaxed | P-EQUITY | -14.7 | -20.6 | -26.4 | -31.9 | -35.0 |
| relaxed | P-OPERATOR | -18.6 | -23.5 | -29.6 | -35.4 | -38.4 |
| relaxed | P-PASSENGER | -18.6 | -23.5 | -29.6 | -35.4 | -38.4 |

## Route-level changes (α = 0.5, relaxed f_max; all modes in `outputs/tables/gp_route_changes.csv`)
Route fleet = max over periods of x_rt. Headways are shown for the period that sets the route's bus count (ref_period).
"Demand" reasons come from baseline load and waiting; "supply" reasons come from buses vs cycle time.

**P-PASSENGER (f_max relaxed)**

| direction | route_no | x0 | x_new | delta | ref_period | headway_base | headway_new | reason_type | reason |
|---|---|---|---|---|---|---|---|---|---|
| gain | 31 | 3 | 4 | 1 | AM | 80 | 60 | demand | overcrowded at baseline (peak LF 2.45): headway 80→60 min |
| gain | 28A | 2 | 3 | 1 | Midday | 80 | 60 | demand | overcrowded at baseline (peak LF 2.17): headway 80→60 min |
| gain | 101 | 2 | 3 | 1 | Midday | 80 | 60 | demand | overcrowded at baseline (peak LF 2.07): headway 80→60 min |
| gain | 40 | 3 | 4 | 1 | AM | 60 | 60 | supply | baseline short of buses for its own timetable (f·τ = 3.08 > 3) |
| gain | 70A | 3 | 4 | 1 | AM | 60 | 45 | demand | overcrowded at baseline (peak LF 1.46): headway 60→45 min |
| gain | 8 | 2 | 3 | 1 | AM | 75 | 45 | demand | overcrowded at baseline (peak LF 1.39): headway 75→45 min |
| gain | 213 | 4 | 5 | 1 | PM | 52 | 45 | demand | overcrowded at baseline (peak LF 1.25): headway 52→45 min |
| gain | 214 | 6 | 7 | 1 | AM | 35 | 30 | demand | overcrowded at baseline (peak LF 1.14): headway 35→30 min |
| gain | 79 | 4 | 5 | 1 | PM | 45 | 40 | demand | overcrowded at baseline (peak LF 1.13): headway 45→40 min |
| gain | 20A | 3 | 4 | 1 | AM | 60 | 40 | demand | overcrowded at baseline (peak LF 1.07): headway 60→40 min |
| lose | 32 | 14 | 11 | -3 | AM | 20 | 25 | supply | surplus buses: x0 = 14 vs f·τ = 11.31 at baseline frequency |
| lose | 551 | 9 | 7 | -2 | AM | 10 | 10 | supply | surplus buses: x0 = 9 vs f·τ = 6.60 at baseline frequency |
| lose | 206 | 10 | 8 | -2 | AM | 12 | 15 | demand | spare capacity (peak LF 0.14): headway 12→15 min |
| lose | 10 | 8 | 6 | -2 | AM | 17 | 20 | demand | spare capacity (peak LF 0.15): headway 17→20 min |
| lose | 20 | 9 | 7 | -2 | AM | 20 | 25 | demand | spare capacity (peak LF 0.31): headway 20→25 min |
| lose | 38AB | 8 | 6 | -2 | AM | 22 | 25 | demand | spare capacity (peak LF 0.35): headway 22→25 min |
| lose | 5A | 8 | 6 | -2 | AM | 20 | 20 | supply | surplus buses: x0 = 8 vs f·τ = 5.76 at baseline frequency |
| lose | 2F | 10 | 8 | -2 | AM | 22 | 25 | supply | surplus buses: x0 = 10 vs f·τ = 8.37 at baseline frequency |
| lose | 5C | 8 | 6 | -2 | AM | 20 | 20 | supply | surplus buses: x0 = 8 vs f·τ = 5.76 at baseline frequency |
| lose | 242 | 13 | 11 | -2 | AM | 17 | 20 | supply | buses released to meet the fleet limit for higher-priority routes |

**P-OPERATOR (f_max relaxed)**

| direction | route_no | x0 | x_new | delta | ref_period | headway_base | headway_new | reason_type | reason |
|---|---|---|---|---|---|---|---|---|---|
| gain | 31 | 3 | 4 | 1 | AM | 80 | 60 | demand | overcrowded at baseline (peak LF 2.45): headway 80→60 min |
| gain | 28A | 2 | 3 | 1 | Midday | 80 | 60 | demand | overcrowded at baseline (peak LF 2.17): headway 80→60 min |
| gain | 101 | 2 | 3 | 1 | Midday | 80 | 60 | demand | overcrowded at baseline (peak LF 2.07): headway 80→60 min |
| gain | 40 | 3 | 4 | 1 | AM | 60 | 60 | supply | baseline short of buses for its own timetable (f·τ = 3.08 > 3) |
| gain | 70A | 3 | 4 | 1 | AM | 60 | 45 | demand | overcrowded at baseline (peak LF 1.46): headway 60→45 min |
| gain | 8 | 2 | 3 | 1 | AM | 75 | 45 | demand | overcrowded at baseline (peak LF 1.39): headway 75→45 min |
| gain | 213 | 4 | 5 | 1 | PM | 52 | 45 | demand | overcrowded at baseline (peak LF 1.25): headway 52→45 min |
| gain | 214 | 6 | 7 | 1 | AM | 35 | 30 | demand | overcrowded at baseline (peak LF 1.14): headway 35→30 min |
| gain | 79 | 4 | 5 | 1 | PM | 45 | 40 | demand | overcrowded at baseline (peak LF 1.13): headway 45→40 min |
| gain | 20A | 3 | 4 | 1 | AM | 60 | 40 | demand | overcrowded at baseline (peak LF 1.07): headway 60→40 min |
| lose | 32 | 14 | 11 | -3 | AM | 20 | 25 | supply | surplus buses: x0 = 14 vs f·τ = 11.31 at baseline frequency |
| lose | 551 | 9 | 7 | -2 | AM | 10 | 10 | supply | surplus buses: x0 = 9 vs f·τ = 6.60 at baseline frequency |
| lose | 206 | 10 | 8 | -2 | AM | 12 | 15 | demand | spare capacity (peak LF 0.14): headway 12→15 min |
| lose | 10 | 8 | 6 | -2 | AM | 17 | 20 | demand | spare capacity (peak LF 0.15): headway 17→20 min |
| lose | 20 | 9 | 7 | -2 | AM | 20 | 25 | demand | spare capacity (peak LF 0.31): headway 20→25 min |
| lose | 38AB | 8 | 6 | -2 | AM | 22 | 25 | demand | spare capacity (peak LF 0.35): headway 22→25 min |
| lose | 5A | 8 | 6 | -2 | AM | 20 | 20 | supply | surplus buses: x0 = 8 vs f·τ = 5.76 at baseline frequency |
| lose | 2F | 10 | 8 | -2 | AM | 22 | 25 | supply | surplus buses: x0 = 10 vs f·τ = 8.37 at baseline frequency |
| lose | 5C | 8 | 6 | -2 | AM | 20 | 20 | supply | surplus buses: x0 = 8 vs f·τ = 5.76 at baseline frequency |
| lose | 242 | 13 | 11 | -2 | AM | 17 | 20 | supply | buses released to meet the fleet limit for higher-priority routes |

**P-EQUITY (f_max relaxed)**

| direction | route_no | x0 | x_new | delta | ref_period | headway_base | headway_new | reason_type | reason |
|---|---|---|---|---|---|---|---|---|---|
| gain | 31 | 3 | 4 | 1 | AM | 80 | 60 | demand | overcrowded at baseline (peak LF 2.45): headway 80→60 min |
| gain | 28A | 2 | 3 | 1 | AM | 80 | 60 | demand | overcrowded at baseline (peak LF 2.17): headway 80→60 min |
| gain | 101 | 2 | 3 | 1 | AM | 80 | 60 | demand | overcrowded at baseline (peak LF 2.07): headway 80→60 min |
| gain | 40 | 3 | 4 | 1 | AM | 60 | 60 | supply | baseline short of buses for its own timetable (f·τ = 3.08 > 3) |
| gain | 70A | 3 | 4 | 1 | PM | 60 | 45 | demand | overcrowded at baseline (peak LF 1.46): headway 60→45 min |
| gain | 8 | 2 | 3 | 1 | AM | 75 | 45 | demand | overcrowded at baseline (peak LF 1.39): headway 75→45 min |
| gain | 213 | 4 | 5 | 1 | PM | 52 | 45 | demand | overcrowded at baseline (peak LF 1.25): headway 52→45 min |
| gain | 214 | 6 | 7 | 1 | PM | 35 | 30 | demand | overcrowded at baseline (peak LF 1.14): headway 35→30 min |
| gain | 20A | 3 | 4 | 1 | PM | 60 | 45 | demand | overcrowded at baseline (peak LF 1.07): headway 60→45 min |
| gain | 23B | 1 | 2 | 1 | AM | 90 | 45 | demand | busy route (M = 33 pax/h): headway 90→45 min cuts waiting |
| lose | 32 | 14 | 11 | -3 | AM | 20 | 25 | supply | surplus buses: x0 = 14 vs f·τ = 11.31 at baseline frequency |
| lose | 551 | 9 | 7 | -2 | AM | 10 | 10 | supply | surplus buses: x0 = 9 vs f·τ = 6.60 at baseline frequency |
| lose | 206 | 10 | 8 | -2 | AM | 12 | 15 | demand | spare capacity (peak LF 0.14): headway 12→15 min |
| lose | 10 | 8 | 6 | -2 | AM | 17 | 20 | demand | spare capacity (peak LF 0.15): headway 17→20 min |
| lose | 20 | 9 | 7 | -2 | AM | 20 | 25 | demand | spare capacity (peak LF 0.31): headway 20→25 min |
| lose | 38AB | 8 | 6 | -2 | AM | 22 | 25 | demand | spare capacity (peak LF 0.35): headway 22→25 min |
| lose | 5A | 8 | 6 | -2 | AM | 20 | 25 | demand | spare capacity (peak LF 0.47): headway 20→25 min |
| lose | 2F | 10 | 8 | -2 | AM | 22 | 25 | supply | surplus buses: x0 = 10 vs f·τ = 8.37 at baseline frequency |
| lose | 5C | 8 | 6 | -2 | AM | 20 | 20 | supply | surplus buses: x0 = 8 vs f·τ = 5.76 at baseline frequency |
| lose | 242 | 13 | 11 | -2 | AM | 17 | 20 | supply | buses released to meet the fleet limit for higher-priority routes |

**P-BALANCED (f_max relaxed)**

| direction | route_no | x0 | x_new | delta | ref_period | headway_base | headway_new | reason_type | reason |
|---|---|---|---|---|---|---|---|---|---|
| gain | 31 | 3 | 4 | 1 | AM | 80 | 60 | demand | overcrowded at baseline (peak LF 2.45): headway 80→60 min |
| gain | 28A | 2 | 3 | 1 | AM | 80 | 60 | demand | overcrowded at baseline (peak LF 2.17): headway 80→60 min |
| gain | 101 | 2 | 3 | 1 | AM | 80 | 60 | demand | overcrowded at baseline (peak LF 2.07): headway 80→60 min |
| gain | 40 | 3 | 4 | 1 | AM | 60 | 60 | supply | baseline short of buses for its own timetable (f·τ = 3.08 > 3) |
| gain | 70A | 3 | 4 | 1 | PM | 60 | 45 | demand | overcrowded at baseline (peak LF 1.46): headway 60→45 min |
| gain | 8 | 2 | 3 | 1 | AM | 75 | 45 | demand | overcrowded at baseline (peak LF 1.39): headway 75→45 min |
| gain | 213 | 4 | 5 | 1 | PM | 52 | 45 | demand | overcrowded at baseline (peak LF 1.25): headway 52→45 min |
| gain | 214 | 6 | 7 | 1 | PM | 35 | 30 | demand | overcrowded at baseline (peak LF 1.14): headway 35→30 min |
| gain | 20A | 3 | 4 | 1 | PM | 60 | 45 | demand | overcrowded at baseline (peak LF 1.07): headway 60→45 min |
| gain | 23B | 1 | 2 | 1 | AM | 90 | 45 | demand | busy route (M = 33 pax/h): headway 90→45 min cuts waiting |
| lose | 32 | 14 | 11 | -3 | AM | 20 | 25 | supply | surplus buses: x0 = 14 vs f·τ = 11.31 at baseline frequency |
| lose | 551 | 9 | 7 | -2 | AM | 10 | 10 | supply | surplus buses: x0 = 9 vs f·τ = 6.60 at baseline frequency |
| lose | 206 | 10 | 8 | -2 | AM | 12 | 15 | demand | spare capacity (peak LF 0.14): headway 12→15 min |
| lose | 10 | 8 | 6 | -2 | AM | 17 | 20 | demand | spare capacity (peak LF 0.15): headway 17→20 min |
| lose | 20 | 9 | 7 | -2 | AM | 20 | 25 | demand | spare capacity (peak LF 0.31): headway 20→25 min |
| lose | 38AB | 8 | 6 | -2 | AM | 22 | 25 | demand | spare capacity (peak LF 0.35): headway 22→25 min |
| lose | 5A | 8 | 6 | -2 | AM | 20 | 25 | demand | spare capacity (peak LF 0.47): headway 20→25 min |
| lose | 2F | 10 | 8 | -2 | AM | 22 | 25 | supply | surplus buses: x0 = 10 vs f·τ = 8.37 at baseline frequency |
| lose | 5C | 8 | 6 | -2 | AM | 20 | 20 | supply | surplus buses: x0 = 8 vs f·τ = 5.76 at baseline frequency |
| lose | 242 | 13 | 11 | -2 | AM | 17 | 20 | supply | buses released to meet the fleet limit for higher-priority routes |

**CHEBYSHEV (f_max relaxed)**

| direction | route_no | x0 | x_new | delta | ref_period | headway_base | headway_new | reason_type | reason |
|---|---|---|---|---|---|---|---|---|---|
| gain | 31 | 3 | 4 | 1 | AM | 80 | 60 | demand | overcrowded at baseline (peak LF 2.45): headway 80→60 min |
| gain | 28A | 2 | 3 | 1 | Midday | 80 | 60 | demand | overcrowded at baseline (peak LF 2.17): headway 80→60 min |
| gain | 101 | 2 | 3 | 1 | Midday | 80 | 60 | demand | overcrowded at baseline (peak LF 2.07): headway 80→60 min |
| gain | 40 | 3 | 4 | 1 | AM | 60 | 60 | supply | baseline short of buses for its own timetable (f·τ = 3.08 > 3) |
| gain | 70A | 3 | 4 | 1 | AM | 60 | 45 | demand | overcrowded at baseline (peak LF 1.46): headway 60→45 min |
| gain | 8 | 2 | 3 | 1 | AM | 75 | 45 | demand | overcrowded at baseline (peak LF 1.39): headway 75→45 min |
| gain | 213 | 4 | 5 | 1 | PM | 52 | 45 | demand | overcrowded at baseline (peak LF 1.25): headway 52→45 min |
| gain | 214 | 6 | 7 | 1 | AM | 35 | 30 | demand | overcrowded at baseline (peak LF 1.14): headway 35→30 min |
| gain | 79 | 4 | 5 | 1 | PM | 45 | 40 | demand | overcrowded at baseline (peak LF 1.13): headway 45→40 min |
| gain | 20A | 3 | 4 | 1 | AM | 60 | 40 | demand | overcrowded at baseline (peak LF 1.07): headway 60→40 min |
| lose | 32 | 14 | 11 | -3 | AM | 20 | 25 | supply | surplus buses: x0 = 14 vs f·τ = 11.31 at baseline frequency |
| lose | 551 | 9 | 7 | -2 | AM | 10 | 10 | supply | surplus buses: x0 = 9 vs f·τ = 6.60 at baseline frequency |
| lose | 206 | 10 | 8 | -2 | AM | 12 | 15 | demand | spare capacity (peak LF 0.14): headway 12→15 min |
| lose | 10 | 8 | 6 | -2 | AM | 17 | 20 | demand | spare capacity (peak LF 0.15): headway 17→20 min |
| lose | 20 | 9 | 7 | -2 | AM | 20 | 25 | demand | spare capacity (peak LF 0.31): headway 20→25 min |
| lose | 38AB | 8 | 6 | -2 | AM | 22 | 25 | demand | spare capacity (peak LF 0.35): headway 22→25 min |
| lose | 5A | 8 | 6 | -2 | AM | 20 | 20 | supply | surplus buses: x0 = 8 vs f·τ = 5.76 at baseline frequency |
| lose | 2F | 10 | 8 | -2 | AM | 22 | 25 | supply | surplus buses: x0 = 10 vs f·τ = 8.37 at baseline frequency |
| lose | 5C | 8 | 6 | -2 | AM | 20 | 20 | supply | surplus buses: x0 = 8 vs f·τ = 5.76 at baseline frequency |
| lose | 242 | 13 | 11 | -2 | AM | 17 | 20 | supply | buses released to meet the fleet limit for higher-priority routes |

## Lexicographic check
For every preemptive run, the final schedule's deviation at each priority level is ≤ the value locked at that level.
Status: PASS for all runs.
