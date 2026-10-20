"""Single entry point: `python run_all.py` reproduces every output of the project.

Stages implemented so far:
    1. data audit + cycle-time calibration  (src/stage1.py)
    2. periods, synthetic demand, TFNs       (src/stage2.py)
    3. corrected MILP, baseline metrics      (src/stage3.py)
    4. goal programming with priorities      (src/stage4.py, config/gp_scenarios.json)
    5. Pareto front: AUGMECON + NSGA-II      (src/stage5.py, src/pareto.py; about 2 min)
    6. simulation and sensitivity            (src/stage6.py, src/simulate.py)

`python run_all.py --skip-pareto` reuses saved Stage 5 fronts (faster iteration; the full run regenerates them).
"""
import logging
import sys

from src import params as P


def main() -> int:
    P.OUT_LOG.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(P.OUT_LOG / "run_all.log", mode="w", encoding="utf-8")],
    )
    if not P.RAW_XLSX.exists():
        logging.error("missing %s (copy CTU_Routes_Structured.xlsx into data/raw/)", P.RAW_XLSX)
        return 1

    from src import stage1, stage2, stage3, stage4, stage5, stage6
    s1 = stage1.run()
    s2 = stage2.run(s1["data"])
    routes, dem = s1["data"]["routes"], s2["demand"]
    stage3.run(routes, dem)
    stage4.run(routes, dem)
    if "--skip-pareto" in sys.argv and (P.OUT / "pareto_nsga2.csv").exists():
        logging.info("stage 5 skipped (--skip-pareto); reusing saved fronts")
    else:
        stage5.run(routes, dem)
    stage6.run(routes, dem)
    return 0


if __name__ == "__main__":
    sys.exit(main())
