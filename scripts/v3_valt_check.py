"""VALT.TO relabel check (NOT a registered run): E1 CA for the shipped engine, strategy "robokit", levels 1-5, and
E8(a) for VALT.TO, with VALT.TO labelled hedged=True in the universe the registered run used. Same dates, seeds and
locked defaults as output/v3. Writes only under output/v3_valt_check/. Its _data/ folder (a copy of vendor prices,
which data/v2 keeps git-ignored) is deleted at the end unless --keep-data is given.

    python -B scripts/v3_valt_check.py            robokit only, levels 1-5: 85 builds
    python -B scripts/v3_valt_check.py --full     the whole registered E1 CA stage (all 13 strategies, Holm, DSR): 697 builds

The archived check (output/v3_valt_check) was made with --full on 9 Oct 2026 (docs/RESEARCH_LOG.md section 13).
    --base shipped                     relabel data/v2/universe.pkl instead of data/v2/universe_v3_evaluated.pkl
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "v3_valt_check"
DATA = OUT / "_data"
# Set before robokit is imported: robokit/config.py reads ROBOKIT_DATA_DIR at import time. The spawned pool
# workers inherit the environment and re-run this top level, so they read the same directory.
os.environ["ROBOKIT_DATA_DIR"] = str(DATA)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]


def main():
    import argparse
    import json
    import shutil

    import pandas as pd

    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--base", choices=("evaluated", "shipped"), default="evaluated")
    ap.add_argument("--keep-data", action="store_true")
    args = ap.parse_args()
    src = ROOT / "data" / "v2"
    if OUT.exists():
        sys.exit(f"{OUT} exists: this check writes to a new folder only")
    reg = json.loads((ROOT / "output" / "v3" / "results.json").read_text(encoding="utf-8"))  # read only
    base = src / ("universe_v3_evaluated.pkl" if args.base == "evaluated" else "universe.pkl")
    DATA.mkdir(parents=True)
    try:
        # returns, FX and bill rates of the registered run, and the base universe with one label changed
        for f in ("close_monthly.pkl", "usdcad_monthly.pkl", "context_monthly.pkl"):
            shutil.copy2(src / f, DATA / f)
        U = pd.read_pickle(base)
        valt = U.yahoo == "VALT.TO"
        assert valt.sum() == 1
        was = bool(U.loc[valt, "hedged"].iloc[0])
        U.loc[valt, "hedged"] = True  # the only change
        U.to_pickle(DATA / "universe.pkl")
        run(args, reg, base, was)
    finally:
        if not args.keep_data:
            shutil.rmtree(DATA, ignore_errors=True)


def run(args, reg, base, was):
    import hashlib
    import json
    import time

    import pandas as pd
    import run_v3_evaluation as RV  # import only: never RV.main(), which writes output/v3

    from robokit import audit as AU
    from robokit import engine as E
    from robokit import evaluation as EV
    from robokit.history import proxies_for

    t0 = time.time()
    # this process reads the relabelled copy (never the snapshot fallback) and the registered returns data
    assert Path(E.DATA_DIR).resolve() == DATA.resolve() and E.data_source() == "local"
    assert E.snapshot_id() == reg["provenance"]["data_snapshot"]  # 00a560f4a6d3
    U = E._load_all()[0]
    hedged = dict(zip(U.yahoo, U.hedged.astype(bool)))
    assert hedged["VALT.TO"]
    shelf, _, _ = E.select_funds(E.Request(market="CA"))
    sleeve = shelf.loc[shelf.ticker == "VALT.TO", "sleeve"].iloc[0]
    chain = proxies_for(sleeve, True, lambda x: hedged.get(x, False))
    assert chain == [("GLD", False)], chain  # GLD unconverted (was CGL-C.TO, then GLD converted to CAD)

    locks = {k: reg["locked_defaults"][k] for k in ("resample", "qis_switch")}  # resample True, qis_switch 0.25
    RV.OUT = OUT  # stage_e1 writes its path CSVs to this module global
    sh = EV.reference_shelf("CA")
    cash = sh.full[sh.cash]
    dates = EV.december_dates(sh.full)
    assert [str(d.date()) for d in dates] == reg["E1"]["CA"]["dates"] and sh.tickers == reg["E1"]["CA"]["shelf"]

    if args.full:  # the registered stage itself
        e1 = RV.stage_e1("CA", locks, dry=False)
        rk = {L: pd.read_csv(OUT / f"e1_CA_robokit_L{L}.csv", index_col=0, parse_dates=True) for L in EV.LEVELS}
    else:  # the same tasks, builds and paths for robokit alone
        res, errors = RV.walk_forward("CA", locks, ["robokit"], lambda s: EV.LEVELS, dates)
        paths = RV.analyse_paths(res["builds"], sh.full, cash, ["robokit"], EV.LEVELS, "E1", "CA")
        rk = {L: paths[("robokit", L)] for L in EV.LEVELS if ("robokit", L) in paths}
        for L, p in rk.items():
            p.to_csv(OUT / f"e1_CA_robokit_L{L}.csv")
        e1 = {"build_errors": errors}
        # the workers must have read the relabelled data too: one build again in this process
        chk = ("CA", str(dates[-1].date()), 3, "robokit", "fixed", RV.locked_extra("robokit", locks))
        w0 = EV.build_at(chk)["weights"]
        w1 = next(b for b in res["builds"] if b["task"] == chk[:5])["weights"]
        assert set(w0) == set(w1) and max(abs(w0[t] - w1[t]) for t in w0) < 1e-9
    if RV.PATH_ERRORS or sorted(rk) != list(EV.LEVELS):
        sys.exit(f"a robokit path is missing: {RV.PATH_ERRORS}")

    # as stage_e1: levels 2-4 together (simultaneous 90%), levels 1 and 5 each alone (90%); block 6, 5000 draws, seed 0
    rd = {"primary": EV.risk_delivery(rk, EV.PRIMARY), "level_1": RV.one_level(rk, 1), "level_5": RV.one_level(rk, 5)}
    desc = {L: RV.described(rk[L], cash) for L in EV.LEVELS}  # sharpe: excess over the cash fund, divisor T, x sqrt 12
    e8 = [r for r in AU.standin_holdout("CA") if r["fund"] == "VALT.TO"]

    old_rd, old_sr = reg["E1"]["CA"]["risk_delivery"], reg["E1"]["CA"]["strategies"]["robokit"]
    print(f"VALT.TO hedged {was} -> True in {base.name}; its stand-ins now {chain}")
    print("E1 CA robokit   realised/target [interval]   registered ratio [interval]   | Sharpe  registered")
    for L in EV.LEVELS:
        part = "primary" if L in EV.PRIMARY else f"level_{L}"
        n, o = rd[part][L], old_rd[part][str(L)]
        so = old_sr.get(str(L), {}).get("sharpe")
        so = "n/a" if so is None else f"{so:.4f}"
        print(
            f"  L{L}  {n['ratio']:.4f} [{n['lo']:.4f}, {n['hi']:.4f}]   {o['ratio']:.4f} [{o['lo']:.4f}, {o['hi']:.4f}]"
            f"   | {desc[L]['sharpe']:.4f}  {so}"
        )
    print(f"  levels 2-4: {rd['primary']['reading']} (registered {old_rd['primary']['reading']})")
    print("  levels 1 and 5: descriptive, each with its own 90% interval (no Sharpe was registered for them)")
    if args.full:
        for b in EV.CONFIRMATORY:
            for L in EV.PRIMARY:
                c, o = e1["comparisons"][b][L], reg["E1"]["CA"]["comparisons"][b][str(L)]
                print(
                    f"  vs {b} L{L}: {c.get('sharpe_other', float('nan')):.4f} ({o['sharpe_other']:.4f}), {c.get('reading')} ({o['reading']})"
                )
    reg_e8 = [r for r in reg["E8"]["standin_holdout"]["CA"]["rows"] if r["fund"] == "VALT.TO"]
    print("E8(a) VALT.TO, registered:", [(r["standin"], round(r["correlation"], 4)) for r in reg_e8])
    for r in e8:
        print(
            f"  now {r['standin']}: {r['months']} months, correlation {r['correlation']:.4f}, tracking error"
            f" {r['tracking_error']:.4f}, vol ratio {r['vol_ratio']:.4f}, mean gap {r['mean_gap_annual']:.4f}"
        )
    out = {
        "note": "not a registered run: E1 CA robokit and E8(a) VALT.TO with VALT.TO relabelled hedged=True",
        "base_universe": base.name,
        "base_universe_md5": hashlib.md5(base.read_bytes()).hexdigest(),
        "valt_hedged_before": was,
        "valt_standins": chain,
        "locks": locks,
        "dates": [str(d.date()) for d in dates],
        "risk_delivery": rd,
        "robokit": desc,
        "E8a_VALT": e8,
        "E1": e1,
        "seconds": round(time.time() - t0),
    }
    tmp = OUT / "results.json.tmp"
    tmp.write_text(json.dumps(RV.clean(out), indent=1), encoding="utf-8")
    os.replace(tmp, OUT / "results.json")
    print("done", out["seconds"], "s, written to", OUT)


if __name__ == "__main__":
    main()
