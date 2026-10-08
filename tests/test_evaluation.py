"""The evaluation's machinery (robokit/evaluation.py, robokit/audit.py) on cases with known answers."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from robokit import audit as AU
from robokit import evaluation as EV


def _builds(weights_by_date, target=0.08):
    return [{"task": ("CA", d, 3, "x", "fixed"), "weights": w, "target": target} for d, w in weights_by_date.items()]


def test_hold_path_charges_the_drift_and_the_annual_change():
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    R = pd.DataFrame({"A": 0.02, "B": 0.0}, index=idx)
    b = _builds({"2019-12-31": {"A": 0.5, "B": 0.5}, "2020-12-31": {"A": 0.3, "B": 0.7}})
    p = EV.hold_path(b, R, cost=0.001)
    assert len(p) == 24 and np.allclose(p.loc["2020", "gross"], 0.01)
    drift = 0.5 * (abs(0.5 * 1.02 / 1.01 - 0.5) + abs(0.5 / 1.01 - 0.5))
    assert p["turn"].iloc[1] == pytest.approx(drift)
    drift_new = 0.5 * (abs(0.3 * 1.02 / 1.006 - 0.3) + abs(0.7 / 1.006 - 0.7))  # January drifts from the new 30/70
    assert p["turn"].iloc[12] == pytest.approx(drift_new + 0.2, rel=1e-9)  # plus the move from 50/50 to 30/70
    assert (p["gross"] - p["net"]).to_numpy() == pytest.approx(0.001 * p["turn"].to_numpy())


def test_risk_delivery_reads_a_path_that_hits_its_target_as_delivered_or_inconclusive():
    idx = pd.date_range("2001-01-31", periods=400, freq="ME")
    rng = np.random.default_rng(0)
    paths = {L: pd.DataFrame({"net": rng.normal(0, 0.06 / math.sqrt(12), 400), "target": 0.06}, index=idx) for L in (2, 3, 4)}
    out = EV.risk_delivery(paths, (2, 3, 4), n_boot=499)
    assert out["reading"] in ("delivered", "inconclusive") and all(0.85 < out[L]["ratio"] < 1.15 for L in (2, 3, 4))
    paths[3]["net"] *= 1.6
    assert EV.risk_delivery(paths, (2, 3, 4), n_boot=499)["reading"] == "missed at levels 3"


def test_ideal_account_with_flat_prices_and_no_cost_earns_nothing_whatever_the_flows():
    idx = pd.date_range("2020-01-31", periods=6, freq="ME")
    prices = pd.DataFrame({"A": 10.0, "B": 20.0}, index=idx)
    t = {"2019-12-31": {"A": 0.6, "B": 0.4}}
    df = AU.account_path(t, prices, 10_000.0, 500.0, "ideal", cost_bps=0.0)["path"]
    assert df["return"].abs().max() < 1e-12 and df["value"].iloc[-1] == pytest.approx(10_000 + 500 * 6)  # a contribution each month


def test_production_rebalancer_account_never_goes_short_or_overdrawn():
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    rng = np.random.default_rng(1)
    prices = pd.DataFrame(100 * np.cumprod(1 + rng.normal(0.005, 0.04, size=(24, 3)), axis=0), index=idx, columns=["A", "B", "C"])
    t = {"2019-12-31": {"A": 0.5, "B": 0.3, "C": 0.2}, "2020-12-31": {"A": 0.3, "B": 0.4, "C": 0.3}}
    for rule in ("monthly", "bands", "annual"):
        df = AU.account_path(t, prices, 10_000.0, 250.0, rule)["path"]
        assert (df["cash_share"] >= -1e-12).all() and (df["value"] > 0).all()


@pytest.mark.parametrize(
    "c,want",
    [
        (
            {"p_holm": 0.01, "sharpe_diff_annual": -0.3, "p_noninferior_holm": 0.9, "min_track_record_months": float("inf"), "months": 200},
            "benchmark better",
        ),
        (
            {"p_holm": 0.01, "sharpe_diff_annual": 0.3, "p_noninferior_holm": 0.01, "min_track_record_months": 50.0, "months": 200},
            "robokit better",
        ),
        (
            {"p_holm": 0.4, "sharpe_diff_annual": 0.05, "p_noninferior_holm": 0.02, "min_track_record_months": 900.0, "months": 200},
            "robokit not worse by more than 0.10",
        ),
        (
            {"p_holm": 0.4, "sharpe_diff_annual": 0.05, "p_noninferior_holm": 0.2, "min_track_record_months": 900.0, "months": 200},
            "too short to tell",
        ),
        (
            {"p_holm": 0.4, "sharpe_diff_annual": -0.05, "p_noninferior_holm": 0.2, "min_track_record_months": float("inf"), "months": 200},
            "inconclusive",
        ),
        (
            {"p_holm": 0.4, "sharpe_diff_annual": -0.05, "p_noninferior_holm": 0.2, "min_track_record_months": None, "months": 200},
            "inconclusive",
        ),
        (
            {"p_holm": 0.4, "sharpe_diff_annual": 0.05, "p_noninferior_holm": 0.2, "min_track_record_months": 150.0, "months": 200},
            "inconclusive",
        ),
    ],
)
def test_the_confirmatory_reading_follows_the_registered_rule(c, want):
    assert EV.reading(c) == want


def test_account_returns_are_after_trading_costs():
    idx = pd.date_range("2020-01-31", periods=6, freq="ME")
    prices = pd.DataFrame({"A": 10.0, "B": 20.0}, index=idx)
    t = {"2019-12-31": {"A": 0.6, "B": 0.4}}
    df = AU.account_path(t, prices, 10_000.0, 0.0, "ideal", cost_bps=10.0)["path"]
    assert df["return"].iloc[0] == pytest.approx(-10_000 * 1e-3 / 10_000, rel=1e-6)  # buying everything costs 10 bps
    assert df["return"].iloc[1:].abs().max() < 1e-12  # flat prices, back at target: nothing more to pay


def test_band_coverage_counts_a_fund_the_minimum_position_dropped():
    from robokit.simulation import band_coverage

    band = {"A": (0.30, 0.40), "B": (0.55, 0.65)}  # C (true weight 1%) was dropped by the 2% rule: no band shown
    assert band_coverage(band, ["A", "B", "C"], np.array([0.35, 0.60, 0.01])) == pytest.approx(2 / 3)
    assert band_coverage(band, ["A", "B", "C"], np.array([0.35, 0.60, 0.0])) == pytest.approx(1.0)


@pytest.mark.parametrize("drop", [5, 0])
def test_hold_path_refuses_a_missing_month(drop):
    """A month missing from the return dates (inside a year, or the first month after an estimation date) would
    drop its return unseen: the path fails instead, and the runner records it."""
    idx = pd.date_range("2020-01-31", periods=24, freq="ME").delete(drop)
    R = pd.DataFrame({"A": 0.01, "B": 0.0}, index=idx)
    b = _builds({"2019-12-31": {"A": 0.5, "B": 0.5}, "2020-12-31": {"A": 0.3, "B": 0.7}})
    with pytest.raises(ValueError, match="consecutive"):
        EV.hold_path(b, R)


def test_the_annual_rule_turns_the_bands_off_between_januaries(monkeypatch):
    seen = []
    real = AU.rebalance

    def spy(*a, **kw):
        seen.append(kw)
        return real(*a, **kw)

    monkeypatch.setattr(AU, "rebalance", spy)
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    prices = pd.DataFrame(
        100 * np.cumprod(1 + np.random.default_rng(2).normal(0.005, 0.04, size=(24, 3)), axis=0), index=idx, columns=list("ABC")
    )
    t = {"2019-12-31": {"A": 0.5, "B": 0.3, "C": 0.2}, "2020-06-30": {"A": 0.6, "B": 0.4}}  # C leaves the mix in July
    df = AU.account_path(t, prices, 10_000.0, 0.0, "annual")["path"]
    assert len(seen) == len(df)
    for kw, m in zip(seen, df.index):
        if m.month == 1:
            assert kw.get("band_trades", True) and kw["band_abs"] == 0.0
        else:
            assert kw["band_trades"] is False


def test_the_crisis_hold_out_uses_the_replay_stand_in_rule():
    """robokit/stress.py standin_peers, the fund itself left out, the same fallback to the asset class, no minimum
    number of peers: the hold-out tests the rule the replay uses."""
    from robokit import engine as E
    from robokit.stress import SCENARIOS, standin_peers

    rows = AU.crisis_standin_holdout()
    U, R, _, _ = E._load_all()
    meta = U.set_index("yahoo")
    assert rows and {r["peer_rule"] for r in rows} <= {"class, region and market", "class", "none"}
    for r0 in rows[:: max(1, len(rows) // 25)]:
        sc = next(s for s in SCENARIOS if s["key"] == r0["episode"])
        win = R.loc[(R.index > pd.Timestamp(sc["start"])) & (R.index <= pd.Timestamp(sc["end"]))]
        full = win.notna().all()
        peers, rule = standin_peers(meta, r0["ticker"], set(full.index[full]) - {r0["ticker"]})
        assert r0["ticker"] not in peers and rule == r0["peer_rule"] and len(peers) == r0["peers"]
        if peers:
            ep = (1 + win.fillna(0)).prod() - 1
            assert r0["standin"] == pytest.approx(float(np.median(ep[peers])))


def test_hold_path_refuses_a_missing_build_on_its_schedule():
    """A December build that failed must not let the previous weights run for 24 months."""
    idx = pd.date_range("2020-01-31", periods=36, freq="ME")
    R = pd.DataFrame({"A": 0.01, "B": 0.0}, index=idx)
    b = _builds({"2019-12-31": {"A": 0.5, "B": 0.5}, "2021-12-31": {"A": 0.3, "B": 0.7}})
    assert len(EV.hold_path(b, R)) == 36  # without the schedule the gap is invisible
    with pytest.raises(ValueError, match="2020-12-31"):
        EV.hold_path(b, R, schedule=["2019-12-31", "2020-12-31", "2021-12-31"])
    assert len(EV.hold_path(b, R, schedule=["2019-12-31", "2021-12-31"])) == 36


def test_the_runner_stops_a_path_with_a_failed_build_and_records_it():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("runner", Path(__file__).resolve().parents[1] / "scripts" / "run_v3_evaluation.py")
    rv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rv)
    idx = pd.date_range("2020-01-31", periods=36, freq="ME")
    R = pd.DataFrame({"A": 0.01, "B": 0.0}, index=idx)
    ok = _builds({"2019-12-31": {"A": 0.5, "B": 0.5}, "2021-12-31": {"A": 0.3, "B": 0.7}})
    failed = {"task": (None, "2020-12-31", 3, "s", "fixed"), "error": "RoboKitInputError: too short"}
    rv.PATH_ERRORS.clear()
    assert rv.safe_path([*ok, failed], R, "E1", "CA", "s", 3) is None
    assert rv.PATH_ERRORS and rv.PATH_ERRORS[0]["stage"] == "E1" and "2020-12-31" in rv.PATH_ERRORS[0]["error"]
    early = {"task": (None, "2018-12-31", 3, "s", "strict"), "error": "short history", "kind": "short_history"}
    assert rv.safe_path([early, *ok], R, "E2", "CA", "s", 3, leading_skips=True) is not None  # a leading skip is registered
    assert rv.safe_path([early, *ok, failed], R, "E2", "CA", "s", 3, leading_skips=True) is None  # a later gap is not
    assert rv.schedule_of([early, *ok], leading_skips=True) == ["2019-12-31", "2021-12-31"]
    other = {"task": (None, "2018-12-31", 3, "s", "strict"), "error": "solver", "kind": None}
    assert rv.safe_path([other, *ok], R, "E2", "CA", "s", 3, leading_skips=True) is None  # only short history is skipped
    assert rv.clean({"x": float("inf"), "y": float("-inf"), "z": float("nan")}) == {"x": "inf", "y": "-inf", "z": None}


@pytest.mark.parametrize("market", ["CA", "US"])
def test_the_stand_in_hold_out_compares_two_different_funds(market):
    """The slot's stand-in chain starts with the reference fund itself: compared with itself it gave a NaN
    correlation (two columns with one name). Every row compares two funds and every statistic is finite."""
    rows = AU.standin_holdout(market)
    assert rows and all(r["fund"] != r["standin"] for r in rows)
    assert all(math.isfinite(r[k]) for r in rows for k in ("correlation", "tracking_error", "vol_ratio", "mean_gap_annual"))


def test_account_summary_keeps_the_cost_of_investing_the_starting_cash():
    """The first row is the month-end the starting cash is invested: its cost is chained into the first invested
    month, so the summary's return includes it while no month out of the market is counted."""
    idx = pd.date_range("2020-01-31", periods=7, freq="ME")
    prices = pd.DataFrame({"A": 10.0, "B": 20.0}, index=idx)
    t = {"2019-12-31": {"A": 0.6, "B": 0.4}}
    df = AU.account_path(t, prices, 10_000.0, 0.0, "ideal", cost_bps=10.0)["path"]
    s = AU.summarise_account(df, df)
    assert s["months"] == 6 and s["ann_return"] == pytest.approx((1 - 1e-3) ** 2 - 1, rel=1e-9)
    assert s["return_gap_vs_ideal"] == pytest.approx(0.0, abs=1e-15)


