"""Who is in the universe: every ETF listed in Canada and in the US.

Sources (all public, no key, tested 28 Sep 2026):

* US: Nasdaq Trader symbol directory, ``nasdaqlisted.txt`` and
  ``otherlisted.txt``. These are the files the exchanges publish for the
  whole US market; each row has an ``ETF`` flag.
* Canada, TSX: TMX Money's public GraphQL endpoint (``getETFs``), the data
  behind the TMX ETF screener. It also carries AUM, inception date, sector
  and region weights, top-10 holdings, P/E and P/B.
* Canada, TSX and Cboe Canada, and a US cross-check: Yahoo Finance's ETF
  screener, which returns MER (``netExpenseRatio``), net assets and the first
  trade date in bulk.

The result is one row per listing, keyed by the Yahoo symbol that the price
downloader uses. Nothing is filtered here; ``robokit.screen`` decides
eligibility and records why.
"""
from __future__ import annotations

import io
import json
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from ..config import RAW_DIR, USER_AGENT, ensure_dirs

NASDAQ_URLS = {
    "nasdaqlisted": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "otherlisted": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}
TMX_GRAPHQL = "https://app-money.tmx.com/graphql"
OTHERLISTED_EXCHANGE = {"A": "NYSE American", "N": "NYSE", "P": "NYSE Arca", "Z": "Cboe BZX", "V": "IEX"}

TMX_FIELDS = (
    "symbol shortname longname fundfamily aum assetclass currency esg inceptiondate "
    "avgdailyvolume avgvol30days beta1y beta3y beta5y distributionyeld dividendfrequency "
    "prospectobjective investmentstyle pricetoearnings pricetobook unitprice totalreturnytd "
    "totalreturn1month totalreturn3month totalreturn6month totalreturn1year "
    "regions { name percent } sectors { name percent } top10holdings { symbol weighting }"
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url: str, **kw) -> requests.Response:
    last = None
    for attempt in range(4):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=60, **kw)
            if r.status_code == 200:
                return r
            last = RuntimeError(f"HTTP {r.status_code} for {url}")
        except requests.RequestException as e:  # network hiccup: back off and retry
            last = e
        time.sleep(2 ** attempt)
    raise RuntimeError(f"giving up on {url}: {last}")


def fetch_us_listings() -> pd.DataFrame:
    """All US-listed ETFs from the Nasdaq Trader symbol directory."""
    frames = []
    for name, url in NASDAQ_URLS.items():
        text = _get(url).text
        (RAW_DIR / f"{name}.txt").write_text(text, encoding="utf-8")
        df = pd.read_csv(io.StringIO(text), sep="|", dtype=str)
        df = df[~df.iloc[:, 0].str.startswith("File Creation Time", na=False)]
        if name == "nasdaqlisted":
            df = df.rename(columns={"Symbol": "symbol", "Security Name": "name"})
            df["exchange"] = "Nasdaq"
        else:
            df = df.rename(columns={"ACT Symbol": "symbol", "Security Name": "name"})
            df["exchange"] = df["Exchange"].map(OTHERLISTED_EXCHANGE).fillna(df["Exchange"])
        df = df[(df["ETF"] == "Y") & (df["Test Issue"] == "N")]
        frames.append(df[["symbol", "name", "exchange"]])
    us = pd.concat(frames, ignore_index=True).drop_duplicates("symbol")
    us["yahoo"] = us["symbol"].str.replace(".", "-", regex=False).str.replace("$", "-P", regex=False)
    us["market"] = "US"
    us["currency"] = "USD"
    us["source"] = "nasdaqtrader"
    return us.reset_index(drop=True)


