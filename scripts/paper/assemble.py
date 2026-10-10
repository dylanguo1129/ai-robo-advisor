"""Assemble docs/paper/paper.md from the section drafts, in the paper's order, and check every placeholder resolves.

    python scripts/paper/assemble.py [numbers.json]

The drafts are split at their top-level headings ("# ..."); the title block ("% " lines) comes from front_draft.md.
With a numbers file (default docs/paper/build/paper_numbers.json, written by derive.py), each {{path|format}} is
looked up and formatted exactly as build_paper.py will, so a missing path fails here first.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DOCS = ROOT / "docs" / "paper"
DRAFTS = ["front_draft.md", "literature_draft.md", "method_draft.md", "design_draft.md", "results_draft.md", "back_draft.md"]
ORDER = [
    "Abstract",
    "1. Introduction",
    "2. Related literature",
    "3. Data",
    "4. Method",
    "5. Evaluation design",
    "6. Results",
    "7. Limitations",
    "8. Conclusion",
    "Use of generative AI",
    "References",
    "Appendix A. The exact projection onto the capped simplex",
]


def sections() -> tuple[list[str], dict[str, str]]:
    title, found = [], {}
    for name in DRAFTS:
        cur = None
        for line in (DOCS / name).read_text(encoding="utf-8").splitlines():
            if line.startswith("% "):
                title.append(line)
            elif line.startswith("# "):
                cur = line[2:].strip()
                if cur in found:
                    sys.exit(f"section {cur!r} appears twice")
                found[cur] = line + "\n"
            elif cur is not None:
                found[cur] += line + "\n"
    return title, found


def main():
    title, found = sections()
    missing = [s for s in ORDER if s not in found]
    extra = [s for s in found if s not in ORDER]
    if missing or extra:
        sys.exit(f"sections missing {missing}, not placed {extra}")
    md = "\n".join(title) + "\n\n" + "\n".join(found[s].rstrip() + "\n" for s in ORDER)
    (DOCS / "paper.md").write_text(md, encoding="utf-8", newline="\n")
    numbers = Path(sys.argv[1]) if len(sys.argv) > 1 else DOCS / "build" / "paper_numbers.json"
    if numbers.exists():
        sys.path.insert(0, str(HERE))
        from build_paper import fmt, lookup

        res = json.loads(numbers.read_text(encoding="utf-8"))
        bad = []
        for m in re.finditer(r"\{\{([^}]+)\}\}", md):
            path, _, spec = m.group(1).partition("|")
            try:
                fmt(lookup(res, path.strip()), (spec or "raw").strip())
            except Exception as e:  # noqa: BLE001 - reported, then the script fails
                bad.append(f"{m.group(0)}: {type(e).__name__}: {e}")
        n = len(re.findall(r"\{\{", md))
        if bad:
            print("\n".join(bad))
            sys.exit(f"{len(bad)} of {n} placeholders do not resolve")
        print(f"paper.md written: {len(md.split())} words, {n} placeholders, all resolve")
    else:
        print(f"paper.md written ({numbers} not found: placeholders not checked)")


if __name__ == "__main__":
    main()
