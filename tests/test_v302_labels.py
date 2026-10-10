"""3.0.2: currency-hedging labels the name rule got wrong (docs/DECISIONS.md, "After the run: currency-hedging labels").

The hedged flag decides which stand-in extends a young fund before it existed (robokit/history.py: a hedged fund gets
foreign returns unconverted, an unhedged one gets them converted to CAD), and which holdings the page counts as foreign
currency exposure. It is read from the fund's name, so a unit whose name carries no hedging word needs an
issuer-sourced override, and three naming patterns needed fixing."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from robokit import __version__
from robokit.classify import LABEL_OVERRIDES, classify_row
from tests.test_v2 import needs_data

ROOT = Path(__file__).resolve().parents[1]


def _hedged(yahoo: str, name: str) -> bool:
    return bool(classify_row(pd.Series({"yahoo": yahoo, "name": name, "market": "CA"}))["hedged"])


@pytest.mark.parametrize(
    "yahoo, name, hedged",
    [
        ("CGL.TO", "iShares Gold Bullion ETF (CAD-Hedged)", True),
        ("CGL-C.TO", "iShares Gold Bullion ETF (Non-Hedged)", False),
        ("VALT-B.TO", "CI Gold Bullion ETF UnHedged", False),
        ("KILO-B.TO", "Purpose Gold Bullion Non-FX Hedged", False),  # was True: "Non-FX Hedged" means not hedged
        ("BTCC-B.TO", "Purpose Bitcoin ETF Non-Currency Hedged Units", False),  # was True
        ("SBT-B.TO", "Silver Bullion Trust ETF Non-Currency Hedged Units", False),  # was True
        ("BTCX.TO", "CI Galaxy Bitcoin ETF C$ Hedged Series", True),  # was False: "C$ Hedged Series" is hedged to CAD
        ("FCVH.TO", "Fidelity U.S. Value Currency Neutral ETF", True),  # was False: Fidelity hedges USD to CAD
        ("CGIN-U.TO", "CI Global Investment Grade ETF (ETF US$ Hedged Series)", False),  # US$ unit, unchanged
        ("VI.TO", "Vanguard FTSE Developed All Cap ex North America Index ETF (CAD-Hdd)", True),  # B46, unchanged
    ],
)
def test_the_name_rule_reads_hedging_words(yahoo, name, hedged):
    assert _hedged(yahoo, name) is hedged


def test_issuer_overrides_apply_and_say_where_they_come_from():
    for yahoo, (fix, source) in LABEL_OVERRIDES.items():
        assert set(fix) <= {"hedged", "derivatives"} and fix
        assert ":" in source and "(" in source  # "<issuer>: <what it says> (<document>)"
        row = classify_row(pd.Series({"yahoo": yahoo, "name": "A plain fund name", "market": "CA"}))
        for k, v in fix.items():
            assert row[k] == v
        assert source in row["why"]
    # VALT's name carries no hedging word; only the override makes it hedged
    assert _hedged("VALT.TO", "CI Gold Bullion ETF") is True
    assert _hedged("VALT-U.TO", "CI Gold Bullion ETF USD") is False


@needs_data
def test_the_fund_list_carries_the_corrected_labels():
    from robokit import engine as E

    U = E._load()[0].set_index("yahoo")
    for t in LABEL_OVERRIDES:
        if t in U.index:
            for k, v in LABEL_OVERRIDES[t][0].items():
                assert U.at[t, k] == v, (t, k)
    for t, want in (("KILO-B.TO", False), ("BTCC-B.TO", False), ("SBT-B.TO", False), ("FCVH.TO", True), ("VALT-B.TO", False)):
        if t in U.index:
            assert bool(U.at[t, "hedged"]) is want, t


@needs_data
def test_valt_is_extended_with_unconverted_gold_before_2021():
    """A CAD-hedged gold fund earns roughly gold's own-currency return, so its stand-in is GLD in US dollars,
    unconverted; CGL-C (non-hedged) no longer qualifies."""
    from robokit.engine import Request, build_portfolio

    p = build_portfolio(Request(market="CA", risk_level=4, resample=False))
    notes = [n for n in p["history"]["VALT.TO"] if n["used"]]
    assert [n["proxy"] for n in notes] == ["GLD"]
    assert not notes[0]["converted_to_cad"]


def test_the_web_bundle_and_the_plugin_manifests_carry_the_engine_version():
    core = json.loads((ROOT / "web" / "data" / "core.json").read_text(encoding="utf-8"))
    assert core["meta"]["engine_version"] == __version__
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert plugin["version"] == __version__
    market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    assert all(p["version"] == __version__ for p in market["plugins"])


def test_the_web_bundle_marks_valt_hedged():
    ca = json.loads((ROOT / "web" / "data" / "ca.json").read_text(encoding="utf-8"))
    cols = ca["universe"]["columns"]
    row = next(r for r in ca["universe"]["rows"] if r[cols.index("yahoo")] == "VALT.TO")
    assert row[cols.index("hedged")] is True
    gold = next(s for s in ca["sleeves"] if s["key"] == "ca_gold")
    assert gold["proxies_hedged"] == [{"ticker": "GLD", "convert": False}]


def test_the_point_in_time_shelf_takes_only_funds_the_swap_gate_admits(monkeypatch):
    """HUG tracks gold futures (issuer override), so the swap gate refuses it in the gold slot. The strict point-in-time
    shelf (E2) must apply the same like-for-like rule: with no admissible fund old enough, the slot is left out."""
    from robokit import research

    c = pd.DataFrame(
        {
            "yahoo": ["VALT.TO", "KILO.TO", "HUG.TO"],
            "derivatives": ["", "", "futures"],
            "satellite_only": [False, False, True],
            "theme": ["", "", ""],
        }
    )
    monkeypatch.setattr(research, "_load_all", lambda: (None, None, None, None))
    monkeypatch.setattr(research, "default_sleeves", lambda market: ["ca_gold"])
    monkeypatch.setattr(research, "candidates", lambda U, sleeve: c)
    monkeypatch.setattr(research, "own_history_months", lambda d: pd.Series({"VALT.TO": 10, "KILO.TO": 20, "HUG.TO": 150}))
    assert research.pit_shelf("CA", pd.Timestamp("2016-12-31")) == ({}, [], {})
    monkeypatch.setattr(research, "own_history_months", lambda d: pd.Series({"VALT.TO": 10, "KILO.TO": 40, "HUG.TO": 150}))
    assert research.pit_shelf("CA", pd.Timestamp("2023-12-31"))[0] == {"ca_gold": "KILO.TO"}
