import os

import numpy as np
import pandas as pd
import pytest

from optimizer.data import load_prices, to_monthly_returns
from optimizer.portfolio import RiskProfiles, RoboKitOptimizer

HERE = os.path.dirname(os.path.abspath(__file__))
PRICES = os.path.join(HERE, "..", "data", "prices_daily_adjclose.csv")


def synthetic_panel(t=120, n=8, seed=0):
    rng = np.random.default_rng(seed)
    f = rng.normal(0.004, 0.04, size=(t, 1))
    beta = np.linspace(0.0, 1.4, n).reshape(1, n)
    eps = rng.normal(0, 0.02, size=(t, n))
    x = 0.002 + f @ beta + eps
    x[:, 0] = 0.0015 + rng.normal(0, 0.0005, size=t)  # cash-like asset
    cols = [f"A{i}" for i in range(n)]
    cols[0] = "CASH"
    idx = pd.date_range("2016-01-31", periods=t, freq="ME")
    return pd.DataFrame(x, index=idx, columns=cols)


@pytest.fixture(scope="module")
def opt():
    panel = synthetic_panel()
    o = RoboKitOptimizer(panel, rf=0.02, cash_ticker="CASH", w_max=0.35)
    return o.fit()


def test_fit_populates_inputs(opt):
    assert opt.sigma.shape == (8, 8)
    assert np.all(np.linalg.eigvalsh(opt.sigma.to_numpy()) > 0)
    assert opt.delta > 0
    assert opt.mu_info["method"] == "equilibrium"
    assert opt.cov_info["method"] in ("lw_cc", "qis")


def test_weights_are_valid_and_monotone_in_risk(opt):
    res = opt.three_profiles(resample=False)
    vols = []
    for name in ("low", "mid", "high"):
        r = res[name]
        assert abs(r.weights.sum() - 1) < 1e-8
        assert (r.weights >= -1e-9).all()
        non_cash = r.weights.drop("CASH")
        assert (non_cash <= 0.35 + 1e-9).all()
        vols.append(r.exp_vol)
        assert abs(r.risk_contributions.sum() - 1) < 1e-8
        assert 1.0 <= r.effective_n <= 8.0 + 1e-9
    assert vols[0] >= vols[1] >= vols[2]
    assert res["high"].weights["CASH"] >= res["low"].weights["CASH"]


def test_numeric_profile_and_shortlist(opt):
    r = opt.optimize(3.0, tickers=["A3", "A5", "CASH"], resample=False)
    assert set(r.weights.index) == {"A3", "A5", "CASH"}
    assert abs(r.weights.sum() - 1) < 1e-8


def test_forced_and_excluded(opt):
    r = opt.optimize("mid", forced={"A2": 0.2}, excluded=["A7"], resample=False)
    assert r.weights["A2"] >= 0.2 - 1e-9
    assert r.weights["A7"] == 0.0
    # excluding the cash ticker must win over the "cash may be 100%" rule
    r = opt.optimize("high", excluded=["CASH"], resample=False)
    assert r.weights["CASH"] == 0.0 and abs(r.weights.sum() - 1) < 1e-8


def test_min_weight_drops_small_positions(opt):
    r = opt.optimize("mid", resample=False, min_weight=0.05)
    nz = r.weights[r.weights > 0]
    assert (nz >= 0.05 - 1e-9).all()
    assert abs(r.weights.sum() - 1) < 1e-8


def test_group_bounds(opt):
    r = opt.optimize("low", group_bounds={"risky": (["A5", "A6", "A7"], 0.0, 0.3)}, resample=False)
    assert r.weights[["A5", "A6", "A7"]].sum() <= 0.3 + 1e-6


def test_resampling_is_deterministic_and_diversifies(opt):
    a = opt.optimize("mid", resample=True, n_boot=100, seed=1)
    b = opt.optimize("mid", resample=True, n_boot=100, seed=1)
    assert np.allclose(a.weights.values, b.weights.values)
    assert a.weight_band is not None and set(a.weight_band.columns) == {"std", "q05", "q95"}
    assert abs(a.weights.sum() - 1) < 1e-8
    point = opt.optimize("mid", resample=False)
    assert a.effective_n >= point.effective_n - 0.5  # averaging should not concentrate


def test_calibrate_to_target_vol(opt):
    prof = opt.calibrate_to_target_vol({"low": 0.12, "mid": 0.08, "high": 0.04})
    assert prof.low < prof.mid < prof.high
    for name, tv in {"low": 0.12, "mid": 0.08, "high": 0.04}.items():
        r = opt.optimize(name, resample=False)
        assert abs(r.exp_vol - tv) < 0.005
    opt.profiles = RiskProfiles()  # restore defaults for other tests


def test_mu_methods_run():
    panel = synthetic_panel(seed=3)
    for m in ("equilibrium", "james_stein", "sample"):
        o = RoboKitOptimizer(panel, rf=0.02, mu_method=m).fit()
        r = o.optimize("mid", resample=False)
        assert abs(r.weights.sum() - 1) < 1e-8
    P = np.zeros((1, 8))
    P[0, 1] = 1.0
    o = RoboKitOptimizer(panel, rf=0.02, mu_method="black_litterman", views={"P": P, "Q": np.array([0.08])}).fit()
    assert o.optimize("mid", resample=True, n_boot=20).weights.sum() == pytest.approx(1.0)


def test_bad_inputs():
    panel = synthetic_panel()
    bad = panel.copy()
    bad.iloc[0, 0] = np.nan
    with pytest.raises(ValueError):
        RoboKitOptimizer(bad)
    o = RoboKitOptimizer(panel).fit()
    with pytest.raises(ValueError):
        o.optimize("mid", tickers=["NOPE"])
    with pytest.raises(RuntimeError):
        RoboKitOptimizer(panel).optimize("mid")


@pytest.mark.skipif(not os.path.exists(PRICES), reason="cached price file not present")
def test_real_universe_end_to_end():
    panel = to_monthly_returns(load_prices(PRICES), start="2016-01-01")
    o = RoboKitOptimizer(panel.returns, rf=0.0225, cash_ticker="PSA.TO").fit()
    res = o.three_profiles(resample=False)
    assert res["low"].exp_vol >= res["mid"].exp_vol >= res["high"].exp_vol
    for r in res.values():
        assert abs(r.weights.sum() - 1) < 1e-8
    # cautious client on an all-equity shortlist still gets a valid, diversified answer
    r = o.optimize("high", tickers=["XIC.TO", "VFV.TO", "XEF.TO", "XEC.TO"], resample=False)
    assert abs(r.weights.sum() - 1) < 1e-8 and r.effective_n > 1.5
