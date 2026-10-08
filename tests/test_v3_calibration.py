"""Lambda is calibrated on the mix the person gets (v3 Track D1): resampled, minimum position applied, the same bootstrap
draws at every step. web/test_robokit.mjs checks that the browser takes the same steps."""

from __future__ import annotations

import pytest

from robokit.engine import CAL_MAX, CAL_TOL, Request, build_portfolio


@pytest.mark.parametrize("market,level", [("CA", 1), ("CA", 3), ("US", 2), ("US", 4)])
def test_the_final_mix_hits_its_target(market, level):
    p = build_portfolio(Request(market=market, risk_level=level))
    c = p["risk"]["calibration"]
    assert c["within_tolerance"] and abs(c["achieved_vol"] - c["target_vol"]) <= CAL_TOL
    assert abs(p["stats"]["volatility"] - p["risk"]["target_vol"]) <= 1e-4 + 5e-5 + 1e-12  # both shown to 4 decimals
    assert 1 <= c["evaluations"] <= CAL_MAX


@pytest.mark.parametrize("kw", [dict(risk_level=2, min_weight=0.05), dict(risk_level=3.5, satellites=["XIT.TO", "ZEB.TO"])])
def test_the_minimum_position_no_longer_moves_the_risk(kw):
    p = build_portfolio(Request(market="CA", resample=False, **kw))
    assert p["risk"]["calibration"]["within_tolerance"], p["risk"]["calibration"]


def test_an_unreachable_target_says_so_with_the_final_volatility():
    p = build_portfolio(Request(market="CA", target_vol=0.30, resample=False))
    c = p["risk"]["calibration"]
    assert c["outcome"] == "out of reach" and not c["within_tolerance"]
    note = [n["en"] for n in p["notes"] if "cannot reach" in n["en"]]
    assert note and f"{c['achieved_vol']:.1%}" in note[0]


def test_level_five_is_capped_by_the_fund_limits_not_by_the_calibration():
    p = build_portfolio(Request(market="CA", risk_level=5))
    c = p["risk"]["calibration"]
    assert c["outcome"] == "out of reach"  # volatility is flat near the lowest lambda: the caps bind
    assert 0 < c["target_vol"] - c["achieved_vol"] < 0.005  # a small miss: no note, the paper reports it


def _random_requests(n=40, seed=20261010):
    import numpy as np

    from robokit import engine

    rng = np.random.default_rng(seed)
    U = engine._load()[0]
    out = []
    for _ in range(n):
        market = "CA" if rng.random() < 0.6 else "US"
        pool = list(U[(U.market == market) & U.eligible & (U.asset_class == "Equity") & (U.history_months >= 60)].yahoo)
        req = dict(market=market, resample=False)
        if rng.random() < 0.7:
            req["risk_level"] = float(rng.choice([1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5]))
        else:
            req["target_vol"] = float(rng.uniform(0.01, 0.13))
        if rng.random() < 0.4:
            req["satellites"] = [str(t) for t in rng.choice(pool, size=int(rng.integers(1, 4)), replace=False)]
        if rng.random() < 0.3:
            req["max_weight"] = float(rng.choice([0.2, 0.3, 0.4]))
        if rng.random() < 0.3:
            req["min_weight"] = float(rng.choice([0.0, 0.02, 0.05, 0.1]))
        out.append(req)
    return out


@pytest.mark.parametrize("req", _random_requests(), ids=lambda r: f"{r['market']}-{r.get('risk_level', r.get('target_vol'))}")
def test_every_calibration_ends_on_target_or_proves_why_not(req):
    """Within tolerance, or a jump of the minimum-position rule (no lambda in between), or a bound of lambda: never the
    evaluation limit, and never an unexplained miss."""
    from optimizer.errors import InfeasibleConstraints
    from robokit.errors import RoboKitInputError

    try:
        p = build_portfolio(Request(**req))
    except (RoboKitInputError, InfeasibleConstraints):
        return
    c = p["risk"]["calibration"]
    assert c["outcome"] in ("within tolerance", "jump", "out of reach"), c
    assert c["within_tolerance"] == (c["outcome"] == "within tolerance")
    _check_evidence(req, c)


def _check_evidence(req: dict, c: dict) -> None:
    """Rebuild at the lambdas a calibration names as its evidence and check its claim from those builds alone: a jump
    is a sign change of volatility minus target across a bracket narrower than CAL_WIDTH in log lambda; out of reach is
    a bound of lambda with the mix there still on the far side of the target."""
    import numpy as np

    from robokit.engine import CAL_WIDTH, LAM_HI, LAM_LO

    e = c["evidence"]

    def vol_at(lam):
        return build_portfolio(Request(**req), lean=True, research={"lambda": lam})["volatility"]

    if c["outcome"] == "jump":
        assert e["log_width"] < CAL_WIDTH and np.log(e["lambda_below"] / e["lambda_above"]) == pytest.approx(e["log_width"], rel=1e-6)
        va, vb = vol_at(e["lambda_above"]), vol_at(e["lambda_below"])
        assert va == pytest.approx(e["vol_above"], abs=1e-9) and vb == pytest.approx(e["vol_below"], abs=1e-9)
        assert va > c["target_vol"] > vb
    elif c["outcome"] == "out of reach":
        v = vol_at(e["bound_lambda"])
        assert v == pytest.approx(e["vol_at_bound"], abs=1e-9)
        if e["side"] == "above":  # the steadiest mix the limits allow is still above the target
            assert e["bound_lambda"] == pytest.approx(LAM_HI) and v > c["target_vol"]
        else:  # the riskiest mix is still below it
            assert e["bound_lambda"] == pytest.approx(LAM_LO) and v < c["target_vol"]
    if c["outcome"] in ("jump", "out of reach"):
        assert abs(c["achieved_vol"] - c["target_vol"]) > CAL_TOL


@pytest.mark.parametrize(
    "req",
    [
        dict(market="CA", risk_level=2.5),
        dict(market="CA", risk_level=3.5, satellites=["XIT.TO", "ZEB.TO"]),
        dict(market="US", risk_level=4, min_weight=0.05),
        dict(market="CA", risk_level=5),
        dict(market="CA", target_vol=0.30),
    ],
    ids=["CA-2.5", "CA-3.5-satellites", "US-4-min5", "CA-5", "CA-30pct"],
)
def test_resampled_calibrations_end_on_target_or_prove_why_not(req):
    """The shipped default (resampled): the same guarantee as the single solve, with the evidence re-checked."""
    p = build_portfolio(Request(**req))
    c = p["risk"]["calibration"]
    assert c["outcome"] in ("within tolerance", "jump", "out of reach"), c
    assert c["within_tolerance"] == (c["outcome"] == "within tolerance")
    _check_evidence(req, c)
