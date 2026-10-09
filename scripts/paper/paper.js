// Renders docs/paper/build/blocks.json (from build_paper.py) to a .docx: node paper.js blocks.json out.docx
// Maths appears as @@EQ:id@@ paragraphs and @@IEQ:id@@ runs; eqinject.py turns them into Word equations.
const fs = require("fs");
const L = require("./lib.js");
const { Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, ImageRun } = require("docx");

const [, , src, out] = process.argv;
const blocks = JSON.parse(fs.readFileSync(src, "utf8"));

function segRuns(segs, base = {}) {
  const outRuns = [];
  for (const [kind, v] of segs) {
    if (kind === "t") outRuns.push(...L.runs(v, base));
    else outRuns.push(new TextRun({ text: `@@IEQ:${v}@@`, ...base }));
  }
  return outRuns;
}
const segText = (segs) => segs.map(([k, v]) => (k === "t" ? v : "xx")).join("");

const border = { style: BorderStyle.SINGLE, size: 4, color: L.LINE };
const borders = { top: border, bottom: border, left: border, right: border };
function table(rows) {
  const n = rows[0].length;
  const len = Array.from({ length: n }, (_, j) => Math.max(...rows.map(r => Math.min(60, segText(r[j] || []).length)), 4));
  const tot = len.reduce((a, b) => a + b, 0);
  const widths = len.map(x => Math.round((x / tot) * L.W));
  widths[n - 1] += L.W - widths.reduce((a, b) => a + b, 0);
  const cell = (segs, j, head, keep) => new TableCell({
    borders,
    width: { size: widths[j], type: WidthType.DXA },
    shading: head ? { fill: "D9E2F3", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: [new Paragraph({ keepNext: keep, children: segRuns(segs || [], head ? { size: 18, bold: true } : { size: 18 }), spacing: { after: 0, line: 245 } })],
  });
  return new Table({
    width: { size: L.W, type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map((r, i) => new TableRow({ tableHeader: i === 0, cantSplit: true, children: r.map((c, j) => cell(c, j, i === 0, i < rows.length - 1 && rows.length <= 14)) })),
  });
}

function pngSize(file) {
  const b = fs.readFileSync(file);
  return [b.readUInt32BE(16), b.readUInt32BE(20)];
}

let figN = 0, tabN = 0;
const body = [];
for (const b of blocks) {
  switch (b.type) {
    case "meta-title":
      body.push(new Paragraph({ children: [new TextRun({ text: b.text, bold: true, size: 40, color: "1F3864" })], spacing: { after: 80 } }));
      break;
    case "meta-subtitle":
      body.push(new Paragraph({ children: [new TextRun({ text: b.text, size: 25, color: "404040" })], spacing: { after: 80 } }));
      break;
    case "meta-byline":
      body.push(new Paragraph({ children: [new TextRun({ text: b.text, size: 19, color: "7F7F7F" })], spacing: { after: 280 } }));
      break;
    case "h1":
      body.push(L.H1(b.text));
      break;
    case "h2":
      body.push(L.H2(b.text));
      break;
    case "h3":
      body.push(new Paragraph({ keepNext: true, children: [new TextRun({ text: b.text, bold: true, size: 21, color: "1F3864" })], spacing: { before: 200, after: 80 } }));
      break;
    case "p":
      body.push(new Paragraph({ children: segRuns(b.segs), spacing: { after: 120, line: 276 }, alignment: AlignmentType.JUSTIFIED }));
      break;
    case "bullet":
      body.push(new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: segRuns(b.segs), spacing: { after: 80, line: 264 } }));
      break;
    case "num":
      body.push(new Paragraph({ numbering: { reference: "steps", level: 0 }, children: segRuns(b.segs), spacing: { after: 90, line: 264 } }));
      break;
    case "tcap":
      body.push(new Paragraph({ keepNext: true, children: [new TextRun({ text: `Table ${++tabN}. `, bold: true, size: 19, color: "404040" }), ...segRuns(b.segs, { size: 19, color: "404040" })], spacing: { before: 160, after: 80 } }));
      break;
    case "table":
      body.push(table(b.rows));
      body.push(L.gap());
      break;
    case "eq":
      body.push(L.EQ(b.id));
      break;
    case "image": {
      const [w, h] = pngSize(b.file);
      const px = 600;
      body.push(new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120, after: 40 },
        children: [new ImageRun({ type: "png", data: fs.readFileSync(b.file), transformation: { width: px, height: Math.round(px * h / w) } })] }));
      body.push(new Paragraph({ children: [new TextRun({ text: `Figure ${++figN}. `, bold: true, size: 18, color: "404040" }), ...L.runs(b.caption, { size: 18, color: "595959", italics: true })], spacing: { before: 40, after: 200 } }));
      break;
    }
    case "pagebreak":
      body.push(new Paragraph({ pageBreakBefore: true, children: [] }));
      break;
    default:
      throw new Error(`unknown block ${b.type}`);
  }
}
L.write(L.makeDoc({ title: "Robo-Kit v3: research paper", footer: "Robo-Kit v3 portfolio engine: design, proofs and a pre-registered evaluation", body }), out);
