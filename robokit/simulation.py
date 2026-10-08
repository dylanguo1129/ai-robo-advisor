"""E3 of the pre-registered v3 evaluation: the shipped pipeline on simulated histories with a known truth.

The engine is not reimplemented: each simulated history is handed to ``engine.build_portfolio`` through its data
loader (``simulated_data``), so the estimates, caps, resampling, minimum position and calibration are the product's.

Data-generating process (monthly, the 10 Canadian reference funds):
* Sigma: the Ledoit-Wolf constant-correlation estimate over the funds' extended history up to the first walk-forward
  (E1) estimation date (``truth_end``), so nothing E1 tests informs it (the truth).
* Means: world 'a' rf + delta Sigma w_prior (the model is right); worlds 'b' and 'c' the FP Canada 2026 planning
  return after the fund's fee, made arithmetic: (1 + g)^(1/12) - 1 + Sigma_ii / 2.
* Shocks: worlds 'a' and 'b' multivariate Student t, 5 degrees of freedom, scale Sigma (nu - 2) / nu so the covariance
  is Sigma, independent over time; world 'c' two regimes (calm and stress) with stay probabilities 0.97 and 0.85, the
  stress covariance 2.5 times the calm one, scaled so the long-run covariance is Sigma, normal within a regime.
* Truth at level L: the target is L x 20% of the true volatility of the policy-weighted equity slots; the true optimum
  maximises mu_excess'w - (gamma/2) w'Sigma w under the engine's limits at that level, gamma set so its true
  volatility equals the target. A method's loss is the certainty equivalent of the true optimum minus its own, at
  that gamma, in basis points a year. This optimum ignores the 2% minimum position, so every method's loss includes
  the cost of discretising; a second oracle applies the engine's minimum-position rule to the truth (``loss_bp_minpos``).
"""

from __future__ import annotations

import math
from contextlib import contextmanager

import numpy as np
import pandas as pd

from optimizer.estimators import choose_covariance, qis
from optimizer.solver import solve_qp_pgd

from . import cma
from . import engine as E
from . import evalstats as es
from . import profile as prof
from .engine import SLEEVE_CAPS, Request, build_portfolio, build_returns, risk_free, select_funds, us_rates
from .evaluation import ENGINE, OUTSIDE, outside_weights
from .shelf import prior_share

NU = 5
STAY = (0.97, 0.85)  # calm, stress
STRESS_MULT = 2.5


def truth_end(market: str) -> str:
    """The first E1 estimation date: every month the walk-forward tests comes after it."""
    from .evaluation import december_dates, reference_shelf

    return str(december_dates(reference_shelf(market).full)[0].date())


def truth(market: str = "CA") -> dict:
    """The fixed ingredients of the simulation. The covariance uses only months before the walk-forward (E1) tests
    anything, so the defaults E3 locks are not informed by E1's test period; the planning returns are 2026
    assumptions, not past returns."""
    shelf, core, _ = select_funds(Request(market=market))
    _, full, _ = build_returns(market, shelf, core, [])
    X = full[core].dropna(how="any").loc[: truth_end(market)]
    S_m, _ = choose_covariance(X.to_numpy(), "lw_cc")
    prior = pd.Series(0.0, index=core)
    for _, r in shelf.iterrows():
        prior[r.ticker] += prior_share(market, r.sleeve)
    prior = prior / prior.sum()
    rf = risk_free(market)[0]
    rf_m = (1 + rf) ** (1 / 12) - 1
    U = E._load_all()[0].set_index("yahoo")
    mu_b = []
    for t in core:
        a, _ = cma.assumption(U.at[t, "asset_class"], U.at[t, "region"], market, us_rates())
        g = (a if a is not None else rf) - (float(U.at[t, "mer"]) if pd.notna(U.at[t, "mer"]) else 0.0)
        mu_b.append((1 + g) ** (1 / 12) - 1 + S_m[core.index(t), core.index(t)] / 2)
    mu_a = rf_m + 2.5 * S_m @ prior.to_numpy()
    eq = [r.ticker for _, r in shelf.iterrows() if r.asset_class == "Equity" and r.prior > 0]
    weq = prior[eq] / prior[eq].sum()
    idx = [core.index(t) for t in eq]
    S_a = 12 * S_m
    eq_vol = float(math.sqrt(weq.to_numpy() @ S_a[np.ix_(idx, idx)] @ weq.to_numpy()))
    caps = {r.ticker: SLEEVE_CAPS[r.sleeve] for _, r in shelf.iterrows() if r.sleeve in SLEEVE_CAPS}
    cash = shelf.loc[shelf.role == "cash", "ticker"].iloc[0]
    return {
        "market": market,
        "tickers": core,
        "Sigma_m": S_m,
        "mu": {"a": mu_a, "b": np.array(mu_b), "c": np.array(mu_b)},
        "rf_m": rf_m,
        "rf": rf,
        "prior": prior,
        "eq_vol": eq_vol,
        "caps": caps,
        "cash": cash,
        "start": X.index[0],
        "truth_months": [str(X.index[0].date()), str(X.index[-1].date()), int(len(X))],
    }


