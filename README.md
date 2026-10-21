# Multi-Objective Bus Fleet Allocation under Demand Variability
### Case Study: Chandigarh Transport Undertaking (CTU) · 68 Routes · 389 Buses

[![Tests](https://img.shields.io/badge/Tests-100%20passing-success)](tests/)
[![Solver](https://img.shields.io/badge/Solver-HiGHS%20%2F%20PuLP-blue)](requirements.txt)
[![Python](https://img.shields.io/badge/Python-3.10%2B-informational)](requirements.txt)
[![Docs](https://img.shields.io/badge/Docs-Complete-brightgreen)](docs/)

**Minor Project — B.Tech Mathematics and Computing**  
*Punjab Engineering College (Deemed to be University), Chandigarh*  
*Advisor:* Dr. Sumati Mahajan, Department of Mathematics  
*Primary developer:* **Naman Vasudev** (24112032)

---

## What This Project Does

Urban bus operators must spread a fixed fleet over routes whose demand shifts by time of day. When departures don't match loads, two failures happen simultaneously: high-demand corridors overflow and low-demand ones run near-empty.

This repository is a fully reproducible, open-source optimization engine for bus headway and fleet allocation. Applied to the 68-route CTU network (Depots II, III, IV), it:

1. **Audits and corrects** a published timetable: identifies 17 rounding errors, resolves a cycle-time convention ambiguity, and calibrates fleet utilization to 96.4 %.
2. **Formulates a three-objective MILP** over a discrete headway menu — no fractional buses, no erratic timetables.
3. **Handles demand uncertainty** with triangular fuzzy numbers and α-cut capacity rules (L = 0.80 M, U = 1.35 M).
4. **Applies goal programming** (preemptive lexicographic, weighted, Chebyshev) for operator-defined priority scenarios.
5. **Computes the exact Pareto front** via AUGMECON (augmented ε-constraint MILP), yielding 46 strictly efficient, non-dominated schedules in 60 s.
6. **Stress-tests** every schedule by Monte Carlo simulation (2 000 synthetic demand draws) and one-at-a-time sensitivity analysis.

---

## Key Results

| Schedule | Waiting Z₁ [pax·min/h] | Vehicle-km Z₂ [veh-km/day] | Overflow Z₃ [pax/day] | Fleet used |
|:---|:---:|:---:|:---:|:---:|
| Published CTU baseline | 184 777 | 79 478 | 3 086 | **385 (infeasible)** |
| P-PASSENGER (GP) | 177 430 | 77 466 | 2 173 | 357 ✓ |
| P-OPERATOR (GP) | 177 733 | 77 088 | 2 173 | 357 ✓ |
| CHEBYSHEV (GP) | 177 687 | 77 097 | 2 173 | 357 ✓ |

- **Pareto front:** 46 non-dominated points, hypervolume = 0.946, zero dominated solutions verified.
- **Price of robustness:** Moving from α = 1.0 to α = 0.0 raises vehicle-km by 1.8 % while cutting overflow risk by 29.6 %.

> **Scope note:** Demand is synthetic (scaled to 81 326 boardings/day from a CTU-wide anchor). Results are illustrative pending real ETM ridership data from CTU.

---

## Mathematical Model

### Decision Variables
- $y_{rtk} \in \{0,1\}$ — headway $h_k$ assigned to route $r$, period $t$
- $x_{rt} \in \mathbb{Z}_{\ge 0}$ — buses allocated to route $r$, period $t$
- $o_{rt} \ge 0$ — passengers above seated capacity per hour

### Objectives (simultaneous minimisation)

$$Z_1 = \sum_r M_{rt} \sum_k \tfrac{h_k}{2}\, y_{rtk} \quad [\text{pax·min/h}]$$

$$Z_2 = \sum_r \sum_t d_r^{\text{cyc}} H_{rt} f_{rt} \quad [\text{veh·km/day}]$$

$$Z_3 = \sum_r \sum_t o_{rt} H_{rt} \quad [\text{pax/day}]$$

### Core Constraints
1. **Fleet:** $\sum_r x_{rt} \le B_{\text{eff}} = 357$ (389 buses minus 8 % spares)
2. **Cycle feasibility:** $\tau_r f_{rt} \le x_{rt}$ (22 km/h, 10 % layover)
3. **Overflow:** $o_{rt} \ge D_{rt}^\alpha - C f_{rt},\; o_{rt} \ge 0$, $C = 60$ pax/bus
4. **Headway menu:** $\sum_k y_{rtk} = 1$, $K = \{10,12,15,20,25,30,40,45,60,90\}$ min
5. **Equity cap:** maximum headway 60 min (urban) / 90 min (suburban)

---

## Exact Pareto Front (AUGMECON)

<p align="center">
  <img src="outputs/figures/pareto_2d_no_nsga.png" alt="2D Pareto projections — exact AUGMECON ε-constraint" width="100%"/>
</p>

The exact multi-objective trade-off surface is mapped using the Augmented ε-Constraint method (AUGMECON) across a 20×20 grid (400 MILP sub-problems). The method avoids weakly efficient solutions and eliminates stochastic variation — every point carries a certificate of MILP optimality.

- **Grid solves:** 400 cells → 298 Optimal, 19 Infeasible, 83 skipped by early exit
- **Strictly efficient schedules:** 46 distinct non-dominated points in 59.7 s
- **Hypervolume indicator:** 0.946 (normalized three-objective space)
- **Dominance check:** 0 dominated solutions within the front
- **Published CTU baseline:** strictly dominated across all three objectives and infeasible (385 > 357 buses)

Full metrics in [`outputs/pareto_report.md`](outputs/pareto_report.md).

---

## Sensitivity Analysis

<p align="center">
  <img src="outputs/figures/sensitivity_tornado.png" alt="Sensitivity tornado" width="700"/>
</p>

One-at-a-time (OAT) sweeps over speed, capacity, fleet size, layover, α, and spare ratio. Operating speed is the most influential parameter; robustness cost (α) shows a near-linear trade-off.

---

## Repository Structure

```
config/               # GP scenario targets and model parameters
data/
├── raw/              # Audited CTU published timetable (xlsx)
└── processed/        # Route features, demand matrices, stop tables (CSV)
docs/                 # Technical documentation
├── MODEL.md          # Full formulation and constraint derivations
├── LITERATURE.md     # Verified literature survey
├── DECISIONS.md      # Design decision log (53 entries)
└── GLOSSARY.md       # Transport planning metric definitions
outputs/
├── figures/          # All plots (2D Pareto, sensitivity, simulation)
├── tables/           # Numerical tables (CSV)
└── *.csv / *.md      # Pipeline outputs and markdown reports
src/                  # Production Python modules
├── calibration.py    # Cycle-time and fleet calibration
├── data.py           # Timetable ingestion and audit
├── demand.py         # Triangular fuzzy demand parameterization
├── goals.py          # Goal programming (preemptive, weighted, Chebyshev)
├── metrics.py        # Load factor, Gini equity, waiting time, EWT
├── model.py          # PuLP/HiGHS MILP formulation
├── params.py         # Centralised configuration
├── pareto.py         # AUGMECON ε-constraint exact multi-objective solver
├── plots.py          # Publication-quality figures
└── simulate.py       # Monte Carlo demand simulation
tests/                # 100-test pytest suite
run_all.py            # End-to-end pipeline (one command)
requirements.txt      # Python dependencies
```

---

## Quickstart

```bash
git clone https://github.com/Naman-Vasudev/Multi_objective_resource_allocation_public_transport.git
cd Multi_objective_resource_allocation_public_transport
pip install -r requirements.txt
python run_all.py
```

Skip Stage 5 (Pareto, ~2 min) on subsequent runs:
```bash
python run_all.py --skip-pareto
```

Run the test suite:
```bash
pytest -v
```

---

## Future Work (Phase 2)

The following are planned extensions — **none of the below are implemented yet**:

- **Real ridership data:** Request ETM ticket data from CTU; fit TFN parameters from 10th/50th/90th percentiles of measured boardings at 5–10 major hubs.
- **Metaheuristic comparison:** Implement and compare NSGA-II, PSO, and QPSO against the AUGMECON exact front using hypervolume, GD, IGD, and C-coverage indicators. This will determine whether approximate methods are competitive at larger network scales.
- **Arrival timing model:** Replace half-headway waiting with a bus-bunching / Poisson-arrival model for long-headway routes.
- **Depot and interlining constraints:** Explicit depot-to-route assignment and driver-duty feasibility checks.
- **Conference write-up:** Target CTRG 2027 (Conference of Transportation Research Group of India) and ORSI Annual Convention.

---

## Citation

```bibtex
@misc{vasudev2026multiobjective,
  title   = {Multi-Objective Bus Fleet Allocation under Demand Variability: A Case Study on CTU},
  author  = {Vasudev, Naman and Garg, Daksh and Aggarwal, Piyush and Chauhan, Abhay},
  year    = {2026},
  note    = {Minor project, B.Tech Mathematics and Computing, Punjab Engineering College, Chandigarh.
             Advisor: Dr. Sumati Mahajan},
  url     = {https://github.com/Naman-Vasudev/Multi_objective_resource_allocation_public_transport}
}
```
