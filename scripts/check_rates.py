"""Check that the rate and exchange-rate scripts work as intended.

    python scripts/check_rates.py

Reads from the Bank of Canada, Yahoo Finance and FRED and prints one line per check
(PASS, WARN or FAIL) with the values behind it. Nothing is saved. It ends with the
values to compare by hand against the Bank of Canada website. Exit code 1 if any
check fails.
"""

from __future__ import annotations

import io
import json
import os
import sys

import pandas as pd
import requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import robokit.engine as E  # noqa: E402
from robokit.data.context import BOC_SERIES, boc_monthly, yahoo_monthly  # noqa: E402
from robokit.data.prices import to_cad, usdcad_monthly  # noqa: E402
from robokit.history import rate_returns  # noqa: E402

VALET = "https://www.bankofcanada.ca/valet/observations/{series}/json"
results: list[tuple[str, str, str]] = []


def report(status: str, name: str, detail: str) -> None:
    results.append((status, name, detail))
    print(f"{status:4}  {name}\n      {detail}")


def valet_recent(series: str, n: int = 3) -> list[tuple[str, float]]:
    """The latest n observations, oldest first (Valet returns them newest first)."""
    obs = requests.get(VALET.format(series=series), params={"recent": n}, timeout=60).json()["observations"]
    return sorted((o["d"], float(o[series]["v"])) for o in obs if o.get(series, {}).get("v") not in (None, ""))


def check(name: str):
    def wrap(fn):
        try:
            fn(name)
        except Exception as e:  # a check that cannot run is a failure, never a silent skip
            report("FAIL", name, f"could not run: {type(e).__name__}: {e}")
        return fn

    return wrap


boc = None


@check("1. Bank of Canada fetch works and rates are in percent")
def _(name):
    global boc
    boc = boc_monthly(start="2000-01-01")
    missing = [s for s in BOC_SERIES if s not in boc or boc[s].dropna().empty]
    policy = float(boc["V39079"].dropna().iloc[-1])
    ok = not missing and 0.1 <= policy <= 10
    report(
        "PASS" if ok else "FAIL",
        name,
        f"{len(boc.columns)} series, policy rate {policy:.2f} (expect about 2.25, not 0.0225), missing: {missing or 'none'}",
    )


@check("2. The T-bill data is fresh")
def _(name):
    d, v = valet_recent("V80691344")[-1]
    age = (pd.Timestamp.today().normalize() - pd.Timestamp(d)).days
    report(
        "PASS" if age <= 14 else "WARN",
        name,
        f"latest 3-month T-bill {v:.2f}% on {d}, {age} days old (weekly, dated Wednesdays and published a day or two later; "
        "expect 14 days or less)",
    )


@check("3. Every series is monthly, with no gaps and no stale series")
def _(name):
    if boc is None:
        raise RuntimeError("the Bank of Canada data did not load (see check 1)")
    m = pd.concat([boc, yahoo_monthly()], axis=1)
    bad = []
    for c in m:
        s = m[c].dropna()
        gaps = int(m[c].loc[s.index[0] : s.index[-1]].isna().sum())
        stale = (m.index[-1].to_period("M") - s.index[-1].to_period("M")).n  # CPI is published about a month late
        if gaps or stale > 2 or not s.index.is_month_end.all():
            bad.append(f"{c} ({gaps} gaps, last {s.index[-1]:%Y-%m})")
    report("PASS" if not bad else "FAIL", name, f"{m.shape[1]} series checked; problems: {', '.join(bad) or 'none'}")


@check("4. US yields match the Federal Reserve (FRED)")
def _(name):
    import yfinance as yf

    start = (pd.Timestamp.today() - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    y = yf.download(["^IRX", "^FVX", "^TNX"], start=start, interval="1d", auto_adjust=False, progress=False)["Close"]
    gaps, levels = {}, {}
    for tick, fred in (("^IRX", "DTB3"), ("^FVX", "DGS5"), ("^TNX", "DGS10")):
        text = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fred}&cosd={start}", timeout=30).text
        f = pd.read_csv(io.StringIO(text), index_col=0, parse_dates=True).iloc[:, 0]
        both = pd.concat([y[tick], pd.to_numeric(f, errors="coerce")], axis=1, keys=["yahoo", "fred"]).dropna()
        gaps[tick] = round(float((both.yahoo - both.fred).abs().max()), 3)
        levels[tick] = round(float(both.yahoo.iloc[-1]), 2)
    # Yahoo's close and FRED's end-of-day reading are taken at different times, so gaps of a few hundredths are normal.
    big = max(gaps.values())
    units_ok = all(1 <= v <= 15 for v in levels.values())
    status = "FAIL" if (not units_ok or big > 0.25) else ("WARN" if big > 0.10 else "PASS")
    report(status, name, f"largest gap in points {gaps} (expect under 0.10); latest levels {levels} (expect about 4 to 6, not 40 to 60)")


@check("5. Each market uses its own bill as the risk-free rate")
def _(name):
    ca, us = E.risk_free("CA"), E.risk_free("US")
    ok = "Bank of Canada" in ca[1] and "^IRX" in us[1] and 0.001 < ca[0] < 0.1 and 0.001 < us[0] < 0.1
    fallback = "fallback" in ca[1] or "fallback" in us[1]
    report(
        "PASS" if ok else ("WARN" if fallback else "FAIL"),
        name,
        f"Canada {ca[0]:.4f} ({ca[1]}); US {us[0]:.4f} ({us[1]}); data source: {E.data_source()}",
    )


