"""Regression tests for the findings of the adversarial review of the v3 safety change (both engines were affected;
web/test_safety.mjs carries the browser side). Each test reproduces one reported trigger."""

from __future__ import annotations

import pytest

from optimizer.errors import InfeasibleConstraints
from robokit import engine
from robokit.engine import Request, build_portfolio, validate_request
from robokit.errors import RoboKitInputError


def _ca(**kw):
    return build_portfolio(Request(market="CA", resample=False, **kw))


@pytest.fixture(scope="module")
def eq_vol():
    return _ca(risk_level=3)["risk"]["stock_market_vol"]


def _satellites(n=3):
    U = engine._load()[0]
    core = {r["ticker"] for r in _ca(risk_level=3)["shelf"]}
    c = U[(U.market == "CA") & U.eligible & (U.asset_class == "Equity") & ~U.yahoo.isin(core) & (U.history_months >= 120)]
    return list(c.sort_values("aum", ascending=False).yahoo.head(n))


def _assert_within_caps(p, req_max=0.5, tol=2e-4):
    """Every holding within its requested cap, or the value recorded when a relaxation was asked for."""
    caps = dict(p["method"]["sleeve_caps"])
    for r in p["method"]["relaxations"]:
        if r["limit"] == "cap":
            caps[r["ticker"]] = r["applied"]
    for h in p["holdings"]:
        cap = caps.get(h["ticker"], 1.0 if h["role"] == "cash" else req_max)
        assert h["weight"] <= cap + tol, (h["ticker"], h["weight"], cap, p["notes"])


VIEW = [{"type": "relative", "long": "XIC.TO", "short": "ZAG.TO", "difference": 0.03, "confidence": 0.8}]


@pytest.mark.parametrize(
    "kw",
    [
        dict(risk_level=4, max_weight=0.131),
        dict(risk_level=2, max_weight=0.1, min_weight=0.2),
        dict(risk_level=3, max_weight=0.2, min_weight=0.1),
    ],
)
def test_view_tilt_never_breaks_caps(kw):
    p = _ca(views=VIEW, **kw)
    _assert_within_caps(p, kw.get("max_weight", 0.5))
    t = p["views"]["tilt"]
    assert t["tracking_error_after"] <= 0.01 + 1e-4 and t["largest_move_after"] <= 0.05 + 1e-4


def test_view_with_every_position_small_does_not_crash():
    p = _ca(risk_level=2.5, max_weight=0.1, min_weight=0.2, views=VIEW)
    assert abs(sum(h["weight"] for h in p["holdings"]) - 1) < 1e-3
    assert any("minimum position size was not applied" in n["en"] for n in p["notes"])


def test_view_that_cannot_apply_says_so():
    p = _ca(risk_level=5, views=[{"type": "relative", "long": "VFV.TO", "short": "XIC.TO", "difference": 0.02, "confidence": 0.5}])
    _assert_within_caps(p)
    if p["views"]["tilt"]["scale"] == 0:
        assert any("could not be applied within the limits" in n["en"] for n in p["notes"])
        assert p["method"]["expected_returns_for_weights"] == "equilibrium"


@pytest.mark.parametrize(
    "kw",
    [
        dict(risk_level=4, max_weight=0.3, min_weight=0.2),
        dict(risk_level=5, max_weight=0.4, min_weight=0.25),
        dict(risk_level=5, max_weight=0.2, min_weight=0.1),
    ],
)
def test_minimum_position_never_renormalises_past_a_cap(kw):
    p = _ca(**kw)
    _assert_within_caps(p, kw["max_weight"])
    assert p["method"]["relaxations"] == []


def test_relaxing_touches_core_funds_before_own_picks():
    p = _ca(risk_level=3, max_weight=0.05, satellites=["ZSP.TO"], on_infeasible="relax")
    assert all(h["weight"] <= 0.10 + 2e-4 for h in p["holdings"] if h["role"] == "satellite")
    assert not any(r["limit"] == "group" for r in p["method"]["relaxations"])
    assert not any(r.get("ticker") == "ZSP.TO" for r in p["method"]["relaxations"])


def test_relax_mode_does_not_relax_just_to_drop_a_small_position():
    p = _ca(risk_level=4, max_weight=0.131, on_infeasible="relax")
    assert p["method"]["relaxations"] == []
    _assert_within_caps(p, 0.131)


