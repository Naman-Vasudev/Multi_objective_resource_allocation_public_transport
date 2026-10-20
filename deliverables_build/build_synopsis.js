// Revised synopsis: same structure as the submitted synopsis, with the mathematical and citation errors corrected.
const fs = require("fs");
const path = require("path");
const C = require("./docx_common.js");
const { D, F, REFS, runs, P, EQ, H1, H2, BUL, NUM, figure, table, numbering, styles, MODEL_EQ, CONS_EQ, FONT, NAVY, n0 } = C;
const { Document, Packer, Paragraph, AlignmentType, ImageRun, Footer, PageNumber, TextRun } = D;
const OUT = path.join(C.PROJ, "Minor_Project_Synopsis_Revised.docx");

// citations numbered in order of first use (only cited works are listed)
const used = [];
const cite = (...keys) => "[" + keys.map((k) => { if (!used.includes(k)) used.push(k); return used.indexOf(k) + 1; }).join(", ") + "]";
const center = (text, o = {}) => new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: o.after ?? 120 },
  children: runs(text, { size: o.size || 24, bold: o.bold, italics: o.italics, color: o.color }) });
const H2n = (t) => new Paragraph({ heading: D.HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT })], spacing: { before: 200, after: 100 }, keepNext: true });

const logo = fs.readFileSync(path.join(C.MEDIA, "pec_logo.png"));
const ls = C.pngSize(path.join(C.MEDIA, "pec_logo.png"));
const cover = [
  center("PUNJAB ENGINEERING COLLEGE (DEEMED TO BE UNIVERSITY), CHANDIGARH", { bold: true, size: 26, after: 240 }),
  center("MINOR PROJECT SYNOPSIS (REVISED)", { bold: true, size: 28, color: NAVY, after: 240 }),
  center("OPTIMIZATION-BASED RESOURCE ALLOCATION FOR PUBLIC BUS FLEET SCHEDULING UNDER DEMAND VARIABILITY", { bold: true, size: 30, after: 120 }),
  center("(A case-study orientation using the Chandigarh Transport Undertaking)", { italics: true, after: 300 }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 300 }, children: [new ImageRun({ type: "png", data: logo,
    transformation: { width: 150, height: 150 * ls.h / ls.w }, altText: { title: "PEC logo", description: "Punjab Engineering College logo", name: "logo" } })] }),
  center("Submitted in partial fulfilment of the requirements for the award of the degree of", { after: 60 }),
  center("BACHELOR OF TECHNOLOGY in MATHEMATICS AND COMPUTING", { bold: true, after: 300 }),
  center("Under the guidance of", { italics: true, after: 40 }), center("Dr. Sumati Mahajan", { bold: true, after: 20 }),
  center("Department of Mathematics, Punjab Engineering College", { after: 240 }),
  center("Submitted by", { italics: true, after: 40 }),
  center("Daksh Garg (24112005)    Piyush Aggarwal (24112006)", { after: 20 }),
  center("Abhay Chauhan (24112015)    Naman Vasudev (24112032)", { after: 300 }),
  center("DEPARTMENT OF MATHEMATICS AND COMPUTING, PUNJAB ENGINEERING COLLEGE, CHANDIGARH", { bold: true, after: 60 }),
  center("Revised October 2026: corrects the formulation and references of the submitted synopsis (see Appendix A)", { italics: true, size: 20, after: 0 }),
];

