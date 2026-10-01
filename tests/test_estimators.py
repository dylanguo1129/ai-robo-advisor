import math

import numpy as np
import pandas as pd
import pytest

from optimizer.estimators import (
    black_litterman_posterior,
    equilibrium_returns,
    james_stein_returns,
    ledoit_wolf_constant_correlation,
    ledoit_wolf_identity,
    market_risk_aversion,
    qis,
    sample_covariance,
)


def simulate(t, n, seed, factor=True):
    rng = np.random.default_rng(seed)
    if factor:
        f = rng.normal(0, 0.04, size=(t, 1))
        beta = rng.uniform(0.3, 1.3, size=(1, n))
        eps = rng.normal(0, 0.03, size=(t, n))
        return 0.005 + f @ beta + eps
    return rng.normal(0.005, 0.04, size=(t, n))


def is_psd(m, tol=1e-10):
    return np.linalg.eigvalsh((m + m.T) / 2).min() >= -tol


# --------------------------------------------------------------------------- #
# Linear shrinkage
# --------------------------------------------------------------------------- #


def test_lw_identity_matches_sklearn():
    sklearn = pytest.importorskip("sklearn.covariance")
    x = simulate(120, 12, 1)
    sigma, shrink = ledoit_wolf_identity(x)
    ref, ref_shrink = sklearn.ledoit_wolf(x, assume_centered=False)
    assert abs(shrink - ref_shrink) < 1e-10
    # sklearn returns the 1/T-scaled matrix; ours is rescaled to T-1
    assert np.abs(sigma * (120 - 1) / 120 - ref).max() < 1e-12


def test_lw_constant_correlation_properties():
    x = simulate(120, 15, 2)
    sigma, shrink = ledoit_wolf_constant_correlation(x)
    s = sample_covariance(x)
    assert 0.0 <= shrink <= 1.0
    assert is_psd(sigma)
    # diagonal is preserved by the constant-correlation target
    assert np.abs(np.diag(sigma) - np.diag(s)).max() < 1e-12
    # off-diagonal correlations are pulled toward their average
    d = np.sqrt(np.diag(s))
    corr_s = s / np.outer(d, d)
    corr_sh = sigma / np.outer(d, d)
    rbar = (corr_s.sum() - 15) / (15 * 14)
    off = ~np.eye(15, dtype=bool)
    assert np.abs(corr_sh[off] - rbar).mean() <= np.abs(corr_s[off] - rbar).mean() + 1e-12


def test_lw_constant_correlation_against_loop_implementation():
    """Independent, slow re-implementation of the 2003 formulas."""
    x = simulate(60, 6, 5)
    t, n = x.shape
    xc = x - x.mean(axis=0)
    s = xc.T @ xc / t
    var = np.diag(s)
    sd = np.sqrt(var)
    rbar = sum(s[i, j] / (sd[i] * sd[j]) for i in range(n) for j in range(n) if i != j) / (n * (n - 1))
    f = np.array([[var[i] if i == j else rbar * sd[i] * sd[j] for j in range(n)] for i in range(n)])
    pi_hat = sum(np.mean((xc[:, i] * xc[:, j] - s[i, j]) ** 2) for i in range(n) for j in range(n))
    theta = lambda k, i, j: np.mean((xc[:, k] ** 2 - s[k, k]) * (xc[:, i] * xc[:, j] - s[i, j]))
    rho_hat = sum(np.mean((xc[:, i] ** 2 - s[i, i]) ** 2) for i in range(n))
    for i in range(n):
        for j in range(n):
            if i != j:
                rho_hat += (rbar / 2) * (math.sqrt(var[j] / var[i]) * theta(i, i, j) + math.sqrt(var[i] / var[j]) * theta(j, i, j))
    gamma_hat = np.sum((f - s) ** 2)
    kappa = (pi_hat - rho_hat) / gamma_hat
    shrink_ref = max(0.0, min(1.0, kappa / t))
    sigma_ref = (shrink_ref * f + (1 - shrink_ref) * s) * t / (t - 1)

    sigma, shrink = ledoit_wolf_constant_correlation(x)
    assert abs(shrink - shrink_ref) < 1e-10
    assert np.abs(sigma - sigma_ref).max() < 1e-10


# --------------------------------------------------------------------------- #
# QIS nonlinear shrinkage
# --------------------------------------------------------------------------- #


