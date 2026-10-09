"""The swap gate and the fund labels after the E7(e) taxonomy audit (docs/research/e7e_taxonomy.md).

The audit found that the old gate (eligible, not satellite-only, same asset class and region as the slot's fund) let
narrow funds into core slots: an equity name the rules could not place was labelled "Broad market", and some
single-country funds were labelled region "US". A swap must now pass the slot's own rule, the rule that picked the
reference fund (shelf.slot_members), and a stock fund is labelled broad only on positive evidence. The browser side
is in web/test_safety.mjs."""

from __future__ import annotations

import pandas as pd
import pytest

from robokit.classify import classify_row
from robokit.universe import broad_equity, satellite_only
from tests.test_v2 import needs_data


def _build(market: str, **kw):
    from robokit.engine import Request, build_portfolio

    return build_portfolio(Request(market=market, risk_level=3, resample=False, **kw))


def _held(p) -> set[str]:
    return {h["ticker"] for h in p["holdings"]}


# ------------------------------------------------------------------ the gate: the slot's own rule
@needs_data
@pytest.mark.parametrize(
    "market,slot,fund,why",
    [
        ("US", "us_equity", "XLK", "a sector fund"),
        ("US", "us_equity", "FTXH", "a pharmaceuticals fund"),
        ("US", "us_equity", "SPYD", "a high-dividend S&P 500 fund"),
        ("US", "us_equity", "QQQ", "the Nasdaq-100"),
        ("US", "us_equity", "TUR", "a single foreign country labelled region US"),
        ("US", "us_equity", "MAYW", "a buffer fund"),
        ("US", "us_agg_bond", "HYLB", "high yield in the aggregate-bond slot"),
        ("US", "us_short_treasury", "TUA", "a futures-based fund the slot's name rule admits"),
        ("CA", "ca_equity", "XMA.TO", "a materials sector fund"),
        ("CA", "ca_gold", "SBT.TO", "silver in the gold slot"),
    ],
)
def test_a_fund_outside_the_slots_rule_is_not_swapped_in(market, slot, fund, why):
    p = _build(market, swaps={slot: fund})
    assert fund not in _held(p), why
    assert any(f"{fund} is not one of the funds the" in n["en"] for n in p["notes"])


@needs_data
@pytest.mark.parametrize(
    "market,slot,fund,sleeves",
    [
        ("US", "us_equity", "VTI", None),
        ("CA", "ca_equity", "ZCN.TO", None),
        ("CA", "ca_us_equity", "VSP.TO", None),  # the hedged twin: hedging is the user's choice
        ("US", "us_small_cap", "IWM", ["us_equity", "us_agg_bond", "us_small_cap", "us_cash"]),  # a segment slot
    ],
)
def test_a_fund_the_slots_rule_admits_is_swapped_in(market, slot, fund, sleeves):
    p = _build(market, swaps={slot: fund}, sleeves=sleeves)
    assert fund in _held(p)


@needs_data
@pytest.mark.parametrize("esg", [False, True])
def test_every_reference_fund_and_every_offered_alternative_passes_the_gate(esg):
    """The page never offers a fund the gate would refuse (a futures-based fund the name rule admits, for one)."""
    from robokit.engine import _load
    from robokit.shelf import SLEEVES, build_shelf, slot_members

    U = _load()[0]
    for market in ("CA", "US"):
        for _, r in build_shelf(U, market, prefer_esg=esg).iterrows():
            mem = slot_members(U, SLEEVES[r.sleeve], prefer_esg=esg)
            for t in ([r.ticker] if r.ticker else []) + list(r.alternatives):
                assert t in mem, (market, r.sleeve, t)


@needs_data
def test_the_slot_rule_alone_is_not_enough():
    """PBP (an S&P 500 buy-write fund) passes the US-stock slot's name rule but is an option-income fund: the
    like-for-like filter, an independent second check, keeps it out."""
    from robokit.engine import _load
    from robokit.shelf import SLEEVES, candidates, slot_members

    U = _load()[0]
    assert "PBP" in set(candidates(U, SLEEVES["us_equity"]).yahoo)
    assert "PBP" not in slot_members(U, SLEEVES["us_equity"])


