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
from dataclasses import asdict, dataclass, field
from functools import lru_cache

import numpy as np
import pandas as pd

from optimizer import RoboKitOptimizer

from . import __version__, cma
from . import profile as prof
from .config import DATA_DIR, DELTA
from .data.prices import monthly_returns, to_cad, to_usd
from .explain import explain_portfolio
from .history import backfill_by_regression, backfill_regressors, proxies_for, splice
from .projection import project
from .shelf import PRIOR, build_shelf, prior_share
from .stress import stress_test
from .views import bound_tilt, views_to_bl

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
    profile: str | None = None  # 'low' | 'mid' | 'high': the brief's presets (levels 2 / 3 / 4)
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


# ------------------------------------------------------------------ data
def data_source() -> str:
    return "local" if (DATA_DIR / "universe.pkl").exists() and (DATA_DIR / "close_monthly.pkl").exists() else "snapshot"


@lru_cache(maxsize=1)
def _load():
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
    _load.cache_clear()


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


def build_returns(market: str, shelf: pd.DataFrame, core: list[str], sats: list[str]) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Returns in the portfolio currency with young histories extended: (window, full, notes)."""
    U, R, fx, ctx = _load()
    fx_r = fx.pct_change()
    X = returns_in(market, core + sats)
    hedged = dict(zip(U.yahoo, U.hedged.astype(bool)))
    notes: dict[str, list] = {}
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
    return common_window(X), X, notes


def equity_vol(X: pd.DataFrame, shelf: pd.DataFrame) -> float:
    """Volatility of the stock part of the policy prior over the window: the 'stock market' yardstick."""
    eq = shelf[(shelf.asset_class == "Equity") & (shelf.prior > 0) & shelf.ticker.isin(X.columns)]
    if eq.empty:
        eq = shelf[(shelf.asset_class == "Equity") & shelf.ticker.isin(X.columns)]
    if eq.empty:
        return 0.15
    w = eq.groupby("ticker")["prior"].sum()
    w = w / w.sum() if w.sum() > 0 else pd.Series(1.0 / len(w), index=w.index)
    port = X[list(w.index)].to_numpy() @ w.to_numpy()
    return float(np.std(port, ddof=1) * np.sqrt(12))


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
def build_portfolio(req: Request | dict) -> dict:
    if isinstance(req, dict):
        req = Request(**req)
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
    if fixed and not any(t in tickers for t in fixed):
        why = "; ".join(n["en"] for n in notes) or "none of them is in the fund list"
        raise ValueError(f"None of the funds in your own weights can be used: {why}")

    X, X_full, history_notes = build_returns(req.market, shelf, core, ok_sats)
    if len(X) < MIN_WINDOW:
        raise ValueError(f"only {len(X)} common months of data; need {MIN_WINDOW}")
    eq_vol = equity_vol(X, shelf)
    lvl5, lvl10, tv, level_src = _level(req, eq_vol)

    prior = pd.Series(0.0, index=tickers)
    for _, row in shelf.iterrows():
        prior[row.ticker] += prior_share(req.market, row.sleeve)
    if prior.sum() <= 0:
        prior[:] = 1.0
    prior = prior / prior.sum()
    cash_t = shelf.loc[shelf.role == "cash", "ticker"]
    cash_t = cash_t.iloc[0] if len(cash_t) else None

    rf, rf_src = risk_free(req.market)
    opt = RoboKitOptimizer(
        X, rf=rf, prior_weights=prior, delta=DELTA, w_max=req.max_weight, cash_ticker=cash_t, cash_max=1.0, mu_method="equilibrium"
    ).fit()

    sat_cap = req.satellite_cap if req.satellite_cap is not None else prof.satellite_cap(lvl10)
    forced = {t: float(v) for t, v in (req.minimums or {}).items() if t in tickers}
    group = {"satellites": (ok_sats, 0.0, sat_cap)} if ok_sats else None
    caps = {row.ticker: min(SLEEVE_CAPS[row.sleeve], req.max_weight) for _, row in shelf.iterrows() if row.sleeve in SLEEVE_CAPS}
    for t in ok_sats:
        caps[t] = req.crypto_max_each if meta.at[t, "asset_class"] == "Crypto" else req.satellite_max_each
    if cash_t is not None and prof.cash_cap(lvl10) < 1.0:
        caps[cash_t] = prof.cash_cap(lvl10)

    def solve(o, lam, tick=None, resample=False, n_boot=0):
        return o.optimize(
            float(lam),
            tickers=tick or tickers,
            forced=forced,
            excluded=list(req.exclude or []),
            w_max=req.max_weight,
            group_bounds=group,
            resample=resample,
            n_boot=n_boot,
            seed=req.seed,
            caps=caps,
        )

    views_info, lam, band, dropped = None, None, None, []
    if fixed:  # the person's own weights: no optimisation, same report
        w = pd.Series({t: fixed.get(t, 0.0) for t in tickers}, dtype=float)
        w = w[w > 0] / w[w > 0].sum()
    else:
        lam, _, reach = _calibrate(lambda lam_: solve(opt, lam_), tv)
        if reach:
            notes.append(reach)
        res = solve(opt, lam, resample=req.resample, n_boot=req.n_boot)
        w, res, dropped = _drop_small(res, req, forced, lambda tick: solve(opt, lam, tick, req.resample, req.n_boot), tickers, notes)
        band = res.weight_band
        if cash_t is not None and float(w.get(cash_t, 0.0)) > 0.5:
            c = float(w[cash_t])
            notes.append(
                _note(
                    f"{c:.0%} sits in the cash-like ETF: at this risk aversion the model prefers safety over the small extra return of the other funds."
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
                w_bounded, tilt = bound_tilt(w.reindex(tickers).fillna(0.0), wv_raw, opt.sigma.loc[tickers, tickers].to_numpy())
                views_info = {"views": views_info, "tilt": tilt, "no_view_weights": {t: round(float(v), 4) for t, v in w.items() if v > 0}}
                w = w_bounded[w_bounded > 1e-6]
    w = w[w > 1e-6]
    w = w / w.sum()

    sig = opt.sigma.loc[w.index, w.index].to_numpy()
    wv = w.to_numpy()
    vol = float(np.sqrt(wv @ sig @ wv))
    model_ret = rf + float(opt.mu_excess.loc[w.index].to_numpy() @ wv)
    rc = wv * (sig @ wv) / (vol**2) if vol > 0 else wv * 0
    if fixed:  # the level these weights behave like: their volatility as a share of the stock market's
        lvl10 = max(2.0, min(10.0, 10.0 * vol / eq_vol))  # levels run 1-5; almost-all-cash weights read as level 1
        lvl5, tv, level_src = lvl10 / 2, None, "your own weights"

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
    plan_ret = proj["median_annual_return"]

    lvl_i = int(round(lvl5))
    out = {
        "market": req.market,
        "currency": home,
        "as_of": str(R.index.max().date()),
        "window": {"start": str(X.index.min().date()), "end": str(X.index.max().date()), "months": int(len(X))},
        "mode": "own_weights" if fixed else "optimized",
        "risk": {
            "level": round(lvl5, 1),
            "label": prof.LEVELS[lvl_i],
            "engine_level": round(lvl10, 1),
            "risk_share": None if fixed else round(prof.risk_share(lvl10), 4),
            "stock_market_vol": round(eq_vol, 4),
            "target_vol": None if tv is None else round(tv, 4),
            "achieved_vol": round(vol, 4),
            "lambda": None if lam is None else round(float(lam), 4),
            "source": level_src,
            "chosen_level": req.risk_level,
            "cash_cap": prof.cash_cap(lvl10),
            "satellite_cap": sat_cap,
        },
        "holdings": holdings,
        "stats": {
            "volatility": round(vol, 4),
            "volatility_long": round(vol_long, 4),
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
            "expected_returns_for_weights": opt.mu_info.get("method"),
            "delta": opt.delta,
            "covariance": opt.cov_info.get("method"),
            "shrinkage": opt.cov_info.get("shrinkage"),
            "resampled": bool(req.resample and not fixed),
            "n_boot": req.n_boot if (req.resample and not fixed) else 0,
            "prior": {t: round(float(v), 4) for t, v in prior.items() if v > 0},
            "sleeve_caps": {t: c for t, c in caps.items()},
        },
        "shelf": [
            {"sleeve": r.sleeve, "label": r.label, "ticker": r.ticker, "fund": r.fund, "alternatives": r.alternatives}
            for _, r in shelf.iterrows()
        ],
        "notes": notes,
        "record": {"engine_version": __version__, "data_snapshot": snapshot_id(), "request": asdict(req)},
    }
    out["explanation"] = explain_portfolio(out)
    return out


def _drop_small(res, req: Request, forced: dict, resolve, tickers: list[str], notes: list[dict]):
    """Remove positions under ``min_weight`` and re-solve, until none is left (a re-solve can
    create new small ones); anything still under the line after three rounds is set to zero.
    Returns (weights, last result, dropped tickers)."""
    w = res.weights.reindex(tickers).fillna(0.0)
    if req.min_weight <= 0:
        return w, res, []
    keep, dropped = list(tickers), []
    for _ in range(3):
        small = [t for t in keep if 0 < w[t] < req.min_weight and t not in forced]
        if not small:
            break
        dropped += small
        keep = [t for t in keep if t not in small]
        res = resolve(keep)
        w = res.weights.reindex(tickers).fillna(0.0)
    rest = [t for t in keep if 0 < w[t] < req.min_weight and t not in forced]
    if rest:
        dropped += rest
        w[rest] = 0.0
        w = w / w.sum()
    if dropped:
        n = len(dropped)
        notes.append(
            _note(
                f"Dropped because {'each' if n > 1 else 'it'} would have held less than {req.min_weight:.0%}: "
                + ", ".join(dropped)
                + ". The other funds were re-optimised."
            )
        )
    return w, res, dropped


def _calibrate(solve, target: float) -> tuple[float, float, dict | None]:
    """Bisection on log(lambda): volatility falls as lambda rises."""
    lo, hi = 0.05, 2000.0
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
