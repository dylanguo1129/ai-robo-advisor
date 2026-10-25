"""Input estimators: covariance matrices and expected returns.

Design stance (see docs/METHOD.md for the evidence):

* The covariance matrix is the *estimable* input. The product never uses the
  raw sample covariance (it is kept for the evaluation's comparisons); it is shrunk with Ledoit-Wolf linear shrinkage
  (2003/2004) when the universe is small relative to the history, and with
  quadratic-inverse (nonlinear) shrinkage (Ledoit & Wolf, Bernoulli 2022)
  when the number of ETFs is large relative to the number of months.

* Expected returns are the *un-estimable* input at the sample sizes an ETF
  robo-advisor has (100-150 months). Sample means are kept only as a
  benchmark. The default is the CAPM/Black-Litterman equilibrium implied by a
  prior portfolio, which anchors mu to a model instead of to the last decade's
  luck. This is the instructor's slide 39 ("anchor the expected returns (mu)
  and variances to some factors and/or forecast models") and what Betterment
  documents for its own portfolios (mu = lambda * Sigma * w_market).

All functions take a T x N array of (monthly) returns and return quantities
at the same frequency; annualization happens in the optimizer.
"""

from __future__ import annotations

import numpy as np

# --------------------------------------------------------------------------- #
# Covariance
# --------------------------------------------------------------------------- #


def _as_2d(x) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.ndim != 2:
        raise ValueError("returns must be a 2-D array of shape (T, N)")
    if np.isnan(x).any():
        raise ValueError("returns contain NaN; align the panel first (data.to_monthly_returns)")
    return x


def sample_covariance(returns) -> np.ndarray:
    """Plain sample covariance with T-1 degrees of freedom."""
    x = _as_2d(returns)
    return np.atleast_2d(np.cov(x, rowvar=False, ddof=1))  # one fund: a 1 x 1 matrix, as the other estimators give


def ledoit_wolf_identity(returns) -> tuple[np.ndarray, float]:
    """Ledoit & Wolf (2004) shrinkage toward a scaled identity matrix.

    Returns ``(sigma, shrinkage)``. Formula follows the paper (and matches
    scikit-learn's ``ledoit_wolf`` up to the mean-centering convention).
    """
    x = _as_2d(returns)
    t, n = x.shape
    x = x - x.mean(axis=0)
    s = x.T @ x / t
    mu = np.trace(s) / n
    delta2 = np.sum((s - mu * np.eye(n)) ** 2) / n
    beta2 = 0.0
    for row in x:  # sum_t ||x_t x_t' - S||_F^2 / n, divided by t^2
        beta2 += np.sum((np.outer(row, row) - s) ** 2)
    beta2 = beta2 / (t * t) / n
    beta2 = min(beta2, delta2)
    shrink = 0.0 if delta2 == 0 else beta2 / delta2
    sigma = (1 - shrink) * s + shrink * mu * np.eye(n)
    # rescale to the unbiased (T-1) convention used elsewhere
    sigma = sigma * t / (t - 1)
    return sigma, float(shrink)


def ledoit_wolf_constant_correlation(returns) -> tuple[np.ndarray, float]:
    """Ledoit & Wolf (2003, "Honey, I shrunk the sample covariance matrix").

    Shrinks toward the constant-correlation target, which suits asset returns
    better than the identity because it keeps each asset's own variance and
    pulls all pairwise correlations toward their average. Returns
    ``(sigma, shrinkage)`` with the shrinkage intensity clipped to [0, 1].
    """
    x = _as_2d(returns)
    t, n = x.shape
    x = x - x.mean(axis=0)
    s = x.T @ x / t
    var = np.diag(s)
    sd = np.sqrt(var)
    corr = s / np.outer(sd, sd)
    rbar = (corr.sum() - n) / (n * (n - 1))
    f = rbar * np.outer(sd, sd)
    np.fill_diagonal(f, var)

    # pi_hat: sum of asymptotic variances of the sample covariance entries
    x2 = x**2
    pi_mat = (x2.T @ x2) / t - s**2
    pi_hat = pi_mat.sum()

    # rho_hat: sum of asymptotic covariances between entries of S and F
    # theta_{kk,ij} = (1/t) sum_t (x_tk^2 - s_kk)(x_ti x_tj - s_ij)
    term1 = (x**3).T @ x / t  # (i,j): (1/t) sum_t x_ti^3 x_tj
    help_ = term1 - np.outer(var, np.ones(n)) * s  # theta_{ii,ij}
    np.fill_diagonal(help_, 0.0)
    theta_ii_ij = help_
    theta_jj_ij = help_.T
    rho_diag = np.sum(np.diag(pi_mat))
    rho_off = (rbar / 2) * np.sum(np.outer(1 / sd, sd) * theta_ii_ij + np.outer(sd, 1 / sd) * theta_jj_ij)
    rho_hat = rho_diag + rho_off

    gamma_hat = np.sum((f - s) ** 2)
    kappa = (pi_hat - rho_hat) / gamma_hat if gamma_hat > 0 else 0.0
    shrink = float(max(0.0, min(1.0, kappa / t)))
    sigma = shrink * f + (1 - shrink) * s
    sigma = sigma * t / (t - 1)
    return sigma, shrink


