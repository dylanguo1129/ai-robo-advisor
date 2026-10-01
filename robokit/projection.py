"""Forward projections: a range of possible futures, not a forecast.

Method (docs/research/methods-signals.md section 6):

1. Each fund's monthly history over the estimation window is de-meaned and
   re-centred on its long-run planning assumption net of its fee
   (``robokit.cma``; FP Canada 2026 for Canada). Geometric assumptions are
   converted to arithmetic monthly means (add half the monthly variance), as
   FP Canada's guidelines say to do for Monte Carlo work.
2. Blocks of months are drawn with replacement (stationary bootstrap, mean
   block six months) so crashes and calm spells cluster the way they did.
   Each draw applies the same months to every fund, which keeps their
   co-movement.
3. The portfolio is rebalanced monthly to its weights; contributions are added
   at the end of each month.

What is reported, and why (Betterment, Wealthsimple, Kitces, Benartzi and
Thaler; see the research file):
* 10th to 90th percentile fan and the median, never a single line;
* the one-year range and the long-horizon range side by side;
* annualised return ranges by holding period (1, 3, 5, 10 years);
* for a goal: "chance you would need to adjust" (save more, spend less, wait
  longer) and how large the typical shortfall is, never "success %".
"""

from __future__ import annotations

import numpy as np

DISCLOSURE = {
    "en": (
        "The projections are hypothetical in nature, do not reflect actual investment results and are not "
        "guarantees of future results. They come from re-sampling past monthly returns, re-centred on published "
        "planning assumptions after fund fees. Results may vary with each use and over time. Other investments "
        "not considered may have characteristics similar or superior to those analysed."
    ),
}


def _stationary_rows(rng: np.random.Generator, t: int, n: int, block: float) -> np.ndarray:
    rows = np.empty(n, dtype=int)
    i = 0
    p = 1.0 / block
    while i < n:
        start = rng.integers(0, t)
        length = rng.geometric(p)
        take = min(length, n - i)
        rows[i : i + take] = (start + np.arange(take)) % t
        i += take
    return rows


def recentre(asset_returns: np.ndarray, annual_geo: np.ndarray) -> np.ndarray:
    """De-mean each column and add the arithmetic monthly mean implied by the geometric annual assumption."""
    X = np.asarray(asset_returns, dtype=float)
    var_m = X.var(axis=0, ddof=1)
    geo_m = (1 + np.asarray(annual_geo, dtype=float)) ** (1 / 12) - 1
    arith_m = geo_m + 0.5 * var_m
    return X - X.mean(axis=0) + arith_m


def project(
    asset_returns: np.ndarray,
    weights: np.ndarray,
    annual_geo_net: np.ndarray,
    amount: float = 10_000.0,
    monthly_contribution: float = 0.0,
    years: int = 10,
    goal: float | None = None,
    n_paths: int = 2000,
    block: float = 6.0,
    seed: int = 7,
) -> dict:
    X = recentre(asset_returns, annual_geo_net)
    w = np.asarray(weights, dtype=float)
    port = X @ w
    t = len(port)
    months = int(years * 12)
    paths = np.empty((n_paths, months + 1))
    growth = np.empty((n_paths, months))  # pure return paths (no contributions) for holding-period ranges
    lasting = np.full(n_paths, months)  # months of withdrawals paid in full (months = it lasted)
    for p in range(n_paths):
        # one generator per path: the first year of every path is the same whatever the horizon,
        # so changing the number of years never reshuffles the one-year range
        rng = np.random.default_rng([seed, p])
        r = port[_stationary_rows(rng, t, months, block)]
        growth[p] = r
        v = amount
        paths[p, 0] = v
        for m in range(months):
            v = v * (1 + r[m]) + monthly_contribution
            if v < 0:  # a withdrawal the money could not cover: that month was not paid in full
                if lasting[p] == months:
                    lasting[p] = m
                v = 0.0
            paths[p, m + 1] = v
    qs = (10, 25, 50, 75, 90)
    yearly = [{"year": y, **{f"p{q}": round(float(np.percentile(paths[:, y * 12], q)), 2) for q in qs}} for y in range(years + 1)]
    final = paths[:, -1]
    invested = amount + monthly_contribution * months if monthly_contribution >= 0 else None

    def ann_range(h):
        if h * 12 > months:
            return None
        cum = np.prod(1 + growth[:, : h * 12], axis=1)
        ann = cum ** (1 / h) - 1
        return {
            "years": h,
            "p10": round(float(np.percentile(ann, 10)), 4),
            "p50": round(float(np.percentile(ann, 50)), 4),
            "p90": round(float(np.percentile(ann, 90)), 4),
        }

    one = np.prod(1 + growth[:, :12], axis=1) - 1 if months >= 12 else None
    med_growth = np.percentile(np.prod(1 + growth, axis=1), 50) ** (1 / years) - 1
    out = {
        "years": years,
        "amount": amount,
        "monthly_contribution": monthly_contribution,
        "invested": None if invested is None else round(invested, 2),
        "final": {f"p{q}": round(float(np.percentile(final, q)), 2) for q in qs},
        "median_annual_return": round(float(med_growth), 4),
        "one_year": None
        if one is None
        else {
            "p5": round(float(np.percentile(one, 5)), 4),
            "p10": round(float(np.percentile(one, 10)), 4),
            "p50": round(float(np.percentile(one, 50)), 4),
            "p90": round(float(np.percentile(one, 90)), 4),
            "prob_loss": round(float((one < 0).mean()), 3),
        },
        "by_holding_period": [r for r in (ann_range(h) for h in (1, 3, 5, 10)) if r],
        "prob_below_invested": None if invested is None else round(float((final < invested).mean()), 3),
        # value after twelve months including the monthly adds or withdrawals (what the person will see)
        "one_year_value": None if months < 12 else {f"p{q}": round(float(np.percentile(paths[:, 12], q)), 2) for q in (5, 10, 50, 90)},
        "yearly": yearly,
        "n_paths": n_paths,
        "method": "stationary bootstrap (mean block 6 months) of monthly fund returns, re-centred on planning assumptions net of fees",
        "disclosure": DISCLOSURE,
    }
    if out["one_year"]:
        out["one_year_dollars"] = {
            k: round(amount * (1 + v)) for k, v in out["one_year"].items() if k[1:].isdigit()
        }  # p5..p90, not prob_loss
    if monthly_contribution < 0:
        out["withdrawal"] = {
            "monthly": round(-monthly_contribution, 2),
            "chance_lasts": round(float((lasting >= months).mean()), 3),
            "p10_months": int(np.percentile(lasting, 10)),
            "p50_months": int(np.percentile(lasting, 50)),
            "months": months,
        }
    if goal:
        short = final < goal
        out["goal"] = goal
        out["chance_need_to_adjust"] = round(float(short.mean()), 3)
        out["median_shortfall"] = round(float(np.median(goal - final[short])), 2) if short.any() else 0.0
    return out
