"""The evaluation statistics (robokit/evalstats.py) against known answers and their own definitions."""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats

from robokit import evalstats as es


def test_holm_matches_a_worked_example():
    # sorted: 0.005 x 4 = 0.02; 0.01 x 3 = 0.03; 0.03 x 2 = 0.06; 0.04 x 1 = 0.04 -> 0.06 (monotone)
    assert es.holm([0.01, 0.04, 0.03, 0.005]) == pytest.approx([0.03, 0.06, 0.06, 0.02])


def test_newey_west_with_no_lags_is_the_plain_t_statistic():
    x = np.random.default_rng(1).normal(0.1, 1, 400)
    r = es.newey_west_t(x, lags=0)
    plain = x.mean() / (x.std(ddof=0) / math.sqrt(len(x)))
    assert r["t"] == pytest.approx(plain)


def test_hac_on_independent_data_is_close_to_the_sample_covariance():
    y = np.random.default_rng(2).normal(size=(20000, 2)) @ np.array([[1.0, 0.3], [0.0, 0.8]])
    assert np.allclose(es.hac_qs_prewhitened(y), np.cov(y.T, ddof=0), rtol=0.06, atol=0.02)


def test_ledoit_wolf_test_has_about_the_right_size_and_some_power():
    rng = np.random.default_rng(3)
    rej = 0
    reps = 150
    for k in range(reps):  # equal Sharpe ratios, correlated, mildly autocorrelated
        z = rng.normal(size=(121, 2))
        z = 0.3 * z[:-1] + z[1:]
        a = 0.005 + 0.04 * z[:, 0]
        b = 0.005 + 0.04 * (0.7 * z[:, 0] + math.sqrt(1 - 0.49) * z[:, 1])
        rej += es.sharpe_diff_test(a, b, block=6, n_boot=199, seed=k)["p"] < 0.05
    assert 0.0 <= rej / reps <= 0.12
    z = rng.normal(size=(240, 2))
    strong = es.sharpe_diff_test(0.03 + 0.04 * z[:, 0], 0.0 + 0.04 * z[:, 1], n_boot=499)
    assert strong["p"] < 0.05 and strong["diff"] > 0


def test_deflated_sharpe_with_one_trial_is_the_probabilistic_sharpe_ratio():
    r = np.random.default_rng(4).normal(0.01, 0.04, 240)
    d = es.deflated_sharpe(r, [0.25], n_trials=1)
    sr = r.mean() / r.std(ddof=1)
    g3, g4 = stats.skew(r), stats.kurtosis(r, fisher=False)
    want = stats.norm.cdf(sr * math.sqrt(239) / math.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr**2))
    assert d["sr0"] == 0.0 and d["dsr"] == pytest.approx(want)


def test_more_trials_raise_the_bar():
    r = np.random.default_rng(5).normal(0.01, 0.04, 240)
    few = es.deflated_sharpe(r, [0.1, 0.2, 0.15], n_trials=3)
    many = es.deflated_sharpe(r, [0.1, 0.2, 0.15], n_trials=300)
    assert many["sr0"] > few["sr0"] and many["dsr"] < few["dsr"]


def test_min_track_record_formula():
    r = np.random.default_rng(6).normal(0.01, 0.04, 240)
    sr, g3, g4 = r.mean() / r.std(ddof=1), stats.skew(r), stats.kurtosis(r, fisher=False)
    want = 1 + (1 - g3 * sr + (g4 - 1) / 4 * sr**2) * (stats.norm.ppf(0.95) / sr) ** 2
    assert es.min_track_record(r) == pytest.approx(want)
    assert es.min_track_record(-np.abs(r)) == float("inf")


def test_vol_ratio_interval_covers_the_truth_about_as_often_as_it_says():
    """On i.i.d. standardised returns (ratio 1) the 90% interval covers 1 in about 87% of samples of 120 months: the
    percentile interval for a standard deviation runs slightly short, and the paper says so."""
    hits = sum(
        es.vol_ratio_interval(np.random.default_rng(1000 + s).normal(0, 1, 120), n_boot=299, seed=s)["contains_1"] for s in range(200)
    )
    assert 0.80 <= hits / 200 <= 0.95


