"""Portfolio construction: what the model does with the funds a person chose.

Pipeline (each step deterministic and reported back):

1. Funds: the reference shelf (the lowest-cost broad fund per asset class,
   ``robokit.shelf``) with any swaps the user made, plus the user's own picks
   as satellites. In the product the user confirms or edits this list; the
   engine never adds a fund on its own.
2. Data: monthly total returns over the longest common window (up to 15
   years). Young core funds are extended with a disclosed long-lived proxy;
   young satellites are back-filled by regression (``robokit.history``). A
   US-listed fund in a Canadian portfolio is converted to Canadian dollars.
3. Estimates: shrunk covariance and equilibrium expected returns anchored on
   the written policy prior (docs/METHOD.md); optional Black-Litterman views
   with Idzorek-style 0-100% confidence, bounded by a tracking-error budget.
4. Risk: the chosen level (1-5) sets a share of the stock market's
   volatility; the risk-aversion parameter is found by bisection to hit it.
5. Weights: constrained mean-variance with guardrails (cap per fund, per
   sleeve, cash cap and satellite cap by level), averaged over resampled
   histories, then tiny positions removed.
6. Report: weights with bands, volatility, planning-assumption returns after
   fees, fees in dollars, risk shares, asset mix, stress tests, projections,
   suitability-style checks, plain-language explanation and a reproducibility
   record (engine version, data snapshot, parameters).
"""

from __future__ import annotations

import hashlib
import json
import math
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, fields, replace
from functools import lru_cache

import numpy as np
import pandas as pd

from optimizer import RoboKitOptimizer

from . import __version__, cma
from . import profile as prof
from .config import DATA_DIR, DELTA
from .data.prices import monthly_returns, to_cad, to_usd
from .errors import InfeasibleConstraints, RoboKitInputError
from .explain import explain_portfolio
from .history import backfill_by_regression, backfill_regressors, proxies_for, splice
from .projection import project
from .shelf import PRIOR, build_shelf, prior_share
from .stress import stress_test
from .views import bound_tilt_clean, views_to_bl

MAX_WINDOW = 180
MIN_WINDOW = 36

# Guardrails a human advisor would also apply: narrow or volatile sleeves cannot
# dominate a portfolio just because their equilibrium return is high.
SLEEVE_CAPS = {
    "ca_reit": 0.10,
    "us_reit": 0.10,
    "ca_gold": 0.10,
    "us_gold": 0.10,
    "ca_em_equity": 0.15,
    "us_em_equity": 0.15,
    "ca_high_yield": 0.10,
    "us_high_yield": 0.10,
    "us_small_cap": 0.15,
    "ca_long_bond": 0.25,
    "us_long_treasury": 0.25,
    "ca_real_return": 0.20,
    "us_tips": 0.20,
}


@dataclass
class Request:
    market: str = "CA"
    risk_level: float | None = None  # 1..5 (Conservative .. Aggressive growth)
    target_vol: float | None = None
    profile: str | None = (
        None  # risk appetite 'low' | 'mid' | 'high' = levels 2 / 3 / 4 (or 'high_aversion' | 'mid_aversion' | 'low_aversion')
    )
    prefer_esg: bool = False
    hedge_us_equity: bool = False
    sleeves: list[str] | None = None
    swaps: dict[str, str] = field(default_factory=dict)
    satellites: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    minimums: dict[str, float] = field(default_factory=dict)
    max_weight: float = 0.50
    satellite_cap: float | None = None
    satellite_max_each: float = 0.10
    crypto_max_each: float = 0.05
    min_weight: float = 0.02
    views: list[dict] = field(default_factory=list)
    resample: bool = True
    n_boot: int = 200
    seed: int = 0
    amount: float = 10_000.0
    monthly_contribution: float = 0.0
    years: int = 10
    goal: float | None = None
    fixed_weights: dict[str, float] | None = None  # the person's own weights (no optimisation)
    level_chosen: bool = True  # False when risk_level is an untouched default ("the reference level" in checks)
    on_infeasible: str = "refuse"  # 'refuse': limits that cannot all hold stop the build; 'relax': relax them and say so
    # opt-in suitability (off by default; the level policy is unchanged): with the profile answers, a level above the
    # suggestion is built at the suggestion unless the person confirms the extra risk (31-103CP s.13.2: the lower of
    # willingness and ability to take risk)
    answers: dict | None = None
    enforce_suitability: bool = False
    acknowledged_above_suggestion: bool = False


MARKETS = ("CA", "US")


def _finite(v, name: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float, str, np.integer, np.floating)):
        raise RoboKitInputError(f"{name} must be a number, not {v!r}.", {"field": name})
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise RoboKitInputError(f"{name} must be a number, not {v!r}.", {"field": name}) from None
    if not math.isfinite(x):
        raise RoboKitInputError(f"{name} must be a finite number, not {v!r}.", {"field": name})
    return x


def _share(v, name: str, lo: float = 0.0, hi: float = 1.0, lo_open: bool = False) -> float:
    x = _finite(v, name)
    if x < lo or x > hi or (lo_open and x <= lo):
        rng = f"{'above' if lo_open else 'at least'} {lo:g} and at most {hi:g}"
        raise RoboKitInputError(f"{name} must be {rng}; got {x:g}.", {"field": name, "value": x})
    return x


def validate_request(req: Request | dict) -> Request:
    """Check every field before anything is built; raise ``RoboKitInputError`` with a plain message.

    Nothing is silently clamped: a level of 7 or NaN is an error, not level 5."""
    if isinstance(req, dict):
        known = {f.name for f in fields(Request)}
        unknown = sorted(set(req) - known)
        if unknown:
            raise RoboKitInputError(f"Unknown request field(s): {', '.join(unknown)}.", {"fields": unknown})
        req = Request(**req)
    else:
        req = replace(req)  # never change the caller's object
    market = str(req.market).upper() if isinstance(req.market, str) else req.market
    if market not in MARKETS:
        raise RoboKitInputError(f"market must be one of {', '.join(MARKETS)}; got {req.market!r}.", {"field": "market"})
    req.market = market
    if req.risk_level is not None:
        req.risk_level = _finite(req.risk_level, "risk_level")
        if not 1.0 <= req.risk_level <= 5.0:
            raise RoboKitInputError(f"risk_level must be between 1 and 5; got {req.risk_level:g}.", {"field": "risk_level"})
    if req.target_vol is not None:
        req.target_vol = _share(req.target_vol, "target_vol", 0.0, 1.0, lo_open=True)
    if req.profile is not None and req.profile not in prof.PRESETS:
        raise RoboKitInputError(f"profile must be one of {', '.join(prof.PRESETS)}; got {req.profile!r}.", {"field": "profile"})
    req.amount = _finite(req.amount, "amount")
    if req.amount <= 0:
        raise RoboKitInputError("amount must be above 0.", {"field": "amount"})
    req.monthly_contribution = 0.0 if req.monthly_contribution is None else _finite(req.monthly_contribution, "monthly_contribution")
    y = _finite(req.years, "years")
    if y != int(y) or not 1 <= y <= 100:
        raise RoboKitInputError(f"years must be a whole number from 1 to 100; got {req.years!r}.", {"field": "years"})
    req.years = int(y)
    if req.goal is not None:
        req.goal = _finite(req.goal, "goal")
        if req.goal <= 0:  # a goal of 0 means "no goal"
            req.goal = None
    req.max_weight = _share(req.max_weight, "max_weight", 0.0, 1.0, lo_open=True)
    if req.satellite_cap is not None:
        req.satellite_cap = _share(req.satellite_cap, "satellite_cap")
    req.satellite_max_each = _share(req.satellite_max_each, "satellite_max_each")
    req.crypto_max_each = _share(req.crypto_max_each, "crypto_max_each")
    req.min_weight = _share(req.min_weight, "min_weight", 0.0, 0.25)
    nb = _finite(req.n_boot, "n_boot")
    if nb != int(nb) or not 0 <= nb <= 5000:
        raise RoboKitInputError(f"n_boot must be a whole number from 0 to 5000; got {req.n_boot!r}.", {"field": "n_boot"})
    req.n_boot = int(nb)
    sd = _finite(req.seed, "seed")
    if sd != int(sd):
        raise RoboKitInputError("seed must be a whole number.", {"field": "seed"})
    req.seed = int(sd)
    for name in ("satellites", "exclude"):
        v = getattr(req, name) or []
        if not isinstance(v, (list, tuple)) or not all(isinstance(t, str) for t in v):
            raise RoboKitInputError(f"{name} must be a list of tickers.", {"field": name})
        setattr(req, name, list(v))
    if not isinstance(req.swaps or {}, dict):
        raise RoboKitInputError("swaps must map a slot to a ticker.", {"field": "swaps"})
    for k in ("minimums", "fixed_weights"):
        if getattr(req, k) is not None and not isinstance(getattr(req, k), dict):
            raise RoboKitInputError(f"{k} must map tickers to shares.", {"field": k})
    mins = {t: _share(v, f"minimum for {t}") for t, v in (req.minimums or {}).items()}
    if sum(mins.values()) > 1 + 1e-9:
        raise RoboKitInputError(f"The minimums add up to {_pct(sum(mins.values()))}, more than 100%.", {"field": "minimums"})
    clash = sorted(t for t, v in mins.items() if v > 0 and t in req.exclude)
    if clash:
        raise RoboKitInputError(f"{', '.join(clash)} cannot be both excluded and given a minimum.", {"field": "minimums", "tickers": clash})
    req.minimums = mins
    if req.fixed_weights is not None:
        fw = {t: _finite(v, f"weight for {t}") for t, v in req.fixed_weights.items()}
        if any(v < 0 for v in fw.values()):
            raise RoboKitInputError("Your own weights cannot be negative.", {"field": "fixed_weights"})
        if fw and sum(fw.values()) <= 0:
            raise RoboKitInputError("Your own weights must add up to more than 0.", {"field": "fixed_weights"})
        req.fixed_weights = fw
    req.views = _valid_views(req.views)
    if req.on_infeasible not in ("refuse", "relax"):
        raise RoboKitInputError("on_infeasible must be 'refuse' or 'relax'.", {"field": "on_infeasible"})
    for k in ("enforce_suitability", "acknowledged_above_suggestion"):
        if not isinstance(getattr(req, k), bool):
            raise RoboKitInputError(f"{k} must be true or false.", {"field": k})
    if req.answers is not None and not isinstance(req.answers, dict):
        raise RoboKitInputError("answers must be an object of question ids and answers.", {"field": "answers"})
    return req


