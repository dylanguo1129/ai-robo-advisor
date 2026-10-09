"""Regression tests for the second bug hunt (9 Oct 2026, docs/DECISIONS.md): six finders by code area, each finding
reproduced by running the code and re-run by an independent verifier. Each test reproduces the reported trigger; the
ids (B01 ...) are the findings' numbers in the record. Where a finding concerned both engines, the browser engine
(web/robokit.js, run under node) is checked against the same rule."""

from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from robokit import evalstats as es
from robokit.errors import InfeasibleConstraints, RoboKitInputError
from tests.test_v2 import needs_data

WEB = Path(__file__).resolve().parents[1] / "web"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node not installed")


def _js(body: str):
    """Run ``body`` against the browser engine (markets loaded as CA and US) and return what it passes to ``out``."""
    head = (
        "import { readFileSync } from 'node:fs';\n"
        f"import * as RK from '{(WEB / 'robokit.js').as_uri()}';\n"
        f"import * as EN from '{(WEB / 'engine.js').as_uri()}';\n"
        f"const rd = (f) => JSON.parse(readFileSync(new URL(f, '{WEB.as_uri()}/')));\n"
        "const core = rd('data/core.json'); const CA = new RK.Market(core, rd('data/ca.json')); const US = new RK.Market(core, rd('data/us.json'));\n"
        "const out = (v) => console.log(JSON.stringify(v));\n"
        "const err = (f) => { try { f(); return null; } catch (e) { return e.message; } };\n"
    )
    r = subprocess.run([NODE, "--input-type=module", "-e", head + body], capture_output=True, text=True, check=True)
    return json.loads(r.stdout.strip().splitlines()[-1])


def _build(**kw):
    from robokit.engine import Request, build_portfolio

    return build_portfolio(Request(**{"market": "CA", "resample": False, **kw}))


def _weights(p) -> dict:
    return {h["ticker"]: h["weight"] for h in p["holdings"]}


def _notes(p) -> list[str]:
    return [n["en"] for n in p["notes"]]


def _mcp(name: str, args: dict):
    from robokit.mcp_server import mcp

    r = asyncio.run(mcp.call_tool(name, args))
    c = r[0] if isinstance(r, tuple) else r
    return json.loads(c[0].text)


# ------------------------------------------------------------------ requests and validation
@needs_data
def test_b01_mcp_refuses_unknown_arguments_instead_of_building_level_3():
    with pytest.raises(Exception, match="risk_level"):
        _mcp("build_portfolio", {"market": "CA", "risk_level": 5})
    assert _mcp("build_portfolio", {"market": "CA", "level": 5})["risk"]["level"] == 5


@needs_data
def test_b02_a_relative_view_needs_two_different_funds():
    with pytest.raises(RoboKitInputError):
        _build(risk_level=3, views=[{"type": "relative", "long": "XIC.TO", "short": "XIC.TO", "difference": 0.02}])


@needs_node
def test_b02_browser_refuses_it_too():
    e = _js(
        "out(err(() => RK.buildPortfolio(CA, {risk_level: 3, resample: false, views: [{type: 'relative', long: 'XIC.TO', short: 'XIC.TO', difference: 0.02}]})));"
    )
    assert e


@needs_data
def test_b03_own_weights_on_an_excluded_fund_are_refused():
    with pytest.raises(RoboKitInputError, match="cannot be both excluded and given a weight"):
        _build(fixed_weights={"XIC.TO": 0.5, "VFV.TO": 0.5}, exclude=["VFV.TO"])


@needs_data
def test_b04_unmatched_exclusions_and_minimums_are_named():
    p = _build(risk_level=3, exclude=["VFV"])
    assert any("VFV is not in this mix" in n for n in _notes(p))
    p = _build(risk_level=3, minimums={"NOPE.TO": 0.3})
    assert any("The minimum for NOPE.TO was not used" in n for n in _notes(p))


