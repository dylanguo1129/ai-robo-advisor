"""Statistics for the pre-registered v3 evaluation (docs/RESEARCH_LOG.md section 10). Tested in tests/test_evalstats.py.

* ``sharpe_diff_test``: Ledoit and Wolf (2008), "Robust performance hypothesis testing with the Sharpe ratio",
  Journal of Empirical Finance 15(5): the difference of two Sharpe ratios from paired returns, its standard error by
  the delta method with a prewhitened quadratic-spectral HAC estimate (Andrews 1991; Andrews and Monahan 1992), and a
  p-value from the studentized circular block bootstrap (their Section 3.2).
* ``newey_west_t``: Newey and West (1987) t-statistic of a mean.
* ``holm``: Holm (1979) step-down adjusted p-values.
* ``deflated_sharpe`` and ``min_track_record``: Bailey and Lopez de Prado (2014; 2012).
* ``diebold_mariano``: Diebold and Mariano (1995) on a loss differential, Newey-West variance.
* ``vol_ratio_interval``: a circular block-bootstrap interval for realised over target volatility.
* ``erc_weights`` and ``min_variance``: the benchmark portfolios (Maillard, Roncalli and Teiletche 2010).
"""

from __future__ import annotations

import math

import numpy as np
from scipy import optimize, stats

EULER = 0.5772156649015329


# ------------------------------------------------------------------ HAC covariance (prewhitened QS kernel)
def _qs(x: np.ndarray) -> np.ndarray:
    """Quadratic-spectral kernel (Andrews 1991, eq. 2.7)."""
    x = np.asarray(x, dtype=float)
    out = np.ones_like(x)
    nz = x != 0
    z = 6 * np.pi * x[nz] / 5
    out[nz] = 25 / (12 * np.pi**2 * x[nz] ** 2) * (np.sin(z) / z - np.cos(z))
    return out


def hac_qs_prewhitened(y: np.ndarray) -> np.ndarray:
    """Long-run covariance of the rows of ``y`` (T x k, demeaned inside): VAR(1) prewhitening, the QS kernel with the
    Andrews (1991) AR(1) plug-in bandwidth, recoloured (Andrews and Monahan 1992)."""
    y = np.asarray(y, dtype=float)
    y = y - y.mean(axis=0)
    T, k = y.shape
    X, Y = y[:-1], y[1:]
    A = np.linalg.lstsq(X, Y, rcond=None)[0].T  # y_t = A y_{t-1} + e_t
    e = Y - X @ A.T
    n = len(e)
    # bandwidth: AR(1) fit to each residual series, Andrews (1991) eq. 6.4 with unit weights, alpha(2)
    num = den = 0.0
    for j in range(k):
        x0, x1 = e[:-1, j], e[1:, j]
        rho = float(x0 @ x1 / (x0 @ x0)) if x0 @ x0 > 0 else 0.0
        rho = max(min(rho, 0.97), -0.97)
        s2 = float(np.mean((x1 - rho * x0) ** 2))
        num += 4 * rho**2 * s2**2 / (1 - rho) ** 8
        den += s2**2 / (1 - rho) ** 4
    alpha2 = num / den if den > 0 else 0.0
    bw = 1.3221 * (alpha2 * n) ** 0.2
    S = e.T @ e / n
    if bw > 0:
        for lag in range(1, n):
            w = float(_qs(np.array([lag / bw]))[0])
            G = e[lag:].T @ e[:-lag] / n
            S += w * (G + G.T)
    B = np.linalg.inv(np.eye(k) - A)
    return B @ S @ B.T


# ------------------------------------------------------------------ Ledoit-Wolf (2008)
def _sharpe_parts(ri: np.ndarray, rn: np.ndarray):
    mi, mn = ri.mean(), rn.mean()
    gi, gn = (ri**2).mean(), (rn**2).mean()
    return mi, mn, gi, gn


