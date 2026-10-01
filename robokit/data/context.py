"""Market context: macro, geopolitics and news, each with its source and date.

These series describe the environment. They are shown to the user as context
and risk flags; they do not move portfolio weights unless a back-test in
``robokit.signals`` supports it (see docs/METHOD.md, section on signals).

Sources (tested 28 Sep 2026):

* Bank of Canada Valet API (no key): policy rate, benchmark yields, CPI.
* Yahoo Finance indices: US Treasury yields (^IRX 13-week, ^FVX 5-year,
  ^TNX 10-year, ^TYX 30-year), VIX (^VIX), and USD/CAD.
* FRED (St. Louis Fed) CSV download, optional: high-yield option-adjusted
  spread. The endpoint times out from some networks, so it is best-effort.
* Caldara and Iacoviello Geopolitical Risk index (monthly file from the
  authors' site).
* Baker, Bloom and Davis Economic Policy Uncertainty indices, US and Canada.
* GDELT DOC 2.0 API (no key): news volume and average tone by topic, and
  recent headlines with links.
"""
from __future__ import annotations

import io
import json
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests

from ..config import DATA_DIR, RAW_DIR, USER_AGENT, ensure_dirs

BOC = "https://www.bankofcanada.ca/valet/observations/{series}/json"
BOC_SERIES = {
    "V39079": "BoC policy rate (%)",
    "V80691344": "Canada 3-month T-bill yield (%)",
    "BD.CDN.2YR.DQ.YLD": "Canada 2-year benchmark yield (%)",
    "BD.CDN.10YR.DQ.YLD": "Canada 10-year benchmark yield (%)",
    "STATIC_TOTALCPICHANGE": "Canada CPI inflation, year over year (%)",
}
YAHOO_SERIES = {
    "^IRX": "US 13-week T-bill yield (%)",
    "^FVX": "US 5-year Treasury yield (%)",
    "^TNX": "US 10-year Treasury yield (%)",
    "^VIX": "VIX, expected S&P 500 volatility (%)",
    "CAD=X": "Canadian dollars per US dollar",
}
FRED_SERIES = {"BAMLH0A0HYM2": "US high-yield credit spread (%)"}
GPR_URL = "https://www.matteoiacoviello.com/gpr_files/data_gpr_export.xls"
EPU_URLS = {
    "US": "https://www.policyuncertainty.com/media/US_Policy_Uncertainty_Data.xlsx",
    "Canada": "https://www.policyuncertainty.com/media/Canada_Policy_Uncertainty_Data.xlsx",
}
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
NEWS_TOPICS = {
    "economy": '(recession OR inflation OR "interest rates" OR "central bank")',
    "trade": '(tariff OR tariffs OR "trade war")',
    "geopolitics": '(war OR sanctions OR conflict OR military)',
    "energy": '("oil prices" OR OPEC OR "natural gas")',
    "technology": '("artificial intelligence" OR semiconductor OR chips)',
    "canada": '("Bank of Canada" OR "Canadian economy" OR "Canadian dollar")',
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url: str, timeout: int = 60, **kw) -> requests.Response:
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout, **kw)
    r.raise_for_status()
    return r


def boc_monthly(start: str = "2000-01-01") -> pd.DataFrame:
    """Bank of Canada series, month-end values."""
    url = BOC.format(series=",".join(BOC_SERIES))
    obs = _get(url, params={"start_date": start}).json()["observations"]
    rows = []
    for o in obs:
        row = {"date": o["d"]}
        for k in BOC_SERIES:
            v = o.get(k, {}).get("v")
            row[k] = float(v) if v not in (None, "") else np.nan
        rows.append(row)
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date").resample("ME").last()


def yahoo_monthly(start: str = "2000-01-01") -> pd.DataFrame:
    import yfinance as yf

    d = yf.download(list(YAHOO_SERIES), start=start, interval="1mo", auto_adjust=False, progress=False)["Close"]
    d.index = d.index.to_period("M").to_timestamp("M")
    return d


def fred_monthly(series: str, timeout: int = 20) -> pd.Series | None:
    """Best-effort FRED CSV; returns None when the endpoint does not answer."""
    try:
        text = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}", timeout=timeout).text
    except Exception:
        return None
    df = pd.read_csv(io.StringIO(text))
    df.columns = ["date", series]
    df["date"] = pd.to_datetime(df["date"])
    s = pd.to_numeric(df.set_index("date")[series], errors="coerce")
    return s.resample("ME").last()


def gpr_monthly() -> pd.DataFrame:
    """Geopolitical Risk index (Caldara and Iacoviello), monthly: GPR, threats, acts, plus Canada and US country indices."""
    content = _get(GPR_URL, timeout=90).content
    (RAW_DIR / "data_gpr_export.xls").write_bytes(content)
    df = pd.read_excel(io.BytesIO(content))
    df["month"] = pd.to_datetime(df["month"])
    keep = [c for c in ("GPR", "GPRT", "GPRA", "GPRC_CAN", "GPRC_USA") if c in df.columns]
    out = df.set_index("month")[keep]
    out.index = out.index.to_period("M").to_timestamp("M")
    return out