const params = [
  ["R, T", "Routes r (68 CTU routes) and time periods t (AM 07-10, Midday 10-16, PM 16-19)"],
  ["K_{rt}", "Headway menu for route r in period t (minutes): {10, 12, 15, 20, 25, 30, 40, 45, 60, 90} plus the route's published headways, within its published range"],
  ["B, B_{eff}", "Buses allocated (389) and buses available for service after spares, B_{eff} = ⌊(1 − s)B⌋"],
  ["C", "Passenger capacity of one bus (seated plus permitted standees)"],
  ["D̃_{rt} = (L, M, U)", "Triangular fuzzy hourly demand on route r in period t: low, most plausible and high values (passengers per hour)"],
  ["τ_{r}", "Cycle time of route r in hours: running time for a full cycle plus layover"],
  ["d_{r}, d_{r}^{cyc}", "Published route length (one-way for non-loop routes) and distance per bus cycle (2d_{r}, or d_{r} for loops), km"],
  ["H_{rt}", "Hours of service of route r inside period t"],
  ["f_{r}^{min}, f_{r}^{max}", "Published frequency bounds (departures per hour) = 60 / longest and shortest published headway"],
];
const vars = [
  ["y_{rtk} ∈ {0, 1}", "1 if route r runs headway k ∈ K_{rt} in period t"],
  ["f_{rt} = Σ_{k} (60/h_{k}) y_{rtk}", "Resulting frequency (departures per hour); a linear expression, not a separate variable"],
  ["x_{rt} ∈ ℤ_{≥0}", "Buses allocated to route r in period t"],
  ["o_{rt} ≥ 0", "Overflow: passengers per hour above capacity on route r in period t"],
];
const corrections = [
  ["3.1 Decision variables", "f_{rt} continuous", "Published headways come in discrete steps, and a continuous f makes the waiting objective nonlinear", "f_{rt} chosen from a headway menu through binaries y_{rtk}"],
  ["3.2 Objective Z_{1}", "Σ D_{rt}·(30/f_{rt})", "Nonlinear (division by a decision variable); cannot be solved as an MILP", "Σ M_{rt} Σ_{k} (h_{k}/2) y_{rtk}, linear in y"],
  ["3.2 Objective Z_{2}", "Σ d_{r}·x_{rt}", "Counts buses times length, not distance run; ignores frequency and period length", "Vehicle-km Σ d_{r}^{cyc} H_{rt} f_{rt}"],
  ["3.3 Constraint (2)", "o_{rt} ≥ D_{rt} − C·x_{rt}", "Hourly capacity is C times departures per hour, not C times buses allocated", "o_{rt} ≥ D_{rt}^{α} − C·f_{rt}"],
  ["3.4 Demand bounds", "D^{L} “pessimistic”, D^{U} “optimistic”", "For capacity planning, high demand is the pessimistic case", "L = low demand, U = high demand"],
  ["3.4 Uncertainty", "P(C·x ≥ D̃) ≥ 1 − α and C·x ≥ D^{L} + (1−α)(D^{M} − D^{L})", "A probability statement needs a distribution, which a triangular fuzzy number does not define; the formula is the lower α-cut and plans for low demand", "Possibilistic α-level constraint C·f ≥ U − α(U − M) (upper α-cut)"],
  ["7 Solution methods", "MILP only for small instances; fuzzy model solved by simplex or interior point", "The corrected MILP solves the full network exactly in under a second; with integer variables the crisp model is still an MILP (branch and bound), not an LP", "Exact MILP for the full network; NSGA-II as a benchmark and for nonlinear extensions"],
  ["References [2], [3], [4]", "Daduna (2004); TfL (2024); LTA (2023)", "Could not be verified as cited", "Replaced by verified sources (Leong et al. 2016; TfL 2012)"],
  ["9 Expected outcomes", "“without requiring additional vehicles” stated as an outcome", "Cannot be claimed before real demand data are used", "Stated as a hypothesis to test"],
];
const tools = [["Programming", "Python (pandas, NumPy, SciPy, Matplotlib, openpyxl) for data, analysis and figures"],
               ["Optimization", "PuLP with the HiGHS solver for the MILP, goal programming and the ε-constraint method"],
               ["Metaheuristic", "DEAP for NSGA-II"],
               ["Fuzzy demand", "Closed-form triangular fuzzy numbers and α-cuts (no separate library needed)"],
               ["Testing", "pytest for automated checks of data, model, solvers and simulation"]];
