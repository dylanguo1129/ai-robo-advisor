"""Compare the registered run (output/v3) with the archived first run (output/v3_run1) value by value (RESEARCH_LOG
section 11). Expected differences: provenance (commit, times), E2 CA static_mix and what is computed from it,
path_errors. Anything else that differs is a reproducibility failure.

    python scripts/v3_compare_runs.py
"""

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
a = json.load(open(ROOT / "output" / "v3_run1" / "results.json", encoding="utf-8"))
b = json.load(open(ROOT / "output" / "v3" / "results.json", encoding="utf-8"))
diffs = []


def walk(x, y, path):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if k not in x or k not in y:
                diffs.append((path + "/" + k, "only in " + ("run 1" if k in x else "run 2")))
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
expected_prefixes = ("/provenance", "/E2/CA", "/path_errors")
unexpected = [d for d in diffs if not d[0].startswith(expected_prefixes)]
print(f"{len(diffs)} differing values; {len(unexpected)} outside the expected places")
for d in unexpected[:40]:
    print("UNEXPECTED", d)
for d in [d for d in diffs if d[0].startswith("/E2/CA")][:12]:
    print("E2 CA", d)
sys.exit(1 if unexpected else 0)