@needs_data
def test_the_point_in_time_shelf_is_never_refused_by_the_gate():
    """E2 (strict point-in-time) puts each December's best fund with 36 months of history in each slot by a swap; the
    gate must accept every one, so the registered E2 result does not depend on the gate."""
    from robokit.engine import _load
    from robokit.research import pit_shelf
    from robokit.shelf import SLEEVES, slot_members

    U = _load()[0]
    for market in ("CA", "US"):
        for year in range(2000, 2026):
            swaps, _, _ = pit_shelf(market, pd.Timestamp(f"{year}-12-31"))
            for k, t in swaps.items():
                assert t in slot_members(U, SLEEVES[k]), (market, year, k, t)


# ------------------------------------------------------------------ labels: broad only on positive evidence
def _row(name: str, market: str = "US") -> pd.Series:
    return pd.Series({"name": name, "market": market, "yahoo": "X", "in_tmx": market == "CA"})


@pytest.mark.parametrize(
    "name,theme",
    [
        ("First Trust Nasdaq Pharmaceuticals ETF", "Healthcare"),
        ("iShares U.S. Industrials ETF", "Industrials"),
        ("AllianzIM U.S. Large Cap Buffer20 May ETF", "Buffer / defined outcome"),
        ("First Trust NASDAQ Cybersecurity ETF", "Technology / AI"),
        ("iShares MSCI France Index Fund", "Single country"),
        ("Invesco RAFI Developed Markets ex-U.S. ETF", "Factor: other"),
        ("Putnam BDC Income ETF", "Financials / banks"),
    ],
)
def test_narrow_names_get_their_theme(name, theme):
    assert theme in classify_row(_row(name))["theme"].split("; ")


def test_a_region_without_a_country_is_not_single_country():
    assert "Single country" not in classify_row(_row("iShares MSCI Emerging Markets ex China ETF"))["theme"]


@pytest.mark.parametrize(
    "name,options",
    [
        ("iShares Premium Money Market ETF", False),  # a money-market fund, not an option premium
        ("Fidelity Enhanced High Yield ETF", False),  # "enhanced" alone is a manager's word (examiner finding)
        ("Xtrackers MSCI EAFE Hedged Equity ETF", False),  # currency hedging
        ("First Trust BuyWrite Income ETF", True),
        ("JPMorgan Equity Premium Income ETF", True),
        ("Global X Enhanced Income ETF", True),
    ],
)
def test_the_options_tag(name, options):
    assert ("options" in classify_row(_row(name))["derivatives"]) is options


def test_a_slot_with_no_reference_fund_takes_no_swap():
    from dataclasses import replace

    from robokit.shelf import SLEEVES, slot_members

    U = _labelled(["Vanguard Total Stock Market ETF"]).assign(
        yahoo="VTI", market="US", aum=1e9, dollar_volume=1e8, mer=0.0003, history_months=200, hedged=False, currency="USD"
    )
    impossible = replace(SLEEVES["us_equity"], include=r"no fund has this name")
    assert slot_members(U, impossible) == []


def _labelled(names: list[str]) -> pd.DataFrame:
    rows = []
    for n in names:
        c = classify_row(_row(n))
        rows.append({"name": n, "eligible": True, **c})
    return pd.DataFrame(rows)


def test_broad_index_funds_are_broad_and_narrow_ones_are_satellites():
    broad = [
        "Vanguard Total Stock Market ETF",
        "iShares Core S&P 500 ETF",
        "Vanguard Total International Stock ETF",
        "Vanguard FTSE Emerging Markets ETF",
        "Schwab International Equity ETF",
        "Vanguard ESG U.S. Stock ETF",
        "iShares Russell 3000 Fund",
    ]
    narrow = [
        "Subversive Congressional Republicans Trading ETF",  # no theme the rules can place: not broad by default
        "JPMorgan Equity Focus ETF",
        "State Street SPDR Portfolio S&P 500 High Dividend ETF",
        "iShares S&P/TSX Capped Materials Index ETF",
        "Invesco S&P 500 High Beta ETF",
        "Overlay Shares Large Cap Equity ETF",
    ]
    U = _labelled(broad + narrow)
    assert list(broad_equity(U)) == [True] * len(broad) + [False] * len(narrow)
    assert list(satellite_only(U)) == [False] * len(broad) + [True] * len(narrow)