def _delta_and_grad(mi, mn, gi, gn):
    vi, vn = gi - mi**2, gn - mn**2
    d = mi / math.sqrt(vi) - mn / math.sqrt(vn)
    grad = np.array([gi / vi**1.5, -gn / vn**1.5, -mi / (2 * vi**1.5), mn / (2 * vn**1.5)])
    return d, grad


def _circular_blocks(rng: np.random.Generator, T: int, b: int) -> np.ndarray:
    n_blocks = math.ceil(T / b)
    starts = rng.integers(0, T, n_blocks)
    return ((starts[:, None] + np.arange(b)[None, :]) % T).ravel()[:T]


def sharpe_diff_test(ri, rn, block: int = 6, n_boot: int = 5000, seed: int = 0, margin: float = 0.0) -> dict:
    """H0: Sharpe(i) = Sharpe(n) on paired excess returns. Returns the difference (per period), its HAC standard
    error, the two-sided studentized circular block-bootstrap p-value (Ledoit and Wolf 2008, Section 3.2), the
    studentized bootstrap 95% interval, and a one-sided non-inferiority p-value for H0: difference <= -margin (per
    period), all from the same draws. With one seed for every comparison the block draws are common to all of them."""
    ri, rn = np.asarray(ri, dtype=float), np.asarray(rn, dtype=float)
    T = len(ri)
    mi, mn, gi, gn = _sharpe_parts(ri, rn)
    d, grad = _delta_and_grad(mi, mn, gi, gn)
    y = np.column_stack([ri - mi, rn - mn, ri**2 - gi, rn**2 - gn])
    se = math.sqrt(max(float(grad @ hac_qs_prewhitened(y) @ grad), 1e-300) / T)
    rng = np.random.default_rng(seed)
    b = int(block)
    n_blocks = math.ceil(T / b)
    exceed = 0
    tstar = np.empty(n_boot)
    for k in range(n_boot):
        idx = _circular_blocks(rng, T, b)
        si, sn = ri[idx], rn[idx]
        m = _sharpe_parts(si, sn)
        dd, gg = _delta_and_grad(*m)
        ys = np.column_stack([si - m[0], sn - m[1], si**2 - m[2], sn**2 - m[3]])
        # block-sum estimate of the long-run covariance of the resample (the "natural" estimate of Section 3.2)
        zeta = ys[: n_blocks * b].reshape(-1, b, 4).sum(axis=1) / math.sqrt(b) if len(ys) == n_blocks * b else None
        if zeta is None:  # T not a multiple of b: pad the last block with the first rows of the resample (circular)
            pad = np.vstack([ys, ys[: n_blocks * b - T]])
            zeta = pad.reshape(-1, b, 4).sum(axis=1) / math.sqrt(b)
        psi = zeta.T @ zeta / n_blocks
        se_b = math.sqrt(max(float(gg @ psi @ gg), 1e-300) / T)
        tstar[k] = (dd - d) / se_b
        if abs(dd - d) / se_b >= abs(d) / se:
            exceed += 1
    q_lo, q_hi = np.quantile(tstar, [0.025, 0.975])
    t_ni = (d + margin) / se
    return {
        "diff": d,
        "se": se,
        "p": (exceed + 1) / (n_boot + 1),
        "ci95": (d - q_hi * se, d - q_lo * se),
        "p_noninferior": (int((tstar >= t_ni).sum()) + 1) / (n_boot + 1),
        "margin": margin,
        "T": T,
        "block": b,
        "n_boot": n_boot,
    }


# ------------------------------------------------------------------ means, multiple testing, forecasts
def newey_west_t(x, lags: int = 6) -> dict:
    """t-statistic of the mean of ``x`` with a Newey-West (Bartlett) long-run variance."""
    x = np.asarray(x, dtype=float)
    T = len(x)
    e = x - x.mean()
    s = float(e @ e) / T
    for lag in range(1, lags + 1):
        s += 2 * (1 - lag / (lags + 1)) * float(e[lag:] @ e[:-lag]) / T
    se = math.sqrt(max(s, 1e-300) / T)
    t = float(x.mean() / se)
    return {"mean": float(x.mean()), "se": se, "t": t, "p": float(2 * stats.norm.sf(abs(t)))}


