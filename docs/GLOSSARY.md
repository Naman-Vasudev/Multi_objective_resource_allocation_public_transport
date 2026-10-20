# GLOSSARY (symbols and units)

| Symbol / column | Meaning | Unit |
|---|---|---|
| r ∈ R | route; R has 68 routes | - |
| route_no | route identifier, always a string ("1", "25/25A") | - |
| d_r, d_r_km | published route length (one-way for non-loop routes under S2) | km |
| is_loop | origin = destination, so d_r is already a full cycle | bool |
| h, headway_min_lo / _hi | headway: time between departures (shortest / longest published) | min |
| f, f_min / f_max / f_mid | frequency = 60 / h; f_min uses the longest headway | dep/h |
| v | average commercial speed, including dwell time | km/h |
| l | layover as a fraction of running time | - |
| L_r | distance a bus covers per cycle: d_r (S1, loops) or 2·d_r (S2, non-loop) | km |
| τ_r, tau_h | cycle time = L_r / v × (1 + l) | h |
| x_r, x_base | buses currently allocated to route r | buses |
| B | total fleet = Σ x_base = 389 | buses |
| s | spare ratio = spares ÷ buses in service | - |
| N_need | Σ_r f_r · τ_r: buses needed to run frequencies f | buses |
| U | utilisation = N_need / B | - |
| f_r · τ_r | buses route r needs at frequency f_r (Little's law) | buses |
| x_r / τ_r | maximum frequency route r's buses can deliver | dep/h |
| H_t | length of time period t (later stages) | h |
| D_rt | passenger demand on route r in period t. **Synthetic, illustrative** | pax/h |
| C | bus capacity (later stages; must be a stated parameter) | pax/bus |
| o_rt | overflow / unmet demand ≥ D_rt − C · f_rt | pax/h |
| span_hours | last departure − first departure (wraps past midnight) | h |
| centrality_sum / _mean | Σ / mean of "routes serving" over a route's stops | routes |
| hub stop | stop served by ≥ 10 routes | - |
| S1 / S2 / S3 | calibration scenarios: full-cycle / one-way / one-way + spares | - |
