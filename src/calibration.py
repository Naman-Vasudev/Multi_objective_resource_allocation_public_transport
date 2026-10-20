"""Stage 1 cycle-time calibration: how many buses does the published timetable need?

Cycle time of route r (time for one bus to come back to where it started) [h]:

    running_h = L_r / v                 L_r = distance one bus covers per cycle [km], v [km/h]
    tau_r     = running_h * (1 + l)     l = layover fraction of running time [-]

Scenarios for what the published route length d_r means:
    S1  d_r is the full cycle for every route           L_r = d_r
    S2  d_r is one-way for non-loop routes, full cycle   L_r = 2 d_r (non-loop), d_r (loop)
        for loops
    S3  S2 plus spare buses held at depots              N_total = N_need * (1 + s)

Buses needed to run frequency f_r [dep/h] on route r (Little's law: buses = rate * cycle time):

    n_r = f_r * tau_r    [dep/h * h = buses]
    N_need = sum_r f_mid_r * tau_r

No passenger demand is used in this stage.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src import params as P

SCENARIO_LABELS = {
    "S1": "S1: d_r = full cycle",
    "S2": "S2: d_r one-way (non-loop), loops full cycle",
    "S3": f"S3: S2 + {P.SPARE_RATIO:.0%} spares",
}


def cycle_distance_km(d_r_km, is_loop, scenario: str):
    """Distance [km] one bus covers per cycle under the scenario's reading of d_r."""
    d = np.asarray(d_r_km, dtype=float)
    loop = np.asarray(is_loop, dtype=bool)
    if scenario == "S1":
        return d
    if scenario in ("S2", "S3"):
        return np.where(loop, d, 2.0 * d)
    raise ValueError(f"unknown scenario {scenario!r}")


def cycle_time_h(d_r_km, is_loop, scenario: str, v_kmh: float, layover_frac: float):
    """Cycle time tau_r [h] = (cycle distance [km] / v [km/h]) * (1 + layover fraction)."""
    if v_kmh <= 0 or layover_frac < 0:
        raise ValueError("speed must be > 0 km/h and layover >= 0")
    return cycle_distance_km(d_r_km, is_loop, scenario) / v_kmh * (1.0 + layover_frac)


def buses_needed(routes: pd.DataFrame, scenario: str, v_kmh: float, layover_frac: float,
                 freq_col: str = "f_mid", spare_ratio: float | None = None) -> float:
    """Total buses [buses] = sum_r f_r [dep/h] * tau_r [h], times (1 + s) for S3."""
    tau = cycle_time_h(routes.d_r_km, routes.is_loop, scenario, v_kmh, layover_frac)
    n = float(np.sum(routes[freq_col].to_numpy() * tau))
    if scenario == "S3":
        n *= 1.0 + (P.SPARE_RATIO if spare_ratio is None else spare_ratio)
    return n


def per_route(routes: pd.DataFrame, scenario: str, v_kmh: float, layover_frac: float) -> pd.DataFrame:
    """Per-route requirement table for one scenario. Spares (S3) are fleet-level, so S3 == S2 here."""
    tau = cycle_time_h(routes.d_r_km, routes.is_loop, scenario, v_kmh, layover_frac)
    out = routes[["route_no", "is_loop", "d_r_km", "x_base", "f_min", "f_mid", "f_max",
                  "headway_min_lo", "headway_min_hi", "service_type", "span_hours"]].copy()
    out["tau_h"] = tau
    out["need_fmin"] = out.f_min * tau            # buses to run the LOWEST published frequency
    out["need_fmid"] = out.f_mid * tau
    out["need_fmax"] = out.f_max * tau            # buses to run the HIGHEST published frequency
    out["ceil_fmin"] = np.ceil(out.need_fmin - 1e-9).astype(int)
    out["ceil_fmax"] = np.ceil(out.need_fmax - 1e-9).astype(int)
    out["max_freq_x_over_tau"] = out.x_base / tau  # [dep/h] max frequency the allocated buses allow
    # speed [km/h] at which x_base buses EXACTLY deliver f_min:  x = f_min * L (1+l) / v
    out["v_needed_for_fmin_kmh"] = (out.f_min * cycle_distance_km(out.d_r_km, out.is_loop, scenario)
                                    * (1.0 + layover_frac) / out.x_base)
    return out


def scenario_grid(routes: pd.DataFrame) -> pd.DataFrame:
    """N_need for every scenario x speed x layover, vs B. Utilisation U = N_need / B [-]."""
    rows = []
    for sc in ("S1", "S2", "S3"):
        for v in P.SPEEDS_KMH:
            for lay in P.LAYOVER_FRACS:
                pr = per_route(routes, sc, v, lay)
                n_mid = buses_needed(routes, sc, v, lay, "f_mid")
                n_min = buses_needed(routes, sc, v, lay, "f_min")
                n_max = buses_needed(routes, sc, v, lay, "f_max")
                u = n_mid / P.FLEET_B
                rows.append(dict(
                    scenario=sc, v_kmh=v, layover_frac=lay,
                    N_need_fmin=n_min, N_need_fmid=n_mid, N_need_fmax=n_max,
                    B=P.FLEET_B, utilisation=u,
                    in_band=P.UTIL_BAND[0] <= u <= P.UTIL_BAND[1],
                    n_routes_x_lt_fmin_tau=int((pr.x_base < pr.need_fmin - 1e-9).sum()),
                    n_routes_x_lt_ceil_fmin=int((pr.x_base < pr.ceil_fmin).sum()),
                    n_routes_x_gt_ceil_fmax=int((pr.x_base > pr.ceil_fmax).sum()),
                ))
    return pd.DataFrame(rows)


def implied_uniform_speed(routes: pd.DataFrame, scenario: str, layover_frac: float,
                          target_buses: float) -> float:
    """Speed [km/h] at which N_need (f_mid) equals target_buses. N is proportional to 1/v, so solve directly."""
    n_at_1 = buses_needed(routes, scenario, 1.0, layover_frac, "f_mid")
    return n_at_1 / target_buses


def am_peak_need(routes: pd.DataFrame, scenario: str, v_kmh: float, layover_frac: float) -> float:
    """N_need counting only routes active in the AM peak window (night/short routes excluded) [buses]."""
    act = routes[routes.active_am == 1]
    return buses_needed(act, scenario, v_kmh, layover_frac, "f_mid")


def round_half(x: float) -> float:
    return math.floor(x + 0.5)
