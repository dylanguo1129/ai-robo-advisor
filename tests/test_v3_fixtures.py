"""Small decisions checked against hand-computed answers (Stage 1 review of the v3 evaluation plan, section C):
gaps in prices, the prior after aliases and missing slots, when the risk note appears, the timing of monthly
contributions in projections, and the planning-return rules."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from robokit.cma import FPC_2026, assumption
from robokit.data.prices import monthly_returns
from robokit.engine import Request, _reach_note, build_portfolio
from robokit.projection import project


def test_a_gap_in_prices_stays_a_gap():
    idx = pd.date_range("2020-01-31", periods=5, freq="ME")
    close = pd.DataFrame({"A": [100.0, 110.0, np.nan, 121.0, 133.1]}, index=idx)
    r = monthly_returns(close)["A"]
    assert np.isnan(r.iloc[0]) and r.iloc[1] == pytest.approx(0.10)
    assert np.isnan(r.iloc[2]) and np.isnan(r.iloc[3])  # no return across the gap, nothing filled in
    assert r.iloc[4] == pytest.approx(0.10)


@pytest.mark.parametrize(
    "kw",
    [dict(hedge_us_equity=True), dict(sleeves=["ca_equity", "ca_us_equity", "ca_agg_bond", "ca_cash"])],
)
def test_the_prior_follows_the_policy_shares_and_sums_to_one(kw):
    p = build_portfolio(Request(market="CA", risk_level=3, resample=False, **kw))
    prior = p["method"]["prior"]
    assert sum(prior.values()) == pytest.approx(1.0, abs=2e-4)
    if "sleeves" in kw:  # 0.18 : 0.27 : 0.22 for Canadian stocks, US stocks, bonds (cash has no policy share)
        tick = {r["sleeve"]: r["ticker"] for r in p["shelf"]}
        a, b, c = (prior[tick[k]] for k in ("ca_equity", "ca_us_equity", "ca_agg_bond"))
        assert a / c == pytest.approx(0.18 / 0.22, rel=2e-3) and b / c == pytest.approx(0.27 / 0.22, rel=2e-3)


@pytest.mark.parametrize(
    "target,vol,outcome,says",
    [
        (0.10, 0.09, "out of reach", "cannot reach"),
        (0.03, 0.04, "out of reach", "steadiest mix"),
        (0.08, 0.0745, "jump", "moves in steps"),
        (0.08, 0.0755, "jump", None),  # half a point or less: no note
        (0.08, 0.0799, "within tolerance", None),
        (0.10, 0.0965, "out of reach", None),
    ],
)
def test_the_risk_note_appears_exactly_when_the_mix_is_over_half_a_point_away(target, vol, outcome, says):
    note = _reach_note(target, vol, outcome)
    assert (note is None) if says is None else (says in note["en"])


def test_contributions_arrive_at_the_end_of_each_month():
    g = 0.06
    X = np.zeros((120, 1))  # no variation: every path earns the planning return exactly
    out = project(X, np.array([1.0]), np.array([g]), amount=10_000, monthly_contribution=100, years=2, n_paths=50)
    m = (1 + g) ** (1 / 12) - 1
    want = 10_000 * (1 + m) ** 24 + 100 * sum((1 + m) ** k for k in range(24))
    assert out["final"]["p50"] == pytest.approx(want, abs=0.01)


def test_planning_return_rules():
    assert assumption("Fixed income", "US", "US", {"note5": 0.041})[0] == 0.041
    assert assumption("Cash", "US", "US", {"bill": 0.037})[0] == 0.037
    assert assumption("Fixed income", "Canada", "CA")[0] == FPC_2026["fixed_income"]
    eq = assumption("Equity", "Canada", "CA")[0]
    assert assumption("Multi-asset", "Canada", "CA")[0] == pytest.approx(0.6 * eq + 0.4 * FPC_2026["fixed_income"])


def test_the_month_in_progress_is_dropped(tmp_path, monkeypatch):
    """A month that has not ended has no month-end close yet: assemble drops it and labels the rest month-end."""
    from robokit.data import prices as P

    idx = pd.to_datetime(["2026-08-01", "2026-09-01", "2026-10-01"])
    frame = pd.DataFrame({"AAA": [10.0, 11.0, 12.0]}, index=idx)
    pd.to_pickle({"close": frame, "volume": frame, "tickers": ["AAA"]}, tmp_path / "universe_0.pkl")
    monkeypatch.setattr(P, "CHUNK_DIR", tmp_path)
    close, _ = P.assemble("universe", today=pd.Timestamp("2026-10-15"))
    assert list(close.index) == [pd.Timestamp("2026-08-31"), pd.Timestamp("2026-09-30")]


@pytest.mark.parametrize("months,rho,used", [(24, 0.8005, True), (23, 0.95, False), (36, 0.7995, False), (36, 0.8005, True)])
def test_the_stand_in_gate_needs_24_months_and_a_correlation_of_0_8(months, rho, used):
    """D3: a young fund is extended with a stand-in only if they overlap 24 months or more with correlation 0.8 or
    more (robokit/history.py splice)."""
    import math

    from robokit.history import splice

    idx = pd.date_range("2000-01-31", periods=120, freq="ME")
    rng = np.random.default_rng(3)
    zs, zn = rng.normal(size=months), rng.normal(size=months)
    zs = (zs - zs.mean()) / zs.std()
    zn = zn - zn.mean()
    zn = zn - (zn @ zs) / (zs @ zs) * zs
    zn = zn / zn.std()  # orthogonal to zs: the overlap's correlation is exactly rho
    own_idx = idx[-months:]
    own = pd.Series(0.01 * zs, index=own_idx)
    proxy = pd.Series(rng.normal(0, 0.01, 120), index=idx)
    proxy.loc[own_idx] = 0.01 * (rho * zs + math.sqrt(1 - rho**2) * zn)
    s, _ = splice(own, [("P", False)], pd.DataFrame({"P": proxy}), pd.Series(0.0, index=idx), pd.DataFrame(index=idx))
    assert (len(s) == 120) is used
