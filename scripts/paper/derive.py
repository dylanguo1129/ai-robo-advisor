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

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from robokit import engine as E  # noqa: E402
from robokit.config import DATA_DIR  # noqa: E402
from robokit.engine import Request, select_funds  # noqa: E402

RESULTS = Path(os.environ.get("V3_RESULTS", ROOT / "output" / "v3" / "results.json"))
OUT = Path(os.environ.get("V3_NUMBERS", ROOT / "docs" / "paper" / "build" / "paper_numbers.json"))


def _and(items: list[str]) -> str:
    return "none" if not items else items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _targets(path: Path) -> pd.Series:
    """The target in force at each estimation date: the path's first month after it (January)."""
    s = pd.read_csv(path, index_col=0, parse_dates=True)["target"]
    s = s[s.index.month == 1]
    s.index = s.index.year - 1  # the December it was set
    return s


def main():
    res = json.loads(RESULTS.read_text(encoding="utf-8"))
    snap = E.snapshot_id()
    if snap != res["provenance"]["data_snapshot"]:
        sys.exit(f"data snapshot {snap} is not the run's {res['provenance']['data_snapshot']}")
    # the fund list as the run saw it: labels corrected after the run (docs/DECISIONS.md, second bug hunt) changed some
    # eligibility counts, though none of the evaluated picks, so the counts come from the universe archived with the run
    eval_u = DATA_DIR / "universe_v3_evaluated.pkl"
    if not eval_u.exists():
        sys.exit(f"{eval_u} (the universe the registered run used) is missing")
    U = pd.read_pickle(eval_u)
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
        d["e6"][m]["funds_over_1pct_adv_text"] = (
            (", ".join(over[:-1]) + " and " + over[-1]) if len(over) > 1 else (over[0] if over else "none")
        )
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
    # E5: the Monte Carlo standard error at 5,000 paths that the square-root law implies from the one measured at 2,000
    d["e5"] = {
        m: {L: v["2000"]["se"] * (2000 / 5000) ** 0.5 for L, v in res["E5"][m]["today"]["projection_se"].items()} for m in ("CA", "US")
    }
    # The printed 95% intervals are equal-tailed (the registered method); the two-sided p inverts the symmetric
    # studentised interval, so the two can disagree. The confirmatory rows where they do, in E1 and E2.
    name = {"static_mix": "static mix", "textbook_60": "textbook optimizer", "erc_cash": "equal risk contribution", "minvar_cash": "minimum variance"}
    rows, dis = 0, []
    for ex in ("E1", "E2"):
        for m in ("CA", "US"):
            for b, by_level in res[ex][m]["comparisons"].items():
                for L, c in by_level.items():
                    rows += 1
                    lo, hi = c["ci95_annual"]
                    if (c["p_two_sided"] < 0.05) != (lo > 0 or hi < 0):
                        dis.append(f"{ex} {'Canada' if m == 'CA' else 'US'}, {name[b]} at level {L}")
    d["intervals"] = {"rows": rows, "disagree_count": len(dis), "disagree": dis, "disagree_text": _and(dis)}
    # The textbook optimizer's target (its own 60 months) against Robo-Kit's (the common window): the 'target' column of
    # the registered paths, one value per estimation date (the January after it), in volatility points
    d["textbook_target"] = {}
    for ex in ("e1", "e2"):
        for m in ("CA", "US"):
            for L in ("2", "3", "4"):
                rk, tb = (_targets(RESULTS.parent / f"{ex}_{m}_{s}_L{L}.csv") for s in ("robokit", "textbook_60"))
                j = pd.concat([rk, tb], axis=1, keys=["rk", "tb"]).dropna()
                gap = (j.tb - j.rk) * 100
                d["textbook_target"].setdefault(ex, {}).setdefault(m, {})[L] = {
                    "dates": int(len(j)),
                    "mean_gap_points": float(gap.mean()),
                    "mean_abs_gap_points": float(gap.abs().mean()),
                    "max_rel_gap": float(((j.tb - j.rk).abs() / j.rk).max()),
                    "mean_robokit": float(j.rk.mean()),
                    "mean_textbook": float(j.tb.mean()),
                }
    tt = [v for ex in d["textbook_target"].values() for mk in ex.values() for v in mk.values()]
    d["textbook_target"]["max_rel_gap_all"] = max(v["max_rel_gap"] for v in tt)
    d["textbook_target"]["max_mean_abs_gap_all"] = max(v["mean_abs_gap_points"] for v in tt)
    d["provenance"] = {"short_commit": res["provenance"]["commit"][:7]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({**res, "derived": d}, indent=1, default=str), encoding="utf-8")
    print("written", OUT, "| snapshot", snap)


if __name__ == "__main__":
    main()