def qis(returns, demean: bool = True) -> np.ndarray:
    """Quadratic-Inverse Shrinkage (Ledoit & Wolf, Bernoulli 2022).

    Nonlinear shrinkage: keeps the sample eigenvectors and shrinks the
    *inverse* eigenvalues toward two targets weighted by quadratic functions
    of the concentration ratio c = N/T. This is the estimator to use when the
    universe is large relative to the history (c above roughly 0.25), where
    linear shrinkage leaves the small eigenvalues too small and the
    minimum-variance weights blow up.

    Port of the authors' reference Python code (BSD 2-clause, (c) 2021
    Olivier Ledoit and Michael Wolf) to plain NumPy; the port is checked
    against the original in tests/test_estimators.py.
    """
    y = _as_2d(returns)
    big_n, p = y.shape
    if demean:
        y = y - y.mean(axis=0)
        k = 1
    else:
        k = 0
    n = big_n - k  # effective sample size
    c = p / n  # concentration ratio

    sample = (y.T @ y) / n
    sample = (sample + sample.T) / 2
    lam, u = np.linalg.eigh(sample)  # ascending eigenvalues, orthonormal u
    lam = np.clip(lam, 0.0, None)

    h = (min(c**2, 1 / c**2) ** 0.35) / p**0.35  # smoothing parameter
    start = max(1, p - n + 1) - 1
    if not lam.size or lam[-1] <= 0 or (lam[start:p] <= lam[-1] * RANK_TOL).any():
        # the formulas divide by every eigenvalue past the p - n null ones; a duplicated fund, or a resampled history
        # with fewer distinct months than funds, leaves another one at zero and the result would be NaN
        raise np.linalg.LinAlgError(
            "QIS needs a full-rank sample: the returns are collinear (a duplicated fund, or too few distinct months)"
        )
    invlam = 1.0 / lam[start:p]  # inverse of the non-null eigenvalues
    m = invlam.size
    lj = np.tile(invlam.reshape(m, 1), (1, m))  # column j holds 1/lambda_j
    lj_i = lj - lj.T  # (1/lambda_j) - (1/lambda_i)
    denom = lj_i**2 + (lj**2) * h**2
    theta = (lj * lj_i / denom).mean(axis=0)  # smoothed Stein shrinker
    htheta = (lj * lj * h / denom).mean(axis=0)  # its conjugate
    atheta2 = theta**2 + htheta**2  # squared amplitude

    if p <= n:
        delta = 1.0 / ((1 - c) ** 2 * invlam + 2 * c * (1 - c) * invlam * theta + c**2 * invlam * atheta2)
    else:
        delta0 = 1.0 / ((c - 1) * invlam.mean())  # shrinkage of the null eigenvalues
        delta = np.concatenate([np.repeat(delta0, p - n), 1.0 / (invlam * atheta2)])

    delta_qis = delta * (lam.sum() / delta.sum())  # preserve the trace
    sigma = (u * delta_qis) @ u.T
    sigma = (sigma + sigma.T) / 2
    # n = T - 1 after demeaning, so the 1/n sample matrix above is already the
    # unbiased (T-1) convention used by the other estimators; no rescaling.
    return sigma


RANK_TOL = 1e-12  # eigenvalue / largest eigenvalue at or below which the sample counts as rank-deficient
QIS_SWITCH = 0.25  # N/T above which QIS replaces constant-correlation shrinkage (tested: RESEARCH_LOG section 10, E3)


def choose_covariance(returns, method: str = "auto") -> tuple[np.ndarray, dict]:
    """Dispatch on ``method`` and return ``(sigma, info)``.

    ``auto`` picks constant-correlation linear shrinkage when N/T <= 0.25 and
    QIS above that. The threshold is a judgement call, not a theorem: linear
    shrinkage is easier to explain to a panel, nonlinear shrinkage is what the
    2022 paper and the 2025-26 minimum-variance literature use once the
    universe is wide.
    """
    x = _as_2d(returns)
    t, n = x.shape
    conc = n / t
    if method.startswith("auto"):  # 'auto' switches at N/T = 0.25; 'auto:0.2' at another point (evaluation only)
        cut = float(method.split(":", 1)[1]) if ":" in method else QIS_SWITCH
        method = "qis" if conc > cut else "lw_cc"
    info: dict = {"method": method, "concentration_ratio": conc, "n_assets": n, "n_obs": t}
    if method == "sample":
        sigma = sample_covariance(x)
    elif method == "lw_id":
        sigma, s = ledoit_wolf_identity(x)
        info["shrinkage"] = s
    elif method == "lw_cc":
        sigma, s = ledoit_wolf_constant_correlation(x)
        info["shrinkage"] = s
    elif method == "qis":
        try:
            sigma = qis(x)
        except np.linalg.LinAlgError as e:  # rank-deficient sample: constant-correlation shrinkage is still defined
            sigma, s = ledoit_wolf_constant_correlation(x)
            info.update(method="lw_cc", shrinkage=s, fallback=f"qis: {e}")
    else:
        raise ValueError(f"unknown covariance method {method!r}")
    info["condition_number"] = float(np.linalg.cond(sigma))
    return sigma, info


