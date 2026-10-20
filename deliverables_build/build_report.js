// Progress report (format supplied by the department). Numbers come from outputs/report_facts.json.
const fs = require("fs");
const path = require("path");
const C = require("./docx_common.js");
const { D, F, REFS, cite, pct, n0, runs, P, EQ, H1, H2, H3, BUL, NUM, BREAK, caption, figure, table, numbering, styles,
        MODEL_EQ, CONS_EQ, FONT, NAVY } = C;
const { Document, Packer, Paragraph, TextRun, AlignmentType, ImageRun, TableOfContents, Footer, PageNumber,
        NumberFormat, SectionType } = D;
const OUT = path.join(C.PROJ, "Progress_Report_CTU_Fleet_Allocation.docx");

const center = (text, o = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: o.after ?? 120, before: o.before ?? 0 },
  children: runs(text, { size: o.size || 24, bold: o.bold, italics: o.italics, color: o.color }) });
const H = F.sim.headline, POL = F.sim.rows[H.policy], BASE = F.sim.rows["Baseline"], PEAK = F.sim.rows["Baseline (peak f_max)"];
const gpRow = (n) => F.gp.rows.find((r) => r.name === n);
const order = { "P-PASSENGER": "G2 > G1 > G4 > G3", "P-OPERATOR": "G3 > G2 > G1 > G4", "P-EQUITY": "G4 > G2 > G1 > G3",
                "P-BALANCED": "equal normalised weights", "CHEBYSHEV": "min-max of normalised deviations" };
const infeasible = F.sens.filter((r) => !r.feasible).map((r) => ({ "speed v": `speed ${r.value} km/h`, "spare ratio s": `spares ${Math.round(100 * r.value)}%`,
  layover: `layover ${Math.round(100 * r.value)}%` }[r.factor] || `${r.factor} ${r.value}`))
  .concat(F.fleet.filter((r) => !r.feasible).map((r) => `fleet cut ${Math.round(100 * r.cut)}% (B_eff = ${r.B_eff})`));

// ------------------------------------------------------------------ preliminary pages
const logo = fs.readFileSync(path.join(C.MEDIA, "pec_logo.png"));
const ls = C.pngSize(path.join(C.MEDIA, "pec_logo.png"));
const title = [
  center("PUNJAB ENGINEERING COLLEGE (DEEMED TO BE UNIVERSITY), CHANDIGARH", { bold: true, size: 26, after: 300 }),
  center("MINOR PROJECT PROGRESS REPORT", { bold: true, size: 28, color: NAVY, after: 300 }),
  center("OPTIMIZATION-BASED RESOURCE ALLOCATION FOR PUBLIC BUS FLEET SCHEDULING UNDER DEMAND VARIABILITY", { bold: true, size: 30, after: 160 }),
  center("(A case study of the Chandigarh Transport Undertaking)", { italics: true, after: 360 }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 }, children: [new ImageRun({ type: "png", data: logo,
    transformation: { width: 150, height: 150 * ls.h / ls.w }, altText: { title: "PEC logo", description: "Punjab Engineering College logo", name: "logo" } })] }),
  center("Submitted in partial fulfilment of the requirements for the award of the degree of", { after: 60 }),
  center("BACHELOR OF TECHNOLOGY", { bold: true, after: 40 }), center("in", { after: 40 }),
  center("MATHEMATICS AND COMPUTING", { bold: true, after: 360 }),
  center("Under the guidance of", { italics: true, after: 40 }), center("Dr. Sumati Mahajan", { bold: true, after: 20 }),
  center("Department of Mathematics, Punjab Engineering College", { after: 300 }),
  center("Submitted by", { italics: true, after: 40 }),
  center("Daksh Garg (24112005)    Piyush Aggarwal (24112006)", { after: 20 }),
  center("Abhay Chauhan (24112015)    Naman Vasudev (24112032)", { after: 360 }),
  center("DEPARTMENT OF MATHEMATICS AND COMPUTING", { bold: true, after: 20 }),
  center("PUNJAB ENGINEERING COLLEGE, CHANDIGARH", { bold: true, after: 20 }),
  center("October 2026", { after: 0 }),
];
const sig = (n) => new Paragraph({ spacing: { before: 360, after: 0 }, children: runs("____________________     " + n) });
const declaration = [
  H1("Declaration", true),
  P("We hereby declare that the work presented in this progress report, entitled “Optimization-Based Resource Allocation for Public Bus Fleet Scheduling under Demand Variability”, is our own work carried out under the guidance of Dr. Sumati Mahajan, Department of Mathematics, Punjab Engineering College, Chandigarh. The work has not been submitted elsewhere for the award of any degree. Sources of information have been acknowledged in the references."),
  P("All passenger-demand values used in this report are synthetic and illustrative; they are not measured Chandigarh Transport Undertaking (CTU) ridership, and no result in this report should be read as a measured improvement of CTU service."),
  sig("Daksh Garg (24112005)"), sig("Piyush Aggarwal (24112006)"), sig("Abhay Chauhan (24112015)"), sig("Naman Vasudev (24112032)"),
  new Paragraph({ spacing: { before: 360 }, children: runs("Date: ____________     Place: Chandigarh") }),
];
const ack = [
  H1("Acknowledgement", true),
  P("We are grateful to our guide, Dr. Sumati Mahajan, Department of Mathematics, Punjab Engineering College, for her guidance and for encouraging a careful, mathematically honest treatment of the problem. We thank the Department of Mathematics for the facilities provided, and the Chandigarh Transport Undertaking for making its timetable publicly available, which made this case study possible."),
];
const abstract = [
  H1("Abstract", true),
  P(`Urban bus operators must allocate a fixed fleet across many routes whose demand varies by place, time of day and day to day. This project formulates that allocation as a multi-objective optimization problem and applies it to the Chandigarh Transport Undertaking (CTU), using its published timetable: ${F.data.routes} routes, ${F.data.buses} allocated buses and ${n0(F.data.km)} km of route length. The data were audited against the timetable PDF, and cycle times were calibrated so that the published frequencies are consistent with the allocated fleet.`),
  P(`The formulation in the project synopsis was corrected in four places: the waiting-time objective is linearised with a discrete headway menu; operating effort is measured in vehicle-kilometres; hourly capacity is bus capacity times frequency; and demand uncertainty uses the upper α-cut of a triangular fuzzy number. The resulting mixed-integer linear program (${F.model.n_vars} variables, ${F.model.n_cons} constraints) is solved exactly. Goal programming with explicit priorities is used to balance waiting, vehicle-km, overcrowding and headway equity, and the trade-offs are cross-checked against an exact AUGMECON Pareto front and NSGA-II.`),
  P(`No ridership data are public, so demand is synthetic. Under this synthetic demand, the balanced goal-programming schedule reduces expected waiting by ${pct(H.vs_mid.wait)}, overflow passengers by ${pct(H.vs_mid.over)} and vehicle-km by ${pct(H.vs_mid.vkm)} relative to the published schedule, using ${POL.fleet} instead of ${BASE.fleet} buses, across ${n0(F.sim.N)} simulated demand days. The gains persist against a fairer peak-frequency baseline (overflow ${pct(H.vs_peak.over)}). The results are not measured CTU outcomes: they demonstrate the method, and the report states where they could be artefacts of the synthetic demand and of the calibration.`),
  P("Keywords: bus fleet allocation, frequency setting, mixed-integer linear programming, goal programming, fuzzy demand, α-cut, Pareto front, NSGA-II, Monte Carlo simulation.", { run: { italics: true } }),
];
const toc = [
  H1("Table of Contents", true),
  new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-2" }),
  H1("List of Figures", true),
  new TableOfContents("List of Figures", { hyperlink: true, captionLabelIncludingNumbers: "Figure" }),
  H1("List of Tables", true),
  new TableOfContents("List of Tables", { hyperlink: true, captionLabelIncludingNumbers: "Table" }),
];