def holm(pvalues) -> list[float]:
    """Holm (1979) adjusted p-values, in the input order."""
    p = np.asarray(pvalues, dtype=float)
    m = len(p)
    order = np.argsort(p, kind="stable")
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return adj.tolist()


def diebold_mariano(loss_a, loss_b, lags: int = 6) -> dict:
    """Equal predictive accuracy of A and B (Diebold and Mariano 1995): the mean of loss_a - loss_b with a
    Newey-West variance. Negative means A has the lower loss."""
    r = newey_west_t(np.asarray(loss_a, dtype=float) - np.asarray(loss_b, dtype=float), lags)
    return {"mean_diff": r["mean"], "t": r["t"], "p": r["p"], "relative": float(np.mean(loss_a) / np.mean(loss_b) - 1)}


# ------------------------------------------------------------------ selection-adjusted Sharpe (Bailey and Lopez de Prado)
def _moments(r):
    r = np.asarray(r, dtype=float)
    sr = r.mean() / r.std(ddof=1)
    return sr, float(stats.skew(r)), float(stats.kurtosis(r, fisher=False))


def deflated_sharpe(r, trial_srs, n_trials: int | None = None) -> dict:
    """Probability that the true Sharpe ratio of ``r`` (per period) exceeds the expected maximum of ``n_trials``
    unskilled trials whose estimated Sharpe ratios have the spread of ``trial_srs`` (Bailey and Lopez de Prado 2014,
    eq. 2 with the expected-maximum approximation)."""
    sr, g3, g4 = _moments(r)
    T = len(r)
    n = int(n_trials or len(trial_srs))
    v = float(np.var(trial_srs, ddof=1)) if len(trial_srs) > 1 else 0.0
    sr0 = math.sqrt(v) * ((1 - EULER) * stats.norm.ppf(1 - 1 / n) + EULER * stats.norm.ppf(1 - 1 / (n * math.e))) if n > 1 else 0.0
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr**2)
    return {"sr": sr, "sr0": sr0, "dsr": float(stats.norm.cdf(z)), "n_trials": n}


def min_track_record(r, sr_star: float = 0.0, alpha: float = 0.05) -> float:
    """Minimum number of periods for the estimated Sharpe ratio of ``r`` to exceed ``sr_star`` with confidence
    1 - alpha (Bailey and Lopez de Prado 2012); infinite when the estimate does not exceed sr_star."""
    sr, g3, g4 = _moments(r)
    if sr <= sr_star:
        return float("inf")
    return float(1 + (1 - g3 * sr + (g4 - 1) / 4 * sr**2) * (stats.norm.ppf(1 - alpha) / (sr - sr_star)) ** 2)


# ------------------------------------------------------------------ realised risk
def vol_ratio_interval(standardised, block: int = 6, n_boot: int = 5000, level: float = 0.90, seed: int = 0) -> dict:
    """Realised over target volatility from monthly returns already divided by each month's target monthly volatility
    (so a mix that delivers its target has ratio 1), with a circular block-bootstrap percentile interval."""
    x = np.asarray(standardised, dtype=float)
    T = len(x)
    ratio = float(x.std(ddof=1))
    rng = np.random.default_rng(seed)
    draws = np.array([x[_circular_blocks(rng, T, block)].std(ddof=1) for _ in range(n_boot)])
    lo, hi = np.quantile(draws, [(1 - level) / 2, 1 - (1 - level) / 2])
    return {"ratio": ratio, "lo": float(lo), "hi": float(hi), "contains_1": bool(lo <= 1 <= hi)}


def max_drawdown(r) -> float:
    w = np.cumprod(1 + np.asarray(r, dtype=float))
    return float((w / np.maximum.accumulate(w) - 1).min())


