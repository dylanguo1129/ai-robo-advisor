"""Lambda is calibrated on the mix the person gets (v3 Track D1): resampled, minimum position applied, the same bootstrap
draws at every step. web/test_robokit.mjs checks that the browser takes the same steps."""

from __future__ import annotations

import pytest

from robokit.engine import CAL_MAX, CAL_TOL, LAM_LO, Request, build_portfolio


@pytest.mark.parametrize("market,level", [("CA", 1), ("CA", 3), ("US", 2), ("US", 4)])
def test_the_final_mix_hits_its_target(market, level):
    p = build_portfolio(Request(market=market, risk_level=level))
    c = p["risk"]["calibration"]
    assert c["within_tolerance"] and abs(c["achieved_vol"] - c["target_vol"]) <= CAL_TOL
    assert abs(p["stats"]["volatility"] - p["risk"]["target_vol"]) <= 1e-4 + 5e-5 + 1e-12  # both shown to 4 decimals
    assert 1 <= c["evaluations"] <= CAL_MAX


@pytest.mark.parametrize("kw", [dict(risk_level=2, min_weight=0.05), dict(risk_level=3.5, satellites=["XIT.TO", "ZEB.TO"])])
def test_the_minimum_position_no_longer_moves_the_risk(kw):
    p = build_portfolio(Request(market="CA", resample=False, **kw))
    assert p["risk"]["calibration"]["within_tolerance"], p["risk"]["calibration"]


def test_an_unreachable_target_says_so_with_the_final_volatility():
    p = build_portfolio(Request(market="CA", target_vol=0.30, resample=False))
    c = p["risk"]["calibration"]
    assert p["risk"]["lambda"] == pytest.approx(LAM_LO) and not c["within_tolerance"]
    note = [n["en"] for n in p["notes"] if "cannot reach" in n["en"]]
    assert note and f"{c['achieved_vol']:.1%}" in note[0]


def test_level_five_is_capped_by_the_fund_limits_not_by_the_calibration():
    p = build_portfolio(Request(market="CA", risk_level=5))
    c = p["risk"]["calibration"]
    assert p["risk"]["lambda"] == pytest.approx(LAM_LO)  # the riskiest mix the limits allow
    assert 0 < c["target_vol"] - c["achieved_vol"] < 0.005  # a small miss: no note, the paper reports it
