"""Property test: seeded random requests never produce a portfolio that breaks its own rules.

Every request either builds or raises one of the engine's own errors. A build always sums to 1, keeps every fund within
its limit (or the limit recorded as relaxed, when relaxing was asked for), keeps own picks within their group cap, keeps
every position at or above the minimum unless a note says why not, and records no relaxation when asked to refuse."""

from __future__ import annotations

import numpy as np
import pytest

from optimizer.errors import InfeasibleConstraints
from robokit import engine
from robokit.engine import Request, build_portfolio
from robokit.errors import RoboKitInputError

N = 60


def _requests(n=N, seed=20261008):
    rng = np.random.default_rng(seed)
    U = engine._load()[0]
    shelves = {m: [r["ticker"] for r in build_portfolio(Request(market=m, risk_level=3, resample=False))["shelf"]] for m in ("CA", "US")}
    out = []
    for _ in range(n):
        market = "CA" if rng.random() < 0.6 else "US"
        pool = list(U[(U.market == market) & U.eligible & (U.asset_class == "Equity") & (U.history_months >= 60)].yahoo)
        req = dict(market=market, resample=False)
        if rng.random() < 0.8:
            req["risk_level"] = float(rng.choice([1, 2, 3, 4, 5, 1.5, 2.5, 3.5, 4.75]))
        else:
            req["target_vol"] = float(rng.uniform(0.01, 0.12))
        if rng.random() < 0.4:
            req["satellites"] = [str(t) for t in rng.choice(pool, size=int(rng.integers(1, 4)), replace=False)]
        if rng.random() < 0.4:
            req["max_weight"] = float(rng.choice([0.08, 0.13, 0.2, 0.3, 0.4, 0.6]))
        if rng.random() < 0.4:
            req["min_weight"] = float(rng.choice([0.0, 0.02, 0.05, 0.1, 0.2, 0.25]))
        if rng.random() < 0.3:
            a, b = rng.choice(shelves[market], size=2, replace=False)
            req["views"] = [
                {
                    "type": "relative",
                    "long": str(a),
                    "short": str(b),
                    "difference": float(rng.uniform(-0.04, 0.04)),
                    "confidence": float(rng.uniform(0.1, 0.9)),
                }
            ]
        if rng.random() < 0.3:
            req["on_infeasible"] = "relax"
        out.append(req)
    return out


@pytest.mark.parametrize("req", _requests(), ids=lambda r: f"{r['market']}-{r.get('risk_level', r.get('target_vol'))}")
def test_random_requests_keep_every_rule(req):
    try:
        p = build_portfolio(Request(**req))
    except (RoboKitInputError, InfeasibleConstraints):
        return
    ws = {h["ticker"]: h["weight"] for h in p["holdings"]}
    assert abs(sum(ws.values()) - 1) < 1e-3
    rel = p["method"]["relaxations"]
    if req.get("on_infeasible", "refuse") == "refuse":
        assert rel == []
    caps = dict(p["method"]["sleeve_caps"])
    for r in rel:
        if r["limit"] == "cap":
            caps[r["ticker"]] = r["applied"]
    mx = req.get("max_weight", 0.5)
    for h in p["holdings"]:
        cap = caps.get(h["ticker"], 1.0 if h["role"] == "cash" else mx)
        assert h["weight"] <= cap + 2e-4, (h["ticker"], h["weight"], cap)
    sat = sum(h["weight"] for h in p["holdings"] if h["role"] == "satellite")
    g = [r["applied"] for r in rel if r["limit"] == "group"]
    assert sat <= (g[-1] if g else p["risk"]["satellite_cap"]) + 2e-4
    mw = req.get("min_weight", 0.02)
    explained = any(("Kept under" in n["en"]) or ("minimum position size was not applied" in n["en"]) for n in p["notes"])
    if mw > 0 and not explained:
        assert min(ws.values()) >= mw - 2e-4, (ws, p["notes"])
