"""3.1.0: the self-rating (C0) and its second chance against the drop scenario (robokit/profile.py), and the guided
page's sourced holdings file. The browser side is tests/ui/test_guided.py; the conversation logic web/test_converse.mjs."""

import json
from pathlib import Path

import pytest

from robokit import profile as prof

ROOT = Path(__file__).resolve().parents[1]
BASE = {"A1": "wealth", "A2": "yes", "A3": "no", "B1": "20plus", "B4": "10to25", "B5": "very"}


def flags(a):
    return [f["id"] for f in prof.score({**BASE, **a}).flags]


def test_the_self_rating_maps_to_the_briefs_three_settings():
    # low and medium are the brief's settings; high is 5 since 3.3.1, so every tolerance question can reach the top level
    assert [o["level"] for o in prof.ITEM["C0"]["options"]] == [prof.PRESETS["low"], prof.PRESETS["mid"], 5]
    assert prof.ITEM["C0"]["optional"] is True
    assert "C0" not in prof.score(BASE).missing


@pytest.mark.parametrize(
    ("c0", "c2", "disagree"),
    [
        ("low", "buy", True),
        ("low", "wait", True),
        ("low", "sell_some", False),
        ("medium", "wait", False),
        ("medium", "sell_all", True),
        ("high", "buy", False),
        ("high", "wait", True),
        ("high", "dont_know", False),
    ],
)
def test_the_second_chance_fires_when_the_self_rating_and_the_drop_disagree(c0, c2, disagree):
    assert ("F_self_vs_drop" in flags({"C0": c0, "C2": c2})) is disagree


def test_the_second_chance_names_both_answers():
    f = next(f for f in prof.score({**BASE, "C0": "low", "C2": "buy"}).flags if f["id"] == "F_self_vs_drop")
    assert '"Buy more"' in f["en"] and "rated your comfort with risk as low" in f["en"] and f["items"] == ["C0", "C2"]


def test_without_the_self_rating_the_score_is_unchanged():
    a = {**BASE, "C1": "4", "C2": "wait", "C3": "3", "C4": "both"}
    r = prof.score(a)
    assert (r.capacity, r.tolerance, r.suggested_level) == (5, 3, 3)  # mean of 4, 4, 3, 3 rounded down
    assert prof.score({**a, "C0": "medium"}).tolerance == 3  # (4 + 4 + 3 + 3 + 3) / 5, rounded down


def test_setting_one_answer_aside_scores_the_other():
    kept_drop = prof.score({**BASE, "C2": "buy", "C1": "3"})
    kept_self = prof.score({**BASE, "C0": "low", "C1": "3"})
    assert kept_drop.tolerance == 4 and kept_self.tolerance == 2


def test_the_default_funds_holdings_are_sourced():
    h = json.loads((ROOT / "data" / "fund_holdings.json").read_text(encoding="utf-8"))
    assert len(h) == 10
    for t, r in h.items():
        assert r["source_url"].startswith("https://") and r["as_of"] and r["holdings"], t
        assert all(x["quote"] for x in r["holdings"]), t
