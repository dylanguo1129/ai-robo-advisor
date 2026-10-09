"""Replace placeholder paragraphs "@@EQ:<id>@@" (display) and runs "@@IEQ:<id>@@" (inline) in a .docx with real Word
equations.

    python eqinject.py in.docx equations.json out.docx

equations.json maps each id to a LaTeX string. LaTeX -> MathML (latex2mathml) -> OMML with
Word's own MML2OMML.XSL, so the equations are native and editable in Word.
"""

import json
import re
import sys
import zipfile

from latex2mathml.converter import convert
from lxml import etree

XSL = r"C:\Program Files\Microsoft Office\root\Office16\MML2OMML.XSL"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NS = {"w": W, "m": M}

src, eq_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
equations = json.load(open(eq_path, encoding="utf-8"))
to_omml = etree.XSLT(etree.parse(XSL))


MML = "http://www.w3.org/1998/Math/MathML"
SPACES = [(1.9, "  "), (0.9, " "), (0.25, " "), (0.0, " ")]  # em, em, four-per-em, thin


def visible_spaces(tree: etree._Element) -> None:
    """Word's converter drops <mspace>; replace each with an <mtext> holding real space characters."""
    for sp in list(tree.iter(f"{{{MML}}}mspace")):
        width = float((sp.get("width") or "0.167em").replace("em", "") or 0.167)
        text = next(ch for limit, ch in SPACES if width >= limit)
        mt = etree.Element(f"{{{MML}}}mtext")
        mt.text = text
        sp.getparent().replace(sp, mt)
    for mv in list(tree.iter(f"{{{MML}}}mover")):
        mo = mv[-1]
        if etree.QName(mo).localname == "mo" and (mo.text or "").strip() in ("~", "˜", "∼"):
            mv.set("accent", "true")
            mo.text = "˜"
    # operator names (max, min, log, ...) come out as <mo>; Word would set them in italics
    for mo in list(tree.iter(f"{{{MML}}}mo")):
        if mo.text and mo.text.isalpha() and len(mo.text) > 1:
            mi = etree.Element(f"{{{MML}}}mi")
            mi.set("mathvariant", "normal")
            mi.text = mo.text
            mo.getparent().replace(mo, mi)


def omml(latex: str) -> etree._Element:
    mathml = convert(latex, display="block")
    tree = etree.fromstring(mathml.encode("utf-8"))
    visible_spaces(tree)
    node = to_omml(tree).getroot()
    if node is not None and etree.QName(node).localname == "oMathPara":  # block mode wraps it
        node = node.find("m:oMath", NS)
    if node is None or etree.QName(node).localname != "oMath":
        raise ValueError(f"no oMath for: {latex}")
    fix_omml(node)
    return node


def fix_omml(node):
    q = lambda n: f"{{{M}}}{n}"
    for d in list(node.iter(q("d"))):
        sep = d.find(f"{q('dPr')}/{q('sepChr')}")
        es = d.findall(q("e"))
        if sep is None or len(es) < 2:
            continue
        ch = sep.get(q("val"))
        if ch in ("", ",", ";", "|"):
            continue
        first = es[0]
        for e in es[1:]:
            r = etree.SubElement(first, q("r"))
            etree.SubElement(r, q("t")).text = ch
            for c in list(e):
                first.append(c)
            d.remove(e)
        sep.set(q("val"), "")
    for nary in node.iter(q("nary")):
        if any(etree.QName(a).localname == "d" for a in nary.iterancestors()):
            continue  # inside a delimiter Word sets text style; grow keeps the sum readable there
        g = nary.find(f"{q('naryPr')}/{q('grow')}")
        if g is not None:
            g.set(q("val"), "0")


with zipfile.ZipFile(src) as z:
    parts = {n: z.read(n) for n in z.namelist()}

doc = etree.fromstring(parts["word/document.xml"])
used, missing = set(), []
for p in doc.iter(f"{{{W}}}p"):
    text = "".join(t.text or "" for t in p.iter(f"{{{W}}}t"))
    m = re.fullmatch(r"\s*@@EQ:([\w-]+)@@\s*", text)
    if not m:
        continue
    key = m.group(1)
    if key not in equations:
        missing.append(key)
        continue
    new_p = etree.Element(f"{{{W}}}p")
    ppr = etree.SubElement(new_p, f"{{{W}}}pPr")
    old_ppr = p.find("w:pPr", NS)
    if old_ppr is not None:  # keep keep-next and spacing from the placeholder
        for child in old_ppr:
            if etree.QName(child).localname in ("keepNext", "keepLines", "spacing"):
                ppr.append(child)
    jc = etree.SubElement(ppr, f"{{{W}}}jc")
    jc.set(f"{{{W}}}val", "center")
    para = etree.SubElement(new_p, f"{{{M}}}oMathPara")
    para_pr = etree.SubElement(para, f"{{{M}}}oMathParaPr")
    mjc = etree.SubElement(para_pr, f"{{{M}}}jc")
    mjc.set(f"{{{M}}}val", "center")
    para.append(omml(equations[key]))
    p.getparent().replace(p, new_p)
    used.add(key)

# inline equations: a run whose whole text is @@IEQ:<id>@@ becomes an inline <m:oMath> in the same paragraph
for r in list(doc.iter(f"{{{W}}}r")):
    t = r.find("w:t", NS)
    if t is None or not t.text:
        continue
    m = re.fullmatch(r"@@IEQ:([\w-]+)@@", t.text)
    if not m:
        continue
    key = m.group(1)
    if key not in equations:
        missing.append(key)
        continue
    r.getparent().replace(r, omml(equations[key]))
    used.add(key)

if missing:
    sys.exit(f"placeholders without an equation: {missing}")
unused = sorted(set(equations) - used)
parts["word/document.xml"] = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for name, data in parts.items():
        z.writestr(name, data)
print(f"inserted {len(used)} equations; unused ids: {unused or 'none'}")
