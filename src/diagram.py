"""Methodology block diagram (report Chapter 3 / slides). Drawn from the pipeline actually implemented."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

from src import params as P  # noqa: E402
from src.plots import save_fig  # noqa: E402

NAVY, YELLOW, INK, INK2, SURF = "#14304a", "#f2b705", "#0b0b0b", "#52514e", "#ffffff"

STEPS = [
    ("1  Data audit", "CTU timetable (68 routes, 389 buses) → validated route table, stop network"),
    ("2  Calibration", "Cycle time τ = (2d or d)/v · (1 + layover); scenarios S1-S3 vs fleet B"),
    ("3  Demand (synthetic)", "Route score → hourly demand per period → fuzzy (L, M, U); α-cut upper bound"),
    ("4  Corrected MILP", "Headway-menu binaries; fleet, frequency-fleet, overflow, bounds; Z1, Z2, Z3"),
    ("5  Goal programming", "Targets + deviations; preemptive priorities, weighted and Chebyshev GP"),
    ("6  Pareto cross-check", "Exact AUGMECON ε-constraint vs NSGA-II; HV, GD, IGD, coverage"),
    ("7  Simulation", "2000 demand days, gamma headways; trade-offs, sensitivity, out-of-sample"),
]


def block_diagram(path) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 10.2), facecolor=SURF)
    ax.set_xlim(0, 10); ax.set_ylim(0, len(STEPS) * 1.45 + 0.2); ax.axis("off")
    for k, (head, body) in enumerate(STEPS):
        y = (len(STEPS) - 1 - k) * 1.45 + 0.35
        ax.add_patch(FancyBboxPatch((0.6, y), 8.8, 1.0, boxstyle="round,pad=0.02,rounding_size=0.12",
                                    facecolor=NAVY, edgecolor=NAVY))
        ax.text(0.95, y + 0.68, head, color=YELLOW, fontsize=13, fontweight="bold", va="center")
        ax.text(0.95, y + 0.3, body, color="white", fontsize=9.6, va="center")
        if k < len(STEPS) - 1:
            ax.add_patch(FancyArrowPatch((5.0, y), (5.0, y - 0.43), arrowstyle="-|>", mutation_scale=16,
                                         color=INK2, linewidth=1.6))
    fig.tight_layout()
    save_fig(fig, path, dpi=200, facecolor=SURF)
    plt.close(fig)


if __name__ == "__main__":
    block_diagram(P.OUT_FIG / "methodology_block_diagram.png")