def simulate(tr: dict, world: str, months: int, rng: np.random.Generator) -> np.ndarray:
    """One simulated history (months x funds) from world 'a', 'b' or 'c'."""
    S, mu = tr["Sigma_m"], tr["mu"][world]
    n = len(mu)
    if world in ("a", "b"):
        L = np.linalg.cholesky(S * (NU - 2) / NU)
        z = rng.standard_normal((months, n)) @ L.T
        w = np.sqrt(rng.chisquare(NU, size=(months, 1)) / NU)
        return mu + z / w
    p_stress = (1 - STAY[0]) / ((1 - STAY[0]) + (1 - STAY[1]))
    calm = S / ((1 - p_stress) + p_stress * STRESS_MULT)
    Lc, Ls = np.linalg.cholesky(calm), np.linalg.cholesky(STRESS_MULT * calm)
    state = rng.random() < p_stress
    out = np.empty((months, n))
    for m in range(months):
        out[m] = mu + (Ls if state else Lc) @ rng.standard_normal(n)
        stay = STAY[1] if state else STAY[0]
        if rng.random() > stay:
            state = not state
    return out


@contextmanager
def simulated_data(tr: dict, returns: np.ndarray):
    """Hand ``returns`` (months x funds, in the order of tr['tickers']) to the engine as if it were the price history,
    with a constant bill yield; the fund list and its metadata stay today's."""
    U, _, fx, ctx = E._load_all()
    idx = pd.date_range(tr["start"], periods=len(returns), freq="ME")
    R = pd.DataFrame(returns, index=idx, columns=tr["tickers"])
    col = "V80691344" if tr["market"] == "CA" else "^IRX"
    ctx_s = pd.DataFrame({col: tr["rf"] * 100.0}, index=idx)
    orig = E._load_all
    E._load_all = lambda: (U, R, fx, ctx_s)
    try:
        yield
    finally:
        E._load_all = orig


def true_optimum(tr: dict, world: str, level: float) -> dict:
    """The constrained optimum under the true means and covariance, at the level's true target."""
    n = len(tr["tickers"])
    S = 12 * tr["Sigma_m"]
    mu_x = 12 * (tr["mu"][world] - tr["rf_m"])
    lvl10 = prof.engine_level(level)
    target = prof.risk_share(lvl10) * tr["eq_vol"]
    ub = np.full(n, 0.5)
    for t, c in tr["caps"].items():
        ub[tr["tickers"].index(t)] = c
    ci = tr["tickers"].index(tr["cash"])
    ub[ci] = prof.cash_cap(lvl10) if prof.cash_cap(lvl10) < 1 else 1.0
    lb = np.zeros(n)

    def vol(g):
        w = solve_qp_pgd(S, mu_x, g, lb, ub)
        return float(math.sqrt(w @ S @ w)), w

    lo, hi = 0.05, 2000.0
    if vol(lo)[0] <= target:
        g = lo
    elif vol(hi)[0] >= target:
        g = hi
    else:
        for _ in range(200):
            mid = math.sqrt(lo * hi)
            if vol(mid)[0] > target:
                lo = mid
            else:
                hi = mid
            if hi / lo < 1 + 1e-10:
                break
        g = math.sqrt(lo * hi)
    v, w = vol(g)
    return {"w": w, "gamma": g, "target": target, "vol": v, "S": S, "mu_x": mu_x}