@needs_data
def test_b05_a_zero_minimum_places_no_limit():
    assert _weights(_build(risk_level=3, minimums={"VALT.TO": 0.0})) == _weights(_build(risk_level=3))


@needs_data
def test_b06_relax_limits_reaches_the_engine_over_mcp():
    with pytest.raises(Exception, match="relax_limits"):
        _mcp("build_portfolio", {"market": "CA", "level": 3, "max_weight": 0.05})
    p = _mcp("build_portfolio", {"market": "CA", "level": 3, "max_weight": 0.05, "relax_limits": True})
    assert any("was raised from 5.0%" in n["en"] for n in p["notes"])  # every relaxed limit is listed


@needs_data
@pytest.mark.parametrize("share", [float("nan"), 5.0, -3.0, float("inf"), 60])
def test_b07_compare_one_fund_refuses_a_share_outside_0_to_1(share):
    from robokit import tools

    assert "stock_share" in tools.call("compare_one_fund", {"market": "CA", "stock_share": share})["error"]


@needs_node
def test_b07_browser_refuses_it_too():
    assert _js("out([60, -3, NaN].map(s => err(() => RK.oneFundChoice(CA, s))));") == [
        "stock_share must be between 0 and 1 (0.6 for 60%), not 60.",
        "stock_share must be between 0 and 1 (0.6 for 60%), not -3.",
        "stock_share must be between 0 and 1 (0.6 for 60%), not NaN.",
    ]


@needs_data
def test_b08_every_tool_reads_the_market_the_same_way():
    from robokit import tools

    assert (
        tools.call("search_etfs", {"query": "S&P 500", "market": "ca"})["matches"]
        == tools.call("search_etfs", {"query": "S&P 500", "market": "CA"})["matches"]
        > 0
    )
    for name in ("reference_shelf", "search_etfs", "scenario_cards", "risk_ladder", "backtest_summary"):
        assert "market must be one of CA, US" in tools.call(name, {"market": "EU"})["error"]
    assert tools.call("compare_one_fund", {"market": "ca", "stock_share": 0.6})["available"]


@needs_data
def test_b09_tools_refuse_nonsense_numbers():
    from robokit import tools

    assert "amount" in tools.call("scenario_cards", {"market": "CA", "amount": -10000})["error"]
    assert "amount" in tools.call("scenario_cards", {"market": "CA", "amount": float("nan")})["error"]
    one = [{"ticker": "XIC.TO", "weight": 1.0, "price": -40.0}]
    assert "price" in tools.call("plan_contribution", {"holdings": one, "new_money": 1000})["error"]
    one[0]["price"] = 40.0
    assert "new_money" in tools.call("plan_contribution", {"holdings": one, "new_money": float("nan")})["error"]
    assert "limit" in tools.call("search_etfs", {"market": "CA", "limit": -5})["error"]
    assert "sort_by" in tools.call("search_etfs", {"market": "CA", "sort_by": "fit"})["error"]


@needs_node
def test_b09_browser_refuses_them_too():
    r = _js(
        "const H = [{ticker: 'A', weight: 1, price: 10}];"
        "out([err(() => RK.planContribution(H, NaN)), err(() => RK.planContribution([{ticker: 'A', weight: 1, price: -4}], 100)),"
        " err(() => RK.searchFunds(CA, {limit: -5})), err(() => RK.searchFunds(CA, {sortBy: 'fit'}))]);"
    )
    assert all(r) and "new_money" in r[0] and "price" in r[1] and "limit" in r[2] and "sort_by" in r[3]


@needs_data
def test_b10_own_weights_without_a_level_do_not_claim_one_was_chosen():
    d = _mcp("build_portfolio", {"market": "CA", "fixed_weights": {"XIC.TO": 1.0}})
    own = [x["en"] for x in d["checks"] if x["id"] == "own_weights"]
    assert own and "the level you chose" not in own[0]


