"""Compare two fund universes (docs/research/e7e_taxonomy.md): which columns differ, and whether any slot's candidate
list changes (both markets, standard and ESG shelves). The fund-label fix after the run must change only labels the
slots' rules do not read.

    python scripts/e7e_universe_diff.py OLD.pkl NEW.pkl
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from robokit.shelf import candidates, sleeves_for  # noqa: E402


def main(old_path: str, new_path: str) -> int:
    old = pd.read_pickle(old_path).set_index("yahoo")
    new = pd.read_pickle(new_path).set_index("yahoo")
    if list(old.index) != list(new.index):
        print("the fund lists differ")
        return 1
    changed = {}
    for c in old.columns:
        a, b = old[c], new[c]
        n = int((~((a == b) | (a.isna() & b.isna()))).sum())
        if n:
            changed[c] = n
    print("columns that differ:", changed)
    o, n = old.reset_index(), new.reset_index()
    moved = [
        (m, s.key, esg)
        for m in ("CA", "US")
        for s in sleeves_for(m)
        for esg in (False, True)
        if list(candidates(o, s, prefer_esg=esg)["yahoo"]) != list(candidates(n, s, prefer_esg=esg)["yahoo"])
    ]
    print("slots whose candidate list changes:", moved or "none")
    return 1 if moved else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