def test_a_missing_cash_return_or_a_flat_series_fails_closed():
    idx = pd.date_range("2020-01-31", periods=24, freq="ME")
    rng = np.random.default_rng(5)
    a = pd.Series(rng.normal(0.006, 0.03, 24), index=idx)
    b = pd.Series(rng.normal(0.005, 0.03, 24), index=idx)
    cash = pd.Series(0.002, index=idx)
    holed = cash.copy()
    holed.iloc[7] = np.nan
    with pytest.raises(ValueError, match="no cash return"):
        EV.compare(a, b, holed, n_boot=99)
    with pytest.raises(ValueError, match="no cash return"):
        EV.describe(pd.DataFrame({"net": a, "gross": a, "turn": 0.0, "target": 0.08}), holed)
    with pytest.raises(ValueError, match="no variance"):
        EV.compare(a, cash + 0.0, cash, n_boot=99)  # a series equal to cash has a constant (zero) excess return


def test_too_short_to_tell_needs_robokit_ahead_whatever_the_track_record():
    """A finite minimum track record with robokit behind cannot come out of compare (both Sharpe ratios use the same
    months), but the reading checks the sign itself rather than rely on that."""
    c = {"p_holm": 0.4, "p_noninferior_holm": 0.3, "sharpe_diff_annual": -0.05, "min_track_record_months": 400.0, "months": 200}
    assert EV.reading(c) == "inconclusive"
    assert EV.reading({**c, "sharpe_diff_annual": 0.05}) == "too short to tell"