// ------------------------------------------------------------------ Chapter 1
const ch1 = [
  H1("Chapter 1  Introduction", false),
  H2("1.1 General"),
  P("Fixed-route bus services are the most accessible and affordable form of public transport for most Indian city commuters. A transport undertaking runs a finite fleet over a network of routes whose demand changes across the city, across the day, and from one day to the next. When the planned supply of departures does not follow this demand, the network fails in two ways at once: passengers on busy corridors face long waits and crowded or full buses, while buses on quiet corridors run with spare capacity that still costs fuel, maintenance and driver hours."),
  P("From an applied-mathematics point of view, this is a constrained multi-objective resource-allocation problem: a limited pool of buses must be divided among routes and time periods to satisfy objectives that conflict. More frequent service reduces waiting and crowding but increases vehicle-kilometres; fewer runs save cost but hurt passengers. A planning method must therefore expose the trade-offs, not just one “optimal” answer " + cite("ceder16", "ibarra15") + "."),
  H2("1.2 Background of the Project"),
  P(`The case study is the Chandigarh Transport Undertaking (CTU), which operates local and tri-city services across Chandigarh, Mohali and Panchkula. The input is CTU's published timetable for Depots II, III and IV (as on 25.07.2026) ${cite("ctu26")}: for each of the ${F.data.routes} routes it gives the operating hours, the published headway range, the route length and the number of buses allocated (${F.data.buses} in total). A stop-coverage list adds ${F.data.stops} named stops.`),
  P("The project began from a synopsis that proposed a multi-objective model with three objectives (waiting time, operating effort and overcrowding), fleet and frequency constraints, fuzzy demand and three solution approaches (MILP, NSGA-II and fuzzy linear programming). During execution, four mathematical errors in that formulation were found and corrected (Section 3.3). The most important practical constraint is that CTU publishes no ridership data, so all passenger demand in this report is synthetic and illustrative; the methods are built so that real ridership can replace it without changing the model."),
  H2("1.3 Objectives"),
  NUM("Build a validated baseline of the CTU network from the published timetable (routes, headways, buses, stops) and calibrate cycle times against the allocated fleet."),
  NUM("Formulate a corrected, linear multi-objective mixed-integer model for choosing headways and allocating buses by route and time period."),
  NUM("Represent uncertain demand with triangular fuzzy numbers and an α-cut capacity rule."),
  NUM("Balance passenger waiting, operating effort, overcrowding and headway equity using goal programming with explicit priorities, and cross-check the trade-offs on an exact Pareto front and with NSGA-II."),
  NUM("Stress-test every schedule by Monte Carlo simulation and sensitivity analysis, and report honestly where the results hold and where they break."),
];