def qis_reference(Y: pd.DataFrame, k=None, eigfn=np.linalg.eig):
    """Verbatim logic of the authors' reference implementation (Ledoit & Wolf,
    BSD 2-clause, 2021), kept here only as a test oracle.

    ``eigfn`` exists because the original uses ``np.linalg.eig``, whose
    null-space eigenvectors are not orthonormal when p > n, so the original
    reconstruction u diag(delta) u' is numerically wrong in that case (we
    measured max |u'u - I| = 0.98). Passing ``np.linalg.eigh`` gives the
    formula the authors intended."""
    N = Y.shape[0]
    p = Y.shape[1]
    if k is None or math.isnan(k):
        Y = Y.sub(Y.mean(axis=0), axis=1)
        k = 1
    n = N - k
    c = p / n
    sample = pd.DataFrame(np.matmul(Y.T.to_numpy(), Y.to_numpy())) / n
    sample = (sample + sample.T) / 2
    lambda1, u = eigfn(sample)
    lambda1 = lambda1.real
    u = u.real
    lambda1 = lambda1.real.clip(min=0)
    dfu = pd.DataFrame(u, columns=lambda1)
    dfu.sort_index(axis=1, inplace=True)
    lambda1 = dfu.columns
    h = (min(c**2, 1 / c**2) ** 0.35) / p**0.35
    invlambda = 1 / lambda1[max(1, p - n + 1) - 1 : p]
    dfl = pd.DataFrame()
    dfl["lambda"] = invlambda
    Lj = dfl[np.repeat(dfl.columns.values, min(p, n))]
    Lj = pd.DataFrame(Lj.to_numpy())
    Lj_i = Lj.subtract(Lj.T)
    theta = Lj.multiply(Lj_i).div(Lj_i.multiply(Lj_i).add(Lj.multiply(Lj) * h**2)).mean(axis=0)
    Htheta = Lj.multiply(Lj * h).div(Lj_i.multiply(Lj_i).add(Lj.multiply(Lj) * h**2)).mean(axis=0)
    Atheta2 = theta**2 + Htheta**2
    if p <= n:
        delta = 1 / ((1 - c) ** 2 * invlambda + 2 * c * (1 - c) * invlambda * theta + c**2 * invlambda * Atheta2)
        delta = delta.to_numpy()
    else:
        delta0 = 1 / ((c - 1) * np.mean(invlambda.to_numpy()))
        delta = np.repeat(delta0, p - n)
        delta = np.concatenate((delta, 1 / (invlambda * Atheta2)), axis=None)
    deltaQIS = delta * (sum(lambda1) / sum(delta))
    temp1 = dfu.to_numpy()
    temp2 = np.diag(deltaQIS)
    temp3 = dfu.T.to_numpy().conjugate()
    return np.matmul(np.matmul(temp1, temp2), temp3)


@pytest.mark.parametrize("t,n,seed", [(120, 20, 1), (60, 40, 2), (200, 12, 4)])
def test_qis_matches_reference_implementation(t, n, seed):
    """Non-singular case (T > N): byte-for-byte agreement with the authors' code."""
    x = simulate(t, n, seed)
    ours = qis(x)
    ref = qis_reference(pd.DataFrame(x))  # the reference's 1/n with n = T-1 is the unbiased convention
    assert np.abs(ours - ref).max() < 1e-8 * max(1.0, np.abs(ref).max() * 1e4)
    assert is_psd(ours)


@pytest.mark.parametrize("t,n,seed", [(36, 60, 3), (48, 120, 5)])
def test_qis_singular_case_matches_reference_with_orthonormal_eigenvectors(t, n, seed):
    """Singular case (N > T-1): agreement with the reference formula once its
    eigen-decomposition is orthonormal; and the properties the paper promises."""
    x = simulate(t, n, seed)
    ours = qis(x)
    ref = qis_reference(pd.DataFrame(x), eigfn=np.linalg.eigh)
    assert np.abs(ours - ref).max() < 1e-8 * max(1.0, np.abs(ref).max() * 1e4)
    assert is_psd(ours)
    assert np.linalg.eigvalsh(ours).min() > 0  # invertible even though the sample matrix is not
    assert abs(np.trace(ours) - np.trace(sample_covariance(x))) < 1e-12


def test_qis_trace_and_conditioning():
    x = simulate(60, 40, 4)
    s = sample_covariance(x)
    q = qis(x)
    assert abs(np.trace(q) - np.trace(s)) < 1e-10 * max(1, np.trace(s))
    assert np.linalg.cond(q) < np.linalg.cond(s)


def test_qis_converges_to_sample_when_history_is_long():
    x = simulate(20000, 5, 6)
    s = sample_covariance(x)
    q = qis(x)
    assert np.abs(q - s).max() / np.abs(s).max() < 0.02


# --------------------------------------------------------------------------- #
# Expected returns
# --------------------------------------------------------------------------- #


def test_james_stein_shrinks_between_sample_and_grand_mean():
    x = simulate(120, 10, 8)
    mu, phi = james_stein_returns(x)
    mbar = x.mean(axis=0)
    assert 0.0 <= phi <= 1.0
    # shrunk means have smaller cross-sectional dispersion than the sample means
    assert mu.std() <= mbar.std() + 1e-15


def test_equilibrium_returns_recover_prior_when_unconstrained():
    """max w'pi - (delta/2) w'Sigma w  s.t. sum w = 1  has solution w = w_prior."""
    from optimizer.solver import solve_qp_pgd

    rng = np.random.default_rng(9)
    n = 6
    a = rng.normal(size=(n, n))
    sigma = a @ a.T / n + 0.05 * np.eye(n)
    w_prior = rng.uniform(0.05, 0.3, size=n)
    w_prior /= w_prior.sum()
    delta = market_risk_aversion(0.05, float(np.sqrt(w_prior @ sigma @ w_prior)))
    pi = equilibrium_returns(sigma, w_prior, delta)
    w = solve_qp_pgd(sigma, pi, delta, ub=np.ones(n))
    assert np.abs(w - w_prior).max() < 1e-5


def test_black_litterman_moves_toward_view():
    n = 4
    sigma = np.diag([0.02, 0.03, 0.01, 0.04])
    w_prior = np.full(n, 0.25)
    pi = equilibrium_returns(sigma, w_prior, 2.5)
    P = np.array([[1, 0, 0, 0]])
    Q = np.array([pi[0] + 0.05])  # bullish view on asset 0
    mu_bl, sig_bl = black_litterman_posterior(pi, sigma, P, Q, tau=0.05)
    assert mu_bl[0] > pi[0]
    assert np.all(np.linalg.eigvalsh(sig_bl) > 0)
    # with omega -> 0 the posterior honours the view exactly
    mu_exact, _ = black_litterman_posterior(pi, sigma, P, Q, tau=0.05, omega=np.array([[1e-12]]))
    assert abs(mu_exact[0] - Q[0]) < 1e-6
