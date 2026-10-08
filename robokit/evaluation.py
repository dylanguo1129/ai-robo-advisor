"""Walk-forward parts of the pre-registered v3 evaluation (docs/RESEARCH_LOG.md section 10): E1, E2, E4, the
walk-forward sensitivities of E5 and E6. scripts/run_v3_evaluation.py runs them once; tests/test_evaluation.py checks
the machinery on small cases. Every strategy that uses the engine goes through ``engine.build_portfolio`` itself
(``lean=True``), with at most one component changed by a research switch, so what is evaluated is what ships.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from optimizer.backtest import _hold
from optimizer.estimators import choose_covariance

from . import evalstats as es
from . import profile as prof
from .engine import Request, as_of, build_portfolio, build_returns, returns_in, select_funds
from .research import pit_shelf
from .shelf import prior_share

COST = 10e-4  # one way, on all turnover (as v1 and v2)
LEVELS = (1, 2, 3, 4, 5)
PRIMARY = (2, 3, 4)
MARGIN_SR = 0.10  # non-inferiority margin, annual Sharpe ratio
BAND = (0.80, 1.25)  # risk delivery: realised over target volatility must lie inside this band

# strategies built by the engine: (Request keyword changes, research switches)
ENGINE = {
    "robokit": ({}, {}),
    "no_resample": ({"resample": False}, {}),
    "sample_cov": ({}, {"cov_method": "sample"}),
    "no_caps": ({}, {"sleeve_caps": False}),
    "no_cash_caps": ({}, {"cash_caps": False}),
    "single_lambda": ({}, {"calibrate": "single"}),
    "sample_mu": ({}, {"mu_method": "sample"}),
    "james_stein_mu": ({}, {"mu_method": "james_stein"}),
    "textbook_60": ({"resample": False, "min_weight": 0.0}, {"mu_method": "sample", "max_window": 60, "calibrate": "single"}),
}
OUTSIDE = ("static_mix", "equal_weight", "erc_cash", "minvar_cash")  # built here from the same as-of data
CONFIRMATORY = ("static_mix", "textbook_60", "erc_cash", "minvar_cash")  # risk-matched benchmarks
ABLATIONS = ("no_resample", "sample_cov", "no_caps", "no_cash_caps", "single_lambda", "sample_mu", "james_stein_mu")


@dataclass
class Shelf:
    market: str
    tickers: list
    prior: pd.Series
    cash: str
    equity: list
    bonds: list
    full: pd.DataFrame  # extended monthly returns, today's knowledge of funds and stand-ins (E1)


def reference_shelf(market: str) -> Shelf:
    shelf, core, _ = select_funds(Request(market=market))
    _, full, _ = build_returns(market, shelf, core, [])
    full = full[core]
    prior = pd.Series(0.0, index=core)
    for _, r in shelf.iterrows():
        prior[r.ticker] += prior_share(market, r.sleeve)
    prior = prior / prior.sum()
    cash = shelf.loc[shelf.role == "cash", "ticker"].iloc[0]
    eq = [r.ticker for _, r in shelf.iterrows() if r.asset_class == "Equity"]
    fi = [r.ticker for _, r in shelf.iterrows() if r.asset_class == "Fixed income"]
    return Shelf(market, core, prior, cash, eq, fi, full)


def december_dates(full: pd.DataFrame, min_months: int = 60) -> list[pd.Timestamp]:
    """Every December month-end from the first one with ``min_months`` of common history, while a month follows."""
    common = full.dropna(how="any")
    first = common.index[min_months - 1]
    last = common.index[-1]
    return [d for d in common.index if d.month == 12 and d >= first and d < last]


# ------------------------------------------------------------------ weights at one date
def outside_weights(
    name: str, tickers: list, X: pd.DataFrame, prior: pd.Series, cash: str, eq: list, fi: list, level: float, target: float
):
    """The four benchmarks not built by the engine, from the same as-of window ``X`` (monthly returns)."""
    w = pd.Series(0.0, index=tickers)
    if name == "static_mix":  # stock share = level x 20%, split by the policy prior (as v2)
        s = prof.risk_share(prof.engine_level(level))
        e = [t for t in eq if t in tickers]
        f = [t for t in fi if t in tickers]
        w[e] = s * prior[e] / prior[e].sum()
        w[f] = (1 - s) * prior[f] / prior[f].sum()
        return w, True
    risky = [t for t in tickers if t != cash]
    if name == "equal_weight":
        w[risky] = 1.0 / len(risky)
        return w, True
    S, _ = choose_covariance(X[tickers].to_numpy(), "lw_cc")
    S = pd.DataFrame(S * 12, index=tickers, columns=tickers)
    Sr = S.loc[risky, risky].to_numpy()
    base = es.erc_weights(Sr) if name == "erc_cash" else es.min_variance(Sr, cap=0.5)
    full = pd.Series(0.0, index=tickers)
    full[risky] = base
    mixed, ok = es.mix_with_cash(full.to_numpy(), S.to_numpy(), tickers.index(cash), target)
    return pd.Series(mixed, index=tickers), ok


def build_at(task: tuple) -> dict:
    """One estimation: (market, date, level, strategy, mode, extra). mode 'fixed' (E1) or 'strict' (E2, point-in-time
    funds, own histories only). extra: research switches added on top (E5 walk-forward variants). Run in a worker."""
    market, date, level, strategy, mode, extra = task
    extra = dict(extra or {})
    no_resample = extra.pop("_no_resample", False)  # a default locked by E3
    date = pd.Timestamp(date)
    req_kw, research = ({}, {}) if strategy in OUTSIDE else ENGINE[strategy]
    if no_resample:
        req_kw = {**req_kw, "resample": False}
    research = {**research, **extra}
    base_kw = {}
    if mode == "strict":
        swaps, kept, _ = pit_shelf(market, date)
        base_kw = {"swaps": swaps, "sleeves": kept}
        research = {**research, "stand_ins": False}
    try:
        with as_of(date, mode):
            if strategy in OUTSIDE:  # the as-of window and target from a single-solve engine build
                q = build_portfolio(Request(market=market, risk_level=level, resample=False, **base_kw), lean=True, research=research)
                X = q["returns"]
                tick = list(X.columns)
                shelf, _, _ = select_funds(Request(market=market, **base_kw))
                prior = pd.Series(0.0, index=tick)
                for _, r in shelf.iterrows():
                    if r.ticker in tick:
                        prior[r.ticker] += prior_share(market, r.sleeve)
                prior = prior / prior.sum()
                cash = shelf.loc[shelf.role == "cash", "ticker"].iloc[0]
                eq = [r.ticker for _, r in shelf.iterrows() if r.asset_class == "Equity"]
                fi = [r.ticker for _, r in shelf.iterrows() if r.asset_class == "Fixed income"]
                w, reachable = outside_weights(strategy, tick, X, prior, cash, eq, fi, level, q["target_vol"])
                S, _ = choose_covariance(X.to_numpy(), "lw_cc")
                vol = float(np.sqrt(w.to_numpy() @ (S * 12) @ w.to_numpy()))
                return {
                    "task": task[:5],
                    "weights": {t: float(v) for t, v in w.items() if v > 0},
                    "target": q["target_vol"],
                    "ex_ante_vol": vol,
                    "reachable": reachable,
                    "outcome": None,
                    "window": q["window"]["months"],
                }
            q = build_portfolio(Request(market=market, risk_level=level, **{**req_kw, **base_kw}), lean=True, research=research)
            return {
                "task": task[:5],
                "weights": q["weights"],
                "target": q["target_vol"],
                "ex_ante_vol": q["volatility"],
                "reachable": True,
                "outcome": q["calibration"]["outcome"] if q["calibration"] else None,
                "window": q["window"]["months"],
            }
    except Exception as e:  # recorded and counted, never dropped silently
        return {"task": task[:5], "error": f"{type(e).__name__}: {e}"}


# ------------------------------------------------------------------ holding
def hold_path(builds: list[dict], realised: pd.DataFrame, cost: float = COST) -> pd.DataFrame:
    """Monthly gross and net returns, turnover and the target in force, for one strategy and level: each December's
    weights held 12 months and rebalanced monthly back to target, cost on the monthly drift and on the annual change."""
    builds = sorted(builds, key=lambda b: b["task"][1])
    rows, prev = [], None
    for i, b in enumerate(builds):
        start = pd.Timestamp(b["task"][1])
        end = pd.Timestamp(builds[i + 1]["task"][1]) if i + 1 < len(builds) else realised.index[-1]
        hold = realised.loc[(realised.index > start) & (realised.index <= end)]
        if hold.empty:
            continue
        tick = list(hold.columns)
        w = np.array([b["weights"].get(t, 0.0) for t in tick])
        w = w / w.sum()
        hold = hold.fillna(0.0) if hold.isna().any().any() else hold
        g, n, t = _hold(hold, w, cost)
        reb = 0.5 * float(np.abs(w - prev).sum()) if prev is not None else 0.0
        n[0] -= cost * reb
        t[0] += reb
        prev = w
        rows.append(pd.DataFrame({"gross": g, "net": n, "turn": t, "target": b["target"]}, index=hold.index))
    return pd.concat(rows) if rows else pd.DataFrame(columns=["gross", "net", "turn", "target"])


# ------------------------------------------------------------------ analysis
def ann_return(r) -> float:
    r = np.asarray(r, dtype=float)
    return float(np.prod(1 + r) ** (12 / len(r)) - 1)


def describe(path: pd.DataFrame, cash: pd.Series) -> dict:
    r = path["net"]
    ex = r - cash.reindex(r.index).fillna(0.0)
    sd = float(ex.std(ddof=1))
    tail = es.cvar(r, 0.95)
    return {
        "months": int(len(r)),
        "from": str(r.index.min().date()),
        "to": str(r.index.max().date()),
        "ann_return": ann_return(r),
        "ann_vol": float(r.std(ddof=1) * math.sqrt(12)),
        "sharpe": float(ex.mean() / sd * math.sqrt(12)) if sd > 0 else float("nan"),  # monthly excess mean / sd, annualised
        "max_drawdown": es.max_drawdown(r),
        "cvar95_monthly": tail,
        "cvar95_tail_months": max(1, int(math.floor(0.05 * len(r)))),
        "monthly_turnover": float(path["turn"].mean()),
        "cost_drag": ann_return(path["gross"]) - ann_return(r),
        "mean_target": float(path["target"].mean()),
    }


def subperiod(path: pd.DataFrame, year: int) -> dict:
    r = path["net"].loc[f"{year}-01-01" : f"{year}-12-31"]
    return {
        "months": int(len(r)),
        "return": float(np.prod(1 + r) - 1) if len(r) else None,
        "vol": float(r.std(ddof=1) * math.sqrt(12)) if len(r) > 1 else None,
        "max_drawdown": es.max_drawdown(r) if len(r) else None,
    }


def risk_delivery(paths: dict, levels=PRIMARY, block: int = 6, n_boot: int = 5000, seed: int = 0) -> dict:
    """Realised over target volatility: the monthly returns divided by the monthly target in force (target / sqrt 12),
    their standard deviation, and simultaneous (Bonferroni) 90% block-bootstrap intervals over ``levels``. Delivered
    if every interval lies inside BAND; missed at a level whose point ratio lies outside BAND; otherwise inconclusive."""
    k = len(levels)
    lev = 1 - 0.10 / k
    out = {}
    for L in levels:
        p = paths[L]
        z = p["net"] / (p["target"] / math.sqrt(12))
        out[L] = es.vol_ratio_interval(z.to_numpy(), block=block, n_boot=n_boot, level=lev, seed=seed)
    inside = all(BAND[0] <= out[L]["lo"] and out[L]["hi"] <= BAND[1] for L in levels)
    missed = [L for L in levels if not BAND[0] <= out[L]["ratio"] <= BAND[1]]
    out["reading"] = "delivered" if inside else ("missed at levels " + ", ".join(map(str, missed)) if missed else "inconclusive")
    out["band"] = BAND
    out["simultaneous_level"] = 0.90
    return out


def compare(a: pd.Series, b: pd.Series, cash: pd.Series, block: int = 6, n_boot: int = 5000, seed: int = 0) -> dict:
    """robokit (a) against another strategy (b) on the months both have: the Ledoit-Wolf (2008) Sharpe test, a
    non-inferiority p-value (H0: a's annual Sharpe is worse by MARGIN_SR or more), Newey-West on the mean return
    difference, and the minimum track record for a's Sharpe to exceed b's."""
    idx = a.index.intersection(b.index)
    c = cash.reindex(idx).fillna(0.0)
    ra, rb = (a.loc[idx] - c).to_numpy(), (b.loc[idx] - c).to_numpy()
    lw = es.sharpe_diff_test(ra, rb, block=block, n_boot=n_boot, seed=seed, margin=MARGIN_SR / math.sqrt(12))
    nw = es.newey_west_t((a.loc[idx] - b.loc[idx]).to_numpy(), lags=6)
    sr_b = rb.mean() / rb.std(ddof=1)
    mtr = es.min_track_record(ra, sr_star=sr_b)
    return {
        "months": int(len(idx)),
        "sharpe_diff_annual": lw["diff"] * math.sqrt(12),
        "ci95_annual": [lw["ci95"][0] * math.sqrt(12), lw["ci95"][1] * math.sqrt(12)],
        "p_two_sided": lw["p"],
        "p_noninferior": lw["p_noninferior"],
        "mean_diff_annual": nw["mean"] * 12,
        "nw_t": nw["t"],
        "min_track_record_months": mtr,
        "track_record_long_enough": bool(len(idx) >= mtr),
    }


def strict_realised(market: str, builds: list[dict]) -> pd.DataFrame:
    """E2: each fund's own monthly returns (no stand-ins) in the portfolio currency, for every fund any point-in-time
    shelf held. A month before a fund's first return cannot be held: the shelf only holds funds with 36 months."""
    tick = sorted({t for b in builds if "weights" in b for t in b["weights"]})
    return returns_in(market, tick)
