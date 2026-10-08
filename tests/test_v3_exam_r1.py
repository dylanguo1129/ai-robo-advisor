"""Regression tests for the findings of examination round 1 (two cross-family examiners; web/test_safety.mjs and
web/test_engine.mjs carry the browser side). Each test reproduces the reported trigger."""

from __future__ import annotations

import numpy as np
import pytest

from optimizer.solver import solve_qp_pgd
from robokit import tools
from robokit.engine import Request, build_portfolio, validate_request
from robokit.errors import RoboKitInputError
from robokit.rebalance import rebalance


def _us(**kw):
    return build_portfolio(Request(market="US", risk_level=3, resample=False, **kw))


# ------------------------------------------------------------------ swaps keep the slot's asset class; narrow funds stay own picks
def test_a_crypto_fund_cannot_take_a_broad_funds_slot():
    p = _us(swaps={"us_equity": "BITO"})
    assert "BITO" not in {h["ticker"] for h in p["holdings"]}
    assert any("only as one of your own picks" in n["en"] for n in p["notes"])


@pytest.mark.parametrize("slot,fund", [("us_equity", "BND"), ("us_reit", "GLDM")])
def test_a_swap_must_keep_the_slots_asset_class_and_region(slot, fund):
    p = _us(swaps={slot: fund})
    assert any("does not hold what the slot holds" in n["en"] for n in p["notes"])


def test_a_like_for_like_swap_still_works():
    assert "QQQ" in {h["ticker"] for h in _us(swaps={"us_equity": "QQQ"})["holdings"]}


# ------------------------------------------------------------------ malformed maps are input errors, never crashes
@pytest.mark.parametrize("field", ["minimums", "fixed_weights"])
def test_a_list_where_a_map_belongs_is_an_input_error(field):
    with pytest.raises(RoboKitInputError):
        validate_request(Request(**{field: [0.1]}))
    out = tools.call("build_portfolio", {"market": "CA", "level": 3, field: [0.1]})
    assert "error" in out


# ------------------------------------------------------------------ the solver's answer is inside every bound exactly
def test_solver_answers_respect_every_bound():
    rng = np.random.default_rng(7)
    worst_box, worst_sum = 0.0, 0.0
    for _ in range(300):
        n = int(rng.integers(2, 9))
        a = rng.normal(size=(n, n))
        sigma = a @ a.T / n + 0.01 * np.eye(n)
        mu = rng.normal(0.03, 0.02, n)
        ub = rng.uniform(0.15, 0.6, n)
        ub[0] = max(ub[0], 1.0 - ub[1:].sum() + 1e-12)  # some problems only just feasible
        lb = np.where(rng.random(n) < 0.2, 0.02, 0.0)
        w = solve_qp_pgd(sigma, mu, float(rng.uniform(0.5, 20)), lb, ub)
        worst_box = max(worst_box, float(np.max(w - ub)), float(np.max(lb - w)))
        worst_sum = max(worst_sum, abs(w.sum() - 1.0))
    assert worst_box <= 0.0 and worst_sum < 1e-12


# ------------------------------------------------------------------ the rebalancer's cash covers the orders and their cost
def test_orders_and_their_cost_fit_in_the_cash():
    r = rebalance({"A": 1.0}, {}, {"A": 100.0}, cash=100.0, min_trade=0, cost_bps=10)
    assert r["rows"][0]["action"] == "hold" and r["cash_after"] >= 0
    r = rebalance({"A": 1.0}, {}, {"A": 100.0}, cash=100.2, min_trade=0, cost_bps=10)
    assert r["rows"][0]["units"] == 1 and r["cash_after"] == pytest.approx(0.1, abs=1e-9)


# ------------------------------------------------------------------ the brief's settings by name, both ways round
@pytest.mark.parametrize("name,level", [("high_aversion", 2), ("mid_aversion", 3), ("low_aversion", 4), ("low", 2), ("high", 4)])
def test_presets_by_appetite_or_aversion(name, level):
    assert build_portfolio(Request(market="CA", profile=name, resample=False))["risk"]["level"] == level