@check("6. FX is Canadian dollars per US dollar and converts the right way")
def _(name):
    fx = usdcad_monthly()
    last = fx.index[-1]
    obs = requests.get(
        VALET.format(series="FXUSDCAD"), params={"start_date": f"{last:%Y-%m}-01", "end_date": f"{last:%Y-%m-%d}"}, timeout=60
    ).json()["observations"]
    boc_d, boc_v = max((o["d"], float(o["FXUSDCAD"]["v"])) for o in obs if o.get("FXUSDCAD", {}).get("v") not in (None, ""))
    gap = abs(float(fx.iloc[-1]) / boc_v - 1)
    toy_fx = pd.Series([1.40, 1.414], index=pd.to_datetime(["2026-07-31", "2026-08-31"]))
    toy = float(to_cad(pd.DataFrame({"US fund": [0.0, 0.0]}, index=toy_fx.index), toy_fx).iloc[-1, 0])
    eng = E._load()[2].dropna()  # the series the engine actually converts with (local cache or snapshot)
    ok = 1.0 <= float(fx.iloc[-1]) <= 1.8 and 1.0 <= float(eng.iloc[-1]) <= 1.8 and gap <= 0.005 and abs(toy - 0.01) < 1e-9
    report(
        "PASS" if ok else "FAIL",
        name,
        f"Yahoo {fx.iloc[-1]:.4f} for {last:%b %Y} vs Bank of Canada {boc_v:.4f} on {boc_d} (gap {gap:.2%}, expect under 0.5%); "
        f"the engine uses {eng.iloc[-1]:.4f} for {eng.index[-1]:%b %Y}; "
        f"a flat US fund when the US dollar rises 1% returns {toy:.2%} in CAD (expect 1.00%)",
    )


@check("7. Cash returns from the T-bill are right")
def _(name):
    ctx = pd.DataFrame({"V80691344": [2.27, 2.39]}, index=pd.to_datetime(["2026-08-31", "2026-09-30"]))
    r = rate_returns(ctx, "V80691344")
    v = float(r.iloc[0])
    ok = len(r) == 1 and abs(v - 0.0227 / 12) < 1e-9
    report("PASS" if ok else "FAIL", name, f"2.27% in August gives {v:.6f} for September (expect 0.001892: last month's yield / 100 / 12)")


@check("8. The risk-free rate does not move the weights")
def _(name):
    req = dict(market="CA", risk_level=3, resample=False, n_boot=0)
    a = E.build_portfolio(E.Request(**req))
    keep = E.risk_free
    E.risk_free = lambda market: (0.05, "test 5%")
    try:
        b = E.build_portfolio(E.Request(**req))
    finally:
        E.risk_free = keep
    wa = {h["ticker"]: h["weight"] for h in a["holdings"]}
    wb = {h["ticker"]: h["weight"] for h in b["holdings"]}
    ok = wa == wb and abs(a["stats"]["sharpe_model"] - b["stats"]["sharpe_model"]) < 1e-9
    report(
        "PASS" if ok else "FAIL",
        name,
        f"Balanced mix at the real rate and at 5%: weights identical {wa == wb}; model return {a['stats']['model_return']:.4f} -> {b['stats']['model_return']:.4f}; "
        f"Sharpe {a['stats']['sharpe_model']} -> {b['stats']['sharpe_model']}",
    )


@check("9. The Python engine and the web page use the same rate")
def _(name):
    with open(os.path.join(ROOT, "web", "data", "core.json"), encoding="utf-8") as fh:
        core = json.load(fh)
    page, eng = core["risk_free"]["CA"], E.risk_free("CA")
    same = abs(page["rate"] - eng[0]) < 1e-9
    note = "" if same else ". A known gap on a fresh clone (the snapshot keeps rate months only where prices exist); weights are unaffected"
    report("PASS" if same else "WARN", name, f"page {page['rate']:.4f} ({page['source']}); engine {eng[0]:.4f} ({eng[1]}){note}")


print("\nCompare by hand with the Bank of Canada website:")
try:
    for s, label in (("V80691344", "3-month T-bill"), ("BD.CDN.2YR.DQ.YLD", "2-year bond"), ("BD.CDN.10YR.DQ.YLD", "10-year bond")):
        d, v = valet_recent(s)[-1]
        print(f"  {label:15} {v:.2f}% on {d}")
    print("  T-bills: https://www.bankofcanada.ca/rates/interest-rates/t-bill-yields/ (use the secondary-market 3-month row)")
    print("  Bonds:   https://www.bankofcanada.ca/rates/interest-rates/canadian-bonds/")
except Exception as e:
    print(f"  could not fetch: {e}")

fails = sum(s == "FAIL" for s, _, _ in results)
print(f"\n{sum(s == 'PASS' for s, _, _ in results)} pass, {sum(s == 'WARN' for s, _, _ in results)} warn, {fails} fail")
sys.exit(1 if fails else 0)
