// Shared helpers for the progress report and the revised synopsis (docx 9.x).
const fs = require("fs");
const path = require("path");
const D = require("docx");
const { Paragraph, TextRun, HeadingLevel, AlignmentType, ImageRun, Table, TableRow, TableCell, WidthType,
        ShadingType, BorderStyle, SequentialIdentifier, PageBreak, LevelFormat } = D;

const PROJ = "C:\\Users\\armaa\\OneDrive\\Desktop\\Minors";
const FIG = path.join(PROJ, "outputs", "figures");
const MEDIA = path.join(__dirname, "assets");
const F = JSON.parse(fs.readFileSync(path.join(PROJ, "outputs", "report_facts.json"), "utf8"));
const REFS = require("./refs.js");
const NAVY = "14304A";
const FONT = "Times New Roman";
const CONTENT_W = 9026;   // A4 (11906) minus 2 x 1440 margins, DXA

const cite = (...keys) => "[" + keys.map((k) => REFS.findIndex((r) => r[0] === k) + 1).join(", ") + "]";
const sgn = (x, d = 1) => (x > 0 ? "+" : x < 0 ? "\u2212" : "") + Math.abs(x).toFixed(d);
const pct = (x, d = 1) => sgn(x, d) + "%";
const n0 = (x) => Math.round(x).toLocaleString("en-IN");

// "Z_{1} = x^{2}" -> runs with sub/superscripts; **bold** segments supported in plain text
function runs(str, base = {}) {
  const out = []; let i = 0, buf = "";
  const push = (t, o) => { if (t) out.push(new TextRun({ text: t, font: FONT, ...base, ...o })); };
  while (i < str.length) {
    if ((str[i] === "_" || str[i] === "^") && str[i + 1] === "{") {
      push(buf, {}); buf = "";
      const j = str.indexOf("}", i);
      push(str.slice(i + 2, j), str[i] === "_" ? { subScript: true } : { superScript: true });
      i = j + 1;
    } else if (str.startsWith("**", i)) {
      push(buf, {}); buf = "";
      const j = str.indexOf("**", i + 2);
      push(str.slice(i + 2, j), { bold: true });
      i = j + 2;
    } else { buf += str[i]; i++; }
  }
  push(buf, {});
  return out;
}
const P = (text, opts = {}) => new Paragraph({ children: runs(text, opts.run || {}), alignment: opts.align || AlignmentType.JUSTIFIED,
  spacing: { after: opts.after ?? 120, line: opts.line ?? 360 }, indent: opts.indent, keepNext: opts.keepNext });
// Equation on its own line: centred at mid-page, number right-aligned at the margin
const EQ = (text, num) => new Paragraph({ spacing: { before: 60, after: 100 }, keepLines: true,
  tabStops: [{ type: D.TabStopType.CENTER, position: Math.round(CONTENT_W / 2) }, { type: D.TabStopType.RIGHT, position: CONTENT_W }],
  children: [new TextRun({ text: "\t", font: FONT }), ...runs(text),
             ...(num ? [new TextRun({ text: "\t(" + num + ")", font: FONT })] : [])] });
const H1 = (text, pageBreak = true) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: pageBreak,
  keepNext: true, children: [new TextRun({ text, font: FONT })], spacing: { after: 240 } });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text, font: FONT })],
  spacing: { before: 240, after: 120 }, keepNext: true });
const H3 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text, font: FONT })],
  spacing: { before: 180, after: 80 }, keepNext: true });
const BUL = (text, level = 0) => new Paragraph({ numbering: { reference: "bullets", level }, children: runs(text),
  spacing: { after: 60, line: 340 }, alignment: AlignmentType.LEFT });
const NUM = (text, ref = "numbers") => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(text),
  spacing: { after: 60, line: 340 }, alignment: AlignmentType.LEFT });
const BREAK = () => new Paragraph({ children: [new PageBreak()] });