// ------------------------------------------------------------------ Chapter 2
const litRows = [
  [cite("ceder16"), "Transit planning chain (textbook)", "Frames frequency setting between network design and timetabling"],
  [cite("fw81"), "Fleet allocation across routes and periods", "Same structure as our fleet and loading constraints"],
  [cite("martinez14"), "MILP frequency setting with discrete frequencies", "Supports the headway-menu linearisation"],
  [cite("verbas15"), "Frequency allocation over routes and periods; trade-offs", "Period-wise allocation and trade-off analysis"],
  [cite("arbex15", "jha19", "ahern22"), "Multi-objective route design and frequency setting (GA, PSO)", "User-operator Pareto fronts; overcrowding risk"],
  [cite("deb02"), "NSGA-II", "Heuristic Pareto front, benchmarked against the exact one"],
  [cite("mavrotas09", "mavrotas13"), "AUGMECON / AUGMECON2", "Exact, strictly efficient ε-constraint front"],
  [cite("cc61", "jt10"), "Goal programming (origin; practice)", "Targets, deviations, preemptive and weighted forms"],
  [cite("zadeh65", "zimm78", "ir00"), "Fuzzy sets; fuzzy and possibilistic LP", "Triangular fuzzy demand and α-cuts"],
  [cite("anlo16", "gk22"), "Transit design and frequency setting under demand uncertainty", "Stochastic alternatives to the fuzzy approach"],
  [cite("tfl12", "leong16"), "Bus service planning; Excess Wait Time in Singapore", "Service-quality metric (EWT)"],
  [cite("mahesh17", "jain22"), "Measured bus speeds in Indian cities", "Speed range 18-26 km/h used in calibration"],
  [cite("fedujwar24"), "Crowding valuation review", "Why crowding costs are not transferred between cities"],
];
const ch2 = [
  H1("Chapter 2  Literature Review", true),
  H2("2.1 Review of Research Papers"),
  H3("Transit planning and frequency setting"),
  P(`Bus planning is classically decomposed into network design, frequency setting, timetabling, and vehicle and crew scheduling ${cite("cw86", "ceder16")}; Ibarra-Rojas et al. ${cite("ibarra15")} review the planning, operation and control problems in this chain. Furth and Wilson ${cite("fw81")} formulated the allocation of a fixed fleet across routes and time periods subject to fleet-size and loading constraints, which is the structure of the present model. Martínez et al. ${cite("martinez14")} formulate frequency setting as a mixed-integer program over a discrete set of frequencies, and Verbas and Mahmassani ${cite("verbas15")} allocate frequencies over routes and time periods while exposing the trade-offs explicitly.`),
  H3("Multi-objective transit optimization"),
  P(`When routes and frequencies are designed together, the search space is very large and metaheuristics dominate: Arbex and da Cunha ${cite("arbex15")} use an alternating-objective genetic algorithm, Jha et al. ${cite("jha19")} a multi-objective particle swarm compared with NSGA-II, and Ahern et al. ${cite("ahern22")} warn that fleet-minimising designs that ignore passenger response can produce overcrowding. NSGA-II ${cite("deb02")} is the standard elitist multi-objective genetic algorithm. For exact fronts, the augmented ε-constraint method AUGMECON ${cite("mavrotas09")} avoids weakly efficient solutions, and AUGMECON2 ${cite("mavrotas13")} is designed for integer programs.`),
  H3("Goal programming"),
  P(`Goal programming originates with Charnes and Cooper ${cite("cc61")}. Each objective becomes a goal with a target, deviation variables measure under- and over-achievement, and only the unwanted deviations are minimised, either in strict priority order (preemptive) or as a weighted sum of normalised deviations ${cite("jt10")}. The method makes priorities explicit, but its answer depends on the targets and on the normalisation.`),
  H3("Demand uncertainty: stochastic and fuzzy approaches"),
  P(`Stochastic programming handles uncertain demand when distributions can be estimated, for example in transit network design ${cite("anlo16")} and frequency setting ${cite("gk22")}. When data are too scarce to fit distributions, fuzzy sets ${cite("zadeh65")} represent demand by a few expert values; Zimmermann ${cite("zimm78")} solved fuzzy multi-objective linear programs, and possibilistic linear programming ${cite("ir00")} converts fuzzy coefficients into crisp constraints through α-level cuts. The present project uses this α-cut route.`),
  H3("Service standards and the Indian context"),
  P(`Transport for London plans bus service levels against published guidelines ${cite("tfl12")}, and Singapore's bus service reliability framework rewards operators according to Excess Wait Time ${cite("leong16")}; this report uses EWT as a reliability measure. GPS studies of Indian city buses report average speeds of 17.8 km/h in the peak and 21.5 km/h off-peak in Chennai ${cite("mahesh17")} and strong spatial and temporal variation in Ahmedabad ${cite("jain22")}. A review of crowding valuation ${cite("fedujwar24")} shows that crowding costs are context-specific, so this project does not convert crowding into money.`),
  new Paragraph({ children: [], spacing: { after: 60 } }),
  caption("Table", "Summary of the reviewed literature and its use in this project"),
  table(["Ref.", "Topic", "Use in this project"], litRows, [1500, 3700, 3826]),
  H2("2.2 Research Gaps"),
  BUL("**Goal programming in bus frequency and fleet allocation.** A Crossref search of peer-reviewed work from 2014 to 2026 found no study applying goal programming to bus frequency setting or fleet allocation; the goal-programming transportation papers found address the classical (shipping) transportation problem. This is a statement about our search, not a claim that no such study exists."),
  BUL("**No public ridership.** CTU publishes no ridership data, so the method must work with fuzzy, synthetic demand and must be ready to take real data later."),
  BUL("**Exact versus heuristic fronts at realistic size.** Many frequency-setting studies use only metaheuristics; for a fixed-route network of this size, the exact MILP can be solved directly and used to benchmark NSGA-II."),
  BUL("**Corrected formulation.** The synopsis formulation contained four mathematical errors (Section 3.3), which had to be fixed before any result could be trusted."),
];

