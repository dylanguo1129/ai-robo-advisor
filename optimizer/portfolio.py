"""The Robo-Kit allocation engine.

Usage sketch
------------
    panel = to_monthly_returns(load_prices("data/prices_daily_adjclose.csv"))
    opt = RoboKitOptimizer(panel.returns, rf=0.0225, prior_weights=aum_weights)
    opt.fit()
    res = opt.optimize("high", tickers=["XIC.TO", "VFV.TO", "ZAG.TO", "PSA.TO"])
    res.weights, res.exp_vol, res.risk_contributions, res.weight_band

What the class does, in the order the brief asks for it
-------------------------------------------------------
1. ``fit`` estimates *once*, on the whole universe: a shrunk covariance
   matrix (linear or nonlinear shrinkage, chosen by N/T) and equilibrium
   expected returns anchored to a prior portfolio. Estimating on the full
   universe and then slicing is deliberate: the shrinkage has more data to
   work with than any client's five-ETF shortlist would give it.
2. ``RiskProfiles`` maps the client's low / mid / high risk aversion to a
   number lam. The scale is the market's own risk aversion delta, so
   lam = delta means "hold the prior portfolio", lam = 2 delta means "half
   prior portfolio, half cash", and lam below delta tilts toward the
   higher-return ETFs. That makes the three settings explainable.
3. ``optimize`` solves the constrained mean-variance problem on the client's
   shortlist, optionally resampling the history to average out estimation
   error (Michaud 1998; the same idea Betterment documents), and returns
   weights plus everything the education layer needs: expected return and
   volatility, risk contributions, effective number of holdings, a
   confidence band per weight, and a list of plain-language notes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .data import MONTHS_PER_YEAR
from .errors import InfeasibleConstraints
from .estimators import (
    black_litterman_posterior,
    choose_covariance,
    equilibrium_returns,
    james_stein_returns,
    market_risk_aversion,
)
from .rng import Mulberry32, stationary_rows
from .solver import project_capped_simplex, project_with_group_cap, solve_qp

ON_INFEASIBLE = ("raise", "relax")


def _within(w: np.ndarray, lb: np.ndarray, ub: np.ndarray, group_bounds, tol: float = 1e-12) -> bool:
    """Whether the weights keep every fund limit and group limit."""
    if (w < lb - tol).any() or (w > ub + tol).any():
        return False
    for mask, lo, hi in group_bounds or []:
        g = float(np.asarray(mask, dtype=float) @ w)
        if g < float(lo or 0.0) - tol or (hi is not None and g > float(hi) + tol):
            return False
    return True


def tidy_weights(w: np.ndarray, lb: np.ndarray, ub: np.ndarray, group_bounds, cut: float) -> np.ndarray:
    """Zero the weights below ``cut`` that no minimum holds, and rescale the rest to 100%. The rescaling must not push a
    fund past its cap or a group past its limit (a fund at its cap grows with the others): when it would, the weights are
    projected back onto the limits with the dropped funds held at zero, and if no such projection exists they are left as
    they came (the solver's answer and the average of its answers keep every limit)."""
    drop = (np.abs(w) < cut) & (lb <= 0)
    x = np.where(drop, 0.0, w)
    x = x / x.sum()
    if _within(x, lb, ub, group_bounds):
        return x
    ub0 = np.where(drop, 0.0, ub)
    mass = 1.0 - float(lb.sum())
    try:
        if not group_bounds:
            y = lb + project_capped_simplex(x - lb, ub0 - lb, mass)
        elif len(group_bounds) == 1 and (group_bounds[0][1] or 0) <= 0 and group_bounds[0][2] is not None:
            m = np.asarray(group_bounds[0][0], dtype=bool)
            y = lb + project_with_group_cap(x - lb, np.ones(len(x)), ub0 - lb, mass, m, float(group_bounds[0][2]) - float(lb[m].sum()))
        else:
            y = None
    except InfeasibleConstraints:
        y = None
    return y if y is not None and _within(y, lb, ub, group_bounds, 1e-9) else w


def relax_caps(
    tick: list[str], ub: np.ndarray, need_total: float, relax_order: list[list[str]] | None, frozen: set[str]
) -> tuple[np.ndarray, list[dict]]:
    """Raise caps that cannot reach ``need_total``, one group at a time in ``relax_order``.

    Inside a group every cap is multiplied by the same factor (capped at 100%), so the caps keep their
    proportions; a later group is touched only if the earlier ones could not make enough room. Funds in
    ``frozen`` (exclusions) never come back. Returns the new caps and one record per cap that moved."""
    ub = ub.astype(float).copy()
    pos = {t: i for i, t in enumerate(tick)}
    groups = relax_order if relax_order else [list(tick)]
    seen: set[str] = set()
    ordered = []
    for g in groups + [list(tick)]:  # anything not named in relax_order goes last
        members = [t for t in g if t in pos and t not in seen and t not in frozen]
        seen.update(members)
        if members:
            ordered.append(members)
    steps = []
    for members in ordered:
        need = need_total - ub.sum()
        if need <= 1e-12:
            break
        idx = np.array([pos[t] for t in members])
        before = ub[idx].copy()
        room = float(np.sum(1.0 - before))
        if room <= 1e-12 or not (before > 0).any():
            continue
        if room <= need + 1e-12:
            ub[idx] = 1.0
        else:  # the factor f >= 1 with sum(min(1, f * cap)) - sum(cap) = need
            lo, hi = 1.0, 1.0 / float(before[before > 0].min())
            for _ in range(200):
                f = 0.5 * (lo + hi)
                if np.minimum(1.0, f * before).sum() - before.sum() < need:
                    lo = f
                else:
                    hi = f
            ub[idx] = np.minimum(1.0, hi * before)
        for k, i in enumerate(idx):
            if ub[i] > before[k] + 1e-12:
                steps.append({"limit": "cap", "ticker": tick[i], "requested": float(before[k]), "applied": float(ub[i])})
    return ub, steps


@dataclass
class RiskProfiles:
    """Risk-aversion multipliers relative to the market's own risk aversion.

    ``low`` aversion (growth investor) uses 0.6 x delta, ``mid`` 1.0 x delta
    (the prior portfolio is optimal by construction), ``high`` 2.5 x delta.
    ``RoboKitOptimizer.calibrate_to_target_vol`` can replace these with
    multipliers that hit target volatilities instead.
    """

    low: float = 0.6
    mid: float = 1.0
    high: float = 2.5

    def as_dict(self) -> dict[str, float]:
        return {"low": self.low, "mid": self.mid, "high": self.high}


@dataclass
class OptimizationResult:
    profile: str
    risk_aversion: float
    weights: pd.Series
    exp_return: float  # annualized, total (rf + excess)
    exp_vol: float  # annualized
    sharpe: float
    risk_contributions: pd.Series  # fraction of portfolio variance from each ETF
    effective_n: float  # 1 / sum(w^2)
    weight_band: pd.DataFrame | None  # columns: std, q05, q95 (resampling)
    notes: list[str] = field(default_factory=list)
    diagnostics: dict = field(default_factory=dict)
    relaxations: list[dict] = field(default_factory=list)  # every limit that was relaxed (on_infeasible="relax" only)

    def to_dict(self) -> dict:
        d = {
            "profile": self.profile,
            "risk_aversion": self.risk_aversion,
            "weights": {k: round(float(v), 6) for k, v in self.weights.items()},
            "exp_return": round(self.exp_return, 6),
            "exp_vol": round(self.exp_vol, 6),
            "sharpe": round(self.sharpe, 4),
            "risk_contributions": {k: round(float(v), 6) for k, v in self.risk_contributions.items()},
            "effective_n": round(self.effective_n, 3),
            "notes": self.notes,
            "diagnostics": self.diagnostics,
            "relaxations": self.relaxations,
        }
        if self.weight_band is not None:
            d["weight_band"] = {k: {c: round(float(v), 6) for c, v in row.items()} for k, row in self.weight_band.iterrows()}
        return d


class RoboKitOptimizer:
    def __init__(
        self,
        returns: pd.DataFrame,
        rf: float = 0.0225,
        prior_weights: pd.Series | dict | None = None,
        delta: float | None = 2.5,
        market_premium: float | None = None,
        cov_method: str = "auto",
        mu_method: str = "equilibrium",
        w_max: float = 0.35,
        cash_ticker: str | None = None,
        cash_max: float = 1.0,
        profiles: RiskProfiles | None = None,
        views: dict | None = None,
        naive_blend: float = 0.0,
        resample_method: str = "stationary",
        block_length: int = 6,
    ) -> None:
        """
        returns        T x N DataFrame of *monthly* simple returns, aligned (no NaN).
        rf             annual risk-free rate (Bank of Canada overnight target, 2.25% on 2 Sep 2026).
        prior_weights  the portfolio whose implied returns anchor mu (AUM shares of the
                       universe by default). Must be non-negative; is normalized to sum to 1.
        delta          the market's risk aversion in pi = delta * Sigma * w_prior. 2.5 is
                       the conventional value (He & Litterman 1999 use 2.5; Idzorek's guide
                       reports the 2-3 range). It fixes the *scale* of expected returns:
                       the prior portfolio's implied premium is delta * vol_prior^2.
        market_premium alternative to ``delta``: the annual excess return you believe the
                       prior portfolio earns; then delta = premium / vol_prior^2.
        cov_method     'auto' | 'lw_cc' | 'lw_id' | 'qis' | 'sample'.
        mu_method      'equilibrium' (default) | 'james_stein' | 'sample' | 'black_litterman'.
        w_max          default cap per ETF (the brief's tool lets the client change it).
        cash_ticker    the ETF treated as the safe asset (its cap is ``cash_max`` instead of
                       ``w_max`` so a very cautious client can hold mostly cash). None = no
                       special asset.
        cash_max       cap on the cash ETF (1.0 = unlimited; robo-advisors often cap cash).
        views          optional Black-Litterman views {'P': KxN, 'Q': K, 'tau': float, 'omega': KxK}.
        naive_blend    kappa in w = (1-kappa) w_opt + kappa (1/N): Tu & Zhou (2011) style
                       blend with equal weights over the shortlist. 0 = pure optimizer.
        resample_method 'stationary' (Politis-Romano block bootstrap, keeps volatility
                       clustering) or 'iid' (plain row bootstrap).
        block_length   mean block length in months for the stationary bootstrap.
        """
        if returns.isna().any().any():
            raise ValueError("returns must be aligned with no NaN (use data.to_monthly_returns)")
        self.returns = returns.copy()
        self.tickers = list(returns.columns)
        self.rf = float(rf)
        if delta is None and market_premium is None:
            raise ValueError("give delta or market_premium")
        self._delta_arg = None if delta is None else float(delta)
        self.market_premium = None if market_premium is None else float(market_premium)
        self.cov_method = cov_method
        self.mu_method = mu_method
        self.w_max = float(w_max)
        self.cash_ticker = cash_ticker
        self.cash_max = float(cash_max)
        self.profiles = profiles or RiskProfiles()
        self.views = views
        if not 0.0 <= naive_blend <= 1.0:
            raise ValueError("naive_blend must be in [0, 1]")
        self.naive_blend = float(naive_blend)
        if resample_method not in ("stationary", "iid"):
            raise ValueError("resample_method must be 'stationary' or 'iid'")
        self.resample_method = resample_method
        self.block_length = max(1, int(block_length))
        if prior_weights is None:
            pw = pd.Series(1.0, index=self.tickers)
        else:
            pw = pd.Series(prior_weights, dtype=float).reindex(self.tickers)
            if pw.isna().any():
                raise ValueError(f"prior_weights missing for {list(pw.index[pw.isna()])}")
            if (pw < 0).any():
                raise ValueError("prior_weights must be non-negative")
        self.prior_weights = pw / pw.sum()
        self._fitted = False

    # ------------------------------------------------------------------ #
    # Estimation
    # ------------------------------------------------------------------ #
    def fit(self) -> RoboKitOptimizer:
        x = self.returns.to_numpy()
        sigma_m, info = choose_covariance(x, self.cov_method)
        self.sigma = pd.DataFrame(sigma_m * MONTHS_PER_YEAR, index=self.tickers, columns=self.tickers)
        self.cov_info = info

        w0 = self.prior_weights.to_numpy()
        prior_vol = float(np.sqrt(w0 @ self.sigma.to_numpy() @ w0))
        if self.market_premium is not None:
            self.delta = market_risk_aversion(self.market_premium, prior_vol)
        else:
            self.delta = self._delta_arg
            self.market_premium = self.delta * prior_vol**2  # implied premium of the prior
        self.prior_vol = prior_vol

        if self.mu_method == "equilibrium":
            mu_ex = equilibrium_returns(self.sigma.to_numpy(), w0, self.delta)
            mu_info = {"method": "equilibrium", "delta": self.delta, "prior_vol": prior_vol, "prior_implied_premium": self.market_premium}
        elif self.mu_method == "black_litterman":
            pi = equilibrium_returns(self.sigma.to_numpy(), w0, self.delta)
            v = self.views or {}
            mu_ex, sig_bl = black_litterman_posterior(pi, self.sigma.to_numpy(), v["P"], v["Q"], v.get("tau", 0.05), v.get("omega"))
            self.sigma = pd.DataFrame(sig_bl, index=self.tickers, columns=self.tickers)
            mu_info = {"method": "black_litterman", "delta": self.delta, "n_views": len(np.atleast_1d(v["Q"]))}
        elif self.mu_method == "james_stein":
            mu_m, phi = james_stein_returns(x, sigma_m)
            mu_ex = mu_m * MONTHS_PER_YEAR - self.rf
            mu_info = {"method": "james_stein", "phi": phi}
        elif self.mu_method == "sample":
            mu_ex = x.mean(axis=0) * MONTHS_PER_YEAR - self.rf
            mu_info = {"method": "sample"}
        else:
            raise ValueError(f"unknown mu_method {self.mu_method!r}")
        self.mu_excess = pd.Series(mu_ex, index=self.tickers)
        self.mu_info = mu_info
        self._fitted = True
        return self

    def _require_fit(self):
        if not self._fitted:
            raise RuntimeError("call fit() first")

    # ------------------------------------------------------------------ #
    # Risk-aversion mapping
    # ------------------------------------------------------------------ #
    def lam_for(self, profile: str | float) -> float:
        self._require_fit()
        if isinstance(profile, (int, float)) and not isinstance(profile, bool):
            return float(profile)
        mult = self.profiles.as_dict().get(str(profile))
        if mult is None:
            raise ValueError(f"profile must be low/mid/high or a number, got {profile!r}")
        return mult * self.delta

    def calibrate_to_target_vol(self, targets: dict[str, float], tickers: list[str] | None = None, n_iter: int = 50, **kw) -> RiskProfiles:
        """Set the three multipliers so each profile's portfolio (on the given
        universe, default all) has the target annual volatility. Uses bisection
        on lam; volatility is monotone non-increasing in lam. Targets outside
        the reachable range get the boundary lam (max-return or min-variance)."""
        self._require_fit()
        mults = {}
        for name, tv in targets.items():
            lo, hi = 0.02, 200.0
            for _ in range(n_iter):
                mid = np.sqrt(lo * hi)
                vol = self.optimize(mid * self.delta, tickers=tickers, resample=False, **kw).exp_vol
                if vol > tv:
                    lo = mid
                else:
                    hi = mid
            mults[name] = float(np.sqrt(lo * hi))
        self.profiles = RiskProfiles(**{**self.profiles.as_dict(), **mults})
        return self.profiles

    # ------------------------------------------------------------------ #
    # Optimization
    # ------------------------------------------------------------------ #
    def _bounds(
        self,
        tick: list[str],
        w_max: float,
        forced: dict[str, float],
        excluded: list[str],
        caps: dict[str, float] | None = None,
        on_infeasible: str = "raise",
        relax_order: list[list[str]] | None = None,
    ):
        """(lower bounds, upper bounds, relaxations). Caps that cannot reach 100% either raise
        ``InfeasibleConstraints`` (the default) or, with ``on_infeasible="relax"``, are raised group by group
        in ``relax_order`` and every change is returned. A client minimum above a cap overrides the cap."""
        if on_infeasible not in ON_INFEASIBLE:
            raise ValueError(f"on_infeasible must be one of {ON_INFEASIBLE}")
        n = len(tick)
        lb = np.zeros(n)
        ub = np.full(n, w_max)
        caps = caps or {}
        for i, t in enumerate(tick):
            if t == self.cash_ticker:
                ub[i] = max(self.cash_max, w_max)  # a cautious client may hold mostly cash
            if t in caps:
                ub[i] = min(ub[i], float(caps[t]))  # per-fund cap (sleeve guardrail, satellite, crypto, cash)
            if t in excluded:
                ub[i] = 0.0  # exclusion wins over every other rule
            elif t in forced:
                lb[i] = max(lb[i], float(forced[t]))
        relaxations: list[dict] = []
        for i, t in enumerate(tick):  # a client minimum above a fund's limit is a conflict, not a silent override
            if lb[i] > ub[i] + 1e-12:
                details = {"kind": "minimum_above_cap", "ticker": t, "minimum": float(lb[i]), "cap": float(ub[i])}
                if on_infeasible == "raise":
                    raise InfeasibleConstraints(f"The minimum of {lb[i]:.1%} for {t} is above its limit of {ub[i]:.1%}.", details)
                relaxations.append({"limit": "cap", "ticker": t, "requested": float(ub[i]), "applied": float(lb[i]), "reason": "minimum"})
                ub[i] = lb[i]
        if lb.sum() > 1 + 1e-9:
            raise InfeasibleConstraints(
                f"The minimums add up to {lb.sum():.0%}, more than 100%.",
                {
                    "kind": "minimums",
                    "minimums_total": float(lb.sum()),
                    "minimums": {t: float(lb[i]) for i, t in enumerate(tick) if lb[i] > 0},
                },
            )
        if ub.sum() < 1 - 1e-9:
            details = {"kind": "caps", "capacity": float(ub.sum()), "needed": 1.0, "caps": {t: float(ub[i]) for i, t in enumerate(tick)}}
            if on_infeasible == "raise":
                raise InfeasibleConstraints(
                    f"The limits on these funds add up to {ub.sum():.0%}, so they cannot hold 100% of the money.", details
                )
            ub, steps = relax_caps(tick, ub, 1.0, relax_order, set(excluded))
            relaxations += steps
            if ub.sum() < 1 - 1e-9:
                raise InfeasibleConstraints(f"Even with every limit relaxed these funds hold only {ub.sum():.0%}.", details)
        return lb, ub, relaxations

    def _group_bounds(self, tick, lb, ub, group_bounds, on_infeasible):
        """Masks for the group limits, checked against the fund caps: (list of (mask, lo, hi), relaxations)."""
        out, relaxations = [], []
        for name, (members, lo, hi) in group_bounds.items():
            mask = np.array([t in members for t in tick], dtype=float)
            m = mask.astype(bool)
            if not m.any():
                continue
            lo = float(lo or 0.0)
            hi = 1.0 if hi is None else float(hi)
            needed = max(float(lb[m].sum()), 1.0 - float(ub[~m].sum()))  # the group must hold its minimums and what the rest cannot
            if lo > float(ub[m].sum()) + 1e-9:
                raise InfeasibleConstraints(
                    f"The group '{name}' must hold {lo:.0%} but its funds can hold only {ub[m].sum():.0%}.",
                    {"kind": "group_floor", "group": name},
                )
            if hi < needed - 1e-9:
                details = {"kind": "group_cap", "group": name, "cap": hi, "needed": needed, "group_minimums": float(lb[m].sum())}
                if on_infeasible == "raise":
                    raise InfeasibleConstraints(
                        f"The limit of {hi:.0%} on '{name}' cannot hold: the group needs at least {needed:.0%}.", details
                    )
                relaxations.append({"limit": "group", "group": name, "requested": hi, "applied": needed})
                hi = needed
            out.append((mask, lo, hi))
        return out, relaxations

    def _solve(self, sigma: np.ndarray, mu: np.ndarray, lam: float, lb, ub, group_bounds) -> np.ndarray:
        w = tidy_weights(solve_qp(sigma, mu, lam, lb, ub, group_bounds), lb, ub, group_bounds, 1e-6)
        if self.naive_blend > 0:
            allowed = ub > 0
            ew = allowed / allowed.sum()
            w = (1 - self.naive_blend) * w + self.naive_blend * ew
            w = np.clip(w, lb, ub)
            w = w / w.sum()
        return w

    def optimize(
        self,
        profile: str | float = "mid",
        tickers: list[str] | None = None,
        forced: dict[str, float] | None = None,
        excluded: list[str] | None = None,
        w_max: float | None = None,
        group_bounds: dict[str, tuple[list[str], float, float]] | None = None,
        resample: bool = True,
        n_boot: int = 500,
        seed: int = 0,
        min_weight: float = 0.0,
        caps: dict[str, float] | None = None,
        on_infeasible: str = "raise",
        relax_order: list[list[str]] | None = None,
    ) -> OptimizationResult:
        """Optimal weights for one client.

        profile       'low' | 'mid' | 'high' or a numeric risk aversion lam.
        tickers       the client's shortlist (default: whole universe).
        forced        {ticker: minimum weight} for ETFs the client insists on.
        excluded      tickers to force to zero (e.g. leveraged funds).
        w_max         cap per ETF; overrides the instance default.
        group_bounds  {'name': (tickers, lo, hi)} e.g. {'equity': ([...], 0.0, 0.7)}.
        resample      average the weights over bootstrap re-estimations of Sigma
                      (and mu when mu depends on the data). Off = point estimate.
        min_weight    drop positions below this size and re-solve once, so the
                      client is not asked to buy 0.5% of a fund (implementation
                      constraint, not an estimation choice). 0 = keep everything.
        caps          {ticker: maximum weight} for individual funds, tighter than w_max.
        on_infeasible 'raise' (default): limits that cannot all hold raise InfeasibleConstraints.
                      'relax': caps are raised group by group in ``relax_order`` (then any
                      fund not named), group caps to the smallest workable value, and every
                      change is listed in ``result.relaxations``.
        """
        self._require_fit()
        tick = list(tickers) if tickers else list(self.tickers)
        unknown = [t for t in tick if t not in self.tickers]
        if unknown:
            raise ValueError(f"not in the fitted universe: {unknown}")
        forced = dict(forced or {})
        excluded = list(excluded or [])
        w_max = self.w_max if w_max is None else float(w_max)
        lam = self.lam_for(profile)
        notes: list[str] = []

        idx = [self.tickers.index(t) for t in tick]
        sigma = self.sigma.to_numpy()[np.ix_(idx, idx)]
        mu = self.mu_excess.to_numpy()[idx]
        lb, ub, relaxations = self._bounds(tick, w_max, forced, excluded, caps, on_infeasible, relax_order)
        gb = None
        if group_bounds:
            gb, g_relax = self._group_bounds(tick, lb, ub, group_bounds, on_infeasible)
            relaxations += g_relax
            gb = gb or None
        for r in relaxations:
            what = f"the limit on {r['ticker']}" if r["limit"] == "cap" else f"the limit on '{r['group']}'"
            notes.append(
                f"{what[0].upper() + what[1:]} was raised from {r['requested']:.0%} to {r['applied']:.0%} so the funds can hold 100%."
            )

        w_point = self._solve(sigma, mu, lam, lb, ub, gb)

        band = None
        diagnostics = {"lam": lam, "n_assets": len(tick), "resampled": bool(resample), "naive_blend": self.naive_blend}
        if resample and n_boot > 0:
            diagnostics["resample_method"] = self.resample_method
            if self.resample_method == "stationary":
                diagnostics["block_length"] = self.block_length
            w_boot = self._resample_weights(tick, idx, lam, lb, ub, gb, n_boot, seed)
            w_final = tidy_weights(w_boot.mean(axis=0), lb, ub, gb, 1e-4)
            band = pd.DataFrame(
                {"std": w_boot.std(axis=0), "q05": np.quantile(w_boot, 0.05, axis=0), "q95": np.quantile(w_boot, 0.95, axis=0)},
                index=tick,
            )
            diagnostics["n_boot"] = n_boot
            diagnostics["point_estimate_weights"] = {t: round(float(v), 6) for t, v in zip(tick, w_point)}
            diagnostics["mean_abs_change_vs_point"] = float(np.abs(w_final - w_point).mean())
        else:
            w_final = w_point

        if min_weight > 0:
            small = (w_final > 0) & (w_final < min_weight) & (lb == 0)
            if small.any():
                ub2 = ub.copy()
                ub2[small] = 0.0
                if ub2.sum() >= 1 - 1e-9:
                    w_final = self._solve(sigma, mu, lam, lb, ub2, gb)
                    notes.append(f"{int(small.sum())} position(s) below {min_weight:.0%} were dropped and the rest re-optimized.")
                    diagnostics["dropped_small"] = [t for t, s in zip(tick, small) if s]

        port_var = float(w_final @ sigma @ w_final)
        vol = float(np.sqrt(port_var))
        exc = float(mu @ w_final)
        rc = w_final * (sigma @ w_final) / port_var if port_var > 0 else np.zeros_like(w_final)
        eff_n = float(1.0 / np.sum(w_final**2))

        if self.cash_ticker in tick:
            c = w_final[tick.index(self.cash_ticker)]
            if c > 0.5:
                notes.append(
                    f"{c:.0%} sits in the cash-like ETF: at this risk aversion the model prefers safety over the small extra return of the other funds."
                )
        top = tick[int(np.argmax(rc))]
        notes.append(
            f"{top} contributes the largest share of portfolio risk ({rc.max():.0%}); weights and risk shares differ because risk depends on volatility and correlation, not only on the dollar amount."
        )
        if band is not None:
            wide = band["q95"] - band["q05"]
            if (wide > 0.25).any():
                notes.append(
                    "Some weights have a wide confidence band: the history does not pin them down, which is why the model averages over resampled histories instead of trusting one estimate."
                )

        return OptimizationResult(
            profile=str(profile),
            risk_aversion=lam,
            weights=pd.Series(w_final, index=tick),
            exp_return=self.rf + exc,
            exp_vol=vol,
            sharpe=(exc / vol) if vol > 0 else 0.0,
            risk_contributions=pd.Series(rc, index=tick),
            effective_n=eff_n,
            weight_band=band,
            notes=notes,
            diagnostics=diagnostics,
            relaxations=relaxations,
        )

    def _bootstrap_rows(self, rng: np.random.Generator, t: int) -> np.ndarray:
        """Row indices for one bootstrap draw of length t.

        'iid' draws months independently. 'stationary' (Politis & Romano 1994)
        draws blocks whose length is geometric with mean ``block_length``,
        wrapping around the end of the sample, so that the volatility
        clustering and autocorrelation of monthly returns survive the
        resampling."""
        if self.resample_method == "iid":
            return rng.integers(0, t, size=t)
        p = 1.0 / self.block_length
        rows = np.empty(t, dtype=int)
        i = 0
        while i < t:
            start = rng.integers(0, t)
            length = rng.geometric(p)
            for k in range(length):
                if i >= t:
                    break
                rows[i] = (start + k) % t
                i += 1
        return rows

    def _resample_weights(self, tick, idx, lam, lb, ub, gb, n_boot, seed) -> np.ndarray:
        """Bootstrap the monthly history; re-estimate Sigma (and mu, through
        the estimator) on each draw; re-solve; stack. The stationary draws come from
        the generator both engines share (optimizer/rng.py; web/engine.js), seeded
        ``seed + 1`` as the browser does, so both engines resample the same histories."""
        x_full = self.returns.to_numpy()
        t = x_full.shape[0]
        shared = self.resample_method == "stationary"
        rng = Mulberry32(seed + 1) if shared else np.random.default_rng(seed)
        w0 = self.prior_weights.to_numpy()
        out = np.zeros((n_boot, len(tick)))
        for b in range(n_boot):
            rows = stationary_rows(rng, t, t, self.block_length) if shared else self._bootstrap_rows(rng, t)
            xb = x_full[rows]
            sig_b, _ = choose_covariance(xb, self.cov_info["method"])
            sig_b = sig_b * MONTHS_PER_YEAR
            if self.mu_method in ("equilibrium", "black_litterman"):
                mu_b = equilibrium_returns(sig_b, w0, self.delta)
                if self.mu_method == "black_litterman":
                    v = self.views or {}
                    mu_b, sig_b = black_litterman_posterior(mu_b, sig_b, v["P"], v["Q"], v.get("tau", 0.05), v.get("omega"))
            elif self.mu_method == "james_stein":
                m, _ = james_stein_returns(xb, sig_b / MONTHS_PER_YEAR)
                mu_b = m * MONTHS_PER_YEAR - self.rf
            else:
                mu_b = xb.mean(axis=0) * MONTHS_PER_YEAR - self.rf
            out[b] = self._solve(sig_b[np.ix_(idx, idx)], mu_b[idx], lam, lb, ub, gb)
        return out

    # ------------------------------------------------------------------ #
    # Convenience
    # ------------------------------------------------------------------ #
    def frontier(self, lams: list[float], tickers: list[str] | None = None, **kw) -> pd.DataFrame:
        """Expected return / volatility along a grid of risk aversions."""
        rows = []
        for lam in lams:
            r = self.optimize(float(lam), tickers=tickers, resample=False, **kw)
            rows.append({"lam": lam, "exp_return": r.exp_return, "exp_vol": r.exp_vol, "sharpe": r.sharpe, "effective_n": r.effective_n})
        return pd.DataFrame(rows)

    def three_profiles(self, tickers: list[str] | None = None, **kw) -> dict[str, OptimizationResult]:
        return {p: self.optimize(p, tickers=tickers, **kw) for p in ("low", "mid", "high")}

    @staticmethod
    def prior_from_class_weights(
        class_weights: dict[str, float], asset_class: pd.Series, within_class: pd.Series | None = None
    ) -> pd.Series:
        """Build a prior portfolio from asset-class policy weights.

        ``class_weights`` e.g. {'Equity': 0.60, 'Fixed income': 0.35, 'Cash': 0.03,
        'Commodity': 0.02}; ``asset_class`` maps ticker -> class; ``within_class``
        (optional) splits each class across its ETFs (AUM by default equal).
        Classes absent from the universe are dropped and the rest renormalized.
        """
        ac = asset_class.astype(str)
        wc = pd.Series(1.0, index=ac.index) if within_class is None else pd.Series(within_class, dtype=float).reindex(ac.index).fillna(0.0)
        out = pd.Series(0.0, index=ac.index)
        for cls, cw in class_weights.items():
            members = ac.index[ac == cls]
            if len(members) == 0:
                continue
            inner = wc[members]
            inner = inner / inner.sum() if inner.sum() > 0 else pd.Series(1.0 / len(members), index=members)
            out[members] = cw * inner
        if out.sum() <= 0:
            raise ValueError("no class weights matched the universe")
        return out / out.sum()

    def asset_table(self) -> pd.DataFrame:
        """Per-ETF annualized inputs the education layer can show."""
        self._require_fit()
        vol = np.sqrt(np.diag(self.sigma.to_numpy()))
        return pd.DataFrame(
            {
                "prior_weight": self.prior_weights,
                "exp_excess_return": self.mu_excess,
                "exp_return": self.mu_excess + self.rf,
                "exp_vol": vol,
                "hist_ann_return": self.returns.mean() * MONTHS_PER_YEAR,
                "hist_ann_vol": self.returns.std(ddof=1) * np.sqrt(MONTHS_PER_YEAR),
            }
        )