@needs_data
@pytest.mark.parametrize(
    "kw",
    [
        {"hedge_us_equity": "false"},
        {"prefer_esg": "no"},
        {"resample": "false"},
        {"sleeves": "ca_equity"},
        {"profile": ["mid"]},
        {"swaps": {"ca_us_equity": ["XUS.TO"]}},
    ],
)
def test_b11_b49_mistyped_fields_are_input_errors(kw):
    with pytest.raises(RoboKitInputError):
        _build(risk_level=3, **kw)


@needs_data
def test_b12_amounts_and_own_weights_have_an_upper_bound():
    with pytest.raises(RoboKitInputError):
        _build(fixed_weights={"XIC.TO": 1e308, "VFV.TO": 1e308})
    with pytest.raises(RoboKitInputError):
        _build(risk_level=3, amount=1e308)


@needs_data
def test_b13_a_swap_into_an_excluded_fund_is_refused():
    with pytest.raises(RoboKitInputError, match="cannot be both excluded and swapped"):
        _build(risk_level=3, swaps={"ca_us_equity": "XUS.TO"}, exclude=["XUS.TO"])


@needs_node
def test_b13_browser_refuses_it_too():
    e = _js(
        "out(err(() => RK.buildPortfolio(CA, {risk_level: 3, resample: false, swaps: {ca_us_equity: 'XUS.TO'}, exclude: ['XUS.TO']})));"
    )
    assert e == "XUS.TO cannot be both excluded and swapped into a slot."


@needs_data
def test_b14_own_weights_say_which_inputs_they_ignore():
    p = _build(
        risk_level=3,
        fixed_weights={"XIC.TO": 0.5, "VFV.TO": 0.5},
        views=[{"type": "absolute", "ticker": "XIC.TO", "return": 0.2}],
        minimums={"ZAG.TO": 0.3},
    )
    n = " ".join(_notes(p))
    assert "Views do not apply to your own weights" in n and "Minimums do not apply to your own weights" in n


def test_b15_b30_both_validators_read_the_same_numbers():
    from robokit.engine import Request, validate_request

    v = validate_request(Request(views=[{"type": None, "ticker": "XIC.TO", "return": 0.1}]))
    assert v.views[0]["type"] == "absolute"
    for a in ("1_000", "0x10", "0b11"):
        with pytest.raises(RoboKitInputError):
            validate_request(Request(amount=a))
    assert validate_request(Request(amount=" 1e4 ")).amount == 10_000


@needs_node
def test_b15_b30_browser_reads_them_the_same_way():
    r = _js(
        "out([err(() => RK.validateRequest({amount: '0x10'})), err(() => RK.validateRequest({amount: '0b11'})), err(() => RK.validateRequest({amount: '1_000'}))]);"
    )
    assert all(r)


def test_b30_a_whole_float_answer_reads_as_its_option():
    from robokit import profile as prof

    a = {"A0": "CA", "A1": "retirement", "B1": "20plus", "B2": "10plus", "B4": "lt10", "B5": "very", "C2": "wait", "C3": "4", "C4": "both"}
    assert prof.score({**a, "C1": 4.0}).to_dict() == prof.score({**a, "C1": "4"}).to_dict()


@needs_data
def test_b16_no_draws_means_not_resampled():
    p = _build(risk_level=3, resample=True, n_boot=0)
    assert p["method"]["resampled"] is False and p["method"]["n_boot"] == 0


@needs_data
def test_b18_with_a_view_the_calibration_reports_the_delivered_mix():
    view = [{"type": "relative", "long": "XIC.TO", "short": "VFV.TO", "difference": 0.05, "confidence": 0.9}]
    p = _build(risk_level=3, views=view)
    c = p["risk"]["calibration"]
    assert c["applies_to"] == "the mix before the view"
    assert c["delivered_vol"] == pytest.approx(p["stats"]["volatility"], abs=1e-4)
    assert c["delivered_within_tolerance"] == (abs(c["delivered_vol"] - c["target_vol"]) <= 5e-5)