const team = [["Daksh Garg (24112005)", "CTU timetable extraction, data processing and calibration", "Validated route table, cycle-time calibration"],
              ["Piyush Aggarwal (24112006)", "Passenger demand modelling and ridership data", "Synthetic and fuzzy demand; data request and survey"],
              ["Abhay Chauhan (24112015)", "Mathematical optimization and solvers", "MILP, goal programming, Pareto fronts"],
              ["Naman Vasudev (24112032)", "Validation, sensitivity analysis and integration", "Simulation, sensitivity charts, report"]];

const body = [
  H1("1. Introduction", false),
  P("Urban public transport is the backbone of mobility in rapidly growing Indian cities, and fixed-route buses are its most accessible and affordable mode. Transport undertakings must distribute a finite fleet over a network of routes whose demand varies across space and time. When scheduled departures do not follow passenger demand, the network suffers two failures at once: overcrowding and long waits on busy corridors, and under-used capacity on quiet ones."),
  P(`Mathematically, this is a constrained multi-objective resource-allocation problem: a limited pool of buses must be allocated across routes and time periods to balance conflicting objectives. More departures reduce waiting and crowding but increase operating distance and cost; fewer departures save cost but hurt passengers. A useful framework must expose these trade-offs rather than produce a single schedule ${cite("ceder16", "ibarra15")}.`),
  P(`This project develops such a framework for bus fleet allocation and frequency setting under uncertain demand, with a case-study orientation on the Chandigarh Transport Undertaking (CTU), which runs local and tri-city services in Chandigarh, Mohali and Panchkula. It uses CTU's published timetable ${cite("ctu26")} (routes, headways, route lengths and allocated buses) and is formulated generically, so that ridership data from any operator can be plugged in.`),
  H1("2. Problem Statement", false),
  P("Given a fixed number of buses, a network of fixed routes with known cycle times and published headway ranges, and passenger demand that varies by route and time period, determine for every route and period (i) a headway chosen from a discrete set of practical headways and (ii) the number of buses needed to run it. The schedule should minimise expected passenger waiting and overcrowding while keeping operating distance (vehicle-km) within budget, and must respect the fleet limit in every period, the buses required to sustain each frequency, the published frequency bounds and limits on how far allocations may change."),
  P("Demand varies from day to day and no ridership data are public, so demand is modelled as a triangular fuzzy number per route and period. The project tests whether a deterministic model evaluated against demand variation is sufficient, or whether the uncertainty should enter the constraints explicitly through α-cuts."),
  H1("3. Mathematical Modeling Framework", false),
  H2n("3.1 Sets, Parameters and Decision Variables"),
  table(["Symbol", "Meaning"], params, [2400, 6626]),
  new Paragraph({ spacing: { after: 120 }, children: [] }),
  table(["Decision variable", "Meaning"], vars, [3000, 6026]),
  H2n("3.2 Model Objectives"),
  P("All three objectives are minimised and are linear in the decision variables:"),
  ...MODEL_EQ.map(([e], i) => EQ(e, String(i + 1))),
  P(`Z_{1} is the demand-weighted waiting rate: with random arrivals the mean wait is half the headway, so a headway of h_{k} minutes costs M_{rt}h_{k}/2 passenger-minutes per hour. Writing it through the binary headway choice y_{rtk} keeps the model linear; the synopsis form ΣD·30/f is nonlinear in f. Discrete frequency sets are an established way to formulate frequency setting as a mixed-integer program ${cite("martinez14")}. Z_{2} is operating effort in vehicle-km per day, and Z_{3} counts passengers above capacity per day.`),
  H2n("3.3 Operational Constraints"),
  ...CONS_EQ.map(([e], i) => EQ(e, String(i + 4))),
  P(`Constraint (4) selects one headway per active route-period and defines its frequency. Constraint (5) is the fleet limit in every period. Constraint (6) is the frequency-fleet relation: a bus completes one cycle every τ_{r} hours, so x_{rt} buses sustain at most x_{rt}/τ_{r} departures per hour. Constraint (7) defines overflow against the hourly capacity C·f_{rt}; capacity depends on how often buses depart, not on how many are allocated. Constraint (8) keeps frequencies within the published bounds, and (9) limits changes from the current allocation. A maximum headway of 60 minutes in the peaks and 90 minutes at midday is treated as an equity goal. This structure follows the classical fleet-constrained frequency allocation of Furth and Wilson ${cite("fw81")}.`),
  H2n("3.4 Modelling Demand Uncertainty"),
  P(`Hourly demand is represented as a triangular fuzzy number D̃_{rt} = (L_{rt}, M_{rt}, U_{rt}), where L is low demand, M the most plausible demand and U high demand ${cite("zadeh65")}. For capacity planning, high demand is the pessimistic case. A probabilistic chance constraint P(capacity ≥ demand) ≥ 1 − α requires a probability distribution ${cite("cc59")}, which three fuzzy values do not provide. The fuzzy model therefore uses the possibilistic α-level constraint ${cite("ir00")}: at confidence level α ∈ [0, 1], capacity must cover the upper end of the α-cut,`),
  EQ("C f_{rt} ≥ D_{rt}^{α} = U_{rt} − α (U_{rt} − M_{rt})", "10"),
  P("so α = 1 plans for the most plausible demand M and α = 0 for the high value U. This replaces the synopsis expression L + (1 − α)(M − L), which is the lower α-cut and would plan capacity for low demand. The waiting objective uses M (the expected passenger experience), and the capacity constraint uses D^{α} (a safety requirement)."),
  H1("4. Proposed System Methodology", false),
  P("The workflow is a reproducible pipeline from data to policy evaluation (Figure 1). Each stage produces checked outputs, and the pipeline is re-run as better data arrive."),
  ...figure("methodology_block_diagram.png", "Optimization and system methodology", 4.4),
  H1("5. International Benchmarking and Best Practices", false),
  P(`Transport for London plans bus service levels against published planning guidelines ${cite("tfl12")}, and Singapore's Bus Service Reliability Framework rewards or penalises operators according to Excess Wait Time (EWT), the extra waiting caused by irregular service ${cite("leong16")}. We adopt their principles rather than their numbers: allocation is driven by demand at the busiest times, and reliability is measured by EWT = W^{actual} − W^{sched}, with W^{sched} = h/2 for a scheduled headway h. Until arrival (AVL) data are available, irregularity is represented by headways with a coefficient of variation CV, giving an expected wait of (h/2)(1 + CV²) and EWT = (h/2)CV². The model is a repeatable decision-support engine that can be re-run as demand changes, in the spirit of continuous network review.`),
  H1("6. Data Ingestion and Baseline Construction", false),
  P(`The published CTU timetable is the primary input. Parsing and validating it gives ${F.data.routes} routes, ${F.data.buses} allocated buses, ${n0(F.data.km)} km of route length and ${F.data.stops} named stops, with every route checked against the timetable PDF. Cycle times are calibrated so that the published frequencies are consistent with the allocated fleet; the evidence favours reading the published length as one-way, which CTU should confirm.`),
  P("For passenger demand, official ridership data (ticket-machine records or boarding counts) have been requested through CTU. Until they are available, demand is constructed synthetically from documented structural features (route length, service to major hubs such as PGI and the ISBTs, and number of hub stops) and scaled to a network-wide daily total. All results based on it are labelled synthetic and illustrative. A manual boarding count at 5 to 10 hub stops is planned to validate and replace the synthetic values, with L, M and U estimated as the 10th, 50th and 90th percentiles of observed demand."),
  H1("7. Proposed Solution Methods", false),
  NUM(`**Exact optimization (MILP).** The corrected model is a mixed-integer linear program. At the full CTU network size (${F.model.pairs} active route-periods, ${F.model.n_vars} variables) it is solved to proven optimality by branch and bound with an open-source solver. Trade-offs are traced with the augmented ε-constraint method (AUGMECON), which returns only strictly Pareto-efficient schedules ${cite("mavrotas09", "mavrotas13")}.`, "numbers"),
  NUM(`**Goal programming with priorities.** Each objective becomes a goal with a target; preemptive (priority-ordered), weighted and min-max goal programming generate passenger-first, operator-first, equity-first and balanced schedules ${cite("cc61", "jt10")}.`, "numbers"),
  NUM(`**Metaheuristic search (NSGA-II).** NSGA-II ${cite("deb02")} approximates the Pareto front in a single run. It is used to benchmark the exact front and as the route to nonlinear or simulation-based extensions.`, "numbers"),
  NUM(`**Fuzzy constraints.** Fuzzy demand enters through the crisp α-cut constraint (10), so the model remains an MILP. The resulting schedules are then stress-tested by Monte Carlo simulation of demand and headway irregularity, including ±10% and ±20% demand changes.`, "numbers"),
  H1("8. Software Tools, Team Split and Project Plan", false),
  table(["Category", "Tool and purpose"], tools, [2200, 6826]),
  new Paragraph({ spacing: { after: 120 }, children: [] }),
  table(["Team member", "Primary responsibility", "Key outputs"], team, [2600, 3400, 3026]),
  H1("9. Expected Outcomes", false),
  BUL("**Mathematical framework.** A corrected, linear multi-objective model for bus fleet allocation and frequency setting under fuzzy demand."),
  BUL("**Computational toolkit.** A reproducible Python codebase with exact MILP, goal programming, AUGMECON, NSGA-II and Monte Carlo evaluation, with automated tests."),
  BUL("**Baseline and gap analysis.** A validated CTU baseline that identifies route-periods where supply and demand are mismatched."),
  BUL("**Allocation alternatives.** Pareto-efficient and priority-based schedules. The hypothesis to test with real demand data is that waiting and overcrowding can be reduced without additional buses."),
  BUL("**Report and paper.** A final report and a research paper describing the method and the case study."),
  H1("10. Conclusion", false),
  P("This revised synopsis sets out a mathematically sound approach to bus fleet allocation under demand variability for the Chandigarh Transport Undertaking. The formulation balances passenger interests (waiting, crowding) and operator interests (vehicle-km) as a linear multi-objective program, represents uncertain demand with fuzzy α-cuts, and is solved exactly, with goal programming for explicit priorities and NSGA-II as a benchmark. The four corrections to the submitted synopsis, listed in Appendix A, are required for the model to be linear, dimensionally consistent and conservative in the right direction."),
];
const refs = () => [H1("References", false), ...used.map((k, i) => new Paragraph({ spacing: { after: 100, line: 300 },
  indent: { left: 567, hanging: 567 }, alignment: AlignmentType.LEFT,
  children: runs("[" + (i + 1) + "]\t" + (REFS.find((r) => r[0] === k) || EXTRA.find((r) => r[0] === k))[1], { size: 22 }) }))];
// verified (Crossref, doi:10.1287/mnsc.6.1.73); used only in the synopsis
const EXTRA = [["cc59", "A. Charnes and W. W. Cooper, “Chance-constrained programming,” Management Science, vol. 6, no. 1, pp. 73–79, 1959, doi: 10.1287/mnsc.6.1.73."]];
const appendix = [
  H1("Appendix A. Corrections to the Submitted Synopsis", true),
  P("The table lists every change from the submitted synopsis and the reason for it."),
  table(["Section", "Submitted synopsis", "Problem", "Revised"], corrections, [1500, 2300, 2900, 2326], { size: 18 }),
];

// citations in the appendix are not numbered; build refs after body so all keys are registered
const page = { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } };
const footer = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
  children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 })] })] });
const doc = new Document({
  creator: "Daksh Garg, Piyush Aggarwal, Abhay Chauhan, Naman Vasudev",
  title: "Minor Project Synopsis (Revised): Bus Fleet Allocation under Demand Variability",
  styles, numbering,
  sections: [{ properties: { page }, children: cover },
             { properties: { page: { ...page, pageNumbers: { start: 1 } } }, footers: { default: footer },
               children: [...body, ...refs(), ...appendix] }],
});
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT, "refs:", used.length); });
