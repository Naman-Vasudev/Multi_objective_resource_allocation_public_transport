// Final presentation. Every number comes from outputs/report_facts.json (generated from the pipeline CSVs).
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const REFS = require("./refs.js");

const PROJ = "C:\\Users\\armaa\\OneDrive\\Desktop\\Minors";
const FIG = path.join(PROJ, "outputs", "figures");
const MEDIA = path.join(__dirname, "assets");
const F = JSON.parse(fs.readFileSync(path.join(PROJ, "outputs", "report_facts.json"), "utf8"));
const SKILL = "C:\\Users\\armaa\\.claude\\skills\\synced\\02812373-138d-4a58-874b-33e46fa50871_11799b39-ad8d-4aad-816b-46a9cbf23218\\pptx";
const { applyTheme } = require(path.join(SKILL, "scripts", "apply_theme.js"));
const OUT = path.join(PROJ, "Final_Presentation_CTU_Fleet_Allocation.pptx");

const THEME = {
  name: "CTU Fleet Allocation", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "1B1B1B", lt1: "FFFFFF", dk2: "14304A", lt2: "EEF1F4", accent1: "F2B705", accent2: "B83A2E",
            accent3: "1F6F8B", accent4: "2A78D6", accent5: "EB6834", accent6: "1BAF7A", hlink: "1F6F8B", folHlink: "6250D6" },
};
const HEX = THEME.colors;
const cite = (...keys) => "[" + keys.map((k) => REFS.findIndex((r) => r[0] === k) + 1).join(", ") + "]";
const fmt = (x, d = 1) => (x > 0 ? "+" : x < 0 ? "\u2212" : "") + Math.abs(x).toFixed(d);
const pct = (x, d = 1) => fmt(x, d) + "%";
const n0 = (x) => Math.round(x).toLocaleString("en-IN");