# ------------------------------------------------------------------ numerics
def test_b20_zero_risk_aversion_keeps_the_group_cap():
    from optimizer.solver import solve_qp_pgd

    S, mu, m = np.eye(3) * 0.01, np.array([0.10, 0.09, 0.01]), np.array([True, True, False])
    w = solve_qp_pgd(S, mu, 0.0, group_cap=(m, 0.10))
    assert w[m].sum() <= 0.10 + 1e-12 and w.sum() == pytest.approx(1.0)
    with pytest.raises(InfeasibleConstraints):
        solve_qp_pgd(S, mu, 0.0, ub=np.array([1.0, 1.0, 0.5]), group_cap=(m, 0.10))


@needs_node
def test_b20_browser_keeps_it_too():
    w = _js("out(Array.from(RK.solveQPG([[.01,0,0],[0,.01,0],[0,0,.01]], [.10,.09,.01], 0, [0,0,0], [1,1,1], [true,true,false], 0.1)));")
    assert w[0] + w[1] <= 0.10 + 1e-12 and sum(w) == pytest.approx(1.0)


def test_b21_dropping_tiny_weights_never_pushes_a_fund_past_its_cap():
    from optimizer.portfolio import tidy_weights

    w = np.array([0.30, 0.40 - 5e-5, 0.30, 5e-5])  # the first fund sits at its 30% cap
    lb, ub = np.zeros(4), np.array([0.30, 1.0, 1.0, 1.0])
    t = tidy_weights(w, lb, ub, None, 1e-4)
    assert t[3] == 0 and t.sum() == pytest.approx(1.0) and t[0] <= 0.30 + 1e-12
    ok = np.array([0.5, 0.5 - 5e-5, 5e-5])
    assert np.array_equal(tidy_weights(ok, np.zeros(3), np.ones(3), None, 1e-4), np.array([0.5, 0.5 - 5e-5, 0.0]) / (1 - 5e-5))


@needs_data
def test_b21_the_reported_cash_weight_stays_at_its_cap():
    from robokit.engine import build_portfolio

    w = build_portfolio(
        {"market": "CA", "risk_level": 2, "min_weight": 0, "max_weight": 0.2, "n_boot": 200, "satellites": ["BTCC.TO", "CGL.TO"]}, lean=True
    )["weights"]
    assert w["CASH.TO"] <= 0.30 + 1e-12


@needs_node
def test_b21_browser_keeps_it_too():
    d = _js(
        "const r = RK.buildPortfolio(CA, {risk_level: 2, minWeight: 0, maxWeight: 0.2, nBoot: 200, satellites: ['BTCC.TO', 'CGL.TO'], amount: 1e6});"
        "out(r.holdings.find(h => h.ticker === 'CASH.TO').dollars);"
    )
    assert d <= 300_000


def test_b22_qis_falls_back_on_collinear_returns():
    from optimizer.estimators import choose_covariance, qis

    X = np.random.default_rng(5).normal(size=(40, 12)) * 0.04
    X[:, 1] = X[:, 0]
    with pytest.raises(np.linalg.LinAlgError):
        qis(X)
    S, info = choose_covariance(X, "qis")
    assert np.isfinite(S).all() and info["method"] == "lw_cc" and info["fallback"].startswith("qis:")
    full = np.random.default_rng(6).normal(size=(40, 12)) * 0.04
    assert choose_covariance(full, "qis")[1]["method"] == "qis"  # a full-rank sample is untouched


@needs_node
def test_b22_browser_falls_back_too():
    r = _js(
        "const X = Array.from({length: 40}, (_, i) => Array.from({length: 12}, (_, j) => Math.sin(7.3 * i + 3.1 * j * j) * 0.04));"
        "X.forEach(row => { row[1] = row[0]; }); const c = EN.chooseCovariance(X, 'qis');"
        "out([c.method, c.sigma.every(r => Array.from(r).every(Number.isFinite)), !!c.fallback]);"
    )
    assert r == ["lw_cc", True, True]


