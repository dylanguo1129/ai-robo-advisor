"""End-to-end prototype run on the cached Canadian ETF universe.

    python scripts/run_prototype.py            # uses data/prices_daily_adjclose.csv
    python scripts/run_prototype.py --refresh  # re-download prices first

Writes to output/: inputs table, weights for the three profiles (point and
resampled), frontier, risk contributions, the walk-forward back-test table,
the JSON hand-off for the web prototype, and four PNG charts.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from optimizer import RoboKitOptimizer, download_prices, load_prices, to_monthly_returns  # noqa: E402
from optimizer.backtest import paired_comparison, walk_forward_backtest  # noqa: E402
from optimizer.data import integrity_report  # noqa: E402
from optimizer.export import export_web_spec, make_test_cases  # noqa: E402

DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")
RF = 0.0225  # Bank of Canada overnight target, held at 2.25% on 2 Sep 2026
DELTA = 2.5  # market risk aversion (He & Litterman 1999 convention)
CASH = "PSA.TO"
COST_BPS = 10.0  # one-way transaction cost per unit traded (see docs/METHOD.md)
START = "2016-01-01"


def prior_from_aum(universe: pd.DataFrame, info: pd.DataFrame) -> pd.Series:
    """AUM-weighted prior; ETFs whose AUM Yahoo does not report get the
    median AUM of their asset class (flagged in the output)."""
    aum = info.set_index("ticker")["total_assets"].reindex(universe.ticker)
    cls = universe.set_index("ticker")["asset_class"]
    filled = aum.copy()
    for t in aum.index[aum.isna()]:
        same = aum[(cls == cls[t]) & aum.notna()]
        filled[t] = same.median() if len(same) else aum.median()
    return filled / filled.sum(), list(aum.index[aum.isna()])


def main(refresh: bool = False, n_boot: int = 500) -> None:
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "backtest_weights"), exist_ok=True)
    universe = pd.read_csv(os.path.join(DATA, "universe.csv"))
    price_path = os.path.join(DATA, "prices_daily_adjclose.csv")
    if refresh or not os.path.exists(price_path):
        download_prices(list(universe.ticker), "2013-01-01", "2026-09-01", price_path)
    prices = load_prices(price_path)
    panel = to_monthly_returns(prices, start=START, min_months=36)
    print(panel.summary())
    rep = integrity_report(prices.loc[pd.Timestamp(START) :], panel.returns)
    rep.to_csv(os.path.join(OUT, "data_integrity_report.csv"), index=False)
    print(f"data integrity: {len(rep)} finding(s)" + (":\n" + rep.to_string(index=False) if len(rep) else ""))

    info = pd.read_csv(os.path.join(DATA, "etf_info_yf.csv"))
    prior, aum_missing = prior_from_aum(universe, info)
    prior = prior.reindex(panel.returns.columns)

    opt = RoboKitOptimizer(
        panel.returns, rf=RF, prior_weights=prior, delta=DELTA, cov_method="auto", mu_method="equilibrium", w_max=0.35, cash_ticker=CASH
    ).fit()
    print(f"covariance: {opt.cov_info}")
    print(f"delta = {opt.delta:.2f}, prior portfolio vol = {opt.prior_vol:.2%}, implied prior premium = {opt.market_premium:.2%}")

    # 1. inputs table
    inputs = opt.asset_table().join(universe.set_index("ticker")[["name", "asset_class"]])
    inputs.to_csv(os.path.join(OUT, "inputs_by_etf.csv"))

    # 2. three profiles, point estimate and resampled
    rows = []
    results = {}
    for p in ("low", "mid", "high"):
        pt = opt.optimize(p, resample=False)
        rs = opt.optimize(p, resample=True, n_boot=n_boot, seed=0)
        results[p] = rs
        for t in opt.tickers:
            rows.append(
                {
                    "profile": p,
                    "ticker": t,
                    "asset_class": universe.set_index("ticker").asset_class[t],
                    "weight_point": pt.weights[t],
                    "weight_resampled": rs.weights[t],
                    "band_q05": rs.weight_band.loc[t, "q05"],
                    "band_q95": rs.weight_band.loc[t, "q95"],
                    "risk_contribution": rs.risk_contributions[t],
                }
            )
        print(
            f"\n[{p}] lam={rs.risk_aversion:.2f}  E[r]={rs.exp_return:.2%}  vol={rs.exp_vol:.2%}  Sharpe={rs.sharpe:.2f}  effN={rs.effective_n:.1f}  (point: vol={pt.exp_vol:.2%}, effN={pt.effective_n:.1f})"
        )
        print(rs.weights[rs.weights > 0.005].sort_values(ascending=False).round(3).to_string())
        for n in rs.notes:
            print("  note:", n)
    weights = pd.DataFrame(rows)
    weights.to_csv(os.path.join(OUT, "weights_by_profile.csv"), index=False)
    with open(os.path.join(OUT, "profiles.json"), "w", encoding="utf-8") as f:
        json.dump({p: r.to_dict() for p, r in results.items()}, f, indent=1)

    # 3. frontier
    lams = opt.delta * np.array([0.25, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0, 2.5, 3.5, 5.0, 8.0, 15.0])
    frontier = opt.frontier(list(lams))
    frontier.to_csv(os.path.join(OUT, "frontier.csv"), index=False)

    # 4. comparison of mu methods (same Sigma, same lam) -- the "Lucky Bets" exhibit
    comp = {}
    for m in ("sample", "james_stein", "equilibrium"):
        o = RoboKitOptimizer(
            panel.returns, rf=RF, prior_weights=prior, delta=DELTA, cov_method="auto", mu_method=m, w_max=0.35, cash_ticker=CASH
        ).fit()
        comp[m] = o.optimize("mid", resample=False).weights
    comp = pd.DataFrame(comp)
    comp.to_csv(os.path.join(OUT, "mu_method_comparison_mid.csv"))

    # 5. walk-forward back-test
    VOL_TARGETS = {"low": 0.12, "mid": 0.09, "high": 0.04}  # ex-ante vols of the three profiles, rounded
    SUBPERIODS = {
        "2021-2022 (inflation, rate shock)": ("2021-01-31", "2022-12-31"),
        "2023-2026 (AI rally, easing)": ("2023-01-31", "2026-08-31"),
    }
    bt = walk_forward_backtest(
        panel.returns,
        RF,
        prior,
        window=60,
        step=12,
        cash_ticker=CASH,
        w_max=0.35,
        resample=False,
        vol_targets=VOL_TARGETS,
        cost_bps=COST_BPS,
        subperiods=SUBPERIODS,
    )
    bt.stats.round(4).to_csv(os.path.join(OUT, "backtest_stats.csv"))
    bt.monthly.to_csv(os.path.join(OUT, "backtest_monthly_returns.csv"))
    if bt.subperiods is not None:
        bt.subperiods.round(4).to_csv(os.path.join(OUT, "backtest_subperiods.csv"))
    print(
        f"\nWalk-forward back-test (60-month window, annual rebalance, risk-matched at 12/9/4% ex-ante vol, {COST_BPS:.0f} bps one-way costs):"
    )
    print(bt.stats.round(3).to_string())
    comps = [paired_comparison(bt.monthly, f"equilibrium_mvo|{p}", f"sample_mvo|{p}", RF) for p in ("low", "mid", "high")]
    comps += [
        paired_comparison(bt.monthly, "equilibrium_mvo|mid", "equal_weight|mid", RF),
        paired_comparison(bt.monthly, "equilibrium_mvo|mid", "prior|mid", RF),
    ]
    comps = pd.DataFrame(comps)
    comps.to_csv(os.path.join(OUT, "backtest_paired_comparisons.csv"), index=False)
    print("\nPaired monthly-return differences (a - b):")
    print(comps.round(4).to_string(index=False))
    os.makedirs(os.path.join(OUT, "backtest_weights"), exist_ok=True)
    for k, wdf in bt.weights.items():
        wdf.to_csv(os.path.join(OUT, "backtest_weights", f"{k[0]}_{k[1]}.csv"))

    # 6. hand-off for the web prototype
    cases = [
        {"name": "full_universe_mid", "profile": "mid"},
        {"name": "full_universe_high", "profile": "high"},
        {"name": "growth_shortlist_low", "profile": "low", "tickers": ["XIC.TO", "VFV.TO", "XEF.TO", "XEC.TO", "ZAG.TO", "PSA.TO"]},
        {"name": "cautious_all_equity", "profile": "high", "tickers": ["XIC.TO", "VFV.TO", "XEF.TO"]},
        {"name": "forced_and_excluded", "profile": "mid", "forced": {"CGL.TO": 0.10}, "excluded": ["XHY.TO", "ZEB.TO"]},
        {"name": "tight_cap", "profile": "mid", "w_max": 0.15},
    ]
    export_web_spec(
        opt,
        os.path.join(OUT, "robokit_spec.json"),
        make_test_cases(opt, cases),
        extra={"aum_missing_filled_with_class_median": aum_missing, "data_notes": panel.summary()},
    )

    # 7. charts
    plot_weights(weights, os.path.join(OUT, "weights_by_profile.png"))
    plot_frontier(frontier, results, opt, os.path.join(OUT, "frontier.png"))
    plot_bands(results["mid"], os.path.join(OUT, "weight_bands_mid.png"))
    plot_mu_comparison(comp, os.path.join(OUT, "mu_method_comparison_mid.png"))
    print(f"\nwrote outputs to {OUT}")


def plot_weights(weights: pd.DataFrame, path: str) -> None:
    piv = weights.pivot(index="ticker", columns="profile", values="weight_resampled")[["low", "mid", "high"]]
    piv = piv[(piv > 0.005).any(axis=1)].sort_values("mid", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    bottom = np.zeros(3)
    cmap = plt.get_cmap("tab20")
    for i, t in enumerate(piv.index):
        ax.bar(piv.columns, piv.loc[t], bottom=bottom, label=t, color=cmap(i % 20))
        bottom += piv.loc[t].to_numpy()
    ax.set_ylabel("weight")
    ax.set_title("Robo-Kit weights by risk profile (resampled)")
    ax.legend(ncol=2, fontsize=8, loc="center left", bbox_to_anchor=(1, 0.5))
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_frontier(frontier: pd.DataFrame, results: dict, opt: RoboKitOptimizer, path: str) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(frontier.exp_vol, frontier.exp_return, "-o", ms=3, label="constrained frontier (lam grid)")
    for p, r in results.items():
        ax.scatter(r.exp_vol, r.exp_return, s=80, zorder=5, label=f"{p} aversion (lam={r.risk_aversion:.1f})")
    tbl = opt.asset_table()
    ax.scatter(tbl.exp_vol, tbl.exp_return, s=12, c="grey", alpha=0.6, label="individual ETFs (model E[r])")
    for t, row in tbl.iterrows():
        ax.annotate(t.replace(".TO", ""), (row.exp_vol, row.exp_return), fontsize=6, alpha=0.7)
    ax.set_xlabel("expected volatility (annual)")
    ax.set_ylabel("expected return (annual, model-implied)")
    ax.set_title("Model-implied frontier and the three profiles")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_bands(res, path: str) -> None:
    b = res.weight_band.join(res.weights.rename("weight")).sort_values("weight", ascending=False)
    b = b[b.weight > 0.005]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.errorbar(range(len(b)), b.weight, yerr=[b.weight - b.q05, b.q95 - b.weight], fmt="o", capsize=3)
    ax.set_xticks(range(len(b)))
    ax.set_xticklabels(b.index, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("weight (5%-95% band over resampled histories)")
    ax.set_title("How sure is the model? Mid-risk weights with resampling bands")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_mu_comparison(comp: pd.DataFrame, path: str) -> None:
    c = comp[(comp > 0.005).any(axis=1)]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    c.plot.bar(ax=ax, width=0.8)
    ax.set_ylabel("weight (mid profile)")
    ax.set_title("Same covariance, same risk aversion: what changes when mu comes from history vs a model")
    ax.legend(["sample mean (plug-in)", "Bayes-Stein shrinkage", "equilibrium (Robo-Kit)"], fontsize=8)
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--n-boot", type=int, default=500)
    a = ap.parse_args()
    main(refresh=a.refresh, n_boot=a.n_boot)
