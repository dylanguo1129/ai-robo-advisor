import numpy as np
import pandas as pd
import pytest

from optimizer.backtest import _hold, paired_comparison, walk_forward_backtest
from optimizer.data import integrity_report, to_monthly_returns
from optimizer.portfolio import RoboKitOptimizer


def panel(t=132, n=7, seed=0):
    rng = np.random.default_rng(seed)
    f = rng.normal(0.004, 0.04, size=(t, 1))
    beta = np.linspace(0.0, 1.3, n).reshape(1, n)
    x = 0.002 + f @ beta + rng.normal(0, 0.02, size=(t, n))
    x[:, 0] = 0.0015 + rng.normal(0, 0.0005, size=t)
    cols = ["CASH"] + [f"A{i}" for i in range(1, n)]
    return pd.DataFrame(x, index=pd.date_range("2015-01-31", periods=t, freq="ME"), columns=cols)


def test_hold_accounting_is_exact_without_costs():
    r = pd.DataFrame(np.array([[0.10, -0.05], [0.0, 0.02]]), columns=["a", "b"])
    w = np.array([0.5, 0.5])
    gross, net, turn = _hold(r, w, cost=0.0)
    assert np.allclose(gross, [0.025, 0.01])
    assert np.allclose(net, gross)
    # after month 1: a drifted to 0.55/1.025, b to 0.475/1.025 -> one-way turnover = |0.5366-0.5| = 0.0366
    assert abs(turn[0] - 0.0366) < 1e-3


def test_costs_reduce_net_returns_in_proportion_to_turnover():
    p = panel()
    prior = pd.Series(1.0 / p.shape[1], index=p.columns)
    bt0 = walk_forward_backtest(p, 0.02, prior, methods=("sample_mvo",), window=48, cost_bps=0.0)
    bt1 = walk_forward_backtest(p, 0.02, prior, methods=("sample_mvo",), window=48, cost_bps=50.0)
    s0, s1 = bt0.stats.loc[("sample_mvo", "mid")], bt1.stats.loc[("sample_mvo", "mid")]
    assert s1["ann_return"] < s0["ann_return"]
    assert s1["cost_drag"] > 0 and abs(s0["cost_drag"]) < 1e-12
    assert np.allclose(bt0.monthly_gross.values, bt1.monthly_gross.values)


def test_risk_matched_backtest_runs_and_reports_subperiods():
    p = panel()
    prior = pd.Series(1.0 / p.shape[1], index=p.columns)
    bt = walk_forward_backtest(
        p,
        0.02,
        prior,
        window=48,
        cash_ticker="CASH",
        vol_targets={"low": 0.10, "mid": 0.07, "high": 0.03},
        subperiods={"first": ("2019-01-31", "2020-12-31"), "second": ("2021-01-31", "2025-12-31")},
    )
    assert set(bt.stats.index.get_level_values(0)) == {"equilibrium_mvo", "sample_mvo", "minvar", "equal_weight", "prior"}
    assert bt.subperiods is not None and set(bt.subperiods.index.get_level_values(0)) == {"first", "second"}
    # minvar excludes cash, so it is not a 100%-cash portfolio
    assert bt.weights[("minvar", "mid")]["CASH"].max() == 0.0
    eq = bt.stats.loc["equilibrium_mvo"]
    assert eq.loc["low", "ann_vol"] >= eq.loc["high", "ann_vol"]
    c = paired_comparison(bt.monthly, "equilibrium_mvo|mid", "equal_weight|mid")
    assert c["n_months"] == len(bt.monthly)


def test_stationary_bootstrap_rows_and_determinism():
    p = panel()
    o = RoboKitOptimizer(p, rf=0.02, cash_ticker="CASH", resample_method="stationary", block_length=6).fit()
    rng = np.random.default_rng(1)
    rows = o._bootstrap_rows(rng, 100)
    assert rows.shape == (100,) and rows.min() >= 0 and rows.max() < 100
    # consecutive entries mostly increase by one (blocks), unlike iid draws
    steps = np.diff(rows)
    assert (steps == 1).mean() > 0.5
    a = o.optimize("mid", resample=True, n_boot=60, seed=3).weights
    b = o.optimize("mid", resample=True, n_boot=60, seed=3).weights
    assert np.allclose(a.values, b.values) and abs(a.sum() - 1) < 1e-8
    o2 = RoboKitOptimizer(p, rf=0.02, cash_ticker="CASH", resample_method="iid").fit()
    assert abs(o2.optimize("mid", resample=True, n_boot=60, seed=3).weights.sum() - 1) < 1e-8


def test_cash_max_and_naive_blend():
    p = panel()
    o = RoboKitOptimizer(p, rf=0.02, cash_ticker="CASH", cash_max=0.35).fit()
    r = o.optimize("high", resample=False)
    assert r.weights["CASH"] <= 0.35 + 1e-9
    ob = RoboKitOptimizer(p, rf=0.02, cash_ticker="CASH", naive_blend=0.5).fit()
    rb = ob.optimize("mid", resample=False)
    r0 = RoboKitOptimizer(p, rf=0.02, cash_ticker="CASH").fit().optimize("mid", resample=False)
    assert abs(rb.weights.sum() - 1) < 1e-8
    assert rb.effective_n >= r0.effective_n - 1e-9  # blending toward 1/N cannot concentrate
    with pytest.raises(ValueError):
        RoboKitOptimizer(p, naive_blend=1.5)


def test_prior_from_class_weights():
    ac = pd.Series({"A": "Equity", "B": "Equity", "C": "Fixed income", "D": "Cash"})
    w = RoboKitOptimizer.prior_from_class_weights(
        {"Equity": 0.6, "Fixed income": 0.3, "Cash": 0.1, "Gold": 0.5}, ac, within_class=pd.Series({"A": 3.0, "B": 1.0})
    )
    assert abs(w.sum() - 1) < 1e-12
    assert abs(w["A"] - 0.45) < 1e-12 and abs(w["B"] - 0.15) < 1e-12 and abs(w["C"] - 0.3) < 1e-12


def test_integrity_report_flags_jumps_and_stale_prices():
    idx = pd.bdate_range("2020-01-01", periods=300)
    rng = np.random.default_rng(0)
    px = pd.DataFrame({"X": 100 * np.cumprod(1 + rng.normal(0, 0.01, 300)), "Y": 50 * np.cumprod(1 + rng.normal(0, 0.01, 300))}, index=idx)
    px.loc[idx[100:110], "Y"] = px.loc[idx[99], "Y"]  # stale
    px.loc[idx[200] :, "X"] *= 1.6  # jump
    m = to_monthly_returns(px, min_months=6).returns
    rep = integrity_report(px, m)
    assert (rep.kind == "stale_price").any() and (rep[rep.kind == "stale_price"].ticker == "Y").all()
    assert ((rep.kind == "monthly_jump") & (rep.ticker == "X")).any()