function pngSize(p) {
  const b = fs.readFileSync(p);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
function fitImage(slide, p, x, y, w, h, extra = {}) {   // contain inside box, centred
  const s = pngSize(p); const r = Math.min(w / s.w, h / s.h);
  const iw = s.w * r, ih = s.h * r;
  slide.addImage({ path: p, x: x + (w - iw) / 2, y: y + (h - ih) / 2, w: iw, h: ih, ...extra });
}
// "Z_{1} = ..." -> text runs with sub/superscripts
function eq(str, base = {}) {
  const runs = []; let i = 0, buf = "";
  const push = (t, o) => { if (t) runs.push({ text: t, options: { ...base, ...o } }); };
  while (i < str.length) {
    if ((str[i] === "_" || str[i] === "^") && str[i + 1] === "{") {
      push(buf, {}); buf = "";
      const j = str.indexOf("}", i);
      push(str.slice(i + 2, j), str[i] === "_" ? { subscript: true } : { superscript: true });
      i = j + 1;
    } else { buf += str[i]; i++; }
  }
  push(buf, {});
  return runs;
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "Daksh Garg, Piyush Aggarwal, Abhay Chauhan, Naman Vasudev";
  pres.title = "Optimization-Based Resource Allocation for Public Bus Fleet Scheduling under Demand Variability";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;
  const FOOT = "Bus Fleet Allocation under Demand Variability  |  Dept. of Mathematics, PEC Chandigarh";

  pres.defineSlideMaster({
    title: "DARK", background: { color: HEX.dk2 },
    objects: [],
  });
  pres.defineSlideMaster({
    title: "CONTENT", background: { color: "FFFFFF" }, margin: [0.5, 0.5, 0.45, 0.5],
    objects: [
      { placeholder: { options: { name: "kicker", type: "body", x: 0.5, y: 0.28, w: 9.0, h: 0.28, fontSize: 11, bold: true,
          color: C.accent2, charSpacing: 2, margin: 0, valign: "middle" }, text: "" } },
      { placeholder: { options: { name: "title", type: "title", x: 0.5, y: 0.56, w: 9.0, h: 0.62, fontSize: 24, bold: true,
          color: C.text2, fontFace: "Cambria", margin: 0, valign: "middle", align: "left" }, text: "" } },
      { text: { text: FOOT, options: { x: 0.5, y: 5.27, w: 7.2, h: 0.24, fontSize: 9, color: "6B6B6B", margin: 0 } } },
    ],
    slideNumber: { x: 9.1, y: 5.27, w: 0.4, h: 0.24, fontSize: 9, color: "6B6B6B", align: "right" },
  });

  const content = (section, kicker, title) => {
    const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
    s.addText(kicker.toUpperCase(), { placeholder: "kicker" });
    s.addText(title, { placeholder: "title" });
    return s;
  };
  const card = (s, x, y, w, h, fill = C.background2, name = "card") =>
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill }, line: { color: fill, width: 0 },
      rectRadius: 0.08, objectName: name });
  const badge = (s, x, y, d, label, fill = C.accent1, color = C.text2) =>
    s.addText(String(label), { shape: pres.shapes.OVAL, x, y, w: d, h: d, fill: { color: fill }, color, bold: true,
      fontSize: 12, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: "badge " + label });
  const synth = (s) => s.addText("Synthetic demand, illustrative: not measured CTU outcomes", {
    x: 0.5, y: 4.98, w: 9.0, h: 0.24, fontSize: 10, italic: true, color: C.accent2, margin: 0, isTextBox: true });

  // ---------------------------------------------------------------- 1. Title
  pres.addSection({ title: "Title" });
  let s = pres.addSlide({ masterName: "DARK", sectionTitle: "Title" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.5, y: 0.42, w: 1.25, h: 0.83, fill: { color: "FFFFFF" },
    line: { color: "FFFFFF", width: 0 }, rectRadius: 0.06 });
  fitImage(s, path.join(MEDIA, "pec_logo.png"), 0.55, 0.47, 1.15, 0.73);
  s.addText("MINOR PROJECT  \u00b7  B.TECH MATHEMATICS AND COMPUTING", { x: 1.95, y: 0.5, w: 7.3, h: 0.3,
    fontSize: 11, bold: true, color: C.accent1, charSpacing: 3, margin: 0, isTextBox: true });
  s.addText("Punjab Engineering College (Deemed to be University), Chandigarh", { x: 1.95, y: 0.82, w: 7.3, h: 0.28,
    fontSize: 11, color: "C9D3DD", margin: 0, isTextBox: true });
  s.addText("Optimization-Based Resource Allocation for Public Bus Fleet Scheduling under Demand Variability", {
    x: 0.5, y: 1.5, w: 6.6, h: 1.55, fontFace: "Cambria", fontSize: 26, bold: true, color: "FFFFFF", margin: 0,
    valign: "middle", isTextBox: true });
  s.addText("Case study: Chandigarh Transport Undertaking (CTU)  \u00b7  Final presentation", { x: 0.5, y: 3.12,
    w: 7.2, h: 0.32, fontSize: 13, italic: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addShape(pres.shapes.OVAL, { x: 7.75, y: 1.55, w: 1.55, h: 1.55, fill: { color: C.accent3 }, line: { color: C.accent3, width: 0 } });
  fitImage(s, path.join(MEDIA, "bus_icon.png"), 8.1, 1.9, 0.85, 0.85);
  s.addText("UNDER THE GUIDANCE OF", { x: 0.5, y: 3.85, w: 3.2, h: 0.24, fontSize: 9, bold: true, color: "9FB1C2",
    charSpacing: 2, margin: 0, isTextBox: true });
  s.addText([{ text: "Dr. Sumati Mahajan", options: { bold: true, breakLine: true } },
             { text: "Department of Mathematics, PEC" }], { x: 0.5, y: 4.12, w: 3.3, h: 0.55, fontSize: 12,
    color: "FFFFFF", margin: 0, isTextBox: true });
  s.addText("SUBMITTED BY", { x: 4.0, y: 3.85, w: 3.0, h: 0.24, fontSize: 9, bold: true, color: "9FB1C2",
    charSpacing: 2, margin: 0, isTextBox: true });
  s.addText([{ text: "Daksh Garg (24112005)", options: { breakLine: true } }, { text: "Piyush Aggarwal (24112006)" }],
    { x: 4.0, y: 4.12, w: 2.7, h: 0.55, fontSize: 12, color: "FFFFFF", margin: 0, isTextBox: true });
  s.addText([{ text: "Abhay Chauhan (24112015)", options: { breakLine: true } }, { text: "Naman Vasudev (24112032)" }],
    { x: 6.75, y: 4.12, w: 2.75, h: 0.55, fontSize: 12, color: "FFFFFF", margin: 0, isTextBox: true });
  s.addNotes("Introduce the team and the project: allocating CTU's existing bus fleet across routes and time periods when demand is uncertain.");

  // ---------------------------------------------------------------- 2. Introduction
  pres.addSection({ title: "Introduction" });
  s = content("Introduction", "Introduction", "Bus supply rarely matches passenger demand");
  s.addText([
    { text: "Fixed-route buses are the most accessible public transport mode for Indian commuters.", options: { bullet: true, breakLine: true } },
    { text: "A transport undertaking must spread a finite fleet over many routes whose demand changes by place and time of day.", options: { bullet: true, breakLine: true } },
    { text: "When departures do not follow demand, the network fails in two directions at once.", options: { bullet: true } },
  ], { x: 0.5, y: 1.4, w: 4.4, h: 2.9, fontSize: 15, color: C.text1, paraSpaceAfter: 10, valign: "top", margin: 0, isTextBox: true });
  card(s, 5.25, 1.4, 4.25, 1.3); card(s, 5.25, 2.9, 4.25, 1.3);
  badge(s, 5.45, 1.6, 0.42, "!", C.accent2, "FFFFFF");
  s.addText([{ text: "High-demand corridors", options: { bold: true, fontSize: 15, color: C.text2, breakLine: true } },
             { text: "Overcrowding and long waits; passengers left behind by full buses", options: { fontSize: 13, color: "3A3A3A" } }],
    { x: 6.05, y: 1.45, w: 3.3, h: 1.2, valign: "middle", margin: 0, isTextBox: true });
  badge(s, 5.45, 3.1, 0.42, "\u2193", C.accent3, "FFFFFF");
  s.addText([{ text: "Low-demand corridors", options: { bold: true, fontSize: 15, color: C.text2, breakLine: true } },
             { text: "Spare capacity and near-empty runs that still cost fuel and driver hours", options: { fontSize: 13, color: "3A3A3A" } }],
    { x: 6.05, y: 2.95, w: 3.3, h: 1.2, valign: "middle", margin: 0, isTextBox: true });
  s.addNotes("Motivation: the same fleet is over-stretched on some corridors and under-used on others.");

  s = content("Introduction", "Introduction  \u00b7  Case study and problem", "CTU: a fixed fleet, 68 routes, no public ridership data");
  const stats = [[String(F.data.routes), "routes (Depots II, III, IV)"], [String(F.data.buses), "buses allocated"],
                 [n0(F.data.km) + " km", "total route length"], [String(F.data.stops), "named stops"]];
  stats.forEach(([v, l], k) => {
    const x = 0.5 + k * 2.3;
    card(s, x, 1.38, 2.1, 1.2);
    s.addText(v, { x: x + 0.1, y: 1.45, w: 1.9, h: 0.62, fontFace: "Cambria", fontSize: 30, bold: true, color: C.text2, align: "center", margin: 0, isTextBox: true });
    s.addText(l, { x: x + 0.1, y: 2.07, w: 1.9, h: 0.4, fontSize: 12, color: "4A4A4A", align: "center", margin: 0, isTextBox: true });
  });
  const cols = [["Given", ["A fixed fleet (389 buses)", "Routes with published headway ranges and lengths", "Three periods: AM 07-10, Midday 10-16, PM 16-19"]],
                ["Decide", ["A headway for every route and period", "The number of buses each route needs"]],
                ["So that", ["Waiting and overcrowding fall", "Vehicle-km stays within budget", "No route waits beyond the equity cap", "Fleet and cycle-time limits hold"]]];
  cols.forEach(([h, items], k) => {
    const x = 0.5 + k * 3.07;
    s.addText(h, { x, y: 2.85, w: 2.9, h: 0.3, fontSize: 14, bold: true, color: C.accent2, margin: 0, isTextBox: true });
    s.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } })),
      { x, y: 3.17, w: 2.9, h: 1.75, fontSize: 12.5, color: C.text1, paraSpaceAfter: 4, valign: "top", margin: 0, isTextBox: true });
  });
  s.addNotes("Data source: the CTU timetable as on 25.07.2026. Ridership is not public, so demand in this study is synthetic.");

  // ---------------------------------------------------------------- 3-5. Literature review
  pres.addSection({ title: "Literature review" });
  const litSlide = (kicker, title, items, extra) => {
    const sl = content("Literature review", kicker, title);
    items.forEach(([head, contrib, use], k) => {
      const x = 0.5 + (k % 2) * 4.6, y = 1.36 + Math.floor(k / 2) * 1.82;
      card(sl, x, y, 4.4, 1.66);
      sl.addText(head, { x: x + 0.18, y: y + 0.1, w: 4.05, h: 0.34, fontSize: 13, bold: true, color: C.text2, margin: 0, isTextBox: true });
      sl.addText([{ text: contrib, options: { breakLine: true } },
                  { text: "Use here: ", options: { bold: true, color: C.accent2 } }, { text: use }],
        { x: x + 0.18, y: y + 0.46, w: 4.05, h: 1.12, fontSize: 11.5, color: "333333", valign: "top", margin: 0, paraSpaceAfter: 3, isTextBox: true });
    });
    if (extra) extra(sl);
    return sl;
  };
  s = litSlide("Literature review  \u00b7  Transit planning", "Frequency setting is a fleet-constrained planning step", [
    ["Ceder (2016) " + cite("ceder16"), "Planning chain from network design to frequencies, timetables and crews.", "frames our stage: frequencies and buses for fixed routes."],
    ["Furth & Wilson (1981) " + cite("fw81"), "Allocates buses across routes and periods under fleet and loading limits.", "the same structure as our fleet and capacity constraints."],
    ["Mart\u00ednez et al. (2014) " + cite("martinez14"), "MILP for frequency setting with a discrete set of frequencies.", "justifies our headway menu with binary choices."],
    ["Verbas & Mahmassani (2015) " + cite("verbas15"), "Frequency allocation over routes and time periods with explicit trade-offs.", "supports period-wise allocation and trade-off analysis."],
  ]);
  s.addNotes("Reviews of the field: Ibarra-Rojas et al. (2015) and Ceder & Wilson (1986) place frequency setting between network design and timetabling.");
  s = litSlide("Literature review  \u00b7  Methods", "Multi-objective and uncertainty methods we build on", [
    ["Deb et al. (2002): NSGA-II " + cite("deb02"), "Elitist GA with non-dominated sorting and crowding distance.", "heuristic Pareto front, benchmarked against an exact one."],
    ["Mavrotas (2009, 2013): AUGMECON " + cite("mavrotas09", "mavrotas13"), "Augmented \u03b5-constraint: only strictly efficient points; exact for integer programs.", "our exact Pareto front."],
    ["Zimmermann; Inuiguchi & Ram\u00edk " + cite("zimm78", "ir00"), "Fuzzy multi-objective LP (1978); possibilistic programming via \u03b1-level cuts (2000).", "triangular fuzzy demand with an \u03b1-cut capacity rule."],
    ["Charnes & Cooper; Jones & Tamiz " + cite("cc61", "jt10"), "Goal programming (1961): targets, deviations; preemptive vs weighted forms (2010).", "priority scenarios for passengers, operator and equity."],
  ]);
  s.addNotes("Stochastic alternatives exist (An & Lo 2016; Gkiotsalitis et al. 2022). We use fuzzy numbers because no data exist to fit probability distributions.");
  s = content("Literature review", "Literature review  \u00b7  Standards and gap", "Standards, Indian evidence and the gap");
  card(s, 0.5, 1.36, 4.5, 1.66); card(s, 0.5, 3.18, 4.5, 1.66);
  s.addText([{ text: "Reliability standard: Excess Wait Time", options: { bold: true, color: C.text2, fontSize: 13, breakLine: true } },
             { text: "TfL plans bus services against published guidelines " + cite("tfl12") + "; Singapore's reliability framework rewards operators on Excess Wait Time " + cite("leong16") + ". We report EWT = (h/2)\u00b7CV\u00b2.", options: { fontSize: 11.5 } }],
    { x: 0.68, y: 1.46, w: 4.15, h: 1.5, color: "333333", valign: "top", margin: 0, isTextBox: true });
  s.addText([{ text: "Indian bus speeds", options: { bold: true, color: C.text2, fontSize: 13, breakLine: true } },
             { text: "GPS studies: Chennai buses average 17.8 km/h (peak) and 21.5 km/h (off-peak) " + cite("mahesh17") + "; speeds vary strongly across Ahmedabad " + cite("jain22") + ". This sets our 18-26 km/h test range.", options: { fontSize: 11.5 } }],
    { x: 0.68, y: 3.28, w: 4.15, h: 1.5, color: "333333", valign: "top", margin: 0, isTextBox: true });
  card(s, 5.2, 1.36, 4.3, 3.48, C.text2);
  s.addText("Research gap", { x: 5.4, y: 1.48, w: 3.9, h: 0.36, fontFace: "Cambria", fontSize: 17, bold: true, color: C.accent1, margin: 0, isTextBox: true });
  s.addText([
    { text: "Our verified search (2014-2026) found no study applying goal programming to bus frequency or fleet allocation.", options: { bullet: true, breakLine: true } },
    { text: "CTU publishes no ridership, so the method must work with fuzzy, synthetic demand and be ready for real data.", options: { bullet: true, breakLine: true } },
    { text: "The synopsis model had four mathematical errors that had to be corrected first.", options: { bullet: true } },
  ], { x: 5.4, y: 1.9, w: 3.9, h: 2.8, fontSize: 12.5, color: "FFFFFF", paraSpaceAfter: 8, valign: "top", margin: 0, isTextBox: true });
  s.addNotes("The gap statement is limited to what our search found; we do not claim no such study exists.");

  // ---------------------------------------------------------------- 6. Objectives
  pres.addSection({ title: "Objectives" });
  s = content("Objectives", "Objectives", "Project objectives");
  const objs = [
    "Build a validated CTU baseline from the published timetable: routes, headways, buses, stops.",
    "Formulate a corrected, linear multi-objective MILP for headways and bus allocation.",
    "Represent uncertain demand with triangular fuzzy numbers and an \u03b1-cut capacity rule.",
    "Balance waiting, operating effort, crowding and equity with goal programming; cross-check on an exact Pareto front and NSGA-II.",
    "Stress-test every schedule by Monte Carlo simulation and sensitivity analysis.",
  ];
  objs.forEach((t, k) => {
    const y = 1.36 + k * 0.6;
    badge(s, 0.5, y + 0.04, 0.4, k + 1);
    s.addText(t, { x: 1.08, y, w: 5.3, h: 0.5, fontSize: 13, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
  });
  card(s, 6.75, 1.36, 2.75, 1.75, C.text2);
  s.addText([{ text: "Aim", options: { bold: true, color: C.accent1, fontSize: 15, breakLine: true } },
             { text: "Less waiting and crowding using the existing fleet, without additional buses.", options: { color: "FFFFFF", fontSize: 14 } }],
    { x: 6.95, y: 1.5, w: 2.4, h: 1.5, valign: "top", margin: 0, isTextBox: true, fontFace: "Cambria" });

  // ---------------------------------------------------------------- 7-9. Methodology
  pres.addSection({ title: "Methodology" });
  s = content("Methodology", "Methodology  \u00b7  Pipeline", "Seven-stage pipeline, fully reproducible");
  const steps = [["Data audit", "Timetable \u2192 validated route table"], ["Calibration", "Cycle time \u03c4 vs fleet"],
                 ["Demand", "Synthetic, fuzzy (L, M, U)"], ["MILP", "Headway menu, Z1-Z3"], ["Goal programming", "Priority scenarios"],
                 ["Pareto", "AUGMECON vs NSGA-II"], ["Simulation", "2000 days, sensitivity"]];
  steps.forEach(([h, b], k) => {
    const row = k < 4 ? 0 : 1, col = k < 4 ? k : k - 4;
    const x = row === 0 ? 0.5 + col * 2.3 : 1.65 + col * 2.3, y = 1.4 + row * 1.55;
    card(s, x, y, 2.1, 1.3);
    badge(s, x + 0.14, y + 0.14, 0.38, k + 1);
    s.addText(h, { x: x + 0.6, y: y + 0.12, w: 1.42, h: 0.42, fontSize: 13, bold: true, color: C.text2, valign: "middle", margin: 0, isTextBox: true });
    s.addText(b, { x: x + 0.16, y: y + 0.62, w: 1.82, h: 0.6, fontSize: 11.5, color: "3A3A3A", valign: "top", margin: 0, isTextBox: true });
  });
  s.addText("One command (python run_all.py) regenerates every table and figure; 100 automated tests check data, model, solvers and simulation.",
    { x: 0.5, y: 4.55, w: 9.0, h: 0.4, fontSize: 12, italic: true, color: C.accent3, margin: 0, isTextBox: true });

  s = content("Methodology", "Methodology  \u00b7  Corrected model", "A linear multi-objective MILP over a headway menu");
  card(s, 0.5, 1.33, 4.45, 2.72);
  s.addText("Objectives (minimise)", { x: 0.68, y: 1.4, w: 4.1, h: 0.3, fontSize: 13, bold: true, color: C.accent2, margin: 0, isTextBox: true });
  const objEq = [["Z_{1} = \u03a3 M_{rt} \u03a3_{k} (h_{k}/2) y_{rtk}", "waiting (pax\u00b7min/h), linear in binaries y"],
                 ["Z_{2} = \u03a3 d_{r}^{cyc} H_{rt} f_{rt}", "vehicle-km per day"],
                 ["Z_{3} = \u03a3 o_{rt} H_{rt}", "passengers above capacity per day"]];
  objEq.forEach(([e, d], k) => {
    s.addText(eq(e), { x: 0.68, y: 1.78 + k * 0.72, w: 4.1, h: 0.34, fontFace: "Cambria", fontSize: 15, bold: true, color: C.text2, margin: 0, isTextBox: true });
    s.addText(d, { x: 0.68, y: 2.1 + k * 0.72, w: 4.1, h: 0.28, fontSize: 11, color: "4A4A4A", margin: 0, isTextBox: true });
  });
  s.addText("Constraints", { x: 5.2, y: 1.4, w: 4.3, h: 0.3, fontSize: 13, bold: true, color: C.accent2, margin: 0, isTextBox: true });
  const cons = [["\u03a3_{r} x_{rt} \u2264 B_{eff} = " + F.model.B_eff, "fleet in every period"],
                ["\u03c4_{r} f_{rt} \u2264 x_{rt},  x integer", "buses needed to run a frequency"],
                ["o_{rt} \u2265 D_{rt}^{\u03b1} \u2212 C f_{rt},  o \u2265 0", "overflow above capacity C = " + F.model.C],
                ["f_{r}^{min} \u2264 f_{rt} \u2264 f_{r}^{max}", "published bounds, via the menu"],
                ["|x_{rt} \u2212 x_{r}^{0}| \u2264 dev_{r}; headway cap", "practicality, equity"]];
  cons.forEach(([e, d], k) => {
    badge(s, 5.2, 1.8 + k * 0.45, 0.3, k + 1);
    s.addText([...eq(e, { bold: true, color: C.text2, fontFace: "Cambria", fontSize: 12.5 }),
               { text: "   " + d, options: { fontSize: 10.5, color: "555555" } }],
      { x: 5.6, y: 1.77 + k * 0.45, w: 3.9, h: 0.36, valign: "middle", margin: 0, isTextBox: true });
  });
  card(s, 0.5, 4.17, 9.0, 0.72, "FCEFC7");
  s.addText([{ text: "Corrected from the synopsis:  ", options: { bold: true, color: C.accent2 } },
             { text: "(1) \u03a3D\u00b730/f is nonlinear \u2192 headway menu;  (2) Z2 = vehicle-km, not d\u00b7x;  (3) capacity is C\u00b7f, not C\u00b7x;  (4) upper \u03b1-cut U \u2212 \u03b1(U \u2212 M), not the lower cut." }],
    { x: 0.68, y: 4.22, w: 8.7, h: 0.62, fontSize: 11.5, color: C.text1, valign: "middle", margin: 0, isTextBox: true });
  s.addNotes("Sizes: " + F.model.pairs + " active route-periods, " + F.model.n_vars + " variables, " + F.model.n_cons + " constraints. Menu " + F.model.menu.join(", ") + " min plus each route's published headways.");

  s = content("Methodology", "Methodology  \u00b7  Uncertainty and solution", "Fuzzy demand, priorities, Pareto check and simulation");
  const quad = [
    ["Fuzzy demand", "Triangular (L, M, U) with L = " + (1 - F.demand.lo).toFixed(2) + "M, U = " + (1 + F.demand.hi).toFixed(2) + "M. Capacity planned for the upper \u03b1-cut D\u03b1 = U \u2212 \u03b1(U \u2212 M); \u03b1 = 1 gives M, \u03b1 = 0 gives U."],
    ["Goal programming", "G1 waiting \u2212" + (100 * F.gp.kappa1).toFixed(0) + "%, G2 overflow 0, G3 vehicle-km \u2212" + (100 * F.gp.kappa3).toFixed(0) + "%, G4 headway caps 60/90 min. Preemptive (3 priority orders), weighted and Chebyshev forms."],
    ["Pareto cross-check", "Exact AUGMECON on a " + F.pareto.grid + "\u00d7" + F.pareto.grid + " grid vs NSGA-II (population 200, 300 generations, 5 seeds); hypervolume, GD, IGD, coverage."],
    ["Simulation", n0(F.sim.N) + " demand days: triangular \u00d7 a common day shock; gamma headways (CV " + F.sim.cv + "), E[W] = (h/2)(1 + CV\u00b2). Same draws for every schedule."],
  ];
  quad.forEach(([h, b], k) => {
    const x = 0.5 + (k % 2) * 4.6, y = 1.33 + Math.floor(k / 2) * 1.48;
    card(s, x, y, 4.4, 1.36);
    s.addText(h, { x: x + 0.18, y: y + 0.08, w: 4.05, h: 0.32, fontSize: 13, bold: true, color: C.text2, margin: 0, isTextBox: true });
    s.addText(b, { x: x + 0.18, y: y + 0.42, w: 4.05, h: 0.9, fontSize: 11.5, color: "333333", valign: "top", margin: 0, isTextBox: true });
  });
  s.addText("Demand is synthetic: route length \u00d7 (hub, PGI, ISBT, outskirts flags) \u00d7 noise, scaled to " + n0(F.demand.daily_boardings) + " boardings/day from a CTU-wide anchor that is not yet verified.",
    { x: 0.5, y: 4.33, w: 9.0, h: 0.5, fontSize: 11.5, italic: true, color: C.accent2, margin: 0, isTextBox: true });

  // ---------------------------------------------------------------- 10-14. Results
  pres.addSection({ title: "Results" });
  s = content("Results", "Results  \u00b7  Data and calibration", "Only the one-way reading of route length fits the fleet");
  const cl = [["S1: full cycle", F.calib.S1_22_0.N], ["S2: one-way", F.calib.S2_22_0.N], ["S2 + 10% layover", F.calib.S2_22_10.N],
              ["S3: + 10% spares", F.calib.S3_22_10.N]];
  s.addChart(pres.charts.BAR, [{ name: "Buses needed", labels: cl.map((c) => c[0]), values: cl.map((c) => c[1]) }], {
    x: 0.5, y: 1.3, w: 5.2, h: 3.55, barDir: "col", chartColors: [HEX.accent3], showValue: true, dataLabelPosition: "outEnd",
    dataLabelFontSize: 11, dataLabelColor: "333333", dataLabelFormatCode: "0", showLegend: false,
    showTitle: true, title: "Buses needed at 22 km/h vs " + F.data.buses + " allocated", titleFontSize: 12, titleColor: "333333",
    titleFontFace: "+mn-lt", catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
    catAxisLabelFontSize: 10, valAxisLabelFontSize: 10, catAxisLabelColor: "555555", valAxisLabelColor: "555555",
    valAxisMinVal: 0, valAxisMaxVal: 400, valGridLine: { color: "E3E3E3", size: 0.5 }, catGridLine: { style: "none" },
  });
  const calibNotes = [
    ["Data audit", F.data.pdf_ok + "/" + F.data.routes + " routes match the PDF; totals " + F.data.buses + " buses, " + n0(F.data.km) + " km; " + F.data.mv_mismatch + " rounded cells corrected."],
    ["Full-cycle reading fails", "Only " + F.calib.S1_22_0.U + "% of the fleet would be used, and " + F.calib.S1_22_0.over + " of 68 routes would hold more buses than their maximum frequency needs."],
    ["Chosen setting", "One-way length, 22 km/h, 10% layover: " + F.calib.S3_22_10.U + "% fleet use with spares. CTU must confirm the length convention."],
  ];
  calibNotes.forEach(([h, b], k) => {
    const y = 1.33 + k * 1.2;
    card(s, 5.95, y, 3.55, 1.08);
    s.addText([{ text: h, options: { bold: true, color: C.text2, fontSize: 12.5, breakLine: true } }, { text: b, options: { fontSize: 11 } }],
      { x: 6.1, y: y + 0.06, w: 3.28, h: 0.98, color: "333333", valign: "top", margin: 0, isTextBox: true });
  });
  s.addNotes("Implied speed that exactly fills the fleet: " + F.calib.v_implied_noSpare + " km/h without spares, " + F.calib.v_implied_spare + " km/h with 10% spares.");

  s = content("Results", "Results  \u00b7  Goal programming", "Priorities matter once frequency limits are relaxed");
  const order = { "P-PASSENGER": "overflow > wait > equity > km", "P-OPERATOR": "km > overflow > wait > equity",
                  "P-EQUITY": "equity > overflow > wait > km", "P-BALANCED": "equal normalised weights", "CHEBYSHEV": "min-max deviation" };
  const hdr = ["Scenario", "Priority", "Waiting", "Vehicle-km", "Overflow", "Above cap (min)", "Goals met"]
    .map((t) => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 }, fontSize: 11 } }));
  const rows = [hdr, ...F.gp.rows.map((r) => [r.name, order[r.name], pct(r.dZ1), pct(r.dZ2), pct(r.dZ3), String(r.eq), r.met + " of 4"]
    .map((t, i) => ({ text: t, options: { fontSize: 11, bold: r.name === "P-BALANCED", color: "222222",
      fill: { color: r.name === "P-BALANCED" ? "FCEFC7" : "FFFFFF" }, align: i >= 2 ? "center" : "left" } })))];
  s.addTable(rows, { x: 0.5, y: 1.35, w: 9.0, colW: [1.3, 2.4, 0.95, 1.05, 0.95, 1.25, 1.1], border: { type: "solid", color: "D9D9D9", pt: 0.75 },
    rowH: 0.36, margin: 0.05, valign: "middle" });
  s.addText("Changes vs the published schedule; f_max relaxed by two menu levels, \u03b1 = 0.5. With published f_max all five scenarios give the same schedule (waiting " + pct(F.gp.published.dZ1) + ", overflow " + pct(F.gp.published.dZ3) + "): nothing to prioritise. G2 (zero overflow) is unattainable by design; targets were set inside the attainable range after the ideal values were known.",
    { x: 0.5, y: 3.75, w: 9.0, h: 1.05, fontSize: 11.5, color: "333333", valign: "top", margin: 0, isTextBox: true });
  synth(s);

  s = content("Results", "Results  \u00b7  Pareto cross-check", "Exact front confirmed; NSGA-II never beats it");
  fitImage(s, path.join(FIG, "pareto_2d.png"), 0.5, 1.25, 9.0, 2.6);
  const pst = [[String(F.pareto.exact_points), "exact efficient points (AUGMECON " + F.pareto.grid + "\u00d7" + F.pareto.grid + ")"],
               [F.pareto.hv_exact.toFixed(3) + " vs " + F.pareto.hv_union.toFixed(3), "hypervolume: exact vs NSGA-II union"],
               [String(F.pareto.dominated), "exact points strictly dominated by NSGA-II"],
               [F.pareto.t_exact + " s vs " + F.pareto.t_seed + " s", "exact grid vs one NSGA-II seed"]];
  pst.forEach(([v, l], k) => {
    const x = 0.5 + k * 2.3;
    card(s, x, 3.95, 2.1, 0.98);
    s.addText(v, { x: x + 0.08, y: 3.99, w: 1.94, h: 0.44, fontFace: "Cambria", fontSize: 19, bold: true, color: C.text2, align: "center", margin: 0, isTextBox: true });
    s.addText(l, { x: x + 0.08, y: 4.43, w: 1.94, h: 0.45, fontSize: 10, color: "4A4A4A", align: "center", margin: 0, isTextBox: true });
  });
  synth(s);
  s.addNotes("NSGA-II's higher hypervolume comes from its denser point set filling gaps between grid samples; it strictly dominates no exact point. Mean GD " + F.pareto.gd + ", IGD " + F.pareto.igd + ". P-PASSENGER lies exactly on the front; P-BALANCED is " + F.pareto.gp_dist["P-BALANCED"] + " away because it trades a little overflow for full equity.");

  s = content("Results", "Results  \u00b7  Simulation", "Headline: less waiting and crowding, fewer buses");
  const H = F.sim.headline, pol = F.sim.rows[H.policy], base = F.sim.rows["Baseline"];
  const hs = [[pct(H.vs_mid.wait), "expected wait (" + pol.wait.toFixed(2) + " vs " + base.wait.toFixed(2) + " min)"],
              [pct(H.vs_mid.over), "overflow passengers per day"],
              [pct(H.vs_mid.vkm), "vehicle-km per day"],
              [pol.fleet + " vs " + base.fleet, "buses in use"]];
  hs.forEach(([v, l], k) => {
    const x = 0.5 + (k % 2) * 2.25, y = 1.33 + Math.floor(k / 2) * 1.3;
    card(s, x, y, 2.1, 1.18);
    s.addText(v, { x: x + 0.08, y: y + 0.08, w: 1.94, h: 0.56, fontFace: "Cambria", fontSize: 24, bold: true, color: C.text2, align: "center", margin: 0, isTextBox: true });
    s.addText(l, { x: x + 0.08, y: y + 0.66, w: 1.94, h: 0.46, fontSize: 10.5, color: "4A4A4A", align: "center", margin: 0, isTextBox: true });
  });
  s.addText("P-BALANCED (\u03b1 = 0.5) vs the published schedule. Against a fairer peak-frequency baseline: wait " + pct(H.vs_peak.wait) + ", overflow " + pct(H.vs_peak.over) + ", vehicle-km " + pct(H.vs_peak.vkm) + ".",
    { x: 0.5, y: 3.98, w: 4.35, h: 0.9, fontSize: 11, color: "333333", valign: "top", margin: 0, isTextBox: true });
  const ps = [["Baseline", "Published (mid)"], ["Baseline (peak f_max)", "Published (peak)"], ["P-PASSENGER (α=0.5)", "P-PASSENGER"],
              ["P-OPERATOR (α=0.5)", "P-OPERATOR"], ["P-EQUITY (α=0.5)", "P-EQUITY"], ["P-BALANCED (α=0.5)", "P-BALANCED"], ["KNEE (Pareto front)", "Knee point"]];
  s.addChart(pres.charts.BAR, [{ name: "P(overflow > 5%)", labels: ps.map((p) => p[1]), values: ps.map((p) => F.sim.rows[p[0]].p5) }], {
    x: 5.0, y: 1.25, w: 4.5, h: 3.65, barDir: "bar", chartColors: [HEX.accent3], showValue: true, dataLabelPosition: "outEnd",
    dataLabelFormatCode: "0.0\"%\"", dataLabelFontSize: 10, dataLabelColor: "333333", showLegend: false,
    showTitle: true, title: "Days with overflow above 5% of demand (%)", titleFontSize: 12, titleColor: "333333",
    titleFontFace: "+mn-lt", catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
    catAxisLabelFontSize: 10, valAxisLabelFontSize: 10, catAxisLabelColor: "555555", valAxisLabelColor: "555555",
    valAxisMinVal: 0, valAxisMaxVal: 80, valGridLine: { color: "E3E3E3", size: 0.5 }, catGridLine: { style: "none" }, catAxisOrientation: "maxMin",
  });
  synth(s);
  s.addNotes(n0(F.sim.N) + " simulated demand days, identical for every schedule. Waiting differences between optimised schedules are a few seconds and should not be used to rank them.");

  s = content("Results", "Results  \u00b7  Sensitivity and robustness", "Where the result holds, and where it breaks");
  fitImage(s, path.join(FIG, "sensitivity_tornado.png"), 0.4, 1.25, 5.3, 3.6);
  const lab = { "speed v": (v) => v + " km/h", "spare ratio s": (v) => "spares " + Math.round(100 * v) + "%", "layover": (v) => "layover " + Math.round(100 * v) + "%" };
  const inf = F.sens.filter((r) => !r.feasible).map((r) => (lab[r.factor] || ((v) => r.factor + " " + v))(r.value))
    .concat(F.fleet.filter((r) => !r.feasible).map((r) => "fleet cut " + Math.round(100 * r.cut) + "%"));
  const oosP = F.oos["P-BALANCED (α=0.5)"], oosB = F.oos["Baseline"], rob = F.oos["P-BALANCED ROBUST (α=0, spreads ×1.5)"];
  const a1 = F.alpha.find((r) => r.alpha === 1), a0 = F.alpha.find((r) => r.alpha === 0);
  const sens = [
    ["Infeasible settings", inf.join("; ") + ": the published minimum frequencies need more buses than are available."],
    ["Uncertainty wider than planned", "Overflow risk rises " + oosP.ins + "% \u2192 " + oosP.out + "% (baseline " + oosB.ins + "% \u2192 " + oosB.out + "%)."],
    ["Robust variant rejected", "Planning for 1.5\u00d7 wider demand gave " + rob.ins + "% / " + rob.out + "%: worse, not safer, with a fixed fleet."],
    ["\u03b1 barely matters", "Overflow risk " + a1.p5 + "% (\u03b1 = 1) vs " + a0.p5 + "% (\u03b1 = 0): the headway menu is coarse."],
  ];
  sens.forEach(([h, b], k) => {
    const y = 1.3 + k * 0.9;
    card(s, 5.85, y, 3.65, 0.8);
    s.addText([{ text: h, options: { bold: true, color: C.text2, fontSize: 11.5, breakLine: true } }, { text: b, options: { fontSize: 10.5 } }],
      { x: 5.98, y: y + 0.04, w: 3.42, h: 0.74, color: "333333", valign: "middle", margin: 0, isTextBox: true });
  });
  synth(s);

  // ---------------------------------------------------------------- 15-16. Planned work
  pres.addSection({ title: "Planned work" });
  s = content("Planned work", "Planned work", "What remains before the results can speak for CTU");
  const todo = [["Real ridership", "Request ETM ticket data from CTU; boarding counts at 5-10 hubs; L/M/U from 10th/50th/90th percentiles."],
                ["Fairer comparisons", "Simple benchmark (proportional / square-root rule); route-specific running times; GP target sweep."],
                ["Better waiting model", "Arrival-timing model for long headways; within-period peak-hour factor."],
                ["CTU validation", "Confirm the route-length convention, what the 389 buses include, and the 22 km/h speed."],
                ["Operations", "Depot and interlining constraints; driver-duty feasibility; stop capacity at shorter headways."],
                ["Write-up", "Final report, viva preparation, conference paper."]];
  todo.forEach(([h, b], k) => {
    const x = 0.5 + (k % 3) * 3.05, y = 1.33 + Math.floor(k / 3) * 1.78;
    card(s, x, y, 2.85, 1.62);
    badge(s, x + 0.14, y + 0.14, 0.36, k + 1);
    s.addText(h, { x: x + 0.58, y: y + 0.12, w: 2.15, h: 0.42, fontSize: 13, bold: true, color: C.text2, valign: "middle", margin: 0, isTextBox: true });
    s.addText(b, { x: x + 0.16, y: y + 0.62, w: 2.55, h: 0.95, fontSize: 11, color: "333333", valign: "top", margin: 0, isTextBox: true });
  });

  s = content("Planned work", "Planned work  \u00b7  Timeline and team", "Timeline, responsibilities and target venues");
  const tl = [["Month 1", "Ridership request, hub counts"], ["Month 2", "Benchmark, route speeds, waiting model"],
              ["Month 3", "Re-run with real demand; validation"], ["Month 4", "Report, paper submission"]];
  tl.forEach(([m, t], k) => {
    const x = 0.5 + k * 2.3;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.32, w: 2.1, h: 0.95, fill: { color: k === 0 ? HEX.accent1 : HEX.lt2 },
      line: { color: k === 0 ? HEX.accent1 : HEX.lt2, width: 0 }, rectRadius: 0.08 });
    s.addText([{ text: m, options: { bold: true, fontSize: 12.5, color: HEX.dk2, breakLine: true } }, { text: t, options: { fontSize: 11, color: "333333" } }],
      { x: x + 0.12, y: 1.36, w: 1.86, h: 0.87, valign: "middle", margin: 0, isTextBox: true });
  });
  const team = [["DG", "Daksh Garg", "Data, timetable and calibration"], ["PA", "Piyush Aggarwal", "Demand modelling and ridership data"],
                ["AC", "Abhay Chauhan", "Optimization models and solvers"], ["NV", "Naman Vasudev", "Simulation, validation and report"]];
  team.forEach(([ini, nm, role], k) => {
    const y = 2.55 + k * 0.58;
    badge(s, 0.5, y, 0.44, ini, HEX.dk2, "FFFFFF");
    s.addText([{ text: nm + "  ", options: { bold: true, color: HEX.dk2 } }, { text: role, options: { color: "333333" } }],
      { x: 1.08, y, w: 4.0, h: 0.44, fontSize: 12, valign: "middle", margin: 0, isTextBox: true });
  });
  card(s, 5.4, 2.5, 4.1, 2.38);
  s.addText([{ text: "Conferences targeted", options: { bold: true, color: HEX.accent2, fontSize: 13, breakLine: true } },
             { text: "Conference of Transportation Research Group of India (CTRG): biennial; 8th edition held at IIT Guwahati, Dec 2025.", options: { bullet: true, breakLine: true } },
             { text: "ORSI Annual Convention (Operational Research Society of India): usually held in December.", options: { bullet: true, breakLine: true } },
             { text: "Dates for the next calls must be confirmed on the official sites.", options: { italic: true } }],
    { x: 5.58, y: 2.6, w: 3.8, h: 2.2, fontSize: 11, color: "333333", paraSpaceAfter: 5, valign: "top", margin: 0, isTextBox: true });

  // ---------------------------------------------------------------- 17-19. References
  pres.addSection({ title: "References" });
  const per = 9;
  for (let p = 0; p * per < REFS.length; p++) {
    s = content("References", "References" + (p ? "  \u00b7  continued" : ""), p ? "References (continued)" : "References");
    const chunk = REFS.slice(p * per, (p + 1) * per);
    s.addText(chunk.map((r, i) => ({ text: "[" + (p * per + i + 1) + "]  " + r[1], options: { breakLine: i < chunk.length - 1 } })),
      { x: 0.5, y: 1.3, w: 9.0, h: 3.85, fontSize: 10, color: "222222", paraSpaceAfter: 4, valign: "top", margin: 0, isTextBox: true });
  }

  // ---------------------------------------------------------------- 20. Thank you
  pres.addSection({ title: "Close" });
  s = pres.addSlide({ masterName: "DARK", sectionTitle: "Close" });
  s.addText("Thank you", { x: 0.5, y: 1.55, w: 9, h: 0.9, fontFace: "Cambria", fontSize: 40, bold: true, color: "FFFFFF", align: "center", margin: 0, isTextBox: true });
  s.addText("Questions and discussion", { x: 0.5, y: 2.45, w: 9, h: 0.45, fontSize: 18, italic: true, color: C.accent1, align: "center", margin: 0, isTextBox: true });
  s.addText("Daksh Garg  \u00b7  Piyush Aggarwal  \u00b7  Abhay Chauhan  \u00b7  Naman Vasudev", { x: 0.5, y: 3.4, w: 9, h: 0.35,
    fontSize: 13, color: "FFFFFF", align: "center", margin: 0, isTextBox: true });
  s.addText("Guide: Dr. Sumati Mahajan, Department of Mathematics, PEC Chandigarh", { x: 0.5, y: 3.8, w: 9, h: 0.35,
    fontSize: 12, color: "C9D3DD", align: "center", margin: 0, isTextBox: true });

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
})();
