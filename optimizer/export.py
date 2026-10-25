"""Hand-off files for the browser prototype (Task 5 of the brief).

The web page needs: the tickers, annualized expected excess returns, the
annualized covariance matrix, the risk-free rate, the market risk aversion
delta and the three multipliers, the per-ETF cap and the cash ticker. With
those it can run the same projected-gradient solver in JavaScript. The test
vectors let the front-end developer check the port against Python.
"""

from __future__ import annotations

import json
from datetime import date

from .portfolio import RoboKitOptimizer


def export_web_spec(opt: RoboKitOptimizer, path: str, test_cases: list[dict] | None = None, extra: dict | None = None) -> dict:
    opt._require_fit()
    spec = {
        "generated_on": date.today().isoformat(),
        "history_window": [str(opt.returns.index[0].date()), str(opt.returns.index[-1].date())],
        "n_months": int(len(opt.returns)),
        "tickers": opt.tickers,
        "rf": opt.rf,
        "market_premium": opt.market_premium,
        "delta": opt.delta,
        "profiles": opt.profiles.as_dict(),
        "w_max": opt.w_max,
        "cash_ticker": opt.cash_ticker,
        "cov_method": opt.cov_info,
        "mu_method": opt.mu_info,
        "prior_weights": {t: float(v) for t, v in opt.prior_weights.items()},
        "mu_excess": {t: float(v) for t, v in opt.mu_excess.items()},
        "sigma": [[float(v) for v in row] for row in opt.sigma.to_numpy()],
        "solver": {
            "objective": "minimize (lam/2) w'Sigma w - mu' w  s.t. sum w = 1, 0 <= w <= cap (cap = 1 for the cash ticker)",
            "algorithm": "accelerated projected gradient (FISTA with adaptive restart) in the preconditioned space "
            "v = D w, D = diag(sqrt(diag(Sigma))); exact projection onto the weighted capped simplex (sorted breakpoints)",
            "step_size": "1 / (lam * largest eigenvalue of the correlation matrix D^-1 Sigma D^-1)",
            "stop": "max |w_k+1 - w_k| < 1e-10, or 10000 iterations with a projected-gradient residual below 1e-6 "
            "(otherwise SolverNotConverged)",
            "lam": "profile multiplier x delta",
        },
        "test_cases": test_cases or [],
    }
    if extra:
        spec.update(extra)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=1)
    return spec


def make_test_cases(opt: RoboKitOptimizer, cases: list[dict]) -> list[dict]:
    """Each case: {name, profile, tickers, forced?, excluded?, w_max?}. Weights
    are computed *without* resampling so the JS port can match them exactly."""
    out = []
    for c in cases:
        r = opt.optimize(
            c["profile"], tickers=c.get("tickers"), forced=c.get("forced"), excluded=c.get("excluded"), w_max=c.get("w_max"), resample=False
        )
        out.append(
            {
                "name": c["name"],
                "input": {k: v for k, v in c.items() if k != "name"},
                "lam": r.risk_aversion,
                "expected_weights": {t: round(float(w), 6) for t, w in r.weights.items()},
                "expected_vol": round(r.exp_vol, 6),
                "expected_return": round(r.exp_return, 6),
                "tolerance": 1e-4,
            }
        )
    return out
