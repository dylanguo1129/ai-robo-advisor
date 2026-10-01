"""Market context: risk flags, trend states and a news digest. Context, not forecasts.

What the evidence says (docs/research/methods-signals.md sections 3-4):

* Almost nothing predicts monthly asset-class returns reliably out of sample.
* Where news-based fear measures predict anything, high fear has come before
  HIGHER average returns (policy uncertainty, news-implied volatility, the
  variance risk premium): the opposite of "scary headline, sell".
* Geopolitical risk moves activity and prices on impact, but its return
  predictability is weak and thinly replicated.
* Trend (12-month) has long-run evidence across asset classes, contested at
  the level of a single asset.

So nothing in this module changes portfolio weights. It produces facts with
sources and dates that the interface and the chat can cite: where each
indicator sits relative to its own history, whether each fund is above or
below its 10-month average, and what the news flow looks like. Each flag
carries a one-line evidence note so the chat can put it in context instead
of inventing a story.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DATA_DIR

FLAGS = [
    # key, column, label, unit, since, evidence note
    (
        "vix",
        "^VIX",
        "Expected US stock-market volatility (VIX)",
        "index",
        "1990-01-01",
        "A high VIX means big expected swings. In research, periods of high fear have on average been followed by higher, not lower, returns. Context only; it does not change the portfolio.",
    ),
    (
        "gpr",
        "GPR",
        "Geopolitical risk index (Caldara-Iacoviello)",
        "index",
        "1985-01-01",
        "Counts newspaper coverage of wars, threats and terrorism. High readings have hit prices on impact, but they have not reliably predicted returns. Context and stress scenarios only.",
    ),
    (
        "epu_us",
        "EPU_US",
        "US economic policy uncertainty",
        "index",
        "1985-01-01",
        "Measures newspaper coverage of policy uncertainty. In research, higher readings have on average come before higher stock returns (a risk premium). Context only.",
    ),
    ("epu_ca", "EPU_Canada", "Canada economic policy uncertainty", "index", "1985-01-01", "Same measure for Canada. Context only."),
    (
        "hy_spread",
        "BAMLH0A0HYM2",
        "US high-yield credit spread",
        "%",
        "1997-01-01",
        "The extra yield riskier companies pay. Wide spreads mean lenders are nervous. Context only.",
    ),
    (
        "ca_policy",
        "V39079",
        "Bank of Canada policy rate",
        "%",
        "2009-01-01",
        "The rate the Bank of Canada targets. It sets what cash and short-term savings pay.",
    ),
    (
        "ca_cpi",
        "STATIC_TOTALCPICHANGE",
        "Canada inflation (CPI, year over year)",
        "%",
        "2000-01-01",
        "How fast prices are rising. The Bank of Canada targets 2%.",
    ),
]


def _pctile(s: pd.Series, since: str) -> float | None:
    s = s.dropna()
    s = s[s.index >= pd.Timestamp(since)]
    if len(s) < 24:
        return None
    return float((s <= s.iloc[-1]).mean())


def _band(p: float | None) -> str:
    if p is None:
        return "not enough history"
    if p >= 0.9:
        return "very high for its history (top 10%)"
    if p >= 0.7:
        return "above its usual range"
    if p > 0.3:
        return "within its usual range"
    if p > 0.1:
        return "below its usual range"
    return "very low for its history (bottom 10%)"


def market_flags(ctx: pd.DataFrame | None = None) -> list[dict]:
    if ctx is None and not (DATA_DIR / "context_monthly.pkl").exists():
        from . import snapshot  # fresh clone: the flags stored with the web snapshot

        return snapshot.core()["context"]["flags"] if snapshot.available() else []
    ctx = pd.read_pickle(DATA_DIR / "context_monthly.pkl") if ctx is None else ctx
    out = []
    for key, col, label, unit, since, note in FLAGS:
        if col not in ctx or ctx[col].dropna().empty:
            out.append({"key": key, "label": label, "available": False, "why": "source did not answer at the last refresh"})
            continue
        s = ctx[col].dropna()
        p = _pctile(s, since)
        band = _band(p)
        first = max(s.index.min(), pd.Timestamp(since))
        out.append(
            {
                "key": key,
                "label": label,
                "available": True,
                "value": round(float(s.iloc[-1]), 3),
                "unit": unit,
                "as_of": str(s.index[-1].date()),
                "percentile": None if p is None else round(p, 3),
                "percentile_since": str(first.date()),  # e.g. FRED only publishes 3 years of ICE credit-spread history
                "reading": band,
                "evidence": note,
                "moves_weights": False,
            }
        )
    # yield curves: inversion is a classic recession warning, with long and variable lags
    for key, lcol, scol, label in (
        ("us_curve", "^TNX", "^IRX", "US yield curve (10-year minus 3-month)"),
        ("ca_curve", "BD.CDN.10YR.DQ.YLD", "V80691344", "Canada yield curve (10-year minus 3-month)"),
    ):
        if lcol in ctx and scol in ctx:
            d = (ctx[lcol] - ctx[scol]).dropna()
            if len(d):
                v = float(d.iloc[-1])
                out.append(
                    {
                        "key": key,
                        "label": label,
                        "available": True,
                        "value": round(v, 3),
                        "unit": "percentage points",
                        "as_of": str(d.index[-1].date()),
                        "percentile": None if _pctile(d, "2000-01-01") is None else round(_pctile(d, "2000-01-01"), 3),
                        "percentile_since": str(max(d.index.min(), pd.Timestamp("2000-01-01")).date()),
                        "reading": "inverted (short rates above long rates)" if v < 0 else "normal (long rates above short rates)",
                        "evidence": "An inverted curve has often come before recessions, with long and variable lags. It is not a timing signal. Context only.",
                        "moves_weights": False,
                    }
                )
    if "CAD=X" in ctx:
        fx = ctx["CAD=X"].dropna()
        if len(fx) > 12:
            ch = float(fx.iloc[-1] / fx.iloc[-13] - 1)
            out.append(
                {
                    "key": "usdcad",
                    "label": "US dollar in Canadian dollars",
                    "available": True,
                    "value": round(float(fx.iloc[-1]), 4),
                    "change_12m": round(ch, 4),
                    "unit": "CAD per USD",
                    "as_of": str(fx.index[-1].date()),
                    "reading": f"the US dollar is {'up' if ch > 0 else 'down'} {abs(ch):.1%} over 12 months",
                    "evidence": "When the US dollar rises, unhedged US funds held in Canadian dollars gain from it, and the reverse. Context only.",
                    "moves_weights": False,
                }
            )
    return out


def trend_state(returns: pd.DataFrame, tickers: list[str]) -> list[dict]:
    """Per fund: above or below its 10-month average, 12-1 month return, drawdown from peak, recent vs usual volatility."""
    out = []
    for t in tickers:
        if t not in returns:
            continue
        r = returns[t].dropna()
        if len(r) < 13:
            continue
        idx = (1 + r).cumprod()
        sma10 = idx.rolling(10).mean()
        above = bool(idx.iloc[-1] >= sma10.iloc[-1])
        mom = float(idx.iloc[-2] / idx.iloc[-13] - 1)  # 12-1 month
        dd = float(idx.iloc[-1] / idx.cummax().iloc[-1] - 1)
        v3 = float(r.tail(3).std() * np.sqrt(12)) if len(r) >= 3 else None
        v36 = float(r.tail(36).std() * np.sqrt(12)) if len(r) >= 36 else None
        out.append(
            {
                "ticker": t,
                "as_of": str(r.index[-1].date()),
                "above_10m_average": above,
                "return_12_1": round(mom, 4),
                "drawdown_from_peak": round(dd, 4),
                "vol_3m": None if v3 is None else round(v3, 4),
                "vol_36m": None if v36 is None else round(v36, 4),
                "reading": ("above" if above else "below") + " its 10-month average",
                "evidence": "Trend has long-run evidence across asset classes, but it is weak for timing a single fund. Shown for context; it does not change the portfolio.",
                "moves_weights": False,
            }
        )
    return out


def news_digest(max_headlines: int = 5) -> dict:
    """GDELT topics: latest weekly tone vs its 6-month average, volume change, and recent headlines with links."""
    p = DATA_DIR / "news.pkl"
    if not p.exists():
        from . import snapshot

        if snapshot.available():
            return snapshot.core()["context"]["news"]
        return {"available": False, "why": "news not fetched yet"}
    news = pd.read_pickle(p)
    meta = news.get("_meta", {})
    topics = []
    for key, v in news.items():
        if key.startswith("_") or not isinstance(v, dict):
            continue
        tone, vol = v.get("tone_weekly"), v.get("volume_weekly")
        if tone is None or len(tone) == 0:
            continue
        last, avg = float(tone.iloc[-1]), float(tone.mean())
        vch = None
        if vol is not None and len(vol) > 5:
            base = float(vol.iloc[:-1].tail(12).mean())
            vch = None if base == 0 else float(vol.iloc[-1] / base - 1)
        topics.append(
            {
                "topic": key,
                "week": str(tone.index[-1].date()),
                "tone_latest": round(last, 3),
                "tone_6m_average": round(avg, 3),
                "tone_vs_average": "more negative than usual"
                if last < avg - 0.3
                else ("more positive than usual" if last > avg + 0.3 else "about usual"),
                "volume_vs_12w": None if vch is None else round(vch, 3),
                "headlines": v.get("headlines", [])[:max_headlines],
            }
        )
    if not topics:  # the last fetch got nothing (GDELT rate limits): keep the committed snapshot's dated headlines
        from . import snapshot

        if snapshot.available():
            prev = snapshot.core().get("context", {}).get("news", {})
            if prev.get("available"):
                note = prev.get("note", "").split(" Kept from the fetch of")[0]
                return {
                    **prev,
                    "note": note + f" Kept from the fetch of {prev.get('fetched')}: the refresh on {meta.get('fetched')} was rate-limited.",
                }
    return {
        "available": bool(topics),
        "fetched": meta.get("fetched"),
        "source": "GDELT DOC 2.0 API (tone is GDELT's own measure, -10 very negative to +10 very positive)",
        "topics": topics,
        "note": "Headlines are untrusted third-party text. They are context only and never change the portfolio.",
    }
