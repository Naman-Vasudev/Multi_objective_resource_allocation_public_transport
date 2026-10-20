"""Project-wide constants, file paths and the ONE place where units are converted.

Unit conventions (used everywhere in this project):
    frequency  f    departures per hour   [dep/h]
    headway    h    minutes               [min]      h = 60 / f
    distance   d    kilometres            [km]
    speed      v    kilometres per hour   [km/h]
    time       tau  hours                 [h]
    demand     D    passengers per hour   [pax/h]    (synthetic, later stages)

Every assumption here is also recorded in docs/DECISIONS.md.
"""
from pathlib import Path

# ---------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]
RAW_XLSX = ROOT / "data" / "raw" / "CTU_Routes_Structured.xlsx"
PROCESSED = ROOT / "data" / "processed"
OUT_FIG = ROOT / "outputs" / "figures"
OUT_TAB = ROOT / "outputs" / "tables"
OUT_LOG = ROOT / "outputs" / "logs"
OUT = ROOT / "outputs"

# ---------------------------------------------------------------- data facts (asserted on load)
N_ROUTES = 68          # routes in the CTU timetable as on 25.07.2026
FLEET_B = 389          # buses allocated across all routes [buses]
TOTAL_LENGTH_KM = 1662  # sum of published route lengths [km]
N_STOPS = 649          # unique stop names in the Stop Coverage sheet

# ---------------------------------------------------------------- calibration grid (DECISIONS D3-D6)
SPEEDS_KMH = (18.0, 22.0, 26.0)   # average commercial speed [km/h]
LAYOVER_FRACS = (0.0, 0.10)       # layover as a fraction of running time [-]
SPARE_RATIO = 0.10                # spares / buses in service [-]
EXCEL_SPEED_KMH = 22.0            # speed the workbook itself assumed for tau
UTIL_BAND = (0.85, 1.00)          # "plausible baseline utilisation" band [-]
HUB_MIN_ROUTES = 10               # a stop served by >= this many routes is a hub

# Working default, PENDING STUDENT CONFIRMATION (DECISIONS D2).
DEFAULT_SCENARIO = "S2"
DEFAULT_SPEED_KMH = 22.0
DEFAULT_LAYOVER_FRAC = 0.10

# ---------------------------------------------------------------- time periods (DECISIONS D13)
# Period name -> (start, end) as hours of the day [h]. H_t = end - start [h].
# MUST equal the editable cells B2:C4 of the Operating Windows sheet; src/data.py asserts this,
# so if you change one, change the other (otherwise the run stops with a clear message).
PERIODS = {"AM": (7.0, 10.0), "Midday": (10.0, 16.0), "PM": (16.0, 19.0)}
PERIOD_SHEET_LABELS = {"AM": "AM peak", "Midday": "Midday", "PM": "PM peak"}

# ---------------------------------------------------------------- synthetic demand (DECISIONS D14-D17)
# ASSUMPTIONS, NOT DATA. Time-of-day multipliers m_t [-]. The Synthetic Demand sheet is the source of truth
# once it exists; these defaults are asserted equal to it.
DEMAND_MULTIPLIERS = {"AM": 1.4, "Midday": 0.8, "PM": 1.3}
NOISE_SEED = 42

# Synthetic base demand (DECISIONS D19). The workbook has no demand sheet, so these are set here.
#   score_r = d_r * (1 + sum_j w_j * flag_jr + HUB_WEIGHT * n_hub_stops_r) * noise_r
#   D_ref_r = lam * score_r   [pax/h at the busiest section],  lam set by
#   THETA * sum_r D_ref_r * span_r = DAILY_BOARDINGS
ANCHOR_DAILY_RIDERS = 143_000   # CTU-wide daily riders (Tribune India, as given by the student; UNVERIFIED)
ANCHOR_FLEET = 684              # CTU-wide fleet in the same reports (UNVERIFIED)
DAILY_BOARDINGS = ANCHOR_DAILY_RIDERS * FLEET_B / ANCHOR_FLEET   # pro-rata by fleet ~ 81,326 [pax/day]
THETA = 1.8                     # boardings per unit of busiest-section load (turnover factor) [-]
THETA_SENSITIVITY = (1.2, 1.8, 2.5)
DEMAND_STOP_WEIGHTS = {"PGI": 0.6, "ISBT-43": 0.4, "ISBT-17": 0.3}   # route serves this stop
OUTSKIRTS_WEIGHT = 0.3          # a terminal outside Chandigarh city (list below)
DERABASSI_WEIGHT = 0.3          # extra, route terminates at Derabassi
HUB_WEIGHT = 0.05               # per hub stop served
NOISE_SIGMA = 0.15              # noise_r ~ LogNormal(0, sigma), numpy default_rng(seed), route order
# Terminals treated as "outskirts" (tri-city belt outside the city sectors). Classified by place name;
# check against a map and edit freely.
OUTSKIRTS_TERMINALS = (
    "Kharar", "Derabassi", "Zirakpur", "Kurali", "Landran", "Tangori", "Khizrabad", "Mullanpur Eco City",
    "Eco City Block-2 (Takipur)", "Nada Sahib", "Ramgarh", "Chhatbir Zoo", "Manoli", "Dhakoli", "Bhabhat",
    "Badi Karoran", "Sector-123", "Mohali R/Station Ph-11", "Mohali Ph-XI", "Mohali Ph-11",
    "Panchkula Bus Stand", "Mansa Devi", "Mata Mansa Devi", "Saketri (Kaimbwala)", "New Airport",
    "Jayanti Majri", "Omex Tower", "Rani Majra", "Platinum Homes", "Cantonment",
)
BUS_CAPACITY = 60               # C [pax/bus] (seated + standing; ASSUMPTION)
LF_UNDERUSED = 0.30             # baseline load factor below this = under-used [-]

