"""3.3.0: the team's cleaned-up feedback on the prototype (Penguru review, tab 3). The withdrawal-period question (B2)
left the guided page as a repeat of the horizon question; the page now fills it in from the goal, and the score marks it
as an assumption without changing the result. The page's side is web/test_converse.mjs and tests/ui/test_guided.py."""

from robokit import profile as prof

BASE = {"A1": "home", "A2": "yes", "A3": "no", "B1": "2to4", "B2": "once", "B5": "very", "C0": "medium", "C2": "wait"}


def _why(p):
    return " ".join(p.explanation["en"])


def test_an_assumed_answer_scores_exactly_like_a_given_one():
    given, assumed = prof.score(BASE), prof.score(BASE, assumed={"B2"})
    assert (assumed.capacity, assumed.tolerance, assumed.suggested_level, assumed.status) == (
        given.capacity,
        given.tolerance,
        given.suggested_level,
        given.status,
    )


def test_the_explanation_says_the_withdrawal_plan_was_assumed():
    assert "for how long: all at once, assumed from your goal" in _why(prof.score(BASE, assumed={"B2"}))
    assert "assumed" not in _why(prof.score(BASE))


def test_money_needed_all_at_once_within_two_years_still_gets_no_stock_mix():
    assert prof.score(dict(BASE, B1="lt2"), assumed={"B2"}).status == "not_ready"


def test_building_wealth_still_ignores_the_withdrawal_plan():
    p = prof.score(dict(BASE, A1="wealth"), assumed={"B2"})
    assert "not asked (no fixed date)" in _why(p) and "assumed" not in _why(p)
