"""3.2.0: the data rules in the team's PRD v3. D2: a category outside the locked lists is flagged, never used; D3: a
missing value stays blank (dates are no longer written as the text "NaT"). The page's side is web/test_converse.mjs."""

import json
from pathlib import Path

from robokit.classify import ASSET_CLASSES, REGIONS, STRATEGIES, locked_category_problem

ROOT = Path(__file__).resolve().parents[1]


def _rows():
    ca = json.loads((ROOT / "web" / "data" / "ca.json").read_text(encoding="utf-8"))
    cols = ca["universe"]["columns"]
    return [dict(zip(cols, r)) for r in ca["universe"]["rows"]]


def test_a_category_outside_the_locked_lists_is_flagged():
    assert locked_category_problem({"asset_class": "Equity", "region": "US", "strategy": "Active"}) == ""
    assert locked_category_problem({"asset_class": "Equities (US)", "region": "US", "strategy": "Active"}) == (
        "category not in the locked list: asset_class 'Equities (US)'"
    )
    assert "region 'Mars'" in locked_category_problem({"asset_class": "Equity", "region": "Mars", "strategy": "Active"})
    assert "strategy 'Hot tips'" in locked_category_problem({"asset_class": "Equity", "region": "US", "strategy": "Hot tips"})


def test_a_missing_category_stays_blank_rather_than_flagged():
    assert locked_category_problem({"asset_class": None, "region": "US", "strategy": float("nan")}) == ""


def test_every_published_fund_is_inside_the_locked_lists():
    bad = [(r["yahoo"], locked_category_problem(r)) for r in _rows() if locked_category_problem(r)]
    assert bad == []


def test_the_browser_engine_uses_the_same_lists():
    js = (ROOT / "web" / "robokit.js").read_text(encoding="utf-8")
    for v in (*ASSET_CLASSES, *REGIONS, *STRATEGIES):
        assert f"'{v}'" in js, v


def test_missing_dates_are_blank_not_the_text_nat():
    rows = _rows()
    assert not [r["yahoo"] for r in rows if "NaT" in (r.get("first_month"), r.get("last_close_date"))]
