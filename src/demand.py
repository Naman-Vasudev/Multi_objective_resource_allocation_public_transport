"""Time periods, synthetic demand and triangular fuzzy numbers (TFNs).

EVERY DEMAND NUMBER IN THIS PROJECT IS SYNTHETIC AND ILLUSTRATIVE. No CTU ridership data exists.

Units: demand D [pax/h], period length H_t [h], frequency f [dep/h], capacity C [pax/bus].

TFN for route r, period t (modal value M from the synthetic demand set):
    L = (1 - lo) * M        U = (1 + hi) * M        lo = 0.20, hi = 0.35 by default
alpha-cut at level alpha in [0, 1]:
    lower(alpha) = L + alpha * (M - L)      upper(alpha) = U - alpha * (U - M)
alpha = 1 -> [M, M] (modal demand);  alpha = 0 -> [L, U] (widest; U is the most conservative).
The optimisation uses the UPPER cut (plan capacity for the high side of demand).
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from src import data as D
from src import params as P


# ======================================================================
# Periods
# ======================================================================


def period_table(ow: pd.DataFrame, periods: dict | None = None) -> pd.DataFrame:
    """Long table (route_no, period, H_t, active, overlap_h, overlap_frac).

    active      Active AM/Midday/PM flag read from the Operating Windows sheet [0/1]
    overlap_h   hours of the route's daily window [first, last departure] inside the period [h]
    Asserts active == (overlap_h > 0): the sheet's flags and our overlap rule must agree.
    """
    periods = periods or P.PERIODS
    flag_col = {"AM": "active_am", "Midday": "active_midday", "PM": "active_pm"}
    rows = []
    for r in ow.itertuples():
        for t, (s, e) in periods.items():
            ov = D.period_overlap_hours(r.first_departure, r.last_departure, s, e)
            rows.append(dict(route_no=r.route_no, period=t, H_t=e - s, active=int(getattr(r, flag_col[t])),
                             overlap_h=ov, overlap_frac=ov / (e - s)))
    df = pd.DataFrame(rows)
    bad = df[(df.active == 1) != (df.overlap_h > 1e-9)]
    if len(bad):
        raise D.DataError(f"sheet Active flags disagree with window overlap for:\n{bad}")
    return df


# ======================================================================
# Triangular fuzzy numbers
# ======================================================================


def tfn_from_modal(M, lo: float = P.TFN_LO, hi: float = P.TFN_HI):
    """(L, M, U) [pax/h] from modal demand M [pax/h]: L = (1-lo) M, U = (1+hi) M."""
    if not (0.0 <= lo < 1.0) or hi < 0.0:
        raise ValueError(f"need 0 <= lo < 1 and hi >= 0, got lo={lo}, hi={hi}")
    M = np.asarray(M, dtype=float)
    if (M < 0).any():
        raise ValueError("modal demand must be non-negative")
    return (1.0 - lo) * M, M, (1.0 + hi) * M


def _check_alpha(alpha):
    a = np.asarray(alpha, dtype=float)
    if ((a < 0) | (a > 1)).any():
        raise ValueError(f"alpha must be in [0, 1], got {alpha}")
    return a


def alpha_cut_lower(L, M, alpha):
    """Lower end of the alpha-cut [pax/h]: L + alpha (M - L)."""
    a = _check_alpha(alpha)
    return np.asarray(L, float) + a * (np.asarray(M, float) - np.asarray(L, float))


def alpha_cut_upper(U, M, alpha):
    """Upper end of the alpha-cut [pax/h]: U - alpha (U - M). Used by the optimisation (D_alpha)."""
    a = _check_alpha(alpha)
    return np.asarray(U, float) - a * (np.asarray(U, float) - np.asarray(M, float))


def membership(x, L, M, U):
    """Triangular membership mu(x) in [0, 1]."""
    x = np.asarray(x, float)
    left = np.where(M > L, (x - L) / np.where(M > L, M - L, 1), (x >= M).astype(float))
    right = np.where(U > M, (U - x) / np.where(U > M, U - M, 1), (x <= M).astype(float))
    return np.clip(np.minimum(left, right), 0.0, 1.0)


def add_tfn(df: pd.DataFrame, lo: float = P.TFN_LO, hi: float = P.TFN_HI,
            overrides: dict | None = None) -> pd.DataFrame:
    """Add L, U columns to a (route_no, period, M) table; per-route (lo, hi) overrides win over the defaults."""
    overrides = P.TFN_ROUTE_OVERRIDES if overrides is None else overrides
    out = df.copy()
    out["lo"] = [overrides.get(r, (lo, hi))[0] for r in out.route_no]
    out["hi"] = [overrides.get(r, (lo, hi))[1] for r in out.route_no]
    for a, b in zip(out.lo, out.hi):
        tfn_from_modal(0.0, a, b)  # validates every (lo, hi)
    out["L"] = (1.0 - out.lo) * out.M
    out["U"] = (1.0 + out.hi) * out.M
    return out


def check_demand(df: pd.DataFrame) -> dict:
    """Sanity checks on a (route_no, period, L, M, U) table. Raises on failure; returns summary stats."""
    if (df[["L", "M", "U"]] < 0).any().any():
        raise D.DataError("negative demand found")
    if not ((df.L <= df.M) & (df.M <= df.U)).all():
        raise D.DataError("TFN ordering L <= M <= U violated")
    cv = df.groupby("period").M.agg(lambda s: s.std(ddof=0) / s.mean() if s.mean() > 0 else np.nan)
    if (cv.fillna(0) <= 0).any():
        raise D.DataError(f"demand does not vary across routes in some period: CV = {cv.to_dict()}")
    return dict(cv_by_period=cv.to_dict(), total_M=float(df.M.sum()))


# ======================================================================
# Synthetic base demand (DECISIONS D19) - SYNTHETIC, ILLUSTRATIVE
# ======================================================================


def noise_factors(n: int, seed: int = P.NOISE_SEED, sigma: float = P.NOISE_SIGMA) -> np.ndarray:
    """Fixed multiplicative noise per route, LogNormal(0, sigma), in route order. Same seed -> same numbers."""
    return np.random.default_rng(seed).lognormal(mean=0.0, sigma=sigma, size=n)


def route_flags(routes: pd.DataFrame, route_stops: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Structural 0/1 flags per route used in the demand score (plus n_hub_stops)."""
    terminals = set(routes.origin) | set(routes.destination)
    unknown = sorted(set(P.OUTSKIRTS_TERMINALS) - terminals)
    if unknown:
        raise D.DataError(f"OUTSKIRTS_TERMINALS names not found among route terminals: {unknown}")
    # stop names are matched after dropping "(...)" notes, so "PGI (Express)" counts as PGI
    key = lambda s: D._place_key(re.sub(r"\(.*?\)", "", str(s)))  # noqa: E731
    served = route_stops.assign(k=route_stops.stop.map(key)).groupby("route_no").k.apply(set)
    out = pd.DataFrame({"route_no": routes.route_no})
    for stop in P.DEMAND_STOP_WEIGHTS:
        out[f"serves_{stop}"] = [int(key(stop) in served.get(r, set())) for r in routes.route_no]
    out["outskirts"] = [int(o in P.OUTSKIRTS_TERMINALS or d in P.OUTSKIRTS_TERMINALS)
                        for o, d in zip(routes.origin, routes.destination)]
    out["derabassi"] = [int("Derabassi" in (o, d)) for o, d in zip(routes.origin, routes.destination)]
    out["n_hub_stops"] = features.set_index("route_no").n_hub_stops.reindex(routes.route_no).to_numpy()
    return out


