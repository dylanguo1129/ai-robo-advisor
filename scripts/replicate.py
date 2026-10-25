"""Re-run the numbers our reports publish, from a fresh clone, and check them against what is committed.

    python scripts/replicate.py tables               the optimizer tables of both reports (about 2 minutes, no setup)
    python scripts/replicate.py snapshot             rebuild web/data/ from the archived data in a temporary folder and
                                                     compare it with the committed snapshot (about 5 minutes)
    python scripts/replicate.py evaluation           re-run part of the registered evaluation at its own commit and
                                                     compare it value by value with output/v3/ (see REPRODUCE.md)
    python scripts/replicate.py evaluation --full    the whole registered evaluation (hours)
    python scripts/replicate.py data                 unpack the archived data into data/v2/ (for the full test suite)

Every command reads the data from data/replication/ (checked against MANIFEST.json, SHA-256), never from the network,
and writes only to a temporary folder (or data/v2/ for `data`). REPRODUCE.md explains what each check shows."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
REPL = ROOT / "data" / "replication"
MANIFEST = REPL / "MANIFEST.json"
RESULTS = ROOT / "output" / "v3" / "results.json"
SNAPSHOT = "00a560f4a6d3"
LEVELS = (1, 2, 3, 4, 5)
SETTINGS = {"low": 4, "mid": 3, "high": 2}  # the brief's risk aversion: low aversion = level 4, high aversion = level 2


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def archive_files() -> dict[str, bytes]:
    """The archived files by name, each checked against MANIFEST.json (the archive first, then every file)."""
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    arc = REPL / m["archive"]["file"]
    raw = arc.read_bytes()
    if sha256(raw) != m["archive"]["sha256"]:
        sys.exit(f"{arc.name} does not match MANIFEST.json (SHA-256); re-clone the repository")
    out = {}
    with tarfile.open(arc, "r:xz") as tf:
        for member in tf.getmembers():
            if member.name not in m["files"] or not member.isfile():
                sys.exit(f"unexpected entry in the archive: {member.name}")
            data = tf.extractfile(member).read()
            if sha256(data) != m["files"][member.name]["sha256"]:
                sys.exit(f"{member.name} does not match MANIFEST.json (SHA-256)")
            out[member.name] = data
    missing = set(m["files"]) - set(out)
    if missing:
        sys.exit(f"missing from the archive: {sorted(missing)}")
    return out


def data_dir(dest: Path, evaluated: bool = False) -> Path:
    """A data folder for ROBOKIT_DATA_DIR. evaluated: universe.pkl is the universe the registered evaluation used."""
    dest.mkdir(parents=True, exist_ok=True)
    files = archive_files()
    for name, data in files.items():
        if name.startswith("v2/"):
            (dest / name[3:]).write_bytes(data)
    if evaluated:
        (dest / "universe.pkl").write_bytes(files["v2/universe_v3_evaluated.pkl"])
    return dest


def run_child(args: list[str], env_data: Path, cwd: Path = ROOT) -> subprocess.CompletedProcess:
    env = {**os.environ, "ROBOKIT_DATA_DIR": str(env_data), "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, *args], cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8")


# ---------------------------------------------------------------- comparison


def close(a, b, rel: float = 1e-9, abs_: float = 1e-12) -> bool:
    if isinstance(a, bool) or isinstance(b, bool) or not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return a == b
    if math.isnan(a) or math.isnan(b):
        return math.isnan(a) and math.isnan(b)
    return abs(a - b) <= abs_ + rel * max(abs(a), abs(b))


def compare(a, b, path: str = "", out: dict | None = None) -> dict:
    """Value-by-value comparison of two JSON trees: counts, exact matches, the largest difference, and mismatches."""
    out = out if out is not None else {"values": 0, "exact": 0, "max_abs": 0.0, "mismatches": []}
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out["mismatches"].append((f"{path}/{k}", "missing" if k not in a else a[k], "missing" if k not in b else b[k]))
            else:
                compare(a[k], b[k], f"{path}/{k}", out)
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            compare(x, y, f"{path}[{i}]", out)
    else:
        out["values"] += 1
        if a == b:
            out["exact"] += 1
        elif close(a, b):
            out["max_abs"] = max(out["max_abs"], abs(a - b))
        else:
            out["mismatches"].append((path, a, b))
    return out


def compare_csv(new: Path, ref: Path) -> dict:
    import pandas as pd

    a, b = pd.read_csv(new, index_col=0), pd.read_csv(ref, index_col=0)
    if list(a.index) != list(b.index) or list(a.columns) != list(b.columns):
        return {"file": ref.name, "ok": False, "why": "rows or columns differ"}
    d = (a - b).abs().to_numpy()
    scale = b.abs().to_numpy()
    ok = bool(((d <= 1e-12 + 1e-9 * scale) | (a.isna() & b.isna()).to_numpy()).all())
    return {
        "file": ref.name,
        "ok": ok,
        "identical_bytes": new.read_bytes().replace(b"\r\n", b"\n") == ref.read_bytes().replace(b"\r\n", b"\n"),  # Windows line ends aside
        "max_abs": float(pd.DataFrame(d).max().max()),
    }


def report(name: str, ok: bool, detail: str) -> bool:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}: {detail}")
    return ok


# ---------------------------------------------------------------- tables


def build_tables() -> dict:
    """The CA level 1-5 builds the report tables come from, in whatever data mode this process uses."""
    from robokit import engine as E
    from robokit.engine import Request, build_portfolio

    out = {"source": E.data_source(), "snapshot": E.snapshot_id(), "levels": {}}
    for L in LEVELS:
        r = build_portfolio(Request(market="CA", risk_level=L, amount=10_000))
        gfc = next(s for s in r["stress"] if s["key"] == "gfc")
        ac = r["mix"]["asset_class"]
        out["levels"][str(L)] = {
            "weights": {h["ticker"]: h["weight"] for h in r["holdings"]},
            "lambda": r["risk"]["lambda"],
            "target_vol": r["risk"]["target_vol"],
            "achieved_vol": r["risk"]["achieved_vol"],
            "effective_holdings": r["stats"]["effective_holdings"],
            "mix": [ac.get("Equity", 0), ac.get("Fixed income", 0), ac.get("Cash", 0), ac.get("Real estate", 0) + ac.get("Commodity", 0)],
            "typical_year": r["projection"]["median_annual_return"],
            "bad_year": r["projection"]["one_year"]["p5"],
            "replay_2008": gfc["portfolio_return"],
            "fees_per_10000": r["stats"]["fee_per_10k"],
            "rating": r["stats"]["ni81_102"]["rating"],
        }
    return out


def child_tables() -> None:
    """(Internal) build_tables() as JSON on stdout, for a child process with its own ROBOKIT_DATA_DIR."""
    print(json.dumps(build_tables()))


WEIGHT_SLACK = 0.02  # percentage points: the committed snapshot stores each monthly return to the nearest half basis point


def check_tables(got: dict, want: dict, label: str, slack: float = 0.0) -> bool:
    """The printed tables against the engine: a printed number matches when the engine's value rounds to it (within
    half a unit of the last printed digit). ``slack`` widens that for fund weights only (the committed snapshot)."""
    bad, near, checked = [], [], [0]

    def chk(where, value, printed, decimals, scale=100.0, extra=0.0):
        checked[0] += 1
        half = 0.5 * 10**-decimals + 1e-9
        if printed is None:
            if value not in (None, 0) and abs(value) * scale >= half:
                (near if abs(value) * scale < half + extra else bad).append(f"{where}: engine {value * scale:.4f}, report shows none")
            return
        if value is None:
            bad.append(f"{where}: engine none, report {printed}")
        elif abs(value * scale - printed) > half:
            gap = abs(value * scale - printed)
            (near if gap <= half + extra else bad).append(f"{where}: engine {value * scale:.4f}, report {printed}")

    for L in LEVELS:
        g, s = got["levels"][str(L)], str(L)
        tickers = set(g["weights"]) | set(want["weights_pct"][s])
        for t in sorted(tickers):
            chk(f"Table 7 level {L} {t}", g["weights"].get(t), want["weights_pct"][s].get(t), 2, extra=slack)
        chk(f"Table 7 level {L} lambda", g["lambda"], want["level_rows"]["lambda"][s], 2, 1.0)
        chk(f"Table 7 level {L} volatility", g["achieved_vol"], want["level_rows"]["volatility_pct"][s], 2)
        chk(f"Table 7 level {L} effective holdings", g["effective_holdings"], want["level_rows"]["effective_holdings"][s], 2, 1.0)
        lv = want["levels"][s]
        chk(f"Table 4 level {L} target", g["target_vol"], lv["target_pct"], 2)
        chk(f"Table 4 level {L} lambda", g["lambda"], lv["lambda"], 2, 1.0)
        chk(f"Table 4 level {L} reached", g["achieved_vol"], lv["reached_pct"], 2)
    for name, L in SETTINGS.items():
        g, w = got["levels"][str(L)], want["settings"][name]
        chk(f"Table 1 {name} lambda", g["lambda"], w["lambda"], 2, 1.0)
        chk(f"Table 1 {name} volatility", g["achieved_vol"], w["volatility_pct"], 1)
        for i, part in enumerate(("stocks", "bonds", "cash", "real estate and gold")):
            chk(f"Table 1 {name} {part}", g["mix"][i], w["stocks_bonds_cash_realestate_gold_pct"][i], 1)
        chk(f"Table 1 {name} typical year", g["typical_year"], w["typical_year_pct"], 1)
        chk(f"Table 1 {name} bad year", g["bad_year"], w["bad_year_pct"], 1)
        chk(f"Table 1 {name} 2008 replay", g["replay_2008"], w["replay_2008_pct"], 1)
        chk(f"Table 1 {name} fees per $10,000", g["fees_per_10000"], w["fees_per_10000"], 0, 1.0)
        if g["rating"] != w["rating"]:
            bad.append(f"Table 1 {name} rating: engine {g['rating']}, report {w['rating']}")
    n = checked[0] + 3  # and the three ratings
    detail = f"{n - len(bad) - len(near)} of {n} printed values match exactly"
    if near:
        detail += f", {len(near)} fund weights within {slack} percentage points"
    ok = report(label, not bad and got["snapshot"] == SNAPSHOT, f"{detail} (data snapshot {got['snapshot']})")
    for b in bad[:20]:
        print("        " + b)
    return ok


def print_weights(got: dict) -> None:
    rows = sorted({t for L in LEVELS for t in got["levels"][str(L)]["weights"]}, key=lambda t: -got["levels"]["3"]["weights"].get(t, 0))
    print("\n  Weights by risk level (%), Canada, 10 default ETFs (the reports' Table 7 / Table A7):")
    print("  " + "Fund".ljust(10) + "".join(f"L{L}".rjust(8) for L in LEVELS))
    for t in rows:
        print(
            "  "
            + t.split(".")[0].ljust(10)
            + "".join(
                f"{got['levels'][str(L)]['weights'][t] * 100:8.2f}" if t in got["levels"][str(L)]["weights"] else "       -" for L in LEVELS
            )
        )
    print("  " + "lambda".ljust(10) + "".join(f"{got['levels'][str(L)]['lambda']:8.2f}" for L in LEVELS))
    print("  " + "vol %".ljust(10) + "".join(f"{got['levels'][str(L)]['achieved_vol'] * 100:8.2f}" for L in LEVELS) + "\n")


def cmd_tables(args) -> bool:
    want = json.loads((REPL / "report_tables.json").read_text(encoding="utf-8"))
    print("Recomputing the optimizer tables of the reports (Canada, the 10 default ETFs, $10,000)")
    ok = True
    with tempfile.TemporaryDirectory(prefix="robokit_tables_") as tmp:
        (Path(tmp) / "empty").mkdir()
        modes = {"committed snapshot (web/data/, what a fresh clone and the web page use)": (Path(tmp) / "empty", WEIGHT_SLACK)}
        if not args.snapshot_only:
            modes["archived data (data/replication/, what the reports were computed from)"] = (data_dir(Path(tmp) / "data"), 0.0)
        results = {}
        for label, (folder, _) in modes.items():
            r = run_child([str(Path(__file__)), "_tables"], folder)
            if r.returncode:
                print(r.stdout[-2000:], r.stderr[-4000:])
                return report(label, False, "the build failed")
            results[label] = json.loads(r.stdout.strip().splitlines()[-1])
        print_weights(results[list(results)[-1]])
        for label, (_, slack) in modes.items():
            ok &= check_tables(results[label], want, label, slack)
    return ok


# ---------------------------------------------------------------- snapshot


def child_snapshot(out: str) -> None:
    """(Internal) the snapshot builder, writing into ``out`` instead of web/data/."""
    from robokit import bundle as B

    B.WEB_DATA = Path(out) / "data"
    B.export_bundle(with_reference=True)


def drop_jump_lambdas(a: dict, b: dict) -> dict:
    """In a regression case whose calibration ends in a 'jump' (the mix's volatility steps between two lambdas less than
    1e-5 apart in log terms), every lambda on the kept side gives the same weights, so the lambda the search reports
    depends on its path, which the last bits of floating-point arithmetic can change across operating systems. As in
    web/test_robokit.mjs, such a case is compared on its outcome, weights and volatility, not on that lambda, the
    number of evaluations or where the bracket landed; both brackets must still be narrower than 1e-5."""
    n, narrow = 0, True
    for ca, cb in zip(a.get("reference_cases", []), b.get("reference_cases", [])):
        ka, kb = ca.get("calibration") or {}, cb.get("calibration") or {}
        if ka.get("outcome") == "jump" and kb.get("outcome") == "jump":
            n += 1
            for case, cal in ((ca, ka), (cb, kb)):
                narrow &= (cal.get("evidence") or {}).get("log_width", 1.0) < 1e-5
                case.pop("lambda", None)
                for k in ("evaluations", "evidence"):
                    cal.pop(k, None)
    return {"n": n, "narrow": narrow}


def cmd_snapshot(args) -> bool:
    print("Rebuilding the web data snapshot from the archived data (about 5 minutes)")
    with tempfile.TemporaryDirectory(prefix="robokit_snapshot_") as tmp:
        data = data_dir(Path(tmp) / "data_v2")
        t0 = time.time()
        r = run_child([str(Path(__file__)), "_snapshot", tmp], data)
        if r.returncode:
            print(r.stdout[-2000:], r.stderr[-4000:])
            return report("snapshot", False, "the build failed")
        ok = True
        for rel in ("web/data/ca.json", "web/data/us.json", "web/data/core.json", "web/test_profiles.json"):
            new = Path(tmp) / "data" / Path(rel).name if rel.startswith("web/data/") else Path(tmp) / Path(rel).name
            a, b = json.loads(new.read_text(encoding="utf-8")), json.loads((ROOT / rel).read_text(encoding="utf-8"))
            note, narrow = "", True
            if rel.endswith("core.json"):  # the build time is the one field that is meant to change
                note = f" (build time {b['meta'].pop('generated', None)} -> {a['meta'].pop('generated', None)} ignored"
                jumps = drop_jump_lambdas(a, b)
                narrow = jumps["narrow"]
                note += f"; lambda of the {jumps['n']} 'jump' regression cases not compared, as in web/test_robokit.mjs)" if jumps["n"] else ")"
            c = compare(a, b)
            same_bytes = new.read_bytes() == (ROOT / rel).read_bytes()
            ok &= report(
                rel,
                not c["mismatches"] and narrow,
                f"{c['values']:,} values, {c['exact']:,} identical" + (", byte for byte" if same_bytes else "") + note,
            )
            for m in c["mismatches"][:10]:
                print("        ", m)
        print(f"  ({round(time.time() - t0)} s)")
    return ok


# ---------------------------------------------------------------- evaluation

QUICK_DRIVER = '''"""(Generated by scripts/replicate.py) part of E1 for Canada, run with the registered evaluation's own code."""
import json, sys
from pathlib import Path

