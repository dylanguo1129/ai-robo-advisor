"""Compare the registered run (output/v3) with the verification re-run on the corrected code (output/v3_verify), value
by value (docs/RESEARCH_LOG.md section 12). The re-run is not a registered run: it shows which registered values the
fixes after the run would change. Differences are grouped by where they sit; a value that differs must be explained by a
named fix, or it is a failure.

    python scripts/v3_verify_rerun.py
"""

import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
a = json.load(open(ROOT / "output" / "v3" / "results.json", encoding="utf-8"))
b = json.load(open(ROOT / "output" / "v3_verify" / "results.json", encoding="utf-8"))
diffs = []


def walk(x, y, path):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x or k not in y:
                diffs.append((path + "/" + k, "only in " + ("the registered run" if k in x else "the re-run")))
            else:
                walk(x[k], y[k], path + "/" + k)
    elif isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            diffs.append((path, f"length {len(x)} vs {len(y)}"))
        for i, (u, v) in enumerate(zip(x, y)):
            walk(u, v, f"{path}[{i}]")
    elif isinstance(x, float) and isinstance(y, float):
        if not (x == y or (math.isnan(x) and math.isnan(y))):
            diffs.append((path, f"{x!r} vs {y!r}"))
    elif x != y:
        diffs.append((path, f"{str(x)[:60]!r} vs {str(y)[:60]!r}"))


walk(a, b, "")
groups = Counter("/".join(p.split("/")[:4]) for p, _ in diffs)
print(f"{len(diffs)} differing values")
for g, n in sorted(groups.items()):
    print(f"{n:6d}  {g}")
if "-v" in sys.argv:
    for d in diffs:
        print(d)
