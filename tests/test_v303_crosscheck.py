"""3.0.3: labels the team's independent ETF data layer (github.com/shreyajane23/robokit-data) found wrong, and its
bridge file (docs/DECISIONS.md, "After the run: the data layer's cross-check").

Two name rules read the wrong thing: "Global X" (an issuer's brand) as a global region, and "ex U.S." as the US.
The leverage rules lost the sign in "(-3X)" and let a fund category alone make a fund leveraged, so "Daily Inverse"
funds became +2x and "Enhanced" or crypto funds 2x. The bridge fills MER blanks and adds fund facts."""

from __future__ import annotations

import pandas as pd
import pytest

from robokit import universe
from robokit.classify import classify_row, leverage_of
from tests.test_v2 import needs_data


def _row(yahoo, name, market="CA", style=""):
    return classify_row(pd.Series({"yahoo": yahoo, "name": name, "market": market, "tmx_investmentstyle": style}))


@pytest.mark.parametrize(
    "yahoo, name, market, region",
    [
        ("HXS.TO", "Global X S&P 500 Corporate Class ETF", "CA", "US"),
        ("QQCC.TO", "Global X NASDAQ-100 Covered Call ETF", "CA", "US"),
        ("HTB.TO", "Global X US 7-10 Year Treasury Bond Index Corporate Class ETF", "CA", "US"),
        ("DLR.TO", "Global X U.S. Dollar Currency ETF", "CA", "US"),
        ("VDU.TO", "Vanguard FTSE Developed All Cap ex U.S. Index ETF", "CA", "International developed"),
        ("VIU.TO", "Vanguard FTSE Developed All Cap ex North Amer Idx ETF", "CA", "International developed"),
        ("VI.TO", "Vanguard FTSE Developed All Cap ex Nrth Amer Idx ETF (CAD-Hdd)", "CA", "International developed"),
        ("VBG.NE", "Vanguard Global ex-U.S. Aggregate Bond Index ETF (CAD-hedged)", "CA", "International developed"),
        ("HBA.TO", "Hamilton Australian Bank Equal-Weight Index ETF", "CA", "Asia-Pacific"),
        # a theme fund whose name names no region stays global, wherever it is listed
        ("URA", "Global X Uranium ETF", "US", "Global"),
        ("LIT", "Global X Lithium & Battery Tech ETF", "US", "Global"),
        ("HXT.TO", "Global X S&P/TSX 60 Index Corporate Class ETF", "CA", "Canada"),
        ("XAW.TO", "iShares Core MSCI All Country World ex Canada Index ETF", "CA", "Global"),
    ],
)
def test_region_reads_the_index_not_the_brand(yahoo, name, market, region):
    assert _row(yahoo, name, market)["region"] == region


@pytest.mark.parametrize(
    "name, lev",
    [
        ("MegaShort (-3X) S&P 500 Daily Leveraged Alternative ETF", -3.0),
        ("SavvyShort (-2X) TSLA ETF", -2.0),
        ("MegaLong (3X) Canadian Banks Daily Leveraged Alternative ETF", 3.0),
        ("BetaPro -3x S&P/TSX 60 Daily Leveraged Bear alternative ETF", -3.0),
        ("MicroSectors 3? Long Artificial Intelligence (AI) ETNs", 3.0),  # "×" garbled in the listing file
        ("MicroSectors -3? Short Artificial Intelligence (AI) ETNs", -3.0),
        ("ETRACS 2xMonthly Pay Leveraged Preferred Stock Index ETN", 2.0),
        ("Hamilton Enhanced Canadian Bank ETF 1.25x", 1.25),
        ("Is this a 3? test", 1.0),
        ("Vanguard S&P 500 Index ETF", 1.0),
    ],
)
def test_leverage_keeps_its_sign(name, lev):
    assert leverage_of(name)[0] == lev


