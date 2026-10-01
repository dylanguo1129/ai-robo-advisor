"""Run from the committed web snapshot when no local data has been downloaded yet.

`python -m robokit refresh` builds the full dataset on the user's machine
(15-30 minutes). Until then, the engine, the tools and the MCP server read
the dated snapshot that ships with the repo for the web page (web/data/):
every listing with its classification and reasons, and monthly returns for
every eligible fund and every proxy since 2000. Results say which data they
used (`data_status`).
"""

from __future__ import annotations

import base64
import json
from functools import lru_cache

import numpy as np
import pandas as pd

from .config import ROOT

WEB_DATA = ROOT / "web" / "data"


def available() -> bool:
    return (WEB_DATA / "core.json").exists() and (WEB_DATA / "ca.json").exists() and (WEB_DATA / "us.json").exists()


@lru_cache(maxsize=1)
def core() -> dict:
    return json.loads((WEB_DATA / "core.json").read_text(encoding="utf-8"))


def _decode(block: dict) -> pd.DataFrame:
    months = pd.to_datetime(block["months"]) + pd.offsets.MonthEnd(0)
    cols = {}
    for t, s in block["series"].items():
        q = np.frombuffer(base64.b64decode(s["data"]), dtype="<i2").astype(float)
        a = np.full(len(months), np.nan)
        vals = np.where(q == block["missing"], np.nan, q / block["scale"])
        a[s["start"] : s["start"] + len(vals)] = vals
        cols[t] = a
    return pd.DataFrame(cols, index=months)


@lru_cache(maxsize=1)
def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.DataFrame]:
    """(universe, monthly returns, USDCAD, context) built from web/data."""
    frames, rets = [], []
    for code in ("ca", "us"):
        m = json.loads((WEB_DATA / f"{code}.json").read_text(encoding="utf-8"))
        u = pd.DataFrame(m["universe"]["rows"], columns=m["universe"]["columns"])
        u["market"] = m["market"]
        frames.append(u)
        rets.append(_decode(m["returns"]))
    U = pd.concat(frames, ignore_index=True)
    U["inverse"] = U["leverage"] < 0
    U["crypto"] = U["asset_class"] == "Crypto"
    U["target_date"] = False
    for c in ("vol_5y", "ret_10y", "pe", "pb", "inception", "first_month", "last_close", "last_close_date", "yahoo_category", "tmx_style"):
        if c not in U.columns:  # older bundles do not ship these
            U[c] = np.nan
    U["stale"] = False
    U["has_prices"] = True
    U["excluded_because"] = U["excluded_because"].fillna("")
    for c in ("theme", "sector", "derivatives", "why"):
        U[c] = U[c].fillna("")
    R = pd.concat(rets, axis=1)
    R = R.loc[:, ~R.columns.duplicated()]
    c = core()
    fx = pd.Series(c["fx"]["values"], index=pd.to_datetime(c["fx"]["months"]) + pd.offsets.MonthEnd(0), name="USDCAD")
    ctx = pd.DataFrame(index=R.index.union(fx.index))
    for col, block in c["rates"].items():
        s = pd.Series(block["values"], index=pd.to_datetime(block["months"]) + pd.offsets.MonthEnd(0)) * 100.0
        ctx[col] = s
    us = c.get("cma", {}).get("us_rates", {})
    if "note5" in us:
        ctx.loc[ctx.index.max(), "^FVX"] = us["note5"] * 100.0
    return U, R, fx, ctx