// ------------------------------------------------------------------ Chapter 3
const corrections = [
  ["Z_{1} = Σ D_{rt}·30/f_{rt}", "Nonlinear in f (division by a decision variable)", "Headway menu with binaries y_{rtk}; Z_{1} = Σ M_{rt} Σ_{k}(h_{k}/2) y_{rtk} is linear"],
  ["Z_{2} = Σ d_{r}·x_{rt}", "Counts buses, not distance run", "Vehicle-km Z_{2} = Σ d_{r}^{cyc} H_{rt} f_{rt}"],
  ["o_{rt} ≥ D_{rt} − C·x_{rt}", "Capacity per hour depends on frequency, not on buses", "o_{rt} ≥ D_{rt}^{α} − C·f_{rt}"],
  ["C x ≥ D^{L} + (1−α)(D^{M} − D^{L})", "Lower α-cut: plans for low demand; probability statement used for a fuzzy number", "Upper α-cut D^{α} = U − α(U − M); possibility (α-level) interpretation"],
  ["f_{rt} continuous", "Published headways come in discrete steps", "Discrete headway menu K_{rt} (route-specific)"],
];
const tools = [
  ["Programming", "Python 3.13; pandas 2.3, NumPy 2.3, SciPy 1.16, Matplotlib 3.10, openpyxl 3.1", "Data handling, analysis, figures"],
  ["Optimization", "PuLP 4.0.1 with the HiGHS 1.15 MILP solver", "Exact MILP, goal programming, AUGMECON"],
  ["Metaheuristic", "DEAP 1.4", "NSGA-II"],
  ["Testing", "pytest 9.1 (100 automated tests)", "Correctness of data, model, solvers and simulation"],
  ["Literature", "Crossref metadata API, TRB TRID, publisher pages", "Verification of every reference"],
  ["Hardware", "Standard laptop (12 logical cores)", "All runs; full pipeline in about 7 minutes"],
  ["Equipment", "None required so far", "Manual boarding counts (planned) need only counting sheets"],
];
const ch3 = [
  H1("Chapter 3  Methodology", true),
  H2("3.1 Block Diagram"),
  P("Figure 1 shows the seven-stage pipeline that was implemented. A single command (python run_all.py) runs all stages in order and regenerates every table and figure in this report."),
  ...figure("methodology_block_diagram.png", "Methodology block diagram of the implemented pipeline", 4.6),
  H2("3.2 Data Preparation and Calibration"),
  P(`The timetable workbook was parsed into a clean route table: the TOTAL and summary rows were dropped, route numbers were kept as strings (for example “25/25A”), and frequencies were computed exactly as 60 divided by the headway. All ${F.data.routes} routes match the timetable PDF; ${F.data.mv_mismatch} rounded cells in the original workbook were replaced by exact values. ${F.data.loops} routes are loops (origin equals destination) and ${F.data.overnight} are overnight services.`),
  P("The cycle time of route r (time for one bus to return to its starting point) is"),
  EQ("τ_{r} = L_{r} / v · (1 + ℓ),   L_{r} = 2d_{r} (non-loop) or d_{r} (loop)", "3.1"),
  P(`where v is the average operating speed and ℓ the layover fraction. By Little's law, a route running f departures per hour in each direction needs f·τ buses. Three readings of the published length were compared against the fleet (Section 5.1). Only the one-way reading makes the published timetable consistent with the allocation, and the working setting is v = 22 km/h with 10% layover. This is a consistency argument, not a proof; CTU must confirm the length convention.`),
  H2("3.3 Corrected Mathematical Model"),
  P(`Sets: routes r ∈ R (${F.data.routes}), periods t ∈ T = {AM 07-10, Midday 10-16, PM 16-19}, and for each active route-period a headway menu K_{rt} built from {${F.model.menu.join(", ")}} minutes plus the route's published headways. Decision variables: binary y_{rtk} (route r uses headway k in period t), integer buses x_{rt}, and overflow o_{rt} ≥ 0. Parameters: modal demand M_{rt} and its α-cut D_{rt}^{α} (passengers per hour), service hours H_{rt}, cycle distance d_{r}^{cyc}, bus capacity C = ${F.model.C}, and B_{eff} = ${F.model.B_eff} buses (spare ratio ${Math.round(100 * F.model.spare)}%).`),
  P("The three objectives, all minimised, are:"),
  ...MODEL_EQ.map(([e], i) => EQ(e, "3." + (i + 2))),
  P("Z_{1} is the expected waiting rate (passenger-minutes per hour, half the headway per passenger), Z_{2} the operating effort (vehicle-km per day) and Z_{3} the number of passengers above capacity per day. The objectives are subject to:"),
  ...CONS_EQ.map(([e], i) => EQ(e, "3." + (i + 5))),
  P("Equation (3.5) selects exactly one headway for every active route-period and defines its frequency; (3.6) is the fleet limit in every period, with B_{eff} = ⌊(1 − s)B⌋; (3.7) gives the buses needed to run the chosen frequency; (3.8) measures overflow above the hourly capacity C·f; (3.9) keeps frequencies within the published bounds through the menu K_{rt}; and (3.10) limits changes from the published allocation. The 60/90-minute headway cap is treated as a soft goal."),
  P(`The model has ${F.model.pairs} active route-periods, ${F.model.n_vars} variables and ${F.model.n_cons} constraints, and solves to proven optimality in well under a second. Its correctness was checked against brute-force enumeration on a small test network. Table 2 lists the corrections relative to the synopsis.`),
  caption("Table", "Corrections made to the synopsis formulation"),
  C.table(["Synopsis", "Problem", "Correction"], corrections, [2700, 2900, 3426]),
  P(`Two published constraints made the brief infeasible as first stated, and were adjusted with reasons recorded in the project's decision log: with 10% spares, the published minimum frequencies need at least ${F.model.infeasible_s10.split(" > ")[0]} buses but only ${F.model.infeasible_s10.split(" > ")[1]} would be available, so the spare ratio is 8%; and the practicality rule |x − x^{0}| ≤ min(3, 0.3x^{0}) froze every small route, so a minimum change of one bus is allowed.`, { after: 120 }),
  H2("3.4 Fuzzy Demand and the α-Cut"),
  P(`Demand on each route-period is a triangular fuzzy number (L, M, U) with L = ${(1 - F.demand.lo).toFixed(2)}M and U = ${(1 + F.demand.hi).toFixed(2)}M, right-skewed because demand surges are larger than dips. For a confidence level α ∈ [0, 1], the upper end of the α-cut is`),
  EQ("D_{rt}^{α} = U_{rt} − α (U_{rt} − M_{rt})", "3.11"),
  P("Capacity is planned against this value: α = 1 plans for the most plausible demand M, and α = 0 for the most conservative value U. The waiting objective uses M, because it measures the expected passenger experience; the capacity constraint uses D^{α}, because it is a safety requirement."),
  ...figure("tfn_alpha_cuts.png", "Triangular fuzzy demand and its α-cuts for one route-period (synthetic demand)", 5.2),
  H2("3.5 Goal Programming with Priorities"),
  P(`Each objective becomes a goal with a target taken from the published schedule: G1 waiting at most ${Math.round(100 * F.gp.kappa1)}% below today, G2 zero overflow, G3 vehicle-km at least ${Math.round(100 * F.gp.kappa3)}% below today, and G4 no headway above 60 minutes in the peaks or 90 minutes at midday. Deviation variables measure how far each goal is missed, and only the unwanted deviations are minimised. Preemptive goal programming minimises them in a strict priority order, locking each level before moving to the next; weighted goal programming minimises a sum of deviations divided by their baseline values; and a Chebyshev variant minimises the largest normalised deviation. The fleet and frequency-fleet constraints stay hard throughout. Three priority orders were studied (passenger-first, operator-first, equity-first), plus the balanced weighted form and the Chebyshev form. The targets for G1 and G3 were set inside the attainable range after the best achievable values were known; this is disclosed in Section 5.3.`),
  H2("3.6 Pareto Front: Exact and Heuristic Methods"),
  P(`The exact front was computed with AUGMECON ${cite("mavrotas09")}: minimise Z3 subject to Z1 ≤ ε1 and Z2 ≤ ε2 on a ${F.pareto.grid} × ${F.pareto.grid} grid, with slack terms in the objective so that only strictly efficient points are returned, and early exit once a grid cell is infeasible. NSGA-II ${cite("deb02")} encodes one headway choice per route-period; a repair step restores the fleet and frequency-fleet constraints by lengthening the headway with the smallest loss per bus released. It was run with a population of 200 for 300 generations, crossover probability 0.9 and mutation probability 1/n per gene, for 5 fixed random seeds. The two fronts are compared by hypervolume, generational distance, inverted generational distance, coverage, and a strict-dominance check.`),
  H2("3.7 Sampling"),
  P("Two kinds of sampling are used, and a third is planned."),
  BUL(`**Synthetic demand construction.** Each route receives a score proportional to its length and raised for serving PGI, ISBT-43 or ISBT-17, for terminating outside the city sectors, for terminating at Derabassi, and for every hub stop served. The score is multiplied by a fixed log-normal noise factor (seed 42). Scores are scaled so that the network total is ${n0(F.demand.daily_boardings)} boardings per day, a figure scaled from a CTU-wide ridership report that has not yet been verified. Period multipliers are 1.4 (AM), 0.8 (Midday) and 1.3 (PM).`),
  BUL(`**Monte Carlo demand days.** ${n0(F.sim.N)} demand scenarios were drawn (seed ${F.sim.seed}). Each route-period demand is sampled from its triangular distribution and multiplied by a common day-level shock drawn from Normal(1, 0.05), so that busy days are busy everywhere. Every schedule is evaluated on the same draws (common random numbers). Bus arrivals follow gamma-distributed headways with coefficient of variation ${F.sim.cv}, giving an expected wait of (h/2)(1 + CV²).`),
  BUL("**Planned field sampling.** Manual boarding counts at 5 to 10 hub stops (ISBT-17, ISBT-43, PGI and others) on at least 10 weekdays, together with CTU ticket-machine data if granted, to estimate L, M and U as the 10th, 50th and 90th percentiles of observed demand."),
  H2("3.8 Tools, Software and Equipment Used"),
  caption("Table", "Tools, software and equipment"),
  C.table(["Category", "Tool / version", "Purpose"], tools, [1700, 4100, 3226]),
  P("Compared with the synopsis, Google OR-Tools, PyGMO and scikit-fuzzy were not needed: PuLP with HiGHS solved the MILP directly, DEAP provided NSGA-II, and the fuzzy α-cut is a closed-form expression.", { after: 120 }),
];

