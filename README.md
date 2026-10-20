# Multi-Objective Resource Allocation for Public Bus Transit
### A Real-World Case Study on Chandigarh Transport Undertaking (CTU)

This repository contains the complete mathematical formulation, data audit, calibration, multi-objective optimization (MILP & Goal Programming), and exact Pareto front generation for the fleet allocation and timetable optimization of **Chandigarh Transport Undertaking (CTU)** Depot-1 & Depot-3 city bus operations.

---

## 📌 Project Overview
* **Network:** 68 urban and suburban bus routes in the Chandigarh tricity area.
* **Operating Fleet:** 385 buses published in timetable vs. 357 effective fleet capacity after operational spare requirements.
* **Mathematical Framework:** Linear Multi-Objective Mixed Integer Linear Program (MILP) formulated over discrete headway menus.
* **Uncertainty Modeling:** Triangular Fuzzy Numbers (TFN) representing ridership bounds, optimized over $\alpha$-cuts.
* **Multi-Objective Solution Techniques:**
  1. **Lexicographic Preemptive Goal Programming** (P-PASSENGER, P-OPERATOR, P-EQUITY)
  2. **Weighted & Chebyshev Goal Programming** (P-BALANCED)
  3. **Exact $\varepsilon$-Constraint AUGMECON** mapping the true 3-D Pareto optimal trade-offs.

---

## 🎯 Objectives
All three objectives are minimized simultaneously:
1. **$Z_1$ — Total Passenger Waiting Time** $[pax \cdot min / h]$
2. **$Z_2$ — Total Operating Vehicle-Kilometers** $[veh \cdot km / day]$
3. **$Z_3$ — Unserved Demand / Passenger Crowding Overflow** $[pax / day]$

---

## 📊 Key Findings & Pareto Frontier
* **AUGMECON Exact Front:** Evaluated on a $20 \times 20$ grid (400 MILP cell solves), yielding **46 distinct, strictly non-dominated schedules** in ~60 seconds.
* **Hypervolume Indicator:** **0.946** (captures 94.6% of the normalized 3-D objective space).
* **Published Baseline Flaw:** The published CTU timetable is strictly dominated on all three objectives and violates the 357-bus fleet limit (requires 385 buses).
* **Optimal Trade-Offs:**
  * **P-PASSENGER** lies directly on the exact Pareto front ($dist = 0.000$).
  * **P-BALANCED** sits slightly away ($dist = 0.068$) because it satisfies headway equity ($C_5$), an essential 4th operational policy metric invisible in the 3-D objective space.

---

## 📁 Repository Structure
```
├── config/              # Model configurations and scenario parameters
├── data/                # Processed CTU route attributes, menus, and timetable
├── docs/                # Mathematical formulation, literature review, and reports
├── outputs/             # Generated figures, Pareto fronts, metrics, and CSV tables
│   ├── figures/         # 2-D & 3-D Pareto plots, sensitivity charts, calibration
│   └── tables/          # Payoff tables, distance metrics, and goal achievements
├── src/                 # Core Python source code
│   ├── calibration.py   # Fleet cycle time & utilization calibration
│   ├── model.py         # MILP core building and HiGHS solver interface
│   ├── goals.py         # Goal programming formulations & scenario sweeps
│   ├── pareto.py        # Exact AUGMECON & multi-objective front logic
│   └── plots.py         # High-resolution scientific figures
├── tests/               # Automated test suite (data consistency, MILP presolve)
├── run_all.py           # Single-command pipeline runner
└── requirements.txt     # Python dependencies
```

---

## 🚀 Getting Started

### 1. Installation
Clone the repository and install the dependencies:
```bash
git clone https://github.com/Naman-Vasudev/Multi_objective_resource_allocation_public_transport.git
cd Multi_objective_resource_allocation_public_transport
pip install -r requirements.txt
```

### 2. Reproduce the Complete Pipeline
Run the full data audit, calibration, GP, and Pareto front generation:
```bash
python run_all.py
```

### 3. Generate 2-D and 3-D Pareto Plots (AUGMECON exact)
```bash
python scratch/pareto_no_nsga.py
```

---

## 📜 License & Citation
Developed as part of academic research at PEC / Chandigarh. For academic and transit planning references, please review [`docs/LITERATURE.md`](docs/LITERATURE.md).
