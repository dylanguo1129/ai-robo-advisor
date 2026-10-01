"""Walk-forward comparison of allocation methods.

This is the honesty check the course keeps asking for (Session 1 slides
10-13; Arnott, Harvey & Markowitz 2019, "A Backtesting Protocol in the Era
of Machine Learning"; Deutsche Bank 2014, "Seven Sins of Quantitative
Investing"). At each rebalance date the optimizer sees only the trailing
``window`` months, picks weights for each risk profile, and those weights
are held (rebalanced monthly to target) for the next ``step`` months.
Realized statistics are computed on the stitched out-of-sample returns only,
after transaction costs.

Protocol items implemented here
-------------------------------
* trading costs: ``cost_bps`` one-way on every unit of turnover, including
  the monthly drift rebalancing inside the holding period, not only the
  annual re-estimation ("Do not ignore trading costs and fees");
* risk matching: every method is calibrated to the same ex-ante volatility
  per profile, so a method with bigger expected returns cannot look better
  simply by taking more risk;
* sub-period statistics, so a regime such as 2020 or 2022 is visible rather
  than averaged away ("Be aware of structural changes");
* paired t-statistics on monthly differences, so a gap in Sharpe ratios is
  reported with the evidence for it, not as a fact.

Methods compared
----------------
equilibrium_mvo   Robo-Kit default: shrunk Sigma + equilibrium mu
sample_mvo        the textbook plug-in: sample mean, sample covariance
minvar            minimum variance over the risky ETFs (ignores mu)
equal_weight      1/N over the universe
prior             the prior (AUM-weighted) portfolio itself, "just buy the market"
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .data import MONTHS_PER_YEAR, max_drawdown
from .portfolio import RiskProfiles, RoboKitOptimizer

PROFILES = ("low", "mid", "high")


@dataclass
class BacktestResult:
    stats: pd.DataFrame  # index (method, profile); ann_return, ann_vol, sharpe, max_dd, avg_turnover, cost_drag, n_months
    monthly: pd.DataFrame  # net out-of-sample monthly returns, columns "method|profile"
    monthly_gross: pd.DataFrame
    weights: dict  # {(method, profile): DataFrame of target weights by rebalance date}
    subperiods: pd.DataFrame | None = None


def _method_weights(method, hist, rf, prior, profiles, cash, w_max, resample, n_boot, vol_targets, naive_blend, cash_max):
    out = {}
    if method == "equal_weight":
        w = pd.Series(1.0 / hist.shape[1], index=hist.columns)
        return {p: w for p in PROFILES}
    if method == "prior":
        w = prior.reindex(hist.columns).fillna(0.0)
        return {p: w / w.sum() for p in PROFILES}
    common = dict(rf=rf, prior_weights=prior, w_max=w_max, cash_ticker=cash, cash_max=cash_max, profiles=profiles, naive_blend=naive_blend)
    if method == "equilibrium_mvo":
        opt = RoboKitOptimizer(hist, cov_method="auto", mu_method="equilibrium", **common).fit()
    elif method == "sample_mvo":
        opt = RoboKitOptimizer(hist, cov_method="sample", mu_method="sample", **common).fit()
    elif method == "minvar":
        opt = RoboKitOptimizer(hist, cov_method="auto", mu_method="equilibrium", **common).fit()
        w = opt.optimize(1e6, excluded=[cash] if cash in hist.columns else None, resample=False).weights
        return {p: w for p in PROFILES}
    else:
        raise ValueError(method)
    if vol_targets:
        opt.calibrate_to_target_vol(vol_targets, n_iter=40)
    for p in PROFILES:
        out[p] = opt.optimize(p, resample=resample, n_boot=n_boot).weights
    return out


def _hold(hold_returns: pd.DataFrame, w_target: np.ndarray, cost: float):
    """Monthly returns of a portfolio rebalanced back to ``w_target`` at each
    month end. Returns (gross, net, turnover) arrays; turnover is the one-way
    fraction traded each month (drift back to target)."""
    r = hold_returns.to_numpy()
    n_m = r.shape[0]
    gross = np.empty(n_m)
    net = np.empty(n_m)
    turn = np.empty(n_m)
    for m in range(n_m):
        g = float(w_target @ r[m])
        drifted = w_target * (1 + r[m]) / (1 + g) if g > -1 else w_target
        t_m = 0.5 * float(np.abs(drifted - w_target).sum())
        gross[m] = g
        net[m] = g - cost * t_m
        turn[m] = t_m
    return gross, net, turn


def walk_forward_backtest(
    returns: pd.DataFrame,
    rf: float,
    prior_weights: pd.Series,
    methods: tuple[str, ...] = ("equilibrium_mvo", "sample_mvo", "minvar", "equal_weight", "prior"),
    window: int = 60,
    step: int = 12,
    profiles: RiskProfiles | None = None,
    cash_ticker: str | None = None,
    cash_max: float = 1.0,
    w_max: float = 0.35,
    resample: bool = False,
    n_boot: int = 200,
    vol_targets: dict[str, float] | None = None,
    cost_bps: float = 10.0,
    naive_blend: float = 0.0,
    subperiods: dict[str, tuple[str, str]] | None = None,
) -> BacktestResult:
    """``vol_targets`` = {'low': 0.12, 'mid': 0.09, 'high': 0.04} makes the
    comparison risk-matched (recommended). ``cost_bps`` is the one-way cost per
    unit traded (10 bps ~ half a 9 bps median Canadian-equity-ETF spread plus
    slippage, National Bank Financial data cited in docs/RESEARCH_NOTES.md).
    ``subperiods`` = {'2020 crash': ('2020-01-31', '2020-12-31'), ...}."""
    profiles = profiles or RiskProfiles()
    cost = cost_bps / 1e4
    t = len(returns)
    rebal_points = list(range(window, t - 1, step))
    if not rebal_points:
        raise ValueError("not enough history for the requested window")

    net_series: dict[str, list] = {}
    gross_series: dict[str, list] = {}
    weights_log: dict = {}
    rebal_turn: dict = {}
    drift_turn: dict = {}
    for m in methods:
        prev = {p: None for p in PROFILES}
        for start in rebal_points:
            hist = returns.iloc[start - window : start]
            hold = returns.iloc[start : min(start + step, t)]
            w_by_p = _method_weights(
                m, hist, rf, prior_weights, profiles, cash_ticker, w_max, resample, n_boot, vol_targets, naive_blend, cash_max
            )
            for p, w in w_by_p.items():
                w = w.reindex(returns.columns).fillna(0.0)
                wv = w.to_numpy()
                gross, net, turn = _hold(hold, wv, cost)
                key = f"{m}|{p}"
                # cost of moving from last period's (drifted-back-to-target) weights to the new target
                if prev[p] is not None:
                    reb = 0.5 * float(np.abs(wv - prev[p]).sum())
                    net[0] -= cost * reb
                    rebal_turn.setdefault((m, p), []).append(reb)
                drift_turn.setdefault((m, p), []).extend(turn.tolist())
                net_series.setdefault(key, []).append(pd.Series(net, index=hold.index))
                gross_series.setdefault(key, []).append(pd.Series(gross, index=hold.index))
                weights_log.setdefault((m, p), []).append(w.rename(returns.index[start]))
                prev[p] = wv

    monthly = pd.DataFrame({k: pd.concat(v) for k, v in net_series.items()})
    monthly_gross = pd.DataFrame({k: pd.concat(v) for k, v in gross_series.items()})

    def _stats(r: pd.Series) -> dict:
        r = r.dropna()
        ann_ret = float((1 + r).prod() ** (MONTHS_PER_YEAR / len(r)) - 1)
        ann_vol = float(r.std(ddof=1) * np.sqrt(MONTHS_PER_YEAR))
        return {
            "ann_return": ann_ret,
            "ann_vol": ann_vol,
            "sharpe": (ann_ret - rf) / ann_vol if ann_vol > 0 else np.nan,
            "max_dd": max_drawdown(r),
            "n_months": len(r),
        }

    rows = []
    for col in monthly.columns:
        m, p = col.split("|")
        s = _stats(monthly[col])
        g = _stats(monthly_gross[col])
        s["cost_drag"] = g["ann_return"] - s["ann_return"]
        s["avg_rebalance_turnover"] = float(np.mean(rebal_turn.get((m, p), [0.0])))
        s["avg_monthly_drift_turnover"] = float(np.mean(drift_turn.get((m, p), [0.0])))
        rows.append({"method": m, "profile": p, **s})
    stats = pd.DataFrame(rows).set_index(["method", "profile"])

    sub = None
    if subperiods:
        srows = []
        for name, (a, b) in subperiods.items():
            chunk = monthly.loc[pd.Timestamp(a) : pd.Timestamp(b)]
            if len(chunk) < 3:
                continue
            for col in chunk.columns:
                m, p = col.split("|")
                srows.append({"period": name, "method": m, "profile": p, **_stats(chunk[col])})
        sub = pd.DataFrame(srows).set_index(["period", "method", "profile"]) if srows else None

    wl = {k: pd.DataFrame(v) for k, v in weights_log.items()}
    return BacktestResult(stats=stats, monthly=monthly, monthly_gross=monthly_gross, weights=wl, subperiods=sub)


def paired_comparison(monthly: pd.DataFrame, col_a: str, col_b: str, rf: float = 0.0) -> dict:
    """Mean monthly return difference a - b with a t-statistic. With 5-8 years
    of out-of-sample months the t-stat is what tells the panel whether a gap
    in Sharpe ratios means anything."""
    d = (monthly[col_a] - monthly[col_b]).dropna()
    n = len(d)
    se = d.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
    return {
        "a": col_a,
        "b": col_b,
        "n_months": n,
        "mean_monthly_diff": float(d.mean()),
        "annualized_diff": float(d.mean() * MONTHS_PER_YEAR),
        "t_stat": float(d.mean() / se) if se and se > 0 else np.nan,
    }