// ------------------------------------------------------------------ Chapter 4
const phases = [
  ["1", "Data audit and calibration", "Validated route table; calibration report", "Completed"],
  ["2", "Time periods, synthetic demand, fuzzy numbers", "Demand table (L, M, U); demand report", "Completed"],
  ["3", "Corrected MILP and baseline evaluation", "Model, baseline metrics", "Completed"],
  ["4", "Goal programming with priorities", "Five scenarios × 5 α values × 2 bound settings", "Completed"],
  ["5", "Pareto front: AUGMECON and NSGA-II", "Exact and heuristic fronts, metrics", "Completed"],
  ["6", "Simulation and sensitivity", "2000-day simulation, sensitivity and out-of-sample tests", "Completed"],
  ["7", "Self-review and literature verification", "Examiner-style review; verified references", "Completed"],
  ["8", "Real ridership data and validation", "ETM data request; hub counts", "Pending"],
  ["9", "Remaining model refinements", "Benchmark rule, route speeds, waiting model", "Planned"],
];
const ch4 = [
  H1("Chapter 4  Work Completed", true),
  H2("4.1 Project Timeline"),
  P("The project was executed in the stages below. Each stage ended with a definition-of-done check and automated tests."),
  caption("Table", "Project phases and status"),
  C.table(["#", "Phase", "Main output", "Status"], phases, [500, 3400, 3726, 1400], { highlight: (r) => r[3] !== "Completed" }),
  H2("4.2 Work Done So Far"),
  BUL(`**Data.** ${F.data.routes} routes, ${F.data.buses} buses, ${n0(F.data.km)} km and ${F.data.stops} stops were extracted and checked against the timetable PDF; the operating windows and period activity were cross-checked (AM ${F.demand.active.AM}, Midday ${F.demand.active.Midday}, PM ${F.demand.active.PM} active routes).`),
  BUL("**Calibration.** Cycle-time scenarios were compared against the fleet; the one-way reading at 22 km/h with 10% layover was adopted, pending CTU confirmation."),
  BUL("**Model.** The corrected MILP was implemented and verified against brute-force enumeration on a small instance, with unit tests on every formula."),
  BUL(`**Goal programming.** Preemptive, weighted and Chebyshev goal programming was implemented; ${F.gp.runs} scenario runs all solved to proven optimality, and the lexicographic order was verified.`),
  BUL(`**Pareto analysis.** An exact AUGMECON front (${F.pareto.exact_points} efficient points) and NSGA-II fronts for 5 seeds were computed and compared.`),
  BUL(`**Simulation.** ${n0(F.sim.N)} demand days were simulated for 12 schedules, with sensitivity to demand level, capacity, speed, spares, layover, α and fleet size, and an out-of-sample test.`),
  BUL("**Quality.** 100 automated tests pass; an examiner-style self-review was carried out and its most critical point (the choice of baseline) was addressed by adding a peak-frequency baseline."),
  H2("4.3 Challenges Faced"),
  BUL("**No ridership data.** Demand had to be constructed synthetically with documented assumptions; every result is therefore illustrative."),
  BUL("**Errors in the synopsis formulation.** Four formulas were mathematically wrong (Table 2) and were corrected before implementation."),
  BUL(`**Infeasibility of the stated brief.** Published headways such as 35, 50 or 80 minutes were not in the headway menu; a 60-minute peak cap conflicted with published 75-90-minute headways; and 10% spares left too few buses for the published minimum frequencies. Each was diagnosed precisely and resolved with a documented change.`),
  BUL("**Calibration ambiguity.** Whether the published route length is one-way or a full cycle changes the fleet requirement by a factor of almost two; it was resolved by a consistency test and still needs CTU confirmation."),
  BUL("**Software changes.** PuLP 4 no longer bundles the CBC solver and changed its interface; the HiGHS solver was used instead."),
  BUL("**Reference verification.** Three references in the synopsis (Daduna 2004, TfL 2024, LTA 2023) could not be verified and were replaced by verified sources."),
];

