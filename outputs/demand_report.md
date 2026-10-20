# Stage 2: Synthetic demand report

> **SYNTHETIC DEMAND, ILLUSTRATIVE.** No CTU ridership data exists. These numbers show how the model behaves;
> they are not estimates of real CTU demand. See `docs/DECISIONS.md` D13-D20.

## Construction
score_r = d_r × (1 + 0.6·PGI + 0.4·ISBT43 + 0.3·ISBT17 + 0.3·outskirts + 0.3·Derabassi + 0.05·hubs) × noise_r,
with noise_r ~ LogNormal(0, 0.15) and seed 42.
D_ref_r = λ·score_r, where λ is set so that θ·Σ D_ref_r·span_r = 81,326 boardings/day.
That target is 143,000 CTU-wide riders × 389/684 buses, pro-rata (unverified anchor). θ = 1.8.
M_rt = m_t·D_ref_r with m = {'AM': 1.4, 'Midday': 0.8, 'PM': 1.3}. L = 0.80·M and U = 1.35·M.

## Sanity checks
- No negative demand; L ≤ M ≤ U everywhere: PASS.
- Coefficient of variation of M across routes: AM 0.39, Midday 0.41, PM 0.38.
- Sum of M over active routes [pax/h]: AM 4,480, Midday 2,562, PM 4,084.
- Check: θ·Σ D_ref·span = 81,326 (target 81,326).

## Baseline fit (capacity = C·f_max in peaks, C·f_min midday, C = 60)
| period | mean_M | mean_LF | max_LF | n_overloaded | n_underused |
|---|---|---|---|---|---|
| AM | 70.00 | 0.63 | 2.45 | 11 | 14 |
| Midday | 39.42 | 0.38 | 1.40 | 3 | 31 |
| PM | 65.87 | 0.59 | 2.27 | 10 | 16 |

**Overloaded (LF > 1):** 31/AM (2.45), 31/PM (2.27), 28A/AM (2.17), 101/AM (2.07), 28A/PM (2.02), 101/PM (1.92), 40/AM (1.56), 70A/AM (1.46), 40/PM (1.45), 31/Midday (1.40), 8/AM (1.39), 38B/AM (1.37), 70A/PM (1.35), 8/PM (1.29), 38B/PM (1.27), 28A/Midday (1.24), 213/AM (1.19), 101/Midday (1.18), 214/AM (1.14), 79/AM (1.13), 213/PM (1.11), 20A/AM (1.07), 214/PM (1.05), 79/PM (1.05)

**Under-used (LF < 0.3):** 61 pairs, mostly Midday. Lowest: 11A/Midday (0.02), 551/Midday (0.04), 202/Midday (0.06), 35D/Midday (0.07), 551/PM (0.07), 551/AM (0.08), 239/Midday (0.09), 202/PM (0.10), 206/Midday (0.10), 10/Midday (0.10)

The overloaded pairs are long routes with long headways (75-90 min), where demand grows with length but capacity is
only C·f. This is a property of the synthetic formula, not an observed CTU problem.

## θ sensitivity (θ = boardings per unit of busiest-section load; larger θ means less crowded)
| theta | period | mean_M | mean_LF | max_LF | n_overloaded | n_underused |
|---|---|---|---|---|---|---|
| 1.20 | AM | 104.99 | 0.95 | 3.67 | 18.00 | 6.00 |
| 1.20 | Midday | 59.13 | 0.57 | 2.10 | 8.00 | 15.00 |
| 1.20 | PM | 98.80 | 0.88 | 3.41 | 15.00 | 6.00 |
| 1.80 | AM | 70.00 | 0.63 | 2.45 | 11.00 | 14.00 |
| 1.80 | Midday | 39.42 | 0.38 | 1.40 | 3.00 | 31.00 |
| 1.80 | PM | 65.87 | 0.59 | 2.27 | 10.00 | 16.00 |
| 2.50 | AM | 50.40 | 0.45 | 1.76 | 6.00 | 24.00 |
| 2.50 | Midday | 28.38 | 0.28 | 1.01 | 1.00 | 44.00 |
| 2.50 | PM | 47.42 | 0.42 | 1.64 | 4.00 | 24.00 |

## Seed robustness (20 other noise seeds)
Spearman rank correlation of D_ref with seed 42: min 0.858, median 0.911.
Overloaded AM pairs range from 8 to 10. The route ranking is driven mostly by structure, not noise.

## Top routes by D_ref
| route_no | uplift | noise | D_ref |
|---|---|---|---|
| 242 | 2.55 | 1.11 | 93.46 |
| 32 | 2.65 | 0.98 | 89.87 |
| 38B | 2.90 | 1.04 | 87.93 |
| 214 | 2.35 | 1.25 | 83.42 |
| 2C | 2.10 | 1.12 | 82.37 |
| 5C | 2.20 | 1.02 | 78.80 |
| 31 | 2.45 | 0.95 | 78.72 |
| 30B | 2.25 | 1.18 | 75.60 |
| 39 | 2.85 | 1.02 | 72.98 |
| 4A | 2.10 | 1.15 | 71.92 |

![heatmap](figures/demand_heatmap.png)
![tfn](figures/tfn_alpha_cuts.png)
