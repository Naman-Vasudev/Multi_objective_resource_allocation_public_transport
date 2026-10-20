# How we would replace synthetic demand with real data

The model needs one input it does not have: passenger demand D_rt [pax/h] per route r and period t, as a triangular
fuzzy number (L, M, U). Today all three are **synthetic**. This page describes how real data would replace them,
without changing the model.

## 1. Sources

**(a) CTU ticket sales (ETM / electronic ticketing records).** If CTU's ticketing system logs each ticket with
route, bus, time and boarding stage, request a few months of weekday records, through CTU management or an RTI
application. Aggregate them to boardings per route, per period, per day. Two corrections are needed:
- **Pass holders** (students, monthly passes, concessions) may not generate a ticket per trip. Scale them up using
  the ratio of passes to tickets observed in the survey below.
- **Boardings are not load.** The overflow constraint compares demand with capacity C·f_rt, which binds at the
  **busiest section** of the route, not at the total of boardings. Convert using a peak-load ratio
  ρ_r = max on-board load ÷ boardings per trip, measured on board (ride checks).

**(b) Manual boarding counts at 5 to 10 stops.** Choose the hubs from `data/processed/stops.csv`: ISBT-17 (47 routes),
ISBT-43 (39), PGI (33), Aroma (22), 23/22 (18), PEC (16), New OPD, Attawa, 10/16 and 7/19. For each passing bus, record
route, time, boardings, alightings and an approximate on-board load (seated / standing / crush). Cover AM, Midday and
PM on at least 10 weekdays, plus a few ride checks per major route to estimate ρ_r. Counts at hubs miss boardings
elsewhere on the route, so they are used to **validate and scale** the ETM data (or, if there is no ETM data, scaled by the
share of route boardings at the counted stops, estimated from ride checks).

## 2. Estimating (L, M, U) for each (r, t)

1. Build a daily series D_rt,k = (boardings_rt,k × ρ_r) / overlap_h_rt for days k = 1..K, with K ≥ 20 weekdays. The
   unit is pax/h at the busiest section.
2. Set **L = 10th percentile**, **M = median (50th)** and **U = 90th percentile** of the series. The median is a
   robust stand-in for the mode. With more data, the mode of a kernel density estimate can be used instead.
3. Check: about 80% of days should fall in [L, U]. If many routes are much more skewed, keep separate lo and hi per
   route (`TFN_ROUTE_OVERRIDES`).
4. Routes with too few observations (K < 10): keep M from the data, and use the network-average lo and hi.

## 3. What changes in the code

Only `src/demand.py`. A loader for the real table replaces the synthetic-sheet loader, and it must output the same
`demand_rt.csv` columns (route_no, period, L, M, U). Nothing in the model, solvers or plots changes. The
"(synthetic demand)" label is removed only when **every** row comes from data.

## 4. What the synthetic results can and cannot claim

They show that the model works and how trade-offs behave under a plausible demand **shape**. They cannot claim
waiting-time savings or crowding reductions for real CTU passengers.