// ------------------------------------------------------------------ Chapter 5
const calRows = [["S1: length = full cycle", "22 km/h, no layover", F.calib.S1_22_0.N, F.calib.S1_22_0.U + "%", F.calib.S1_22_0.over],
                 ["S2: length one-way", "22 km/h, no layover", F.calib.S2_22_0.N, F.calib.S2_22_0.U + "%", F.calib.S2_22_0.over],
                 ["S2", "22 km/h, 10% layover", F.calib.S2_22_10.N, F.calib.S2_22_10.U + "%", F.calib.S2_22_10.over],
                 ["S3: S2 + 10% spares", "22 km/h, 10% layover", F.calib.S3_22_10.N, F.calib.S3_22_10.U + "%", F.calib.S3_22_10.over],
                 ["S2", "18 km/h, no layover", F.calib.S2_18_0.N, F.calib.S2_18_0.U + "%", F.calib.S2_18_0.over]];
const gpRows = F.gp.rows.map((r) => [r.name, order[r.name], pct(r.dZ1), pct(r.dZ2), pct(r.dZ3), String(r.eq), r.met + " of 4"]);
const simNames = [["Baseline", "Published schedule (mid frequency)"], ["Baseline (peak f_max)", "Published schedule (peak frequency)"],
                  ["P-PASSENGER (α=0.5)", "P-PASSENGER"], ["P-OPERATOR (α=0.5)", "P-OPERATOR"], ["P-EQUITY (α=0.5)", "P-EQUITY"],
                  ["P-BALANCED (α=0.5)", "P-BALANCED"], ["P-BALANCED (α=0)", "P-BALANCED, α = 0"], ["KNEE (Pareto front)", "Knee of the Pareto front"]];
const simRows = simNames.map(([k, lab]) => { const r = F.sim.rows[k];
  return [lab, r.wait.toFixed(2), n0(r.over), n0(r.vkm), String(r.fleet), String(r.eq), r.p5.toFixed(1) + "%"]; });
