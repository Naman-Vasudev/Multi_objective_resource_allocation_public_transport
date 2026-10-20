# Stage 5: Pareto front and cross-check

> **Synthetic demand, illustrative.** f_max relaxed, α = 0.5, B_eff = 357.
> Minimise (Z1 waiting, Z2 vehicle-km, Z3 unserved). Literature: `docs/LITERATURE.md`.

## Payoff table (lexicographic optimisation, Mavrotas 2009)
| minimised | Z1 | Z2 | Z3 |
|---|---|---|---|
| Z1 | 175794.9 | 77440.1 | 2321.3 |
| Z2 | 193752.9 | 74501.1 | 3286.4 |
| Z3 | 177430.2 | 77466.1 | 2173.1 |

Ideal = diagonal; nadir = column maximum (payoff-table estimate). Normalisation: 0 = ideal, 1 = nadir.

## AUGMECON grid (20 × 20 over Z1 and Z2)
min Z3/r3 − 0.001·(s1/r1 + s2/r2) s.t. Z1 + s1 = e1, Z2 + s2 = e2. The slack terms make every optimum
strictly (not weakly) Pareto-efficient. Once a cell is infeasible, every tighter e2 for the same e1 is skipped.
- Cells solved to optimality: 298; infeasible: 19;
  skipped by early exit: 83. Full log in `outputs/tables/pareto_eps_grid.csv`.
- Infeasible or skipped cells are in the corner where both Z1 and Z2 are pushed towards their ideals: high frequency
  (low waiting) costs vehicle-km, so both cannot be minimal at once.
- Distinct non-dominated points, including the 3 lexicographic payoff rows (efficient by construction):
  **46**, found in 59.7 s.

## NSGA-II (DEAP; population 200, 300 generations, crossover 0.9, mutation 1/n_genes, seeds [1, 2, 3, 4, 5])
Encoding: one gene per active route-period = index into its headway menu. Repair: buses above the C5 limit, then the
fleet C1 per period, are removed by lengthening the headway with the smallest normalised loss per bus released.
The repaired genome is written back (Lamarckian).

## Front comparison (normalised space, hypervolume reference point = 1.1 in every objective)
| method | seed | n_points | hypervolume | GD_to_eps | IGD_eps | C_eps_over_this | C_this_over_eps | eps_points_strictly_dominated | runtime_s | evaluations |
|---|---|---|---|---|---|---|---|---|---|---|
| AUGMECON (exact) | - | 46 | 0.9456 | 0.0000 | 0.0000 | 1.0000 | 1.0000 | 0 | 59.6733 | 326 |
| NSGA-II | 1 | 189 | 0.9681 | 0.0498 | 0.0297 | 0.0476 | 0.0217 | 0 | 24.0036 | 60200 |
| NSGA-II | 2 | 191 | 0.9655 | 0.0478 | 0.0362 | 0.0838 | 0.0217 | 0 | 24.4313 | 60200 |
| NSGA-II | 3 | 194 | 0.9647 | 0.0495 | 0.0334 | 0.1186 | 0.0000 | 0 | 24.3976 | 60200 |
| NSGA-II | 4 | 187 | 0.9645 | 0.0492 | 0.0309 | 0.0963 | 0.0217 | 0 | 23.7879 | 60200 |
| NSGA-II | 5 | 191 | 0.9685 | 0.0477 | 0.0316 | 0.0628 | 0.0217 | 0 | 24.1945 | 60200 |
| NSGA-II union of seeds | all | 611 | 0.9801 | 0.0491 | 0.0209 | 0.0524 | 0.0652 | 0 | 120.8149 | 301000 |

- GD = mean distance from NSGA-II points to the nearest ε-constraint point. IGD = mean distance from ε-constraint
  points to the nearest NSGA-II point; this measures coverage. C(A, B) = share of B weakly dominated by A
  (Zitzler & Thiele 1999). C uses weak dominance, so an identical point counts.
- **Correctness check:** no NSGA-II point strictly dominates any AUGMECON point (column
  eps_points_strictly_dominated = 0 for every seed). The exact points are confirmed efficient.
- NSGA-II per seed: hypervolume 0.9645-0.9685 vs exact 0.9456;
  GD 0.0477-0.0498. The union of seeds reaches HV 0.9801.
- Runtime: AUGMECON 59.7 s for the whole grid. NSGA-II 24.2 s per seed
  (60200 evaluations), with 5 seeds run in parallel in 26.6 s of wall time.

## Goal-programming solutions vs the front
| point | Z1 | Z2 | Z3 | dist_to_front_norm | dominated_by_front | feasible |
|---|---|---|---|---|---|---|
| P-PASSENGER | 177430.2131 | 77466.1071 | 2173.0916 | 0.0000 | False | True |
| P-OPERATOR | 177732.9097 | 77087.8671 | 2173.0916 | 0.0081 | False | True |
| P-EQUITY | 177349.7555 | 77041.4426 | 2269.9078 | 0.0695 | True | True |
| P-BALANCED | 177285.8722 | 77045.4626 | 2269.9078 | 0.0679 | True | True |
| CHEBYSHEV | 177686.9042 | 77096.5871 | 2173.0916 | 0.0046 | False | True |
| BASELINE (published) | 184776.5712 | 79478.2892 | 3086.1961 | 1.0930 | True | False |

Distance is Euclidean in normalised space to the nearest point of the combined non-dominated front
(AUGMECON ∪ NSGA-II). 1 of 5 GP solutions lie exactly on the front: those that put G2
(Z3) first coincide with the lexicographic min-Z3 payoff point. A positive distance with "dominated = False" means
no sampled front point dominates it. P-EQUITY and P-BALANCED optimise equity (G4), which is not one of the three
front objectives, so they are efficient in a 4-D sense and sit just off the 3-D front. The published
baseline breaks the fleet limit (385 > 357 buses), so it is outside the feasible set and is
shown only for reference.

## Discussion
- **The exact method is better here.** At this size (191 route-periods, about 650 variables) one MILP solves in a
  fraction of a second. AUGMECON gives strictly efficient points with a certificate of optimality, plus a list of
  infeasible regions, in 60 s.
- **NSGA-II still matters.** It returns a whole front from one run, needs no linearisation, and would handle
  objectives an MILP cannot: for example, Z1 from a bus-bunching simulation, or a non-linear crowding discomfort
  function. That is why the bus-network literature uses metaheuristics for larger, integrated route-design and
  frequency problems.
- **Read the NSGA-II metrics as a benchmark of the heuristic against the exact front, not the reverse.**
  NSGA-II's higher hypervolume (0.980 vs 0.946) comes from its many points filling
  the gaps between the 46 ε-grid samples, not from beating them. It strictly dominates none of
  them, and its GD of about 0.05 (normalised) shows it stays near the exact surface. A finer
  grid (AUGMECON2-style, Mavrotas & Florios) would raise the exact hypervolume at the cost of more MILP solves.
