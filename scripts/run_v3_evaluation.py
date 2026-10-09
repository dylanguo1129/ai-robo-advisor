"""Run the pre-registered v3 evaluation once (docs/RESEARCH_LOG.md section 10). Every number the paper uses is
written to output/v3/results.json; monthly paths go to output/v3/*.csv.

Order (Stage 1 review): E3 first; its decision rules lock the defaults; E1, E2, E4, E5, E6, E7 and E8 then run on the
locked configuration. Provenance (git commit, a clean working tree, the data snapshot, versions) is recorded and the
run refuses to start from an uncommitted tree.

  python scripts/run_v3_evaluation.py            the registered run (once)
  python scripts/run_v3_evaluation.py --dry-run  a two-date check of the machinery into a temporary folder that is
                                                 deleted; it prints counts only, never a result
"""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from optimizer.estimators import choose_covariance  # noqa: E402
from robokit import audit as AU  # noqa: E402
from robokit import engine as E  # noqa: E402
from robokit import evalstats as es  # noqa: E402
from robokit import evaluation as EV  # noqa: E402
from robokit import simulation as SIM  # noqa: E402
from robokit.bundle import WIDE_US  # noqa: E402
from robokit.engine import Request, build_portfolio  # noqa: E402
from robokit.projection import project  # noqa: E402
from robokit.shelf import PRIOR, build_shelf  # noqa: E402

WORKERS = max(1, min(28, (os.cpu_count() or 4) - 2))
N_TRIALS = 54  # RESEARCH_LOG section 10: the trials counted for the deflated Sharpe ratio, enumerated there
TRIAL_INVENTORY = {  # the 54, written into results.json beside the deflated Sharpe ratios
    "RESEARCH_LOG section 2: the five methods of the first back-test": 5,
    "RESEARCH_LOG section 4: 7 configurations x 5 methods": 35,
    "RESEARCH_LOG section 6: v2 strategies": 5,
    "E1 confirmatory strategies (robokit and four benchmarks)": 5,
    "E3 contrasts that could move a default (resampling; three QIS tests)": 4,
}
assert sum(TRIAL_INVENTORY.values()) == N_TRIALS


def pmap(fn, tasks, chunksize=1):
    if WORKERS == 1:
        return [fn(t) for t in tasks]
    with ProcessPoolExecutor(WORKERS) as ex:
        return list(ex.map(fn, tasks, chunksize=chunksize))


