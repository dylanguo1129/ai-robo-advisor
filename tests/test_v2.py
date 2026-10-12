"""Tests for the v2 layers: classification, profile scoring, shelf, engine invariants, views, validator, tools.

Engine tests marked ``needs_data`` need the local data cache (data/v2/*.pkl, built by `python -m robokit refresh`);
they are skipped when it is absent (a fresh clone, CI) so the other tests still run.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from optimizer.solver import project_with_group_cap, solve_qp_pgd, solve_qp_slsqp
from robokit import profile as prof
from robokit.classify import classify_row, leverage_of
from robokit.config import DATA_DIR
from robokit.validate import check_reply
from robokit.views import bound_tilt

HAS_DATA = (DATA_DIR / "universe.pkl").exists() and (DATA_DIR / "close_monthly.pkl").exists()
needs_data = pytest.mark.skipif(not HAS_DATA, reason="local data cache data/v2 not present (python -m robokit refresh)")


# ------------------------------------------------------------------ classification
@pytest.mark.parametrize(
    "name,lev",
    [
        ("ProShares UltraPro QQQ", 3.0),
        ("Direxion Daily Semiconductor Bear 3X Shares", -3.0),
        ("BetaPro S&P 500 2x Daily Bull ETF", 2.0),
        ("ProShares Short 20+ Year Treasury", -1.0),
        ("iShares Core S&P 500 ETF", 1.0),
        ("iShares Short Treasury Bond ETF", 1.0),
        ("Vanguard Short-Term Bond ETF", 1.0),
    ],
)
def test_leverage_from_name(name, lev):
    assert leverage_of(name)[0] == lev


def _row(name, **kw):
    base = {
        "name": name,
        "market": "US",
        "yahoo": "X",
        "in_tmx": False,
        "tmx_investmentstyle": None,
        "yahoo_category": None,
        "tmx_sectors": None,
        "tmx_regions": None,
        "currency": "USD",
        "yahoo_family": None,
    }
    base.update(kw)
    return pd.Series(base)


@pytest.mark.parametrize(
    "name,ac",
    [
        ("iShares Core U.S. Aggregate Bond ETF", "Fixed income"),
        ("Global X S&P/TSX 60 Index Corporate Class ETF", "Equity"),
        ("BMO Equal Weight REITs Index ETF", "Real estate"),
        ("iShares Gold Trust", "Commodity"),
        ("iShares Bitcoin Trust ETF", "Crypto"),
        ("Global X High Interest Savings ETF", "Cash"),
        ("Vanguard Balanced ETF Portfolio", "Multi-asset"),
    ],
)
def test_asset_class_rules(name, ac):
    assert classify_row(_row(name))["asset_class"] == ac


def test_cdr_detected_in_canada():
    r = classify_row(_row("Apple Inc.", market="CA", in_tmx=False, currency="CAD"))
    assert r["cdr"] and r["asset_class"] == "Single stock"


# ------------------------------------------------------------------ profile scoring
FULL = {
    "A2": "yes",
    "A3": "no",
    "B1": "10to19",
    "B2": "10plus",
    "B4": "10to25",
    "B5": "mostly",
    "C1": "4",
    "C2": "wait",
    "C3": "3",
    "C4": "both",
}


def test_lower_of_capacity_and_tolerance():
    p = prof.score(FULL)
    assert p.status == "complete" and p.capacity == 5 and p.tolerance == 3 and p.suggested_level == 3 and p.binding == "tolerance"
    assert p.can_choose == [1, 2, 3, 4, 5] and p.within_check == [1, 2, 3, 4, 5]


def test_capacity_binds_suggestion_but_is_not_a_ceiling():
    # RESEARCH_LOG section 7: the suggestion is the lower of the two; levels above capacity stay choosable
    # (the page asks for an explicit look at their bad year first), only the gates cap what is built
    a = dict(FULL, B1="2to4", B2="once", C1="5", C2="buy", C3="5", C4="missing")
    p = prof.score(a)
    assert p.binding == "capacity" and p.suggested_level == p.capacity == 1
    assert p.can_choose == [1, 2, 3, 4, 5] and p.within_check == [1] and p.gate_cap == 5
    assert [b["id"] for b in p.binding_answers] == ["B1", "B2"]


def test_gates():
    assert prof.score(dict(FULL, B1="lt2", B2="once")).status == "not_ready"
    phased = prof.score(dict(FULL, B1="lt2", B2="10plus"))  # a retiree drawing income for years is not turned away
    assert phased.status == "complete" and not any(g["id"] == "G1" for g in phased.gates)
    p = prof.score(dict(FULL, A2="no", C1="5", C2="buy", C3="5", C4="missing"))
    assert p.suggested_level <= 2 and p.gate_cap == 2 and p.can_choose == [1, 2] and p.binding == "gate"
    assert any(g["id"] == "G2" for g in p.gates) and any(f["id"] == "F_gate_vs_tolerance" for f in p.flags)


def test_cushions_combine_to_at_most_one_step_on_a_long_horizon():
    # 20+ years, all three cushions: one step, not three (was level 2 for this saver)
    p = prof.score(dict(FULL, A2="partly", B1="20plus", B2="10plus", B4="50to75", B5="varies", C1="5", C2="buy", C3="5", C4="missing"))
    assert p.capacity == 4 and p.suggested_level == 4


def test_wealth_goal_skips_withdrawal_question():
    a = {k: v for k, v in FULL.items() if k != "B2"}
    p = prof.score(dict(a, A1="wealth"))
    assert p.status == "complete" and "B2" not in p.missing and p.capacity == 4  # 10-19 years (8) + not asked (3) = 11


def test_inconsistency_penalty_and_flag():
    consistent = prof.score(dict(FULL, C1="5", C2="buy", C3="5", C4="missing"))
    mixed = prof.score(dict(FULL, C1="5", C2="sell_all", C3="5", C4="missing"))
    assert mixed.tolerance < consistent.tolerance
    assert {f["id"] for f in mixed.flags} >= {"F_inconsistent", "F_drop_vs_range"}


def test_unknown_answer_rejected():
    with pytest.raises(ValueError):
        prof.score({"B1": "tomorrow"})


def test_risk_mapping_monotone():
    shares = [prof.risk_share(prof.engine_level(lvl)) for lvl in (1, 2, 3, 4, 5)]
    assert shares == sorted(shares) and shares[-1] == 1.0
    assert prof.cash_cap(2) == 1.0 and prof.cash_cap(6) == 0.15


# ------------------------------------------------------------------ solver group cap
def test_group_cap_matches_slsqp():
    rng = np.random.default_rng(3)
    for _ in range(20):
        n = int(rng.integers(5, 12))
        vols = rng.uniform(0.01, 0.25, n)
        C = np.corrcoef(rng.normal(size=(80, n)).T)
        S = C * np.outer(vols, vols)
        mu = rng.normal(0.03, 0.02, n)
        mask = np.zeros(n, bool)
        mask[: max(1, n // 3)] = True
        ub = np.full(n, 0.5)
        hi = 0.15
        w1 = solve_qp_pgd(S, mu, 2.0, np.zeros(n), ub, group_cap=(mask, hi))
        w2 = solve_qp_slsqp(S, mu, 2.0, np.zeros(n), ub, [(mask, 0.0, hi)])
        f = lambda w, S=S, mu=mu: w @ S @ w - mu @ w  # bind this iteration's S and mu
        assert w1[mask].sum() <= hi + 1e-8 and abs(w1.sum() - 1) < 1e-9
        assert f(w1) <= f(w2) + 1e-9


def test_group_projection_is_feasible():
    x = np.array([0.5, 0.4, 0.3, 0.2])
    v = project_with_group_cap(x, np.ones(4), np.full(4, 0.6), 1.0, np.array([True, True, False, False]), 0.3)
    assert abs(v.sum() - 1) < 1e-9 and v[:2].sum() <= 0.3 + 1e-9 and (v >= -1e-12).all()


# ------------------------------------------------------------------ views
def test_bound_tilt_respects_budgets():
    w0 = pd.Series([0.4, 0.4, 0.2], index=list("abc"))
    w1 = pd.Series([0.1, 0.6, 0.3], index=list("abc"))
    S = np.diag([0.04, 0.02, 0.01])
    w, info = bound_tilt(w0, w1, S)
    d = (w - w0).to_numpy()
    assert np.abs(d).max() <= 0.05 + 1e-9 and np.sqrt(d @ S @ d) <= 0.01 + 1e-9 and abs(w.sum() - 1) < 1e-9
    assert info["scale"] < 1


# ------------------------------------------------------------------ provenance validator
def test_validator_accepts_tool_numbers_and_roundings():
    tools = [{"volatility": 0.0642, "fee_per_year": 12.34, "explanation": "could fall to about $9,466 CAD"}]
    assert check_reply("Volatility is about 6.4% (or 6%), fees about $12 a year, bad year $9,466.", tools)["ok"]


def test_validator_rejects_invented_numbers_and_tickers():
    tools = [{"volatility": 0.0642}]
    r = check_reply("It returned 23.7% last year. You might also like ZZZQ.", tools, universe_tickers={"XIC.TO"})
    assert not r["ok"] and "23.7%" in r["unsupported_numbers"] and "ZZZQ" in r["unknown_tickers"]


def test_validator_allows_counts_and_years():
    assert check_reply("Three funds, 5 levels, since 2008.", [])["ok"]
    assert check_reply("Your 401(k) and a 403b are account names.", [])["ok"]  # not figures


# ------------------------------------------------------------------ engine (needs data)
@needs_data
@pytest.mark.parametrize("market", ["CA", "US"])
def test_engine_invariants(market):
    from robokit.engine import Request, build_portfolio

    vols = []
    for lvl in (1, 3, 5):
        p = build_portfolio(Request(market=market, risk_level=lvl, resample=False))
        w = np.array([h["weight"] for h in p["holdings"]])
        assert abs(w.sum() - 1) < 1e-3 and (w >= 0).all()
        assert all(h["weight"] <= 0.5 + 1e-3 for h in p["holdings"] if h["role"] != "cash")  # cash may exceed at level 1
        cash = [h for h in p["holdings"] if h["role"] == "cash"]
        if lvl >= 3 and cash:
            assert cash[0]["weight"] <= 0.30 + 1e-3
        assert p["risk"]["achieved_vol"] <= p["risk"]["target_vol"] + 0.006
        for n in p["explanation"]["en"]:
            assert "—" not in n
        vols.append(p["stats"]["volatility"])
    assert vols == sorted(vols)


@needs_data
def test_engine_excludes_leveraged_satellite_with_reason():
    from robokit.engine import Request, build_portfolio

    p = build_portfolio(Request(market="US", risk_level=3, satellites=["TQQQ"], resample=False))
    assert "TQQQ" not in [h["ticker"] for h in p["holdings"]]
    assert any("TQQQ" in n["en"] and "leveraged" in n["en"] for n in p["notes"])


@needs_data
def test_engine_satellite_cap():
    from robokit.engine import Request, build_portfolio

    sats = ["SMH", "XLK", "XLE", "IBB"]
    p = build_portfolio(Request(market="US", risk_level=5, satellites=sats, minimums={s: 0.05 for s in sats[:2]}, resample=False))
    sat_w = sum(h["weight"] for h in p["holdings"] if h["role"] == "satellite")
    assert sat_w <= p["risk"]["satellite_cap"] + 1e-3


@needs_data
def test_explanations_only_use_computed_numbers():
    from robokit.engine import Request, build_portfolio

    p = build_portfolio(Request(market="CA", risk_level=3, resample=False))
    tool = {k: v for k, v in p.items() if k != "explanation"}
    for sentence in p["explanation"]["en"]:
        r = check_reply(sentence, [tool])
        assert r["ok"], (sentence, r)


@needs_data
def test_tools_contract():
    from robokit import tools

    assert tools.call("etf_profile", {"ticker": "VOO"})["found"]
    assert not tools.call("etf_profile", {"ticker": "NOSUCHFUND"})["found"]
    s = tools.call("search_etfs", {"query": "gold", "market": "CA", "limit": 3})
    assert s["shown"] <= 3 and all(r["eligible"] for r in s["results"])
    assert "error" in tools.call("no_such_tool")
    assert tools.call("explain_term", {"term": "MER"})["found"]


def test_snapshot_mode_runs_without_local_data(tmp_path):
    """A fresh clone (no data/v2) must still answer tools from the committed web snapshot."""
    import json
    import os
    import subprocess
    import sys

    from robokit import snapshot

    if not snapshot.available():
        pytest.skip("web snapshot not built")
    code = (
        "import json; from robokit import tools; s = tools.call('data_status'); "
        "p = tools.call('build_portfolio', {'market': 'US', 'level': 2}); "
        "print(json.dumps({'source': s['data_source'], 'n': len(p['holdings']), 'sum': sum(h['weight'] for h in p['holdings'])}))"
    )
    env = {**os.environ, "ROBOKIT_DATA_DIR": str(tmp_path / "none"), "PYTHONIOENCODING": "utf-8"}
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=600, cwd=str(snapshot.ROOT))
    assert out.returncode == 0, out.stderr[-2000:]
    r = json.loads(out.stdout.strip().splitlines()[-1])
    assert r["source"] == "snapshot" and r["n"] >= 3 and abs(r["sum"] - 1) < 1e-3


# ------------------------------------------------------------------ regressions from the independent code review (docs/VERIFICATION.md section 3)
@pytest.mark.parametrize(
    "name,ac",
    [
        ("SPDR Gold Shares", "Commodity"),
        ("iShares Silver Trust", "Commodity"),
        ("SPDR Gold MiniShares Trust", "Commodity"),
        ("Invesco DB Commodity Index Tracking Fund", "Commodity"),
        ("Invesco DB Agriculture Fund", "Commodity"),
        ("Vanguard Short-Term Inflation-Protected Securities Index Fund ETF Shares", "Fixed income"),
        ("VanEck Gold Miners ETF", "Equity"),
        ("iShares Global Agriculture Index ETF", "Equity"),
    ],
)
def test_review_commodity_and_tips_classes(name, ac):
    assert classify_row(pd.Series({"name": name, "market": "US"}))["asset_class"] == ac


def test_review_double_long_etn_is_leveraged():
    assert leverage_of("DB Gold Double Long ETN")[0] == 2.0
    assert leverage_of("DB Gold Short ETN")[0] == -1.0


def test_review_validator_reads_text_money_and_acronyms():
    R = [{"stats": {"volatility": 0.0641, "fee_per_year": 9.5}}]
    assert check_reply("Your mix returned 13.7% last year, with volatility of about 6.4%.", R)["unsupported_numbers"] == ["13.7%"]
    assert check_reply("Consider buying ZZZQ and VFV.", R, {"VFV", "VFV.TO"})["unknown_tickers"] == ["ZZZQ"]
    assert not check_reply("Fees would cost you about $2,040.", R)["ok"]
    assert check_reply("You could hold this in your IRA, TFSA or RRIF.", R, {"VFV"})["ok"]
    assert check_reply("Please call or text 988 now.", R)["ok"]


def test_review_incomplete_profile_respects_gates():
    p = prof.score({"A2": "no", "A3": "lot", "C1": "5", "C2": "buy", "C3": "5", "C4": "missing"})
    assert p.status == "incomplete" and p.suggested_level <= 2 and p.can_choose == [1, 2]


@needs_data
def test_review_hedged_us_equity_keeps_us_stocks():
    from robokit.engine import Request, build_portfolio

    a = build_portfolio(Request(market="CA", risk_level=3, resample=False))
    b = build_portfolio(Request(market="CA", risk_level=3, hedge_us_equity=True, resample=False))
    us_a = sum(h["weight"] for h in a["holdings"] if h["sleeve"] == "ca_us_equity")
    us_b = sum(h["weight"] for h in b["holdings"] if h["sleeve"] == "ca_us_equity_hedged")
    assert us_b > 0.15 and abs(us_b - us_a) < 0.05


@needs_data
def test_review_exact_ticker_wins():
    from robokit import tools

    assert tools.etf_profile("AGG")["ticker"] == "AGG"
    assert tools.etf_profile("AGG.TO")["ticker"] == "AGG.TO"
    assert tools.etf_profile("BND")["ticker"] == "BND"


@needs_data
def test_review_hedged_swap_gets_hedged_history():
    from robokit.engine import Request, build_portfolio

    p = build_portfolio(Request(market="CA", risk_level=4, swaps={"ca_us_equity": "VSP.TO"}, resample=False))
    assert all(not n["converted_to_cad"] for n in p["history"]["VSP.TO"])
    gfc = [s for s in p["stress"] if s["scenario"].startswith("2008")][0]
    assert gfc["worst_fund"] == "VSP.TO" and gfc["worst_fund_return"] < -0.45  # hedged S&P 500 fell about 52%


@needs_data
def test_review_swaps_pass_the_eligibility_gate():
    from robokit.engine import Request, build_portfolio

    p = build_portfolio(Request(market="US", risk_level=5, swaps={"us_equity": "TQQQ"}, resample=False))
    assert "TQQQ" not in {h["ticker"] for h in p["holdings"]}
    assert any("TQQQ was not swapped in" in n["en"] for n in p["notes"])
    p = build_portfolio(Request(market="CA", risk_level=3, swaps={"ca_equity": "HXU.TO"}, resample=False))
    assert any("HXU.TO is not in the fund list" in n["en"] for n in p["notes"])
    assert "reference" not in {c["id"] for c in p["checks"]}


@needs_data
def test_review_currency_follows_the_fund():
    from robokit.engine import Request, build_portfolio, currency_of, returns_in

    assert currency_of("XUS-U.TO") == "USD" and currency_of("XIC.TO") == "CAD" and currency_of("SPY") == "USD"
    r_cad = returns_in("CA", ["XIC.TO"])["XIC.TO"].dropna()
    r_usd = returns_in("US", ["XIC.TO"])["XIC.TO"].dropna()
    assert not np.allclose(r_cad.tail(24), r_usd.tail(24))
    p = build_portfolio(Request(market="US", risk_level=3, satellites=["XIC.TO"], minimums={"XIC.TO": 0.08}, resample=False))
    assert any("XIC.TO trades in Canadian dollars" in n["en"] for n in p["notes"])


@needs_data
def test_review_stress_stand_ins_in_portfolio_currency():
    from robokit.engine import Request, build_portfolio

    p = build_portfolio(Request(market="CA", risk_level=4, satellites=["SCHD"], minimums={"SCHD": 0.10}, resample=False))
    oil = [s for s in p["stress"] if s["scenario"].startswith("2014")][0]
    assert oil["portfolio_return"] > 0.05  # the loonie fell: US holdings gained in CAD


@needs_data
def test_review_no_position_below_min_weight_and_clean_dollar_range():
    from robokit import tools
    from robokit.engine import Request, build_portfolio

    for sats, lvl in ((["QQQ", "SCHD", "XLK", "ARKK", "BITO"], 3), (["QQQ", "BITO", "GLD"], 2)):
        out = tools.call("build_portfolio", {"market": "US", "level": lvl, "satellites": sats})
        assert min(h["weight"] for h in out["holdings"]) >= 0.02 - 1e-9
    p = build_portfolio(Request(market="CA", risk_level=5, amount=10000, resample=False))
    assert set(p["projection"]["one_year_dollars"]) == {"p5", "p10", "p50", "p90"}


# ------------------------------------------------------------------ round-2 persona and review regressions (docs/qa/ux/round2/RANKED.md)
def test_round2_b2_ignored_for_wealth_goal():
    a = dict(FULL, A1="retirement", B2="once")
    w = prof.score(dict(a, A1="wealth"))
    assert w.capacity == prof.score({k: v for k, v in dict(a, A1="wealth").items() if k != "B2"}).capacity


def test_round2_single_cushion_wording_and_equal_levels():
    p = prof.score(dict(FULL, A2="partly", B1="20plus", B2="10plus", C1="4", C2="wait", C3="4", C4="both"))
    assert any("one step lower" in x and "together" not in x for x in p.explanation["en"])
    q = prof.score(dict(FULL, C1="5", C2="buy", C3="5", C4="missing"))
    assert q.capacity == q.tolerance and "Both point there" in q.explanation["en"][-1]


def test_round2_withdrawal_counts_only_months_paid_in_full():
    from robokit.projection import project

    r = np.zeros((60, 1))
    p = project(r, np.array([1.0]), np.array([0.0]), amount=1195, monthly_contribution=-10, years=10, n_paths=50)
    assert p["withdrawal"]["chance_lasts"] == 0.0 and p["withdrawal"]["p10_months"] == 119
    assert p["invested"] is None and p["prob_below_invested"] is None


def test_round2_first_year_does_not_depend_on_horizon():
    from robokit.projection import project

    rng = np.random.default_rng(1)
    r = rng.normal(0.005, 0.03, size=(200, 2))
    a = project(r, np.array([0.6, 0.4]), np.array([0.05, 0.03]), years=10)
    b = project(r, np.array([0.6, 0.4]), np.array([0.05, 0.03]), years=25)
    assert a["one_year"] == b["one_year"] and a["one_year_value"] == b["one_year_value"]


@needs_data
def test_round2_crisis_rows_never_dropped_silently():
    from robokit.engine import Request, build_portfolio

    p = build_portfolio(Request(market="US", risk_level=4, satellites=["BITO"], minimums={"BITO": 0.05}, resample=False))
    assert len(p["stress"]) == 7
    gfc = [s for s in p["stress"] if s["key"] == "gfc"][0]
    # round 3 (RESEARCH_LOG section 8, item 6): BITO is back-filled to 2004, so its 2008 row is kept and marked estimated
    assert gfc["portfolio_return"] is not None and "BITO" in gfc["estimated"]
    # a fund with no history at all for an episode still keeps the row, with the fund named (never dropped)
    assert all(s["portfolio_return"] is not None or s["not_estimable"] for s in p["stress"])


@needs_data
def test_round2_own_weights_edge_cases():
    from robokit import tools
    from robokit.engine import Request, build_portfolio

    p = build_portfolio(Request(market="CA", fixed_weights={"CASH.TO": 1.0}, resample=False))
    assert p["risk"]["level"] >= 1
    out = tools.call("build_portfolio", {"market": "CA", "fixed_weights": {"NOPE.TO": 1.0}})
    assert "error" in out and "None of the funds" in out["error"] and "NOPE.TO" in out["error"]


@needs_data
def test_round2_fee_rate_counts_known_funds_only():
    from robokit.engine import Request, build_portfolio

    # MNT.TO (bullion receipts) has no MER in either dataset; XUU.TO, used here before 3.0.3, now has one from the
    # team data layer's bridge
    p = build_portfolio(Request(market="CA", fixed_weights={"MNT.TO": 0.5, "XIC.TO": 0.5}, amount=100000, resample=False))
    xic = 0.0006
    assert abs(p["stats"]["fee_per_year"] - 0.5 * xic * 100000) < 1.0
    assert any(c["id"] == "fee_unknown" and "leave it out" in c["en"] for c in p["checks"])