def test_b23_sample_covariance_of_one_fund_is_1_by_1():
    from optimizer.portfolio import RoboKitOptimizer

    X = pd.DataFrame(np.random.default_rng(0).normal(0.005, 0.03, size=(60, 1)), columns=["A"])
    o = RoboKitOptimizer(X, cov_method="sample", w_max=1.0).fit()
    assert o.sigma.shape == (1, 1)


# ------------------------------------------------------------------ the two engines agree
@needs_data
def test_b24_the_hedge_applies_to_a_callers_own_slot_list():
    p = _build(risk_level=3, hedge_us_equity=True, sleeves=["ca_equity", "ca_us_equity", "ca_agg_bond", "ca_cash"])
    assert "XSP.TO" in _weights(p) and "VFV.TO" not in _weights(p)


@needs_data
@needs_node
def test_b24_both_engines_build_the_same_hedged_mix():
    py = _weights(_build(risk_level=3, hedge_us_equity=True, sleeves=["ca_equity", "ca_us_equity", "ca_agg_bond", "ca_cash"]))
    js = _js(
        "const p = RK.buildPortfolio(CA, {risk_level: 3, hedgeUsEquity: true, sleeves: ['ca_equity','ca_us_equity','ca_agg_bond','ca_cash'], resample: false});"
        "out(Object.fromEntries(p.holdings.map(h => [h.ticker, h.weight])));"
    )
    assert set(py) == set(js) and all(abs(py[t] - js[t]) < 2e-4 for t in py)


@needs_data
@needs_node
def test_b25_a_back_filled_fund_is_not_a_crisis_peer():
    py = _build(market="US", fixed_weights={"BNDX": 0.5, "IAGG": 0.5})["stress"]
    js = _js("out(RK.buildPortfolio(US, {fixedWeights: {BNDX: 0.5, IAGG: 0.5}, resample: false}).stress);")
    g = {x["key"]: x for x in py}["gfc"], {x["key"]: x for x in js}["gfc"]
    assert g[0]["stand_ins"] == ["BNDX"] and g[0]["portfolio_return"] == pytest.approx(g[1]["portfolio_return"], abs=1e-4)


@needs_data
def test_b26_b40_the_esg_shelf_keeps_every_slot():
    from robokit import engine as E
    from robokit.shelf import build_shelf

    U = E._load()[0]
    for m, k in (("US", "us_agg_bond"), ("CA", "ca_high_yield")):
        s = build_shelf(U, m, prefer_esg=True).set_index("sleeve")
        assert isinstance(s.at[k, "ticker"], str)


@needs_data
@needs_node
def test_b27_both_engines_print_the_same_figures():
    fw = {"XIC.TO": 0.625, "ZAG.TO": 0.375}
    py = _build(risk_level=3, fixed_weights=fw)
    js = _js(
        f"const p = RK.buildPortfolio(CA, {{risk_level: 3, fixedWeights: {json.dumps(fw)}, resample: false}});"
        "out({checks: p.checks.map(c => c.en), expl: RK.explain(p).en, mer: p.stats.weighted_mer});"
    )
    assert [c["en"] for c in py["checks"]] == js["checks"]
    assert py["explanation"]["en"] == js["expl"]
    assert py["stats"]["weighted_mer"] == js["mer"]


def test_b28_an_exact_multiple_buys_its_last_unit():
    from robokit.engine import plan_contribution

    assert plan_contribution([{"ticker": "ZAG.TO", "symbol": "ZAG", "weight": 1.0, "price": 13.53}], 94.71)["rows"][0]["units"] == 7


@needs_node
def test_b28_browser_agrees():
    assert _js("out(RK.planContribution([{ticker: 'ZAG.TO', symbol: 'ZAG', weight: 1, price: 13.53}], 94.71).rows[0].units);") == 7


