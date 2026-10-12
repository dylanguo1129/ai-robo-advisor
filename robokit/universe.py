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
    # A Nasdaq listing name can be generic ("Common Shares of Beneficial Interest") or lose a "+" ("10  Year"); the
    # issuer's long name then says what the fund holds, which the classification and the slot rules read.
    if "longName" in L.columns:
        bad = L["name"].fillna("").str.contains(r"^(?:common )?shares of beneficial interest$|\d  +year", case=False, regex=True)
        L.loc[bad & L["longName"].notna(), "name"] = L.loc[bad & L["longName"].notna(), "longName"]
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


JUMP_LOG = float(np.log(2.0))  # a one-month doubling or halving
JUMP_FROM = "2000-01-01"  # the history the engine and the web page use


def price_jumps(R: pd.DataFrame, U: pd.DataFrame, candidates: pd.Series) -> dict[str, tuple]:
    """Funds whose monthly total return at least doubled or halved in a month when similar funds did not.

    "Similar funds" are the candidates of the same market and asset class (at least five with data that
    month); the gap is measured in log returns, so +100% and -50% count the same. A move this size is
    either a data error, such as a unit consolidation priced as a return, or a fund too narrow for a
    long-term portfolio; in both cases its history would dominate the risk estimate. Crypto is exempt.
    Returns {ticker: (month, return, peer median return)} for the largest such month of each fund."""
    Rw = R[R.index >= JUMP_FROM]
    L = np.log1p(Rw.where(Rw > -1))
    pool = U[candidates & U.yahoo.isin(Rw.columns) & (U.asset_class != "Crypto")]
    out: dict[str, tuple] = {}
    for _, g in pool.groupby(["market", "asset_class"]):
        cols = list(g.yahoo)
        peer = L[cols].median(axis=1)
        n = L[cols].notna().sum(axis=1)
        for t in cols:
            gap = (L[t] - peer).abs().where((L[t].abs() >= JUMP_LOG) & (n >= 5))
            gap = gap[gap >= JUMP_LOG]
            if len(gap):
                d = gap.idxmax()
                out[t] = (d, float(np.expm1(L.at[d, t])), float(np.expm1(peer[d])))
    return out


# Regions a whole-market stock fund can cover; a single foreign country or one region (Europe, Japan) is narrower.
BROAD_REGIONS = ("US", "Canada", "North America", "Global", "International developed", "Emerging markets")
# Themes a broad stock fund may carry: the broad-market index name, and an ESG screen of it (the ESG shelf's funds).
BROAD_THEMES = ({"Broad market"}, {"Broad market", "ESG / climate"})


def broad_equity(U: pd.DataFrame) -> pd.Series:
    """A stock fund that holds a whole market: its name names a whole-market index, and nothing narrower (no sector,
    style, size, factor, dividend, thematic, single-country or options marker), it is not run on a manager's picks,
    and it covers a broad region. Positive evidence is required: a name the rules cannot place is not broad."""
    themes = U["theme"].fillna("").map(lambda s: frozenset(t.strip() for t in s.split(";") if t.strip()))
    return (
        (U["asset_class"] == "Equity")
        & themes.map(lambda s: s in BROAD_THEMES)
        & U["region"].isin(BROAD_REGIONS)
        & ~U["strategy"].isin(["Active", "Options-based", "Leveraged / inverse (daily reset)"])
        & ~U["derivatives"].fillna("").str.contains("options|futures")
    )


def satellite_only(U: pd.DataFrame) -> pd.Series:
    """Eligible funds that are narrow or complex: crypto, alternatives, option-overlay and futures-based funds, and
    every stock fund that is not a broad index fund. They are labelled so; what may stand in a core slot is decided by
    the slot's own rule (engine.select_funds)."""
    return U["eligible"] & (
        U.asset_class.isin(["Crypto", "Alternative"])
        | U.theme.str.contains("Covered call|Buffer", na=False)
        | U.derivatives.str.contains("futures", na=False)
        | ((U.asset_class == "Equity") & ~broad_equity(U))
    )


TEAM_BRIDGE = "robokit_bridge_ca.csv"
MER_RANGE = (0.0005, 0.03)  # an MER outside 0.05%-3% is most likely in the wrong unit


def add_team_data(U: pd.DataFrame) -> pd.DataFrame:
    """Fields from the team's Canadian ETF data layer (github.com/shreyajane23/robokit-data, optimizer_bridge), when
    its bridge file is in DATA_DIR: inception date, fund age, a risk rating calculated with the CSA method,
    distribution frequency and yield, and a secondary theme (columns rk_*, keyed on yahoo). Its MER and AUM fill only
    our blanks (an MER outside MER_RANGE and an AUM of zero are left out); each filled value says so in the
    fund's note. Without the file the universe is unchanged."""
    p = DATA_DIR / TEAM_BRIDGE
    if not p.exists():
        return U
    B = pd.read_csv(p)
    U = U.merge(B[[c for c in B.columns if c == "yahoo" or c.startswith("rk_")]], on="yahoo", how="left")
    mer = U["mer"].isna() & U["rk_mer"].between(*MER_RANGE)
    U.loc[mer, "mer"] = U.loc[mer, "rk_mer"]
    U.loc[mer, "why"] = U.loc[mer, "why"].fillna("") + " | MER from the team's data layer (Yahoo fund profile)"
    aum = U["aum"].isna() & (U["rk_aum"] > 0)  # a zero is a missing value in the source, not an empty fund
    U.loc[aum, "aum"] = U.loc[aum, "rk_aum"]
    U.loc[aum, "why"] = U.loc[aum, "why"].fillna("") + " | assets from the team's data layer (Yahoo fund profile)"
    return U


def build_universe(save: bool = True) -> pd.DataFrame:
    L = dedupe_canada(load_listings())
    C = classify(L)
    close = pd.read_pickle(DATA_DIR / "close_monthly.pkl")
    volume = pd.read_pickle(DATA_DIR / "volume_monthly.pkl")
    S = price_stats(close, volume)
    U = add_team_data(C.merge(S, left_on="yahoo", right_index=True, how="left"))
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
    # price-history integrity: a one-month doubling or halving that similar funds did not share
    jumps = price_jumps(monthly_returns(close), U, U["excluded_because"] == "")
    for t, (d, r, peer) in jumps.items():
        i = U.index[U.yahoo == t]
        U.loc[i, "excluded_because"] = (
            f"its price history moved {r:+.0%} in {pd.Timestamp(d):%b %Y} while similar funds moved {peer:+.0%}: "
            "either a data error such as an unadjusted unit split, or a fund too narrow for a long-term portfolio"
        )
    U["eligible"] = U["excluded_because"] == ""
    U["satellite_only"] = satellite_only(U)
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