def _valid_views(views) -> list[dict]:
    """Each view checked and written in one shape (the same rule as web/robokit.js validateViews)."""
    if views is None:
        return []
    if not isinstance(views, list):
        raise RoboKitInputError("views must be a list.", {"field": "views"})
    out = []
    for k, v in enumerate(views, 1):
        if not isinstance(v, dict):
            raise RoboKitInputError(f"View {k} must be an object.", {"field": "views"})
        typ = v.get("type", "absolute")
        if typ not in ("absolute", "relative"):
            raise RoboKitInputError(f"View {k}: type must be 'absolute' or 'relative'.", {"field": "views"})
        c = v.get("confidence")
        c = 0.5 if c is None else _share(c, f"confidence of view {k}")
        if typ == "relative":
            if not isinstance(v.get("long"), str) or not isinstance(v.get("short"), str):
                raise RoboKitInputError(f"View {k}: a relative view names a 'long' and a 'short' fund.", {"field": "views"})
            out.append(
                {
                    "type": "relative",
                    "long": v["long"],
                    "short": v["short"],
                    "difference": _finite(v.get("difference"), f"difference of view {k}"),
                    "confidence": c,
                }
            )
        else:
            if not isinstance(v.get("ticker"), str):
                raise RoboKitInputError(f"View {k}: an absolute view names a 'ticker'.", {"field": "views"})
            out.append(
                {"type": "absolute", "ticker": v["ticker"], "return": _finite(v.get("return"), f"return of view {k}"), "confidence": c}
            )
    return out


def _round_half_up(x: float, nd: int = 0) -> float:
    """Round halves away from zero, guarded against binary representation (the same formula as web/robokit.js roundHalfUp)."""
    f = 10.0**nd
    v = math.floor(abs(float(x)) * f + 0.5 + 1e-9) / f
    return 0.0 if v == 0 else math.copysign(v, x)


def _pct(x: float, nd: int = 0) -> str:
    """A share as a percentage, rounded the same way in both engines (web/robokit.js pctTxt)."""
    return f"{_round_half_up(float(x) * 100.0, nd):.{nd}f}%"


def _pct_pair(a: float, b: float) -> tuple[str, str]:
    """Two shares as percentages with the fewest decimals (1 to 3) that tell them apart (web/robokit.js pctPair)."""
    for nd in (1, 2, 3):
        x, y = _pct(a, nd), _pct(b, nd)
        if x != y:
            return x, y
    return x, y


def level_label(lvl5: float) -> str:
    """Name of the nearest level, rounding halves up and staying within 1-5 (the same rule as web/robokit.js)."""
    return prof.LEVELS[min(5, max(1, int(math.floor(float(lvl5) + 0.5 + 1e-9))))]


# ------------------------------------------------------------------ data
def data_source() -> str:
    return "local" if (DATA_DIR / "universe.pkl").exists() and (DATA_DIR / "close_monthly.pkl").exists() else "snapshot"


_AS_OF: list = []  # active as-of dates (evaluation only; the product never sets one)


@contextmanager
def as_of(date, mode: str = "fixed"):
    """Build as if today were the end of ``date``'s month (evaluation only).

    mode 'strict': returns, exchange rates and interest rates stop there before anything is computed, so every
    estimate, stand-in and back-fill uses only what was known then; a fund with no history yet cannot be used (pair it
    with a point-in-time shelf and ``research={'stand_ins': False}``).
    mode 'fixed': today's funds keep their stand-in histories (chosen with today's data, a disclosed look-ahead), but
    the returns used for estimation, and the interest rate, stop at the as-of month.
    Fund metadata (the list, fees, sizes, eligibility) is today's in both modes."""
    if mode not in ("fixed", "strict"):
        raise ValueError("mode must be 'fixed' or 'strict'")
    _AS_OF.append((pd.Timestamp(date) + pd.offsets.MonthEnd(0), mode))
    try:
        yield
    finally:
        _AS_OF.pop()


def _load():
    U, R, fx, ctx = _load_all()
    if not _AS_OF:
        return U, R, fx, ctx
    d, mode = _AS_OF[-1]
    ctx_d = ctx.loc[:d] if len(ctx) else ctx
    return (U, R.loc[:d], fx.loc[:d], ctx_d) if mode == "strict" else (U, R, fx, ctx_d)


@lru_cache(maxsize=1)
def _load_all():
    if data_source() == "snapshot":  # fresh clone: run from the committed web snapshot (robokit/snapshot.py)
        from . import snapshot

        if not snapshot.available():
            raise FileNotFoundError("No data yet. Run `python -m robokit refresh` to download it (15-30 minutes).")
        return snapshot.load()
    U = pd.read_pickle(DATA_DIR / "universe.pkl")
    close = pd.read_pickle(DATA_DIR / "close_monthly.pkl")
    R = monthly_returns(close)
    fx = pd.read_pickle(DATA_DIR / "usdcad_monthly.pkl")
    ctx = pd.read_pickle(DATA_DIR / "context_monthly.pkl") if (DATA_DIR / "context_monthly.pkl").exists() else pd.DataFrame()
    return U, R, fx, ctx


def reload() -> None:
    """Drop cached data (after a data refresh)."""
    _load_all.cache_clear()


@lru_cache(maxsize=1)
def snapshot_id() -> str:
    """Short hash identifying the data snapshot (prices through date, universe size, returns checksum).

    In snapshot mode (a fresh clone) this is the id recorded in web/data/core.json when the snapshot was built, so
    the web page, the CLI and the MCP server report the same id for the same data."""
    if data_source() == "snapshot":
        from . import snapshot

        sid = snapshot.core().get("meta", {}).get("data_snapshot")
        if sid:
            return sid
    U, R, _, _ = _load()
    h = hashlib.sha256()
    h.update(str(R.index.max()).encode())
    h.update(str(R.shape).encode())
    h.update(str(len(U)).encode())
    h.update(np.nan_to_num(R.tail(12).to_numpy(), nan=0.0).round(8).tobytes())
    return h.hexdigest()[:12]


def risk_free(market: str) -> tuple[float, str]:
    """Latest 3-month bill yield: Bank of Canada (V80691344) or US 13-week bill (^IRX)."""
    _, _, _, ctx = _load()
    col, label = ("V80691344", "Canada 3-month T-bill, Bank of Canada") if market == "CA" else ("^IRX", "US 13-week T-bill, Yahoo ^IRX")
    if col in ctx:
        s = ctx[col].dropna()
        if len(s):
            return float(s.iloc[-1]) / 100.0, f"{label}, {s.index[-1]:%b %Y}"
    from .config import RISK_FREE

    return RISK_FREE[market], "fallback constant in robokit/config.py"


def us_rates() -> dict:
    _, _, _, ctx = _load()
    out = {}
    for key, col in (("bill", "^IRX"), ("note5", "^FVX")):
        if col in ctx and ctx[col].notna().any():
            out[key] = float(ctx[col].dropna().iloc[-1]) / 100.0
    return out


@lru_cache(maxsize=1)
def _currencies() -> dict:
    U = _load()[0]
    return dict(zip(U.yahoo, U.currency))


def currency_of(ticker: str) -> str:
    """Trading currency from the fund list (USD units on the TSX such as XUS-U.TO are USD); suffix as fallback."""
    c = _currencies().get(ticker)
    if isinstance(c, str) and c in ("CAD", "USD"):
        return c
    return "CAD" if str(ticker).endswith((".TO", ".NE")) else "USD"


def returns_in(market: str, tickers: list[str]) -> pd.DataFrame:
    """Monthly returns for ``tickers`` in the portfolio's currency, converted by each fund's trading currency."""
    U, R, fx, _ = _load()
    X = R.reindex(columns=tickers).copy()
    home = "CAD" if market == "CA" else "USD"
    foreign = [t for t in tickers if currency_of(t) != home]
    if foreign:
        X[foreign] = to_cad(X[foreign], fx) if home == "CAD" else to_usd(X[foreign], fx)
    return X


def common_window(X: pd.DataFrame, max_months: int = MAX_WINDOW) -> pd.DataFrame:
    return X.dropna(how="any").tail(max_months)