@needs_node
def test_b29_browser_own_weights_without_a_level_choose_none():
    r = _js(
        "const p = RK.buildPortfolio(CA, {fixedWeights: {'VFV.TO': 1}, resample: false}); out([p.risk.chosen_level ?? null, p.checks.filter(c => c.id === 'own_weights').map(c => c.en)]);"
    )
    assert r[0] is None or not any("the level you chose" in t for t in r[1])


# ------------------------------------------------------------------ rebalancer
def test_b31_a_cost_top_up_never_sells_more_units_than_held():
    from robokit.rebalance import rebalance

    x = rebalance({"X": 1.0}, {"X": 10.5}, {"X": 100.0}, flow=-1000.0)["rows"][0]
    assert x["units_after"] >= 0


def test_b32_raising_the_reserve_sells_what_it_needs():
    from robokit.rebalance import rebalance

    r = rebalance({"X": 1.0}, {"X": 1000}, {"X": 1.0}, cash=0.0, cash_reserve=40.0)
    assert r["cash_after"] >= 40.0


def test_b33_no_order_below_the_minimum_trade():
    from robokit.rebalance import rebalance

    r = rebalance({"X": 1.0}, {}, {"X": 40.0}, flow=80.0)
    assert all(abs(x["amount"]) >= 50 for x in r["rows"] if x["action"] != "hold")


def test_b34_the_note_never_says_nothing_to_trade_when_orders_go_out():
    from robokit.rebalance import rebalance

    r = rebalance({"A": 0.6, "B": 0.4}, {"A": 600, "B": 400}, {"A": 10.0, "B": 10.0}, cash=5000.0)
    if r["traded"]:
        assert not any("nothing to trade" in n for n in r["notes"])


def test_b35_drift_is_reported_even_when_band_trades_are_off():
    from robokit.rebalance import rebalance

    r = rebalance({"A": 0.6, "B": 0.4}, {"A": 900, "B": 100}, {"A": 10.0, "B": 10.0}, band_trades=False)
    assert {x["ticker"]: x["out_of_band_after_flow"] for x in r["rows"]} == {"A": True, "B": True}


@needs_node
def test_b36_browser_refuses_null_units_and_targets():
    r = _js(
        "out([err(() => RK.rebalance({A: 0.6, B: 0.4}, {A: null}, {A: 10, B: 10}, {flow: 100})),"
        " err(() => RK.rebalance({A: 1, B: null}, {A: 5}, {A: 10, B: 10}, {flow: 100}))]);"
    )
    assert all(r)


def test_b37_a_cost_of_100_percent_is_refused():
    from robokit.rebalance import rebalance

    with pytest.raises(RoboKitInputError):
        rebalance({"A": 1.0}, {"A": 100.0}, {"A": 10.0}, flow=-500.0, whole_units=False, cost_bps=10000.0, min_trade=0.0)


@needs_node
def test_b38_both_rebalancers_word_the_rule_the_same_way():
    from robokit.rebalance import rebalance

    py = rebalance(
        {"A": 0.6, "B": 0.4},
        {"A": 900, "B": 100},
        {"A": 10.0, "B": 10.0},
        band_abs=0.025,
        adv_limit=0.005,
        min_trade=12.5,
        adv={"A": 1000.0, "B": 1000.0},
    )
    js = _js(
        "const r = RK.rebalance({A: 0.6, B: 0.4}, {A: 900, B: 100}, {A: 10, B: 10}, {bandAbs: 0.025, advLimit: 0.005, minTrade: 12.5, adv: {A: 1000, B: 1000}}); out([r.rule, r.notes]);"
    )
    assert [py["rule"], py["notes"]] == js


# ------------------------------------------------------------------ fund labels and the swap gate
def test_b41_ultra_short_bond_funds_are_not_leveraged():
    from robokit.classify import leverage_of

    assert leverage_of("JPMorgan Ultra-Short Income ETF")[0] == 1.0
    assert leverage_of("BMO Ultra Short-Term Bond ETF")[0] == 1.0
    assert leverage_of("ProShares Ultra S&P500")[0] == 2.0