@pytest.mark.parametrize(
    "name, style, lev",
    [
        ("BetaPro S&P/TSX 60 Daily Inverse ETF", "Leverage Strategy", -1.0),
        ("BetaPro S&P 500 Daily Inverse ETF", "Leverage Strategy", -1.0),
        ("BetaPro Natural Gas Inverse Leveraged Daily Bear ETF", "Leverage Strategy", -2.0),
        ("BetaPro Crude Oil Daily Bull ETF", "Leverage Strategy", 2.0),
        # a category alone does not make a daily-reset product
        ("Global X Enhanced All-In-One Commodity Producers Equity Covered Call ETF", "Leverage Strategy", 1.0),
        ("Harvest Diversified Monthly Income ETF - Class A Units", "Leverage Strategy", 1.0),
        ("Purpose Solana ETF Currency Hedged Units", "Trading-Leveraged Miscellaneous", 1.0),
    ],
)
def test_a_leverage_category_needs_a_geared_name(name, style, lev):
    r = _row("X.TO", name, style=style)
    assert r["leverage"] == lev and r["inverse"] == (lev < 0)


def _universe():
    return pd.DataFrame(
        {
            "yahoo": ["A.TO", "B.TO", "C.TO", "D.TO", "E.TO"],
            "mer": [0.002, None, None, None, None],
            "aum": [5e8, None, None, None, None],
            "why": ["", "", "", "", None],
        }
    )


def test_the_bridge_fills_only_blanks_and_plausible_values(tmp_path, monkeypatch):
    monkeypatch.setattr(universe, "DATA_DIR", tmp_path)
    pd.DataFrame(
        {
            "yahoo": ["A.TO", "B.TO", "C.TO", "D.TO", "Z.TO"],
            "rk_mer": [0.009, 0.004, 0.0003, None, 0.01],  # C: 0.03%, most likely the wrong unit
            "rk_aum": [1e9, 2e8, 0.0, None, 1e8],  # C: zero means missing in the source
            "rk_fund_age_years": [10.0, 3.2, 1.0, None, 2.0],
            "other": [1, 2, 3, 4, 5],
        }
    ).to_csv(tmp_path / universe.TEAM_BRIDGE, index=False)
    U = universe.add_team_data(_universe()).set_index("yahoo")
    assert U.at["A.TO", "mer"] == 0.002 and U.at["A.TO", "aum"] == 5e8  # ours is kept
    assert U.at["B.TO", "mer"] == 0.004 and U.at["B.TO", "aum"] == 2e8 and "team's data layer" in U.at["B.TO", "why"]
    assert pd.isna(U.at["C.TO", "mer"]) and pd.isna(U.at["C.TO", "aum"])
    assert U.at["B.TO", "rk_fund_age_years"] == 3.2 and "other" not in U.columns and "Z.TO" not in U.index


def test_without_the_bridge_the_universe_is_unchanged(tmp_path, monkeypatch):
    monkeypatch.setattr(universe, "DATA_DIR", tmp_path)
    U = _universe()
    pd.testing.assert_frame_equal(universe.add_team_data(U), U)


@needs_data
def test_the_cross_check_corrections_reach_the_fund_list():
    U = pd.read_pickle(universe.DATA_DIR / "universe.pkl").set_index("yahoo")
    for t in ("HXS.TO", "HXQ.TO", "USCC.TO", "USCL.TO", "QQCC.TO", "HTB.TO", "DLR.TO"):
        assert U.at[t, "region"] == "US", t
    for t in ("VDU.TO", "VEF.TO"):
        assert U.at[t, "region"] == "International developed", t
    for t in ("SPYD.TO", "QQQD.TO", "SOXD.TO", "CGMD.TO"):
        assert U.at[t, "leverage"] == -3.0 and U.at[t, "inverse"], t
    assert U.at["CNDI.TO", "leverage"] == -1.0 and U.at["HND.TO", "leverage"] == -2.0
    assert U.at["SOLL.TO", "leverage"] == 1.0 and U.at["CMCL.TO", "leverage"] == 1.0
    # kept on purpose: S&P/TSX indices of miners listed in Canada (Global would put them in the international slot),
    # and the Mint's bullion receipts (commodities are global; Canada would take MNT out of the gold slot)
    assert U.at["XGD.TO", "region"] == "Canada" and U.at["XBM.TO", "region"] == "Canada"
    assert U.at["MNT.TO", "region"] == "Global" and U.at["MNS.TO", "region"] == "Global"
