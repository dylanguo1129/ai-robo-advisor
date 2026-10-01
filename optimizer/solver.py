"""Quadratic-programme solvers for the allocation step.

The problem is

    minimize   (lam / 2) w' Sigma w - mu' w
    subject to sum(w) = 1,  lb <= w <= ub,  optional group bounds.

Two solvers are provided on purpose:

* ``solve_qp_pgd``  - accelerated projected gradient (FISTA with adaptive
  restart) in a diagonally preconditioned space, with an exact projection
  onto the (weighted) capped simplex. No dependencies beyond NumPy, about
  sixty lines, deterministic, and easy to port to JavaScript for the browser
  prototype. Handles box + budget constraints.

  Why the preconditioning: a cash-like ETF has 0.3% volatility next to
  equity ETFs at 15%, so Sigma's condition number is in the thousands and
  plain projected gradient crawls. Working in v = D w with D = diag(sqrt of
  the variances) turns Sigma into a correlation matrix (condition number in
  the tens) and turns the simplex into {a'v = 1, 0 <= v <= D ub} with
  a = 1/diag(D), which is still a one-dimensional bisection to project onto.

* ``solve_qp_slsqp`` - SciPy's SLSQP. The reference in the tests and the
  fallback whenever group constraints are present.

``solve_qp`` picks the right one.
"""

from __future__ import annotations

import numpy as np

EPS = 1e-12


def project_weighted_capped_simplex(x: np.ndarray, a: np.ndarray, cap: np.ndarray, total: float = 1.0, tol: float = 1e-13) -> np.ndarray:
    """Euclidean projection of ``x`` onto {v : a'v = total, 0 <= v <= cap}, a > 0.

    KKT gives v_i = clip(x_i - tau a_i, 0, cap_i); a'v is non-increasing in
    tau, so tau is found by bisection.
    """
    x = np.asarray(x, dtype=float)
    a = np.asarray(a, dtype=float)
    cap = np.asarray(cap, dtype=float)
    if a @ cap < total - 1e-9:
        raise ValueError(f"infeasible: a'cap = {a @ cap:.4f} < {total}")
    lo = float(((x - cap) / a).min()) - 1.0
    hi = float((x / a).max()) + 1.0
    for _ in range(200):
        tau = 0.5 * (lo + hi)
        s = a @ np.clip(x - tau * a, 0.0, cap)
        if s > total:
            lo = tau
        else:
            hi = tau
        if hi - lo < tol:
            break
    v = np.clip(x - 0.5 * (lo + hi) * a, 0.0, cap)
    free = (v > 0) & (v < cap)
    gap = total - a @ v
    if free.any():  # exact budget fix on the interior coordinates
        v[free] += gap * a[free] / (a[free] @ a[free])
        v = np.clip(v, 0.0, cap)
    return v


def project_with_group_cap(x: np.ndarray, a: np.ndarray, cap: np.ndarray, total: float, mask: np.ndarray, group_cap: float) -> np.ndarray:
    """Projection onto {a'v = total, 0 <= v <= cap, sum_{mask} a_i v_i <= group_cap}.

    One inequality on top of the capped simplex. If the plain projection
    already satisfies it we are done; otherwise the constraint binds at the
    optimum (a convex problem with one violated inequality), so the problem
    splits into two independent capped-simplex projections: the group onto
    total ``group_cap`` and the rest onto ``total - group_cap``.
    """
    mask = np.asarray(mask, dtype=bool)
    v = project_weighted_capped_simplex(x, a, cap, total)
    if not mask.any() or a[mask] @ v[mask] <= group_cap + 1e-12:
        return v
    rest = ~mask
    room_rest = float(a[rest] @ cap[rest])
    g = max(group_cap, total - room_rest)  # the rest cannot absorb more than its caps
    out = np.zeros_like(v)
    if g > 1e-15:
        out[mask] = project_weighted_capped_simplex(x[mask], a[mask], cap[mask], g)
    if rest.any() and total - g > 1e-15:
        out[rest] = project_weighted_capped_simplex(x[rest], a[rest], cap[rest], total - g)
    return out


def project_capped_simplex(v: np.ndarray, ub: np.ndarray, total: float = 1.0, tol: float = 1e-13) -> np.ndarray:
    """Projection onto {w : sum(w) = total, 0 <= w <= ub} (unweighted case)."""
    return project_weighted_capped_simplex(v, np.ones(len(v)), ub, total, tol)


def _greedy_max_return(mu: np.ndarray, lb: np.ndarray, ub: np.ndarray) -> np.ndarray:
    """lam = 0 limit: fill the highest-mu assets up to their caps."""
    w = lb.copy()
    room = 1.0 - w.sum()
    for i in np.argsort(-mu):
        take = min(ub[i] - w[i], room)
        w[i] += take
        room -= take
        if room <= EPS:
            break
    return w