def true_optimum_minpos(tr: dict, world: str, level: float, min_weight: float = 0.02) -> dict:
    """The true optimum after the engine's minimum-position rule: drop positions under ``min_weight``, re-solve and
    recalibrate gamma to the target, round after round until none is small."""
    base = true_optimum(tr, world, level)
    S, mu_x, target = base["S"], base["mu_x"], base["target"]
    n = len(tr["tickers"])
    lvl10 = prof.engine_level(level)
    ub0 = np.full(n, 0.5)
    for t, c in tr["caps"].items():
        ub0[tr["tickers"].index(t)] = c
    ci = tr["tickers"].index(tr["cash"])
    ub0[ci] = prof.cash_cap(lvl10) if prof.cash_cap(lvl10) < 1 else 1.0
    keep = np.ones(n, dtype=bool)
    w, g = base["w"], base["gamma"]
    for _ in range(n):
        small = keep & (w > 1e-9) & (w < min_weight - 1e-9)
        if not small.any():
            break
        trial = keep & ~small
        if (ub0 * trial).sum() < 1 - 1e-9:  # the remaining limits cannot hold everything: keep as is (as the engine)
            break
        keep = trial
        ub = ub0 * keep

        def vol(gg, ub=ub):
            ww = solve_qp_pgd(S, mu_x, gg, np.zeros(n), ub)
            return float(math.sqrt(ww @ S @ ww)), ww

        lo, hi = 0.05, 2000.0
        if vol(lo)[0] <= target:
            g = lo
        elif vol(hi)[0] >= target:
            g = hi
        else:
            for _ in range(200):
                mid = math.sqrt(lo * hi)
                if vol(mid)[0] > target:
                    lo = mid
                else:
                    hi = mid
                if hi / lo < 1 + 1e-10:
                    break
            g = math.sqrt(lo * hi)
        w = vol(g)[1]
    return {"w": w, "gamma": g, "target": target, "vol": float(math.sqrt(w @ S @ w)), "S": S, "mu_x": mu_x}


def band_coverage(band: dict, tickers: list, w_true) -> float:
    """Share of funds whose true optimal weight lies in the resampling band. Every fund counts: a fund the final mix
    does not hold (dropped by the minimum position, or never held) has the band [0, 0]."""
    full = {t: band.get(t, (0.0, 0.0)) for t in tickers}
    return float(np.mean([full[t][0] - 1e-9 <= w_true[i] <= full[t][1] + 1e-9 for i, t in enumerate(tickers)]))


def ce(opt: dict, w: np.ndarray) -> float:
    return float(opt["mu_x"] @ w - opt["gamma"] / 2 * w @ opt["S"] @ w)


def method_weights(tr: dict, returns: np.ndarray, method: str, level: float, seed: int = 0) -> dict:
    """The weights a method would hold after seeing ``returns``."""
    with simulated_data(tr, returns):
        if method in OUTSIDE:
            q = build_portfolio(Request(market=tr["market"], risk_level=level, resample=False), lean=True, research={"stand_ins": False})
            X = q["returns"]
            eq = [
                t
                for t in tr["tickers"]
                if t in E._load_all()[0].set_index("yahoo").index and E._load_all()[0].set_index("yahoo").at[t, "asset_class"] == "Equity"
            ]
            fi = [t for t in tr["tickers"] if E._load_all()[0].set_index("yahoo").at[t, "asset_class"] == "Fixed income"]
            w, _ = outside_weights(method, list(X.columns), X, tr["prior"], tr["cash"], eq, fi, level, q["target_vol"])
            return {"w": w.reindex(tr["tickers"]).fillna(0.0).to_numpy(), "band": None}
        req_kw, research = ENGINE[method]
        q = build_portfolio(
            Request(market=tr["market"], risk_level=level, seed=seed, **req_kw), lean=True, research={**research, "stand_ins": False}
        )
        w = np.array([q["weights"].get(t, 0.0) for t in tr["tickers"]])
        return {"w": w, "band": q["band"], "outcome": q["calibration"]["outcome"] if q["calibration"] else None}


