"""One command to rebuild every dataset on your own machine (python -m robokit refresh).

Order: listings -> categories -> prices (resumable) -> macro, geopolitics -> news -> universe -> caches.
Each step records what it fetched and when; a failed source is reported, never hidden.
"""

from __future__ import annotations

import json
import time

from .config import DATA_DIR, RAW_DIR, ensure_dirs


def refresh(news: bool = True) -> dict:
    ensure_dirs()
    log = {"started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    from .data.listings import build_listings, fetch_yahoo_categories

    L = build_listings()
    log["listings"] = int(len(L))
    for name, ex in (("us", ["NMS", "NGM", "NCM", "NYQ", "ASE", "PCX", "BTS"]), ("ca", ["TOR", "NEO"])):
        try:
            fetch_yahoo_categories(ex).to_csv(RAW_DIR / f"yahoo_categories_{name}.csv", index=False)
        except Exception as e:  # categories are optional enrichment
            log[f"categories_{name}"] = f"failed: {e}"
    import importlib.util
    from pathlib import Path

    from .data.prices import assemble, download_monthly, usdcad_monthly

    spec = importlib.util.spec_from_file_location("fetch", Path(__file__).resolve().parent.parent / "scripts" / "v2_fetch_prices.py")
    fetch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fetch)
    for p in (RAW_DIR / "price_chunks").glob("universe_*.pkl"):
        p.unlink()  # new prices replace the old snapshot
    m = download_monthly(fetch.candidate_tickers(L), chunk=100, tag="universe")
    close, volume = assemble("universe")
    close.to_pickle(DATA_DIR / "close_monthly.pkl")
    volume.to_pickle(DATA_DIR / "volume_monthly.pkl")
    usdcad_monthly().to_pickle(DATA_DIR / "usdcad_monthly.pkl")
    log["prices"] = {"series": int(close.shape[1]), "through": str(close.index.max().date()), "failed_chunks": m.get("failed_chunks", [])}
    from .data.context import build_context, build_news

    ctx = build_context(include_news=False)
    log["context"] = ctx["meta"]["status"]
    if news:
        log["news"] = build_news().get("_meta", {}).get("status")
    from .universe import build_universe

    U = build_universe(save=True)
    log["eligible"] = int(U.eligible.sum())
    from . import engine

    engine.reload()
    engine.snapshot_id.cache_clear()
    log["finished"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (DATA_DIR / "refresh_log.json").write_text(json.dumps(log, indent=1, default=str))
    print(json.dumps(log, indent=1, default=str))
    return log