def test_the_registered_truth_windows_are_the_ones_the_code_builds():
    """The run stops unless E3's truths use the windows the plan writes down; this checks they do today."""
    import importlib.util
    from pathlib import Path

    from robokit import simulation as SIM

    spec = importlib.util.spec_from_file_location("runner", Path(__file__).resolve().parents[1] / "scripts" / "run_v3_evaluation.py")
    rv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rv)
    assert SIM._truth_cache()["truth_months"] == rv.REGISTERED_TRUTH["CA"]
    assert rv.qis_truths()["_window"] == rv.REGISTERED_TRUTH["QIS"]


def _runner():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("runner", Path(__file__).resolve().parents[1] / "scripts" / "run_v3_evaluation.py")
    rv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rv)
    return rv


def test_e6_refuses_a_target_schedule_with_a_failed_december():
    rv = _runner()
    rv.PATH_ERRORS.clear()
    builds = [
        {"task": ("CA", "2019-12-31", 3, "robokit", "fixed"), "weights": {"A": 1.0}},
        {"task": ("CA", "2020-12-31", 3, "robokit", "fixed"), "error": "RoboKitInputError: x", "kind": None},
        {"task": ("CA", "2021-12-31", 3, "robokit", "fixed"), "weights": {"A": 1.0}},
    ]
    out = rv.stage_e6("CA", builds)
    assert "2020-12-31" in out["error"] and rv.PATH_ERRORS[0]["stage"] == "E6"


