"""The paper's numbers: output/v3/results.json plus a few values derived from it, and facts about the data snapshot
the run used (checked to be the same snapshot), written to docs/paper/build/paper_numbers.json.

    python scripts/paper/derive.py

Every derived value is a plain function of results.json or of the snapshot, defined here, so a reader can check it.
build_paper.py reads this file (PAPER_RESULTS) instead of results.json.
"""

from __future__ import annotations

import json
import os
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from robokit import engine as E  # noqa: E402
from robokit.engine import Request, select_funds  # noqa: E402

RESULTS = Path(os.environ.get("V3_RESULTS", ROOT / "output" / "v3" / "results.json"))
OUT = Path(os.environ.get("V3_NUMBERS", ROOT / "docs" / "paper" / "build" / "paper_numbers.json"))


def main():
    res = json.loads(RESULTS.read_text(encoding="utf-8"))
    snap = E.snapshot_id()
    if snap != res["provenance"]["data_snapshot"]:
        sys.exit(f"data snapshot {snap} is not the run's {res['provenance']['data_snapshot']}")
    U = E._load()[0]
    d = {"data": {}, "e3": {}, "e6": {}, "e8": {}}
    for m in ("CA", "US"):
        u = U[U.market == m]
        shelf, core, _ = select_funds(Request(market=m))
        d["data"][m] = {"listed": int(len(u)), "eligible": int(u.eligible.sum()), "shelf_funds": int(len(core)), "shelf": list(core)}
    d["data"]["eligible_total"] = d["data"]["CA"]["eligible"] + d["data"]["US"]["eligible"]
    d["data"]["as_of"] = str(E._load()[1].index.max().date())
    # E3: losses relative to robokit, level 3, 180 months
    for w in "abc":
        s = res["E3"]["summary"][w]["3"]["180"]
        d["e3"][w] = {m: s[m]["loss_bp"] - s["robokit"]["loss_bp"] for m in s}  # method minus robokit (positive: worse)
        d["e3"][w]["static_mix_advantage"] = s["robokit"]["loss_bp"] - s["static_mix"]["loss_bp"]  # positive: static mix better
    # E6: shipped bands against the ideal and monthly rules, per account
    for m in ("CA", "US"):
        for acct, a in res["E6"][m]["accounts"].items():
            d["e6"].setdefault(m, {})[acct] = {
                "bands_minus_ideal_return": a["bands"]["ann_return"] - a["ideal"]["ann_return"],
                "bands_cost_share_of_monthly": a["bands"]["total_cost"] / a["monthly"]["total_cost"],
            }
        shares = res["E6"][m]["largest_order_share_of_daily_volume"]
        over = sorted(t for t, v in shares.items() if v is not None and v > 0.01)
        d["e6"][m]["funds_over_1pct_adv"] = over
        d["e6"][m]["funds_over_1pct_adv_text"] = (", ".join(over[:-1]) + " and " + over[-1]) if len(over) > 1 else (over[0] if over else "none")
        d["e6"][m]["funds_over_1pct_adv_count"] = len(over)
        d["e6"][m]["max_adv_share"] = max(v for v in shares.values() if v is not None)
    # E8(b): medians across the twenty funds
    for m in ("CA", "US"):
        rows = res["E8"]["backfill_holdout"][m]["rows"]
        d["e8"][m] = {
            "median_corr": st.median(r["correlation"] for r in rows),
            "median_te": st.median(r["tracking_error"] for r in rows),
            "median_home_te": st.median(r["home_fund_tracking_error"] for r in rows),
            "funds": len(rows),
        }
    # E8(a): the stand-ins by name, and their median correlation with the funds they stand in for
    rows_a = {m: res["E8"]["standin_holdout"][m]["rows"] for m in ("CA", "US")}
    allrows = rows_a["CA"] + rows_a["US"]
    d["e8"]["standin_median_corr"] = st.median(r["correlation"] for r in allrows)
    d["e8"]["standin_rows"] = len(allrows)
    pick = {(r["fund"], r["standin"]): r for r in allrows}
    d["e8"]["bndx_bwx_corr"] = pick[("BNDX", "BWX")]["correlation"]
    d["e8"]["vfv_spy_corr"] = pick[("VFV.TO", "SPY")]["correlation"]
    d["e8"]["below_gate"] = sorted(f"{r['fund']} / {r['standin']}" for r in allrows if r["correlation"] < 0.8)
    # E1: how many builds of the two cash-mixed benchmarks there were (each date, levels 2-4)
    d["e1"] = {m: {"cash_mixed_builds": 2 * 3 * len(res["E1"][m]["dates"])} for m in ("CA", "US")}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({**res, "derived": d}, indent=1, default=str), encoding="utf-8")
    print("written", OUT, "| snapshot", snap)


if __name__ == "__main__":
    main()
