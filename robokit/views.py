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


def _refill(w: np.ndarray, room: np.ndarray, mass: float) -> np.ndarray | None:
    """Give ``mass`` back to the held funds in proportion to their weights, never past ``room``; None if it cannot."""
    w = w.copy()
    for _ in range(100):
        if mass <= 1e-12:
            return w
        live = (w > 0) & (room - w > 1e-12)
        if not live.any():
            return None
        add = np.minimum(mass * w[live] / w[live].sum(), (room - w)[live])
        w[live] += add
        mass -= float(add.sum())
    return w if mass <= 1e-9 else None


def bound_tilt_clean(
    w0: pd.Series,
    w1: pd.Series,
    sigma: np.ndarray,
    min_weight: float = 0.0,
    protected: set[str] | None = None,
    ub: pd.Series | None = None,
    groups: list[tuple[list[str], float]] | None = None,
    te_budget: float = TE_BUDGET,
    max_tilt: float = MAX_TILT,
) -> tuple[pd.Series, dict]:
    """The bounded tilt of ``bound_tilt``, with the portfolio rules applied to the result.

    After the move w0 + s (w1 - w0), positions under ``min_weight`` are removed (never the ``protected`` ones:
    forced funds and positions the no-view mix holds below the minimum on purpose), and their weight goes back
    to the held funds in proportion, never past a fund's limit ``ub``. The scale s is the largest value in
    [0, s_max] whose result keeps the tracking error and the largest move within budget, every weight within
    its limit and each group within its cap. If no s > 0 works, the result is w0 itself (scale 0)."""
    protected = protected or set()
    names = list(w0.index)
    ubv = np.ones(len(names)) if ub is None else ub.reindex(names).fillna(1.0).to_numpy()
    w0v = w0.to_numpy()
    d = (w1 - w0).to_numpy()
    te = float(np.sqrt(max(d @ sigma @ d, 0.0)))
    biggest = float(np.abs(d).max()) if len(d) else 0.0
    s_max = 1.0
    if te > te_budget:
        s_max = min(s_max, te_budget / te)
    if biggest > max_tilt:
        s_max = min(s_max, max_tilt / biggest)

    def clean(s: float) -> tuple[np.ndarray | None, list[str]]:
        w = np.clip(w0v + s * d, 0.0, None)
        small = [i for i, t in enumerate(names) if 0 < w[i] < min_weight - 1e-9 and t not in protected] if min_weight > 0 else []
        if not small:
            return w / w.sum(), []
        mass = float(w[small].sum())
        w[small] = 0.0
        if not (w > 0).any():
            return None, []
        return _refill(w, ubv, mass), [names[i] for i in small]

    def ok(w: np.ndarray | None) -> bool:
        if w is None or not np.isfinite(w).all() or abs(w.sum() - 1.0) > 1e-9:
            return False
        dd = w - w0v
        if float(np.sqrt(max(dd @ sigma @ dd, 0.0))) > te_budget + 1e-9 or float(np.abs(dd).max()) > max_tilt + 1e-9:
            return False
        if (w > ubv + 1e-9).any():
            return False
        return all(float(sum(w[names.index(t)] for t in m if t in names)) <= cap + 1e-9 for m, cap in (groups or []))

    s, (w, small) = s_max, clean(s_max)
    if not ok(w):  # search down to the largest scale whose result obeys every rule
        lo, hi = 0.0, s_max
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            if ok(clean(mid)[0]):
                lo = mid
            else:
                hi = mid
        s, (w, small) = lo, clean(lo)
        if lo == 0.0 or not ok(w):  # nothing works: the no-view mix, exactly
            s, w, small = 0.0, w0v.copy(), []
    w = pd.Series(w, index=names)
    dd = (w - w0).to_numpy()
    return w, {
        "tracking_error_before": round(te, 4),
        "largest_move_before": round(biggest, 4),
        "scale": round(s, 4),
        "tracking_error_after": round(float(np.sqrt(max(dd @ sigma @ dd, 0.0))), 4),
        "largest_move_after": round(float(np.abs(dd).max()) if len(dd) else 0.0, 4),
        "dropped_after_tilt": [t for t in small if w0.get(t, 0.0) > 0 or w1.get(t, 0.0) > 0],
        "budget": {"tracking_error": te_budget, "per_fund": max_tilt, "min_weight": min_weight},
    }
