"""Historical stress tests: what would this mix have done in past crises?

A stress test replays a real episode on today's weights (buy and hold over
the episode, no rebalancing). Funds that did not exist yet are stood in for
by the median fund of the same asset class and region that did, and the
result says which funds were stood in for. Month-end data, so intra-month
lows are deeper than what is shown.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SCENARIOS = [
    {
        "key": "gfc",
        "name": "2008 financial crisis",
        "start": "2007-11-30",
        "end": "2009-02-28",
        "what": "Banks failed, credit froze and stock markets fell by about half.",
    },
    {
        "key": "euro",
        "name": "2011 euro debt crisis",
        "start": "2011-04-30",
        "end": "2011-09-30",
        "what": "Fears that Greece, Italy and Spain could not repay their debts.",
    },
    {
        "key": "oil",
        "name": "2014-16 oil crash",
        "start": "2014-06-30",
        "end": "2016-01-31",
        "what": "Oil fell from over $100 to under $30; hard on Canadian energy and the loonie.",
    },
    {
        "key": "q4_2018",
        "name": "Late-2018 sell-off",
        "start": "2018-09-30",
        "end": "2018-12-31",
        "what": "Rate hikes and trade-war worries.",
    },
    {
        "key": "covid",
        "name": "2020 COVID crash",
        "start": "2020-01-31",
        "end": "2020-03-31",
        "what": "Economies shut down; the fastest bear market on record.",
    },
    {
        "key": "rates_2022",
        "name": "2022 inflation and rate shock",
        "start": "2021-12-31",
        "end": "2022-10-31",
        "what": "Stocks and bonds fell together as central banks raised rates quickly.",
    },
    {
        "key": "tariffs_2025",
        "name": "2025 tariff shock",
        "start": "2025-01-31",
        "end": "2025-04-30",
        "what": "Sweeping US tariff announcements and retaliation.",
    },
]


def standin_peers(meta: pd.DataFrame, t: str, available) -> tuple[list[str], str]:
    """The funds whose median episode return stands in for ``t``: eligible funds among ``available`` (those with data
    through the whole episode) of the same asset class, region and market; if there are none, of the same asset class
    anywhere. The replay uses it, and so does its hold-out test (robokit/audit.py), with the fund itself left out.
    Returns the peers and the rule that found them."""
    if t not in meta.index:
        return [], "none"
    ac, rg, mk = meta.at[t, "asset_class"], meta.at[t, "region"], meta.at[t, "market"]
    pool = meta[meta.eligible & meta.index.isin(list(available))]
    peers = list(pool[(pool.asset_class == ac) & (pool.region == rg) & (pool.market == mk)].index)
    if peers:
        return peers, "class, region and market"
    peers = list(pool[pool.asset_class == ac].index)
    return peers, ("class" if peers else "none")


def scenario_returns(returns_full: pd.DataFrame, universe: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Episode return per fund (rows: scenarios, columns: tickers) and a proxied flag frame."""
    meta = universe.set_index("yahoo")
    out, proxied = {}, {}
    for sc in SCENARIOS:
        s, e = pd.Timestamp(sc["start"]), pd.Timestamp(sc["end"])
        win = returns_full.loc[(returns_full.index > s) & (returns_full.index <= e)]
        if win.empty:
            continue
        full = win.notna().all()
        ep = (1 + win.fillna(0)).prod() - 1
        row, prow = {}, {}
        for t in tickers:
            if t in win.columns and bool(full.get(t, False)):
                row[t], prow[t] = float(ep[t]), False
                continue
            peers, _ = standin_peers(meta, t, set(full.index[full]) - {t})
            row[t] = float(np.median(ep[peers])) if peers else np.nan
            prow[t] = True
        out[sc["key"]], proxied[sc["key"]] = row, prow
    return pd.DataFrame(out).T, pd.DataFrame(proxied).T


def stress_test(
    weights: pd.Series, returns_full: pd.DataFrame, universe: pd.DataFrame, amount: float = 10_000.0, first_month: dict | None = None
) -> list[dict]:
    """One row per episode: the mix's return and its dollar change on ``amount``. ``estimated`` lists funds
    that did not exist yet, whose episode return comes from their disclosed splice or back-fill; ``stand_ins``
    lists funds with no extended history, replaced by the median peer."""
    w = weights[weights > 0]
    R, P = scenario_returns(returns_full, universe, list(w.index))
    first_month = first_month or {}
    res = []
    for sc in SCENARIOS:
        if sc["key"] not in R.index:
            continue
        r = R.loc[sc["key"], w.index]
        stand = [t for t in w.index if bool(P.loc[sc["key"], t])]
        first_in_window = str((pd.Timestamp(sc["start"]) + pd.offsets.MonthEnd(1)).date())
        row = {"key": sc["key"], "scenario": sc["name"], "from": sc["start"], "to": sc["end"], "what": sc["what"]}
        missing = [t for t in w.index if pd.isna(r[t])]
        if missing:  # never drop an episode silently: keep the row and name the funds with no history or stand-in
            res.append(
                {
                    **row,
                    "portfolio_return": None,
                    "dollars": None,
                    "worst_fund": None,
                    "worst_fund_return": None,
                    "stand_ins": [t for t in stand if t not in missing],
                    "estimated": [],
                    "not_estimable": missing,
                }
            )
            continue
        pr = float((w * r).sum())
        res.append(
            {
                **row,
                "portfolio_return": round(pr, 4),
                "dollars": round(pr * amount),
                "worst_fund": str(r.idxmin()),
                "worst_fund_return": round(float(r.min()), 4),
                "stand_ins": stand,
                "estimated": [t for t in w.index if t not in stand and first_month.get(t) and first_month[t] > first_in_window],
                "not_estimable": [],
            }
        )
    return res
