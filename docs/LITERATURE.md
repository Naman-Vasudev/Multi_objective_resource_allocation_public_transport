# Literature behind the methods

These sources were found with the Consensus paper search on 2026-10-15. **None has yet been resolved through LibKey:**
the institution's LibKey connector was not authorised in this session. Before you put any of them in the report's
bibliography, open each through LibKey or your library and check the full citation (volume, pages, DOI).
Where Consensus's metadata looks incomplete, this is flagged below. Links point to the Consensus record.

## Multi-objective exact methods (Stage 5, AUGMECON)
1. Mavrotas, G. (2009). [Effective implementation of the epsilon-constraint method in Multi-Objective Mathematical Programming problems](https://consensus.app/papers/details/fe45f288a3ad59e4ac2db0381be0db5a/?utm_source=claude_code). *Applied Mathematics and Computation*.
   - Introduces **AUGMECON**: slack variables added to the objective so the ε-constraint method returns only strictly
     (not weakly) Pareto-optimal points; a lexicographic payoff table; and an early exit from infeasible grid regions.
   - Used here in `src/pareto.py::lexicographic_payoff` and `augmecon`.
2. Mavrotas, G. & Florios, K. [An improved version of the augmented epsilon-constraint method (AUGMECON2) for finding the exact Pareto set in Multi-Objective Integer Programming problems](https://consensus.app/papers/details/d830f8b6999f532db823f4c3fefea974/?utm_source=claude_code).
   - Consensus lists it as 2020 with no journal; check the year and venue via LibKey.
   - AUGMECON2 is suited to *integer* programmes like ours and can produce the exact Pareto set with a fine enough
     grid. That is why the report says a finer grid would raise the exact hypervolume.
3. Nikas, A. et al. (2020). [A robust augmented ε-constraint method (AUGMECON-R)](https://consensus.app/papers/details/aab6d437620a5c698131451bf28746d4/?utm_source=claude_code). *Operational Research*.
   - Addresses AUGMECON2's handling of nadir points and its run time with many objectives. With 3 objectives,
     plain AUGMECON is enough; this is cited as the known extension.

## Evolutionary multi-objective optimisation (Stage 5, NSGA-II)
4. Deb, K. et al. (2002). [A fast and elitist multiobjective genetic algorithm: NSGA-II](https://consensus.app/papers/details/237b677956015741afc75904864d6c8d/?utm_source=claude_code). *IEEE Transactions on Evolutionary Computation*.
   - The algorithm we run: fast non-dominated sorting, crowding distance, elitist (μ + λ) selection.
   - Deb et al. also define constrained dominance. **We use a repair operator instead**, because the fleet and
     frequency-fleet constraints have a clear "lengthen the headway" fix.
5. Ma, H. et al. (2023). [A comprehensive survey on NSGA-II for multi-objective optimization and applications](https://consensus.app/papers/details/7dffce4b8b9a50a8aa39812f06c5af4f/?utm_source=claude_code). *Artificial Intelligence Review*.
   - Survey of NSGA-II variants and applications; supports the choice of NSGA-II as the standard baseline heuristic.

## Comparing fronts (Stage 5 metrics)
6. Zitzler, E. & Thiele, L. (1999). [Multiobjective evolutionary algorithms: a comparative case study and the strength Pareto approach](https://consensus.app/papers/details/6080eb993160546b8fdc40642e776f96/?utm_source=claude_code). *IEEE Transactions on Evolutionary Computation*.
   - Source of the quantitative comparison measures we report: the dominated-space (hypervolume) measure and the
     set coverage C(A, B).
7. Riquelme, N. et al. (2015). [Performance metrics in multi-objective optimization](https://consensus.app/papers/details/9cf3108635e95fc68141dc7747d10e27/?utm_source=claude_code). *CLEI 2015*.
   - Review of 54 metrics; finds hypervolume the most used, followed by generational distance, the ε-indicator and
     IGD. That is why we report HV, GD and IGD.
8. Jiang, S. et al. (2014). [Consistencies and Contradictions of Performance Metrics in Multiobjective Optimization](https://consensus.app/papers/details/21a52459b02d5ac08cf06ba288100ee6/?utm_source=claude_code). *IEEE Transactions on Cybernetics*.
   - Shows these metrics can disagree, especially on concave fronts. So we never rely on one metric, and we add the
     strict-dominance check.
9. Audet, C. et al. [Performance indicators in multiobjective optimization](https://consensus.app/papers/details/cddfd920fcfa5686bfa8af0ed87d2b4b/?utm_source=claude_code). *European Journal of Operational Research*.
   - Consensus lists it as 2018; check the year of the journal version via LibKey. It reviews 63 indicators grouped as
     cardinality, convergence, distribution and spread. Our table covers cardinality (n_points), convergence (GD),
     and spread/coverage (IGD, HV).

## Bus planning context (Stages 3-5)
10. Ibarra-Rojas, O. et al. (2015). [Planning, operation, and control of bus transport systems: A literature review](https://consensus.app/papers/details/a818cc307351578698b8a5009655c3db/?utm_source=claude_code). *Transportation Research Part B*.
    - Places frequency setting inside the transit planning chain: network design, then frequencies, timetabling,
      vehicle and crew scheduling. Our model covers the frequency-setting step with a fleet constraint.
11. Ahern, Z. et al. (2022). [Approximate multi-objective optimization for integrated bus route design and service frequency setting](https://consensus.app/papers/details/09b594396f4053a582e28116722ae6f3/?utm_source=claude_code). *Transportation Research Part B*.
    - Passenger vs operator trade-off. It warns that minimising fleet without coupling frequency to passenger
      choices produces overcrowding. Our Z3 and the C3 capacity constraint address exactly that coupling, in
      simplified form (no passenger assignment).
12. Jha, S. B. et al. (2019). [A multi-objective meta-heuristic approach for transit network design and frequency setting problem in a bus transit system](https://consensus.app/papers/details/b8a6ec3e178153ba90fe0ff14cf0aeb1/?utm_source=claude_code). *Computers & Industrial Engineering*.
    - A frequency-setting Pareto front (passenger time vs operating cost) found by a metaheuristic and compared with
      NSGA-II. This is the same kind of comparison as our Stage 5.
13. Arbex, R. & da Cunha, C. (2015). [Efficient transit network design and frequencies setting multi-objective optimization by alternating objective genetic algorithm](https://consensus.app/papers/details/d764a6033f59532cb651cca03581336a/?utm_source=claude_code). *Transportation Research Part B*.
    - A GA for the combined route-design and frequency problem. It shows why metaheuristics dominate when routes are
      also decided (huge combinatorial space), unlike our fixed-route problem, which an MILP solves exactly.

## How our study differs (be explicit in the viva)
- **Routes are fixed.** CTU's 68 routes are given; we choose only headways and buses. That keeps the problem small
  enough for exact MILP. The literature above uses GAs mainly because it also designs the routes.
- **Demand is synthetic.** The papers use real or benchmark origin-destination data (for example Mandl's network).
  Our results show the method's behaviour, not CTU outcomes.
- **No passenger assignment.** Unlike Ahern et al., passengers do not switch routes when frequencies change.
  Demand per route is fixed, which is a stated limitation.

## Evidence used for the judgment calls (DECISIONS D42-D55)
Found with Consensus on 2026-10-15; not LibKey-resolved (connector not authorised).

14. Mahesh, S. et al. (2017). [Analysis of driving characteristics and estimation of pollutant emissions from intra-city buses](https://consensus.app/papers/details/864ddeb17ede55c282734529bad6cba4/?utm_source=claude_code). *Transportation Research Procedia*.
    - GPS data on four Chennai bus routes: average speed 17.8 km/h in the peak and 21.5 km/h off-peak. Gives the
      band for the speed sensitivity (18-26 km/h).
15. Nesamani, K. et al. (2011). [Development of a driving cycle for intra-city buses in Chennai, India](https://consensus.app/papers/details/ff2f6ec370bd5890b8144cd6ae0ce9cc/?utm_source=claude_code). *Atmospheric Environment*.
    - More than 90% of trips average below 30 km/h, and much of the time is spent idling at stops and signals. 26 km/h
      is therefore an optimistic upper case.
16. Jain, G. et al. (2022). [Evaluation of travel speed of conventional buses and BRTS in Ahmedabad](https://consensus.app/papers/details/0155b7f277285d55a4362869ffec5ea9/?utm_source=claude_code). *Journal of Public Transportation*.
    - Bus speed varies strongly by place and time in Indian cities. This supports flagging uniform speed as a limitation.
17. Minkoff, M. et al. (2014). [System-Specific Spare Bus Ratios Update](https://consensus.app/papers/details/f71875effe8852b194720e1ed124e2cf/?utm_source=claude_code). *TCRP Synthesis of Transit Practice*.
    - Spare ratios are agency-specific and depend on fleet, service and maintenance factors.
18. Raposo, H. et al. (2021). [An Integrated Model for Dimensioning the Reserve Fleet based on the Maintenance Policy](https://consensus.app/papers/details/f82dfcf6894a5b22b96587eb1b340de1/?utm_source=claude_code). *WSEAS Transactions on Systems and Control*.
    - Spare-fleet indicators are often copied "almost as a dogma". They should be tied to the maintenance policy. We
      have no CTU maintenance data, so the spare ratio is a tested assumption, not a fact.
19. Kaewunruen, S. et al. (2021). [Causal analysis of bus travel time reliability in Birmingham, UK](https://consensus.app/papers/details/a888e01dba6a5f37b37d911e7a011fc2/?utm_source=claude_code). *Results in Engineering*.
    - Departure delay, signalised intersections and stop spacing drive bus delay. Schedules need recovery
      (layover) time, so the layover share is tested at 5-15%.
20. Mohamed, A. et al. (2021). [Identification of Affecting Factors on the Travel Time Reliability for Bus Transportation](https://consensus.app/papers/details/5dfde21b306b59d295ac9897a465023d/?utm_source=claude_code).
    - Route length and the number of stops strongly affect travel-time reliability. Long routes need more slack.
21. Bertsimas, D. & Sim, M. (2004). [The Price of Robustness](https://consensus.app/papers/details/10861ceeb7c5505d94b70ad46979b88b/?utm_source=claude_code). *Operations Research*.
    - Robust solutions trade nominal optimality for protection against data changes, and the level of conservatism
      should be adjustable. Our α and the "robust variant" planned on a wider uncertainty set are that dial.
22. Wardman, M. & Whelan, G. (2011). [Twenty Years of Rail Crowding Valuation Studies](https://consensus.app/papers/details/0f0bc1ea49985f5491ae38531bfb29ae/?utm_source=claude_code). *Transport Reviews*.
    - A meta-analysis of 208 valuations: standing time is valued at about 2.32 times seated time. Crowding is costly,
      so overflow (Z3) deserves high priority.
23. Yap, M. et al. (2023). [Public transport crowding valuation in a post-pandemic era](https://consensus.app/papers/details/eac2af2bdf7e5b3f9acf650a96bd68de/?utm_source=claude_code). *Transportation*.
    - Waiting and walking time is valued at about 1.9 times in-vehicle time, and crowding penalties have risen since the
      pandemic. Waiting (Z1) and crowding (Z3) are both first-order concerns, which supports balanced weighting.
24. Fedujwar, R. et al. (2024). [A systematic review on crowding valuation in public transport](https://consensus.app/papers/details/4afd93dbd4435c0490cc75939b1f86b1/?utm_source=claude_code). *Public Transport*.
    - Crowding valuations vary by city and mode, so European multipliers cannot simply be transferred to Chandigarh.
      We do not convert crowding into money.
25. Tamiz, M. et al. (1995). [A review of Goal Programming and its applications](https://consensus.app/papers/details/a15680b4dde05f2591a7e2e129306593/?utm_source=claude_code). *Annals of Operations Research*.
    - Lexicographic vs weighted GP, and how the way weights and priorities are assigned shapes the result. This is the
      basis for setting targets inside the attainable range (ideal to baseline).