def cvar(r, level: float = 0.95) -> float:
    """Mean of the worst (1 - level) share of monthly returns (at least one month)."""
    r = np.sort(np.asarray(r, dtype=float))
    k = max(1, int(math.floor((1 - level) * len(r))))
    return float(r[:k].mean())


# ------------------------------------------------------------------ benchmark portfolios
def erc_weights(sigma) -> np.ndarray:
    """Equal risk contribution, long only (Maillard, Roncalli and Teiletche 2010): the solution of
    min 1/2 y'Sigma y - sum log y, normalised to sum to one."""
    S = np.asarray(sigma, dtype=float)
    n = len(S)
    x0 = 1 / np.sqrt(np.diag(S))
    res = optimize.minimize(
        lambda y: 0.5 * y @ S @ y - np.log(y).sum(),
        x0,
        jac=lambda y: S @ y - 1 / y,
        bounds=[(1e-10, None)] * n,
        method="L-BFGS-B",
        options={"ftol": 1e-15, "gtol": 1e-12, "maxiter": 10000},
    )
    y = res.x
    return y / y.sum()


def min_variance(sigma, cap: float = 0.5) -> np.ndarray:
    """Long-only minimum variance with a per-fund cap (the engine's solver with zero expected returns)."""
    from optimizer.solver import solve_qp_pgd

    S = np.asarray(sigma, dtype=float)
    n = len(S)
    return solve_qp_pgd(S, np.zeros(n), 1.0, np.zeros(n), np.full(n, cap))


def mix_with_cash(w_risky, sigma_full, cash_index: int, target: float) -> tuple[np.ndarray, bool]:
    """theta x risky + (1 - theta) x cash with volatility equal to ``target`` (bisection on theta in [0, 1]); returns the
    weights and whether the target was reachable."""
    S = np.asarray(sigma_full, dtype=float)
    n = len(S)
    cash = np.zeros(n)
    cash[cash_index] = 1.0

    def vol(theta):
        w = theta * w_risky + (1 - theta) * cash
        return math.sqrt(max(float(w @ S @ w), 0.0))

    if vol(1.0) <= target:
        return np.asarray(w_risky, dtype=float), False
    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if vol(mid) < target:
            lo = mid
        else:
            hi = mid
    th = 0.5 * (lo + hi)
    return th * np.asarray(w_risky, dtype=float) + (1 - th) * cash, True


# ------------------------------------------------------------------ automatic block length
def politis_white_block(x) -> float:
    """Optimal mean block length of the stationary bootstrap (Politis and White 2004, with the correction of Patton,
    Politis and White 2009): flat-top lag window, bandwidth from the first run of K_n insignificant autocorrelations."""
    x = np.asarray(x, dtype=float)
    x = x - x.mean()
    n = len(x)
    kn = max(5, math.ceil(math.sqrt(math.log10(n))))
    mmax = math.ceil(math.sqrt(n)) + kn
    bmax = math.ceil(min(3 * math.sqrt(n), n / 3))
    acov = np.array([float(x[k:] @ x[: n - k]) / n for k in range(mmax + 1)])
    rho = acov / acov[0]
    thresh = 2 * math.sqrt(math.log10(n) / n)
    m_hat = None
    for m in range(0, mmax - kn + 1):
        if np.all(np.abs(rho[m + 1 : m + kn + 1]) < thresh):
            m_hat = m
            break
    if m_hat is None:
        m_hat = mmax - kn
    M = min(2 * max(m_hat, 1), mmax)
    k = np.arange(-M, M + 1)
    t = np.abs(k) / M
    lam = np.where(t <= 0.5, 1.0, np.where(t <= 1.0, 2 * (1 - t), 0.0))
    R = acov[np.abs(k)]
    G = float(np.sum(lam * np.abs(k) * R))
    g0 = float(np.sum(lam * R))
    b = (2 * G**2 / (2 * g0**2)) ** (1 / 3) * n ** (1 / 3)
    return float(min(max(b, 1.0), bmax))
