"""Optimizer hand-off files in the format the team's interface design asks for.

    python scripts/export_handoff.py              # Canadian reference shelf
    python scripts/export_handoff.py --market US  # US reference shelf

Writes to output/v2/handoff/:
  covariance_<M>.csv        annualized covariance of monthly returns (Ledoit-Wolf shrunk), ticker x ticker
  expected_returns_<M>.csv  one row per fund: equilibrium expected excess return, total return, fee, prior weight
  constants_<M>.json        market risk aversion, the three lambda values (low / mid / high risk aversion)
                            with their target volatilities, and the caps

The three lambda values are calibrated on the reference shelf: each one makes the shelf hit its
level's target volatility. On a different shortlist the same lambda gives a different risk, which is
why the engine re-solves lambda for every request (robokit/engine.py, _calibrate).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from optimizer import RoboKitOptimizer  # noqa: E402
from robokit import __version__, engine  # noqa: E402
from robokit.config import DELTA, OUTPUT_DIR  # noqa: E402
from robokit.shelf import prior_share  # noqa: E402

# The team's table is in risk aversion; the engine's presets are in risk appetite (profile.PRESETS).
AVERSION_TO_PRESET = {"low": "high", "mid": "mid", "high": "low"}


def fitted(market: str):
    """The optimizer exactly as build_portfolio sets it up for the reference shelf (no swaps, no satellites)."""
    req = engine.Request(market=market)
    shelf, core, sats = engine.select_funds(req)
    X, _, _ = engine.build_returns(market, shelf, core, sats)
    tickers = core + [t for t in sats if t in X.columns]
    prior = pd.Series(0.0, index=tickers)
    for _, row in shelf.iterrows():
        prior[row.ticker] += prior_share(market, row.sleeve)
    prior = prior / prior.sum()
    cash_t = shelf.loc[shelf.role == "cash", "ticker"]
    cash_t = cash_t.iloc[0] if len(cash_t) else None
    rf, rf_src = engine.risk_free(market)
    opt = RoboKitOptimizer(
        X[tickers], rf=rf, prior_weights=prior, delta=DELTA, w_max=req.max_weight, cash_ticker=cash_t, cash_max=1.0, mu_method="equilibrium"
    ).fit()
    return opt, shelf, rf_src


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--market", default="CA", choices=["CA", "US"])
    a = ap.parse_args()
    out = OUTPUT_DIR / "handoff"
    out.mkdir(parents=True, exist_ok=True)
    m = a.market

    opt, shelf, rf_src = fitted(m)
    opt.sigma.round(8).rename_axis("ticker").to_csv(out / f"covariance_{m}.csv")

    info = shelf.drop_duplicates("ticker").set_index("ticker")
    rows = pd.DataFrame(
        {
            "sleeve": info["sleeve"].reindex(opt.tickers),
            "asset_class": info["asset_class"].reindex(opt.tickers),
            "prior_weight": opt.prior_weights.round(6),
            "expected_excess_return": opt.mu_excess.round(6),
            "expected_total_return": (opt.mu_excess + opt.rf).round(6),
            "volatility": pd.Series(opt.sigma.to_numpy().diagonal() ** 0.5, index=opt.tickers).round(6),
        }
    )
    if "mer" in info:
        rows.insert(2, "mer", info["mer"].reindex(opt.tickers).round(6))
    rows.index.name = "ticker"
    rows.to_csv(out / f"expected_returns_{m}.csv")

    presets = {}
    for aversion, preset in AVERSION_TO_PRESET.items():
        r = engine.build_portfolio({"market": m, "profile": preset, "resample": False})
        presets[aversion] = {
            "level": r["risk"]["level"],
            "label": r["risk"]["label"],
            "target_volatility": r["risk"]["target_vol"],
            "lambda": r["risk"]["lambda"],
            "cash_cap": r["risk"]["cash_cap"],
            "weights": {h["ticker"]: round(h["weight"], 4) for h in r["holdings"]},  # same keys as the CSV files
        }
    # Caps that hold at every level; the cash cap depends on the level (risk_aversion[*].cash_cap).
    sleeve_caps = {t: c for t, c in r["method"]["sleeve_caps"].items() if t != opt.cash_ticker}

    constants = {
        "market": m,
        "engine_version": __version__,
        "data_snapshot": engine.snapshot_id(),
        "data_source": engine.data_source(),  # 'local' cache or the committed 'snapshot'; rates differ by a month between them
        "history_window": [str(opt.returns.index[0].date()), str(opt.returns.index[-1].date())],
        "months": int(len(opt.returns)),
        "risk_free": opt.rf,
        "risk_free_source": rf_src,
        "delta": opt.delta,
        "covariance": opt.cov_info,
        "objective": "maximize mu'w - (lambda/2) w'Sigma w, weights sum to 1, no shorting",
        "min_weight_rule": "funds under min_weight_per_fund are dropped and the problem is solved again at the same lambda "
        "(up to 3 rounds); the weights in risk_aversion are after this step",
        "weights_note": "the weights in risk_aversion are one estimate (resampling off); the product averages 200 resampled "
        "histories at the same lambda, so its weights differ by a few tenths of a point",
        "risk_aversion": presets,
        "max_weight_per_fund": engine.Request().max_weight,
        "min_weight_per_fund": engine.Request().min_weight,
        "sleeve_caps": sleeve_caps,
        "level_rule": "target volatility = level / 5 x volatility of the stock part of the policy prior",
        "note": "Lambda is calibrated on this shelf. On another shortlist the engine re-solves it to hit the same target volatility.",
    }
    (out / f"constants_{m}.json").write_text(json.dumps(constants, indent=1, default=float), encoding="utf-8")

    print(f"Wrote {out}")
    for k, v in presets.items():
        print(
            f"  {k:>4} risk aversion: level {v['level']:.0f} ({v['label']}), target vol {v['target_volatility']:.1%}, lambda {v['lambda']:.2f}"
        )
    print(f"  {len(opt.tickers)} funds, {len(opt.returns)} months, max weight per fund {constants['max_weight_per_fund']:.0%}")


if __name__ == "__main__":
    main()