def provenance(allow_dirty: bool) -> dict:
    def git(*a):
        r = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"git {' '.join(a)} failed: the registered run needs a git checkout ({r.stderr.strip()})")
        return r.stdout.strip()

    commit = git("rev-parse", "HEAD")
    if len(commit) != 40:
        sys.exit("no commit id: the registered run needs a committed protocol")

    dirty = "\n".join(
        line
        for line in git("status", "--porcelain").splitlines()
        if line[3:].startswith(("scripts/", "robokit/", "optimizer/", "tests/")) or not line.startswith("??")
    )
    if dirty and not allow_dirty:
        sys.exit("The working tree has uncommitted changes: commit the protocol before the registered run.\n" + dirty)
    import scipy

    return {
        "commit": commit,
        "dirty": bool(dirty),
        "data_snapshot": E.snapshot_id(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "workers": WORKERS,
        "started": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def clean(o):
    """JSON-safe: numpy scalars to floats, NaN to None, infinities to "inf" and "-inf", tuples to lists."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)):
        x = float(o)
        if math.isnan(x):
            return None
        return x if math.isfinite(x) else ("inf" if x > 0 else "-inf")  # an infinite minimum track record stays readable
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, pd.Timestamp):
        return str(o.date())
    return o


# ================================================================== E3: simulation and the locked defaults
E3_METHODS = list(EV.ENGINE) + list(EV.OUTSIDE)


def one_sided(d: np.ndarray, margin: float, greater: bool) -> dict:
    """Mean of paired differences, its standard error, and the one-sided p-value against ``margin``: Student t with
    n - 1 degrees of freedom (the replications are independent)."""
    from scipy import stats

    n = len(d)
    m, se = float(np.mean(d)), float(np.std(d, ddof=1) / math.sqrt(n))
    t = (m - margin) / se if se > 0 else 0.0
    p = float(stats.t.sf(t, n - 1)) if greater else float(stats.t.cdf(t, n - 1))
    q = float(stats.t.ppf(0.95, n - 1))
    return {"mean": m, "se": se, "lo95_one_sided": m - q * se, "hi95_one_sided": m + q * se, "p": p, "n": int(n)}


FAMILY = {"CA": "confirmatory", "US": "exploratory"}
ONE_LEVEL = "descriptive: one level with its own 90% interval; the registered reading covers levels 2-4 together"  # RESEARCH_LOG section 10, power: stated in advance
REGISTERED_TRUTH = {"CA": ["2004-12-31", "2009-12-31", 61], "QIS": ["2009-01-31", "2018-12-31", 120]}  # RESEARCH_LOG section 10, E3


def stage_e3(reps: int) -> tuple[dict, dict]:
    tm = SIM._truth_cache()["truth_months"]
    if tm != REGISTERED_TRUTH["CA"]:
        raise RuntimeError(f"E3's truth window is {tm}, not the registered {REGISTERED_TRUTH['CA']}: stopped")
    tasks = [(w, r, 3, E3_METHODS, 180) for w in "abc" for r in range(reps)]  # level 3, every method
    tasks += [(w, r, L, ["robokit", "no_resample"], 180) for w in "abc" for r in range(reps) for L in (2, 4)]
    tasks += [("b", r, 3, ["robokit"], T) for T in (36, 60, 120) for r in range(reps)]
    rows = [x for chunk in pmap(SIM.replicate, tasks) for x in chunk]
    df = pd.DataFrame(rows)
    errors = df[df.get("error").notna()] if "error" in df else pd.DataFrame()
    ok = df[df["loss_bp"].notna()] if "loss_bp" in df else df
    summary = {}
    for (w, L, m, T), g in ok.groupby(["world", "level", "method", "months"]):
        summary.setdefault(w, {}).setdefault(int(L), {}).setdefault(int(T), {})[m] = {
            "loss_bp": float(g.loss_bp.mean()),
            "loss_bp_minpos": float(g.loss_bp_minpos.mean()),
            "loss_bp_se": float(g.loss_bp.std(ddof=1) / math.sqrt(len(g))),
            "vol_error": float(g.vol_error.mean()),
            "abs_vol_error": float(g.vol_error.abs().mean()),
            "distance": float(g.distance.mean()),
            "turnover": float(g.turnover.mean()) if g.turnover.notna().any() else None,
            "band_coverage": float(g.band_coverage.mean()) if "band_coverage" in g and g.band_coverage.notna().any() else None,
            "calibration_outcomes": g.outcome.value_counts().to_dict() if g.outcome.notna().any() else None,
            "n": int(len(g)),
        }
    # paired contrasts against robokit, level 3, 180 months, aligned by replication (common random numbers)
    contrasts = {}
    for w in "abc":
        base = ok[(ok.world == w) & (ok.level == 3) & (ok.months == 180) & (ok.method == "robokit")].set_index("rep")
        for m in E3_METHODS:
            if m == "robokit":
                continue
            other = ok[(ok.world == w) & (ok.level == 3) & (ok.months == 180) & (ok.method == m)].set_index("rep")
            for col in ("loss_bp", "loss_bp_minpos"):
                d = (other[col] - base[col]).dropna()
                contrasts.setdefault(w, {}).setdefault(m, {})[col] = {
                    "mean_minus_robokit": float(d.mean()),
                    "se": float(d.std(ddof=1) / math.sqrt(len(d))) if len(d) > 1 else None,
                    "pairs": int(len(d)),
                }
    # the resampling rule's inputs: per replication, d = loss(robokit) - loss(no_resample), level 3, 180 months
    dd = {}
    for w in "abc":
        a = ok[(ok.world == w) & (ok.level == 3) & (ok.months == 180) & (ok.method == "robokit")].set_index("rep").loss_bp
        b = ok[(ok.world == w) & (ok.level == 3) & (ok.months == 180) & (ok.method == "no_resample")].set_index("rep").loss_bp
        dd[w] = (a - b).dropna().to_numpy()  # positive: resampling costs certainty equivalent

    # the QIS switch study (sub-study ii)
    qtruths = qis_truths()
    qmeta = {"months": qtruths.pop("_months"), "funds": qtruths.pop("_funds"), "window": qtruths.pop("_window"), "end": SIM.truth_end("US")}
    if qmeta["window"] != REGISTERED_TRUTH["QIS"]:
        raise RuntimeError(f"the QIS truth window is {qmeta['window']}, not the registered {REGISTERED_TRUTH['QIS']}: stopped")
    qtasks = [(name, S, ratio, rep) for name, S in qtruths.items() for ratio in (0.1, 0.2, 0.25, 0.3, 0.4, 0.6) for rep in range(reps)]
    q = pd.DataFrame(pmap(SIM.qis_switch_sample, qtasks, chunksize=25))
    # a default locks only on the full registered sample, checked before any statistic is computed: every input of
    # both rules has exactly ``reps`` finite pairs (a truth or ratio with no samples at all is caught too)
    short = {f"resampling, world {w}": len(dd[w]) for w in ("b", "c") if len(dd[w]) != reps}
    for name in qtruths:
        gg = q[q.truth == name] if len(q) else q
        for r in (0.2, 0.25, 0.3):
            n_ok = int(np.isfinite(gg.loc[gg.n_over_t == r, "rel"]).sum()) if len(gg) else 0
            if n_ok != reps:
                short[f"QIS, {name} truth at {r}"] = n_ok
    if short:
        raise RuntimeError(f"a locking rule lacks its {reps} replications {short}: no default is locked, the run stops")
    # the resampling rule: drop resampling only if it costs more than 2 bp in both realistic worlds (b, c), level 3
    rule = {w: one_sided(dd[w], 2.0, greater=True) if len(dd[w]) > 1 else {"n": int(len(dd[w])), "error": "too few pairs"} for w in "abc"}
    drop_resampling = all(rule[w]["lo95_one_sided"] > 2.0 for w in ("b", "c"))
    qsum = {
        name: {
            str(r): {"mean_rel": float(g.rel.mean()), "se": float(g.rel.std(ddof=1) / math.sqrt(len(g))), "n": int(len(g))}
            for r, g in gg.groupby("n_over_t")
        }
        for name, gg in q.groupby("truth")
    }
    tests = {}
    for name in qtruths:
        rel = {r: g.rel.to_numpy() for r, g in q[q.truth == name].groupby("n_over_t")}
        t1 = one_sided(rel[0.2], -0.01, greater=False)  # QIS better at 0.20 by more than 1%
        t2 = one_sided(rel[0.25], 0.01, greater=True)  # QIS worse at 0.25 by more than 1%
        t3 = one_sided(rel[0.3], -0.01, greater=False)  # QIS better at 0.30 by more than 1%
        adj = es.holm([t1["p"], t2["p"], t3["p"]])
        tests[name] = {
            "qis_better_at_0.20": {**t1, "p_holm": adj[0]},
            "qis_worse_at_0.25": {**t2, "p_holm": adj[1]},
            "qis_better_at_0.30": {**t3, "p_holm": adj[2]},
        }
    t1 = [tests[n]["qis_better_at_0.20"]["p_holm"] < 0.05 for n in qtruths]
    t2 = [tests[n]["qis_worse_at_0.25"]["p_holm"] < 0.05 for n in qtruths]
    # down only if T1 holds in both truths and T2 in neither; up only if T2 holds in both and T1 in neither;
    # otherwise, contradictory results included, the switch stays
    switch = 0.20 if (all(t1) and not any(t2)) else (0.30 if (all(t2) and not any(t1)) else 0.25)
    locks = {"resample": not drop_resampling, "qis_switch": switch}
    result = {
        "summary": summary,
        "paired_contrasts": contrasts,
        "resampling_rule": {**rule, "drop_resampling": drop_resampling},
        "qis_switch": {"by_ratio": qsum, "tests": tests, "t1_holds": t1, "t2_holds": t2, "switch": switch, "truth": qmeta},
        "truth_months": SIM._truth_cache()["truth_months"],
        "errors": int(len(errors)),
        "error_examples": errors.head(5).to_dict(orient="records") if len(errors) else [],
        "replications": reps,
    }
    return result, locks


def qis_truths() -> dict:
    """Two truths for the QIS study, estimated on exactly the 120 months before the first US estimation date, from 20
    funds drawn once (seed 20261008) among those on the 43-fund US list with a return in every one of those months:
    constant-correlation shrinkage (structure that favours linear shrinkage) and the sample covariance (none imposed)."""
    shelf, core, _ = E.select_funds(Request(market="US"))
    end = SIM.truth_end("US")  # only months before the US walk-forward tests anything
    names = list(dict.fromkeys(core + WIDE_US))
    window = E.returns_in("US", names).loc[:end].tail(120)
    ym = np.asarray(window.index.year * 12 + window.index.month)
    if len(window) != 120 or (np.diff(ym) != 1).any():
        raise RuntimeError(f"the QIS truth needs the 120 consecutive months up to {end}")
    pool = [t for t in names if window[t].notna().all()]
    rng = np.random.default_rng(20261008)
    pick = list(rng.choice(pool, size=20, replace=False))
    X = window[pick].to_numpy()
    return {
        "constant_correlation": choose_covariance(X, "lw_cc")[0],
        "sample": np.cov(X.T, ddof=1),
        "_months": len(X),
        "_funds": pick,
        "_window": [str(window.index[0].date()), str(window.index[-1].date()), len(window)],
    }


# ================================================================== E1 and E2
def locked_extra(strategy: str, locks: dict) -> dict:
    extra = {}
    if locks.get("qis_switch", 0.25) != 0.25 and strategy != "sample_cov":
        extra["cov_method"] = f"auto:{locks['qis_switch']}"
    if not locks.get("resample", True):
        extra["_no_resample"] = True
    return extra


def walk_forward(market: str, locks: dict, strategies, levels_all, dates=None, mode="fixed", extra=None) -> tuple[dict, list]:
    sh = EV.reference_shelf(market)
    dates = dates or EV.december_dates(sh.full)
    tasks = []
    for d in dates:
        for s in strategies:
            for L in levels_all(s):
                tasks.append((market, str(d.date()), L, s, mode, {**locked_extra(s, locks), **(extra or {})}))
    builds = pmap(EV.build_at, tasks)
    return {"shelf": sh, "dates": dates, "builds": builds}, [b for b in builds if "error" in b]


PATH_ERRORS: list = []  # a held fund without a return stops that path; recorded, never filled in


def schedule_of(attempted: list, leading_skips: bool = False) -> list:
    """The estimation dates a path must have: every date attempted. With ``leading_skips`` (E2's one registered
    exception), a date refused for short common own history (kind "short_history") before the first date that built
    is left out; any other failure stays on the schedule, so the path stops."""
    dates = sorted(b["task"][1] for b in attempted)
    if leading_skips:
        ok = sorted(b["task"][1] for b in attempted if "weights" in b)
        skip = {b["task"][1] for b in attempted if ok and b["task"][1] < ok[0] and b.get("kind") == "short_history"}
        dates = [d for d in dates if d not in skip]
    return dates


def safe_path(attempted, realised, stage: str, market: str, strategy: str, level, leading_skips: bool = False) -> pd.DataFrame | None:
    """EV.hold_path on the builds that succeeded, against the schedule of every build attempted (a failed build stops
    the path), a failure recorded in PATH_ERRORS (stage, market, strategy, level) instead of raised."""
    builds = [b for b in attempted if "weights" in b]
    if not builds:
        PATH_ERRORS.append({"stage": stage, "market": market, "strategy": strategy, "level": level, "error": "no build succeeded"})
        return None
    try:
        return EV.hold_path(builds, realised, schedule=schedule_of(attempted, leading_skips))
    except ValueError as e:
        PATH_ERRORS.append({"stage": stage, "market": market, "strategy": strategy, "level": level, "error": str(e)})
        return None


def past_centre(builds, realised, index) -> pd.Series:
    """For each month, the mean return the weights in force predicted from the last 180 months, up to their estimation
    date, in which every held fund has a return (as E4(a)'s window): the centre of a loss that uses no later data."""
    builds = sorted(builds, key=lambda b: b["task"][1])
    out = pd.Series(np.nan, index=index)
    for i, b in enumerate(builds):
        d = pd.Timestamp(b["task"][1])
        end = pd.Timestamp(builds[i + 1]["task"][1]) if i + 1 < len(builds) else index[-1]
        w = pd.Series(b["weights"], dtype=float)
        mu = realised.loc[:d, list(w.index)].dropna(how="any").tail(180).mean()  # jointly complete months, as E4(a)
        out.loc[(index > d) & (index <= end)] = float((w * mu).sum() / w.sum())
    return out


def one_level(rk: dict, L: int) -> dict:
    """Risk delivery at one level, descriptive: its ratio and own 90% interval, without the registered reading's
    labels, which belong to levels 2-4 together."""
    out = {k: v for k, v in EV.risk_delivery(rk, (L,)).items() if k != "reading"}
    return {**out, "role": ONE_LEVEL}


def label_family(res: dict, market: str) -> None:
    """Every comparison row, confirmatory or descriptive, error stubs included, carries its market's family."""
    for table in (res.get("comparisons", {}), res.get("descriptive", {})):
        for row in table.values():
            for c in row.values():
                c["family"] = FAMILY[market]


def described(p: pd.DataFrame, cash: pd.Series) -> dict:
    """EV.describe with the 2020 and 2022 subperiods; a missing cash return is recorded, not raised."""
    try:
        return {**EV.describe(p, cash), "2020": EV.subperiod(p, 2020), "2022": EV.subperiod(p, 2022)}
    except ValueError as e:
        return {"error": str(e)}


def analyse_paths(builds, realised, cash, strategies, levels, stage: str, market: str, leading_skips: bool = False) -> dict:
    """One path per strategy and level, from every build attempted (failed ones included, so a gap is seen)."""
    paths = {}
    for s in strategies:
        for L in levels:
            bs = [b for b in builds if b["task"][3] == s and b["task"][2] == L]
            if bs:
                p = safe_path(bs, realised, stage, market, s, L, leading_skips)
                if p is not None:
                    paths[(s, L)] = p
    return paths


def stage_e1(market: str, locks: dict, dry: bool) -> dict:
    strategies = list(EV.ENGINE) + list(EV.OUTSIDE)
    if dry:
        strategies = ["robokit", "static_mix", "erc_cash"]
    sh = EV.reference_shelf(market)
    dates = EV.december_dates(sh.full)
    if dry:
        dates = dates[:2]
    out, errors = walk_forward(market, locks, strategies, lambda s: (1, 2, 3, 4, 5) if s == "robokit" else EV.PRIMARY, dates)
    builds = out["builds"]
    realised = sh.full
    cash = realised[sh.cash]
    paths = analyse_paths(builds, realised, cash, strategies, (1, 2, 3, 4, 5), "E1", market)
    res = {
        "market": market,
        "inference": "confirmatory" if market == "CA" else "exploratory (stated in advance: about 92 months, underpowered)",
        "dates": [str(d.date()) for d in dates],
        "errors": errors,
        "strategies": {},
        "comparisons": {},
        "descriptive": {},
    }
    for (s, L), p in paths.items():
        res["strategies"].setdefault(s, {})[L] = described(p, cash)
        p.to_csv(OUT / f"e1_{market}_{s}_L{L}.csv")
    if dry:
        return {"counts": {"builds": len(builds), "errors": len(errors), "paths": len(paths)}}
    missing = [
        (s, L) for s in ["robokit", *EV.CONFIRMATORY] for L in ((1, 2, 3, 4, 5) if s == "robokit" else EV.PRIMARY) if (s, L) not in paths
    ]
    res["missing_paths"] = [f"{s} level {L}" for s, L in missing]
    # every registered output is computed from the paths that exist; one that needs a missing path says so
    rk = {L: paths[("robokit", L)] for L in (1, 2, 3, 4, 5) if ("robokit", L) in paths}
    gone = {"error": "the robokit path is missing (see path_errors)"}
    res["regulator_rating"] = {L: E.ni81_102_rating(p["net"].to_numpy()) for L, p in rk.items()}  # realised paths, last 120 months
    res["risk_delivery"] = {
        "primary": EV.risk_delivery(rk, EV.PRIMARY) if all(L in rk for L in EV.PRIMARY) else gone,
        "level_1": one_level(rk, 1) if 1 in rk else gone,
        "level_5": one_level(rk, 5) if 5 in rk else gone,
    }
    res["risk_delivery_other"] = {
        s: {L: EV.risk_delivery({L: paths[(s, L)]}, (L,))[L] for L in EV.PRIMARY if (s, L) in paths} for s in strategies if s != "robokit"
    }
    conf = []
    for L in EV.PRIMARY:
        for b in EV.CONFIRMATORY:
            if (b, L) not in paths or L not in rk:
                res["comparisons"].setdefault(b, {})[L] = {"error": "path missing (see path_errors)"}
                continue
            try:
                c = EV.compare(rk[L]["net"], paths[(b, L)]["net"], cash)
                for blk in (3, 12):
                    c[f"p_two_sided_block{blk}"] = EV.compare(rk[L]["net"], paths[(b, L)]["net"], cash, block=blk)["p_two_sided"]
            except ValueError as e:  # a month without a cash return, or a series with no variance: recorded
                res["comparisons"].setdefault(b, {})[L] = {"error": str(e)}
                continue
            res["comparisons"].setdefault(b, {})[L] = c
            conf.append((b, L))
    # Holm over all 12 registered comparisons: one without a path (or with an error) enters with p = 1, so it never
    # makes the others easier to pass
    family = [(b, L) for L in EV.PRIMARY for b in EV.CONFIRMATORY]
    adj = es.holm([res["comparisons"][b][L]["p_two_sided"] if (b, L) in conf else 1.0 for b, L in family])
    adj_ni = es.holm([res["comparisons"][b][L]["p_noninferior"] if (b, L) in conf else 1.0 for b, L in family])
    res["holm_family"] = len(family)
    for (b, L), a, ani in zip(family, adj, adj_ni):
        if (b, L) not in conf:
            continue
        res["comparisons"][b][L]["p_holm"] = a
        res["comparisons"][b][L]["p_noninferior_holm"] = ani
        res["comparisons"][b][L]["reading"] = EV.reading(res["comparisons"][b][L])
        res["comparisons"][b][L]["family"] = FAMILY[market]  # the US readings are exploratory, on every row
    for s in [x for x in strategies if x not in EV.CONFIRMATORY and x != "robokit"]:
        for L in EV.PRIMARY:
            if (s, L) in paths and L in rk:
                try:
                    res["descriptive"].setdefault(s, {})[L] = EV.compare(rk[L]["net"], paths[(s, L)]["net"], cash)
                except ValueError as e:
                    res["descriptive"].setdefault(s, {})[L] = {"error": str(e)}
    label_family(res, market)
    res["dsr"] = {}
    res["dsr_trials"] = {
        "n_trials": N_TRIALS,
        "inventory": TRIAL_INVENTORY,
        "trial_sharpe_variance": "var_trials in each level's entries: the variance of the E1 strategies' monthly Sharpe ratios at that level and market; the earlier trials cannot be recomputed on these months, so this spread may understate theirs and the deflated Sharpe ratio is, if anything, too favourable. The _n_e1 entries use N = the E1 strategies only (a weaker deflation)",
    }
    for L in EV.PRIMARY:
        excess = {}
        for s in strategies:
            if (s, L) in paths:
                try:
                    excess[s] = (paths[(s, L)]["net"] - EV.cash_on(cash, paths[(s, L)].index)).to_numpy()
                except ValueError:
                    continue
        if "robokit" not in excess:
            res["dsr"][L] = gone if L not in rk else {"error": "a robokit month has no cash return"}
            continue
        srs = [float(x.mean() / x.std(ddof=1)) for x in excess.values() if x.std(ddof=1) > 0]
        res["dsr"][L] = {
            "units": "sr and sr0 are monthly Sharpe ratios (not annualised); dsr is a probability",
            "robokit": es.deflated_sharpe(excess["robokit"], srs, N_TRIALS),
            "robokit_n_e1": es.deflated_sharpe(excess["robokit"], srs, len(srs)),  # N = the E1 strategies only
            "best_benchmark": None,
            "benchmark": None,
        }
        # the best confirmatory benchmark among those with a path and a finite Sharpe ratio
        have = [b for b in EV.CONFIRMATORY if b in excess and math.isfinite(res["strategies"][b][L].get("sharpe", float("nan")))]
        if have:
            best = max(have, key=lambda b: res["strategies"][b][L]["sharpe"])
            res["dsr"][L]["best_benchmark"] = best
            res["dsr"][L]["benchmark"] = es.deflated_sharpe(excess[best], srs, N_TRIALS)
            res["dsr"][L]["benchmark_n_e1"] = es.deflated_sharpe(excess[best], srs, len(srs))
    res["ex_ante_gap"] = {}
    for s in strategies:
        for L in EV.PRIMARY:
            g = [abs(b["ex_ante_vol"] - b["target"]) for b in builds if "weights" in b and b["task"][3] == s and b["task"][2] == L]
            if g:
                res["ex_ante_gap"].setdefault(s, {})[L] = {"mean": float(np.mean(g)), "max": float(np.max(g))}
    # the calibration ablation: ex-ante gap to target, robokit against single-solve lambda
    gaps = {}
    for s in ("robokit", "single_lambda"):
        g = [abs(b["ex_ante_vol"] - b["target"]) for b in builds if "weights" in b and b["task"][3] == s and b["task"][2] in EV.PRIMARY]
        gaps[s] = {"mean_abs_gap": float(np.mean(g)), "max_abs_gap": float(np.max(g)), "n": len(g)} if g else {"n": 0}
    res["calibration_ablation"] = {
        "ex_ante_gap": gaps,
        "realised_ratio": {
            s: {L: EV.risk_delivery({L: paths[(s, L)]}, (L,))[L]["ratio"] for L in EV.PRIMARY if (s, L) in paths}
            for s in ("robokit", "single_lambda")
        },
    }
    res["calibration_outcomes"] = (
        pd.Series([b.get("outcome") for b in builds if "weights" in b and b["task"][3] == "robokit"]).value_counts().to_dict()
    )
    res["calibration_failures"] = [  # the evaluation limit reached: neither on target nor a proven jump or bound
        {"strategy": b["task"][3], "date": b["task"][1], "level": b["task"][2]}
        for b in builds
        if "weights" in b and b.get("outcome") == "limit"
    ]
    res["unreachable_benchmarks"] = sum(1 for b in builds if "weights" in b and not b.get("reachable", True))
    res["shelf"] = sh.tickers
    return res


def e2_outputs(res: dict, paths: dict, cash: pd.Series, benchmarks=("static_mix", "textbook_60")) -> None:
    """E2's risk delivery and comparisons (descriptive, no readings) from the paths that exist, as in E1: an output
    that needs a missing path, or that fails closed, records why."""
    rk = {L: paths[("robokit", L)] for L in EV.PRIMARY if ("robokit", L) in paths}
    gone = {"error": "the robokit path is missing (see path_errors)"}
    res["risk_delivery"] = EV.risk_delivery(rk, EV.PRIMARY) if len(rk) == len(EV.PRIMARY) else gone
    for b in benchmarks:
        for L in EV.PRIMARY:
            if (b, L) not in paths or L not in rk:
                res["comparisons"].setdefault(b, {})[L] = {"error": "path missing (see path_errors)"}
                continue
            try:
                res["comparisons"].setdefault(b, {})[L] = EV.compare(rk[L]["net"], paths[(b, L)]["net"], cash)
            except ValueError as e:
                res["comparisons"].setdefault(b, {})[L] = {"error": str(e)}


def leading_skips(attempted: list, strategies, levels) -> dict:
    """For each strategy and level, the estimation dates refused for short common own history (under 36 months)
    before the first one that built: the registered E2 skips. Any other failure counts only under build_failures, and
    a later failure stops the path (path_errors)."""
    out = {}
    for s in strategies:
        for L in levels:
            att = [b for b in attempted if b["task"][3] == s and b["task"][2] == L]
            ok = sorted(b["task"][1] for b in att if "weights" in b)
            out[f"{s} level {L}"] = sorted(
                b["task"][1] for b in att if b.get("kind") == "short_history" and (not ok or b["task"][1] < ok[0])
            )
    return out


def stage_e2(market: str, locks: dict) -> dict:
    sh = EV.reference_shelf(market)
    dates = EV.december_dates(sh.full)
    strategies = ["robokit", "static_mix", "textbook_60"]
    out, errors = walk_forward(market, locks, strategies, lambda s: EV.PRIMARY, dates, mode="strict")
    builds = [b for b in out["builds"] if "weights" in b]
    skipped = [b for b in out["builds"] if "error" in b]
    realised = EV.strict_realised(market, builds)
    cash = sh.full[sh.cash]  # the bill-extended cash series: the Sharpe reference, the same as E1
    paths = analyse_paths(out["builds"], realised, cash, strategies, EV.PRIMARY, "E2", market, leading_skips=True)
    res = {
        "market": market,
        "build_failures": len(skipped),
        "failure_reasons": pd.Series([b["error"][:80] for b in skipped]).value_counts().to_dict(),
        "leading_skips": leading_skips(out["builds"], strategies, EV.PRIMARY),
        "strategies": {},
        "comparisons": {},
    }
    for (s, L), p in paths.items():
        res["strategies"].setdefault(s, {})[L] = described(p, cash)
        p.to_csv(OUT / f"e2_{market}_{s}_L{L}.csv")
    e2_outputs(res, paths, cash)
    label_family(res, market)
    res["shelves"] = {b["task"][1]: sorted(b["weights"]) for b in builds if b["task"][3] == "robokit" and b["task"][2] == 3}
    return res


# ================================================================== E4 covariance estimators (descriptive)
def stage_e4(market: str, locks: dict) -> dict:
    sh = EV.reference_shelf(market)
    dates = EV.december_dates(sh.full)
    ests = ("sample", "lw_id", "lw_cc", "qis")
    # target-risk portfolios of the shipped pipeline with only the estimator changed (level 3)
    tasks = [
        (market, str(d.date()), 3, "robokit", "fixed", {**locked_extra("robokit", locks), "cov_method": m}) for d in dates for m in ests
    ]
    builds = pmap(EV.build_at, tasks)
    realised = sh.full
    out = {"target_risk": {}, "min_variance": {}, "forecast": {}, "errors": sum(1 for b in builds if "error" in b)}
    series_tr, centre_tr = {}, {}
    for m in ests:
        bs = [b for t, b in zip(tasks, builds) if t[5].get("cov_method") == m]
        p = safe_path(bs, realised, "E4", market, f"robokit ({m})", 3)
        if p is not None:
            series_tr[m] = p["net"]
            centre_tr[m] = past_centre([b for b in bs if "weights" in b], realised, p.index)
    # minimum-variance portfolios (non-cash funds, 50% cap) and the fixed-weight forecast check
    series_mv = {m: [] for m in ests}
    fc = {m: [] for m in ests}
    risky = [t for t in sh.tickers if t != sh.cash]
    w0 = sh.prior[risky] / sh.prior[risky].sum()
    for d in dates:
        win = realised.loc[:d].dropna(how="any").tail(180)[risky]
        nxt = realised.loc[(realised.index > d)].head(12)[risky]
        if len(nxt) == 0:
            continue
        for m in ests:
            S = choose_covariance(win.to_numpy(), m)[0]
            w = es.min_variance(S, cap=0.5)
            past_mean = float(win.to_numpy().mean(axis=0) @ w)
            r = nxt.to_numpy() @ w
            series_mv[m].append(pd.DataFrame({"r": r, "loss": (r - past_mean) ** 2}, index=nxt.index))
            pred = float(w0.to_numpy() @ S @ w0.to_numpy())
            real = float(np.var(nxt.to_numpy() @ w0.to_numpy(), ddof=1)) if len(nxt) > 2 else np.nan
            fc[m].append({"date": str(d.date()), "pred": pred, "real": real})
    mv = {m: pd.concat(v) for m, v in series_mv.items() if v}
    for m in ests:
        if m in series_tr:
            r_tr = series_tr[m]
            out["target_risk"][m] = {"ann_vol": float(r_tr.std(ddof=1) * math.sqrt(12)), "months": int(len(r_tr))}
        else:
            out["target_risk"][m] = {"error": "path missing (see path_errors)"}
        out["min_variance"][m] = {"ann_vol": float(mv[m]["r"].std(ddof=1) * math.sqrt(12)), "mean_loss": float(mv[m]["loss"].mean())}
        f = pd.DataFrame(fc[m]).dropna()
        pos = f[(f.pred > 0) & (f.real > 0)]  # QLIKE needs positive variances; any other year is counted, not used
        out["forecast"][m] = {
            "mse": float(((f.pred - f.real) ** 2).mean()),
            "qlike": float((pos.real / pos.pred - np.log(pos.real / pos.pred) - 1).mean()) if len(pos) else None,
            "years": int(len(f)),
            "years_without_qlike": int(len(f) - len(pos)),
        }
    base_mv = mv["lw_cc"]["loss"]
    for m in ests:
        if m == "lw_cc":
            continue
        idx = mv[m].index.intersection(base_mv.index)
        out["min_variance"][m]["dm_vs_lw_cc"] = es.diebold_mariano(mv[m]["loss"].loc[idx].to_numpy(), base_mv.loc[idx].to_numpy())
        if m in series_tr and "lw_cc" in series_tr:
            a, b = series_tr[m], series_tr["lw_cc"]
            idx = a.index.intersection(b.index)
            la = (a.loc[idx] - centre_tr[m].loc[idx]) ** 2
            lb = (b.loc[idx] - centre_tr["lw_cc"].loc[idx]) ** 2
            out["target_risk"][m]["dm_vs_lw_cc"] = es.diebold_mariano(la.to_numpy(), lb.to_numpy())
    out["note"] = (
        "descriptive: no back-test result changes a default (section 6 rule); every squared-deviation loss is centred on a "
        "mean predicted from the past only (minimum variance: the window mean; target risk: the weights in force times "
        "the funds' 180-month mean up to their estimation date)"
    )
    return out


# ================================================================== E5 sensitivities
def prior_variant(market: str, home: float | None = None, sixty_forty: bool = False) -> dict:
    from robokit.shelf import SLEEVES

    p = dict(PRIOR[market])
    eq_keys = [k for k in p if SLEEVES[k].asset_class == "Equity"]
    bond_keys = [k for k in p if SLEEVES[k].asset_class == "Fixed income"]
    if home is not None and market == "CA":
        eq = sum(p[k] for k in eq_keys)
        others = [k for k in eq_keys if k != "ca_equity"]
        o = sum(p[k] for k in others)
        p["ca_equity"] = home * eq
        for k in others:
            p[k] = p[k] / o * (1 - home) * eq
    if sixty_forty:
        for k in ("ca_reit", "ca_gold", "us_reit", "us_gold"):
            p.pop(k, None)
        e = sum(p[k] for k in eq_keys)
        for k in eq_keys:
            p[k] = p[k] / e * 0.60
        b = sum(p[k] for k in bond_keys)
        for k in bond_keys:
            p[k] = p[k] / b * 0.40
    if abs(sum(p.values()) - 1.0) > 1e-9:
        raise ValueError(f"prior variant sums to {sum(p.values())}")
    return p


def e5_today(market: str, locks: dict) -> dict:
    base_extra = {k: v for k, v in locked_extra("robokit", locks).items() if not k.startswith("_")}
    base_req = {} if locks.get("resample", True) else {"resample": False}

    def lean(level=3, req=None, research=None):
        return build_portfolio(
            Request(market=market, risk_level=level, **base_req, **(req or {})), lean=True, research={**base_extra, **(research or {})}
        )

    out = {}
    base = lean()
    out["base"] = {"weights": base["weights"], "volatility": base["volatility"], "target": base["target_vol"]}

    def diff(q):
        keys = set(q["weights"]) | set(base["weights"])
        return {
            "max_weight_change": max(abs(q["weights"].get(k, 0) - base["weights"].get(k, 0)) for k in keys),
            "volatility": q["volatility"],
            "holdings": len(q["weights"]),
            "outcome": q["calibration"]["outcome"] if q["calibration"] else None,
        }

    pw_x = base["returns"].to_numpy() @ np.array([EV.reference_shelf(market).prior.get(t, 0.0) for t in base["returns"].columns])
    pw = es.politis_white_block(pw_x)
    out["politis_white_block"] = pw
    out["block_length"] = {str(b): diff(lean(research={"block_length": b})) for b in (3, 12, max(1, round(pw)))}
    out["window"] = {str(w): diff(lean(research={"max_window": w})) for w in (120, 100_000)}  # 100,000: no cap (all months)
    if market == "CA":
        out["home_bias"] = {str(h): diff(lean(research={"prior": prior_variant(market, home=h)})) for h in (0.0, 0.2, 0.4)}
    out["sixty_forty_prior"] = diff(lean(research={"prior": prior_variant(market, sixty_forty=True)}))
    out["cap_scale"] = {str(k): diff(lean(research={"cap_scale": k})) for k in (0.5, 2.0)}
    out["min_weight"] = {str(m): diff(lean(req={"min_weight": m})) for m in (0.0, 0.01, 0.05)}
    out["max_weight"] = {str(m): diff(lean(req={"max_weight": m})) for m in (0.35, 0.7)}
    out["delta"] = {str(d): diff(lean(research={"delta": d})) for d in (1.0, 4.0)}
    for v in out["delta"].values():  # Proposition 1 with lambda calibrated: the risk agrees with delta 2.5's
        v["vol_gap_vs_delta_2.5"] = abs(v["volatility"] - base["volatility"])
        v["threshold"] = 2 * E.CAL_TOL
        v["within_twice_tolerance"] = bool(v["vol_gap_vs_delta_2.5"] <= 2 * E.CAL_TOL)
    home_sleeve = "ca_equity" if market == "CA" else "us_equity"
    out["yardstick_home_fund"] = diff(lean(research={"yardstick": {home_sleeve: 1.0}}))
    # Monte Carlo spread of the weights: 10 seeds at 100, 200, 500 draws
    spread = {}
    for nb in (100, 200, 500):
        ws = [lean(req={"n_boot": nb, "seed": s})["weights"] for s in range(1, 11)]
        keys = sorted({k for w in ws for k in w})
        sd = {k: float(np.std([w.get(k, 0.0) for w in ws], ddof=1)) for k in keys}
        spread[str(nb)] = {"max_sd": max(sd.values()), "mean_sd": float(np.mean(list(sd.values())))}
    out["draws_spread"] = spread
    # the shelf's ranking rule, each coefficient moved by +/- 50%
    U = E._load_all()[0]
    ref = build_shelf(U, market).set_index("sleeve")
    from robokit.shelf import SCORE

    changes = {}
    ref_esg = build_shelf(U, market, prefer_esg=True).set_index("sleeve")
    for k in SCORE:
        for f in (0.5, 1.5):
            esg = k == "esg"  # the ESG coefficient applies only to the ESG shelf
            base_ref = ref_esg if esg else ref
            alt = build_shelf(U, market, prefer_esg=esg, coef={k: SCORE[k] * f}).set_index("sleeve")
            changed = [s for s in base_ref.index if base_ref.at[s, "ticker"] != alt.at[s, "ticker"]]
            changes[f"{k}x{f}"] = {
                "slots_changed": changed,
                "fee_change": {s: float((alt.at[s, "mer"] or 0) - (base_ref.at[s, "mer"] or 0)) for s in changed},
            }
    out["shelf_score"] = changes
    # projection precision: the Monte Carlo standard error of the one-year 5th percentile over 10 seeds
    proj = {}
    for L in (1, 2, 3, 4, 5):
        q = lean(level=L)
        X = q["returns"]
        tick = list(q["weights"])
        w = np.array([q["weights"][t] for t in tick])
        g = np.full(len(tick), 0.05)
        for paths in (2000, 5000):
            p5 = [project(X[tick].to_numpy(), w, g, n_paths=paths, seed=s)["one_year"]["p5"] for s in range(1, 11)]
            proj.setdefault(str(L), {})[str(paths)] = {"se": float(np.std(p5, ddof=1) / math.sqrt(10)), "values": p5}
    out["projection_se"] = proj
    # the rule (numerical accuracy only): 0.25 points = 0.0025 in the decimal returns projection.py reports
    over = [L for L in proj if proj[L]["2000"]["se"] > 0.0025]
    out["projection_rule"] = {
        "threshold": 0.0025,
        "over_at_2000": over,
        "paths": 5000 if over else 2000,
        "still_over_at_5000": [L for L in over if proj[L]["5000"]["se"] > 0.0025],
    }
    return out


E5_WALK = {
    "block_3": {"block_length": 3},
    "block_12": {"block_length": 12},
    "window_120": {"max_window": 120},
    "window_all": {"max_window": 100_000},
    "home_0": "home:0.0",
    "home_20": "home:0.2",
    "home_40": "home:0.4",
    "sixty_forty": "sixty_forty",
    "yardstick_home_fund": "yardstick",
}


def e5_walk(market: str, locks: dict, pw: float) -> dict:
    sh = EV.reference_shelf(market)
    dates = EV.december_dates(sh.full)
    variants = dict(E5_WALK)
    variants["block_pw"] = {"block_length": max(1, round(pw))}
    out = {}
    for name, v in variants.items():
        if isinstance(v, str) and v.startswith("home") and market != "CA":
            continue
        if isinstance(v, dict):
            extra = v
        elif v.startswith("home"):
            extra = {"prior": prior_variant(market, home=float(v.split(":")[1]))}
        elif v == "sixty_forty":
            extra = {"prior": prior_variant(market, sixty_forty=True)}
        elif v == "yardstick":
            extra = {"yardstick": {("ca_equity" if market == "CA" else "us_equity"): 1.0}}
        else:
            extra = {}
        res, errors = walk_forward(market, locks, ["robokit"], lambda s: (3,), dates, extra=extra)
        p = safe_path(res["builds"], sh.full, "E5", market, f"robokit ({name})", 3)
        if p is None:
            out[name] = {"error": "path missing (see path_errors)", "errors": len(errors)}
            continue
        out[name] = {**described(p, sh.full[sh.cash]), "risk_ratio": EV.risk_delivery({3: p}, (3,))[3], "errors": len(errors)}
    return out


# ================================================================== E6 rebalancing on an account
def stage_e6(market: str, e1_builds: list) -> dict:
    # the targets must cover every scheduled December, as in E1: a failed build would hold a mix past its 12 months
    attempted = [b for b in e1_builds if b["task"][3] == "robokit" and b["task"][2] == 3]
    ok = {b["task"][1]: b["weights"] for b in attempted if "weights" in b}
    missing = sorted(set(schedule_of(attempted)) - set(ok))
    if not ok or missing:
        err = (
            f"no robokit level-3 build for {missing}: a target would be held past 12 months" if ok else "no robokit level-3 build succeeded"
        )
        PATH_ERRORS.append({"stage": "E6", "market": market, "strategy": "robokit", "level": 3, "error": err})
        return {"error": err}
    sh = EV.reference_shelf(market)
    targets = ok
    prices = AU.own_prices(market, sh.tickers)
    out = {"prices_from": str(prices.index[0].date()), "to": str(prices.index[-1].date()), "accounts": {}}
    for start, flow in ((100_000.0, 0.0), (100_000.0, 500.0), (10_000.0, 500.0)):
        key = f"{int(start)}_{int(flow)}"
        ideal = AU.account_path(targets, prices, start, flow, "ideal")["path"]
        out.setdefault("from", str(ideal.index[0].date()))  # the first month an account runs (a target is in force)
        res = {"ideal": AU.summarise_account(ideal, None)}
        for rule in ("monthly", "bands", "annual"):
            res[rule] = AU.summarise_account(AU.account_path(targets, prices, start, flow, rule)["path"], ideal)
        for mt in (0.0, 250.0):
            res[f"bands_min_trade_{int(mt)}"] = AU.summarise_account(
                AU.account_path(targets, prices, start, flow, "bands", min_trade=mt)["path"], ideal
            )
        out["accounts"][key] = res
    U = E._load_all()[0].set_index("yahoo")
    big = AU.account_path(targets, prices, 1_000_000.0, 0.0, "bands")["largest_order"]
    out["largest_order_share_of_daily_volume"] = {
        t: (big[t] / float(U.at[t, "dollar_volume"])) if pd.notna(U.at[t, "dollar_volume"]) else None for t in sh.tickers
    }
    out["note"] = "each fund's largest order on a 1,000,000 account under the shipped bands, over its average daily traded value (today's)"
    return out


# ================================================================== risk-delivery interval coverage
def coverage_check(samples: int = 1000, months: int = 120, n_boot: int = 999, block: int = 6) -> dict:
    """How often the risk-delivery interval (circular block bootstrap, percentile) covers the true ratio 1 on i.i.d.
    standardised months, at the nominal 90% of one interval and at the 96.7% each of three simultaneous ones."""
    out = {"samples": samples, "months": months, "n_boot": n_boot, "block": block}
    # the simultaneous claim: three correlated levels (correlation 0.9, as the levels' paths are), 96.7% each, the same
    # bootstrap draws for all three (as risk_delivery uses), all three intervals covering 1 at once
    rho, level = 0.9, 1 - 0.10 / 3
    C = np.linalg.cholesky(np.full((3, 3), rho) + (1 - rho) * np.eye(3))
    joint = 0
    for s in range(samples):
        Z = np.random.default_rng(5000 + s).normal(0, 1, (months, 3)) @ C.T
        joint += all(es.vol_ratio_interval(Z[:, k], block=block, n_boot=n_boot, level=level, seed=s)["contains_1"] for k in range(3))
    out["simultaneous_0.90_three_levels"] = joint / samples
    out["correlation_between_levels"] = rho
    for name, level in (("nominal_0.90", 0.90), ("nominal_0.967", 1 - 0.10 / 3)):
        hits = sum(
            es.vol_ratio_interval(np.random.default_rng(1000 + s).normal(0, 1, months), block=block, n_boot=n_boot, level=level, seed=s)[
                "contains_1"
            ]
            for s in range(samples)
        )
        out[name] = hits / samples
    return out


# ================================================================== E7 and E8
def stage_e7() -> dict:
    out = {
        "jump_screen": {str(round(k, 4)): AU.jump_screen_at(k) for k in (math.log(1.5), math.log(2), math.log(3))},
        "jump_screen_self_excluded_ln2": AU.jump_screen_self_excluded(math.log(2)),
    }
    h = pd.DataFrame(AU.crisis_standin_holdout())
    no_peer = int(h.standin.isna().sum())
    h = h.dropna(subset=["standin"])
    h["abs_error"] = (h.actual - h.standin.astype(float)).abs()
    out["crisis_standins"] = {
        "no_peer": no_peer,
        "by_rule": {
            r: {"mae": float(g.abs_error.mean()), "median_ae": float(g.abs_error.median()), "n": int(len(g))}
            for r, g in h.groupby("peer_rule")
        },
        "by_episode": {
            ep: {"mae": float(g.abs_error.mean()), "median_ae": float(g.abs_error.median()), "n": int(len(g))}
            for ep, g in h.groupby("episode")
        },
        "by_asset_class": {
            ac: {"mae": float(g.abs_error.mean()), "median_ae": float(g.abs_error.median()), "n": int(len(g))}
            for ac, g in h.groupby("asset_class")
        },
    }
    out["liquidity_margins"] = {m: AU.liquidity_margins(m) for m in ("CA", "US")}
    out["crisis_episode_rule"] = {m: AU.crisis_episode_rule(m) for m in ("CA", "US")}
    return out


def stage_e8() -> dict:
    out = {"standin_holdout": {}, "backfill_holdout": {m: AU.backfill_holdout(m) for m in ("CA", "US")}}
    for m in ("CA", "US"):
        rows = AU.standin_holdout(m)
        shelf = EV.reference_shelf(m).tickers
        # a fund with no written stand-in other than itself, or under 24 shared months, has no row: listed, not hidden
        out["standin_holdout"][m] = {"rows": rows, "funds_without_a_row": sorted(set(shelf) - {r["fund"] for r in rows})}
    return out


# ================================================================== main
def main():
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--reps", type=int, default=500)
    args = ap.parse_args()
    if args.dry_run:
        OUT = Path(tempfile.mkdtemp(prefix="v3_dry_"))
        prov = provenance(allow_dirty=True)
        locks = {"resample": True, "qis_switch": 0.25}
        try:
            counts = stage_e1("CA", locks, dry=True)["counts"]
            sims = SIM.replicate(("b", 0, 3, ["robokit", "erc_cash"], 180))
            print(
                "dry run: E1 builds",
                counts["builds"],
                "errors",
                counts["errors"],
                "paths",
                counts["paths"],
                "| E3 rows",
                len(sims),
                "errors",
                sum("error" in r for r in sims),
                "| commit",
                prov["commit"][:10],
            )
        finally:
            shutil.rmtree(OUT, ignore_errors=True)
        return
    OUT = ROOT / "output" / "v3"
    if args.reps != 500:
        sys.exit("the registered run uses 500 replications (RESEARCH_LOG section 10, E3); other values are for smoke runs only")
    if (OUT / "results.json").exists():
        sys.exit("output/v3/results.json exists: the registered evaluation runs once (section 6 rule).")
    OUT.mkdir(parents=True, exist_ok=True)
    results = {"provenance": {**provenance(allow_dirty=False), "replications": args.reps}}
    t0 = time.time()

    def save():
        results["provenance"]["seconds"] = round(time.time() - t0)
        (OUT / "results.json.tmp").write_text(json.dumps(clean(results), indent=1))
        os.replace(OUT / "results.json.tmp", OUT / "results.partial.json")

    results["E3"], locks = stage_e3(args.reps)
    results["locked_defaults"] = locks
    save()
    print("E3 done", round(time.time() - t0), "s; locked defaults", locks, flush=True)
    results["E1"] = {}
    for m in ("CA", "US"):
        results["E1"][m] = stage_e1(m, locks, dry=False)
        save()
        print("E1", m, round(time.time() - t0), "s", flush=True)
    results["E2"] = {m: stage_e2(m, locks) for m in ("CA", "US")}
    save()
    results["E4"] = {m: stage_e4(m, locks) for m in ("CA", "US")}
    save()
    results["E5"] = {}
    for m in ("CA", "US"):
        today = e5_today(m, locks)
        results["E5"][m] = {"today": today, "walk_forward": e5_walk(m, locks, today["politis_white_block"])}
        save()
    # one path count for the product: 5,000 if either market needs it (the standard errors by market stay under E5)
    results["locked_defaults"]["projection_paths"] = max(results["E5"][m]["today"]["projection_rule"]["paths"] for m in ("CA", "US"))
    save()
    # E6 uses the E1 level-3 robokit targets (rebuilt here from the same deterministic builds)
    results["E6"] = {}
    for m in ("CA", "US"):
        sh = EV.reference_shelf(m)
        res, _ = walk_forward(m, locks, ["robokit"], lambda s: (3,), EV.december_dates(sh.full))
        results["E6"][m] = stage_e6(m, res["builds"])
        save()
    results["risk_delivery_coverage"] = coverage_check()
    save()
    results["E7"] = stage_e7()
    results["E8"] = stage_e8()
    results["path_errors"] = PATH_ERRORS
    results["provenance"]["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
    results["provenance"]["seconds"] = round(time.time() - t0)
    (OUT / "results.json").write_text(json.dumps(clean(results), indent=1))
    (OUT / "results.partial.json").unlink(missing_ok=True)
    print("done", round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    main()
