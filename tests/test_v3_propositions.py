"""The paper's propositions, checked numerically on the reference shelf (the derivations are in the paper's appendix).

1. The weights depend on lambda and delta only through lambda / delta (pi = delta Sigma w0 enters linearly), so with
   lambda calibrated to a volatility target, delta does not change the mix.
2. Scaling the covariance by c > 0 (x12 to annualise, x T/(T-1)) scales pi by c too: the weights at a given lambda do
   not change.
3. The single solve's volatility falls as lambda rises, so bisection on lambda is valid.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from optimizer import RoboKitOptimizer
from robokit.engine import Request, build_returns, select_funds
from robokit.shelf import prior_share


@pytest.fixture(scope="module")
def shelf():
    req = Request(market="CA", risk_level=3)
    s, core, _ = select_funds(req)
    X, _, _ = build_returns("CA", s, core, [])
    prior = pd.Series([sum(prior_share("CA", r.sleeve) for _, r in s.iterrows() if r.ticker == t) for t in X.columns], index=X.columns)
    return X, prior / prior.sum()


def _w(X, prior, lam, delta=2.5):
    o = RoboKitOptimizer(X, rf=0.0, prior_weights=prior, delta=delta, w_max=0.5, cash_ticker="CASH.TO", cash_max=1.0).fit()
    return o.optimize(lam, resample=False).weights.reindex(X.columns).fillna(0.0).to_numpy()


@pytest.mark.parametrize("delta", [1.0, 4.0])
def test_proposition_1_only_lambda_over_delta_matters(shelf, delta):
    X, prior = shelf
    k = 1.15  # lambda / delta
    assert np.abs(_w(X, prior, k * delta, delta) - _w(X, prior, k * 2.5, 2.5)).max() < 1e-7


@pytest.mark.parametrize("c", [1.0 / 12, 179 / 180, 4.0])
def test_proposition_2_scaling_the_covariance_leaves_the_weights(shelf, c):
    X, prior = shelf
    # returns times sqrt(c) scale the shrunk covariance by c (the shrinkage intensity is scale-free) and pi by c
    assert np.abs(_w(X * np.sqrt(c), prior, 2.9) - _w(X, prior, 2.9)).max() < 1e-7


def test_proposition_3_volatility_falls_as_lambda_rises(shelf):
    X, prior = shelf
    o = RoboKitOptimizer(X, rf=0.0, prior_weights=prior, delta=2.5, w_max=0.5, cash_ticker="CASH.TO", cash_max=1.0).fit()
    # the single solve (no resampling): averaged resampled weights need not be monotone, which is why the final
    # pipeline's calibration brackets the target instead of assuming it (robokit/engine.py _calibrate_final)
    vols = [o.optimize(lam, resample=False).exp_vol for lam in np.geomspace(0.05, 2000, 60)]
    assert all(b <= a + 1e-10 for a, b in zip(vols, vols[1:]))


def test_proposition_1_holds_through_the_final_pipeline():
    """The mix the person gets (minimum position applied) at a given delta and lambda depends only on lambda / delta,
    so with lambda calibrated to the volatility target, delta 1 and delta 4 give the same risk to within the
    calibration tolerance (they differ only where each calibration stops inside its tolerance). This holds while
    lambda stays inside its bounds [0.05, 2000], which are absolute, not relative to delta."""
    from robokit.engine import CAL_TOL, Request, build_portfolio

    req = Request(market="CA", risk_level=3, resample=False)
    a = build_portfolio(req, lean=True, research={"delta": 1.0, "lambda": 1.0 * 1.3})
    b = build_portfolio(req, lean=True, research={"delta": 4.0, "lambda": 4.0 * 1.3})
    names = set(a["weights"]) | set(b["weights"])
    assert max(abs(a["weights"].get(t, 0.0) - b["weights"].get(t, 0.0)) for t in names) < 1e-5
    c1 = build_portfolio(req, lean=True, research={"delta": 1.0})
    c4 = build_portfolio(req, lean=True, research={"delta": 4.0})
    assert c1["calibration"]["within_tolerance"] and c4["calibration"]["within_tolerance"]
    assert abs(c1["volatility"] - c4["volatility"]) <= 2 * CAL_TOL