@needs_data
@pytest.mark.parametrize(
    "market,slot,ticker",
    [
        ("US", "us_equity", "PHDG"),  # B42 VIX futures
        ("US", "us_cash", "BOXX"),  # B42 box spreads
        ("US", "us_agg_bond", "AGGH"),  # B42 options overlay
        ("US", "us_intl_equity", "VSS"),  # B43 small cap
        ("US", "us_equity", "SPUS"),  # B43 values screen
        ("US", "us_high_yield", "EUHY"),  # B43 single region
        ("US", "us_tips", "LTPZ"),  # B43 long maturity
        ("US", "us_corp_bond", "IGLB"),  # B43 long maturity
        ("US", "us_high_yield", "PEY"),  # B44 a stock fund
        ("US", "us_small_cap", "PSCE"),  # B47 sector small cap
        ("US", "us_reit", "SRVR"),  # B47 narrow sub-sector
    ],
)
def test_b42_to_b47_the_swap_gate_refuses_funds_the_slot_rule_excludes(market, slot, ticker):
    from robokit.engine import Request, select_funds

    notes: list = []
    shelf, _, _ = select_funds(Request(market=market, sleeves=[slot], swaps={slot: ticker}), notes)
    assert ticker not in set(shelf.ticker) and any(ticker in n["en"] for n in notes)


@needs_data
def test_b44_b45_b46_labels():
    from robokit import engine as E

    U = E._load()[0].set_index("yahoo")
    assert U.at["PEY", "asset_class"] == "Equity"
    assert U.at["BITW", "asset_class"] == "Crypto"
    assert bool(U.at["VI.TO", "hedged"])


# ------------------------------------------------------------------ evaluation statistics
def test_b50_the_symmetric_interval_is_the_one_the_p_value_inverts():
    rng = np.random.default_rng(7)
    for k in range(25):
        x = rng.standard_t(4, size=(150, 2)) * 0.03 + 0.005
        x[:, 1] = 0.85 * x[:, 0] + 0.15 * x[:, 1] + rng.normal(0, 0.004, 150) * (k % 5)
        r = es.sharpe_diff_test(x[:, 0], x[:, 1], n_boot=999, seed=k)
        lo, hi = r["ci95_symmetric"]
        assert lo < r["diff"] < hi
        assert (lo > 0 or hi < 0) == (r["p"] < 0.05)
        assert r["ci95"] != r["ci95_symmetric"]  # the registered equal-tailed interval is kept beside it


@needs_data
def test_b51_the_textbook_benchmark_aims_at_the_common_target():
    import robokit.evaluation as EV

    for market, date in (("CA", "2017-12-31"), ("US", "2023-12-31")):
        tk = EV.build_at((market, date, 3, "robokit", "fixed", {}))
        tb = EV.build_at((market, date, 3, "textbook_60", "fixed", {}))
        assert tb["target"] == pytest.approx(tk["target"], rel=1e-12)


def test_b53_the_static_mix_fails_closed_without_bonds_or_stocks():
    import robokit.evaluation as EV

    t = ["EQ1", "EQ2", "BOND"]
    X = pd.DataFrame(np.random.default_rng(0).normal(0.005, 0.03, (120, 3)), columns=t)
    with pytest.raises(ValueError, match="stock fund and a bond fund"):
        EV.outside_weights("static_mix", t, X, pd.Series([0.4, 0.2, 0.4], index=t), None, ["EQ1", "EQ2"], [], 3, 0.07)
    with pytest.raises(ValueError, match="stock fund and a bond fund"):
        EV.outside_weights("static_mix", t, X, pd.Series([0.0, 0.0, 1.0], index=t), None, ["EQ1", "EQ2"], ["BOND"], 3, 0.07)
    w, ok = EV.outside_weights("static_mix", t, X, pd.Series([0.4, 0.2, 0.4], index=t), None, ["EQ1", "EQ2"], ["BOND"], 3, 0.07)
    assert ok and w.sum() == pytest.approx(1.0)
