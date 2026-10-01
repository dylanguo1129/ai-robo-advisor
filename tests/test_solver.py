import numpy as np
import pytest

from optimizer.solver import project_capped_simplex, solve_qp, solve_qp_pgd, solve_qp_slsqp


def random_pd(n, rng, scale=0.04):
    a = rng.normal(size=(n, n))
    s = a @ a.T / n + 0.2 * np.eye(n)
    d = np.sqrt(np.diag(s))
    corr = s / np.outer(d, d)
    vols = rng.uniform(0.03, 0.25, size=n)
    return corr * np.outer(vols, vols)


def brute_force_projection(v, ub, total):
    # exact projection via a fine 1-D root search on tau (independent implementation)
    taus = np.linspace(v.min() - ub.max() - 1, v.max() + 1, 400001)
    sums = np.clip(v[None, :] - taus[:, None], 0, ub[None, :]).sum(axis=1)
    k = np.argmin(np.abs(sums - total))
    return np.clip(v - taus[k], 0, ub)


@pytest.mark.parametrize("seed", range(5))
def test_projection_matches_brute_force(seed):
    rng = np.random.default_rng(seed)
    n = 8
    v = rng.normal(size=n)
    ub = rng.uniform(0.15, 0.6, size=n)
    w = project_capped_simplex(v, ub, 1.0)
    assert abs(w.sum() - 1) < 1e-9
    assert (w >= -1e-12).all() and (w <= ub + 1e-12).all()
    ref = brute_force_projection(v, ub, 1.0)
    assert np.abs(w - ref).max() < 2e-4


def test_projection_infeasible_raises():
    with pytest.raises(ValueError):
        project_capped_simplex(np.zeros(3), np.full(3, 0.2), 1.0)


@pytest.mark.parametrize("seed", range(8))
def test_pgd_matches_slsqp(seed):
    rng = np.random.default_rng(100 + seed)
    n = rng.integers(4, 15)
    sigma = random_pd(n, rng)
    mu = rng.normal(0.04, 0.03, size=n)
    lam = float(rng.uniform(0.5, 8))
    ub = np.full(n, 0.35)
    w_pgd = solve_qp_pgd(sigma, mu, lam, ub=ub)
    w_ref = solve_qp_slsqp(sigma, mu, lam, ub=ub)

    def obj(w):
        return 0.5 * lam * w @ sigma @ w - mu @ w

    assert abs(w_pgd.sum() - 1) < 1e-8
    assert (w_pgd >= -1e-9).all() and (w_pgd <= 0.35 + 1e-9).all()
    # same objective value (SLSQP can differ slightly in weights on flat regions)
    assert obj(w_pgd) <= obj(w_ref) + 1e-7
    assert np.abs(w_pgd - w_ref).max() < 2e-3


def test_large_lambda_is_minimum_variance():
    rng = np.random.default_rng(7)
    n = 10
    sigma = random_pd(n, rng)
    mu = rng.normal(0.05, 0.02, size=n)
    w_big = solve_qp_pgd(sigma, mu, 1e6, ub=np.ones(n))
    w_mv = solve_qp_pgd(sigma, np.zeros(n), 1.0, ub=np.ones(n))
    assert np.abs(w_big - w_mv).max() < 1e-4


def test_zero_lambda_is_greedy_corner():
    mu = np.array([0.02, 0.10, 0.05, 0.07])
    sigma = np.eye(4) * 0.01
    w = solve_qp_pgd(sigma, mu, 0.0, ub=np.full(4, 0.4))
    assert np.allclose(w, [0.0, 0.4, 0.2, 0.4])


def test_bounds_and_forced_weights_are_respected():
    rng = np.random.default_rng(3)
    n = 6
    sigma = random_pd(n, rng)
    mu = rng.normal(0.04, 0.02, size=n)
    lb = np.array([0.0, 0.25, 0.0, 0.0, 0.0, 0.0])
    ub = np.array([0.3, 0.3, 0.0, 0.3, 0.3, 0.3])  # asset 2 excluded
    w = solve_qp_pgd(sigma, mu, 3.0, lb=lb, ub=ub)
    assert w[1] >= 0.25 - 1e-9
    assert w[2] == 0.0
    assert (w <= ub + 1e-9).all() and abs(w.sum() - 1) < 1e-9


def test_group_bounds_via_dispatch():
    rng = np.random.default_rng(11)
    n = 6
    sigma = random_pd(n, rng)
    mu = np.array([0.08, 0.09, 0.07, 0.01, 0.015, 0.012])  # first three "equity"
    mask = np.array([1, 1, 1, 0, 0, 0], dtype=float)
    w = solve_qp(sigma, mu, 1.0, ub=np.ones(n), group_bounds=[(mask, 0.0, 0.5)])
    assert mask @ w <= 0.5 + 1e-6
    assert abs(w.sum() - 1) < 1e-6