WT, OUT, LEVELS, WORKERS, LOCKS = Path(sys.argv[1]), Path(sys.argv[2]), [int(x) for x in sys.argv[3].split(",")], int(sys.argv[4]), json.loads(sys.argv[5])
sys.path[:0] = [str(WT), str(WT / "scripts")]
import run_v3_evaluation as R  # noqa: E402  (the registered code, from its own commit)


def main():
    import robokit
    if WT.resolve() not in Path(robokit.__file__).resolve().parents:
        sys.exit(f"robokit was imported from {robokit.__file__}, not from the registered commit")
    if WORKERS:
        R.WORKERS = WORKERS
    R.OUT = OUT
    OUT.mkdir(parents=True, exist_ok=True)
    sh = R.EV.reference_shelf("CA")
    dates = R.EV.december_dates(sh.full)
    out, errors = R.walk_forward("CA", LOCKS, ["robokit"], lambda s: tuple(LEVELS), dates)
    cash = sh.full[sh.cash]
    paths = R.analyse_paths(out["builds"], sh.full, cash, ["robokit"], tuple(LEVELS), "E1", "CA")
    stats = {}
    for (s, L), p in paths.items():
        p.to_csv(OUT / f"e1_CA_{s}_L{L}.csv")
        stats[str(L)] = R.described(p, cash)
    result = {"dates": [str(d.date()) for d in dates], "builds": len(out["builds"]), "errors": errors, "stats": stats, "path_errors": R.PATH_ERRORS}
    (OUT / "quick.json").write_text(json.dumps(R.clean(result), indent=1))


