# Goal programming in plain language

## The idea
A normal optimisation asks for "as good as possible" on one number. Planners rarely think that way. They say
"cut waiting by 15%, don't add vehicle-km, and no route should wait more than an hour".
**Goal programming (GP)** writes each of those wishes as a **goal** with a **target**:

    achieved value + n − p = target,    n, p ≥ 0

- **n** (under-achievement) is how far *below* the target we land.
- **p** (over-achievement) is how far *above* the target we land.

For a "smaller is better" goal, landing below the target is fine; only **p** is unwanted. GP minimises only the
unwanted deviations, so a goal that is already met costs nothing. Hard rules (fleet size, buses needed to run a
frequency) stay as ordinary constraints. A goal can be missed; a hard rule cannot.

## Our goals
| Goal | Meaning | Target | Unwanted |
|---|---|---|---|
| G1 | passenger waiting Z1 | 4% below today's (κ1 = 0.04; was 0.15, see D48) | p1 (waiting above target) |
| G2 | unserved / overloaded passengers Z3 | 0 | p2 (any overflow) |
| G3 | vehicle-km Z2 | 3% below today's (κ3 = 0.03; was 0, see D49) | p3 (extra km) |
| G4 | equity: every headway ≤ cap (60 min peak, 90 min midday) | 0 minutes above the cap | Σ p4 (minutes above the cap) |

"Today" means the published CTU schedule evaluated by the same model with the same α. Demand is synthetic.

## Two ways to trade goals off
**Preemptive (lexicographic) GP.** Goals are ranked. First, make the top goal's unwanted deviation as small as
possible. Then **lock** that result (it may not get worse by more than a tiny tolerance) and make the second goal as
small as possible, and so on down the list. A lower goal can never buy itself an improvement by worsening a higher one.
Scenarios:
- P-PASSENGER: G2 > G1 > G4 > G3
- P-OPERATOR: G3 > G2 > G1 > G4
- P-EQUITY: G4 > G2 > G1 > G3

**Weighted GP (P-BALANCED).** One solve. Minimise w1·p1/s1 + w2·p2/s2 + w3·p3/s3 + w4·Σp4/s4, where each s is the
baseline value of that goal. Dividing by s puts the goals in comparable units, so "1% worse waiting" and "1% more
overflow" weigh the same.

**Chebyshev GP (min-max).** Minimise the *largest* normalised deviation. No single goal is left far behind, so it is
the fairness-oriented compromise.

After each method, one last "tidy" solve minimises the total number of buses while keeping every goal result locked.
Buses do not appear in Z1-Z3, so without this step the reported fleet would be arbitrary.

## Ideal and nadir
The **ideal** of a goal is the best value it can reach when optimised alone. The **nadir** is its worst value
among the other goals' single-objective optima. Together they show each goal's real range. A target outside
[ideal, nadir] tells you in advance whether the goal is impossible or trivially easy.

## Why GP and not a plain weighted sum
Targets and priorities are explicit and easy to interpret: "overflow first, then waiting" is a sentence a
transport manager can sign off. A weighted sum hides the same judgement inside weights whose effect depends on the
units and scale of each objective.

## Known weaknesses
1. **The answer depends on the targets and the ordering.** Our first targets showed this. G3 = "no more vehicle-km
   than today" never bound, so P-OPERATOR was identical to P-PASSENGER. G1 = "−15% waiting" was beyond the best
   possible value (−4.9%). After the targets were moved inside the attainable range (κ1 = 4%, κ3 = 3%; D48-D49),
   the scenarios differ and goal achievement becomes informative. G2 = 0 overflow stays unattainable on purpose,
   as a "minimise" goal.
2. **Preemptive GP can ignore low-priority goals completely.** Once the top levels are locked, there may be no room
   left for the rest, however cheap a small concession upstairs would have been.
3. **Weighted GP depends on the normalisation.** Changing the scales s_i changes the answer.

## Where this is in the code
- `src/goals.py`: goal model, preemptive, weighted and Chebyshev solvers, payoff table.
- `config/gp_scenarios.json`: scenarios. Add your own ordering here; ties are written as a list, e.g. `[["G1","G2"],"G3"]`.
- `src/stage4.py`: runs every scenario × α × f_max mode and writes the tables, figure and report.