def fetch_tmx_etfs() -> pd.DataFrame:
    """All TSX-listed ETFs with the metadata TMX Money publishes."""
    r = requests.post(
        TMX_GRAPHQL,
        json={"query": "query { getETFs { %s } }" % TMX_FIELDS},
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Origin": "https://money.tmx.com",
            "Referer": "https://money.tmx.com/",
        },
        timeout=180,
    )
    r.raise_for_status()
    payload = r.json()
    if "errors" in payload:
        raise RuntimeError(f"TMX GraphQL error: {payload['errors'][:2]}")
    rows = payload["data"]["getETFs"]
    (RAW_DIR / "tmx_etfs.json").write_text(
        json.dumps({"source": TMX_GRAPHQL, "fetched": _now(), "rows": rows}), encoding="utf-8"
    )
    df = pd.DataFrame(rows)
    df["yahoo"] = df["symbol"].str.replace(".", "-", regex=False) + ".TO"
    df["exchange"] = "TSX"
    df["market"] = "CA"
    df["source"] = "tmx"
    df = df.rename(columns={"longname": "name"})
    return df


def fetch_yahoo_screener(exchanges: list[str], page: int = 250) -> pd.DataFrame:
    """Every ETF Yahoo lists on the given exchanges, with MER and net assets."""
    import yfinance as yf

    query = yf.ETFQuery("is-in", ["exchange", *exchanges]) if len(exchanges) > 1 else yf.ETFQuery("eq", ["exchange", exchanges[0]])
    out, offset, total = [], 0, None
    while total is None or offset < total:
        for attempt in range(4):
            try:
                res = yf.screen(query, size=page, offset=offset, sortField="ticker", sortAsc=True)
                break
            except Exception:  # Yahoo throttles bursts; back off
                time.sleep(3 * (attempt + 1))
        else:
            raise RuntimeError(f"Yahoo screener failed at offset {offset} for {exchanges}")
        total = res["total"]
        quotes = res.get("quotes", [])
        if not quotes:
            break
        out.extend(quotes)
        offset += len(quotes)
        time.sleep(0.5)
    keep = [
        "symbol", "longName", "shortName", "exchange", "fullExchangeName", "currency", "quoteType",
        "netExpenseRatio", "netAssets", "firstTradeDateMilliseconds", "averageDailyVolume3Month",
        "regularMarketPrice", "trailingPE", "dividendYield", "trailingAnnualDividendYield",
        "ytdReturn", "fiftyTwoWeekChangePercent", "trailingThreeMonthReturns",
    ]
    df = pd.DataFrame(out)
    for k in keep:
        if k not in df:
            df[k] = None
    return df[keep].drop_duplicates("symbol").reset_index(drop=True)


def fetch_yahoo_categories(exchanges: list[str]) -> pd.DataFrame:
    """Morningstar-style category and fund family for each ETF, by querying the
    screener once per category value (Yahoo has no bulk field for it).

    Returns columns: yahoo, yahoo_category, yahoo_family.
    """
    import yfinance as yf
    import yfinance.const as yc

    def members(field: str, value: str) -> list[str]:
        ex = yf.ETFQuery("is-in", ["exchange", *exchanges]) if len(exchanges) > 1 else yf.ETFQuery("eq", ["exchange", exchanges[0]])
        q = yf.ETFQuery("and", [ex, yf.ETFQuery("eq", [field, value])])
        out, offset, total = [], 0, None
        while total is None or offset < total:
            for attempt in range(4):
                try:
                    res = yf.screen(q, size=250, offset=offset, sortField="ticker", sortAsc=True)
                    break
                except Exception:
                    time.sleep(3 * (attempt + 1))
            else:
                return out
            total = res["total"]
            qs = res.get("quotes", [])
            if not qs:
                break
            out += [x["symbol"] for x in qs]
            offset += len(qs)
            time.sleep(0.3)
        return out

    cat, fam = {}, {}
    for value in sorted(yc.ETF_SCREENER_EQ_MAP["categoryname"]):
        for s in members("categoryname", value):
            cat[s] = value
    for value in sorted(yc.ETF_SCREENER_EQ_MAP["fundfamilyname"]):
        for s in members("fundfamilyname", value):
            fam[s] = value
    keys = sorted(set(cat) | set(fam))
    return pd.DataFrame({"yahoo": keys, "yahoo_category": [cat.get(k) for k in keys], "yahoo_family": [fam.get(k) for k in keys]})