const pm = F.pareto;
const ch5 = [
  H1("Chapter 5  Results and Discussion", true),
  P("All results that depend on passenger demand use synthetic demand and are illustrative. They show how the method behaves; they are not measured CTU outcomes.", { run: { italics: true } }),
  H2("5.1 Observations"),
  H3("Calibration"),
  P(`Table 5 compares the buses needed to run the published mid-range frequencies with the ${F.data.buses} buses allocated. If the published length were a full cycle (S1), only ${F.calib.S1_22_0.U}% of the fleet would be needed and ${F.calib.S1_22_0.over} of 68 routes would hold more buses than even their highest published frequency requires. Under the one-way reading with 10% layover, ${F.calib.S2_22_10.U}% of the fleet is needed (${F.calib.S3_22_10.U}% with 10% spares), and only ${F.calib.S2_22_10.short} routes look short of buses. At 18 km/h, ${F.calib.S2_18_0.short} routes could not run their published minimum frequency, which contradicts the timetable CTU actually operates. The speed that exactly fills the fleet is ${F.calib.v_implied_noSpare} km/h without spares and ${F.calib.v_implied_spare} km/h with 10% spares, consistent with measured Indian bus speeds ${cite("mahesh17")}.`),
  caption("Table", "Buses needed to run the published timetable, by calibration scenario"),
  C.table(["Scenario", "Speed, layover", "Buses needed", "Share of 389", "Routes over-supplied"], calRows, [2500, 2100, 1450, 1450, 1526],
    { align: [0, 0, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER] }),
  ...figure("calibration_N_need.png", "Buses needed across calibration scenarios vs the allocated fleet", 6.0),
  H3("Synthetic demand"),
  P(`Mean modal demand is ${F.demand.mean_M.AM} passengers per hour per route in the AM peak, ${F.demand.mean_M.Midday} at midday and ${F.demand.mean_M.PM} in the PM peak, with a coefficient of variation across routes of ${F.demand.cv.AM}-${F.demand.cv.Midday}. Against published capacity, ${F.demand.overloaded.AM} route-periods are overloaded in the AM peak, mostly long routes with 75-90-minute headways. This pattern follows directly from the synthetic construction, in which demand grows with route length.`),
  ...figure("demand_heatmap.png", "Modal demand by route and period (synthetic demand)", 2.45),
  H3("Baseline against the model's constraints"),
  P(`The published schedule keeps ${BASE.fleet} buses on the road at the busiest time, more than the ${F.model.B_eff} allowed by the model's 8% spare rule (by ${F.model.c1_excess.AM}, ${F.model.c1_excess.Midday} and ${F.model.c1_excess.PM} buses in the AM, Midday and PM periods). Routes ${F.model.c2_routes.join(", ")} cannot run their mid-range frequency with their own buses at 22 km/h. The optimised schedules therefore have fewer buses available than the published one.`),
  H2("5.2 Graphs and Comparisons"),
  H3("Goal programming"),
  P(`With the published frequency limits, all five scenarios give the same schedule (waiting ${pct(F.gp.published.dZ1)}, overflow ${pct(F.gp.published.dZ3)}): the goals do not conflict, because the overcrowded routes are already at their highest published frequency. When the maximum frequency is relaxed by two menu levels, the priorities matter (Table 6). Passenger-first and Chebyshev schedules give the largest overflow reduction but leave 100 minutes of headway above the equity caps; equity-first and balanced schedules remove every headway above the cap for a slightly smaller overflow reduction, and meet three of the four goals.`),
  caption("Table", "Goal-programming scenarios (f_max relaxed, α = 0.5; change vs the published schedule; synthetic demand)"),
  C.table(["Scenario", "Priority", "Waiting", "Vehicle-km", "Overflow", "Above cap (min)", "Goals met"], gpRows,
    [1450, 2300, 950, 1050, 1000, 1150, 1126],
    { size: 19, highlight: (r) => r[0] === "P-BALANCED", align: [0, 0, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER, AlignmentType.CENTER] }),
  ...figure("gp_pct_change.png", "Change vs the published schedule by goal-programming scenario (synthetic demand)", 6.2),
  H3("Pareto front"),
  P(`The ${pm.grid} × ${pm.grid} AUGMECON grid gave ${pm.optimal} optimal cells, ${pm.infeasible} infeasible cells and ${pm.skipped} cells skipped by early exit, yielding ${pm.exact_points} distinct strictly efficient points in ${pm.t_exact} s. NSGA-II returned ${pm.nsga_points} non-dominated points per seed in about ${pm.t_seed} s per seed (${n0(pm.evals)} evaluations). The NSGA-II hypervolume (${pm.hv_seed_min.toFixed(3)}-${pm.hv_seed_max.toFixed(3)} per seed, ${pm.hv_union.toFixed(3)} for the union) is higher than that of the exact grid (${pm.hv_exact.toFixed(3)}) only because its many points fill the gaps between grid samples: no NSGA-II point strictly dominates any exact point (${pm.dominated} cases), and its mean generational distance to the exact front is ${pm.gd}. P-PASSENGER lies exactly on the front; P-BALANCED is ${pm.gp_dist["P-BALANCED"]} away in normalised units because it gives up a little overflow for full headway equity, a fourth criterion that the three-objective front does not show.`),
  ...figure("pareto_2d.png", "Two-dimensional projections of the exact and NSGA-II fronts, with the goal-programming solutions and the baseline (synthetic demand)", 6.4),
  H3("Simulation"),
  P(`Table 7 summarises ${n0(F.sim.N)} simulated demand days. The balanced schedule reduces expected waiting from ${BASE.wait.toFixed(2)} to ${POL.wait.toFixed(2)} minutes (${pct(H.vs_mid.wait)}), overflow from ${n0(BASE.over)} to ${n0(POL.over)} passengers per day (${pct(H.vs_mid.over)}) and vehicle-km by ${pct(H.vs_mid.vkm)}, using ${POL.fleet} instead of ${BASE.fleet} buses. The share of days on which overflow exceeds 5% of demand falls from ${BASE.p5}% to ${POL.p5}%. Against the fairer peak-frequency baseline, the changes are ${pct(H.vs_peak.wait)} waiting, ${pct(H.vs_peak.over)} overflow and ${pct(H.vs_peak.vkm)} vehicle-km, so the headline result is not an artefact of the baseline definition. The waiting differences among the optimised schedules are only a few seconds and should not be used to rank them.`),
  caption("Table", "Simulated performance over 2000 demand days (synthetic demand)"),
  C.table(["Schedule", "Wait (min)", "Overflow (pax/day)", "Vehicle-km/day", "Buses", "Above cap (min)", "P(overflow > 5%)"], simRows,
    [2550, 900, 1150, 1250, 800, 1050, 1326],
    { size: 19, highlight: (r) => r[0] === "P-BALANCED", align: [0, 1, 1, 1, 1, 1, 1].map((a) => (a ? AlignmentType.CENTER : AlignmentType.LEFT)) }),
  ...figure("sim_tradeoff_bars.png", "Simulated change vs the published schedule, by metric and schedule (synthetic demand)", 6.4),
  ...figure("sim_overflow_distribution.png", "Distribution of overflow as a share of demand across simulated days (synthetic demand)", 5.6),
  H3("Sensitivity and robustness"),
  P(`The wait improvement of the balanced policy ranges from ${Math.min(...F.sens.filter((r) => r.feasible).map((r) => r.imp)).toFixed(1)}% to ${Math.max(...F.sens.filter((r) => r.feasible).map((r) => r.imp)).toFixed(1)}% across the feasible settings, and is most sensitive to speed and layover. Several settings are infeasible because the published minimum frequencies alone need more buses than are available: ${infeasible.join("; ")}. When demand is more uncertain than planned (spreads ×1.5, day shock sd 0.10), the share of days with overflow above 5% rises from ${F.oos["P-BALANCED (α=0.5)"].ins}% to ${F.oos["P-BALANCED (α=0.5)"].out}% for the balanced policy and from ${F.oos["Baseline"].ins}% to ${F.oos["Baseline"].out}% for the published schedule. A variant planned for that wider uncertainty did worse (${F.oos["P-BALANCED ROBUST (α=0, spreads ×1.5)"].ins}% and ${F.oos["P-BALANCED ROBUST (α=0, spreads ×1.5)"].out}%): with a fixed fleet, planning for higher demand everywhere cannot add capacity. The choice of α changes little, because the headway menu is coarse.`),
  ...figure("sensitivity_tornado.png", "One-factor-at-a-time sensitivity of the wait improvement (synthetic demand)", 6.0),
  ...figure("sensitivity_out_of_sample.png", "Overflow risk in-sample and when demand is more uncertain than planned (synthetic demand)", 5.6),
  H2("5.3 Discussion and Limitations"),
  P("The method works as intended: the corrected model is linear and solves exactly at full network size, goal programming exposes how priorities change the schedule, the exact and heuristic fronts agree, and the simulation shows that the optimised schedules carry less crowding risk than the published one while using fewer buses. Several caveats limit what the numbers mean."),
  BUL("**Synthetic demand.** Demand grows with route length and with hub, PGI and ISBT flags, so the gains concentrate on long, infrequent routes partly by construction."),
  BUL("**Calibration.** A single speed of 22 km/h makes some routes look over-supplied, which frees buses for others; route-specific running times are needed to test this."),
  BUL("**Targets.** The goal-programming targets were set after the best achievable values were known, so goal achievement is conditional on those targets."),
  BUL("**Modelling simplifications.** The waiting objective is a per-hour rate not weighted by period length; the h/2 waiting rule overstates waiting at long headways; there is no within-period peak-hour factor; buses move freely between routes across periods; and there are no transfers, depot, crew or stop-capacity constraints."),
  BUL("**Relaxed frequency limits.** The headline results allow two headway levels shorter than the published minimum, which would need CTU approval."),
];