FULL_MONTHS = 192  # the longest study: 180 months, plus 12 for the re-estimate a year later


def history(tr: dict, world: str, rep: int, months: int) -> np.ndarray:
    """The simulated history for (world, rep): one FULL_MONTHS path, of which a study of ``months`` takes the first
    months + 12. Common random numbers: every method and every window length sees the same draws, so the 36-, 60- and
    120-month histories are the first months of the 180-month one."""
    if months + 12 > FULL_MONTHS:
        raise ValueError(f"at most {FULL_MONTHS - 12} months")
    rng = np.random.default_rng([20261008, ord(world), rep])
    return simulate(tr, world, FULL_MONTHS, rng)[: months + 12]


def replicate(task: tuple) -> list[dict]:
    """One simulated history: every method at one level. task = (world, rep, level, methods, months). Common random
    numbers: the history depends only on (world, rep) (``history``)."""
    world, rep, level, methods, months = task
    tr = TRUTH or _truth_cache()
    hist = history(tr, world, rep, months)
    opt = true_optimum(tr, world, level)
    opt_mp = true_optimum_minpos(tr, world, level)
    out = []
    for m in methods:
        try:
            a = method_weights(tr, hist[:months], m, level)
            b = method_weights(tr, hist[12 : months + 12], m, level) if months >= 60 else None
        except Exception as e:  # recorded and counted
            out.append({"world": world, "rep": rep, "level": level, "method": m, "error": f"{type(e).__name__}: {e}"})
            continue
        w = a["w"]
        row = {
            "world": world,
            "rep": rep,
            "level": level,
            "method": m,
            "months": months,
            "loss_bp": 1e4 * (ce(opt, opt["w"]) - ce(opt, w)),
            "loss_bp_minpos": 1e4 * (ce(opt_mp, opt_mp["w"]) - ce(opt_mp, w)),
            "vol_error": float(math.sqrt(w @ opt["S"] @ w)) - opt["target"],
            "distance": 0.5 * float(np.abs(w - opt["w"]).sum()),
            "turnover": None if b is None else 0.5 * float(np.abs(b["w"] - w).sum()),
            "outcome": a.get("outcome"),
        }
        if a["band"]:
            row["band_coverage"] = band_coverage(a["band"], tr["tickers"], opt["w"])
        out.append(row)
    return out


TRUTH = None


def _truth_cache():
    global TRUTH
    if TRUTH is None:
        TRUTH = truth("CA")
    return TRUTH


# ------------------------------------------------------------------ sub-study (ii): where QIS should take over
def qis_switch_sample(task: tuple) -> dict:
    """One sample for the QIS switch study: (truth_name, Sigma_true, n_over_t, rep). The long-only minimum-variance
    portfolio (50% cap) from constant-correlation shrinkage and from QIS, and each one's true variance."""
    name, S, ratio, rep = task
    n = len(S)
    T = int(round(n / ratio))
    rng = np.random.default_rng([20261009, int(ratio * 1000), rep, len(name)])
    X = rng.multivariate_normal(np.zeros(n), S, size=T)
    out = {"truth": name, "n_over_t": ratio, "rep": rep}
    for est in ("lw_cc", "qis"):
        Sh = choose_covariance(X, est)[0] if est == "lw_cc" else qis(X)
        w = es.min_variance(Sh, cap=0.5)
        out[est] = float(w @ S @ w)
    out["rel"] = out["qis"] / out["lw_cc"] - 1
    return out
