"""Walk-forward back-test of the v2 engine on the reference shelf (pre-registered in docs/RESEARCH_LOG.md section 6).

Every number this produces is hypothetical: it is what the rules would have
done with data available at each date, after trading costs, on funds chosen
with today's information. The product shows it labelled that way.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from optimizer import RoboKitOptimizer
from optimizer.backtest import _hold, paired_comparison
from optimizer.data import max_drawdown

from . import profile as prof
from .config import DELTA
from .engine import SLEEVE_CAPS, Request, build_returns, select_funds
from .shelf import prior_share
from .views import bound_tilt

IC = 0.05


def _calibrated(opt, target, caps, cash_t, lvl10, resample, n_boot, seed=0):
    def vol(lam):
        return opt.optimize(float(lam), resample=False, caps=caps).exp_vol

    lo, hi = 0.05, 2000.0
    if target >= vol(lo):
        lam = lo
    elif target <= vol(hi):
        lam = hi
    else:
        for _ in range(35):
            mid = float(np.sqrt(lo * hi))
            if vol(mid) > target:
                lo = mid
            else:
                hi = mid
            if hi / lo < 1.003:
                break
        lam = float(np.sqrt(lo * hi))
    return lam, opt.optimize(lam, resample=resample, n_boot=n_boot, seed=seed, caps=caps).weights


def _trend_views(win: pd.DataFrame, opt, tickers, cash_t):
    P, Q, om = [], [], []
    sig = opt.sigma.to_numpy()
    for i, t in enumerate(tickers):
        if t == cash_t:
            continue
        r = win[t]
        if len(r) < 13:
            continue
        mom = float((1 + r.iloc[-13:-1]).prod() - 1)
        s_ann = float(r.std() * np.sqrt(12))
        z = float(np.clip(mom / s_ann, -2, 2)) if s_ann > 0 else 0.0
        p = np.zeros(len(tickers))
        p[i] = 1.0
        P.append(p)
        Q.append(float(opt.mu_excess.iloc[i]) + np.sqrt(sig[i, i]) * IC * z)
        om.append(0.05 * float(p @ sig @ p))  # 50% confidence: alpha = 1
    return np.vstack(P), np.array(Q), np.diag(om)


def walk_forward(
    market: str,
    levels=(2, 3, 4),
    window: int = 60,
    step: int = 12,
    cost_bps: float = 10.0,
    n_boot: int = 50,
    strategies=("robokit", "robokit_trend", "static_mix", "sample_mvo", "equal_weight"),
    max_rebalances: int | None = None,
) -> dict:
    """``max_rebalances`` limits the run for smoke tests of the code (not for results)."""
    shelf, core, _ = select_funds(Request(market=market))
    _, X, hist = build_returns(market, shelf, core, [])
    X = X[core].dropna(how="any")
    tickers = list(X.columns)
    prior = pd.Series(0.0, index=tickers)
    for _, row in shelf.iterrows():
        prior[row.ticker] += prior_share(market, row.sleeve)
    prior = prior / prior.sum()
    cash_t = shelf.loc[shelf.role == "cash", "ticker"].iloc[0]
    sleeve_caps = {row.ticker: SLEEVE_CAPS[row.sleeve] for _, row in shelf.iterrows() if row.sleeve in SLEEVE_CAPS}
    eq = [row.ticker for _, row in shelf.iterrows() if row.asset_class == "Equity"]
    fi = [row.ticker for _, row in shelf.iterrows() if row.asset_class == "Fixed income"]
    cost = cost_bps / 1e4

    monthly, weights_log, targets, prev_target = {}, [], {}, {}
    starts = list(range(window, len(X), step))
    if max_rebalances:
        starts = starts[:max_rebalances]
    for start in starts:
        win = X.iloc[start - window : start]
        hold = X.iloc[start : start + step]
        if hold.empty:
            break
        eq_w = prior[eq] / prior[eq].sum()
        eq_vol = float((win[eq].to_numpy() @ eq_w.to_numpy()).std(ddof=1) * np.sqrt(12))
        opt = RoboKitOptimizer(win, rf=0.0, prior_weights=prior, delta=DELTA, w_max=0.5, cash_ticker=cash_t, cash_max=1.0).fit()
        opt_s = RoboKitOptimizer(
            win, rf=0.0, prior_weights=prior, delta=DELTA, w_max=0.5, cash_ticker=cash_t, cash_max=1.0, mu_method="sample"
        ).fit()
        for lvl in levels:
            lvl10 = prof.engine_level(lvl)
            target = prof.risk_share(lvl10) * eq_vol
            caps = dict(sleeve_caps)
            if prof.cash_cap(lvl10) < 1:
                caps[cash_t] = prof.cash_cap(lvl10)
            ws = {}
            if "robokit" in strategies or "robokit_trend" in strategies:
                lam, w = _calibrated(opt, target, caps, cash_t, lvl10, True, n_boot)
                ws["robokit"] = w.reindex(tickers).fillna(0.0)
                if "robokit_trend" in strategies:
                    P, Q, om = _trend_views(win, opt, tickers, cash_t)
                    opt_v = RoboKitOptimizer(
                        win,
                        rf=0.0,
                        prior_weights=prior,
                        delta=DELTA,
                        w_max=0.5,
                        cash_ticker=cash_t,
                        cash_max=1.0,
                        mu_method="black_litterman",
                        views={"P": P, "Q": Q, "tau": 0.05, "omega": om},
                    ).fit()
                    _, wv = _calibrated(opt_v, target, caps, cash_t, lvl10, True, n_boot)
                    wb, _ = bound_tilt(ws["robokit"], wv.reindex(tickers).fillna(0.0), opt.sigma.to_numpy())
                    ws["robokit_trend"] = wb
            if "static_mix" in strategies:
                s = prof.risk_share(lvl10)
                w = pd.Series(0.0, index=tickers)
                w[eq] = s * prior[eq] / prior[eq].sum()
                w[fi] = (1 - s) * prior[fi] / prior[fi].sum()
                ws["static_mix"] = w
            if "sample_mvo" in strategies:
                _, w = _calibrated(opt_s, target, caps, cash_t, lvl10, False, 0)
                ws["sample_mvo"] = w.reindex(tickers).fillna(0.0)
            if "equal_weight" in strategies:
                w = pd.Series(1.0, index=tickers)
                w[cash_t] = 0.0
                ws["equal_weight"] = w / w.sum()
            for name, w in ws.items():
                key = f"{name}|{lvl}"
                g, n, t = _hold(hold, w.to_numpy(), cost)
                # moving from last year's target to this year's is traded too (pre-registered: cost on all turnover)
                reb = 0.5 * float(np.abs(w.to_numpy() - prev_target[key]).sum()) if key in prev_target else 0.0
                n[0] -= cost * reb
                t[0] += reb
                prev_target[key] = w.to_numpy().copy()
                monthly.setdefault(key, []).append(pd.DataFrame({"gross": g, "net": n, "turn": t}, index=hold.index))
                weights_log.append(
                    {"date": str(win.index[-1].date()), "strategy": name, "level": lvl, **{k: round(float(v), 4) for k, v in w.items()}}
                )
                targets[(name, lvl, str(win.index[-1].date()))] = target

    series = {k: pd.concat(v) for k, v in monthly.items()}
    net = pd.DataFrame({k: v["net"] for k, v in series.items()})
    gross = pd.DataFrame({k: v["gross"] for k, v in series.items()})
    cash_r = X[cash_t].reindex(net.index)
    rows = []
    for col in net.columns:
        name, lvl = col.split("|")
        r = net[col].dropna()
        ann = float((1 + r).prod() ** (12 / len(r)) - 1)
        vol = float(r.std(ddof=1) * np.sqrt(12))
        cash_ann = float((1 + cash_r.loc[r.index]).prod() ** (12 / len(r)) - 1)
        g = gross[col].dropna()
        gann = float((1 + g).prod() ** (12 / len(g)) - 1)
        tv = np.mean([v for (n_, l_, _), v in targets.items() if n_ == name and l_ == int(lvl)])
        rows.append(
            {
                "strategy": name,
                "level": int(lvl),
                "ann_return": ann,
                "ann_vol": vol,
                "sharpe_vs_cash": (ann - cash_ann) / vol if vol > 0 else np.nan,
                "max_drawdown": max_drawdown(r),
                "avg_target_vol": tv,
                "cost_drag": gann - ann,
                "monthly_turnover": float(series[col]["turn"].mean()),
                "n_months": len(r),
                "from": str(r.index.min().date()),
                "to": str(r.index.max().date()),
            }
        )
    stats = pd.DataFrame(rows).sort_values(["level", "strategy"])
    sub = []
    for label, (a, b) in {"2020": ("2020-01-31", "2020-12-31"), "2022": ("2022-01-31", "2022-12-31")}.items():
        chunk = net.loc[a:b]
        for col in chunk.columns:
            name, lvl = col.split("|")
            sub.append({"period": label, "strategy": name, "level": int(lvl), "return": float((1 + chunk[col]).prod() - 1)})
    pairs = []
    for lvl in levels:
        for other in [s for s in strategies if s != "robokit"]:
            if f"robokit|{lvl}" in net and f"{other}|{lvl}" in net:
                pc = paired_comparison(net, f"robokit|{lvl}", f"{other}|{lvl}")
                pairs.append({"level": lvl, "vs": other, **pc})
        if f"robokit_trend|{lvl}" in net:
            pc = paired_comparison(net, f"robokit_trend|{lvl}", f"robokit|{lvl}")
            pairs.append({"level": lvl, "vs": "robokit (trend minus base)", **pc})
    return {
        "market": market,
        "tickers": tickers,
        "history": hist,
        "stats": stats,
        "subperiods": pd.DataFrame(sub),
        "paired": pd.DataFrame(pairs),
        "monthly_net": net,
        "weights": pd.DataFrame(weights_log),
    }
