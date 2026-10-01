"""Download monthly total-return prices for every listing that could be an ETF.

Run after ``robokit.data.listings.build_listings``. Resumable: rerun to fill gaps.
Cboe Canada quotes of funds whose primary listing is the TSX are skipped
(same fund, second venue).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from robokit.config import DATA_DIR, RAW_DIR
from robokit.data.prices import assemble, download_monthly, usdcad_monthly


def candidate_tickers(listings: pd.DataFrame) -> list[str]:
    ca = listings[listings.market == "CA"].copy()
    base = ca.yahoo.str.replace(r"\.(TO|NE)$", "", regex=True)
    on_tsx = set(base[ca.yahoo.str.endswith(".TO")])
    ca = ca[ca.yahoo.str.endswith(".TO") | ~base.isin(on_tsx)]
    us = listings[listings.market == "US"]
    return sorted(set(ca.yahoo) | set(us.yahoo))


if __name__ == "__main__":
    listings = pd.read_pickle(RAW_DIR / "listings.pkl")
    tickers = candidate_tickers(listings)
    print(f"{len(tickers)} tickers to download", flush=True)
    m = download_monthly(tickers, chunk=100, tag="universe")
    print(f"chunks: {len(m['chunks'])}, failed: {m.get('failed_chunks', [])}", flush=True)
    close, volume = assemble("universe")
    close.to_pickle(DATA_DIR / "close_monthly.pkl")
    volume.to_pickle(DATA_DIR / "volume_monthly.pkl")
    fx = usdcad_monthly()
    fx.to_pickle(DATA_DIR / "usdcad_monthly.pkl")
    print(f"close {close.shape}, window {close.index.min().date()} to {close.index.max().date()}; fx {len(fx)} months", flush=True)
