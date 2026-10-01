"""Run the pre-registered v2 walk-forward back-test (docs/RESEARCH_LOG.md section 6). Run once."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from robokit.backtest import walk_forward
from robokit.config import OUTPUT_DIR, ensure_dirs

if __name__ == "__main__":
    ensure_dirs()
    t0 = time.time()
    summary = {}
    for market in ("CA", "US"):
        res = walk_forward(market)
        res["stats"].to_csv(OUTPUT_DIR / f"backtest_{market}_stats.csv", index=False)
        res["subperiods"].to_csv(OUTPUT_DIR / f"backtest_{market}_subperiods.csv", index=False)
        res["paired"].to_csv(OUTPUT_DIR / f"backtest_{market}_paired.csv", index=False)
        res["monthly_net"].to_csv(OUTPUT_DIR / f"backtest_{market}_monthly_net.csv")
        res["weights"].to_csv(OUTPUT_DIR / f"backtest_{market}_weights.csv", index=False)
        summary[market] = {
            "tickers": res["tickers"],
            "history": res["history"],
            "stats": res["stats"].round(5).to_dict(orient="records"),
            "subperiods": res["subperiods"].round(5).to_dict(orient="records"),
            "paired": res["paired"].round(5).to_dict(orient="records"),
        }
        print(market, f"{time.time() - t0:.0f}s", flush=True)
        print(res["stats"].round(4).to_string(index=False), flush=True)
        print(res["paired"].round(4).to_string(index=False), flush=True)
    (OUTPUT_DIR / "backtest_v2_summary.json").write_text(json.dumps(summary, indent=1, default=str))