def test_group_refusal_names_the_minimums_when_they_cause_it():
    sats = _satellites(3)  # each minimum fits its own 10% limit; together they exceed the 20% for own picks at level 3
    with pytest.raises(InfeasibleConstraints) as e:
        _ca(risk_level=3, satellites=sats, minimums={t: 0.09 for t in sats})
    assert "minimums you set on your own picks" in str(e.value)


def test_messages_do_not_contradict_their_numbers():
    with pytest.raises(InfeasibleConstraints) as e:
        _ca(risk_level=3, max_weight=0.094)
    assert "add up to 99.6%" in str(e.value)
    p = _ca(risk_level=3, max_weight=0.094, on_infeasible="relax")
    for n in p["notes"]:
        if "was raised from" in n["en"]:
            a, b = n["en"].split("was raised from ")[1].split(" to ")[:2]
            assert a != b.split(" ")[0], n["en"]


def test_half_level_label_follows_the_level_shown(eq_vol):
    p = _ca(target_vol=0.492 * eq_vol)
    assert p["risk"]["level"] == 2.5 and p["risk"]["label"] == "Balanced"


def test_no_equity_yardstick_uses_the_default_reference_funds(eq_vol):
    p = _ca(risk_level=2, sleeves=["ca_agg_bond", "ca_short_bond", "ca_global_bond", "ca_cash"])
    assert abs(p["risk"]["stock_market_vol"] - eq_vol) < 1e-4


@pytest.mark.parametrize("field,value", [("risk_level", True), ("risk_level", [4]), ("amount", "abc"), ("seed", 1.5)])
def test_validation_refuses_non_numbers(field, value):
    with pytest.raises(RoboKitInputError):
        validate_request(Request(**{field: value}))


def test_validation_reads_a_missing_monthly_flow_as_zero():
    assert validate_request(Request(monthly_contribution=None)).monthly_contribution == 0.0


@pytest.mark.parametrize(
    "view",
    [
        {"type": "relative", "long": "XIC.TO", "short": "ZAG.TO", "difference": float("nan")},
        {"type": "relative", "long": "XIC.TO", "short": "ZAG.TO"},
        {"type": "absolute", "ticker": "XIC.TO"},
        {"type": "absolute", "ticker": "XIC.TO", "return": "abc"},
        {"type": "sideways", "ticker": "XIC.TO", "return": 0.05},
        {"type": "absolute", "ticker": "XIC.TO", "return": 0.05, "confidence": 1.5},
        "XIC beats ZAG",
    ],
)
def test_bad_views_are_input_errors(view):
    with pytest.raises(RoboKitInputError):
        validate_request(Request(views=[view]))


def test_view_without_confidence_uses_fifty_percent():
    v = validate_request(Request(views=[{"type": "absolute", "ticker": "XIC.TO", "return": 0.08, "confidence": None}])).views[0]
    assert v["confidence"] == 0.5


def test_a_weight_at_a_cap_equal_to_the_minimum_is_not_small():
    p = build_portfolio(Request(market="US", risk_level=5, max_weight=0.3, min_weight=0.1, resample=False))
    assert not any("would have held less than" in n["en"] and ("VNQ" in n["en"] or "GLDM" in n["en"]) for n in p["notes"])
    _assert_within_caps(p, 0.3)


def test_a_minimum_above_a_funds_limit_is_a_conflict():
    with pytest.raises(InfeasibleConstraints) as e:
        _ca(risk_level=5, satellites=["XIT.TO"], minimums={"XIT.TO": 0.15}, satellite_max_each=0.10)
    assert e.value.details["kind"] == "minimum_above_cap" and "Lower the minimum" in str(e.value)
    p = _ca(risk_level=5, satellites=["XIT.TO"], minimums={"XIT.TO": 0.15}, satellite_max_each=0.10, on_infeasible="relax")
    rec = [r for r in p["method"]["relaxations"] if r.get("reason") == "minimum"]
    assert rec and rec[0]["ticker"] == "XIT.TO" and rec[0]["applied"] == 0.15
    assert {h["ticker"]: h["weight"] for h in p["holdings"]}["XIT.TO"] >= 0.15 - 1e-4


def test_own_weights_of_zero_are_an_input_error():
    with pytest.raises(RoboKitInputError):
        validate_request(Request(fixed_weights={"XIC.TO": 0}))
