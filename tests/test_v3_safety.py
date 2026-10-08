"""v3 safety: the engine refuses bad inputs and broken limits instead of building a portfolio that breaks its rules.

Each test pins one defect found in the v3 audit (docs/superpowers/specs/2026-10-08-optimizer-v3-design.md, Track A).
They run on the local cache or, on a fresh clone, on the committed web snapshot."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from optimizer.errors import InfeasibleConstraints, SolverNotConverged
from optimizer.solver import project_with_group_cap, solve_qp_pgd, solve_qp_slsqp
from robokit import tools
from robokit.config import DATA_DIR
from robokit.engine import Request, build_portfolio, level_label, validate_request
from robokit.errors import RoboKitInputError

HAS_DATA = (DATA_DIR / "universe.pkl").exists() and (DATA_DIR / "close_monthly.pkl").exists()
needs_data = pytest.mark.skipif(not HAS_DATA, reason="exact regression values need the local data cache")


def _ca(**kw):
    return build_portfolio(Request(market="CA", resample=False, **kw))


@pytest.fixture(scope="module")
def eq_vol():
    return _ca(risk_level=3)["risk"]["stock_market_vol"]


def _satellites(n=3):
    """Eligible Canadian broad-equity funds that are not on the reference shelf, largest first."""
    from robokit import engine

    U = engine._load()[0]
    core = {r["ticker"] for r in _ca(risk_level=3)["shelf"]}
    c = U[(U.market == "CA") & U.eligible & (U.asset_class == "Equity") & ~U.yahoo.isin(core) & (U.history_months >= 120)]
    return list(c.sort_values("aum", ascending=False).yahoo.head(n))


# ------------------------------------------------------------------ A1 request validation
@pytest.mark.parametrize(
    "field,value",
    [
        ("risk_level", float("nan")),
        ("risk_level", 7),
        ("risk_level", 0),
        ("target_vol", 0.0),
        ("target_vol", -0.1),
        ("target_vol", float("nan")),
        ("years", 0),
        ("years", 2.5),
        ("amount", -10_000),
        ("amount", float("inf")),
        ("max_weight", 0),
        ("min_weight", 0.5),
        ("n_boot", -1),
        ("market", "EU"),
        ("on_infeasible", "ignore"),
    ],
)
def test_validation_refuses_bad_fields(field, value):
    with pytest.raises(RoboKitInputError) as e:
        validate_request(Request(**{field: value}))
    assert e.value.details.get("field") == field


def test_validation_refuses_minimums_above_100_and_excluded_minimums():
    with pytest.raises(RoboKitInputError):
        validate_request(Request(minimums={"XIC.TO": 0.6, "VFV.TO": 0.6}))
    with pytest.raises(RoboKitInputError):
        validate_request(Request(minimums={"XIC.TO": 0.1}, exclude=["XIC.TO"]))


def test_validation_normalises_without_touching_the_caller():
    req = Request(market="ca", years=10.0)
    out = validate_request(req)
    assert out.market == "CA" and out.years == 10 and isinstance(out.years, int)
    assert req.market == "ca"  # the caller's object is unchanged


def test_validation_refuses_unknown_dict_fields():
    with pytest.raises(RoboKitInputError):
        validate_request({"market": "CA", "levle": 3})


def test_nan_level_never_builds_a_portfolio():
    with pytest.raises(RoboKitInputError):
        _ca(risk_level=float("nan"))


# ------------------------------------------------------------------ A2 level labels (K1)
@pytest.mark.parametrize(
    "lvl,label",
    [
        (0.5, "Conservative"),
        (1.0, "Conservative"),
        (1.5, "Cautious"),
        (2.5, "Balanced"),
        (4.5, "Aggressive growth"),
        (5.0, "Aggressive growth"),
    ],
)
def test_label_rounds_half_up_and_stays_in_range(lvl, label):
    assert level_label(lvl) == label


def test_low_target_volatility_builds_with_a_label(eq_vol):
    for tv in (0.05 * eq_vol, 0.0053, 0.5 * eq_vol):
        p = _ca(target_vol=tv)
        assert p["risk"]["label"] in ("Conservative", "Balanced")
        assert abs(sum(h["weight"] for h in p["holdings"]) - 1) < 1e-3


# ------------------------------------------------------------------ A3 infeasible limits (K3)
def test_caps_that_cannot_reach_100_are_refused_with_a_plain_message():
    with pytest.raises(InfeasibleConstraints) as e:
        _ca(risk_level=3, max_weight=0.05)
    assert "cannot hold all the money" in str(e.value)
    assert e.value.details["kind"] == "caps"


def test_relaxed_caps_are_listed_and_respected():
    p = _ca(risk_level=3, max_weight=0.05, on_infeasible="relax")
    rel = p["method"]["relaxations"]
    assert rel, "relaxing must be recorded"
    applied = {r["ticker"]: r["applied"] for r in rel if r["limit"] == "cap"}
    for h in p["holdings"]:
        if h["ticker"] in applied:
            assert h["weight"] <= applied[h["ticker"]] + 2e-4
    assert any(c["id"] == "limits_relaxed" for c in p["checks"])
    assert any("was raised from" in n["en"] for n in p["notes"])


def test_satellite_group_cap_is_refused_not_stretched():
    sats = _satellites(3)
    assert len(sats) == 3
    with pytest.raises(InfeasibleConstraints) as e:
        _ca(risk_level=3, sleeves=["ca_reit", "ca_gold", "ca_cash"], satellites=sats)
    assert e.value.details["kind"] in ("group_cap", "caps")


def test_satellite_group_cap_relaxed_on_request_is_recorded():
    sats = _satellites(3)
    p = _ca(risk_level=3, sleeves=["ca_reit", "ca_gold", "ca_cash"], satellites=sats, on_infeasible="relax")
    assert p["method"]["relaxations"]
    sat_total = sum(h["weight"] for h in p["holdings"] if h["role"] == "satellite")
    applied_group = [r["applied"] for r in p["method"]["relaxations"] if r["limit"] == "group"]
    cap = applied_group[-1] if applied_group else p["risk"]["satellite_cap"]
    assert sat_total <= cap + 2e-4


def test_forced_satellite_minimums_above_the_group_cap_are_refused():
    sats = _satellites(2)
    with pytest.raises(InfeasibleConstraints):
        _ca(risk_level=3, satellites=sats, minimums={sats[0]: 0.15, sats[1]: 0.15})


def test_default_list_never_relaxes():
    for lvl in (1, 2, 3, 4, 5):
        assert _ca(risk_level=lvl)["method"]["relaxations"] == []


# ------------------------------------------------------------------ A4 views keep the minimum position (K2)
def test_views_keep_the_minimum_position_and_budgets():
    view = [{"type": "relative", "long": "XIC.TO", "short": "ZAG.TO", "difference": 0.03, "confidence": 0.8}]
    for resample in (False, True):
        p = build_portfolio(Request(market="CA", risk_level=3, views=view, resample=resample, n_boot=50))
        ws = [h["weight"] for h in p["holdings"]]
        assert min(ws) >= 0.02 - 1e-4, ws
        t = p["views"]["tilt"]
        assert t["tracking_error_after"] <= 0.01 + 1e-4 and t["largest_move_after"] <= 0.05 + 1e-4
        assert p["method"]["expected_returns_for_weights"] == "black_litterman (bounded)"


# ------------------------------------------------------------------ A5 fail closed
def test_no_equity_list_measures_the_market_on_reference_funds():
    p = _ca(risk_level=3, sleeves=["ca_agg_bond", "ca_short_bond", "ca_cash"])
    assert p["risk"]["stock_market_vol"] != 0.15
    assert 0.05 < p["risk"]["stock_market_vol"] < 0.25
    assert any("holds no stock fund" in n["en"] for n in p["notes"])


def test_group_projection_fails_closed():
    a = np.ones(2)
    with pytest.raises(InfeasibleConstraints):
        project_with_group_cap(np.array([0.5, 0.5]), a, np.array([5 / 6, 1 / 6]), 1.0, np.array([False, True]), 0.10)


def test_fista_refuses_an_unfinished_solve():
    rng = np.random.default_rng(3)
    A = rng.normal(size=(30, 30))
    S = A @ A.T / 30 + 1e-3 * np.eye(30)
    mu = rng.normal(0.05, 0.02, 30)
    with pytest.raises(SolverNotConverged):
        solve_qp_pgd(S, mu, 1.0, ub=np.full(30, 0.2), max_iter=2, tol=1e-14)
    info = {}
    w = solve_qp_pgd(S, mu, 1.0, ub=np.full(30, 0.2), info=info)
    assert info["converged"] and info["residual"] < 1e-6 and abs(w.sum() - 1) < 1e-12


def test_slsqp_checks_its_answer():
    S = np.diag([0.04, 0.09, 0.01])
    mu = np.array([0.05, 0.07, 0.02])
    gb = [(np.array([1.0, 1.0, 0.0]), 0.0, 0.6)]
    w = solve_qp_slsqp(S, mu, 3.0, np.zeros(3), np.ones(3), gb)
    assert w[:2].sum() <= 0.6 + 1e-7 and abs(w.sum() - 1) < 1e-9


# ------------------------------------------------------------------ A7 minimum weight that would drop everything
def test_large_min_weight_keeps_a_valid_portfolio():
    p = _ca(risk_level=3, min_weight=0.25)
    ws = [h["weight"] for h in p["holdings"]]
    assert abs(sum(ws) - 1) < 1e-3 and ws
    dropped_note = [n["en"] for n in p["notes"] if n["en"].startswith("Dropped because")]
    held = {h["ticker"] for h in p["holdings"]}
    for n in dropped_note:  # a fund named as dropped is not held
        for t in held:
            assert t not in n


def test_no_funds_left_is_an_input_error():
    keys = [r["sleeve"] for r in _ca(risk_level=3)["shelf"]]
    with pytest.raises(RoboKitInputError):
        _ca(risk_level=3, sleeves=keys[:0])


# ------------------------------------------------------------------ tools wrapper
@pytest.mark.parametrize(
    "args",
    [{"market": "CA", "level": float("nan")}, {"market": "CA", "level": 3, "years": 0}, {"market": "CA", "level": 3, "max_weight": 0.05}],
)
def test_tools_return_errors_as_messages(args):
    out = tools.call("build_portfolio", args)
    assert "error" in out and isinstance(out["error"], str) and out["error"]


def test_tools_relax_limits_on_request():
    out = tools.call("build_portfolio", {"market": "CA", "level": 3, "max_weight": 0.05, "relax_limits": True})
    assert "error" not in out and out["method"]["relaxations"]


# ------------------------------------------------------------------ the reference mix (local data); v3 safety left the point mix unchanged
REFERENCE_L3 = {  # v3: shared draws (optimizer/rng.py) and lambda calibrated on the final pipeline
    "VFV.TO": 0.2283,
    "ZAG.TO": 0.1996,
    "XIC.TO": 0.1607,
    "CASH.TO": 0.0975,
    "FLUR.NE": 0.0938,
    "XSB.TO": 0.0915,
    "VBU.NE": 0.0664,
    "VEE.TO": 0.0395,
    "XRE.TO": 0.0227,
}


@needs_data
def test_reference_balanced_mix_is_unchanged():
    p = build_portfolio(Request(market="CA", risk_level=3))
    got = {h["ticker"]: h["weight"] for h in p["holdings"]}
    assert set(got) == set(REFERENCE_L3)
    for t, v in REFERENCE_L3.items():
        assert math.isclose(got[t], v, abs_tol=1e-4), (t, got[t], v)
    assert pd.notna(p["risk"]["lambda"])
