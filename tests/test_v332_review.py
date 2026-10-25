"""Regression tests for 3.3.2: the whole-repository review of 25 Oct 2026 (docs/VERIFICATION.md section 8.15). Each
finding was reproduced by running the code before it was fixed; the letters are the findings' ids in that record."""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
import pytest

from robokit import tools
from robokit.engine import _load
from robokit.shelf import candidates, sleeves_for
from tests.test_v2 import needs_data


# ------------------------------------------------------------------ A: the reference shelf is ordered by its score
@pytest.mark.parametrize("market", ["CA", "US"])
def test_a_the_shelf_lists_the_scores_first_fund_first_and_cost_sorts_by_fee(market):
    U, _, _, _ = _load()
    shelf = tools.reference_shelf(market)
    for s, row in zip(sleeves_for(market), shelf["sleeves"], strict=True):
        assert row["funds"][0]["ticker"] == candidates(U, s).iloc[0]["yahoo"], s.key
    assert tools.reference_shelf(market, sort_by="score") == shelf
    for row in tools.reference_shelf(market, sort_by="cost")["sleeves"]:
        fees = [f["mer"] for f in row["funds"] if f["mer"] is not None]
        assert fees == sorted(fees), row["sleeve"]
    assert "sort_by" in tools.call("reference_shelf", {"market": market, "sort_by": "fit"})["error"]


def test_a_no_tool_text_calls_the_shelf_the_lowest_cost():
    from robokit import mcp_server

    texts = [tools.reference_shelf.__doc__, mcp_server.reference_shelf.__doc__, tools.risk_ladder("CA")["note"]]
    assert not any("lowest-cost" in t for t in texts)


# ------------------------------------------------------------------ K: --help never starts a download or a rewrite
@pytest.mark.parametrize(
    "cmd, action",
    [("refresh", "robokit.refresh.refresh"), ("bundle", "robokit.bundle.export_bundle"), ("status", "robokit.tools.data_status")],
)
@pytest.mark.parametrize("flag, code", [("--help", 0), ("--no-such-flag", 2)])
def test_k_cli_commands_parse_their_arguments_before_acting(monkeypatch, cmd, action, flag, code):
    from robokit.__main__ import main

    def must_not_run(*a, **k):
        raise AssertionError(f"{action} ran on `robokit {cmd} {flag}`")

    monkeypatch.setattr(action, must_not_run)
    monkeypatch.setattr(sys, "argv", ["robokit", cmd, flag])
    with pytest.raises(SystemExit) as e:
        main()
    assert e.value.code == code


# ------------------------------------------------------------------ M: compare_etfs on funds without a price series
def test_m_compare_etfs_takes_a_fund_without_a_price_series_and_a_repeated_fund():
    U, R, _, _ = _load()
    bare = next(y for y in U["yahoo"] if y not in R.columns)  # snapshot: a fund outside the eligible set; local: no prices
    r = tools.call("compare_etfs", {"tickers": ["XIC.TO", bare]})
    assert "error" not in r
    assert [f["ticker"] for f in r["funds"]] == ["XIC.TO", bare]
    assert r["correlation_60m"] is None  # one fund with a series: nothing to correlate
    r = tools.call("compare_etfs", {"tickers": ["XIC.TO", "XIC", "ZAG.TO"]})
    assert "error" not in r and [f["ticker"] for f in r["funds"]] == ["XIC.TO", "ZAG.TO"]
    assert set(r["correlation_60m"]) == {"XIC.TO", "ZAG.TO"}
    json.dumps(r)


# ------------------------------------------------------------------ N: a missing date is sent as null
def test_n_clean_turns_a_missing_date_into_none():
    assert tools._clean(pd.NaT) is None
    assert tools._clean({"first_month": pd.NaT, "d": np.datetime64("NaT"), "t": pd.Timestamp("2026-08-31")}) == {
        "first_month": None,
        "d": None,
        "t": "2026-08-31",
    }


@needs_data
def test_n_profiles_of_funds_without_a_first_month_can_be_sent():
    U, _, _, _ = _load()
    y = U.loc[U["first_month"].isna(), "yahoo"].iloc[0]
    p = tools.etf_profile(y)
    assert p["found"] and p["first_month"] is None
    json.dumps(p)
    json.dumps(tools.call("compare_etfs", {"tickers": [y, "XIC.TO"]}))


# ------------------------------------------------------------------ O: the self-rating is asked with the tolerance questions
def test_o_the_question_note_says_c0_is_asked_and_only_d1_d2_come_after():
    note = tools.get_questions()["note"]
    assert "C0" in note and "D1, D2" in note
    assert "(the two knowledge checks)" not in note


# ------------------------------------------------------------------ P: an amount just under a minimum never reads as the minimum
def test_p_exclusion_amounts_are_rounded_down():
    from robokit.universe import below

    assert below(19.95e6, 1e6) == "19.9"
    assert below(19_999_999, 1e6) == "19.9"
    assert below(49_999, 1e3) == "49.9"
    assert below(2e6, 1e6) == "2"


# ------------------------------------------------------------------ AE: the back-test shown is the v2 engine's, and says so
def test_ae_the_backtest_tool_names_the_engine_it_tested():
    r = tools.backtest_summary("CA", 3)
    assert r["available"]
    assert "v2 engine" in r["label"] and "not of the current engine" in r["label"]
    assert "60-month" in r["method"] and "50 resampling draws" in r["method"] and "E1" in r["method"]