def test_erc_weights_have_equal_risk_contributions():
    a = np.random.default_rng(8).normal(size=(6, 6))
    S = a @ a.T / 6 + 0.05 * np.eye(6)
    w = es.erc_weights(S)
    rc = w * (S @ w)
    assert abs(w.sum() - 1) < 1e-12 and (w > 0).all() and np.ptp(rc) / rc.mean() < 1e-6


def test_min_variance_on_a_diagonal_covariance_is_inverse_variance_with_the_cap():
    S = np.diag([0.01, 0.04, 0.09, 0.16])
    w = es.min_variance(S, cap=0.5)
    inv = 1 / np.diag(S)
    assert w[0] == pytest.approx(0.5, abs=1e-8)  # the cap binds for the least volatile fund
    rest = inv[1:] / inv[1:].sum() * 0.5
    assert np.allclose(w[1:], rest, atol=1e-7)


def test_mixing_with_cash_hits_the_target_or_says_it_cannot():
    S = np.array([[0.04, 0.0], [0.0, 1e-6]])
    w, ok = es.mix_with_cash(np.array([1.0, 0.0]), S, 1, 0.1)
    assert ok and math.sqrt(w @ S @ w) == pytest.approx(0.1, rel=1e-9)
    _, ok = es.mix_with_cash(np.array([1.0, 0.0]), S, 1, 0.5)
    assert not ok


def test_drawdown_and_cvar():
    r = np.array([0.1, -0.5, 0.2, -0.1])
    assert es.max_drawdown(r) == pytest.approx(-0.5)  # wealth 1.1, 0.55, 0.66, 0.594: the trough is half the peak
    assert es.cvar(np.arange(1, 101) / 100, 0.95) == pytest.approx(np.mean(np.arange(1, 6) / 100))


def test_sharpe_interval_and_non_inferiority():
    z = np.random.default_rng(9).normal(size=(240, 2))
    a, b = 0.006 + 0.04 * z[:, 0], 0.006 + 0.04 * (0.9 * z[:, 0] + math.sqrt(1 - 0.81) * z[:, 1])
    r = es.sharpe_diff_test(a, b, n_boot=999, margin=0.10 / math.sqrt(12))
    assert r["ci95"][0] < r["diff"] < r["ci95"][1]
    loose = es.sharpe_diff_test(a, b, n_boot=999, margin=1.0)  # a margin far wider than the uncertainty
    assert loose["p_noninferior"] < 0.01 and r["p_noninferior"] >= loose["p_noninferior"]


def test_politis_white_block_length_on_an_ar1_matches_the_closed_form():
    """For an AR(1) with coefficient phi the stationary-bootstrap optimum is (2 phi / (1 - phi^2))^(2/3) n^(1/3)."""
    phi, n = 0.5, 20000
    e = np.random.default_rng(10).normal(size=n + 200)
    x = np.empty_like(e)
    x[0] = e[0]
    for i in range(1, len(e)):
        x[i] = phi * x[i - 1] + e[i]
    want = (2 * phi / (1 - phi**2)) ** (2 / 3) * n ** (1 / 3)
    assert es.politis_white_block(x[200:]) == pytest.approx(want, rel=0.15)
    assert es.politis_white_block(np.random.default_rng(11).normal(size=500)) < 3  # no dependence: short blocks


def test_erc_fails_closed_when_the_risk_contributions_are_not_equal(monkeypatch):
    """A solve that stops early (or any answer whose risk contributions are not equal) raises instead of returning."""
    from types import SimpleNamespace

    from optimizer.errors import SolverNotConverged

    S = np.diag([0.04, 0.09, 0.16])
    monkeypatch.setattr(
        es.optimize, "minimize", lambda *a, **k: SimpleNamespace(x=np.array([1.0, 1.0, 1.0]), success=False, message="stopped")
    )
    with pytest.raises(SolverNotConverged, match="equal risk contribution"):
        es.erc_weights(S)
