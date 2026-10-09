const fs = require("fs");
const path = require("path");
const {
  Document, PageBreak, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun, HeadingLevel, AlignmentType,
  WidthType, ShadingType, BorderStyle, LevelFormat, Footer, PageNumber, TabStopType,
} = require("docx");

const IMG = process.env.IMG || path.join(__dirname, "img");
const FONT = "Calibri";
const MONO = "Consolas";
const W = 9360; // content width in DXA (8.5in - 2 x 1in)
const GREY = "F2F2F2";
const LINE = "BFBFBF";

// **bold**, `code` and *italic* inside a string
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*|_\{[^}]+\}|\^\{[^}]+\})/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: MONO, size: 19, ...base }));
    else if (t.startsWith("_{")) out.push(new TextRun({ text: t.slice(2, -1), subScript: true, ...base }));
    else if (t.startsWith("^{")) out.push(new TextRun({ text: t.slice(2, -1), superScript: true, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}
const P = (text, opts = {}) => new Paragraph({ children: runs(text, opts.run || {}), spacing: { after: 120, line: 276 }, ...opts.para });
const H1 = text => new Paragraph({ heading: HeadingLevel.HEADING_1, keepNext: true, children: [new TextRun(text)], spacing: { before: 360, after: 160 } });
const H2 = text => new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: [new TextRun(text)], spacing: { before: 280, after: 100 } });
const bullet = text => new Paragraph({ numbering: { reference: "bullets", level: 0 }, children: runs(text), spacing: { after: 80, line: 264 } });
const numbered = (text, ref) => new Paragraph({ numbering: { reference: ref, level: 0 }, children: runs(text), spacing: { after: 100, line: 264 } });
const caption = text => new Paragraph({ children: [new TextRun({ text, italics: true, size: 18, color: "595959" })], spacing: { before: 60, after: 200 } });
const EQ = (id, next = false) => new Paragraph({ alignment: AlignmentType.CENTER, keepLines: true, keepNext: next, spacing: { before: 60, after: 140 }, children: [new TextRun("@@EQ:" + id + "@@")] });
const formula = text => new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text, font: "Cambria Math", size: 22 })], spacing: { before: 80, after: 140 } });

function image(file, w, h, widthPx = 560) { // 560 px is about 5.8in at 96 dpi
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    keepNext: true,
    spacing: { before: 120, after: 40 },
    children: [new ImageRun({ type: "png", data: fs.readFileSync(path.join(IMG, file)), transformation: { width: widthPx, height: Math.round(widthPx * h / w) } })],
  });
}

const border = { style: BorderStyle.SINGLE, size: 4, color: LINE };
const borders = { top: border, bottom: border, left: border, right: border };
function table(headers, rows, widths, keepTogether = true) {
  const total = widths.reduce((a, b) => a + b, 0);
  if (total !== W) throw new Error(`table widths sum to ${total}, not ${W}`);
  const cell = (text, i, head, keep) => new TableCell({
    borders,
    width: { size: widths[i], type: WidthType.DXA },
    shading: head ? { fill: "D9E2F3", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ keepNext: keep, children: runs(text, { size: 19, bold: head || undefined }), spacing: { after: 0, line: 252 } })],
  });
  return new Table({
    width: { size: W, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((t, i) => cell(t, i, true, keepTogether)) }),
      ...rows.map((r, k) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, i, false, keepTogether && k < rows.length - 1)) })),
    ],
  });
}
const gap = () => new Paragraph({ children: [], spacing: { after: 120 } });

function code(lines) {
  return lines.map((ln, i) => new Paragraph({
    keepNext: lines.length <= 14 && i < lines.length - 1,
    keepLines: true,
    shading: { fill: GREY, type: ShadingType.CLEAR, color: "auto" },
    spacing: { before: i === 0 ? 120 : 0, after: i === lines.length - 1 ? 160 : 0, line: 240 },
    indent: { left: 120, right: 120 },
    children: [new TextRun({ text: ln.length ? ln : " ", font: MONO, size: 16 })],
  }));
}


// numbered caption helpers: Figure n / Table n
let figN = 0, tabN = 0;
const figure = text => caption(`Figure ${++figN}. ${text}`);
const tcap = text => new Paragraph({ keepNext: true, children: [new TextRun({ text: `Table ${++tabN}. `, bold: true, size: 19, color: "404040" }), ...runs(text, { size: 19, color: "404040" })], spacing: { before: 160, after: 80 } });
const resetCounters = () => { figN = 0; tabN = 0; };

function makeDoc({ title, footer, body }) {
  return new Document({
    creator: "Team Summerhill",
    title,
    styles: {
      default: { document: { run: { font: FONT, size: 21 } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 32, bold: true, font: FONT, color: "1F3864" }, paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 25, bold: true, font: FONT, color: "2F5496" }, paragraph: { spacing: { before: 280, after: 100 }, outlineLevel: 1 } },
      ],
    },
    numbering: {
      config: [
        { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
        { reference: "setup", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] },
        { reference: "steps", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } } } }] },
        { reference: "refs", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "[%1]", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 540 } } } }] },
      ],
    },
    sections: [{
      properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
      footers: {
        default: new Footer({ children: [new Paragraph({
          tabStops: [{ type: TabStopType.RIGHT, position: W }],
          children: [
            new TextRun({ text: footer, size: 16, color: "7F7F7F" }),
            new TextRun({ children: [String.fromCharCode(9), PageNumber.CURRENT], size: 16, color: "7F7F7F" }),
          ],
        })] }),
      },
      children: body,
    }],
  });
}

function write(doc, out) {
  return Packer.toBuffer(doc).then(buf => { fs.writeFileSync(out, buf); console.log("wrote", out, buf.length); });
}

module.exports = { fs, path, Paragraph, TextRun, HeadingLevel, AlignmentType, ShadingType, BorderStyle, PageBreak, W, GREY, LINE, MONO,
  runs, P, H1, H2, bullet, numbered, caption, EQ, image, table, gap, code, figure, tcap, resetCounters, makeDoc, write };
