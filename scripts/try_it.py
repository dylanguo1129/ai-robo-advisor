"""Hands-on demo of the Robo-Kit optimizer.

python scripts/try_it.py                                  # all 20 ETFs, three profiles
python scripts/try_it.py --profile high                   # one profile
python scripts/try_it.py --tickers XIC.TO VFV.TO ZAG.TO PSA.TO --profile mid
python scripts/try_it.py --tickers XIC.TO VFV.TO XEF.TO --profile high      # cautious client, all-equity shortlist
python scripts/try_it.py --force CGL.TO=0.10 --exclude XHY.TO ZEB.TO
python scripts/try_it.py --cap 0.20 --no-resample
python scripts/try_it.py --list                           # show the universe
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from optimizer import RoboKitOptimizer, load_prices, to_monthly_returns  # noqa: E402

DATA = os.path.join(ROOT, "data")


def load_optimizer():
    universe = pd.read_csv(os.path.join(DATA, "universe.csv")).set_index("ticker")
    info = pd.read_csv(os.path.join(DATA, "etf_info_yf.csv")).set_index("ticker")
    panel = to_monthly_returns(load_prices(os.path.join(DATA, "prices_daily_adjclose.csv")), start="2016-01-01")
    aum = info["total_assets"].reindex(panel.returns.columns)
    cls = universe["asset_class"].reindex(panel.returns.columns)
    for t in aum.index[aum.isna()]:
        aum[t] = aum[(cls == cls[t]) & aum.notna()].median()
    opt = RoboKitOptimizer(panel.returns, rf=0.0225, prior_weights=aum / aum.sum(), delta=2.5, w_max=0.35, cash_ticker="PSA.TO").fit()
    return opt, universe, panel


def show(res, universe, opt):
    w = res.weights[res.weights > 0.001].sort_values(ascending=False)
    rc = res.risk_contributions
    print(f"\n=== profile: {res.profile}   risk aversion lam = {res.risk_aversion:.2f} ===")
    print(
        f"expected return {res.exp_return:6.2%}   expected volatility {res.exp_vol:6.2%}   Sharpe {res.sharpe:.2f}   effective # of holdings {res.effective_n:.1f}"
    )
    rows = []
    for t, v in w.items():
        row = {
            "ticker": t,
            "name": universe.loc[t, "name"][:38],
            "class": universe.loc[t, "asset_class"],
            "weight": f"{v:6.1%}",
            "risk share": f"{rc[t]:6.1%}",
        }
        if res.weight_band is not None:
            row["band 5%-95%"] = f"{res.weight_band.loc[t, 'q05']:5.1%} - {res.weight_band.loc[t, 'q95']:5.1%}"
        rows.append(row)
    print(pd.DataFrame(rows).to_string(index=False))
    eq = sum(v for t, v in res.weights.items() if universe.loc[t, "asset_class"] in ("Equity", "Real estate"))
    fi = sum(v for t, v in res.weights.items() if universe.loc[t, "asset_class"] == "Fixed income")
    cash = sum(v for t, v in res.weights.items() if universe.loc[t, "asset_class"] == "Cash")
    print(f"asset mix: equity {eq:.0%} | fixed income {fi:.0%} | cash {cash:.0%} | other {1 - eq - fi - cash:.0%}")
    for n in res.notes:
        print("  -", n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", choices=["low", "mid", "high", "all"], default="all")
    ap.add_argument("--tickers", nargs="*", help="the client's shortlist (default: whole universe)")
    ap.add_argument("--force", nargs="*", default=[], help="TICKER=minweight, e.g. CGL.TO=0.10")
    ap.add_argument("--exclude", nargs="*", default=[])
    ap.add_argument("--cap", type=float, default=None, help="max weight per ETF (default 0.35)")
    ap.add_argument("--no-resample", action="store_true", help="point estimate only (faster, no bands)")
    ap.add_argument("--list", action="store_true", help="print the universe and exit")
    a = ap.parse_args()

    opt, universe, panel = load_optimizer()
    if a.list:
        tbl = opt.asset_table().join(universe[["name", "asset_class"]])
        tbl = tbl[["name", "asset_class", "prior_weight", "exp_return", "exp_vol", "hist_ann_return", "hist_ann_vol"]]
        print(tbl.round(3).to_string())
        return
    print(panel.summary())
    print(
        f"model: {opt.cov_info['method']} covariance (shrinkage {opt.cov_info.get('shrinkage', float('nan')):.2f}), equilibrium mu, delta {opt.delta}, rf {opt.rf:.2%}"
    )
    forced = {kv.split("=")[0]: float(kv.split("=")[1]) for kv in a.force}
    profiles = ["low", "mid", "high"] if a.profile == "all" else [a.profile]
    for p in profiles:
        res = opt.optimize(p, tickers=a.tickers, forced=forced, excluded=a.exclude, w_max=a.cap, resample=not a.no_resample, n_boot=200)
        show(res, universe, opt)


if __name__ == "__main__":
    main()
