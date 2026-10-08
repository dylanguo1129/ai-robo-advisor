"""Export the data the web page needs (python -m robokit bundle).

Files written to web/data/:
  core.json   meta, disclosures, questions, glossary, sleeves and priors, planning
              assumptions, stress windows, market context, news, back-test summary,
              and reference results from the Python engine for the parity test
  ca.json     Canadian universe (every listing, with eligibility and reasons) and
              monthly returns of eligible funds and proxies, 2000 onward
  us.json     the same for the US market

Returns are stored as int16 in units of 0.5 basis points (0.00005), base64,
one block per fund with its first month; -32768 marks a missing month. That
keeps 2,600 funds x 320 months under 2 MB per file.

Licensing (docs/research/data-sources.md): prices and listings come from
Yahoo, TMX and Nasdaq, which allow personal use. The bundle is for the team's
private artifact; a public launch needs licensed data (data/README.md, docs/research/gap-public-data-licensing.md).
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from . import __version__, cma, glossary
from . import profile as prof
from .config import OUTPUT_DIR, ROOT
from .engine import ONE_FUND, SLEEVE_CAPS, Request, _load, build_portfolio, returns_in, risk_free, snapshot_id, us_rates
from .history import PROXIES, proxies_for
from .projection import DISCLOSURE as PROJ_DISCLOSURE
from .shelf import PRIOR, candidates, prior_share, sleeves_for
from .signals import market_flags, news_digest
from .stress import SCENARIOS
from .tools import DISCLOSURE

SCALE = 20000.0  # 1 unit = 0.5 bp
START = "2000-01-31"
WEB_DATA = ROOT / "web" / "data"


def _enc(arr: np.ndarray) -> str:
    q = np.where(np.isnan(arr), -32768, np.clip(np.round(arr * SCALE), -32767, 32767)).astype("<i2")
    return base64.b64encode(q.tobytes()).decode("ascii")


def _num(v, nd=6):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if not np.isfinite(f) else round(f, nd)


def _universe_rows(U: pd.DataFrame, market: str) -> list:
    cols = [
        "yahoo",
        "symbol",
        "name",
        "exchange",
        "currency",
        "asset_class",
        "region",
        "theme",
        "sector",
        "strategy",
        "hedged",
        "leverage",
        "issuer",
        "mer",
        "aum",
        "history_months",
        "vol_3y",
        "ret_1y",
        "ret_3y",
        "ret_5y",
        "max_drawdown",
        "dividend_yield",
        "dollar_volume",
        "eligible",
        "excluded_because",
        "satellite_only",
        "esg",
        "why",
        "derivatives",
        "single_stock",
        "cdr",
        "market",
        "first_month",
        "last_close",
        "last_close_date",
    ]
    u = U[U.market == market]
    rows = []
    for _, r in u.iterrows():
        row = []
        for c in cols:
            v = r[c]
            if isinstance(v, pd.Timestamp):
                row.append(str(v.date()))
            elif isinstance(v, (bool, np.bool_)):
                row.append(bool(v))
            elif isinstance(v, (int, np.integer)):
                row.append(int(v))
            elif isinstance(v, (float, np.floating)):
                row.append(
                    _num(
                        v,
                        6
                        if c in ("mer", "vol_3y", "ret_1y", "ret_3y", "ret_5y", "max_drawdown", "dividend_yield")
                        else 4
                        if c == "last_close"
                        else 2,
                    )
                )
            elif v is None or (isinstance(v, float) and np.isnan(v)):
                row.append(None)
            else:
                row.append(str(v) if str(v) != "nan" else None)
        rows.append(row)
    return {"columns": cols, "rows": rows}


def _returns_block(R: pd.DataFrame, tickers: list[str]) -> dict:
    R = R[R.index >= pd.Timestamp(START)]
    months = [d.strftime("%Y-%m") for d in R.index]
    series = {}
    for t in tickers:
        if t not in R.columns:
            continue
        s = R[t]
        fv = s.first_valid_index()
        if fv is None:
            continue
        s = s.loc[fv:]
        series[t] = {"start": months.index(fv.strftime("%Y-%m")), "data": _enc(s.to_numpy(dtype=float))}
    return {"months": months, "scale": SCALE, "missing": -32768, "series": series}


def _sleeves(U: pd.DataFrame, market: str) -> list:
    out = []
    hedged = dict(zip(U.yahoo, U.hedged.astype(bool)))
    lh = lambda x: hedged.get(x, False)  # noqa: E731
    for s in sleeves_for(market):
        c = candidates(U, s)
        c_esg = candidates(U, s, prefer_esg=True)
        out.append(
            {
                "key": s.key,
                "label": s.label,
                "plain": s.plain,
                "asset_class": s.asset_class,
                "regions": list(s.regions),
                "role": s.role,
                "prior": prior_share(market, s.key),
                "cap": SLEEVE_CAPS.get(s.key),
                "hedged": s.hedged,
                "rule": {"include": s.include, "exclude": s.exclude},
                "candidates": list(c["yahoo"].head(8)),
                "candidates_esg": list(c_esg["yahoo"].head(8)),
                "proxies": [{"ticker": t, "convert": cv} for t, cv in proxies_for(s.key, False, lh)],
                "proxies_hedged": [{"ticker": t, "convert": cv} for t, cv in proxies_for(s.key, True, lh)],
            }
        )
    return out


def _peer_medians(R: pd.DataFrame, U: pd.DataFrame) -> dict:
    """Scenario returns of the median eligible fund per (market, asset class, region) and per asset class:
    stand-ins for young funds, in each portfolio currency ({"CA": ... in CAD, "US": ... in USD})."""
    return {m: _peer_medians_in(returns_in(m, list(R.columns)), U) for m in ("CA", "US")}


def _peer_medians_in(R: pd.DataFrame, U: pd.DataFrame) -> dict:
    out = {}
    E = U[U.eligible]
    for sc in SCENARIOS:
        s, e = pd.Timestamp(sc["start"]), pd.Timestamp(sc["end"])
        win = R.loc[(R.index > s) & (R.index <= e)]
        full = win.notna().all()
        ep = (1 + win.fillna(0)).prod() - 1
        d = {}
        for (mk, ac, rg), g in E.groupby(["market", "asset_class", "region"]):
            peers = [p for p in g.yahoo if p in win.columns and bool(full.get(p, False))]
            if peers:
                d[f"{mk}|{ac}|{rg}"] = round(float(np.median(ep[peers])), 5)
        for ac, g in E.groupby("asset_class"):
            peers = [p for p in g.yahoo if p in win.columns and bool(full.get(p, False))]
            if peers:
                d[f"*|{ac}|*"] = round(float(np.median(ep[peers])), 5)
        out[sc["key"]] = d
    return out


def reference_profiles(n: int = 400, seed: int = 5) -> list:
    """Random self-check answer sets scored in Python, for the JavaScript scorer parity test."""
    import random

    rnd = random.Random(seed)
    ids = [i for i in prof.ITEMS if i["options"]]
    out = []
    for _ in range(n):
        a = {}
        for it in ids:
            if rnd.random() < 0.85:
                a[it["id"]] = rnd.choice(it["options"])["value"]
        out.append({"answers": a, "result": prof.score(a).to_dict()})
    return out


def reference_cases() -> list:
    """Python results with resampling off, for the JavaScript parity test."""
    cases = [
        dict(market="CA", risk_level=3),
        dict(market="CA", risk_level=1),
        dict(market="CA", risk_level=5),
        dict(market="US", risk_level=2),
        dict(market="US", risk_level=4),
        dict(market="CA", risk_level=4, satellites=["XIT.TO", "ZEB.TO"]),
        dict(
            market="US", risk_level=3, views=[{"type": "relative", "long": "GLDM", "short": "BND", "difference": 0.02, "confidence": 0.6}]
        ),
        dict(
            market="CA",
            risk_level=3,
            views=[{"type": "relative", "long": "XIC.TO", "short": "ZAG.TO", "difference": 0.03, "confidence": 0.8}],
        ),
        dict(market="CA", risk_level=3, max_weight=0.05, on_infeasible="relax"),
        dict(market="CA", target_vol=0.03),
        # review regressions (v3): both engines must agree on the hard cases too
        dict(market="CA", risk_level=2, sleeves=["ca_agg_bond", "ca_short_bond", "ca_global_bond", "ca_cash"]),
        dict(
            market="CA",
            risk_level=4,
            max_weight=0.131,
            views=[{"type": "relative", "long": "XIC.TO", "short": "ZAG.TO", "difference": 0.03, "confidence": 0.8}],
        ),
        dict(market="CA", risk_level=4, max_weight=0.3, min_weight=0.2),
        dict(market="US", risk_level=5, max_weight=0.3, min_weight=0.1),
        dict(market="CA", risk_level=5, satellites=["XIT.TO"], minimums={"XIT.TO": 0.15}, satellite_max_each=0.10, on_infeasible="relax"),
        dict(
            market="CA",
            risk_level=5,
            views=[{"type": "relative", "long": "VFV.TO", "short": "XIC.TO", "difference": 0.02, "confidence": 0.5}],
        ),
        dict(market="CA", risk_level=3, max_weight=0.094, on_infeasible="relax"),
        dict(
            market="CA",
            risk_level=2.5,
            max_weight=0.1,
            min_weight=0.2,
            views=[{"type": "relative", "long": "XIC.TO", "short": "ZAG.TO", "difference": 0.03, "confidence": 0.8}],
        ),
        dict(market="CA", risk_level=3, hedge_us_equity=True),
        dict(market="CA", risk_level=4, swaps={"ca_us_equity": "VSP.TO"}),
        dict(market="US", risk_level=4, swaps={"us_equity": "TQQQ", "us_reit": "NOPE"}),
        dict(market="CA", risk_level=4, fixed_weights={"VFV.TO": 0.4, "XIC.TO": 0.3, "ZAG.TO": 0.3}),
        dict(market="US", risk_level=5, satellites=["QQQ", "SCHD", "BITO"]),
        dict(market="US", risk_level=4, satellites=["BITO"], minimums={"BITO": 0.05}),
    ]
    out = []
    for c in cases:
        p = build_portfolio(Request(**c, resample=False))
        out.append(
            {
                "request": c,
                "weights": {h["ticker"]: h["weight"] for h in p["holdings"]},
                "volatility": p["stats"]["volatility"],
                "lambda": p["risk"]["lambda"],
                "target_vol": p["risk"]["target_vol"],
                "window": p["window"],
                "planning_return_net": {h["ticker"]: h["planning_return_net"] for h in p["holdings"]},
                "stress": {s["scenario"]: s["portfolio_return"] for s in p["stress"]},
                "notes": p["notes"],
                "checks": [c_["id"] for c_ in p["checks"]],
            }
        )
    return out


def export_bundle(with_reference: bool = True) -> dict:
    U, R, fx, ctx = _load()
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    proxies = sorted({t for v in PROXIES.values() for t, _ in v if not t.startswith("RATE:")})
    rates = {}
    for col in ("V80691344", "^IRX"):
        s = ctx[col].dropna() / 100.0
        s = s[s.index >= pd.Timestamp(START) - pd.offsets.MonthEnd(1)]
        rates[col] = {"months": [d.strftime("%Y-%m") for d in s.index], "values": [round(float(v), 6) for v in s]}
    fxs = fx[fx.index >= pd.Timestamp(START) - pd.offsets.MonthEnd(1)]
    sizes = {}
    for market in ("CA", "US"):
        elig = list(U[(U.market == market) & U.eligible].yahoo)
        payload = {
            "market": market,
            "universe": _universe_rows(U, market),
            "returns": _returns_block(R, sorted(set(elig) | set(proxies))),
            "sleeves": _sleeves(U, market),
            "prior": PRIOR[market],
        }
        p = WEB_DATA / f"{market.lower()}.json"
        p.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        sizes[market] = p.stat().st_size
    bt = OUTPUT_DIR / "backtest_v2_summary.json"
    core = {
        "meta": {
            "engine_version": __version__,
            "data_snapshot": snapshot_id(),
            "prices_through": str(R.index.max().date()),
            "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sources": {
                "listings": "Nasdaq Trader symbol directory; TMX Money ETF data; Yahoo Finance screener",
                "prices": "Yahoo Finance monthly adjusted closes (total return)",
                "rates": "Bank of Canada Valet (3-month T-bill); Yahoo ^IRX (US 13-week bill)",
                "fx": "Yahoo CAD=X",
                "context": "Bank of Canada, Yahoo, FRED, Caldara-Iacoviello GPR, Baker-Bloom-Davis EPU, GDELT",
            },
            "licensing": "Prices and listings are licensed for personal use. This snapshot is for private, educational use.",
        },
        "disclosure": DISCLOSURE,
        "projection_disclosure": PROJ_DISCLOSURE,
        "questions": prof.ITEMS,
        "levels": {k: {"en": v} for k, v in prof.LEVELS.items()},
        "glossary": {k: {"en": {"term": v[0], "definition": v[1]}} for k, v in glossary.TERMS.items()},
        "delta": 2.5,
        "sleeve_caps": SLEEVE_CAPS,
        "cma": {"fpc_2026": cma.FPC_2026, "fpc_source": cma.FPC_SOURCE, "us_rates": us_rates()},
        "risk_free": {m: {"rate": risk_free(m)[0], "source": risk_free(m)[1]} for m in ("CA", "US")},
        "rates": rates,
        "fx": {"months": [d.strftime("%Y-%m") for d in fxs.index], "values": [round(float(v), 6) for v in fxs]},
        "scenarios": SCENARIOS,
        "scenario_peers": _peer_medians(R, U),
        "one_fund": {m: [[t, sh] for t, sh in ONE_FUND[m]] for m in ONE_FUND},
        "context": {"flags": market_flags(), "news": news_digest()},
        "backtest": json.loads(bt.read_text()) if bt.exists() else None,
        "reference_cases": reference_cases() if with_reference else [],
    }
    (WEB_DATA / "core.json").write_text(json.dumps(core, separators=(",", ":"), default=str), encoding="utf-8")
    if with_reference:  # test fixture only: not part of the published page data
        (WEB_DATA.parent / "test_profiles.json").write_text(json.dumps(reference_profiles(), separators=(",", ":")), encoding="utf-8")
    sizes["core"] = (WEB_DATA / "core.json").stat().st_size
    return sizes