def epu_monthly() -> pd.DataFrame:
    """Economic Policy Uncertainty indices for the US and Canada."""
    out = {}
    for name, url in EPU_URLS.items():
        content = _get(url, timeout=60).content
        (RAW_DIR / url.rsplit("/", 1)[-1]).write_bytes(content)
        df = pd.read_excel(io.BytesIO(content))
        df = df[pd.to_numeric(df.iloc[:, 0], errors="coerce").notna()]
        year = df.iloc[:, 0].astype(int)
        month = pd.to_numeric(df.iloc[:, 1], errors="coerce")
        df = df[month.notna()]
        idx = pd.to_datetime(dict(year=year[month.notna()], month=month.dropna().astype(int), day=1)) + pd.offsets.MonthEnd(0)
        col = [c for c in df.columns if "news" in str(c).lower() or "index" in str(c).lower() or "policy" in str(c).lower()]
        series = pd.to_numeric(df[col[0] if col else df.columns[2]], errors="coerce")
        out[f"EPU_{name}"] = pd.Series(series.values, index=idx)
    return pd.DataFrame(out)


def _gdelt(params: dict, attempts: int = 5) -> dict:
    """GDELT allows about one request every five seconds; back off on 429."""
    for i in range(attempts):
        try:
            r = requests.get(GDELT, params=params, headers={"User-Agent": USER_AGENT}, timeout=60)
        except requests.RequestException:
            time.sleep(30 * (i + 1))
            continue
        if r.status_code == 429:
            time.sleep(30 * (i + 1))
            continue
        r.raise_for_status()
        time.sleep(12)
        try:
            return r.json()
        except ValueError:  # GDELT answers plain text for malformed queries
            raise RuntimeError(r.text[:200])
    raise RuntimeError("GDELT kept answering 429 Too Many Requests")


def gdelt_topic(query: str, timespan: str = "6months") -> dict:
    """Weekly article volume and average tone for a query, plus the latest headlines with links."""
    base = {"query": f"{query} sourcelang:english", "format": "json", "timespan": timespan}
    tone = _gdelt({**base, "mode": "timelinetone", "timelinesmooth": 7})
    vol = _gdelt({**base, "mode": "timelinevolraw"})
    arts = _gdelt({**base, "mode": "artlist", "maxrecords": 15, "sort": "hybridrel", "timespan": "7days"})

    def series(payload):
        tl = payload.get("timeline") or []
        if not tl:
            return pd.Series(dtype=float)
        pts = tl[0].get("data", [])
        s = pd.Series({pd.to_datetime(p["date"]): p["value"] for p in pts}, dtype=float)
        return s

    # weekly buckets labelled by the Monday that starts each week
    t = series(tone).resample("W-MON", label="left", closed="left").mean()
    v = series(vol).resample("W-MON", label="left", closed="left").sum()
    headlines = [
        {"title": a.get("title"), "url": a.get("url"), "domain": a.get("domain"), "seendate": a.get("seendate")}
        for a in (arts.get("articles") or [])
    ]
    return {"tone_weekly": t, "volume_weekly": v, "headlines": headlines}


def _fetch_news(status: dict) -> dict:
    """Fetch every GDELT topic. A topic that fails keeps its last good data (and says so in
    ``status``), so a rate-limited refresh never replaces working headlines with nothing."""
    path = DATA_DIR / "news.pkl"
    old = pd.read_pickle(path) if path.exists() else {}
    news = {}
    for key, q in NEWS_TOPICS.items():
        try:
            news[key] = gdelt_topic(q)
            status[f"gdelt_{key}"] = "ok"
        except Exception as e:
            status[f"gdelt_{key}"] = f"failed: {type(e).__name__}: {e}"[:300]
            if isinstance(old.get(key), dict):
                news[key] = old[key]
                status[f"gdelt_{key}"] += f"; kept the data fetched {old.get('_meta', {}).get('fetched', 'earlier')}"
    news["_meta"] = {"fetched": _now(), "status": status}
    tmp = path.with_suffix(".tmp")
    pd.to_pickle(news, tmp)
    tmp.replace(path)
    return news


def build_news() -> dict:
    """Fetch the GDELT topics on their own (slow: GDELT rate-limits hard)."""
    ensure_dirs()
    return _fetch_news({})


def build_context(include_news: bool = True) -> dict:
    """Fetch everything, save raw and tidy copies, and return a summary dict with as-of dates."""
    ensure_dirs()
    fetched = _now()
    status: dict[str, str] = {}
    frames = {}
    for name, fn in (("boc", boc_monthly), ("yahoo", yahoo_monthly), ("gpr", gpr_monthly), ("epu", epu_monthly)):
        try:
            frames[name] = fn()
            status[name] = "ok"
        except Exception as e:  # record, never hide, a failed source
            status[name] = f"failed: {type(e).__name__}: {e}"[:300]
    hy = fred_monthly("BAMLH0A0HYM2")
    status["fred_hy_spread"] = "ok" if hy is not None else "unavailable (endpoint did not answer)"
    macro = pd.concat([f for f in frames.values()], axis=1) if frames else pd.DataFrame()
    if hy is not None:
        macro["BAMLH0A0HYM2"] = hy
    macro = macro.sort_index()
    macro.to_pickle(DATA_DIR / "context_monthly.pkl")

    news = _fetch_news(status) if include_news else {}
    meta = {"fetched": fetched, "status": status}
    (DATA_DIR / "context_meta.json").write_text(json.dumps(meta, indent=2))
    return {"macro": macro, "news": news, "meta": meta}
