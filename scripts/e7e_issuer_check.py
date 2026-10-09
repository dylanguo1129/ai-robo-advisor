"""E7(e) (docs/research/e7e_issuer_check.md): our annualised total return for each reference fund over the window an
issuer's published figure covers. Monthly returns from adjusted month-end closes in the fund's own trading currency
(the data the engine uses), compounded over the 60 months ending at the as-of date.

    python scripts/e7e_issuer_check.py   -> one line per fund, as of 31 Aug 2026
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from robokit import engine as E  # noqa: E402

TICKERS = {
    "XIC": "XIC.TO",
    "VFV": "VFV.TO",
    "FLUR": "FLUR.NE",
    "VEE": "VEE.TO",
    "ZAG": "ZAG.TO",
    "XSB": "XSB.TO",
    "VBU": "VBU.NE",
    "XRE": "XRE.TO",
    "VALT": "VALT.TO",
    "CASH": "CASH.TO",
    "VOO": "VOO",
    "VXUS": "VXUS",
    "VWO": "VWO",
    "BND": "BND",
    "VGSH": "VGSH",
    "SCHP": "SCHP",
    "BNDX": "BNDX",
    "VNQ": "VNQ",
    "GLDM": "GLDM",
    "SGOV": "SGOV",
}


def ours(ticker: str, as_of: str, years: float = 5.0) -> tuple[float | None, int]:
    """Annualised return over the ``years`` ending at ``as_of`` (None when the data end earlier or are too short)."""
    s = E._load()[1][TICKERS[ticker]].dropna()
    end = pd.Timestamp(as_of) + pd.offsets.MonthEnd(0)
    if end > s.index.max():
        return None, 0
    n = int(round(12 * years))
    w = s.loc[:end].iloc[-n:]
    if len(w) < n:
        return None, len(w)
    return float(np.prod(1 + w.to_numpy()) ** (12 / len(w)) - 1), len(w)


if __name__ == "__main__":
    for t in TICKERS:
        g, n = ours(t, "2026-08-31")
        print(t, "short history" if g is None else f"{100 * g:.2f}%", n)
