"""Recompute, with separate code, the values the pipeline derives from its stored data, and compare:
1. per-fund statistics in universe.pkl (history months, 1/3/5-year returns, 3-year volatility, maximum drawdown);
2. the Bank of Canada series in context_monthly.pkl against a fresh download from the Valet API;
3. the eligibility screen, re-implemented from the written thresholds.
"""

import json
import math
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
D = REPO / "data" / "v2"
U = pd.read_pickle(D / "universe.pkl").set_index("yahoo")
close = pd.read_pickle(D / "close_monthly.pkl")


# 1. statistics, computed fund by fund with plain loops over the stored month-end closes
def window(by_month, n):
    return [by_month.get(m) for m in close.index[-n:]]


def ann_ret(by_month, n):
    w = window(by_month, n)
    if any(x is None for x in w):
        return np.nan
    g = 1.0
    for x in w:
        g *= 1 + x
    return g ** (12 / n) - 1


def vol(by_month, n):
    w = [x for x in window(by_month, n) if x is not None]
    if len(w) < int(0.9 * n):
        return np.nan
    m = sum(w) / len(w)
    return math.sqrt(sum((x - m) ** 2 for x in w) / (len(w) - 1)) * math.sqrt(12)


rows = []
for t in U.index[U.has_prices]:
    s = close[t]
    rets = []  # (month, return) only where this month and the previous one both have a close
    vals = s.values
    for i in range(1, len(vals)):
        if not (math.isnan(vals[i]) or math.isnan(vals[i - 1])):
            rets.append((s.index[i], vals[i] / vals[i - 1] - 1))
    by_month = dict(rets)
    peak, wealth, mdd = 1.0, 1.0, 0.0
    for m in close.index:
        x = by_month.get(m)
        if x is None:
            continue  # a gap leaves wealth unchanged, as the pipeline's fillna(0) does
        wealth *= 1 + x
        peak = max(peak, wealth)
        mdd = min(mdd, wealth / peak - 1)
    rows.append(
        dict(
            yahoo=t,
            history_months=len(rets),
            ret_1y=ann_ret(by_month, 12),
            ret_3y=ann_ret(by_month, 36),
            ret_5y=ann_ret(by_month, 60),
            vol_3y=vol(by_month, 36),
            max_drawdown=mdd if rets else np.nan,
        )
    )
R = pd.DataFrame(rows).set_index("yahoo")
print("1. statistics recomputed for", len(R), "funds with prices")
for c in R.columns:
    a, b = U.loc[R.index, c].astype(float), R[c].astype(float)
    both = a.notna() & b.notna()
    mism = ((a - b).abs() > 1e-9) & both
    only = a.notna() != b.notna()
    print(
        f"   {c:<15} compared {int(both.sum()):>5}  max abs diff {float((a - b)[both].abs().max()):.2e}  mismatches {int(mism.sum())}  present on one side only {int(only.sum())}"
    )

# 2. Bank of Canada series: stored month-end values against a fresh Valet download
ctx = pd.read_pickle(D / "context_monthly.pkl")
for code in ("V39079", "V80691344", "BD.CDN.2YR.DQ.YLD", "BD.CDN.10YR.DQ.YLD"):
    u = f"https://www.bankofcanada.ca/valet/observations/{code}/json?start_date=2000-01-01&end_date=2026-09-30"
    j = json.load(urllib.request.urlopen(u, timeout=60))
    s = pd.Series(
        {pd.Timestamp(o["d"]): float(o[code]["v"]) for o in j["observations"] if o.get(code) and o[code].get("v") not in (None, "")}
    )
    me = s.resample("ME").last()
    both = ctx[code].notna() & me.reindex(ctx.index).notna()
    d = (ctx[code] - me.reindex(ctx.index))[both].abs()
    print(
        f"2. {code:<20} months {int(both.sum()):>4}  max abs diff {d.max():.4f}  months differing {int((d > 1e-9).sum())}"
        + (f" (latest: {d[d > 1e-9].index.max().date()})" if (d > 1e-9).any() else "")
    )

# 3. eligibility, re-implemented from the thresholds written in robokit/config.py and the screen's reasons
cfg = {"MIN_HISTORY": 36, "MIN_AUM": {"CA": 20e6, "US": 50e6}, "MIN_DV": {"CA": 50e3, "US": 250e3}}
last = close.index[-1]
ok = (
    ~U.cdr.astype(bool)
    & (U.leverage == 1.0)
    & ~U.single_stock.astype(bool)
    & ~((U.market == "CA") & (U.currency == "USD"))
    & U.has_prices
    & (U.history_months >= cfg["MIN_HISTORY"])
    & (pd.to_datetime(U.last_month) >= last)
    & ~(U.aum.notna() & (U.aum < U.market.map(cfg["MIN_AUM"])))
    & ~(U.dollar_volume.notna() & (U.dollar_volume < U.market.map(cfg["MIN_DV"])))
    & ~(U.aum.isna() & U.dollar_volume.isna())
)
jump = U.excluded_because.fillna("").str.contains("price history moved")
mine = ok & ~jump
diff = mine != U.eligible
print(
    f"3. eligibility re-implemented: {int(mine.sum())} eligible ({int(mine[U.market == 'CA'].sum())} CA, {int(mine[U.market == 'US'].sum())} US); "
    f"differs from the pipeline for {int(diff.sum())} funds; price-jump exclusions {int(jump.sum())}"
)
if diff.any():
    print(U.loc[diff, ["name", "eligible", "excluded_because"]].head(20).to_string())