# --------------------------------------------------------------------------- #
# Expected returns
# --------------------------------------------------------------------------- #


def james_stein_returns(returns, sigma: np.ndarray | None = None) -> tuple[np.ndarray, float]:
    """Jorion (1986) Bayes-Stein shrinkage of the sample mean toward the
    grand mean (the return of the global minimum-variance portfolio).

    Returns ``(mu, phi)`` where ``phi`` in [0, 1] is the weight on the target.
    With 120 months and 20 assets phi is typically 0.5-0.9: the data
    barely move the estimate, which is the honest answer.
    """
    x = _as_2d(returns)
    t, n = x.shape
    mbar = x.mean(axis=0)
    if sigma is None:
        sigma = sample_covariance(x)
    ones = np.ones(n)
    inv = np.linalg.solve(sigma, ones)
    mu0 = float(inv @ mbar / (inv @ ones))  # GMV portfolio mean
    diff = mbar - mu0
    quad = float(diff @ np.linalg.solve(sigma, diff))
    phi = (n + 2) / ((n + 2) + t * quad) if quad > 0 else 1.0
    phi = float(min(1.0, max(0.0, phi)))
    return (1 - phi) * mbar + phi * mu0, phi


def market_risk_aversion(market_premium: float, market_vol: float) -> float:
    """delta = E[r_m - r_f] / sigma_m^2, the risk aversion implied by the
    market portfolio (He & Litterman 1999). With a 5% premium and 15%
    volatility this is 2.2, in the usual 2-3 range."""
    return market_premium / market_vol**2


def equilibrium_returns(sigma: np.ndarray, prior_weights: np.ndarray, delta: float) -> np.ndarray:
    """Reverse-optimized *excess* returns: pi = delta * Sigma * w_prior.

    If an investor with risk aversion ``delta`` holds ``prior_weights``, these
    are the excess returns that make that portfolio optimal. Assets earn a
    premium in proportion to their covariance with the prior portfolio: no
    asset is rewarded for volatility the prior portfolio diversifies away.
    """
    sigma = np.asarray(sigma, dtype=float)
    w = np.asarray(prior_weights, dtype=float)
    return delta * sigma @ w


def black_litterman_posterior(
    pi: np.ndarray,
    sigma: np.ndarray,
    P: np.ndarray,
    Q: np.ndarray,
    tau: float = 0.05,
    omega: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Black-Litterman posterior mean and covariance of expected excess returns.

    ``P`` (K x N) picks the assets each view is about, ``Q`` (K) the view
    values. If ``omega`` is omitted it is set to diag(P tau Sigma P'), the
    He-Litterman convention (view confidence proportional to prior variance).
    Returns ``(mu_bl, sigma_bl)``; ``sigma_bl`` is the covariance to use in
    the optimizer if one wants to reflect estimation uncertainty in returns.
    """
    pi = np.asarray(pi, dtype=float)
    sigma = np.asarray(sigma, dtype=float)
    P = np.atleast_2d(np.asarray(P, dtype=float))
    Q = np.asarray(Q, dtype=float).reshape(-1)
    ts = tau * sigma
    if omega is None:
        omega = np.diag(np.diag(P @ ts @ P.T))
    omega = np.asarray(omega, dtype=float)
    middle = np.linalg.solve(P @ ts @ P.T + omega, np.eye(len(Q)))
    mu_bl = pi + ts @ P.T @ middle @ (Q - P @ pi)
    post_cov = ts - ts @ P.T @ middle @ P @ ts
    return mu_bl, sigma + post_cov


def capm_returns(returns, market_returns, rf_periodic: float) -> tuple[np.ndarray, np.ndarray]:
    """CAPM excess returns from betas against a market series: beta_i * mean(r_m - rf).

    Returns ``(mu_excess, beta)``. Kept as an alternative anchor; the
    equilibrium approach above does the same thing without needing to pick a
    single market index.
    """
    x = _as_2d(returns)
    m = np.asarray(market_returns, dtype=float).reshape(-1) - rf_periodic
    xe = x - rf_periodic
    mm = m - m.mean()
    beta = (xe - xe.mean(axis=0)).T @ mm / (mm @ mm)
    return beta * m.mean(), beta
