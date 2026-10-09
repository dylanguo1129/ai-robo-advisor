"""The evaluation's engine hooks (as-of builds, research switches, point-in-time shelf): they must not leak the future
and must leave the product untouched."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import robokit.engine as E
from robokit.engine import Request, as_of, build_portfolio
from robokit.errors import RoboKitInputError
from robokit.research import own_history_months, pit_shelf

CUT = pd.Timestamp("2016-12-31")


def test_lean_build_has_the_same_weights_as_the_full_build():
    p = build_portfolio(Request(market="CA", risk_level=3, resample=False))
    q = build_portfolio(Request(market="CA", risk_level=3, resample=False), lean=True)
    assert {h["ticker"]: h["weight"] for h in p["holdings"]} == {t: round(v, 4) for t, v in q["weights"].items()}


def test_a_strict_as_of_build_does_not_see_the_future():
    """Replace every return, interest rate and exchange rate after the as-of month with noise: the mix must not move."""
    U, R, fx, ctx = E._load_all()
    rng = np.random.default_rng(0)
    R2, fx2, ctx2 = R.copy(), fx.copy(), ctx.copy()
    R2.loc[R2.index > CUT] = rng.normal(0, 0.2, size=R2.loc[R2.index > CUT].shape)
    fx2.loc[fx2.index > CUT] = fx2.loc[fx2.index > CUT] * 3
    ctx2.loc[ctx2.index > CUT] = 99.0
    swaps, kept, _ = pit_shelf("CA", CUT)

    def run():
        with as_of(CUT, "strict"):
            return build_portfolio(
                Request(market="CA", risk_level=3, n_boot=50, swaps=swaps, sleeves=kept), lean=True, research={"stand_ins": False}
            )

    clean = run()
    orig = E._load_all
    E._load_all = lambda: (U, R2, fx2, ctx2)
    try:
        dirty = run()
    finally:
        E._load_all = orig
    assert clean["weights"] == dirty["weights"] and clean["window"]["end"] == "2016-12-31"


def test_point_in_time_shelf_only_uses_funds_with_enough_own_history():
    months = own_history_months(CUT)
    _, kept, chosen = pit_shelf("CA", CUT)
    assert kept and all(months[t] >= 36 for t in chosen.values())


def test_fixed_as_of_ends_the_estimation_window_at_the_date():
    with as_of(CUT, "fixed"):
        q = build_portfolio(Request(market="CA", risk_level=3, resample=False), lean=True)
    assert q["window"]["end"] == "2016-12-31" and q["window"]["months"] == 145


def test_unknown_research_switches_are_refused():
    with pytest.raises(RoboKitInputError):
        build_portfolio(Request(market="CA", risk_level=3, resample=False), lean=True, research={"tune_to_backtest": True})


@pytest.mark.parametrize(
    "switch", [{"sleeve_caps": False}, {"calibrate": "single"}, {"cov_method": "sample"}, {"mu_method": "sample"}, {"max_window": 120}]
)
def test_each_research_switch_changes_only_its_component(switch):
    q = build_portfolio(Request(market="CA", risk_level=3, resample=False), lean=True, research=switch)
    assert abs(sum(q["weights"].values()) - 1) < 1e-9
    if "cov_method" in switch:
        assert q["covariance"] == "sample"
    if "max_window" in switch:
        assert q["window"]["months"] == 120
    if "calibrate" in switch:
        assert q["calibration"]["outcome"] == "single solve"


@pytest.mark.parametrize("date,months", [("2024-10-31", 35), ("2024-11-30", 36)])
def test_the_36_month_gate_refuses_35_shared_months_and_builds_on_36(date, months):
    """Strict as-of, own histories only: CASH.TO's first return is for December 2021, so the CA reference funds share
    35 months at the end of October 2024 and 36 a month later."""
    req = Request(market="CA", risk_level=3, resample=False)
    with as_of(pd.Timestamp(date), "strict"):
        if months < 36:
            with pytest.raises(RoboKitInputError) as e:
                build_portfolio(req, lean=True, research={"stand_ins": False})
            assert e.value.details == {"kind": "short_history", "months": months}
        else:
            q = build_portfolio(req, lean=True, research={"stand_ins": False})
            assert q["window"]["months"] == 36 and q["window"]["start"] == "2021-12-31"
