"""Views: how an opinion ("I think gold beats bonds by 2% a year") enters the portfolio.

Machinery, not a strategy (docs/research/methods-signals.md section 2):

* Black-Litterman blends the equilibrium returns with the view, weighted by
  a confidence from 0% to 100%. Confidence uses the closed form of Idzorek's
  method (Walters): omega_k = tau * (1 - c) / c * p_k' Sigma p_k. At 0% the
  view is ignored (equilibrium weights); at 100% the view is imposed exactly.
* Whatever the view says, the resulting tilt is bounded against the no-view
  portfolio: tracking error at most 1% a year and no single fund moved by
  more than 5 percentage points. If the view would move further, the tilt is
  scaled back proportionally and the result says so.
* Views are off by default. Market news, sentiment and geopolitics never
  become views automatically; only a person's own, explicit view does, and
  its effect is shown next to the no-view portfolio.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TE_BUDGET = 0.01
MAX_TILT = 0.05
TAU = 0.05


def views_to_bl(views: list[dict], tickers: list[str], opt) -> tuple:
    """User views -> (P, Q, Omega, info). ``opt`` must be fitted (its shrunk Sigma is used).

    A view is {"type": "absolute", "ticker": T, "return": 0.07, "confidence": 0.5}
    (annual total return) or {"type": "relative", "long": A, "short": B,
    "difference": 0.02, "confidence": 0.5}. Confidence is 0..1.
    """
    idx = {t: i for i, t in enumerate(tickers)}
    sigma = opt.sigma.loc[tickers, tickers].to_numpy()
    rows, q, om, info = [], [], [], []
    for v in views:
        c = float(v.get("confidence", 0.5))
        if not 0.0 <= c <= 1.0:
            info.append({"view": v, "used": False, "why": "confidence must be between 0 and 1"})
            continue
        if c == 0.0:
            info.append({"view": v, "used": False, "why": "0% confidence: the view has no effect"})
            continue
        p = np.zeros(len(tickers))
        if v.get("type") == "relative":
            a, b = v.get("long"), v.get("short")
            if a not in idx or b not in idx:
                info.append({"view": v, "used": False, "why": "both funds must be in the portfolio"})
                continue
            p[idx[a]], p[idx[b]] = 1.0, -1.0
            q.append(float(v["difference"]))
        else:
            t = v.get("ticker")
            if t not in idx:
                info.append({"view": v, "used": False, "why": "fund not in the portfolio"})
                continue
            p[idx[t]] = 1.0
            q.append(float(v["return"]) - opt.rf)
        alpha = (1.0 - c) / c if c < 1.0 else 1e-9
        om.append(max(TAU * alpha * float(p @ sigma @ p), 1e-12))
        rows.append(p)
        info.append({"view": v, "used": True})
    if not rows:
        return None, None, None, info
    return np.vstack(rows), np.array(q), np.diag(om), info


def bound_tilt(
    w0: pd.Series, w1: pd.Series, sigma: np.ndarray, te_budget: float = TE_BUDGET, max_tilt: float = MAX_TILT
) -> tuple[pd.Series, dict]:
    """Scale the move from w0 (no views) to w1 (with views) so it stays inside the budgets."""
    d = (w1 - w0).to_numpy()
    te = float(np.sqrt(max(d @ sigma @ d, 0.0)))
    biggest = float(np.abs(d).max()) if len(d) else 0.0
    s = 1.0
    if te > te_budget:
        s = min(s, te_budget / te)
    if biggest > max_tilt:
        s = min(s, max_tilt / biggest)
    w = w0 + s * (w1 - w0)
    w = w.clip(lower=0.0)
    w = w / w.sum()
    return w, {
        "tracking_error_before": round(te, 4),
        "largest_move_before": round(biggest, 4),
        "scale": round(s, 4),
        "tracking_error_after": round(te * s, 4),
        "budget": {"tracking_error": te_budget, "per_fund": max_tilt},
    }
