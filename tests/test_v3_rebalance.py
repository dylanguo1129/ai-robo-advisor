"""The rebalancer (v3 Track C1): from holdings, prices and a cash flow to whole-unit orders. web/test_robokit.mjs checks
that the browser port gives the same orders on the cases in web/data/core.json."""

from __future__ import annotations

import numpy as np
import pytest

from robokit.errors import RoboKitInputError
from robokit.rebalance import rebalance

T = {"XIC.TO": 0.3, "ZAG.TO": 0.4, "VFV.TO": 0.25, "CASH.TO": 0.05}
P = {"XIC.TO": 40.12, "ZAG.TO": 13.9, "VFV.TO": 150.3, "CASH.TO": 50.0, "OLD": 20.0}
DRIFTED = {"XIC.TO": 300, "ZAG.TO": 500, "VFV.TO": 40, "CASH.TO": 20, "OLD": 50}


def _rows(r):
    return {x["ticker"]: x for x in r["rows"]}


def test_new_money_into_an_empty_account_buys_the_targets():
    r = rebalance(T, {}, P, flow=25_000)
    assert all(x["action"] in ("buy", "hold") for x in r["rows"])
    assert r["cash_after"] >= 0 and r["largest_gap_after"] < 0.005
    assert r["cash_after"] < max(P.values())  # leftover cash is less than one unit of the dearest fund


def test_in_band_new_money_never_sells():
    near = {"XIC.TO": 200, "ZAG.TO": 760, "VFV.TO": 44, "CASH.TO": 26}
    r = rebalance(T, near, P, flow=3_000)
    assert not any(x["action"] == "sell" for x in r["rows"])
    assert r["notes"][0].startswith("No fund is outside its band")


def test_in_band_and_no_flow_trades_nothing():
    r = rebalance(T, {"XIC.TO": 200, "ZAG.TO": 760, "VFV.TO": 44, "CASH.TO": 26}, P)
    assert r["traded"] == 0 and all(x["action"] == "hold" for x in r["rows"])


def test_out_of_band_funds_go_back_inside_and_nothing_is_pushed_out():
    r = rebalance(T, DRIFTED, P, flow=5_000)
    rows = _rows(r)
    assert rows["OLD"]["action"] == "sell" and rows["OLD"]["units_after"] == 0 and "not in the mix" in rows["OLD"]["reason"]
    for t, w in T.items():
        assert abs(rows[t]["weight_after"] - w) <= rows[t]["band"] + 0.004, (t, rows[t])  # whole units: within a unit or so


def test_a_withdrawal_is_paid_from_overweight_funds_first():
    r = rebalance(T, DRIFTED, P, flow=-8_000)
    assert r["cash_after"] >= 0
    sold = {x["ticker"] for x in r["rows"] if x["action"] == "sell"}
    assert "XIC.TO" in sold and "OLD" in sold  # the two furthest above target
    assert not any(x["action"] == "sell" and x["ticker"] == "ZAG.TO" for x in r["rows"])  # furthest below: never sold


def test_a_withdrawal_larger_than_the_account_is_refused():
    with pytest.raises(RoboKitInputError):
        rebalance(T, {"XIC.TO": 10}, P, flow=-1_000)


def test_small_orders_are_skipped_and_said():
    r = rebalance(T, {"XIC.TO": 200, "ZAG.TO": 760, "VFV.TO": 44, "CASH.TO": 26}, P, flow=60, min_trade=50)
    skipped = [x["ticker"] for x in r["rows"] if "under the minimum trade" in x["reason"]]
    assert skipped == ["ZAG.TO"] and any("Skipped because" in n for n in r["notes"])  # 2 units, 27.80


def test_cash_reserve_is_kept():
    r = rebalance(T, DRIFTED, P, flow=5_000, cash_reserve=500)
    assert r["cash_after"] >= 500


def test_liquidity_flag():
    r = rebalance(T, {}, P, flow=1_000_000, adv={"XIC.TO": 5_000_000, "ZAG.TO": 100_000_000})
    rows = _rows(r)
    assert rows["XIC.TO"]["liquidity_flag"] and not rows["ZAG.TO"]["liquidity_flag"]


@pytest.mark.parametrize(
    "kw",
    [
        dict(targets={"A": 0.6, "B": 0.5}),
        dict(prices={"XIC.TO": 40.0}),
        dict(units={"XIC.TO": -1}),
        dict(flow=float("nan")),
        dict(destination=1.5),
    ],
)
def test_bad_inputs_are_input_errors(kw):
    args = dict(targets=T, units=DRIFTED, prices=P) | kw
    with pytest.raises(RoboKitInputError):
        rebalance(**args)


def test_fractional_units_reach_the_band_exactly():
    r = rebalance(T, DRIFTED, P, whole_units=False, min_trade=0)
    for x in r["rows"]:
        if x["ticker"] in T:
            assert abs(x["weight_after"] - T[x["ticker"]]) <= x["band"] + 1e-6


def test_random_accounts_keep_the_invariants():
    rng = np.random.default_rng(11)
    for _ in range(300):
        k = int(rng.integers(2, 8))
        names = [f"F{i}" for i in range(k)]
        w = rng.dirichlet(np.ones(k))
        targets = {t: float(v) for t, v in zip(names, w)}
        targets[names[-1]] = 1.0 - sum(v for t, v in targets.items() if t != names[-1])
        prices = {t: float(rng.uniform(5, 300)) for t in names}
        units = {t: float(rng.integers(0, 400)) for t in names if rng.random() < 0.8}
        held = sum(units[t] * prices[t] for t in units)
        flow = float(rng.choice([0.0, rng.uniform(100, 20_000), -rng.uniform(0, 0.9) * held]))
        try:
            r = rebalance(targets, units, prices, cash=float(rng.uniform(0, 500)), flow=flow, min_trade=float(rng.choice([0, 25, 100])))
        except RoboKitInputError:
            assert held + flow <= 0 or held == 0
            continue
        assert r["cash_after"] >= -1e-9
        for x in r["rows"]:
            assert x["units_after"] >= -1e-12
            if x["action"] == "sell":
                assert x["units"] <= x["units_before"] + 1e-12