def build_returns(
    market: str, shelf: pd.DataFrame, core: list[str], sats: list[str], max_months: int = MAX_WINDOW, stand_ins: bool = True
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Returns in the portfolio currency with young histories extended: (window, full, notes)."""
    U, R, fx, ctx = _load()
    fx_r = fx.pct_change()
    X = returns_in(market, core + sats)
    hedged = dict(zip(U.yahoo, U.hedged.astype(bool)))
    notes: dict[str, list] = {}
    if not stand_ins:  # evaluation only: each fund's own history, nothing extended
        return common_window(X, max_months), X, notes
    for _, row in shelf.iterrows():
        t = row.ticker
        proxies = proxies_for(row.sleeve, hedged.get(t, False), lambda x: hedged.get(x, False))
        s, n = splice(X[t], proxies, R, fx_r if market == "CA" else fx_r * 0, ctx, is_cash=row.role == "cash")
        X[t] = s.reindex(X.index)
        used = [x for x in n if x.get("used")]
        if used:
            notes[t] = used
    # satellites are back-filled as far back as the core funds go, leaving out a core fund that starts years after the rest
    core_full = X[backfill_regressors(X[core])].dropna(how="any")
    for t in sats:
        s, info = backfill_by_regression(X[t], core_full)
        X[t] = s.reindex(X.index)
        if info:
            notes[t] = [info]
    return common_window(X, max_months), X, notes


def equity_vol(X: pd.DataFrame, shelf: pd.DataFrame) -> float | None:
    """Volatility of the stock part of the policy prior over the window: the 'stock market' yardstick.
    None when the list holds no equity fund (see ``market_vol``)."""
    eq = shelf[(shelf.asset_class == "Equity") & (shelf.prior > 0) & shelf.ticker.isin(X.columns)]
    if eq.empty:
        eq = shelf[(shelf.asset_class == "Equity") & shelf.ticker.isin(X.columns)]
    if eq.empty:
        return None
    w = eq.groupby("ticker")["prior"].sum()
    w = w / w.sum() if w.sum() > 0 else pd.Series(1.0 / len(w), index=w.index)
    port = X[list(w.index)].to_numpy() @ w.to_numpy()
    return float(np.std(port, ddof=1) * np.sqrt(12))


def market_vol(market: str, X: pd.DataFrame, shelf: pd.DataFrame, notes: list[dict]) -> float:
    """The stock-market yardstick for the level targets. A list without stock funds borrows the reference
    shelf's stock funds over the same months, and says so; it never falls back to a made-up number."""
    v = equity_vol(X, shelf)
    if v is not None:
        return v
    ref, _, _ = select_funds(Request(market=market))  # the default sleeves (web/robokit.js shelfFor(M, {}))
    ref_eq = ref[(ref.asset_class == "Equity") & (ref.prior > 0)]
    if ref_eq.empty:
        raise RoboKitInputError("No stock fund is available to measure the stock market's volatility.", {"kind": "no_equity"})
    _, full, _ = build_returns(market, ref_eq, list(dict.fromkeys(ref_eq.ticker)), [])
    Xr = full.reindex(X.index).dropna(how="any")
    if len(Xr) < MIN_WINDOW:
        raise RoboKitInputError("The stock funds' history is too short to measure the stock market's volatility.", {"kind": "no_equity"})
    v = equity_vol(Xr, ref_eq)
    notes.append(
        _note(
            f"This list holds no stock fund, so the level targets use the reference stock funds' volatility ({_pct(v, 1)} a year) over the same months."
        )
    )
    return v


def _level(req: Request, eq_vol: float) -> tuple[float, float, float, str]:
    """(level 1-5, engine level 1-10, target volatility, source)."""
    if req.target_vol is not None:
        tv = float(req.target_vol)
        lvl10 = max(1.0, min(10.0, 10.0 * tv / eq_vol))
        return lvl10 / 2, lvl10, tv, "target volatility given directly"
    if req.risk_level is not None:
        lvl5 = max(1.0, min(5.0, float(req.risk_level)))
        src = "risk level chosen"
    else:
        p = req.profile or "mid"
        lvl5 = float(prof.PRESETS.get(p, 3))
        src = f"preset '{p}'"
    lvl10 = prof.engine_level(lvl5)
    return lvl5, lvl10, prof.risk_share(lvl10) * eq_vol, src


def _note(en: str) -> dict:
    return {"en": en}


def _suitability(req: Request):
    """The scored profile when suitability checks are on (None when off). Missing or unready answers are refused."""
    if not req.enforce_suitability:
        return None
    if not req.answers:
        raise RoboKitInputError("With suitability checks on, the profile answers are needed.", {"field": "answers"})
    res = prof.score(req.answers)
    if res.status != "complete" or res.suggested_level is None:
        missing = list(res.missing or [])
        raise RoboKitInputError(
            "With suitability checks on, the profile must be complete first" + (": " + ", ".join(missing) if missing else "") + ".",
            {"field": "answers", "status": res.status, "missing": missing},
        )
    return res


def _suitable_level(req: Request, res, lvl5: float, notes: list, own_weights: bool = False) -> tuple[float, dict]:
    """The level to build at, and the record of the check. A level above the suggestion needs the person's confirmation:
    without it the mix is built at the suggestion (own weights, which cannot be moved, are refused instead)."""
    s = float(res.suggested_level)
    lv = f"{_round_half_up(lvl5, 1):g}"
    why = f"the lower of your capacity ({res.capacity}) and your tolerance ({res.tolerance})"
    rec = {
        "enforced": True,
        "suggested_level": int(s),
        "capacity": res.capacity,
        "tolerance": res.tolerance,
        "requested_level": round(float(lvl5), 2),
        "acknowledged": bool(req.acknowledged_above_suggestion),
    }
    if lvl5 <= s + 1e-9:
        rec["applied_level"] = round(float(lvl5), 2)
        return lvl5, rec
    if req.acknowledged_above_suggestion:
        notes.append(
            _note(
                f"You chose level {lv}, above the level {int(s)} your answers suggest ({why}). You confirmed you understand the extra risk; the confirmation is recorded."
            )
        )
        rec["applied_level"] = round(float(lvl5), 2)
        return lvl5, rec
    if own_weights:
        raise RoboKitInputError(
            f"Your own weights behave like level {lv}, above the level {int(s)} your answers suggest ({why}). "
            "With suitability checks on, confirm you understand the extra risk to keep them.",
            {"field": "fixed_weights", "suggested_level": int(s)},
        )
    notes.append(
        _note(
            f"Your answers suggest level {int(s)} ({why}). With suitability checks on, the mix is built at level {int(s)}, "
            f"not the level {lv} you chose. To build at level {lv}, confirm you understand the extra risk."
        )
    )
    rec["applied_level"] = s
    return s, rec


def select_funds(req: Request, notes: list[dict] | None = None) -> tuple[pd.DataFrame, list[str], list[str]]:
    """The shelf (with swaps) and the satellites: (shelf, core tickers, satellite tickers).

    A swap passes the same eligibility gate as a satellite; a refused or unknown swap
    keeps the reference fund and says why in ``notes``."""
    notes = [] if notes is None else notes
    U, _, _, _ = _load()
    shelf = build_shelf(U, req.market, prefer_esg=req.prefer_esg)
    default = [k for k, v in PRIOR[req.market].items() if v > 0] + [f"{req.market.lower()}_cash"]
    if req.market == "CA" and req.hedge_us_equity:
        default = [("ca_us_equity_hedged" if k == "ca_us_equity" else k) for k in default]
    keys = req.sleeves if req.sleeves is not None else default
    shelf = shelf[shelf.sleeve.isin(keys)].copy()
    meta = U.set_index("yahoo")
    for k, t in (req.swaps or {}).items():
        if k not in set(shelf.sleeve):
            notes.append(_note(f"There is no '{k}' slot in this mix, so the swap to {t} was ignored."))
            continue
        keep = shelf.loc[shelf.sleeve == k, "ticker"].iloc[0]
        if t not in meta.index:
            notes.append(_note(f"{t} is not in the fund list, so the slot keeps {keep}."))
        elif not bool(meta.at[t, "eligible"]):
            why = meta.at[t, "excluded_because"]
            notes.append(_note(f"{t} was not swapped in ({why}), so the slot keeps {keep}."))
        elif bool(meta.at[t, "satellite_only"]):  # crypto, thematic and other narrow funds: own picks only, with their caps
            notes.append(
                _note(
                    f"{t} can be held only as one of your own picks, not in place of a broad fund, so the slot keeps {keep}. Add it as an own pick instead."
                )
            )
        elif (meta.at[t, "asset_class"], meta.at[t, "region"]) != (meta.at[keep, "asset_class"], meta.at[keep, "region"]):
            notes.append(
                _note(
                    f"{t} ({meta.at[t, 'asset_class']}, {meta.at[t, 'region']}) does not hold what the slot holds "
                    f"({meta.at[keep, 'asset_class']}, {meta.at[keep, 'region']}), so the slot keeps {keep}. Add it as an own pick instead."
                )
            )
        else:
            shelf.loc[shelf.sleeve == k, ["ticker", "fund", "mer", "aum"]] = [t, meta.at[t, "name"], meta.at[t, "mer"], meta.at[t, "aum"]]
    shelf = shelf[shelf.ticker.notna() & ~shelf.ticker.isin(req.exclude)]
    core = list(dict.fromkeys(shelf.ticker))
    sats = [t for t in dict.fromkeys(req.satellites) if t not in core and t not in req.exclude]
    return shelf, core, sats


def _last_price(meta: pd.DataFrame, t: str, home: str) -> tuple[float | None, str | None]:
    """Last month-end close of ``t`` in the portfolio currency, and its date."""
    if "last_close" not in meta.columns or pd.isna(meta.at[t, "last_close"]):
        return None, None
    px = float(meta.at[t, "last_close"])
    c = currency_of(t)
    if c != home:
        _, _, fx, _ = _load()
        rate = float(fx.dropna().iloc[-1])  # CAD per USD
        px = px * rate if home == "CAD" else px / rate
    d = meta.at[t, "last_close_date"] if "last_close_date" in meta.columns else None
    return px, (None if d is None or pd.isna(d) else str(pd.Timestamp(d).date()))


# ------------------------------------------------------------------ main entry
RESEARCH_KEYS = {
    "cov_method",
    "mu_method",
    "sleeve_caps",
    "cash_caps",
    "calibrate",
    "prior",
    "block_length",
    "max_window",
    "stand_ins",
    "delta",
    "yardstick",
    "cap_scale",
    "lambda",
}


def build_portfolio(req: Request | dict, *, lean: bool = False, research: dict | None = None) -> dict:
    """The portfolio for a request. ``lean`` stops after the weights (no prices, crisis replays or projections) and
    ``research`` changes one component for an ablation or a sensitivity test; both are for the evaluation
    (scripts/run_v3_evaluation.py), never set by the product. research keys: cov_method ('auto' | 'lw_cc' | 'lw_id' |
    'qis' | 'sample'), mu_method ('equilibrium' | 'sample' | 'james_stein'), sleeve_caps (False drops the sleeve and
    cash caps, keeping the per-fund maximum), cash_caps (False drops only the cash cap), calibrate ('final' |
    'single'), prior ({sleeve: share}), block_length (months), max_window (months), stand_ins (False: each fund's own
    history only), delta (equilibrium risk aversion), yardstick ({sleeve: weight}: the stock-market mix whose
    volatility sets the level targets, in place of the policy-weighted equity slots), cap_scale (the sleeve caps
    multiplied by this factor, at most 1), lambda (the final pipeline at this risk aversion, not calibrated: re-checks
    the evidence a calibration reports)."""
    research = dict(research or {})
    if set(research) - RESEARCH_KEYS:
        raise RoboKitInputError(f"unknown research switches: {sorted(set(research) - RESEARCH_KEYS)}", {"field": "research"})
    if "lambda" in research and not (np.isfinite(float(research["lambda"])) and float(research["lambda"]) > 0):
        raise RoboKitInputError("research lambda must be a positive number", {"field": "research"})
    req = validate_request(req)
    U, R, fx, _ = _load()
    meta = U.set_index("yahoo")
    notes: list[dict] = []
    fixed = {t: float(v) for t, v in (req.fixed_weights or {}).items() if float(v) > 0}

    shelf, core, sats = select_funds(req, notes)
    for t in fixed:  # own weights: funds that are not on the shelf join as the person's own picks
        if t not in core and t not in sats and t not in req.exclude:
            sats.append(t)
    ref = build_shelf(U, req.market, prefer_esg=req.prefer_esg).set_index("sleeve")["ticker"]
    changed = any(ref.get(r.sleeve) != r.ticker for _, r in shelf.iterrows())
    home = "CAD" if req.market == "CA" else "USD"
    ok_sats = []
    for t in sats:
        if t not in meta.index:
            notes.append(_note(f"{t} is not in the fund list, so it was left out."))
        elif not bool(meta.at[t, "eligible"]):
            why = meta.at[t, "excluded_because"]
            notes.append(_note(f"{t} was left out: {why}."))
        else:
            ok_sats.append(t)
    names = {"CAD": "Canadian dollars", "USD": "US dollars"}
    for t in core + ok_sats:
        c = currency_of(t)
        if c != home:
            us = meta.at[t, "market"] == "US"
            notes.append(
                _note(
                    f"{t} trades in {names[c]} {'on a US exchange' if us else 'on a Canadian exchange'}; its returns are shown in {names[home]} and buying it means converting currency."
                )
            )
    tickers = core + ok_sats
    if not tickers:
        why = "; ".join(n["en"] for n in notes)
        raise RoboKitInputError(
            "No fund is left to build a portfolio from" + (f": {why}" if why else ": every fund was excluded."), {"kind": "no_funds"}
        )
    if fixed and not any(t in tickers for t in fixed):
        why = "; ".join(n["en"] for n in notes) or "none of them is in the fund list"
        raise RoboKitInputError(f"None of the funds in your own weights can be used: {why}", {"kind": "no_funds"})

    max_window = int(research.get("max_window", MAX_WINDOW))
    X, X_full, history_notes = build_returns(req.market, shelf, core, ok_sats, max_window, bool(research.get("stand_ins", True)))
    if _AS_OF and _AS_OF[-1][1] == "fixed":  # today's funds and stand-ins; only the months up to the as-of date
        X_full = X_full.loc[: _AS_OF[-1][0]]
        X = common_window(X_full, max_window)
    if len(X) < MIN_WINDOW:
        raise RoboKitInputError(
            f"These funds share only {len(X)} months of history; at least {MIN_WINDOW} are needed.",
            {"kind": "short_history", "months": int(len(X))},
        )
    eq_vol = market_vol(req.market, X, shelf, notes)
    if "yardstick" in research:  # evaluation only: another stock-market mix as the yardstick
        ys = {
            shelf.loc[shelf.sleeve == k, "ticker"].iloc[0]: float(v) for k, v in research["yardstick"].items() if (shelf.sleeve == k).any()
        }
        yw = np.array(list(ys.values())) / sum(ys.values())
        eq_vol = float(np.std(X[list(ys)].to_numpy() @ yw, ddof=1) * np.sqrt(12))
    lvl5, lvl10, tv, level_src = _level(req, eq_vol)
    suit = _suitability(req)
    suitability = None
    if suit is not None and not req.fixed_weights:
        applied, suitability = _suitable_level(req, suit, lvl5, notes)
        if applied != lvl5:
            lvl5, lvl10 = applied, prof.engine_level(applied)
            tv, level_src = prof.risk_share(lvl10) * eq_vol, "suggested level (suitability checks on)"

    prior = pd.Series(0.0, index=tickers)
    share = (lambda k: float(research["prior"].get(k, 0.0))) if "prior" in research else (lambda k: prior_share(req.market, k))
    for _, row in shelf.iterrows():
        prior[row.ticker] += share(row.sleeve)
    if prior.sum() <= 0:
        prior[:] = 1.0
    prior = prior / prior.sum()
    cash_t = shelf.loc[shelf.role == "cash", "ticker"]
    cash_t = cash_t.iloc[0] if len(cash_t) else None

    rf, rf_src = risk_free(req.market)
    opt = RoboKitOptimizer(
        X,
        rf=rf,
        prior_weights=prior,
        delta=float(research.get("delta", DELTA)),
        w_max=req.max_weight,
        cash_ticker=cash_t,
        cash_max=1.0,
        mu_method=research.get("mu_method", "equilibrium"),
        cov_method=research.get("cov_method", "auto"),
        block_length=research.get("block_length", 6),
    ).fit()

    sat_cap = req.satellite_cap if req.satellite_cap is not None else prof.satellite_cap(lvl10)
    forced = {t: float(v) for t, v in (req.minimums or {}).items() if t in tickers}
    group = {"satellites": (ok_sats, 0.0, sat_cap)} if ok_sats else None
    k_cap = float(research.get("cap_scale", 1.0))
    caps = {
        row.ticker: min(SLEEVE_CAPS[row.sleeve] * k_cap, 1.0, req.max_weight) for _, row in shelf.iterrows() if row.sleeve in SLEEVE_CAPS
    }
    for t in ok_sats:
        caps[t] = req.crypto_max_each if meta.at[t, "asset_class"] == "Crypto" else req.satellite_max_each
    if cash_t is not None and prof.cash_cap(lvl10) < 1.0:
        caps[cash_t] = prof.cash_cap(lvl10)
    if research.get("sleeve_caps", True) is False:  # ablation: only the per-fund maximum (and own-pick caps) remain
        caps = {t: c for t, c in caps.items() if t in ok_sats}
    if research.get("cash_caps", True) is False and cash_t is not None:  # ablation: no cash cap by level
        caps.pop(cash_t, None)
    # when the limits cannot all hold: refuse (default), or relax in this order and say so
    on_inf = "relax" if req.on_infeasible == "relax" else "raise"
    relax_order = [core, ok_sats]

    def solve(o, lam, tick=None, resample=False, n_boot=0, caps_=None, group_=None, mode=None):
        return o.optimize(
            float(lam),
            tickers=tick or tickers,
            forced=forced,
            excluded=list(req.exclude or []),
            w_max=req.max_weight if caps_ is None else 1.0,  # applied caps name every fund
            group_bounds=group if group_ is None else group_,
            resample=resample,
            n_boot=n_boot,
            seed=req.seed,
            caps=caps if caps_ is None else caps_,
            on_infeasible=on_inf if mode is None else mode,
            relax_order=relax_order,
        )

    views_info, lam, band, dropped, relaxations, views_applied, calibration = None, None, None, [], [], False, None
    if fixed:  # the person's own weights: no optimisation, same report
        w = pd.Series({t: fixed.get(t, 0.0) for t in tickers}, dtype=float)
        w = w[w > 0] / w[w > 0].sum()
    else:
        try:
            lam_point, _, _ = _calibrate(lambda lam_: solve(opt, lam_), tv)
        except InfeasibleConstraints as e:
            raise _plain_infeasible(e, sat_cap) from None
        # the limits as applied (relaxed ones included): smaller lists tried when dropping small positions must fit inside them
        _, ub_a, _ = opt._bounds(tickers, req.max_weight, forced, list(req.exclude or []), caps, on_inf, relax_order)
        caps_applied = {t: float(u) for t, u in zip(tickers, ub_a)}

        def final(lam_):
            """The mix the person gets at this lambda: resampled, then the minimum position applied. The bootstrap is
            seeded the same way on every call, so every lambda sees the same resampled histories."""
            res_ = solve(opt, lam_, resample=req.resample, n_boot=req.n_boot)
            rel_ = list(res_.relaxations)
            grp_ = group
            for r in rel_:
                if r["limit"] == "group" and group:
                    grp_ = {"satellites": (ok_sats, 0.0, r["applied"])}
            notes_ = []
            w_, res_, dropped_ = _drop_small(
                res_,
                req,
                forced,
                lambda tick: solve(opt, lam_, tick, req.resample, req.n_boot, caps_applied, grp_, "raise"),
                tickers,
                notes_,
            )
            return {
                "lam": float(lam_),
                "w": w_,
                "res": res_,
                "dropped": dropped_,
                "notes": notes_,
                "relaxations": rel_,
                "group": grp_,
                "vol": _mix_vol(w_, opt.sigma),
            }

        if "lambda" in research:  # research: the final pipeline at a given lambda, to re-check calibration evidence
            fin = final(float(research["lambda"]))
            calibration = {
                "method": "final pipeline at a given lambda (research)",
                "lambda_single_solve": round(lam_point, 4),
                "evaluations": 1,
                "outcome": "given lambda",
                "target_vol": round(tv, 6),
                "achieved_vol": round(fin["vol"], 6),
                "within_tolerance": bool(abs(fin["vol"] - tv) <= CAL_TOL),
                "evidence": None,
            }
        elif research.get("calibrate", "final") == "single":  # ablation: lambda from the single solve, as in v2
            fin = final(lam_point)
            calibration = {
                "method": "single solve (v2)",
                "lambda_single_solve": round(lam_point, 4),
                "evaluations": 1,
                "outcome": "single solve",
                "target_vol": round(tv, 6),
                "achieved_vol": round(fin["vol"], 6),
                "within_tolerance": bool(abs(fin["vol"] - tv) <= CAL_TOL),
                "evidence": None,
            }
        else:
            fin, calibration = _calibrate_final(final, tv, final(lam_point))
        lam, w, res, dropped, relaxations, group_applied = (
            fin["lam"],
            fin["w"],
            fin["res"],
            fin["dropped"],
            fin["relaxations"],
            fin["group"],
        )
        reach = _reach_note(tv, fin["vol"], calibration["outcome"])
        if reach:
            notes.append(reach)
        notes.extend(fin["notes"])
        band = res.weight_band
        if cash_t is not None and float(w.get(cash_t, 0.0)) > 0.5:
            c = float(w[cash_t])
            notes.append(
                _note(
                    f"{_pct(c)} sits in the cash-like ETF: at this risk aversion the model prefers safety over the small extra return of the other funds."
                )
            )
        # optional views: Black-Litterman on top, tilt bounded against the no-view weights
        if req.views:
            P, Q, omega, views_info = views_to_bl(req.views, tickers, opt)
            if P is not None:
                opt_v = RoboKitOptimizer(
                    X,
                    rf=rf,
                    prior_weights=prior,
                    delta=DELTA,
                    w_max=req.max_weight,
                    cash_ticker=cash_t,
                    cash_max=1.0,
                    mu_method="black_litterman",
                    views={"P": P, "Q": Q, "tau": 0.05, "omega": omega},
                ).fit()
                lam_v, _, _ = _calibrate(lambda lam_: solve(opt_v, lam_), tv)
                wv_raw = solve(opt_v, lam_v, resample=req.resample, n_boot=req.n_boot).weights.reindex(tickers).fillna(0.0)
                ub_applied = ub_a
                held = [t for t in w.index if w[t] > 0]
                w0 = w.reindex(tickers).fillna(0.0)
                gcap = group_applied["satellites"][2] if group_applied else None
                groups = [(ok_sats, max(gcap, float(w0.reindex(ok_sats).sum())))] if ok_sats else []
                # positions the no-view mix holds below the minimum on purpose (kept, or forced) are never dropped by the tilt
                protected = set(forced) | {t for t in tickers if 0 < w0[t] < req.min_weight - 1e-9}
                w_bounded, tilt = bound_tilt_clean(
                    w0,
                    wv_raw,
                    opt.sigma.loc[tickers, tickers].to_numpy(),
                    min_weight=req.min_weight,
                    protected=protected,
                    ub=pd.Series(ub_applied, index=tickers),
                    groups=groups,
                )
                if tilt["scale"] == 0:
                    notes.append(_note("Your view could not be applied within the limits, so the mix is the same as without it."))
                elif tilt["dropped_after_tilt"]:
                    one = len(tilt["dropped_after_tilt"]) == 1
                    notes.append(
                        _note(
                            f"After your view, {', '.join(tilt['dropped_after_tilt'])} would have held less than {_pct(req.min_weight)}, so "
                            + ("it was" if one else "they were")
                            + " left out and the view's effect was scaled to stay within its limits."
                        )
                    )
                views_info = {"views": views_info, "tilt": tilt, "no_view_weights": {t: round(float(w[t]), 4) for t in held}}
                views_applied = tilt["scale"] > 0
                w = w_bounded[w_bounded > 1e-6]
    w = w[w > 1e-6]
    w = w / w.sum()

    sig = opt.sigma.loc[w.index, w.index].to_numpy()
    wv = w.to_numpy()
    vol = float(np.sqrt(wv @ sig @ wv))
    if lean:  # the evaluation needs the weights and how they were reached, nothing shown to a person
        return {
            "weights": {t: float(v) for t, v in w.items()},
            "volatility": vol,
            "target_vol": tv,
            "lambda": lam,
            "calibration": calibration,
            "stock_market_vol": eq_vol,
            "covariance": opt.cov_info.get("method"),
            "window": {"start": str(X.index.min().date()), "end": str(X.index.max().date()), "months": int(len(X))},
            "returns": X,
            "band": None if band is None else {t: (float(band.at[t, "q05"]), float(band.at[t, "q95"])) for t in band.index},
            "relaxations": relaxations,
            "notes": notes,
        }
    model_ret = rf + float(opt.mu_excess.loc[w.index].to_numpy() @ wv)
    rc = wv * (sig @ wv) / (vol**2) if vol > 0 else wv * 0
    if fixed:  # the level these weights behave like: their volatility as a share of the stock market's
        lvl10 = max(2.0, min(10.0, 10.0 * vol / eq_vol))  # levels run 1-5; almost-all-cash weights read as level 1
        lvl5, tv, level_src = lvl10 / 2, None, "your own weights"
        if suit is not None:
            _, suitability = _suitable_level(req, suit, _round_half_up(lvl5, 1), notes, own_weights=True)

    for t in ok_sats:  # the person's own picks that end up with no weight: say so, never drop silently
        if t not in w.index and t not in dropped:
            if fixed:
                notes.append(_note(f"{t} has no weight in your own weights. Give it one to hold it."))
            else:
                notes.append(
                    _note(f"{t} is not held: at this level the optimizer gave it no weight. You can set a minimum to hold it anyway.")
                )

    # planning assumptions (for projections and the return figure users see)
    rates = us_rates()
    geo_net, plan_src = [], {}
    for t in w.index:
        m = meta.loc[t]
        a, src = cma.assumption(m["asset_class"], m["region"], req.market, rates)
        if a is None:  # no published assumption: use the model's equilibrium return, geometric-ised
            a = rf + float(opt.mu_excess[t]) - 0.5 * float(opt.sigma.at[t, t])
        fee = float(m["mer"]) if pd.notna(m["mer"]) else 0.0
        geo_net.append(a - fee)
        plan_src[t] = src

    holdings = []
    sleeve_of = {row.ticker: row for _, row in shelf.iterrows()}
    invested, priced = 0.0, True
    for i, t in enumerate(w.index):
        m = meta.loc[t]
        sv = sleeve_of.get(t)
        dollars = float(w[t]) * req.amount
        px, px_date = _last_price(meta, t, home)
        units = int(np.floor(dollars / px + 1e-9)) if px else None
        if units is None:
            priced = False
        else:
            invested += units * px
        holdings.append(
            {
                "ticker": t,
                "symbol": str(m["symbol"]),
                "name": str(m["name"]),
                "role": "cash" if t == cash_t else ("core" if t in core else "satellite"),
                "sleeve": None if sv is None else sv.sleeve,
                "sleeve_label": None if sv is None else sv.label,
                "plain": None if sv is None else sv.plain,
                "asset_class": m["asset_class"],
                "region": m["region"],
                "issuer": m["issuer"],
                "weight": round(float(w[t]), 4),
                "band": None
                if band is None or t not in band.index
                else [round(float(band.at[t, "q05"]), 4), round(float(band.at[t, "q95"]), 4)],
                "dollars": round(dollars, 2),
                "price": None if px is None else round(px, 4),
                "price_date": px_date,
                "units": units,
                "mer": None if pd.isna(m["mer"]) else float(m["mer"]),
                "planning_return_net": round(geo_net[i], 4),
                "planning_source": plan_src[t],
                "model_return": round(rf + float(opt.mu_excess[t]), 4),
                "volatility": round(float(np.sqrt(opt.sigma.at[t, t])), 4),
                "risk_share": round(float(rc[i]), 4),
                "history_months": int(m["history_months"]),
                "aum": None if pd.isna(m["aum"]) else float(m["aum"]),
                "dollar_volume": None if pd.isna(m["dollar_volume"]) else float(m["dollar_volume"]),
            }
        )
    holdings.sort(key=lambda h: -h["weight"])

    mer = np.array([meta.at[t, "mer"] if pd.notna(meta.at[t, "mer"]) else np.nan for t in w.index], dtype=float)
    known = ~np.isnan(mer)
    wmer = float(np.sum(mer[known] * wv[known])) if known.any() else None  # funds with no fee in the data add nothing (said in checks)
    mix_class, mix_region = {}, {}
    for h in holdings:
        mix_class[h["asset_class"]] = mix_class.get(h["asset_class"], 0) + h["weight"]
        mix_region[h["region"]] = mix_region.get(h["region"], 0) + h["weight"]

    full_all = returns_in(req.market, list(R.columns))  # stand-in peers in the portfolio currency too
    for t in w.index:  # portfolio funds: extended history in the portfolio currency
        full_all[t] = X_full[t].reindex(full_all.index)
    first = {t: (None if pd.isna(meta.at[t, "first_month"]) else str(pd.Timestamp(meta.at[t, "first_month"]).date())) for t in w.index}
    stress = stress_test(w, full_all, U, amount=req.amount, first_month=first)

    # projections resample the longest history every fund has (spliced and back-filled as disclosed),
    # so a bad year reflects 2008 as well as the 15-year estimation window (RESEARCH_LOG section 7)
    H = X_full[list(w.index)].dropna(how="any")
    proj = project(
        H.to_numpy(),
        wv,
        np.array(geo_net),
        amount=req.amount,
        monthly_contribution=req.monthly_contribution,
        years=req.years,
        goal=req.goal,
    )
    proj["history"] = {"start": str(H.index.min().date()), "end": str(H.index.max().date()), "months": int(len(H))}
    vol_long = float(np.std(H.to_numpy() @ wv, ddof=1) * np.sqrt(12))
    rating = ni81_102_rating(H.to_numpy() @ wv)
    plan_ret = proj["median_annual_return"]

    for r in relaxations:  # limits relaxed on request: say each one in plain words (never silently)
        what = f"The limit on {r['ticker']}" if r["limit"] == "cap" else "The limit on your own picks together"
        why = "to hold the minimum you set" if r.get("reason") == "minimum" else "so the funds can hold all the money"
        before, after = _pct_pair(r["requested"], r["applied"])
        notes.append(_note(f"{what} was raised from {before} to {after} {why}, as you asked."))
    out = {
        "market": req.market,
        "currency": home,
        "as_of": str(R.index.max().date()),
        "window": {"start": str(X.index.min().date()), "end": str(X.index.max().date()), "months": int(len(X))},
        "mode": "own_weights" if fixed else "optimized",
        "risk": {
            "level": _round_half_up(lvl5, 1),
            "label": level_label(_round_half_up(lvl5, 1)),
            "engine_level": round(lvl10, 1),
            "risk_share": None if fixed else round(prof.risk_share(lvl10), 4),
            "stock_market_vol": round(eq_vol, 4),
            "target_vol": None if tv is None else round(tv, 4),
            "achieved_vol": round(vol, 4),
            "lambda": None if lam is None else round(float(lam), 4),
            "calibration": calibration,
            "source": level_src,
            "chosen_level": req.risk_level,
            "cash_cap": prof.cash_cap(lvl10),
            "satellite_cap": sat_cap,
        },
        "holdings": holdings,
        "stats": {
            "volatility": round(vol, 4),
            "volatility_long": round(vol_long, 4),
            "ni81_102": rating,
            "planning_return": round(plan_ret, 4),
            "planning_source": "FP Canada 2026 planning assumptions, after fund fees"
            if req.market == "CA"
            else "FP Canada 2026 equity assumptions and today's US Treasury yields, after fund fees",
            "model_return": round(model_ret, 4),
            "risk_free": round(rf, 4),
            "risk_free_source": rf_src,
            "sharpe_model": round((model_ret - rf) / vol, 3) if vol > 0 else None,
            "weighted_mer": None if wmer is None else round(wmer, 5),
            "fee_per_year": None if wmer is None else round(wmer * req.amount, 2),
            "fee_per_10k": None if wmer is None else round(wmer * 10_000, 2),
            "fee_unknown": [str(meta.at[t, "symbol"]) for t in w.index if pd.isna(meta.at[t, "mer"])],
            "effective_holdings": round(float(1 / np.sum(wv**2)), 2),
            "n_holdings": int(len(w)),
            "invested": round(invested, 2) if priced else None,
            "cash_left": round(req.amount - invested, 2) if priced else None,
        },
        "mix": {
            "asset_class": {k: round(v, 4) for k, v in sorted(mix_class.items(), key=lambda kv: -kv[1])},
            "region": {k: round(v, 4) for k, v in sorted(mix_region.items(), key=lambda kv: -kv[1])},
        },
        "stress": stress,
        "projection": proj,
        "views": views_info,
        "history": history_notes,
        "checks": checks(
            w, holdings, X, req, changed, ok_sats, None if wmer is None else round(wmer, 5), plan_ret, fixed=bool(fixed), lvl5=lvl5, vol=vol
        ),
        "method": {
            "weights": "your own weights" if fixed else "constrained mean-variance",
            "expected_returns_for_weights": "black_litterman (bounded)" if views_applied else opt.mu_info.get("method"),
            "delta": opt.delta,
            "covariance": opt.cov_info.get("method"),
            "shrinkage": opt.cov_info.get("shrinkage"),
            "resampled": bool(req.resample and not fixed),
            "n_boot": req.n_boot if (req.resample and not fixed) else 0,
            "prior": {t: round(float(v), 4) for t, v in prior.items() if v > 0},
            "sleeve_caps": {t: c for t, c in caps.items()},
            "on_infeasible": req.on_infeasible,
            "relaxations": relaxations,
            "suitability": suitability,
        },
        "shelf": [
            {"sleeve": r.sleeve, "label": r.label, "ticker": r.ticker, "fund": r.fund, "alternatives": r.alternatives}
            for _, r in shelf.iterrows()
        ],
        "notes": notes,
        "record": {"engine_version": __version__, "data_snapshot": snapshot_id(), "request": asdict(req)},
    }
    if relaxations:
        out["checks"].append(
            {
                "id": "limits_relaxed",
                "level": "warn",
                "en": f"{len(relaxations)} limit(s) were relaxed so these funds could hold all the money; the notes list each one.",
            }
        )
    out["checks"].append(rating_check(rating))
    out["explanation"] = explain_portfolio(out)
    return out


def _plain_infeasible(e: InfeasibleConstraints, sat_cap: float) -> InfeasibleConstraints:
    """The optimizer's infeasibility, in words a person can act on."""
    d = dict(e.details)
    kind = d.get("kind")
    tip = " To build anyway, ask for the limits to be relaxed (on_infeasible='relax'); every relaxed limit is then listed."
    if kind == "caps":
        msg = (
            f"The limits on these funds add up to {_pct(d.get('capacity', 0), 1)}, so together they cannot hold all the money. "
            "Add a broad fund or the cash fund, or raise the largest weight allowed per fund."
        )
    elif kind == "group_cap" and d.get("needed", 0) <= d.get("group_minimums", 0) + 1e-12:
        msg = (
            f"The minimums you set on your own picks add up to {_pct(d.get('group_minimums', 0), 1)}, above the "
            f"{_pct(d.get('cap', sat_cap), 1)} your own picks may hold at this level. Lower a minimum."
        )
    elif kind == "group_cap":
        msg = (
            f"Your own picks may hold at most {_pct(d.get('cap', sat_cap), 1)} at this level, but the other funds' limits leave "
            f"{_pct(d.get('needed', 0), 1)} for them. Add a broad fund, or remove one of your own picks."
        )
    elif kind == "minimum_above_cap":
        msg = (
            f"You set a minimum of {_pct(d.get('minimum', 0), 1)} for {d.get('ticker')}, above its limit of "
            f"{_pct(d.get('cap', 0), 1)}. Lower the minimum."
        )
    elif kind in ("minimums", "group_minimums"):
        msg = "The minimums you set cannot all hold together with the limits. Lower a minimum."
    else:
        msg = str(e)
    return InfeasibleConstraints(msg + tip, d)


def _drop_small(res, req: Request, forced: dict, resolve, tickers: list[str], notes: list[dict]):
    """Remove positions under ``min_weight`` and re-solve, round after round, until none is left (a re-solve can
    create new small ones; each round removes at least one fund, so it ends). A drop that would leave nothing, or
    that the remaining funds' limits cannot hold, is not made: those small positions stay, with a note. Weights are
    never renormalised past a limit. Returns (weights, last result, dropped tickers)."""
    w = res.weights.reindex(tickers).fillna(0.0)
    if req.min_weight <= 0:
        return w, res, []
    line = req.min_weight - 1e-9  # a weight sitting at a cap equal to the minimum is not "small"
    keep, dropped, kept_small, all_small = list(tickers), [], [], False
    for _ in range(len(tickers)):
        small = [t for t in keep if 0 < w[t] < line and t not in forced]
        if not small:
            break
        trial = [t for t in keep if t not in small]
        if not any(w[t] > 0 for t in trial):  # every position is small: keep the list as it is
            kept_small, all_small = small, True
            break
        try:
            res_t = resolve(trial)
        except InfeasibleConstraints:  # the remaining funds' limits cannot hold 100%: keep these positions
            kept_small = small
            break
        dropped += small
        keep, res = trial, res_t
        w = res.weights.reindex(tickers).fillna(0.0)
    pct = _pct(req.min_weight)
    if all_small:
        notes.append(_note(f"Every position would be under {pct}, so the minimum position size was not applied."))
    elif kept_small:
        notes.append(_note(f"Kept under {pct} because the other funds' limits cannot hold the rest: " + ", ".join(kept_small) + "."))
    if dropped:
        n = len(dropped)
        notes.append(
            _note(
                f"Dropped because {'each' if n > 1 else 'it'} would have held less than {pct}: "
                + ", ".join(sorted(dropped, key=tickers.index))  # list order, not round order (a fund on the line may go a round later)
                + ". The other funds were re-optimised."
            )
        )
    return w, res, dropped


# ------------------------------------------------------------------ the regulator's risk rating (v3 Track C2)
# NI 81-102 Appendix F, Item 1 table and Item 2 formula: the standard deviation of the most recent 120 monthly returns,
# n - 1 in the denominator, times the square root of 12, placed in five bands ("0 to less than 6" is Low, and so on).
APPENDIX_F = ((0.06, "Low"), (0.11, "Low to medium"), (0.16, "Medium"), (0.20, "Medium to high"), (float("inf"), "High"))


def ni81_102_rating(monthly) -> dict:
    """The rating a fund with these monthly returns would show on its Fund Facts or ETF Facts. The mix is rebalanced
    monthly to its weights; months before a fund's own history use its disclosed stand-in, as Item 4(2) allows a
    reference index for the missing years. Item 1(2) lets a manager raise a rating, never lower it."""
    r = np.asarray(monthly, dtype=float)[-120:]
    sd = float(np.std(r, ddof=1) * np.sqrt(12))
    label = next(name for cut, name in APPENDIX_F if sd < cut)
    return {
        "std_10y": round(sd, 4),
        "rating": label,
        "months": int(len(r)),
        "appendix_f": bool(len(r) >= 120),  # the full 10 years Appendix F asks for; fewer is an estimate on what exists
        "method": "NI 81-102 Appendix F: standard deviation of the last 120 monthly returns (n - 1), times the square root of 12",
    }


def rating_check(rating: dict) -> dict:
    short = "" if rating["months"] >= 120 else f" It uses the {rating['months']} months available, not the full 10 years."
    return {
        "id": "regulator_rating",
        "level": "info",
        "en": f"On the scale funds use for their published risk rating (NI 81-102 Appendix F, 10-year standard deviation), "
        f"this mix would rate {rating['rating']} ({_pct(rating['std_10y'], 1)}).{short}",
    }


LAM_LO, LAM_HI = 0.05, 2000.0
CAL_TOL = 5e-5  # final-pipeline volatility within 0.005 percentage points of the target (5e-5 as a decimal)
CAL_MAX = 30  # final-pipeline evaluations at most (each one is a full resampled build); typical requests take 2-4
CAL_WIDTH = 1e-5  # a bracket narrower than this in log lambda (0.001% in lambda, about 1e-6 in volatility) isolates a jump


def _mix_vol(w: pd.Series, sigma: pd.DataFrame) -> float:
    """Volatility of the held mix (weights above 1e-6, renormalised) under the model covariance."""
    w = w[w > 1e-6]
    w = w / w.sum()
    s = sigma.loc[w.index, w.index].to_numpy()
    return float(np.sqrt(w.to_numpy() @ s @ w.to_numpy()))


def _calibrate_final(final, target: float, first: dict) -> tuple[dict, dict]:
    """Risk aversion for the mix the person gets, not for the single solve (Scherer 2002: averaging resampled
    portfolios and dropping small positions move the risk off the target the single solve was calibrated to).

    f(u) = log(vol / target) at u = log(lambda) falls as lambda rises, but the minimum position makes it jump where a
    fund enters or leaves, and caps can make it flat. So the search brackets first, then narrows:
    1. From the single-solve lambda, step towards the target (the first step assumes vol ~ 1/lambda; the step doubles
       while the target is not bracketed) until one evaluated mix is above the target and one below, or a bound of
       lambda is reached (the target is then out of reach).
    2. Inside the bracket, Illinois regula falsi (Dowell and Jarratt 1971); the midpoint replaces a point within 1% of
       either end, or any point when the bracket did not halve over the last four steps, so it halves at least every
       four steps (on the ten standard mixes this takes 23 evaluations in all, against 34 when checked every two).
    It stops within CAL_TOL of the target, when the bracket is narrower than CAL_WIDTH in log lambda (a jump: no mix in
    between), at a bound, or after CAL_MAX evaluations; the closest mix seen is kept. Every evaluation uses the same
    bootstrap draws, so f is a deterministic function of lambda. web/robokit.js calibrateFinal is the same algorithm.
    A stop short of the target carries its evidence, which tests/test_v3_calibration.py re-checks by rebuilding at the
    lambdas it names: for a jump, the last bracket (lambda and volatility at each end, one above the target and one
    below, closer than CAL_WIDTH in log lambda); out of reach, the bound of lambda and the volatility there."""
    lu, hu = float(np.log(LAM_LO)), float(np.log(LAM_HI))
    best, evals = first, 1

    def f_of(fx):
        return float(np.log(max(fx["vol"], 1e-12) / target))

    u, f = float(np.log(first["lam"])), f_of(first)
    a = fa = b = fb = None  # bracket: a has vol above target (f > 0), b below (f < 0), a < b
    va = vb = None  # the volatility at each end (fa and fb are scaled by the Illinois rule)
    last_vol = first["vol"]  # the volatility at u, the last lambda evaluated
    if f > 0:
        a, fa, va = u, f, first["vol"]
    elif f < 0:
        b, fb, vb = u, f, first["vol"]
    step, side, widths, outcome = max(abs(f), 0.05), 0, [], "limit"
    while True:
        if abs(best["vol"] - target) <= CAL_TOL:
            outcome = "within tolerance"
            break
        if evals >= CAL_MAX:
            break
        if a is None or b is None:  # 1. bracket
            nxt = min(hu, max(lu, u + (step if f > 0 else -step)))
            if nxt == u:
                outcome = "out of reach"
                break
            u, step = nxt, 2 * step
        else:  # 2. narrow
            width = b - a
            if width < CAL_WIDTH:
                outcome = "jump"
                break
            u = b - fb * (b - a) / (fb - fa)
            if not (a + 0.01 * width < u < b - 0.01 * width) or (len(widths) >= 4 and width > 0.5 * widths[-4]):
                u = 0.5 * (a + b)
            widths.append(width)
        cur = final(float(np.exp(u)))
        evals += 1
        f = f_of(cur)
        last_vol = cur["vol"]
        if abs(cur["vol"] - target) < abs(best["vol"] - target):
            best = cur
        if a is None or b is None:
            if f > 0 and (a is None or u > a):
                a, fa, va = u, f, cur["vol"]
            elif f < 0 and (b is None or u < b):
                b, fb, vb = u, f, cur["vol"]
        elif f > 0:  # Illinois: an end kept twice in a row has its value halved
            if side == 1:
                fb *= 0.5
            a, fa, va, side = u, f, cur["vol"], 1
        elif f < 0:
            if side == -1:
                fa *= 0.5
            b, fb, vb, side = u, f, cur["vol"], -1
    evidence = None
    if outcome == "out of reach":  # lambda at a bound and the mix there still on the far side of the target
        evidence = {"bound_lambda": float(np.exp(u)), "vol_at_bound": last_vol, "side": "above" if last_vol > target else "below"}
    elif a is not None and b is not None:  # the last bracket
        evidence = {
            "lambda_above": float(np.exp(a)),
            "vol_above": va,
            "lambda_below": float(np.exp(b)),
            "vol_below": vb,
            "log_width": b - a,
        }
    info = {
        "method": "final pipeline (resampled, minimum position applied): bracket, then Illinois regula falsi on log lambda",
        "lambda_single_solve": round(first["lam"], 4),
        "evaluations": evals,
        "outcome": outcome,
        "target_vol": round(target, 6),
        "achieved_vol": round(best["vol"], 6),
        "within_tolerance": bool(abs(best["vol"] - target) <= CAL_TOL),
        "evidence": evidence,
    }
    return best, info


def _reach_note(target: float, vol: float, outcome: str) -> dict | None:
    """Say so when the final mix is more than half a point from the level's target, and why (the calibration outcome)."""
    if outcome == "out of reach" and vol < target - 0.005:
        return _note(
            f"The funds on this list cannot reach the {target:.1%} volatility this level aims for; the riskiest mix they allow is {vol:.1%}."
        )
    if outcome == "out of reach" and vol > target + 0.005:
        return _note(
            f"Even the steadiest mix of these funds swings about {vol:.1%} a year, above the {target:.1%} this level aims for. "
            "Adding cash or short-term bonds would bring it down."
        )
    if abs(vol - target) > 0.005:
        return _note(
            f"This mix swings about {vol:.1%} a year against the {target:.1%} this level aims for: with the minimum position size, "
            "the risk moves in steps as funds enter or leave the mix."
        )
    return None


def _calibrate(solve, target: float) -> tuple[float, float, dict | None]:
    """Bisection on log(lambda): volatility falls as lambda rises."""
    lo, hi = LAM_LO, LAM_HI
    v_lo = solve(lo).exp_vol
    v_hi = solve(hi).exp_vol
    if target >= v_lo:
        msg = (
            _note(
                f"The funds on this list cannot reach the {target:.1%} volatility this level aims for; the riskiest mix they allow is {v_lo:.1%}."
            )
            if target > v_lo + 0.005
            else None
        )
        return lo, v_lo, msg
    if target <= v_hi:
        msg = (
            _note(
                f"Even the steadiest mix of these funds swings about {v_hi:.1%} a year, above the {target:.1%} this level aims for. "
                "Adding cash or short-term bonds would bring it down."
            )
            if target < v_hi - 0.005
            else None
        )
        return hi, v_hi, msg
    for _ in range(40):
        mid = float(np.sqrt(lo * hi))
        if solve(mid).exp_vol > target:
            lo = mid
        else:
            hi = mid
        if hi / lo < 1.002:
            break
    lam = float(np.sqrt(lo * hi))
    return lam, solve(lam).exp_vol, None


# ------------------------------------------------------------------ checks (suitability-style, R5)
def checks(
    w: pd.Series,
    holdings: list[dict],
    X: pd.DataFrame,
    req: Request,
    changed: bool,
    sats: list[str],
    wmer: float | None,
    plan_ret: float,
    fixed: bool = False,
    lvl5: float | None = None,
    vol: float | None = None,
) -> list[dict]:
    """Deterministic warnings shown next to the portfolio (docs/research/regulation.md R5)."""
    out = []
    ccy = "CAD" if req.market == "CA" else "USD"
    top = max(holdings, key=lambda h: h["weight"])
    out.append(
        {
            "id": "concentration",
            "level": "info" if top["weight"] <= 0.5 else "warn",
            "en": f"Largest single fund: {top['symbol']} at {top['weight']:.0%}.",
        }
    )
    C = X[w.index].corr()
    pairs = [(a, b, C.at[a, b]) for i, a in enumerate(w.index) for b in list(w.index)[i + 1 :] if C.at[a, b] > 0.97]
    for a, b, c in pairs:
        cs = "above 0.99" if c >= 0.995 else f"{c:.2f}"
        sym = {h["ticker"]: h["symbol"] for h in holdings}
        a, b = sym.get(a, a), sym.get(b, b)
        out.append(
            {
                "id": "near_duplicate",
                "level": "warn",
                "en": f"{a} and {b} moved almost identically (correlation {cs}); holding both adds little diversification.",
            }
        )
    for h in holdings:
        if h["dollar_volume"] is not None and h["dollar_volume"] < (100e3 if req.market == "CA" else 1e6):
            out.append(
                {
                    "id": "liquidity",
                    "level": "warn",
                    "en": f"{h['symbol']} trades about ${h['dollar_volume'] / 1e3:,.0f}K a day. Use limit orders; the bid-ask spread may be wide.",
                }
            )
    if wmer is not None:
        g = max(plan_ret, 0.0)
        for yrs in (10, 25):
            gross = req.amount * (1 + g + wmer) ** yrs
            net = req.amount * (1 + g) ** yrs
            wd = req.monthly_contribution < 0  # withdrawals shrink the balance, so this overstates the cost
            out.append(
                {
                    "id": f"fee_drag_{yrs}",
                    "level": "info",
                    "en": f"Over {yrs} years, fund fees of {wmer:.2%} a year would cost about ${gross - net:,.0f} {ccy} on ${req.amount:,.0f} {ccy} (at the planning return)."
                    + (" Withdrawals make the balance smaller, so the real cost is lower." if wd else ""),
                }
            )
    unknown = [h["symbol"] for h in holdings if h["mer"] is None]
    if unknown:
        out.append(
            {
                "id": "fee_unknown",
                "level": "info",
                "en": f"Fee not in the data for {', '.join(unknown)}; the fee figures leave it out, so the real total is a little higher.",
            }
        )
    for h in holdings:
        if h["role"] == "satellite" and h["asset_class"] in ("Crypto", "Alternative"):
            cap_en = f"It is {h['weight']:.0%} of your weights." if fixed else "It is capped at a small weight."
            out.append(
                {
                    "id": "complex_product",
                    "level": "warn",
                    "en": f"{h['symbol']} is a {h['asset_class'].lower()} fund: harder to understand and more likely to behave unexpectedly. {cap_en}",
                }
            )
    if fixed and lvl5 is not None:
        chosen = req.risk_level
        off = chosen is not None and abs(lvl5 - float(chosen)) >= 1
        out.append(
            {
                "id": "own_weights",
                "level": "warn" if off else "info",
                "en": f"Your own weights, not the model's: they swing like level {lvl5:.1f} (volatility {vol:.1%} a year)."
                + (
                    (
                        f" That is not level {chosen:g}, the level you chose."
                        if req.level_chosen
                        else f" That is not level {chosen:g}, the reference level."
                    )
                    if off
                    else ""
                ),
            }
        )
    if changed or sats:
        out.append(
            {
                "id": "reference",
                "level": "info",
                "en": "You changed the reference fund list. Compare with the reference mix at the same level to see what your changes cost or add.",
            }
        )
    return out


# ------------------------------------------------------------------ a one-fund version at a similar stock share
ONE_FUND = {  # asset-allocation ETFs and the stock share their names state
    "CA": [
        ("VEQT.TO", 1.0),
        ("XEQT.TO", 1.0),
        ("ZEQT.TO", 1.0),
        ("VGRO.TO", 0.8),
        ("XGRO.TO", 0.8),
        ("ZGRO.TO", 0.8),
        ("VBAL.TO", 0.6),
        ("XBAL.TO", 0.6),
        ("ZBAL.TO", 0.6),
        ("VCNS.TO", 0.4),
        ("XCNS.TO", 0.4),
        ("ZCON.TO", 0.4),
        ("VCIP.TO", 0.2),
        ("XINC.TO", 0.2),
    ],
    "US": [("AOA", 0.8), ("AOR", 0.6), ("AOM", 0.4), ("AOK", 0.3)],
}


def one_fund_choice(market: str, stock_share: float) -> tuple[str | None, float | None]:
    """The eligible asset-allocation ETF whose stated stock share is closest; the cheaper one on ties."""
    U = _load()[0].set_index("yahoo")
    best = None
    for t, s in ONE_FUND.get(market, []):
        if t not in U.index or not bool(U.at[t, "eligible"]):
            continue
        mer = U.at[t, "mer"] if pd.notna(U.at[t, "mer"]) else 1.0
        key = (round(abs(s - stock_share), 6), mer)
        if best is None or key < best[0]:
            best = (key, t, s)
    return (best[1], best[2]) if best else (None, None)


def one_fund(market: str, stock_share: float, amount: float = 10_000.0, monthly_contribution: float = 0.0, years: int = 10) -> dict | None:
    """The same report for a single asset-allocation ETF, on the same window: the do-nothing benchmark."""
    t, s = one_fund_choice(market, stock_share)
    if t is None:
        return None
    p = build_portfolio(
        Request(
            market=market, fixed_weights={t: 1.0}, amount=amount, monthly_contribution=monthly_contribution, years=years, resample=False
        )
    )
    h = p["holdings"][0]
    return {
        "ticker": t,
        "symbol": h["symbol"],
        "name": h["name"],
        "stated_stock_share": s,
        "mer": h["mer"],
        "volatility": p["stats"]["volatility"],
        "fee_per_year": p["stats"]["fee_per_year"],
        "one_year": p["projection"]["one_year"],
        "one_year_dollars": p["projection"].get("one_year_dollars"),
        "one_year_value": p["projection"].get("one_year_value"),
        "stress": [
            {
                "key": x["key"],
                "scenario": x["scenario"],
                "portfolio_return": x["portfolio_return"],
                "dollars": x["dollars"],
                "estimated": x["estimated"],
                "stand_ins": x["stand_ins"],
                "not_estimable": x["not_estimable"],
            }
            for x in p["stress"]
        ],
        "history": p["history"].get(t),
        "window": p["window"],
    }


# ------------------------------------------------------------------ buy-only contributions (web/robokit.js planContribution)
def plan_contribution(holdings: list[dict], new_money: float, current: dict | None = None) -> dict:
    """Split new money across the mix's funds so the holdings move toward the target weights without selling.

    Each fund first gets what it lacks at the new total (in proportion when the money is short); money left after every
    gap is closed goes by target weight. Units round down at the last close."""
    cash = max(0.0, float(new_money or 0))
    cur = {h["ticker"]: max(0.0, float((current or {}).get(h["ticker"]) or 0)) for h in holdings}
    held_now = sum(cur.values())
    total = held_now + cash
    gaps = [max(0.0, h["weight"] * total - cur[h["ticker"]]) for h in holdings]
    need = sum(gaps)
    buys = [(cash * g / need if need else 0.0) if need > cash else g + (cash - need) * h["weight"] for h, g in zip(holdings, gaps)]
    rows = []
    for h, b in zip(holdings, buys):
        after = cur[h["ticker"]] + b
        price = h.get("price")
        rows.append(
            {
                "ticker": h["ticker"],
                "symbol": h.get("symbol"),
                "target": h["weight"],
                "now": cur[h["ticker"]],
                "now_weight": cur[h["ticker"]] / held_now if held_now else None,
                "buy": round(b, 2),
                "units": int(round(b, 2) // price) if price else None,
                "price": price,
                "after_weight": after / total if total else None,
            }
        )

    def drift(key):
        return sum(abs((r[key] if r[key] is not None else r["target"]) - r["target"]) for r in rows) / 2

    return {
        "new_money": cash,
        "held_now": round(held_now, 2),
        "rows": rows,
        "gap_closed": need <= cash + 1e-9,
        "drift_before": round(drift("now_weight"), 4) if held_now else None,
        "drift_after": round(drift("after_weight"), 4),
        "rule": "buy-only: each fund gets what it lacks at the new total (in proportion when money is short), then the rest by target weight; nothing is sold",
    }


# ------------------------------------------------------------------ ladder (asset-class view for all levels)
def ladder(market: str, amount: float = 10_000.0, n_boot: int = 100) -> list[dict]:
    """Asset-class mixes of the reference portfolio at levels 1-5, side by side (Path A default view)."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cache = DATA_DIR / f"ladder_{market}_{data_source()}_{snapshot_id()}_{__version__}.json"
    if cache.exists():
        return json.loads(cache.read_text())
    rows = []
    for lvl in (1, 2, 3, 4, 5):
        p = build_portfolio(Request(market=market, risk_level=lvl, amount=amount, n_boot=n_boot, years=10))
        rows.append(
            {
                "level": lvl,
                "label": p["risk"]["label"],
                "mix": p["mix"]["asset_class"],
                "volatility": p["stats"]["volatility"],
                "planning_return": p["stats"]["planning_return"],
                "one_year": p["projection"]["one_year"],
                "ten_year": p["projection"]["final"],
                "worst_stress": min((s["portfolio_return"] for s in p["stress"] if s["portfolio_return"] is not None), default=None),
                "stress": [{"key": s["key"], "scenario": s["scenario"], "portfolio_return": s["portfolio_return"]} for s in p["stress"]],
                "holdings": [{"ticker": h["ticker"], "weight": h["weight"], "asset_class": h["asset_class"]} for h in p["holdings"]],
            }
        )
    cache.write_text(json.dumps(rows))
    return rows
