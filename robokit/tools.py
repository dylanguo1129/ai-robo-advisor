"""The tool contract: every number the assistant may say comes from one of these.

The same tools, with the same names and inputs, are exposed by the MCP server
(``robokit.mcp_server``), the API-key command-line agent (``robokit.agent``)
and, mirrored in JavaScript, the web page (``web/robokit.js``). Each result is
plain JSON with a ``source`` and an ``as_of`` wherever data is involved.

All tools are read-only. None places orders, links accounts or stores
personal data.
"""

from __future__ import annotations

import json
import math
from typing import Any

import numpy as np
import pandas as pd

from . import __version__, glossary
from . import profile as prof
from .engine import Request, _load, build_portfolio, ladder, snapshot_id
from .errors import InfeasibleConstraints, RoboKitInputError, SolverNotConverged
from .shelf import PRIOR, candidates, sleeves_for
from .signals import market_flags, news_digest, trend_state

DISCLOSURE = {
    "en": (
        "Robo-Kit is an educational tool, not a registered advisor or dealer in Canada or the US. It does not know your full "
        "situation and does not tell you what to buy. Figures come from Robo-Kit's code and public data; results are hypothetical "
        "and not guarantees. You make your own decisions."
    ),
}


def _clean(o: Any) -> Any:
    """JSON-safe: NaN -> None, numpy -> python, timestamps -> ISO strings."""
    if isinstance(o, dict):
        return {str(k): _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        f = float(o)
        return None if not math.isfinite(f) else f
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    return o


def _row(r: pd.Series) -> dict:
    return {
        "ticker": r["yahoo"],
        "symbol": r["symbol"],
        "name": r["name"],
        "market": r["market"],
        "exchange": r["exchange"],
        "currency": r["currency"],
        "asset_class": r["asset_class"],
        "region": r["region"],
        "theme": r["theme"],
        "strategy": r["strategy"],
        "hedged": bool(r["hedged"]),
        "leverage": float(r["leverage"]),
        "issuer": r["issuer"],
        "mer": None if pd.isna(r["mer"]) else float(r["mer"]),
        "aum": None if pd.isna(r["aum"]) else float(r["aum"]),
        "history_months": int(r["history_months"]),
        "vol_3y": None if pd.isna(r["vol_3y"]) else float(r["vol_3y"]),
        "ret_1y": None if pd.isna(r["ret_1y"]) else float(r["ret_1y"]),
        "ret_5y": None if pd.isna(r["ret_5y"]) else float(r["ret_5y"]),
        "max_drawdown": None if pd.isna(r["max_drawdown"]) else float(r["max_drawdown"]),
        "dividend_yield": None if pd.isna(r["dividend_yield"]) else float(r["dividend_yield"]),
        "eligible": bool(r["eligible"]),
        "excluded_because": r["excluded_because"] or None,
        "satellite_only": bool(r["satellite_only"]),
        "esg": bool(r["esg"]),
    }


def _as_of() -> str:
    _, R, _, _ = _load()
    return str(R.index.max().date())


SOURCE = "Listings: Nasdaq Trader, TMX Money, Yahoo Finance. Prices: Yahoo Finance adjusted closes (total return). Classification: Robo-Kit rules."


# ------------------------------------------------------------------ tools
def get_questions() -> dict:
    """The fixed self-check questions, in order, with their answer options."""
    items = []
    for it in prof.ITEMS:
        items.append(
            {
                "id": it["id"],
                "block": it["block"],
                "kind": it["kind"],
                "text": it["text"],
                "options": [{"value": o["value"], "text": o["text"]} for o in it["options"]],
                "scenario": it.get("scenario"),
                "skip_if": it.get("skip_if"),
                "optional": bool(it.get("optional")),
            }
        )
    return {
        "items": items,
        "note": "Ask these with the exact wording, one at a time. You may explain a question, but not reword or score it. "
        "Skip an item when its skip_if matches an earlier answer (B2 is not asked when the goal is building wealth). "
        "Items marked optional (the two knowledge checks) come after the result, only if the person wants them.",
        "levels": {k: {"en": v} for k, v in prof.LEVELS.items()},
    }


def score_profile(answers: dict) -> dict:
    """Score the self-check answers -> suggested level (the lower of capacity and tolerance), gates and flags."""
    return _clean(prof.score(answers).to_dict())


def scenario_cards(market: str = "CA", amount: float = 10_000.0) -> dict:
    """Dollar outcomes for the tolerance questions: one-year and ten-year ranges at levels 1-5, and the sharp-drop amount."""
    rows = ladder(market, amount=10_000.0)
    k = amount / 10_000.0
    cards = []
    for r in rows:
        oy, ty = r["one_year"], r["ten_year"]
        cards.append(
            {
                "level": r["level"],
                "label": r["label"],
                "one_year_low": round(amount * (1 + oy["p10"]), 0),
                "one_year_high": round(amount * (1 + oy["p90"]), 0),
                "ten_year_low": round(ty["p10"] * k, 0),
                "ten_year_high": round(ty["p90"] * k, 0),
            }
        )
    return {
        "market": market,
        "amount": amount,
        "cards": cards,
        "drop_scenario": {"amount": amount, "after": round(amount * 0.8, 0)},
        "note": "Ranges are the 10th to 90th percentiles of hypothetical outcomes for the reference mix at each level.",
        "as_of": _as_of(),
    }


def risk_ladder(market: str = "CA", amount: float = 10_000.0) -> dict:
    """Asset-class mixes of the reference portfolio at every level, side by side (the default, impersonal view)."""
    rows = ladder(market, amount=10_000.0)
    return _clean(
        {
            "market": market,
            "levels": rows,
            "as_of": _as_of(),
            "note": "Illustrations of what each risk level has meant, built from the lowest-cost broad funds. Not a recommendation.",
        }
    )


def search_etfs(
    query: str = "",
    market: str = "CA",
    asset_class: str | None = None,
    region: str | None = None,
    theme: str | None = None,
    max_mer: float | None = None,
    min_aum: float | None = None,
    min_history_months: int | None = None,
    eligible_only: bool = True,
    esg_only: bool = False,
    hedged: bool | None = None,
    sort_by: str = "mer",
    limit: int = 25,
) -> dict:
    """Filter the fund list with neutral criteria. Sort by 'mer', 'aum', 'history' or 'name' (never by 'fit')."""
    U, _, _, _ = _load()
    u = U[U.market == market]
    if eligible_only:
        u = u[u.eligible]
    if query:
        q = query.lower()
        u = u[
            u["name"].str.lower().str.contains(q, regex=False, na=False)
            | u["symbol"].str.lower().eq(q)
            | u["yahoo"].str.lower().eq(q)
            | u["theme"].str.lower().str.contains(q, regex=False, na=False)
        ]
    if asset_class:
        u = u[u.asset_class.str.lower() == asset_class.lower()]
    if region:
        u = u[u.region.str.lower() == region.lower()]
    if theme:
        u = u[u.theme.str.lower().str.contains(theme.lower(), regex=False, na=False)]
    if max_mer is not None:
        u = u[u.mer.notna() & (u.mer <= max_mer)]
    if min_aum is not None:
        u = u[u.aum.notna() & (u.aum >= min_aum)]
    if min_history_months is not None:
        u = u[u.history_months >= min_history_months]
    if esg_only:
        u = u[u.esg]
    if hedged is not None:
        u = u[u.hedged == hedged]
    key = {"mer": ("mer", True), "aum": ("aum", False), "history": ("history_months", False), "name": ("name", True)}.get(
        sort_by, ("mer", True)
    )
    u = u.sort_values(key[0], ascending=key[1], na_position="last")
    total = len(u)
    return _clean(
        {
            "market": market,
            "matches": total,
            "shown": min(limit, total),
            "sorted_by": sort_by,
            "results": [_row(r) for _, r in u.head(limit).iterrows()],
            "as_of": _as_of(),
            "source": SOURCE,
            "note": "Neutral filter over the whole fund list. Sorting is by the key you chose, not by suitability.",
        }
    )


def etf_profile(ticker: str) -> dict:
    """Everything Robo-Kit knows about one fund: facts, classification with reasons, history, trend, exclusion reason."""
    U, R, _, _ = _load()
    r, others = resolve_ticker(U, ticker)
    if r is None:
        return {
            "found": False,
            "ticker": ticker,
            "note": "Not in Robo-Kit's fund list. It may be delisted, not an ETF, or listed elsewhere.",
        }
    tr = trend_state(R, [r["yahoo"]])
    return _clean(
        {
            "found": True,
            **_row(r),
            "classification_notes": r["why"] or None,
            "yahoo_category": r.get("yahoo_category"),
            "tmx_style": r.get("tmx_style"),
            "trend": tr[0] if tr else None,
            "first_month": r.get("first_month"),
            "same_symbol_elsewhere": others or None,
            "as_of": _as_of(),
            "source": SOURCE,
        }
    )


def resolve_ticker(U: pd.DataFrame, ticker: str) -> tuple[pd.Series | None, list[str]]:
    """The fund a ticker names, exact match first: 'AGG' is the US fund, 'AGG.TO' the Canadian one.

    About 200 symbols exist on both sides of the border, so a bare symbol resolves in this
    order: exact Yahoo ticker, then the TSX listing, then Cboe Canada, then a symbol match.
    Returns (row, other listings with the same symbol)."""
    t = ticker.strip().upper()
    order = [t, t + ".TO", t.replace(".", "-") + ".TO", t + ".NE"]
    up = U.yahoo.str.upper()
    for c in order:
        m = U[up == c]
        if len(m):
            r = m.iloc[0]
            break
    else:
        m = U[U.symbol.str.upper().eq(t)]
        if m.empty:
            return None, []
        r = m.iloc[0]
    sym = str(r["symbol"]).upper()
    others = [y for y in U.loc[U.symbol.str.upper().eq(sym), "yahoo"] if y != r["yahoo"]]
    return r, others


def compare_etfs(tickers: list[str]) -> dict:
    """Side-by-side facts for up to 6 funds, plus how closely they moved together. No verdict."""
    U, R, _, _ = _load()
    rows, keys = [], []
    for t in tickers[:6]:
        p = etf_profile(t)
        if p.get("found"):
            rows.append(p)
            keys.append(p["ticker"])
    corr = None
    if len(keys) >= 2:
        C = R[keys].dropna().tail(60).corr()
        corr = {a: {b: round(float(C.at[a, b]), 3) for b in keys} for a in keys}
    return _clean(
        {
            "funds": rows,
            "correlation_60m": corr,
            "as_of": _as_of(),
            "note": "Facts only. Which fits depends on the rest of the portfolio and the person.",
        }
    )


def reference_shelf(market: str = "CA", prefer_esg: bool = False, sort_by: str = "cost") -> dict:
    """For each asset class: the lowest-cost broad funds that fit its written rule, with the rule and runners-up."""
    U, _, _, _ = _load()
    out = []
    for s in sleeves_for(market):
        c = candidates(U, s, prefer_esg=prefer_esg)
        if sort_by == "size":
            c = c.sort_values("aum", ascending=False)
        elif sort_by == "history":
            c = c.sort_values("history_months", ascending=False)
        out.append(
            {
                "sleeve": s.key,
                "label": s.label,
                "plain": s.plain,
                "asset_class": s.asset_class,
                "role": s.role,
                "in_reference_mix": s.key in PRIOR[market] or s.role == "cash",
                "rule": {"regions": list(s.regions), "name_must_match": s.include, "hedged": s.hedged},
                "funds": [_row(r) for _, r in c.head(5).iterrows()],
            }
        )
    return _clean(
        {
            "market": market,
            "sleeves": out,
            "as_of": _as_of(),
            "note": "Default order is the published score (low fee, large, liquid, long history). The user picks; nothing here is chosen for a person.",
        }
    )


def build_portfolio_tool(
    market: str = "CA",
    level: float = 3,
    swaps: dict | None = None,
    satellites: list | None = None,
    exclude: list | None = None,
    minimums: dict | None = None,
    prefer_esg: bool = False,
    hedge_us_equity: bool = False,
    max_weight: float = 0.5,
    views: list | None = None,
    amount: float = 10_000,
    monthly_contribution: float = 0,
    years: int = 10,
    goal: float | None = None,
    fixed_weights: dict | None = None,
    relax_limits: bool = False,
) -> dict:
    """What the model does with the chosen funds at the chosen level: weights, risk, fees, stress tests, projections, checks.
    ``fixed_weights`` ({ticker: share}) skips the optimizer and reports the person's own weights the same way.
    A negative ``monthly_contribution`` is a withdrawal; the projection then says how often the money lasted."""
    req = Request(
        market=market,
        risk_level=level,
        swaps=swaps or {},
        satellites=satellites or [],
        exclude=exclude or [],
        minimums=minimums or {},
        prefer_esg=prefer_esg,
        hedge_us_equity=hedge_us_equity,
        max_weight=max_weight,
        views=views or [],
        amount=amount,
        monthly_contribution=monthly_contribution,
        years=years,
        goal=goal,
        fixed_weights=fixed_weights or None,
        on_infeasible="relax" if relax_limits else "refuse",
    )
    p = build_portfolio(req)
    p.pop("history", None)
    p["disclosure"] = DISCLOSURE
    p["label"] = "What the model does with the funds you chose. Hypothetical; not a recommendation."
    return _clean(p)


def compare_one_fund(market: str = "CA", stock_share: float = 0.6, amount: float = 10_000, years: int = 10) -> dict:
    """The same report for a single asset-allocation ETF at a similar stock share, on the same window: the do-it-yourself benchmark."""
    from .engine import one_fund

    o = one_fund(market, stock_share, amount=amount, years=years)
    if o is None:
        return {"available": False, "note": "No eligible asset-allocation ETF in the fund list for this market."}
    return _clean(
        {
            "available": True,
            **o,
            "label": "A one-fund version at a similar stock share. Hypothetical; not a recommendation.",
            "as_of": _as_of(),
            "disclosure": DISCLOSURE,
        }
    )


def plan_contribution(holdings: list, new_money: float, current: dict | None = None) -> dict:
    """Buy-only split of new money across a mix's funds (holdings from build_portfolio: ticker, weight, price), moving
    toward the target weights without selling. current: {ticker: dollars held now}."""
    from .engine import plan_contribution as plan

    hs = [
        {"ticker": h["ticker"], "symbol": h.get("symbol", h["ticker"]), "weight": float(h["weight"]), "price": h.get("price")}
        for h in holdings
    ]
    if not hs or new_money is None or float(new_money) <= 0:
        return {"error": "need the mix holdings (from build_portfolio) and new_money above 0"}
    return _clean(
        {**plan(hs, float(new_money), current or {}), "label": "Hypothetical buy-only split; not an order.", "disclosure": DISCLOSURE}
    )


def market_context(market: str = "CA", include_news: bool = True) -> dict:
    """Risk flags (VIX, geopolitical risk, policy uncertainty, credit spreads, yield curves, FX) and a news digest. Context only."""
    out = {
        "flags": market_flags(),
        "note": "Context, not forecasts. None of these change the portfolio. High fear readings have historically come before higher, not lower, average returns.",
    }
    if include_news:
        out["news"] = news_digest()
    return _clean(out)


def explain_term(term: str) -> dict:
    """A fixed plain-language definition."""
    return glossary.define(term)


def backtest_summary(market: str = "CA", level: int = 3) -> dict:
    """The pre-registered walk-forward back-test at one level, after costs. Hypothetical."""
    from .config import OUTPUT_DIR

    p = OUTPUT_DIR / "backtest_v2_summary.json"
    if not p.exists():
        return {"available": False}
    s = json.loads(p.read_text())[market]
    return {
        "available": True,
        "market": market,
        "level": level,
        "label": "Hypothetical back-test",
        "stats": [r for r in s["stats"] if r["level"] == level],
        "subperiods": [r for r in s["subperiods"] if r["level"] == level],
        "paired": [r for r in s["paired"] if r["level"] == level],
        "method": "60-month rolling window, yearly re-estimation, monthly rebalancing, 10 bps trading cost, fees in fund returns",
        "caveats": "Funds chosen with today's information; young funds extended with proxies; no delisted funds. Not a track record.",
    }


def data_status() -> dict:
    """Where the data comes from, how fresh it is, and what may be redistributed."""
    from .config import DATA_DIR

    U, R, _, _ = _load()
    meta = json.loads((DATA_DIR / "context_meta.json").read_text()) if (DATA_DIR / "context_meta.json").exists() else {}
    from .engine import data_source

    return _clean(
        {
            "engine_version": __version__,
            "data_snapshot": snapshot_id(),
            "data_source": data_source(),
            "prices_through": _as_of(),
            "listings": int(len(U)),
            "eligible": int(U.eligible.sum()),
            "by_market": {
                m: {"listings": int((U.market == m).sum()), "eligible": int((U.eligible & (U.market == m)).sum())} for m in ("CA", "US")
            },
            "context": meta,
            "licensing": "Yahoo, TMX and Nasdaq data are for personal use; fetch them on your own machine. Bank of Canada, GDELT, GPR and EPU may be redistributed with attribution.",
        }
    )


TOOLS = {
    "get_questions": get_questions,
    "score_profile": score_profile,
    "scenario_cards": scenario_cards,
    "risk_ladder": risk_ladder,
    "search_etfs": search_etfs,
    "etf_profile": etf_profile,
    "compare_etfs": compare_etfs,
    "reference_shelf": reference_shelf,
    "build_portfolio": build_portfolio_tool,
    "compare_one_fund": compare_one_fund,
    "plan_contribution": plan_contribution,
    "market_context": market_context,
    "explain_term": explain_term,
    "backtest_summary": backtest_summary,
    "data_status": data_status,
}


def call(name: str, args: dict | None = None) -> dict:
    if name not in TOOLS:
        return {"error": f"unknown tool {name!r}", "tools": sorted(TOOLS)}
    try:
        return TOOLS[name](**(args or {}))
    except (RoboKitInputError, InfeasibleConstraints) as e:  # the person can act on these: plain message plus details
        return {"error": str(e), "details": e.details}
    except SolverNotConverged as e:
        return {"error": "The optimizer did not reach an answer, so nothing was built.", "details": e.details}
    except TypeError as e:
        return {"error": f"bad arguments for {name}: {e}"}
    except (ValueError, KeyError, IndexError) as e:
        return {"error": f"{type(e).__name__}: {e}"}