// ------------------------------------------------------------------ Chapter 6
const plan = [
  ["Month 1", "Request ETM ticket data from CTU; boarding counts at 5-10 hubs; confirm the route-length convention and fleet composition"],
  ["Month 2", "Simple benchmark (demand-proportional and square-root frequency rules); route-specific running times; arrival-timing waiting model; peak-hour factor"],
  ["Month 3", "Replace synthetic demand with observed L/M/U; re-run all stages; robustness to demand construction and goal targets"],
  ["Month 4", "Final report and viva; conference paper preparation and submission"],
];
const ch6 = [
  H1("Chapter 6  Future Work with Timeline", true),
  P("The remaining work focuses on replacing assumptions with data and on testing whether the gains survive fairer comparisons."),
  BUL("**Real ridership.** CTU ticket-machine (ETM) records and manual boarding counts at hub stops; estimate L, M and U as the 10th, 50th and 90th percentiles of observed daily demand."),
  BUL("**Fairer comparisons.** A simple benchmark rule, route-specific running times, and a sweep of goal targets."),
  BUL("**Better waiting model.** Passengers time their arrivals at long headways, and demand peaks within each period."),
  BUL("**Operations.** Depot and interlining constraints, driver duties, stop and terminal capacity at shorter headways, and timetable-level scheduling of departure times."),
  BUL("**Demand prediction.** Once labelled ridership exists, a prediction model (for example gradient-boosted trees such as XGBoost) could forecast L, M and U for the same α-cut model."),
  caption("Table", "Timeline for the remaining work"),
  C.table(["Period", "Planned work"], plan, [1500, 7526]),
  H2("6.1 Conference Targeted"),
  BUL("**Conference of Transportation Research Group of India (CTRG).** Biennial; the 8th edition was held at IIT Guwahati in December 2025, so the next edition is expected in 2027. The call for papers must be confirmed on the official site."),
  BUL("**Annual Convention of the Operational Research Society of India (ORSI).** Usually held in December; the date and deadlines of the next convention must be confirmed on the society's site."),
  P("A submission would present the method and the synthetic-demand results as a methodological case study, and would be strengthened substantially by the real-ridership validation planned in Months 1-3."),
];

// ------------------------------------------------------------------ References
const refs = [H1("References", true),
  ...REFS.map((r, i) => new Paragraph({ spacing: { after: 100, line: 300 }, indent: { left: 567, hanging: 567 }, alignment: AlignmentType.LEFT,
    children: runs("[" + (i + 1) + "]\t" + r[1], { size: 22 }) }))];

// ------------------------------------------------------------------ document
const footer = (fmt) => new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 })] })] });
const page = { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } };
const doc = new Document({
  creator: "Daksh Garg, Piyush Aggarwal, Abhay Chauhan, Naman Vasudev",
  title: "Minor Project Progress Report: Bus Fleet Allocation under Demand Variability",
  styles, numbering,
  sections: [
    { properties: { page }, children: title },
    { properties: { page: { ...page, pageNumbers: { start: 1, formatType: NumberFormat.LOWER_ROMAN } }, type: SectionType.NEXT_PAGE },
      footers: { default: footer() }, children: [...declaration, ...ack, ...abstract, ...toc] },
    { properties: { page: { ...page, pageNumbers: { start: 1, formatType: NumberFormat.DECIMAL } }, type: SectionType.NEXT_PAGE },
      footers: { default: footer() }, children: [...ch1, ...ch2, ...ch3, ...ch4, ...ch5, ...ch6, ...refs] },
  ],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT); });