def base_demand(routes, route_stops, features, theta: float = P.THETA, seed: int = P.NOISE_SEED,
                daily_boardings: float = P.DAILY_BOARDINGS) -> pd.DataFrame:
    """Per-route reference demand D_ref_r [pax/h at the busiest section]. SYNTHETIC.

    score_r = d_r [km] * (1 + sum_j w_j flag_jr + w_hub * n_hub_r) * noise_r
    lam     = daily_boardings / (theta * sum_r score_r * span_r)      so that
    theta * sum_r D_ref_r * span_r = daily_boardings  [pax/day]
    """
    fl = route_flags(routes, route_stops, features)
    uplift = (1.0
              + sum(w * fl[f"serves_{s}"] for s, w in P.DEMAND_STOP_WEIGHTS.items())
              + P.OUTSKIRTS_WEIGHT * fl.outskirts
              + P.DERABASSI_WEIGHT * fl.derabassi
              + P.HUB_WEIGHT * fl.n_hub_stops)
    out = fl.copy()
    out["d_r_km"] = routes.d_r_km.to_numpy()
    out["span_hours"] = routes.span_hours.to_numpy()
    out["uplift"] = uplift.to_numpy()
    out["noise"] = noise_factors(len(routes), seed)
    out["score"] = out.d_r_km * out.uplift * out.noise
    lam = daily_boardings / (theta * float((out.score * out.span_hours).sum()))
    out["D_ref"] = lam * out.score
    assert np.isclose(theta * (out.D_ref * out.span_hours).sum(), daily_boardings)
    return out


def modal_demand(base: pd.DataFrame, periods_rt: pd.DataFrame, multipliers: dict | None = None) -> pd.DataFrame:
    """M_rt = m_t * D_ref_r for active (r, t), else 0 [pax/h]. SYNTHETIC."""
    m = multipliers or P.DEMAND_MULTIPLIERS
    df = periods_rt.merge(base[["route_no", "D_ref"]], on="route_no", how="left", validate="many_to_one")
    df["m_t"] = df.period.map(m)
    df["M"] = np.where(df.active == 1, df.m_t * df.D_ref, 0.0)
    return df[["route_no", "period", "H_t", "active", "overlap_h", "m_t", "M"]]


def baseline_fit(dem: pd.DataFrame, routes: pd.DataFrame, C: float = P.BUS_CAPACITY) -> pd.DataFrame:
    """Baseline load factor LF = M / capacity, capacity = C f_max (AM, PM) or C f_min (Midday) [pax/h]."""
    df = dem.merge(routes[["route_no", "f_min", "f_max"]], on="route_no")
    df["capacity"] = np.where(df.period == "Midday", C * df.f_min, C * df.f_max)
    df["LF"] = np.where(df.active == 1, df.M / df.capacity, np.nan)
    return df


def demand_table(d: dict, theta: float = P.THETA, seed: int = P.NOISE_SEED):
    """Full synthetic pipeline -> (base per route, demand_rt with L, M, U, periods table)."""
    per = period_table(d["ow"], d["periods"])
    base = base_demand(d["routes"], d["route_stops"], d["features"], theta=theta, seed=seed)
    dem = add_tfn(modal_demand(base, per))
    return base, dem, per
