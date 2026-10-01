"""Assemble the investable universe: listings + classification + price statistics + eligibility.

Output: one row per ETF listing with everything the screener, the optimizer,
the chat agent and the web page need, and an ``eligible`` flag with a
plain-language ``excluded_because`` for every fund the optimizer will not use.
Nothing is deleted: excluded funds stay searchable so the product can explain
why ("TQQQ is a 3x daily leveraged fund; leverage resets daily and is not
suitable for a buy-and-hold portfolio").
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .classify import classify
from .config import DATA_DIR, MIN_AUM, MIN_DOLLAR_VOLUME, MIN_HISTORY_MONTHS, RAW_DIR
from .data.prices import dollar_volume, monthly_returns


def load_listings() -> pd.DataFrame:
    L = pd.read_pickle(RAW_DIR / "listings.pkl")
    cats = []
    for f in ("yahoo_categories_us.csv", "yahoo_categories_ca.csv"):
        p = RAW_DIR / f
        if p.exists():
            cats.append(pd.read_csv(p))
    if cats:
        cat = pd.concat(cats).drop_duplicates("yahoo")
        L = L.merge(cat, on="yahoo", how="left")
    return L


def dedupe_canada(L: pd.DataFrame) -> pd.DataFrame:
    """A TSX-listed fund also quoted on Cboe Canada is one fund: keep the TSX line."""
    is_ca = L.market == "CA"
    base = L.yahoo.str.replace(r"\.(TO|NE)$", "", regex=True)
    on_tsx = set(base[is_ca & L.yahoo.str.endswith(".TO")])
    dup = is_ca & L.yahoo.str.endswith(".NE") & base.isin(on_tsx)
    return L[~dup].copy()


def price_stats(close: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    R = monthly_returns(close)
    last = R.index.max()
    n = R.notna().sum()
    first = R.apply(lambda s: s.first_valid_index())
    lastv = R.apply(lambda s: s.last_valid_index())

    def ann_vol(months: int) -> pd.Series:
        w = R.tail(months)
        ok = w.notna().sum() >= int(0.9 * months)
        return (w.std() * np.sqrt(12)).where(ok)

    def ann_ret(months: int) -> pd.Series:
        w = R.tail(months)
        ok = w.notna().sum() == months
        return ((1 + w).prod() ** (12 / months) - 1).where(ok)

    wealth = (1 + R.fillna(0)).cumprod().where(R.notna() | R.bfill().notna())
    dd = (wealth / wealth.cummax() - 1).min()
    out = pd.DataFrame(
        {
            "history_months": n,
            "first_month": first,
            "last_month": lastv,
            "vol_3y": ann_vol(36),
            "vol_5y": ann_vol(60),
            "ret_1y": ann_ret(12),
            "ret_3y": ann_ret(36),
            "ret_5y": ann_ret(60),
            "ret_10y": ann_ret(120),
            "max_drawdown": dd,
            "dollar_volume": dollar_volume(close, volume),
            "last_close": close.apply(lambda s: s.dropna().iloc[-1] if s.notna().any() else np.nan),
            "last_close_date": close.apply(lambda s: s.last_valid_index()),
        }
    )
    out["stale"] = out["last_month"] < last
    return out


def build_universe(save: bool = True) -> pd.DataFrame:
    L = dedupe_canada(load_listings())
    C = classify(L)
    close = pd.read_pickle(DATA_DIR / "close_monthly.pkl")
    volume = pd.read_pickle(DATA_DIR / "volume_monthly.pkl")
    S = price_stats(close, volume)
    U = C.merge(S, left_on="yahoo", right_index=True, how="left")
    U["history_months"] = U["history_months"].fillna(0).astype(int)
    U["has_prices"] = U["yahoo"].isin(close.columns)

    reasons = []
    for _, r in U.iterrows():
        why = []
        if r.cdr:
            why.append("not an ETF: a depositary receipt on one company")
        if r.leverage != 1.0:
            why.append(
                f"{'inverse' if r.leverage < 0 else 'leveraged'} {abs(r.leverage):g}x with daily reset; built for short-term trading"
            )
        if r.single_stock and not r.cdr:
            why.append("tracks a single company, so it does not diversify")
        if r.market == "CA" and r.currency == "USD":
            why.append("trades in US dollars (this is the U.S.-dollar unit of the fund)")
        if not r.has_prices:
            why.append("no price history available")
        elif r.history_months < MIN_HISTORY_MONTHS:
            why.append(f"only {r.history_months} months of history (need {MIN_HISTORY_MONTHS})")
        elif r.stale:
            why.append("price history stops before the latest month")
        if pd.notna(r.aum) and r.aum < MIN_AUM[r.market]:
            why.append(f"small fund: {r.aum / 1e6:.0f}M in assets (minimum {MIN_AUM[r.market] / 1e6:.0f}M)")
        if pd.notna(r.dollar_volume) and r.dollar_volume < MIN_DOLLAR_VOLUME[r.market]:
            why.append(f"thinly traded: about {r.dollar_volume / 1e3:.0f}K a day")
        if pd.isna(r.aum) and pd.isna(r.dollar_volume):
            why.append("no size or trading data")
        reasons.append("; ".join(why))
    U["excluded_because"] = reasons
    U["eligible"] = U["excluded_because"] == ""
    # Funds that pass but carry extra risk are allowed only as satellites (see engine guardrails).
    U["satellite_only"] = U["eligible"] & (
        U.asset_class.isin(["Crypto", "Alternative"])
        | U.theme.str.contains("Covered call|Buffer", na=False)
        | U.derivatives.str.contains("futures", na=False)
        | ((U.asset_class == "Equity") & ~U.theme.str.contains("Broad market", na=False))
    )
    if save:
        U.to_pickle(DATA_DIR / "universe.pkl")
        U.drop(columns=[]).to_csv(DATA_DIR / "universe.csv", index=False)
        summary = {
            "listings": int(len(U)),
            "by_market": U.groupby("market").size().to_dict(),
            "eligible_by_market": U[U.eligible].groupby("market").size().to_dict(),
            "prices_through": str(close.index.max().date()),
        }
        (DATA_DIR / "universe_summary.json").write_text(json.dumps(summary, indent=2))
    return U