# Triangular fuzzy demand: L = (1 - lo) * M,  U = (1 + hi) * M   [pax/h]
TFN_LO = 0.20            # downside spread [-]
TFN_HI = 0.35            # upside spread [-] (right-skewed: surges exceed dips)
TFN_ROUTE_OVERRIDES: dict[str, tuple[float, float]] = {}   # e.g. {"38AB": (0.10, 0.50)}

# Routes whose published headway is nominal (PDF lists fixed departure times instead). DECISIONS D15.
NOMINAL_FREQUENCY_ROUTES = ("216", "241")
# Routes with extra short trips (Operating Windows notes) that the base model ignores. DECISIONS D16.
EXTRA_TRIPS_IGNORED_ROUTES = ("20", "242")

SYNTHETIC_LABEL = "(synthetic demand)"   # suffix on every demand figure title

# ---------------------------------------------------------------- optimisation model (Stage 3, docs/MODEL.md)
from dataclasses import dataclass, field  # noqa: E402

HEADWAY_MENU_MIN = (10, 12, 15, 20, 25, 30, 40, 45, 60, 90)   # K [min]


@dataclass(frozen=True)
class ModelConfig:
    """Every model knob in one place. Units in comments. See docs/DECISIONS.md D21-D28."""
    C: float = BUS_CAPACITY                    # [pax/bus]
    spare_ratio: float = 0.08                  # s; B_eff = floor((1 - s) B) = 357 [buses]. 0.10 is infeasible (D22)
    alpha: float = 0.5                         # alpha-cut level for capacity constraint [-]
    scenario: str = DEFAULT_SCENARIO           # Stage 1 cycle-time reading
    speed_kmh: float = DEFAULT_SPEED_KMH       # [km/h]
    layover_frac: float = DEFAULT_LAYOVER_FRAC  # [-]
    menu_min: tuple = HEADWAY_MENU_MIN         # K [min]; each route also gets its published headways
    fmax_mode: str = "published"               # "published" | "relaxed" (two menu levels above f_max)
    equity_mode: str = "soft"                  # "hard" | "soft" | "off"
    equity_cap_min: dict = field(default_factory=lambda: {"AM": 60, "Midday": 90, "PM": 60})  # [min]
    equity_weight: float = 1.0                 # soft-mode penalty per minute of headway above the cap
    pract_abs: float = 3.0                     # |x - x0| <= max(pract_min, min(pract_abs, pract_rel * x0))
    pract_rel: float = 0.3
    pract_min: float = 1.0                     # [buses]; 0 reproduces the brief's rule literally
    hours_mode: str = "overlap"                # "overlap" (service hours inside t) | "full" (H_t)
    headway_cv: float = 0.3                    # CV of actual headways, for Excess Wait Time [-]
    fleet_B: int = FLEET_B                     # total fleet B [buses] (changed only in toy tests)

    @property
    def B_eff(self) -> int:
        import math
        return math.floor((1.0 - self.spare_ratio) * self.fleet_B + 1e-9)


# ---------------------------------------------------------------- Pareto stage (Stage 5, DECISIONS D33-D36)
PARETO_FMAX_MODE = "relaxed"     # the only mode with real trade-offs (Stage 4)
PARETO_ALPHA = 0.5
EPS_GRID = 20                    # 20 x 20 grid (D45; was 10) over (Z1, Z2) between ideal and nadir
AUGMECON_EPS = 1e-3              # augmentation weight on the normalised slacks
NSGA_POP = 200
NSGA_GEN = 300
NSGA_CXPB = 0.9
NSGA_SEEDS = (1, 2, 3, 4, 5)
HV_REF = 1.1                     # hypervolume reference point = 1.1 in every normalised objective

# ---------------------------------------------------------------- simulation (Stage 6, DECISIONS D37-D41)
SIM_N = 2000                     # demand scenarios
SIM_SEED = 2026
SIM_SHOCK_SD = 0.05              # common network-wide shock ~ Normal(1, 0.05) per scenario
SIM_HEADWAY_CV = 0.3             # CV of realised (gamma) headways
SIM_OVERFLOW_THRESHOLD = 0.05    # report P(overflow > 5% of demand)
SIM_FMAX_MODE = "relaxed"        # optimised schedules use the Stage 5 setting
SIM_POLICY = "P-BALANCED"        # reference policy for the sensitivity / tornado analysis
SIM_ALPHAS = (0.5, 0.0)          # GP schedules are compared at these alpha values
OOS_WIDEN = 1.5                  # out-of-sample: both TFN spreads x1.5 ...
OOS_SHOCK_SD = 0.10              # ... and a stronger common shock

# ---------------------------------------------------------------- unit conversions
MIN_PER_HOUR = 60.0


def headway_min_to_freq_per_h(headway_min: float) -> float:
    """Headway [min] -> frequency [dep/h]. f = 60 / h."""
    if headway_min <= 0:
        raise ValueError(f"headway must be positive minutes, got {headway_min}")
    return MIN_PER_HOUR / headway_min


def freq_per_h_to_headway_min(freq_per_h: float) -> float:
    """Frequency [dep/h] -> headway [min]. h = 60 / f."""
    if freq_per_h <= 0:
        raise ValueError(f"frequency must be positive dep/h, got {freq_per_h}")
    return MIN_PER_HOUR / freq_per_h
