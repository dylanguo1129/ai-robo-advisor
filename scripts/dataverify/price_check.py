"""Independent check of the monthly total returns the pipeline stores (data/v2/close_monthly.pkl).

The pipeline downloads Yahoo's monthly bars (interval="1mo", auto_adjust=True). This script takes a different path:
daily adjusted closes, the last trading day of each month, and the month's return from those, then compares month by
month with the stored returns up to the snapshot's last month (2026-08). Tickers: every eligible Canadian fund, every
stand-in, the first five candidates of every US slot, and CAD=X.

    python -B scripts/dataverify/price_check.py download   # network, resumable; daily chunks in data/v2/dataverify/daily/
    python -B scripts/dataverify/price_check.py compare    # -> data/v2/dataverify/price_check.csv and a summary
"""

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[2] / "data" / "v2" / "dataverify"  # local data, like the rest of data/v2
REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
DAILY = OUT / "daily"
LAST = pd.Timestamp("2026-08-31")


def tickers() -> list[str]:
    from robokit.history import PROXIES
    from robokit.shelf import SLEEVES, candidates

    U = pd.read_pickle(REPO / "data" / "v2" / "universe.pkl")
    t = set(U[(U.market == "CA") & U.eligible].yahoo)
    t |= {x for v in PROXIES.values() for x, _ in v if not x.startswith("RATE:")}
    for s in SLEEVES.values():
        if s.market == "US":
            t |= set(candidates(U, s).yahoo[:5])
    t.add("CAD=X")
    return sorted(t)


def download():
    import yfinance as yf

    DAILY.mkdir(exist_ok=True)
    tk = tickers()
    print(len(tk), "tickers")
    for k in range(0, len(tk), 40):
        p = DAILY / f"chunk_{k // 40:03d}.pkl"
        if p.exists():
            continue
        part = tk[k : k + 40]
        for attempt in range(4):
            try:
                d = yf.download(part, period="max", interval="1d", auto_adjust=True, progress=False, threads=True, group_by="column")
                if d is not None and len(d):
                    break
            except Exception as e:  # noqa: BLE001
                print("retry", k, e)
            time.sleep(5 * (attempt + 1))
        c = d["Close"]
        if isinstance(c, pd.Series):
            c = c.to_frame(part[0])
        tmp = p.with_suffix(".tmp")
        pd.to_pickle({"close": c, "tickers": part}, tmp)
        tmp.replace(p)
        print("chunk", k // 40, c.shape, flush=True)
        time.sleep(1.5)


def compare():
    closes = []
    for p in sorted(DAILY.glob("chunk_*.pkl")):
        closes.append(pd.read_pickle(p)["close"])
    daily = pd.concat(closes, axis=1)
    daily = daily.loc[:, ~daily.columns.duplicated()]
    daily.index = pd.to_datetime(daily.index).tz_localize(None)
    me = daily.resample("ME").last()
    me = me[me.index <= LAST]
    # a month counts only if the fund traded in its last five calendar days (no stale carry-forward)
    last_day = daily.notna().apply(lambda s: s[s].index.to_series().resample("ME").max())
    ok = last_day.reindex(me.index).apply(lambda s: (me.index - s).dt.days <= 5)
    me = me.where(ok)
    r_new = me.pct_change(fill_method=None).where(me.notna() & me.shift(1).notna())
    stored = pd.read_pickle(REPO / "data" / "v2" / "close_monthly.pkl")
    fx = pd.read_pickle(REPO / "data" / "v2" / "usdcad_monthly.pkl")
    stored["CAD=X"] = fx
    r_old = stored.pct_change(fill_method=None).where(stored.notna() & stored.shift(1).notna())
    rows = []
    for t in daily.columns:
        if t not in r_old.columns:
            rows.append(dict(yahoo=t, status="not in the stored panel"))
            continue
        a, b = r_old[t], r_new[t]
        both = a.notna() & b.notna()
        d = (a - b)[both].abs()
        first_old = stored[t].first_valid_index()
        first_new = daily[t].first_valid_index()
        rows.append(
            dict(
                yahoo=t,
                months=int(both.sum()),
                max_abs=float(d.max()) if len(d) else np.nan,
                n_over_0_5pct=int((d > 0.005).sum()),
                n_over_2pct=int((d > 0.02).sum()),
                worst_month=str(d.idxmax().date()) if len(d) else "",
                stored_first=str(first_old.date()) if first_old is not None else "",
                daily_first=str(first_new.date()) if first_new is not None else "",
                stored_only=int((a.notna() & b.isna()).sum()),
                daily_only=int((a.isna() & b.notna()).sum()),
                stored_last=str(stored[t].last_valid_index().date()) if stored[t].last_valid_index() is not None else "",
            )
        )
    out = pd.DataFrame(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT / "price_check.csv", index=False)
    v = out.dropna(subset=["months"])
    print(
        "tickers compared:",
        len(v),
        "| not in stored panel:",
        int((out["status"] == "not in the stored panel").sum()) if "status" in out else 0,
    )
    print("months compared:", int(v.months.sum()))
    print("tickers with every month within 0.5%:", int((v.n_over_0_5pct == 0).sum()))
    print("tickers with any month off by more than 2%:", int((v.n_over_2pct > 0).sum()))
    print(v.sort_values("max_abs", ascending=False).head(25).to_string(index=False))


if __name__ == "__main__":
    {"download": download, "compare": compare}[sys.argv[1]]()