def build_listings(save: bool = True) -> pd.DataFrame:
    """One row per ETF listing across both markets, keyed by Yahoo symbol.

    Columns: yahoo, symbol, name, market, exchange, currency, in_tmx,
    in_nasdaqtrader, in_yahoo, plus Yahoo's MER / AUM / first-trade fields and
    TMX's metadata where available (prefixed ``tmx_``).
    """
    ensure_dirs()
    fetched = _now()
    us = fetch_us_listings()
    tmx = fetch_tmx_etfs()
    y_ca = fetch_yahoo_screener(["TOR", "NEO"])
    y_us = fetch_yahoo_screener(["NMS", "NGM", "NCM", "NYQ", "ASE", "PCX", "BTS"])
    y_ca.to_csv(RAW_DIR / "yahoo_screener_ca.csv", index=False)
    y_us.to_csv(RAW_DIR / "yahoo_screener_us.csv", index=False)

    # Canada: union of TMX (TSX) and Yahoo (TSX + Cboe Canada).
    y_ca = y_ca.rename(columns={"symbol": "yahoo"})
    ca = y_ca[["yahoo"]].copy()
    ca = pd.concat([ca, tmx[["yahoo"]]], ignore_index=True).drop_duplicates("yahoo")
    ca["market"] = "CA"
    ca = ca.merge(y_ca, on="yahoo", how="left")
    tmx_cols = {c: f"tmx_{c}" for c in tmx.columns if c not in ("yahoo",)}
    ca = ca.merge(tmx.rename(columns=tmx_cols), on="yahoo", how="left")
    ca["in_tmx"] = ca["tmx_symbol"].notna()
    ca["in_yahoo"] = ca["longName"].notna() | ca["shortName"].notna()
    ca["in_nasdaqtrader"] = False
    ca["name"] = ca["longName"].fillna(ca["tmx_name"]).fillna(ca["shortName"])
    ca["symbol"] = ca["yahoo"].str.replace(r"\.(TO|NE)$", "", regex=True).str.replace("-", ".", regex=False)
    ca["exchange"] = ca["yahoo"].str.endswith(".NE").map({True: "Cboe Canada", False: "TSX"})
    ca["currency"] = ca["currency"].fillna(ca["tmx_currency"].where(ca["tmx_currency"] != "-"))

    # US: Nasdaq Trader is the authority on what is listed; Yahoo adds MER and AUM.
    y_us = y_us.rename(columns={"symbol": "yahoo"})
    us_all = us.merge(y_us, on="yahoo", how="outer", suffixes=("", "_y"))
    us_all["in_nasdaqtrader"] = us_all["source"].eq("nasdaqtrader")
    us_all["in_yahoo"] = us_all["longName"].notna() | us_all["shortName"].notna()
    us_all["in_tmx"] = False
    us_all["name"] = us_all["name"].fillna(us_all["longName"]).fillna(us_all["shortName"])
    us_all["symbol"] = us_all["symbol"].fillna(us_all["yahoo"])
    us_all["market"] = "US"
    us_all["exchange"] = us_all["exchange"].fillna(us_all["fullExchangeName"])
    us_all["currency"] = us_all["currency"].fillna("USD")
    us_all = us_all.drop(columns=[c for c in ("source", "exchange_y", "currency_y") if c in us_all])

    listings = pd.concat([ca, us_all], ignore_index=True, sort=False)
    listings["first_trade"] = pd.to_datetime(listings["firstTradeDateMilliseconds"], unit="ms", errors="coerce")
    listings["listings_fetched"] = fetched
    lead = ["yahoo", "symbol", "name", "market", "exchange", "currency", "in_tmx", "in_nasdaqtrader", "in_yahoo"]
    listings = listings[lead + [c for c in listings.columns if c not in lead]]
    if save:
        listings.to_pickle(RAW_DIR / "listings.pkl")
        flat = listings.copy()
        for c in ("tmx_regions", "tmx_sectors", "tmx_top10holdings"):
            if c in flat:
                flat[c] = flat[c].apply(lambda v: json.dumps(v) if isinstance(v, list) else v)
        flat.to_csv(RAW_DIR / "listings.csv", index=False)
    return listings