def solve_qp_pgd(
    sigma: np.ndarray,
    mu: np.ndarray,
    lam: float,
    lb: np.ndarray | None = None,
    ub: np.ndarray | None = None,
    max_iter: int = 10000,
    tol: float = 1e-10,
    w0: np.ndarray | None = None,
    group_cap: tuple[np.ndarray, float] | None = None,
) -> np.ndarray:
    """FISTA (with adaptive restart) on the box-and-budget constrained QP,
    run in the diagonally preconditioned space described in the module doc.

    ``group_cap = (mask, hi)`` adds sum(w[mask]) <= hi (the satellite cap)."""
    sigma = np.asarray(sigma, dtype=float)
    mu = np.asarray(mu, dtype=float)
    n = len(mu)
    lb = np.zeros(n) if lb is None else np.asarray(lb, dtype=float)
    ub = np.ones(n) if ub is None else np.asarray(ub, dtype=float)
    if (lb < -EPS).any() or (ub < lb - EPS).any():
        raise ValueError("need 0 <= lb <= ub")
    if lb.sum() > 1 + 1e-9:
        raise ValueError(f"infeasible: lower bounds sum to {lb.sum():.4f} > 1")
    if lam <= EPS:
        return _greedy_max_return(mu, lb, ub)

    # shift: u = w - lb lives on {sum u = mass, 0 <= u <= cap}
    mass = 1.0 - lb.sum()
    cap = ub - lb
    if mass <= EPS:
        return lb.copy()

    # precondition: v = d * u with d = sqrt(diag(Sigma)); a = 1/d
    d = np.sqrt(np.clip(np.diag(sigma), 1e-16, None))
    a = 1.0 / d
    corr = sigma / np.outer(d, d)  # D^-1 Sigma D^-1
    capv = cap * d
    # gradient of f(v) = (lam/2) v'corr v - (mu/d)'v + lam * (lb' Sigma D^-1 v)
    g_lin = lam * (sigma @ lb) / d - mu / d
    lip = lam * float(np.linalg.eigvalsh(corr).max())
    step = 1.0 / max(lip, EPS)

    if group_cap is not None:
        gmask = np.asarray(group_cap[0], dtype=bool)
        ghi = float(group_cap[1]) - float(lb[gmask].sum())  # in shifted (u) units; a'v = sum u

        def proj(z):
            return project_with_group_cap(z, a, capv, mass, gmask, max(ghi, 0.0))
    else:

        def proj(z):
            return project_weighted_capped_simplex(z, a, capv, mass)

    v0 = (np.full(n, mass / n) if w0 is None else np.clip(np.asarray(w0, dtype=float) - lb, 0, cap)) * d
    v = proj(v0)
    y = v.copy()
    t_k = 1.0
    for _ in range(max_iter):
        grad = lam * corr @ y + g_lin
        v_next = proj(y - step * grad)
        dv = v_next - v
        if (y - v_next) @ dv > 0:  # adaptive restart (O'Donoghue & Candes)
            t_k = 1.0
            y = v_next.copy()
        else:
            t_next = 0.5 * (1 + np.sqrt(1 + 4 * t_k * t_k))
            y = v_next + ((t_k - 1) / t_next) * dv
            t_k = t_next
        converged = np.abs(dv / d).max() < tol
        v = v_next
        if converged:
            break
    w = v / d + lb
    w = np.clip(w, lb, ub)
    return w / w.sum()


def solve_qp_slsqp(
    sigma: np.ndarray,
    mu: np.ndarray,
    lam: float,
    lb: np.ndarray | None = None,
    ub: np.ndarray | None = None,
    group_bounds: list[tuple[np.ndarray, float, float]] | None = None,
    w0: np.ndarray | None = None,
) -> np.ndarray:
    """Reference solver (SciPy SLSQP). ``group_bounds`` is a list of
    ``(mask, lo, hi)`` meaning lo <= sum(w[mask]) <= hi."""
    from scipy.optimize import minimize

    sigma = np.asarray(sigma, dtype=float)
    mu = np.asarray(mu, dtype=float)
    n = len(mu)
    lb = np.zeros(n) if lb is None else np.asarray(lb, dtype=float)
    ub = np.ones(n) if ub is None else np.asarray(ub, dtype=float)

    # scale the objective so SLSQP's tolerances are meaningful
    scale = 1.0 / max(lam * float(np.abs(sigma).max()), float(np.abs(mu).max()), 1e-8)

    def f(w):
        return scale * (0.5 * lam * w @ sigma @ w - mu @ w)

    def g(w):
        return scale * (lam * sigma @ w - mu)

    cons = [{"type": "eq", "fun": lambda w: w.sum() - 1.0, "jac": lambda w: np.ones(n)}]
    for mask, lo, hi in group_bounds or []:
        m = np.asarray(mask, dtype=float)
        if lo is not None and lo > 0:
            cons.append({"type": "ineq", "fun": (lambda w, m=m, lo=lo: m @ w - lo), "jac": (lambda w, m=m: m)})
        if hi is not None and hi < 1:
            cons.append({"type": "ineq", "fun": (lambda w, m=m, hi=hi: hi - m @ w), "jac": (lambda w, m=m: -m)})
    x0 = solve_qp_pgd(sigma, mu, lam, lb, ub, max_iter=2000, tol=1e-8) if w0 is None else np.asarray(w0, dtype=float)
    res = minimize(f, x0, jac=g, bounds=list(zip(lb, ub)), constraints=cons, method="SLSQP", options={"maxiter": 2000, "ftol": 1e-15})
    w = np.clip(res.x, lb, ub)
    return w / w.sum()


def solve_qp(
    sigma: np.ndarray,
    mu: np.ndarray,
    lam: float,
    lb: np.ndarray | None = None,
    ub: np.ndarray | None = None,
    group_bounds: list[tuple[np.ndarray, float, float]] | None = None,
) -> np.ndarray:
    """Solve the constrained mean-variance QP.

    PGD handles box + budget and a single upper-bounded group (the satellite
    cap); anything else goes to SLSQP."""
    if group_bounds:
        if len(group_bounds) == 1 and (group_bounds[0][1] or 0) <= 0 and group_bounds[0][2] is not None:
            mask, _, hi = group_bounds[0]
            return solve_qp_pgd(sigma, mu, lam, lb, ub, group_cap=(np.asarray(mask, dtype=bool), float(hi)))
        return solve_qp_slsqp(sigma, mu, lam, lb, ub, group_bounds)
    return solve_qp_pgd(sigma, mu, lam, lb, ub)
