"""One model, two runtimes (v3 Track B): the shared random generator, the exact projection and QIS.

The browser side of each check is in web/test_robokit.mjs (resampled builds and projections against Python reference
cases) and web/test_engine.mjs; the values hard-coded here were printed by web/engine.js."""

from __future__ import annotations

import numpy as np
import pytest

from optimizer.errors import InfeasibleConstraints
from optimizer.estimators import qis
from optimizer.rng import Mulberry32, stationary_rows, stationary_rows_many
from optimizer.solver import project_weighted_capped_simplex
from robokit.projection import project


# ------------------------------------------------------------------ the generator is bit-exact with web/engine.js
def test_mulberry32_matches_the_browser():
    r = Mulberry32(1)
    assert [r() for _ in range(5)] == [
        0.6270739405881613,
        0.002735721180215478,
        0.5274470399599522,
        0.9810509674716741,
        0.9683778982143849,
    ]
    r = Mulberry32(4294967295)
    assert [r() for _ in range(3)] == [0.8964226141106337, 0.189478256739676, 0.7156526781618595]


def test_stationary_rows_match_the_browser():
    rows = stationary_rows(Mulberry32(8), 40, 40, 6.0)
    assert rows.tolist()[:20] == [6, 7, 8, 9, 10, 11, 12, 13, 14, 20, 22, 23, 38, 39, 5, 22, 23, 24, 25, 18]
    assert rows.tolist()[20:] == [19, 20, 21, 22, 34, 35, 36, 37, 38, 39, 0, 1, 2, 3, 12, 13, 14, 15, 17, 18]


def test_many_paths_equal_one_path_at_a_time():
    seeds = (7 * 1000003 + np.arange(64) * 7919 + 1) & 0xFFFFFFFF
    many = stationary_rows_many(seeds, 158, 120, 6.0)
    for k, s in enumerate(seeds):
        assert np.array_equal(many[k], stationary_rows(Mulberry32(int(s)), 158, 120, 6.0))


# ------------------------------------------------------------------ the exact projection
def _bisection(x, a, cap, total):
    lo, hi = float(np.min((x - cap) / a)) - 1, float(np.max(x / a)) + 1
    for _ in range(300):
        tau = 0.5 * (lo + hi)
        if a @ np.clip(x - tau * a, 0, cap) > total:
            lo = tau
        else:
            hi = tau
    return np.clip(x - 0.5 * (lo + hi) * a, 0, cap)


def test_exact_projection_agrees_with_bisection():
    rng = np.random.default_rng(3)
    for _ in range(2000):
        n = int(rng.integers(1, 12))
        x = rng.normal(0, 0.5, n)
        a = rng.uniform(0.2, 3, n)
        cap = rng.uniform(0.05, 1, n)
        total = float(rng.uniform(0.01, 0.999) * (a @ cap))
        v = project_weighted_capped_simplex(x, a, cap, total)
        assert abs(a @ v - total) < 1e-12 and (v >= 0).all() and (v <= cap + 1e-15).all()
        assert np.abs(v - _bisection(x, a, cap, total)).max() < 1e-9


def test_projection_with_a_zero_budget_is_zero():
    v = project_weighted_capped_simplex(np.array([0.3, -0.1, 0.5]), np.ones(3), np.ones(3), 0.0)
    assert v.tolist() == [0.0, 0.0, 0.0]


def test_projection_refuses_caps_that_cannot_hold_the_budget():
    with pytest.raises(InfeasibleConstraints):
        project_weighted_capped_simplex(np.zeros(3), np.ones(3), np.full(3, 0.3), 1.0)


# ------------------------------------------------------------------ QIS (the browser port is checked in web/test_engine.mjs)
@pytest.mark.parametrize("t,n", [(60, 20), (40, 55)])
def test_qis_is_symmetric_positive_and_keeps_the_trace(t, n):
    rng = np.random.default_rng(t + n)
    x = 0.02 * rng.normal(size=(t, 3)) @ rng.normal(size=(3, n)) + 0.03 * rng.normal(size=(t, n))
    s = qis(x)
    sample = np.cov(x, rowvar=False)
    assert np.allclose(s, s.T) and np.linalg.eigvalsh(s).min() > 0
    assert np.isclose(np.trace(s), np.trace(sample), rtol=1e-10)


# ------------------------------------------------------------------ projections
def _history(t=158, n=3, seed=0):
    rng = np.random.default_rng(seed)
    return rng.normal(0.005, 0.03, size=(t, n))


def test_first_year_does_not_depend_on_the_horizon():
    X, w, g = _history(), np.array([0.5, 0.3, 0.2]), np.array([0.06, 0.04, 0.03])
    a = project(X, w, g, years=5)
    b = project(X, w, g, years=30)
    assert a["one_year"] == b["one_year"] and a["yearly"][1] == b["yearly"][1]


def test_projection_is_reproducible_and_moves_with_the_seed():
    X, w, g = _history(), np.array([0.5, 0.3, 0.2]), np.array([0.06, 0.04, 0.03])
    assert project(X, w, g, seed=7) == project(X, w, g, seed=7)
    assert project(X, w, g, seed=7)["final"] != project(X, w, g, seed=8)["final"]


def test_withdrawals_stop_at_zero_and_count_the_months_paid():
    X, w, g = _history(), np.array([0.5, 0.3, 0.2]), np.array([0.06, 0.04, 0.03])
    out = project(X, w, g, amount=10_000, monthly_contribution=-500, years=5)
    wd = out["withdrawal"]
    assert out["final"]["p90"] == 0.0 and wd["chance_lasts"] == 0.0
    assert 18 <= wd["p50_months"] <= 22  # 10,000 at 500 a month lasts about 20 months
