"""E7(e) taxonomy sample (docs/research/e7e_taxonomy.md): agreement between our labels and the issuer-sourced labels.

    python scripts/e7e_taxonomy_compare.py docs/research/e7e_taxonomy_sample2.csv [--current]

The issuer's labels imply a satellite status by the engine's own rule: crypto or alternative, an options overlay,
futures, leverage, or a stock fund that is not a broad market-cap index fund. Our labels are the ones recorded in the
file (the labels the sample scored), or with --current the labels of the local universe (data/v2/universe.pkl).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def issuer_satellite(d: pd.DataFrame) -> pd.Series:
    up = lambda c: d[c].fillna("").astype(str).str.upper().str.strip()  # noqa: E731
    return (
        d["issuer_asset_class"].isin(["Crypto", "Alternative"])
        | ~up("issuer_options").str.startswith("NONE")
        | up("issuer_futures").str.startswith("YES")
        | ~up("issuer_leverage").str.replace(" ", "").isin(["1X", ""])
        | ((d["issuer_asset_class"] == "Equity") & up("issuer_broad_index").str.startswith("NO"))
    )


def main(path: str, current: bool) -> None:
    d = pd.read_csv(path)
    if current:
        from robokit.engine import _load

        U = _load()[0].set_index("yahoo")
        d["our_satellite"] = d["yahoo"].map(U["satellite_only"]).astype(bool)
        d["our_asset_class"] = d["yahoo"].map(U["asset_class"])
    d["issuer_says_satellite"] = issuer_satellite(d)
    d["agree"] = d["our_satellite"].astype(bool) == d["issuer_says_satellite"]
    for g, x in d.groupby("group", sort=False):
        print(f"{g}: satellite status agrees {int(x.agree.sum())}/{len(x)}")
    eq = d[d["our_asset_class"] == "Equity"]
    core, sat = eq[~eq["our_satellite"].astype(bool)], eq[eq["our_satellite"].astype(bool)]
    print(f"stock funds we label broad: {int((~core.issuer_says_satellite).sum())}/{len(core)} broad per issuer")
    print(f"stock funds we label narrow: {int(sat.issuer_says_satellite.sum())}/{len(sat)} narrow per issuer")
    for _, r in d[~d.agree].iterrows():
        print(f"  {r.yahoo}: ours {'narrow' if r.our_satellite else 'broad/core'}; issuer {r.issuer_asset_class}, {r.issuer_broad_index}")


if __name__ == "__main__":
    main(sys.argv[1], "--current" in sys.argv[2:])
