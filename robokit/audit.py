"""E6, E7 and E8 of the pre-registered v3 evaluation (docs/RESEARCH_LOG.md section 10): the production rebalancer on
a simulated account, audits of the data and input rules, and hold-out tests of the stand-in histories and back-fills.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import engine as E
from . import universe as UV
from .config import MIN_AUM, MIN_DOLLAR_VOLUME, MIN_HISTORY_MONTHS
from .data.prices import monthly_returns
from .engine import Request, returns_in, select_funds
from .history import backfill_by_regression, backfill_regressors, proxies_for
from .rebalance import rebalance
from .stress import SCENARIOS


# ------------------------------------------------------------------ E6: the rebalancer on a simulated account
def account_path(
    targets: dict, prices: pd.DataFrame, start_value: float, flow: float, rule: str, min_trade: float = 50.0, cost_bps: float = 10.0
) -> dict:
    """Run an account month by month at month-end prices. ``targets``: {date: {ticker: weight}} (each in force from the
    month after its date). rule: 'ideal' (fractional, back to target every month: the walk-forward's assumption),
    'monthly' (the production rebalancer with no band: back to target every month, whole units), 'bands' (the
    production rebalancer as shipped), 'annual' (the production rebalancer back to target each January, otherwise new
    money only). Returns monthly time-weighted returns and the trading record."""
    targets = {pd.Timestamp(d): w for d, w in targets.items()}
    dates = sorted(targets)
    months = prices.index[(prices.index > dates[0])]
    tick = list(prices.columns)
    units = {t: 0.0 for t in tick}
    cash = start_value
    v_prev = start_value
    rows = []
    for m in months:
        tgt_date = max(d for d in dates if d < m)
        tgt = {t: float(targets[tgt_date].get(t, 0.0)) for t in tick}
        s = sum(tgt.values())
        tgt = {t: v / s for t, v in tgt.items()}
        px = {t: float(prices.at[m, t]) for t in tick}
        held = sum(units[t] * px[t] for t in tick)
        v_before = held + cash
        r = v_before / v_prev - 1 if v_prev > 0 else 0.0
        drift = max(abs((units[t] * px[t] / held if held > 0 else 0.0) - tgt[t]) for t in tick) if held > 0 else None
        if rule == "ideal":  # fractional, exactly back to target, cost on the traded amount
            total = v_before + flow
            new = {t: tgt[t] * total / px[t] for t in tick}
            traded = sum(abs(new[t] - units[t]) * px[t] for t in tick)
            cost = traded * cost_bps / 1e4
            units = {t: new[t] * (1 - cost / total) for t in tick}
            cash = 0.0
            orders = skipped = 0
        else:
            if rule == "monthly":
                kw = {"band_abs": 0.0, "band_rel": 0.0, "destination": 0.0}
            elif rule == "annual":
                kw = {"band_abs": 0.0, "band_rel": 0.0, "destination": 0.0} if m.month == 1 else {"band_abs": 1.0, "band_rel": 1.0}
            else:
                kw = {}
            res = rebalance(
                tgt, {t: u for t, u in units.items() if u > 0}, px, cash=cash, flow=flow, min_trade=min_trade, cost_bps=cost_bps, **kw
            )
            for row in res["rows"]:
                units[row["ticker"]] = row["units_after"]
            cash = res["cash_after"]
            traded = res["traded"]
            cost = res["estimated_cost"]
            orders = sum(1 for row in res["rows"] if row["action"] != "hold")
            skipped = sum(1 for row in res["rows"] if "under the minimum trade" in row["reason"])
        v_after = sum(units[t] * px[t] for t in tick) + cash
        rows.append(
            {
                "month": m,
                "return": r,
                "value": v_after,
                "traded": traded,
                "cost": cost,
                "orders": orders,
                "skipped": skipped,
                "cash_share": cash / v_after if v_after > 0 else 0.0,
                "max_drift": drift,
            }
        )
        v_prev = v_after
    df = pd.DataFrame(rows).set_index("month")
    return {"path": df}


def summarise_account(df: pd.DataFrame, ideal: pd.DataFrame | None) -> dict:
    r = df["return"].iloc[1:]
    out = {
        "months": int(len(r)),
        "ann_return": float(np.prod(1 + r) ** (12 / len(r)) - 1),
        "ann_vol": float(r.std(ddof=1) * math.sqrt(12)),
        "total_cost": float(df["cost"].sum()),
        "orders": int(df["orders"].sum()),
        "skipped_orders": int(df["skipped"].sum()),
        "mean_cash_share": float(df["cash_share"].mean()),
        "mean_max_drift": float(df["max_drift"].dropna().mean()) if df["max_drift"].notna().any() else None,
        "annual_turnover": float((df["traded"] / df["value"]).sum() / 2 / (len(df) / 12)),
    }
    if ideal is not None:
        d = (r - ideal["return"].reindex(r.index)).dropna()
        out["tracking_error_vs_ideal"] = float(d.std(ddof=1) * math.sqrt(12))
        out["return_gap_vs_ideal"] = out["ann_return"] - float(
            np.prod(1 + ideal["return"].iloc[1:]) ** (12 / len(ideal["return"].iloc[1:])) - 1
        )
    return out


def own_prices(market: str, tickers: list[str]) -> pd.DataFrame:
    """Month-end adjusted closes (dividends reinvested in the price) in the portfolio currency, from the month every
    fund has one."""
    U, R, fx, _ = E._load_all()
    X = returns_in(market, tickers).dropna(how="any")
    return 100.0 * (1 + X).cumprod()


# ------------------------------------------------------------------ E7: data and input rules
def jump_screen_at(threshold_log: float) -> dict:
    """The data-integrity screen with another threshold: the funds it would flag, with month and peer move."""
    U, R, _, _ = E._load_all()
    why = U["excluded_because"].fillna("")
    cand = (why == "") | why.str.startswith("its price history moved")  # as universe.build_universe: every other screen passed
    old = UV.JUMP_LOG
    UV.JUMP_LOG = threshold_log
    try:
        flagged = UV.price_jumps(R, U, cand)
    finally:
        UV.JUMP_LOG = old
    return {t: {"month": str(pd.Timestamp(v[0]).date()), "return": float(v[1]), "peer_median": float(v[2])} for t, v in flagged.items()}


def crisis_standin_holdout() -> list[dict]:
    """For every eligible fund with its own data through an episode: its episode return against the peer-median
    stand-in the replay would have used without it (same class, region and market; itself left out)."""
    U, R, _, _ = E._load_all()
    meta = U.set_index("yahoo")
    rows = []
    for sc in SCENARIOS:
        s, e = pd.Timestamp(sc["start"]), pd.Timestamp(sc["end"])
        win = R.loc[(R.index > s) & (R.index <= e)]
        if win.empty:
            continue
        full = win.notna().all()
        ep = (1 + win.fillna(0)).prod() - 1
        have = [t for t in meta.index[meta.eligible] if t in win.columns and bool(full.get(t, False))]
        for t in have:
            ac, rg, mk = meta.at[t, "asset_class"], meta.at[t, "region"], meta.at[t, "market"]
            peers = [
                p for p in have if p != t and meta.at[p, "asset_class"] == ac and meta.at[p, "region"] == rg and meta.at[p, "market"] == mk
            ]
            if len(peers) < 3:
                continue
            rows.append(
                {
                    "episode": sc["key"],
                    "ticker": t,
                    "asset_class": ac,
                    "actual": float(ep[t]),
                    "standin": float(np.median(ep[peers])),
                    "peers": len(peers),
                }
            )
    return rows


def liquidity_margins(market: str) -> list[dict]:
    """How far each reference fund is above each liquidity screen (multiples of the floor)."""
    U, R, _, _ = E._load_all()
    meta = U.set_index("yahoo")
    shelf, core, _ = select_funds(Request(market=market))
    out = []
    for t in core:
        m = meta.loc[t]
        out.append(
            {
                "ticker": t,
                "aum_multiple": float(m["aum"] / MIN_AUM[market]) if pd.notna(m["aum"]) else None,
                "volume_multiple": float(m["dollar_volume"] / MIN_DOLLAR_VOLUME[market])
                if "dollar_volume" in m and pd.notna(m["dollar_volume"])
                else None,
                "history_multiple": float(m["history_months"] / MIN_HISTORY_MONTHS) if pd.notna(m["history_months"]) else None,
            }
        )
    return out


def crisis_episode_rule(market: str, threshold: float = -0.15) -> list[dict]:
    """Every peak-to-trough fall of the home stock fund (extended history) deeper than ``threshold`` since 2000, and
    whether a crisis replay covers it."""
    shelf, core, _ = select_funds(Request(market=market))
    home = shelf.loc[shelf.sleeve == ("ca_equity" if market == "CA" else "us_equity"), "ticker"].iloc[0]
    _, full, _ = E.build_returns(market, shelf, core, [])
    r = full[home].dropna()
    w = (1 + r).cumprod()
    out, peak_val, peak_date, trough = [], w.iloc[0], w.index[0], None
    in_dd = False
    for d, v in w.items():
        if v >= peak_val:
            if in_dd and trough is not None and trough[1] / peak_val - 1 <= threshold:
                out.append((peak_date, trough[0], trough[1] / peak_val - 1))
            peak_val, peak_date, trough, in_dd = v, d, None, False
        else:
            in_dd = True
            if trough is None or v < trough[1]:
                trough = (d, v)
    if in_dd and trough is not None and trough[1] / peak_val - 1 <= threshold:
        out.append((peak_date, trough[0], trough[1] / peak_val - 1))
    rows = []
    for p, t, dd in out:
        cover = [sc["key"] for sc in SCENARIOS if pd.Timestamp(sc["start"]) <= t and pd.Timestamp(sc["end"]) >= p - pd.offsets.MonthEnd(3)]
        rows.append({"fund": home, "peak": str(p.date()), "trough": str(t.date()), "fall": float(dd), "covered_by": cover})
    return rows


# ------------------------------------------------------------------ E8: hold-out tests of extended histories
def standin_holdout(market: str) -> list[dict]:
    """Each reference fund against each of its written stand-ins over the months both have their own data."""
    U, R, _, _ = E._load_all()
    hedged = dict(zip(U.yahoo, U.hedged.astype(bool)))
    shelf, core, _ = select_funds(Request(market=market))
    rows = []
    for _, row in shelf.iterrows():
        t = row.ticker
        for p, _conv in proxies_for(row.sleeve, hedged.get(t, False), lambda x: hedged.get(x, False)):
            if p.startswith("RATE:") or p not in R.columns:
                continue
            X = returns_in(market, [t, p]).dropna(how="any")
            if len(X) < 24:
                continue
            a, b = X[t].to_numpy(), X[p].to_numpy()
            rows.append(
                {
                    "fund": t,
                    "standin": p,
                    "months": int(len(X)),
                    "correlation": float(np.corrcoef(a, b)[0, 1]),
                    "tracking_error": float(np.std(a - b, ddof=1) * math.sqrt(12)),
                    "vol_ratio": float(np.std(b, ddof=1) / np.std(a, ddof=1)),
                    "mean_gap_annual": float((b.mean() - a.mean()) * 12),
                }
            )
    return rows


def backfill_holdout(market: str, n_funds: int = 20, masked: int = 60) -> list[dict]:
    """Mature own-pick candidates with their first ``masked`` months hidden and back-filled by the regression the
    engine uses, against the hidden truth; the home stock fund (beta one) as the simple alternative."""
    U, R, _, _ = E._load_all()
    shelf, core, _ = select_funds(Request(market=market))
    _, full, _ = E.build_returns(market, shelf, core, [])
    core_full = full[backfill_regressors(full[core])].dropna(how="any")
    home = shelf.loc[shelf.sleeve == ("ca_equity" if market == "CA" else "us_equity"), "ticker"].iloc[0]
    pool = U[(U.market == market) & U.eligible & (U.asset_class == "Equity") & ~U.yahoo.isin(core) & (U.history_months >= masked + 120)]
    pool = pool.sort_values("aum", ascending=False).yahoo.head(n_funds)
    rows = []
    for t in pool:
        s = returns_in(market, [t])[t].dropna()
        s = s[s.index.isin(core_full.index)]
        if len(s) < masked + 60:
            continue
        hidden = s.iloc[:masked]
        filled, _ = backfill_by_regression(s.iloc[masked:], core_full.loc[: s.index[-1]])
        f = filled.reindex(hidden.index)
        ok = f.notna()
        if ok.sum() < 24:
            continue
        a, b = hidden[ok].to_numpy(), f[ok].to_numpy()
        h = full[home].reindex(hidden.index)[ok].to_numpy()
        rows.append(
            {
                "fund": t,
                "months": int(ok.sum()),
                "correlation": float(np.corrcoef(a, b)[0, 1]),
                "vol_ratio": float(np.std(b, ddof=1) / np.std(a, ddof=1)),
                "tracking_error": float(np.std(a - b, ddof=1) * math.sqrt(12)),
                "home_fund_tracking_error": float(np.std(a - h, ddof=1) * math.sqrt(12)),
                "home_fund_correlation": float(np.corrcoef(a, h)[0, 1]),
            }
        )
    return rows


__all__ = [
    "account_path",
    "summarise_account",
    "own_prices",
    "jump_screen_at",
    "crisis_standin_holdout",
    "liquidity_margins",
    "crisis_episode_rule",
    "standin_holdout",
    "backfill_holdout",
    "monthly_returns",
]