def test_leading_skips_keep_only_the_registered_short_history_refusals():
    rv = _runner()
    att = [
        {"task": ("CA", "2010-12-31", 3, "robokit", "strict"), "error": "short", "kind": "short_history"},
        {"task": ("CA", "2011-12-31", 3, "robokit", "strict"), "error": "solver", "kind": None},
        {"task": ("CA", "2012-12-31", 3, "robokit", "strict"), "weights": {"A": 1.0}},
    ]
    assert rv.leading_skips(att, ["robokit"], (3,)) == {"robokit level 3": ["2010-12-31"]}


def test_the_e3_locks_reach_the_evaluation_builds():
    """The locks become research switches (locked_extra) and each build records how it was made."""
    rv = _runner()
    assert rv.locked_extra("robokit", {"resample": False, "qis_switch": 0.2}) == {"cov_method": "auto:0.2", "_no_resample": True}
    assert rv.locked_extra("sample_cov", {"resample": True, "qis_switch": 0.2}) == {}
    assert rv.locked_extra("robokit", {"resample": True, "qis_switch": 0.25}) == {}
    b = EV.build_at(("CA", "2020-12-31", 3, "robokit", "fixed", {"_no_resample": True, "cov_method": "auto:0.01"}))
    assert b["calibration_method"].startswith("final pipeline (single solve,") and b["covariance"] == "qis"
    b = EV.build_at(("CA", "2020-12-31", 3, "robokit", "fixed", {}))
    assert b["calibration_method"].startswith("final pipeline (resampled,") and b["covariance"] == "lw_cc"


@pytest.mark.parametrize("world", ["b", "c"])
def test_shorter_e3_histories_are_the_first_months_of_the_full_one(world):
    """Common random numbers across window lengths: the 36-, 60- and 120-month studies see the first months of the
    replication's 180-month history (plus the 12 months for the re-estimate)."""
    from robokit import simulation as SIM

    tr = SIM._truth_cache()
    full = SIM.history(tr, world, 3, 180)
    assert full.shape[0] == 192
    for T in (36, 60, 120):
        assert np.array_equal(SIM.history(tr, world, 3, T), full[: T + 12])
