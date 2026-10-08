"""The evaluation's machinery (robokit/evaluation.py, robokit/audit.py) on cases with known answers."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from robokit import audit as AU
from robokit import evaluation as EV


def _builds(weights_by_date, target=0.08):
    return [{"task": ("CA", d, 3, "x", "fixed"), "weights": w, "target": target} for d, w in weights_by_date.items()]


def test_hold_path_charges_the_drift_and_the_annual_change():
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    R = pd.DataFrame({"A": 0.02, "B": 0.0}, index=idx)
    b = _builds({"2019-12-31": {"A": 0.5, "B": 0.5}, "2020-12-31": {"A": 0.3, "B": 0.7}})
    p = EV.hold_path(b, R, cost=0.001)
    assert len(p) == 24 and np.allclose(p.loc["2020", "gross"], 0.01)
    drift = 0.5 * (abs(0.5 * 1.02 / 1.01 - 0.5) + abs(0.5 / 1.01 - 0.5))
    assert p["turn"].iloc[1] == pytest.approx(drift)
    drift_new = 0.5 * (abs(0.3 * 1.02 / 1.006 - 0.3) + abs(0.7 / 1.006 - 0.7))  # January drifts from the new 30/70
    assert p["turn"].iloc[12] == pytest.approx(drift_new + 0.2, rel=1e-9)  # plus the move from 50/50 to 30/70
    assert (p["gross"] - p["net"]).to_numpy() == pytest.approx(0.001 * p["turn"].to_numpy())


def test_risk_delivery_reads_a_path_that_hits_its_target_as_delivered_or_inconclusive():
    idx = pd.date_range("2001-01-31", periods=400, freq="ME")
    rng = np.random.default_rng(0)
    paths = {L: pd.DataFrame({"net": rng.normal(0, 0.06 / math.sqrt(12), 400), "target": 0.06}, index=idx) for L in (2, 3, 4)}
    out = EV.risk_delivery(paths, (2, 3, 4), n_boot=499)
    assert out["reading"] in ("delivered", "inconclusive") and all(0.85 < out[L]["ratio"] < 1.15 for L in (2, 3, 4))
    paths[3]["net"] *= 1.6
    assert EV.risk_delivery(paths, (2, 3, 4), n_boot=499)["reading"] == "missed at levels 3"


def test_ideal_account_with_flat_prices_and_no_cost_earns_nothing_whatever_the_flows():
    idx = pd.date_range("2020-01-31", periods=6, freq="ME")
    prices = pd.DataFrame({"A": 10.0, "B": 20.0}, index=idx)
    t = {"2019-12-31": {"A": 0.6, "B": 0.4}}
    df = AU.account_path(t, prices, 10_000.0, 500.0, "ideal", cost_bps=0.0)["path"]
    assert df["return"].abs().max() < 1e-12 and df["value"].iloc[-1] == pytest.approx(10_000 + 500 * 6)  # a contribution each month


def test_production_rebalancer_account_never_goes_short_or_overdrawn():
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    rng = np.random.default_rng(1)
    prices = pd.DataFrame(100 * np.cumprod(1 + rng.normal(0.005, 0.04, size=(24, 3)), axis=0), index=idx, columns=["A", "B", "C"])
    t = {"2019-12-31": {"A": 0.5, "B": 0.3, "C": 0.2}, "2020-12-31": {"A": 0.3, "B": 0.4, "C": 0.3}}
    for rule in ("monthly", "bands", "annual"):
        df = AU.account_path(t, prices, 10_000.0, 250.0, rule)["path"]
        assert (df["cash_share"] >= -1e-12).all() and (df["value"] > 0).all()


@pytest.mark.parametrize(
    "c,want",
    [
        (
            {"p_holm": 0.01, "sharpe_diff_annual": -0.3, "p_noninferior_holm": 0.9, "min_track_record_months": float("inf"), "months": 200},
            "benchmark better",
        ),
        (
            {"p_holm": 0.01, "sharpe_diff_annual": 0.3, "p_noninferior_holm": 0.01, "min_track_record_months": 50.0, "months": 200},
            "robokit better",
        ),
        (
            {"p_holm": 0.4, "sharpe_diff_annual": 0.05, "p_noninferior_holm": 0.02, "min_track_record_months": 900.0, "months": 200},
            "robokit not worse by more than 0.10",
        ),
        (
            {"p_holm": 0.4, "sharpe_diff_annual": 0.05, "p_noninferior_holm": 0.2, "min_track_record_months": 900.0, "months": 200},
            "too short to tell",
        ),
        (
            {"p_holm": 0.4, "sharpe_diff_annual": -0.05, "p_noninferior_holm": 0.2, "min_track_record_months": float("inf"), "months": 200},
            "inconclusive",
        ),
        (
            {"p_holm": 0.4, "sharpe_diff_annual": -0.05, "p_noninferior_holm": 0.2, "min_track_record_months": None, "months": 200},
            "inconclusive",
        ),
        (
            {"p_holm": 0.4, "sharpe_diff_annual": 0.05, "p_noninferior_holm": 0.2, "min_track_record_months": 150.0, "months": 200},
            "inconclusive",
        ),
    ],
)
def test_the_confirmatory_reading_follows_the_registered_rule(c, want):
    assert EV.reading(c) == want


def test_account_returns_are_after_trading_costs():
    idx = pd.date_range("2020-01-31", periods=6, freq="ME")
    prices = pd.DataFrame({"A": 10.0, "B": 20.0}, index=idx)
    t = {"2019-12-31": {"A": 0.6, "B": 0.4}}
    df = AU.account_path(t, prices, 10_000.0, 0.0, "ideal", cost_bps=10.0)["path"]
    assert df["return"].iloc[0] == pytest.approx(-10_000 * 1e-3 / 10_000, rel=1e-6)  # buying everything costs 10 bps
    assert df["return"].iloc[1:].abs().max() < 1e-12  # flat prices, back at target: nothing more to pay


def test_band_coverage_counts_a_fund_the_minimum_position_dropped():
    from robokit.simulation import band_coverage

    band = {"A": (0.30, 0.40), "B": (0.55, 0.65)}  # C (true weight 1%) was dropped by the 2% rule: no band shown
    assert band_coverage(band, ["A", "B", "C"], np.array([0.35, 0.60, 0.01])) == pytest.approx(2 / 3)
    assert band_coverage(band, ["A", "B", "C"], np.array([0.35, 0.60, 0.0])) == pytest.approx(1.0)
