"""Round-3 regressions (docs/VERIFICATION.md, rounds 3-4): young funds keep the long history, withdrawal plans are described with their
flows, withdrawal results carry the median run-out, and an untouched default level is called the reference level."""

import pandas as pd

from robokit.engine import Request, build_portfolio
from robokit.history import backfill_regressors


def test_a_late_core_fund_is_left_out_of_the_back_fill():
    idx = pd.period_range("2000-01", "2026-08", freq="M").to_timestamp("M")
    core = pd.DataFrame({"A": 0.01, "B": 0.01, "C": 0.01}, index=idx)
    core.loc[:"2013-06-30", "C"] = None  # starts 9 years after the others (like BNDX)
    core.loc[:"2001-08-31", "B"] = None  # starts 20 months after A: kept
    assert backfill_regressors(core) == ["A", "B"]


def test_bito_does_not_cut_the_projection_history_short_of_2008():
    base = dict(market="US", risk_level=5, amount=5000, resample=False)
    without = build_portfolio(Request(**base))
    with_bito = build_portfolio(Request(**base, satellites=["BITO"], minimums={"BITO": 0.05}))
    assert with_bito["projection"]["history"]["start"] <= "2005-12-31"
    gap = abs(with_bito["projection"]["one_year"]["p5"] - without["projection"]["one_year"]["p5"])
    assert gap < 0.03, gap  # was about 0.07 (-13.5% vs -20.4%) when BITO cut the window to 2013


def test_withdrawal_plan_sentence_uses_the_flow_and_median_run_out_is_reported():
    p = build_portfolio(Request(market="CA", risk_level=1, amount=300_000, monthly_contribution=-1500, years=25, resample=False))
    en = " ".join(p["explanation"]["en"])
    assert "a month taken out" in en
    v = p["projection"]["one_year_value"]
    assert f"${round(v['p10']):,.0f}" in en
    w = p["projection"]["withdrawal"]
    assert "p50_months" in w and w["p10_months"] <= w["p50_months"] <= w["months"]
    fee_lines = [c["en"] for c in p["checks"] if c["id"].startswith("fee_drag")]
    assert fee_lines and all("real cost is lower" in t for t in fee_lines)


def test_own_weights_off_an_untouched_default_say_reference_level():
    w = {"XUU.TO": 0.4, "XEF.TO": 0.2, "XIC.TO": 0.2, "ZAG.TO": 0.2}
    chosen = build_portfolio(Request(market="CA", risk_level=1, fixed_weights=w, resample=False))
    ref = build_portfolio(Request(market="CA", risk_level=1, fixed_weights=w, level_chosen=False, resample=False))
    own = lambda p: next(c["en"] for c in p["checks"] if c["id"] == "own_weights")
    assert "the level you chose" in own(chosen)
    assert "the reference level" in own(ref)
