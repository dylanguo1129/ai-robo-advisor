"""Build the research paper from docs/paper/paper.md and output/v3/results.json.

    python scripts/paper/build_paper.py            -> docs/paper/Robo-Kit_v3_Paper.docx and .pdf, and
                                                     docs/paper/build/numbers.json (every number placed)

Numbers come only from results.json, through placeholders {{path|format}} such as
{{E1.CA.strategies.robokit.3.sharpe|f2}}; a missing path stops the build. Formats: f0-f3 (fixed decimals), pct0-pct2
(times 100, with %), pp0-pp2 (times 100, no sign), bp0 (times 10,000), int, raw. A leading + (e.g. +pct1) shows the
sign. The source is Markdown: # / ## / ### headings, paragraphs, - bullets, 1. numbered items, | tables | (a line
"Table: caption" before), $$ display maths $$ (LaTeX), $inline maths$, ![caption](img/file.png), \\newpage. The
equations become native Word equations (scripts/paper/eqinject.py). Requires node with the 'docx' package, Python with
latex2mathml and lxml, and Word (for the equation converter and the PDF).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = Path(os.environ.get("PAPER_SRC", ROOT / "docs" / "paper" / "paper.md"))
OUT = Path(os.environ.get("PAPER_OUT", ROOT / "docs" / "paper"))
BUILD = OUT / "build"
RESULTS = Path(os.environ.get("PAPER_RESULTS", ROOT / "output" / "v3" / "results.json"))
HERE = Path(__file__).resolve().parent


def lookup(res: dict, path: str):
    cur = res
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.lstrip("-").isdigit():
            cur = cur[int(part)]
        else:
            raise KeyError(path)
    return cur


def fmt(v, spec: str) -> str:
    sign = spec.startswith("+")
    spec = spec.lstrip("+")
    if spec == "raw":
        return str(v)
    if v is None:
        raise ValueError("null value")
    v = float(v)
    if spec == "int":
        s = f"{round(v):,d}"
    elif spec.startswith("f"):
        s = f"{v:,.{int(spec[1:])}f}"
    elif spec.startswith("pct"):
        s = f"{100 * v:.{int(spec[3:])}f}%"
    elif spec.startswith("pp"):
        s = f"{100 * v:.{int(spec[2:])}f}"
    elif spec == "bp0":
        s = f"{1e4 * v:.0f}"
    else:
        raise ValueError(f"unknown format {spec}")
    s = s.replace("-", "−")  # a true minus sign
    if sign and v > 0:
        s = "+" + s
    return s


def fill(text: str, res: dict, placed: list) -> str:
    def sub(m):
        path, _, spec = m.group(1).partition("|")
        v = lookup(res, path.strip())
        s = fmt(v, (spec or "raw").strip())
        placed.append({"path": path.strip(), "format": spec.strip(), "value": v, "text": s})
        return s

    return re.sub(r"\{\{([^}]+)\}\}", sub, text)


def parse(md: str, equations: dict) -> list[dict]:
    """Markdown to a list of blocks for paper.js. Maths is lifted out into ``equations``."""
    blocks, para, k = [], [], [0]

    def eq_id(latex: str) -> str:
        k[0] += 1
        key = f"e{k[0]}"
        equations[key] = latex.strip()
        return key

    def inline(text: str) -> list:  # [["t", text] | ["m", id]] segments
        out, last = [], 0
        for m in re.finditer(r"(?<!\$)\$([^$\n]+)\$(?!\$)", text):
            if m.start() > last:
                out.append(["t", text[last : m.start()]])
            out.append(["m", eq_id(m.group(1))])
            last = m.end()
        if last < len(text):
            out.append(["t", text[last:]])
        return out

    def flush():
        if para:
            blocks.append({"type": "p", "segs": inline(" ".join(para))})
            para.clear()

    lines = md.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()
        if not s:
            flush()
            i += 1
            continue
        if s.startswith("<!--"):  # comments are not printed
            while "-->" not in lines[i]:
                i += 1
            i += 1
            continue
        if s.startswith("% "):  # title block: % Title, % Subtitle, % Byline, in that order
            flush()
            kind = ["meta-title", "meta-subtitle", "meta-byline"][sum(1 for x in blocks if x["type"].startswith("meta-"))]
            blocks.append({"type": kind, "text": s[2:].strip()})
            i += 1
            continue
        if s == "\\newpage":
            flush()
            blocks.append({"type": "pagebreak"})
        elif s.startswith("$$"):
            flush()
            body = s[2:]
            if body.endswith("$$") and len(body) >= 2:
                latex = body[:-2]
            else:
                acc = [body]
                i += 1
                while not lines[i].strip().endswith("$$"):
                    acc.append(lines[i])
                    i += 1
                acc.append(lines[i].strip()[:-2])
                latex = " ".join(acc)
            blocks.append({"type": "eq", "id": eq_id(latex)})
        elif s.startswith("#"):
            flush()
            level = len(s) - len(s.lstrip("#"))
            blocks.append({"type": f"h{level}", "text": s[level:].strip()})
        elif s.startswith("- "):
            flush()
            blocks.append({"type": "bullet", "segs": inline(s[2:])})
        elif re.match(r"^\d+\. ", s):
            flush()
            blocks.append({"type": "num", "segs": inline(re.sub(r"^\d+\. ", "", s))})
        elif s.startswith("Table:"):
            flush()
            blocks.append({"type": "tcap", "segs": inline(s[6:].strip())})
        elif s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append([inline(c) for c in cells])
                i += 1
            blocks.append({"type": "table", "rows": rows})
            continue
        elif s.startswith("!["):
            flush()
            m = re.match(r"!\[(.*)\]\((.*)\)", s)
            blocks.append({"type": "image", "caption": m.group(1), "file": str((OUT / m.group(2)).resolve())})
        else:
            para.append(s)
        i += 1
    flush()
    return blocks


def literal_numbers(md: str) -> list[str]:
    """Numbers written into the prose by hand (not placeholders, not maths): listed for the number check."""
    text = re.sub(r"\{\{[^}]+\}\}", " ", md)
    text = re.sub(r"\$\$.*?\$\$", " ", text, flags=re.S)
    text = re.sub(r"\$[^$\n]+\$", " ", text)
    text = re.sub(r"\([^()]*\d{4}[^()]*\)", " ", text)  # citations (Author 2004)
    return sorted(set(re.findall(r"(?<![\w.])\d[\d,]*(?:\.\d+)?%?", text)))


def main():
    res = json.loads(RESULTS.read_text())
    BUILD.mkdir(parents=True, exist_ok=True)
    placed: list = []
    md = fill(SRC.read_text(encoding="utf-8"), res, placed)
    equations: dict = {}
    blocks = parse(md, equations)
    (BUILD / "blocks.json").write_text(json.dumps(blocks, ensure_ascii=False))
    (BUILD / "equations.json").write_text(json.dumps(equations, ensure_ascii=False, indent=1))
    (BUILD / "numbers.json").write_text(
        json.dumps(
            {
                "placed": placed,
                "literal_numbers_in_prose": literal_numbers(SRC.read_text(encoding="utf-8")),
                "results_commit": res.get("provenance", {}).get("commit"),
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    raw, out = BUILD / "raw.docx", OUT / "Robo-Kit_v3_Paper.docx"
    env = dict(os.environ)
    subprocess.run(["node", str(HERE / "paper.js"), str(BUILD / "blocks.json"), str(raw)], check=True, env=env)
    subprocess.run([sys.executable, str(HERE / "eqinject.py"), str(raw), str(BUILD / "equations.json"), str(out)], check=True, env=env)
    subprocess.run(
        ["powershell", "-NoProfile", "-File", str(HERE / "render.ps1"), "-Docx", str(out), "-Pdf", str(out.with_suffix(".pdf"))], check=True
    )
    print(f"{len(placed)} numbers placed from results.json; {len(equations)} equations")


if __name__ == "__main__":
    main()