function caption(kind, text) {   // "Figure n: text" with a SEQ field so Word builds the List of Figures/Tables
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 60, after: 200 },
    keepNext: kind === "Table",
    children: [new TextRun({ text: kind + " ", bold: true, font: FONT, size: 20 }),
               new TextRun({ children: [new SequentialIdentifier(kind)], bold: true, font: FONT, size: 20 }),
               new TextRun({ text: ": " + text, font: FONT, size: 20 })] });
}
function pngSize(p) { const b = fs.readFileSync(p); return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) }; }
function figure(file, text, widthIn = 6.0, dir = FIG) {
  const p = path.join(dir, file), s = pngSize(p);
  const w = widthIn * 96, h = w * s.h / s.w;
  return [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 60 },
            children: [new ImageRun({ type: "png", data: fs.readFileSync(p), transformation: { width: w, height: h },
              altText: { title: text, description: text, name: file } })] }),
          caption("Figure", text)];
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "A6A6A6" };
function table(header, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, head, hl) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    shading: head ? { type: ShadingType.CLEAR, color: "auto", fill: NAVY } : hl ? { type: ShadingType.CLEAR, color: "auto", fill: "FCEFC7" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    borders: { top: border, bottom: border, left: border, right: border },
    children: [new Paragraph({ alignment: (opts.align && opts.align[i]) || AlignmentType.LEFT, spacing: { after: 0, line: 260 },
      children: runs(String(t), { size: opts.size || 20, bold: head || hl, color: head ? "FFFFFF" : "000000" }) })] });
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, i, true)) }),
           ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false, opts.highlight && opts.highlight(r))) }))] });
}
const numbering = { config: [
  { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 270 } } } },
    { level: 1, format: LevelFormat.BULLET, text: "\u2013", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 1000, hanging: 270 } } } }] },
  { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] },
  { reference: "numbers2", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] },
  { reference: "numbers3", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] },
] };
const styles = {
  default: { document: { run: { font: FONT, size: 24 } } },
  paragraphStyles: [
    { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 32, bold: true, font: FONT, color: NAVY }, paragraph: { spacing: { before: 120, after: 240 }, outlineLevel: 0 } },
    { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 26, bold: true, font: FONT, color: NAVY }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
    { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: 24, bold: true, italics: true, font: FONT, color: "222222" }, paragraph: { spacing: { before: 180, after: 80 }, outlineLevel: 2 } },
  ],
};

// Corrected model equations shared by both documents
const MODEL_EQ = [
  ["Z_{1} = \u03a3_{r,t} M_{rt} \u03a3_{k} (h_{k}/2) y_{rtk}", "expected waiting rate [passenger-min per hour]"],
  ["Z_{2} = \u03a3_{r,t} d_{r}^{cyc} H_{rt} f_{rt}", "operating effort [vehicle-km per day]"],
  ["Z_{3} = \u03a3_{r,t} o_{rt} H_{rt}", "passengers above capacity [passengers per day]"],
];
const CONS_EQ = [
  ["\u03a3_{k} y_{rtk} = 1,   f_{rt} = \u03a3_{k} (60/h_{k}) y_{rtk}", "one headway per active route-period"],
  ["\u03a3_{r} x_{rt} \u2264 B_{eff}   \u2200t", "fleet limit, B_{eff} = \u230a(1 \u2212 s)B\u230b"],
  ["\u03c4_{r} f_{rt} \u2264 x_{rt},   x_{rt} \u2208 \u2124_{\u22650}", "buses needed to run the frequency"],
  ["o_{rt} \u2265 D_{rt}^{\u03b1} \u2212 C f_{rt},   o_{rt} \u2265 0", "overflow above hourly capacity C\u00b7f"],
  ["f_{r}^{min} \u2264 f_{rt} \u2264 f_{r}^{max}", "published bounds (through the menu K_{rt})"],
  ["|x_{rt} \u2212 x_{r}^{0}| \u2264 max(1, min(3, 0.3x_{r}^{0}))", "practicality; headway cap 60/90 min as a soft goal"],
];

module.exports = { D, F, REFS, NAVY, FONT, CONTENT_W, PROJ, FIG, MEDIA, cite, sgn, pct, n0, runs, P, EQ, H1, H2, H3, BUL, NUM,
  BREAK, caption, figure, table, numbering, styles, MODEL_EQ, CONS_EQ, pngSize };
