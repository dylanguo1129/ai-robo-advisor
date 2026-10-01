"""Robo-Kit portfolio optimizer.

Allocation engine for the MMAI 823 "AI Robo-Advisor Kit" team project
(Task 4 of the brief: portfolio weights for the selected ETFs as a function of
the client's low / mid / high risk aversion).

Public API
----------
RoboKitOptimizer   estimate inputs once, then optimize any subset of ETFs for
                   any risk-aversion level, with resampling and diagnostics.
load_prices, to_monthly_returns   data hygiene helpers.
walk_forward_backtest             honest out-of-sample comparison of methods.
export_web_spec                   JSON hand-off for the browser prototype.
"""

from .data import download_prices, load_prices, to_monthly_returns
from .estimators import (
    black_litterman_posterior,
    equilibrium_returns,
    james_stein_returns,
    ledoit_wolf_constant_correlation,
    ledoit_wolf_identity,
    market_risk_aversion,
    qis,
    sample_covariance,
)
from .portfolio import OptimizationResult, RiskProfiles, RoboKitOptimizer
from .solver import project_capped_simplex, solve_qp

__all__ = [
    "RoboKitOptimizer",
    "OptimizationResult",
    "RiskProfiles",
    "download_prices",
    "load_prices",
    "to_monthly_returns",
    "sample_covariance",
    "ledoit_wolf_identity",
    "ledoit_wolf_constant_correlation",
    "qis",
    "james_stein_returns",
    "equilibrium_returns",
    "black_litterman_posterior",
    "market_risk_aversion",
    "project_capped_simplex",
    "solve_qp",
]
