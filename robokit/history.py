"""Longer histories for young funds, with every splice disclosed.

Many of the cheapest funds on the shelf are young (a 2021 savings ETF, a
2020 gold fund). Estimating risk from five years of data would make the
whole portfolio depend on one short, unusual period. Two standard fixes:

1. Core funds: splice in a long-lived fund with the same exposure for the
   months before the young fund existed (VFV.TO before 2012 is SPY converted
   to Canadian dollars; a savings ETF before 2021 is the 3-month T-bill
   yield). Proxies are written down per sleeve below and must correlate at
   0.8 or more with the fund over their overlap (except for cash, where
   month-to-month correlation is not meaningful).
2. Satellites: fill the months before the fund existed from its measured
   relationship with the core funds (regression on the overlap) plus a
   residual taken from its own history by a fixed stride, so results are
   reproducible and identical in the browser.
   This is a single-imputation version of the approach in Stambaugh (1997),
   "Analyzing investments whose histories differ in length", JFE 45(3).

Every spliced month is listed in the output so the interface can say so.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

PROXIES = {
    "ca_equity": [("XIC.TO", False)],
    "ca_us_equity": [("SPY", True)],
    "ca_us_equity_hedged": [("XSP.TO", False), ("SPY", False)],
    "ca_intl_equity": [("XEF.TO", False), ("EFA", True)],
    "ca_em_equity": [("XEC.TO", False), ("EEM", True)],
    "ca_agg_bond": [("XBB.TO", False)],
    "ca_short_bond": [("XSB.TO", False)],
    "ca_global_bond": [("AGG", False)],  # hedged to CAD ~ the USD return; disclosed as approximate
    "ca_reit": [("XRE.TO", False)],
    "ca_gold": [("CGL-C.TO", False), ("GLD", True)],
    "ca_cash": [("PSA.TO", False), ("RATE:V80691344", False)],
    "ca_long_bond": [("XLB.TO", False)],
    "ca_real_return": [("XRB.TO", False)],
    "ca_high_yield": [("XHY.TO", False), ("HYG", False)],
    "us_equity": [("SPY", False)],
    "us_intl_equity": [("EFA", False)],
    "us_em_equity": [("EEM", False)],
    "us_agg_bond": [("AGG", False)],
    "us_short_treasury": [("SHY", False)],
    "us_tips": [("TIP", False)],
    "us_intl_bond": [("BNDX", False), ("BWX", False)],
    "us_reit": [("VNQ", False), ("IYR", False)],
    "us_gold": [("IAU", False), ("GLD", False)],
    "us_cash": [("BIL", False), ("RATE:^IRX", False)],
    "us_small_cap": [("IWM", False)],
    "us_long_treasury": [("TLT", False)],
    "us_corp_bond": [("LQD", False)],
    "us_high_yield": [("HYG", False)],
}
MIN_CORR = 0.8
MIN_OVERLAP = 24

# Canadian sleeves holding foreign assets, where hedging changes the return a lot
# (the 2008 crisis: S&P 500 hedged to CAD about -52%, unhedged in CAD about -35%).
FX_SLEEVES = {"ca_us_equity", "ca_us_equity_hedged", "ca_intl_equity", "ca_em_equity", "ca_gold"}


def proxies_for(sleeve: str, hedged: bool, listing_hedged) -> list[tuple[str, bool]]:
    """Proxies matched to the fund's currency exposure, not only to its sleeve.

    A fund hedged to CAD earns roughly the foreign asset's own-currency return, so its
    stand-in is the US-listed fund unconverted, or a hedged Canadian listing. An unhedged
    fund earns that return converted to CAD, so its stand-in is the US-listed fund
    converted, or an unhedged Canadian listing. ``listing_hedged(ticker)`` says whether a
    Canadian-listed proxy is hedged. Correlation alone cannot tell the two apart: hedged
    and unhedged S&P 500 moved together at 0.87 over 2012-2026.
    """
    if sleeve not in FX_SLEEVES:
        return list(PROXIES.get(sleeve, []))
    key = sleeve
    if sleeve == "ca_us_equity" and hedged:
        key = "ca_us_equity_hedged"
    elif sleeve == "ca_us_equity_hedged" and not hedged:
        key = "ca_us_equity"
    out = []
    for t, _ in PROXIES.get(key, []):
        if t.endswith((".TO", ".NE")):
            if bool(listing_hedged(t)) == bool(hedged):
                out.append((t, False))
        else:
            out.append((t, not hedged))
    return out


def rate_returns(context: pd.DataFrame, column: str) -> pd.Series:
    """Monthly return of holding 3-month bills: last month's annual yield / 12."""
    y = context[column].dropna() / 100.0
    return (y.shift(1) / 12.0).dropna().rename(f"RATE:{column}")