if __name__ == "__main__":
    main()
'''


def registered_code(commit: str, work: Path, code: str | None) -> tuple[Path, bool]:
    """A checkout of the registered commit: the one given with --code, or a temporary git worktree."""
    if code:
        return Path(code).resolve(), False
    if subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=ROOT, capture_output=True).returncode:
        sys.exit(
            f"commit {commit[:10]} is not in this clone. Use a full clone (not --depth 1, not a ZIP download), or download "
            f"https://github.com/dylanguo1129/ai-robo-advisor/archive/{commit}.zip, unzip it and pass --code <folder>."
        )
    wt = work / "registered_code"
    subprocess.run(["git", "worktree", "add", "--detach", str(wt), commit], cwd=ROOT, check=True, capture_output=True)
    return wt, True


def cmd_evaluation(args) -> bool:
    ref = json.loads(RESULTS.read_text(encoding="utf-8"))
    prov = ref["provenance"]
    commit = prov["commit"]
    work = Path(args.workdir).resolve() if args.workdir else Path(tempfile.mkdtemp(prefix="robokit_eval_"))
    work.mkdir(parents=True, exist_ok=True)
    print(f"Re-running the registered evaluation's code (commit {commit[:10]}, run {prov['started']}) on the archived data")
    print(f"  working folder: {work}")
    wt, made = registered_code(commit, work, args.code)
    ok = True
    try:
        data = data_dir(work / "data_evaluated", evaluated=True)
        t0 = time.time()
        if args.full:
            print("  the whole evaluation: this takes hours (8,312 s for the registered run on 28 worker processes)")
            env = {**os.environ, "ROBOKIT_DATA_DIR": str(data), "PYTHONUNBUFFERED": "1"}
            r = subprocess.run([sys.executable, "scripts/run_v3_evaluation.py"], cwd=wt, env=env)
            if r.returncode:
                return report("evaluation", False, "the run stopped with an error (see above)")
            new = json.loads((wt / "output" / "v3" / "results.json").read_text(encoding="utf-8"))
            new.pop("provenance"), ref.pop("provenance")
            c = compare(new, ref)
            ok &= report(
                "output/v3/results.json",
                not c["mismatches"],
                f"{c['values']:,} values, {c['exact']:,} identical, largest other difference {c['max_abs']:.1e}",
            )
            for m in c["mismatches"][:20]:
                print("        ", m)
            csvs = sorted((ROOT / "output" / "v3").glob("*.csv"))
            res = [compare_csv(wt / "output" / "v3" / f.name, f) for f in csvs if (wt / "output" / "v3" / f.name).exists()]
            ok &= report(
                "output/v3/*.csv",
                len(res) == len(csvs) and all(x["ok"] for x in res),
                f"{sum(x['ok'] for x in res)} of {len(csvs)} monthly path files match ({sum(x['identical_bytes'] for x in res)} character for character)",
            )
        else:
            levels = "2,3,4"
            locks = {k: ref["locked_defaults"][k] for k in ("resample", "qis_switch")}
            print(
                "  quick: E1 Canada (the confirmatory walk-forward, 2010-2026) for Robo-Kit at the brief's three settings, levels 2, 3, 4"
            )
            (work / "quick_driver.py").write_text(QUICK_DRIVER, encoding="utf-8")
            out = work / "quick_out"
            env = {**os.environ, "ROBOKIT_DATA_DIR": str(data), "PYTHONUNBUFFERED": "1"}
            r = subprocess.run(
                [sys.executable, str(work / "quick_driver.py"), str(wt), str(out), levels, str(args.workers or 0), json.dumps(locks)],
                cwd=wt,
                env=env,
            )
            if r.returncode:
                return report("evaluation", False, "the run stopped with an error (see above)")
            q = json.loads((out / "quick.json").read_text(encoding="utf-8"))
            want = {L: ref["E1"]["CA"]["strategies"]["robokit"][L] for L in levels.split(",")}
            c = compare(q["stats"], want)
            ok &= report(
                "E1 CA robokit statistics in output/v3/results.json",
                not c["mismatches"],
                f"{c['values']:,} values, {c['exact']:,} identical, largest other difference {c['max_abs']:.1e}",
            )
            for m in c["mismatches"][:20]:
                print("        ", m)
            ok &= report(
                "estimation dates",
                q["dates"] == ref["E1"]["CA"]["dates"],
                f"{len(q['dates'])} Decembers, {q['dates'][0]} to {q['dates'][-1]}",
            )
            for L in levels.split(","):
                x = compare_csv(out / f"e1_CA_robokit_L{L}.csv", ROOT / "output" / "v3" / f"e1_CA_robokit_L{L}.csv")
                ok &= report(
                    f"output/v3/{x['file']}",
                    x["ok"],
                    "monthly path "
                    + (
                        "identical, character for character"
                        if x.get("identical_bytes")
                        else f"within 1e-9 (largest difference {x.get('max_abs', 0):.1e})"
                    ),
                )
        print(f"  ({round(time.time() - t0)} s)")
    finally:
        if made and not args.keep:
            subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=ROOT, capture_output=True)
        if not args.keep and not args.workdir:
            shutil.rmtree(work, ignore_errors=True)
    return ok


# ---------------------------------------------------------------- data


def cmd_data(args) -> bool:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = archive_files()
    changed, written = [], 0
    for name, data in files.items():
        dest = ROOT / m["files"][name]["path"]
        if dest.exists():
            if sha256(dest.read_bytes()) == m["files"][name]["sha256"]:
                continue  # already in place
            if not args.force:
                changed.append(str(dest.relative_to(ROOT)))
                continue
            shutil.copy2(dest, dest.with_name(dest.name + ".bak"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(dest.name + ".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, dest)
        written += 1
    if changed:
        print("These files exist with different contents (a data refresh?). Nothing was overwritten; use --force to")
        print("replace them (the old ones are kept as *.bak):\n  " + "\n  ".join(changed))
        return False
    r = subprocess.run(
        [sys.executable, "-c", "from robokit import engine as E; print(E.data_source(), E.snapshot_id())"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    got = r.stdout.split()
    return report(
        "data/v2/", got == ["local", SNAPSHOT], f"{len(files)} files in place ({written} written); the engine now uses '{' '.join(got)}'"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("tables", help="recompute the optimizer tables of both reports")
    t.add_argument("--snapshot-only", action="store_true", help="only the committed snapshot (skip the archived data)")
    sub.add_parser("snapshot", help="rebuild web/data/ from the archived data and compare")
    e = sub.add_parser("evaluation", help="re-run the registered evaluation (quick part by default) and compare")
    e.add_argument("--full", action="store_true", help="the whole evaluation (hours)")
    e.add_argument("--workers", type=int, default=0, help="worker processes for the quick part (default: as the registered script)")
    e.add_argument("--code", help="a folder with the registered commit's code, when this is not a git clone")
    e.add_argument("--workdir", help="keep the work in this folder")
    e.add_argument("--keep", action="store_true", help="keep the temporary worktree and outputs")
    d = sub.add_parser("data", help="unpack the archived data into data/v2/")
    d.add_argument("--force", action="store_true", help="replace files that differ (keeping *.bak copies)")
    sub.add_parser("_tables")
    s = sub.add_parser("_snapshot")
    s.add_argument("out")
    args = ap.parse_args()
    if args.cmd == "_tables":
        return child_tables()
    if args.cmd == "_snapshot":
        return child_snapshot(args.out)
    ok = {"tables": cmd_tables, "snapshot": cmd_snapshot, "evaluation": cmd_evaluation, "data": cmd_data}[args.cmd](args)
    print("\nAll checks passed." if ok else "\nSome checks failed (see FAIL above).")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
