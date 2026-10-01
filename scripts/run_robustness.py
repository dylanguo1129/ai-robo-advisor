"""Pre-specified robustness grid for the walk-forward test.

Every configuration here was written down BEFORE it was run (Arnott, Harvey &
Markowitz 2019: "Keep track of what is tried"; "Define the test sample ex
ante"). Nothing is added after seeing results; if a variant is added later it
gets a dated entry in docs/RESEARCH_LOG.md.

    python scripts/run_robustness.py

Writes output/robustness_grid.csv (one row per configuration x method x
profile) and output/robustness_subperiods.csv.
"""

from __future__ import annotations

import os
import sys
import time

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from optimizer import RoboKitOptimizer, load_prices, to_monthly_returns  # noqa: E402
from optimizer.backtest import paired_comparison, walk_forward_backtest  # noqa: E402

DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")
RF = 0.0225
CASH = "PSA.TO"
VOL_TARGETS = {"low": 0.12, "mid": 0.09, "high": 0.04}
SUBPERIODS = {
    "2018-2019 (late cycle)": ("2018-01-31", "2019-12-31"),
    "2020 (COVID crash + rebound)": ("2020-01-31", "2020-12-31"),
    "2021-2022 (inflation, rate shock)": ("2021-01-31", "2022-12-31"),
    "2023-2026 (AI rally, easing)": ("2023-01-31", "2026-08-31"),
}

# The grid. 'start' + 'exclude' define the sample; 'window' the estimation
# length; 'prior' the anchor portfolio; 'blend' the Tu-Zhou 1/N blend; 'cost'
# the one-way transaction cost in bps; 'cash_max' the cap on the cash ETF.
GRID = [
    # the prototype configuration (as in run_prototype.py) with costs added
    dict(name="base_2016_w60", start="2016-01-01", exclude=(), window=60, prior="aum", blend=0.0, cost=10, cash_max=1.0),
    # longer sample: drop XAW (listed 2015) so the panel starts in 2014 and the test covers 2018-2026
    dict(name="long_2014_w48", start="2014-01-01", exclude=("XAW.TO",), window=48, prior="aum", blend=0.0, cost=10, cash_max=1.0),
    dict(name="long_2014_w60", start="2014-01-01", exclude=("XAW.TO",), window=60, prior="aum", blend=0.0, cost=10, cash_max=1.0),
    # prior sensitivity: a stated 60/35/3/2 policy prior instead of AUM
    dict(
        name="long_2014_w48_policyprior",
        start="2014-01-01",
        exclude=("XAW.TO",),
        window=48,
        prior="policy",
        blend=0.0,
        cost=10,
        cash_max=1.0,
    ),
    # Tu-Zhou style blend with 1/N
    dict(name="long_2014_w48_blend50", start="2014-01-01", exclude=("XAW.TO",), window=48, prior="aum", blend=0.5, cost=10, cash_max=1.0),
    # cash capped at 35% like any other ETF (forces bonds into cautious portfolios)
    dict(
        name="long_2014_w48_cashcap35", start="2014-01-01", exclude=("XAW.TO",), window=48, prior="aum", blend=0.0, cost=10, cash_max=0.35
    ),
    # cost sensitivity
    dict(name="long_2014_w48_cost25", start="2014-01-01", exclude=("XAW.TO",), window=48, prior="aum", blend=0.0, cost=25, cash_max=1.0),
]
POLICY = {"Equity": 0.60, "Fixed income": 0.35, "Cash": 0.03, "Commodity": 0.02}


def build_prior(kind: str, universe: pd.DataFrame, info: pd.DataFrame, columns) -> pd.Series:
    cls = universe.set_index("ticker")["asset_class"].reindex(columns)
    aum = info.set_index("ticker")["total_assets"].reindex(columns)
    filled = aum.copy()
    for t in aum.index[aum.isna()]:
        same = aum[(cls == cls[t]) & aum.notna()]
        filled[t] = same.median() if len(same) else aum.median()
    if kind == "aum":
        return filled / filled.sum()
    if kind == "policy":
        cls2 = cls.replace({"Real estate": "Equity"})  # REITs sit inside equity for the policy split
        return RoboKitOptimizer.prior_from_class_weights(POLICY, cls2, within_class=filled)
    raise ValueError(kind)


def main() -> None:
    universe = pd.read_csv(os.path.join(DATA, "universe.csv"))
    info = pd.read_csv(os.path.join(DATA, "etf_info_yf.csv"))
    prices = load_prices(os.path.join(DATA, "prices_daily_adjclose.csv"))
    rows, subrows, comps = [], [], []
    for cfg in GRID:
        t0 = time.time()
        px = prices.drop(columns=list(cfg["exclude"]))
        panel = to_monthly_returns(px, start=cfg["start"], min_months=36)
        prior = build_prior(cfg["prior"], universe, info, panel.returns.columns)
        bt = walk_forward_backtest(
            panel.returns,
            RF,
            prior,
            window=cfg["window"],
            step=12,
            cash_ticker=CASH,
            cash_max=cfg["cash_max"],
            w_max=0.35,
            resample=False,
            vol_targets=VOL_TARGETS,
            cost_bps=cfg["cost"],
            naive_blend=cfg["blend"],
            subperiods=SUBPERIODS,
        )
        st = bt.stats.reset_index()
        st.insert(0, "config", cfg["name"])
        st["oos_start"] = str(bt.monthly.index[0].date())
        st["oos_end"] = str(bt.monthly.index[-1].date())
        rows.append(st)
        if bt.subperiods is not None:
            sp = bt.subperiods.reset_index()
            sp.insert(0, "config", cfg["name"])
            subrows.append(sp)
        for p in ("low", "mid", "high"):
            c = paired_comparison(bt.monthly, f"equilibrium_mvo|{p}", f"sample_mvo|{p}", RF)
            c["config"] = cfg["name"]
            comps.append(c)
        print(
            f"{cfg['name']}: {panel.returns.shape[1]} ETFs, {panel.n_months} months, OOS {bt.monthly.index[0].date()} to {bt.monthly.index[-1].date()}, {time.time() - t0:.0f}s",
            flush=True,
        )
        print(
            bt.stats.loc[
                ["equilibrium_mvo", "sample_mvo", "prior"],
                ["ann_return", "ann_vol", "sharpe", "max_dd", "avg_rebalance_turnover", "cost_drag"],
            ]
            .round(3)
            .to_string(),
            flush=True,
        )
    grid = pd.concat(rows, ignore_index=True)
    grid.round(5).to_csv(os.path.join(OUT, "robustness_grid.csv"), index=False)
    if subrows:
        pd.concat(subrows, ignore_index=True).round(5).to_csv(os.path.join(OUT, "robustness_subperiods.csv"), index=False)
    pd.DataFrame(comps).round(5).to_csv(os.path.join(OUT, "robustness_paired.csv"), index=False)
    print("\nPaired equilibrium - sample (annualized diff, t):")
    print(pd.DataFrame(comps)[["config", "a", "annualized_diff", "t_stat"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
