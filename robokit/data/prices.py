"""Monthly total-return prices for the whole universe.

Yahoo's adjusted close (``auto_adjust=True``) folds dividends and splits into
the price, so month-over-month changes are total returns. Monthly bars are
labelled with the first day of the month and closed at the month's last
trading day; the current, unfinished month is dropped so that no partial
month ever enters an estimate.

Downloads run in chunks and each chunk is written to disk before the next
starts, so an interrupted run resumes where it stopped.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import DATA_DIR, ensure_dirs

CHUNK_DIR = DATA_DIR / "raw" / "price_chunks"
FX_TICKER = "CAD=X"  # Canadian dollars per US dollar


def _download_chunk(tickers: list[str], attempts: int = 4) -> pd.DataFrame:
    import yfinance as yf

    for i in range(attempts):
        try:
            d = yf.download(
                tickers, period="max", interval="1mo", auto_adjust=True,
                progress=False, threads=True, group_by="column",
            )
            if d is not None and len(d):
                return d
        except Exception:  # throttling or a network blip: back off
            pass
        time.sleep(5 * (i + 1))
    return pd.DataFrame()


def download_monthly(tickers: list[str], chunk: int = 100, tag: str = "universe") -> dict:
    """Download monthly adjusted close and volume; resumable. Returns a manifest."""
    ensure_dirs()
    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    tickers = sorted(set(tickers))
    manifest = {"tag": tag, "n_tickers": len(tickers), "chunks": [], "started": datetime.now(timezone.utc).isoformat()}
    for k in range(0, len(tickers), chunk):
        part = tickers[k : k + chunk]
        path = CHUNK_DIR / f"{tag}_{k // chunk:04d}.pkl"
        if path.exists():
            manifest["chunks"].append(str(path.name))
            continue
        d = _download_chunk(part)
        if d.empty:
            manifest.setdefault("failed_chunks", []).append(k // chunk)
            continue
        out = {"close": d["Close"], "volume": d["Volume"] if "Volume" in d else None, "tickers": part}
        tmp = path.with_suffix(".tmp")
        pd.to_pickle(out, tmp)
        tmp.replace(path)  # atomic: a killed run never leaves a half-written chunk
        manifest["chunks"].append(str(path.name))
        time.sleep(1.0)
    manifest["finished"] = datetime.now(timezone.utc).isoformat()
    (DATA_DIR / f"prices_manifest_{tag}.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def assemble(tag: str = "universe", today: pd.Timestamp | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Combine chunks into wide monthly close and volume frames (month-end index)."""
    closes, vols = [], []
    for p in sorted(CHUNK_DIR.glob(f"{tag}_*.pkl")):
        obj = pd.read_pickle(p)
        c = obj["close"]
        if isinstance(c, pd.Series):
            c = c.to_frame(obj["tickers"][0])
        closes.append(c)
        v = obj.get("volume")
        if v is not None:
            if isinstance(v, pd.Series):
                v = v.to_frame(obj["tickers"][0])
            vols.append(v)
    close = pd.concat(closes, axis=1)
    close = close.loc[:, ~close.columns.duplicated()]
    volume = pd.concat(vols, axis=1) if vols else pd.DataFrame(index=close.index)
    volume = volume.loc[:, ~volume.columns.duplicated()]
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    current_month = today.to_period("M").to_timestamp()
    close = close[close.index < current_month]
    volume = volume[volume.index < current_month]
    # month-start labels -> month-end labels, which is what the rest of the code uses
    close.index = close.index.to_period("M").to_timestamp("M")
    volume.index = volume.index.to_period("M").to_timestamp("M")
    # Yahoo sometimes adds an extra mid-month bar for some exchanges; keep one row per month
    close = close.groupby(level=0).last()
    volume = volume.groupby(level=0).max()
    close = close.dropna(how="all", axis=1)
    return close.sort_index(), volume.reindex(columns=close.columns).sort_index()


def monthly_returns(close: pd.DataFrame) -> pd.DataFrame:
    """Simple monthly total returns. Gaps inside a series are left as NaN, never filled."""
    r = close.pct_change(fill_method=None)
    return r.where(close.notna() & close.shift(1).notna())


def usdcad_monthly(today: pd.Timestamp | None = None) -> pd.Series:
    """Month-end CAD per USD, used to express US-listed funds in Canadian dollars."""
    import yfinance as yf

    fx = yf.download(FX_TICKER, period="max", interval="1mo", auto_adjust=True, progress=False)["Close"]
    if isinstance(fx, pd.DataFrame):
        fx = fx.iloc[:, 0]
    today = pd.Timestamp(today or pd.Timestamp.today()).normalize()
    fx = fx[fx.index < today.to_period("M").to_timestamp()]
    fx.index = fx.index.to_period("M").to_timestamp("M")
    return fx.rename("USDCAD").dropna()


def to_cad(returns_usd: pd.DataFrame, usdcad: pd.Series) -> pd.DataFrame:
    """(1 + r_usd)(1 + r_fx) - 1: the return a Canadian investor earns on a US fund."""
    fx_r = usdcad.pct_change().reindex(returns_usd.index)
    return (1 + returns_usd).mul(1 + fx_r, axis=0) - 1


def to_usd(returns_cad: pd.DataFrame, usdcad: pd.Series) -> pd.DataFrame:
    """(1 + r_cad) / (1 + r_fx) - 1: the return a US investor earns on a Canadian-dollar fund."""
    fx_r = usdcad.pct_change().reindex(returns_cad.index)
    return (1 + returns_cad).div(1 + fx_r, axis=0) - 1


def dollar_volume(close: pd.DataFrame, volume: pd.DataFrame, months: int = 6) -> pd.Series:
    """Average daily traded value over the last ``months`` months (approximate: monthly volume / 21)."""
    dv = (close * volume / 21.0).tail(months)
    return dv.replace([np.inf, -np.inf], np.nan).mean()
