"""Opt-in suitability checks (v3 Track C3). Off by default, so the level policy is unchanged; when on, a level above
the suggestion (the lower of capacity and tolerance, 31-103CP s.13.2) needs the person's confirmation."""

from __future__ import annotations

import pytest

from robokit.engine import Request, build_portfolio, validate_request
from robokit.errors import RoboKitInputError

A = {
    "A2": "yes",
    "A3": "no",
    "B1": "10to19",
    "B2": "10plus",
    "B4": "10to25",
    "B5": "mostly",
    "C1": "4",
    "C2": "wait",
    "C3": "3",
    "C4": "both",
}


def _build(**kw):
    return build_portfolio(Request(market="CA", resample=False, **kw))


def test_off_by_default_nothing_changes():
    p = _build(risk_level=5, answers=A)
    assert p["risk"]["level"] == 5 and p["method"]["suitability"] is None


def test_a_level_above_the_suggestion_is_built_at_the_suggestion():
    p = _build(risk_level=5, answers=A, enforce_suitability=True)
    s = p["method"]["suitability"]
    assert s["suggested_level"] == 3 and s["applied_level"] == 3 and p["risk"]["level"] == 3
    assert any("built at level 3, not the level 5 you chose" in n["en"] for n in p["notes"])
    assert p["risk"]["target_vol"] == _build(risk_level=3)["risk"]["target_vol"]


def test_a_confirmed_choice_is_built_and_recorded():
    p = _build(risk_level=5, answers=A, enforce_suitability=True, acknowledged_above_suggestion=True)
    assert p["risk"]["level"] == 5 and p["method"]["suitability"]["acknowledged"]
    assert any("confirmation is recorded" in n["en"] for n in p["notes"])


def test_a_level_at_or_below_the_suggestion_is_left_alone():
    p = _build(risk_level=2, answers=A, enforce_suitability=True)
    assert p["risk"]["level"] == 2 and p["method"]["suitability"]["applied_level"] == 2


def test_a_target_volatility_above_the_suggestion_is_capped_too():
    p = _build(target_vol=0.12, answers=A, enforce_suitability=True)
    assert p["risk"]["level"] == 3


def test_own_weights_above_the_suggestion_are_refused_without_confirmation():
    with pytest.raises(RoboKitInputError):
        _build(fixed_weights={"VFV.TO": 1.0}, answers=A, enforce_suitability=True)
    p = _build(fixed_weights={"VFV.TO": 1.0}, answers=A, enforce_suitability=True, acknowledged_above_suggestion=True)
    assert p["method"]["suitability"]["acknowledged"]


@pytest.mark.parametrize("answers", [None, {}, {"A2": "yes"}])
def test_missing_or_incomplete_answers_are_refused(answers):
    with pytest.raises(RoboKitInputError):
        _build(risk_level=3, answers=answers, enforce_suitability=True)


@pytest.mark.parametrize("field,value", [("enforce_suitability", "yes"), ("acknowledged_above_suggestion", 1), ("answers", ["A2"])])
def test_bad_types_are_input_errors(field, value):
    with pytest.raises(RoboKitInputError):
        validate_request(Request(**{field: value}))