def splice(
    series: pd.Series, proxies: list[tuple[str, bool]], R: pd.DataFrame, fx_r: pd.Series, context: pd.DataFrame, is_cash: bool = False
) -> tuple[pd.Series, list[dict]]:
    """Extend ``series`` backwards with the proxies, in order. Returns (series, splice notes)."""
    s = series.dropna().copy()
    notes = []
    for tick, convert in proxies:
        if s.empty:
            break
        if tick.startswith("RATE:"):
            p = rate_returns(context, tick.split(":", 1)[1])
        elif tick in R.columns:
            p = R[tick].dropna()
            if convert:
                p = ((1 + p) * (1 + fx_r.reindex(p.index)) - 1).dropna()
        else:
            continue
        first = s.index.min()
        before = p[p.index < first]
        if before.empty:
            continue
        overlap = pd.concat([s, p], axis=1, join="inner").dropna()
        if not is_cash and not tick.startswith("RATE:"):
            if len(overlap) < MIN_OVERLAP:
                continue
            corr = float(overlap.corr().iloc[0, 1])
            if corr < MIN_CORR:
                notes.append({"proxy": tick, "used": False, "why": f"correlation {corr:.2f} below {MIN_CORR}"})
                continue
        else:
            corr = float(overlap.corr().iloc[0, 1]) if len(overlap) > 2 else float("nan")
        s = pd.concat([before, s]).sort_index()
        notes.append(
            {
                "proxy": tick.replace("RATE:", "rate "),
                "used": True,
                "from": str(before.index.min().date()),
                "to": str(before.index.max().date()),
                "months": int(len(before)),
                "converted_to_cad": bool(convert),
                "overlap_corr": None if np.isnan(corr) else round(corr, 3),
            }
        )
    return s, notes


def backfill_regressors(core: pd.DataFrame, gap_months: int = 36) -> list[str]:
    """Core funds used to back-fill a young satellite. A core fund whose history starts more than ``gap_months`` after
    every other core fund is left out, so one short series (BNDX starts 2013-07) cannot cut every satellite's history
    short of 2008 (RESEARCH_LOG section 8, item 6)."""
    starts = {c: core[c].first_valid_index() for c in core.columns}
    keep = [c for c in core.columns if starts[c] is not None]
    while len(keep) > 2:
        order = sorted(keep, key=lambda c: starts[c])
        last, prev = order[-1], order[-2]
        gap = (starts[last].year - starts[prev].year) * 12 + (starts[last].month - starts[prev].month)
        if gap <= gap_months:
            break
        keep.remove(last)
    return keep


def backfill_by_regression(target: pd.Series, core: pd.DataFrame, seed: int = 11) -> tuple[pd.Series, dict | None]:
    """Fill months before ``target`` starts using OLS on the core funds plus a resampled residual."""
    t = target.dropna()
    missing = core.index[(core.index < t.index.min()) & core.notna().all(axis=1)]
    if len(missing) == 0:
        return t, None
    ov = pd.concat([t, core], axis=1, join="inner").dropna()
    if len(ov) < 36:
        return t, None
    y = ov.iloc[:, 0].to_numpy()
    X = np.column_stack([np.ones(len(ov)), ov.iloc[:, 1:].to_numpy()])
    # ridge-lite: a tiny penalty keeps the fit stable when core funds are collinear
    lam = 1e-4 * np.trace(X.T @ X) / X.shape[1]
    beta = np.linalg.solve(X.T @ X + lam * np.eye(X.shape[1]), X.T @ y)
    resid = y - X @ beta
    # residual for the k-th missing month: a fixed stride through the fitted residuals
    # (deterministic and identical in the JavaScript port; it spreads the draws over the sample)
    # (k counts back from the month before the fund starts, so a longer core history adds months
    # at the far end without changing the ones already filled)
    n, m = len(resid), len(missing)
    picks = np.array([resid[((m - 1 - j) * 7919 + seed) % n] for j in range(m)])
    Xm = np.column_stack([np.ones(len(missing)), core.loc[missing].to_numpy()])
    fill = Xm @ beta + picks
    r2 = 1 - resid.var() / y.var() if y.var() > 0 else 0.0
    out = pd.concat([pd.Series(fill, index=missing), t]).sort_index()
    return out, {
        "method": "regression on core funds + residual from its own history",
        "months": int(len(missing)),
        "from": str(missing.min().date()),
        "to": str(missing.max().date()),
        "r2": round(float(r2), 3),
    }
