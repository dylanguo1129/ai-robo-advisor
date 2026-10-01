"""The self-check: gates, the clarifying card, changing answers, pausing and resuming, the level sheets and the result."""

import re

import pytest

pytestmark = pytest.mark.ui

# Answers that agree: the situation and the comfort with swings both point to level 3. A horizon under 10 years keeps the
# ladder behind the scenario questions as it was built at page load, so those questions are ready at once.
CALM = [
    ("A2", "yes"),
    ("A3", "no"),
    ("B1", "5to9"),
    ("B2", "6to10"),
    ("B4", "10to25"),
    ("B5", "very"),
    ("C1", "3"),
    ("C2", "wait"),
    ("C3", "3"),
    ("C4", "both"),
]
# Comfortable with large swings (tolerance 5); the situation allows level 4.
BOLD = [
    ("A2", "yes"),
    ("A3", "no"),
    ("B1", "5to9"),
    ("B2", "10plus"),
    ("B4", "10to25"),
    ("B5", "very"),
    ("C1", "5"),
    ("C2", "buy"),
    ("C3", "5"),
    ("C4", "missing"),
]
LEVEL_MOVE = re.compile(r"follows your self-check|mix now uses|mix moved to|Level set to")
# After a reload, the numbers behind the level chooser arrive a second late (as on a slow phone), so a reopened result is drawn
# before they land.
SLOW_LADDER_AFTER_RELOAD = """(() => { if (!sessionStorage.getItem('slow-ladder')) return; const post = Worker.prototype.postMessage;
  Worker.prototype.postMessage = function (m, ...r) {
    if (m && m.type === 'ladder') { setTimeout(() => post.call(this, m, ...r), 1000); return; }
    return post.call(this, m, ...r); }; })();"""
CHOOSER = """() => ({ pressed: [...document.querySelectorAll('.card-check .lad-row[aria-pressed="true"]')].map(b => Number(b.dataset.l)),
  use: document.querySelector('.card-check [data-use]').textContent, level: robokit.st.level })"""
SUMMARY = "document.querySelector('.card-summary .summary-line').textContent"
# Counts the page's saves, which wait 300 ms before writing, and sets a marker 300 ms after each: once every marker has
# fired, no save is still waiting to write.
WATCH_SAVES = """() => { const app = window.robokit, w = app.__saves = { asked: 0, ran: 0 }, save = app.save;
  app.save = function (...a) { w.asked++; const r = save.apply(this, a); setTimeout(() => { w.ran++; }, 300); return r; }; }"""
STORED = """() => { const s = JSON.parse(localStorage.getItem('robokit2.state') || 'null');
  return s && { goal: s.answers.A1, savings: s.answers.A2 ?? null, amount: s.amount }; }"""


def on(p, step):
    p.pg.wait_for_selector(f'.card-check[data-q="{step}"]')


def back_to(p, step):
    """Tap Back on the self-check until `step` is on screen."""
    while (now := p.js("robokit.st.check.step")) != step:
        p.pg.click(".card-check [data-back]")
        p.pg.wait_for_function("s => robokit.st.check.step !== s", arg=now)


def not_ready(p):
    """Open the self-check and answer it so that the money is needed within two years: the not-ready result."""
    p.start_check("retirement", 10000)
    p.answer(("A2", "yes"), ("A3", "no"), ("B1", "lt2"), ("B2", "once"))
    on(p, "result")
    p.settled()


def review(p, step):
    """On the result: open 'Review your answers' and tap Change next to one answer."""
    if not p.js("document.querySelector('.card-check details.review').open"):
        p.pg.click(".card-check details.review summary")
    p.pg.click(f'.card-check [data-goto="{step}"] >> nth=0')
    on(p, step)


def test_the_level_moves_only_once_every_question_is_answered(page_factory):
    """The level moves only once every question is answered, with one note; the one-year question's step is announced once."""
    p = page_factory()
    p.js("""() => { window.__said = []; const a = document.querySelector('#announcer');
      new MutationObserver(() => { if (a.textContent) window.__said.push(a.textContent); })
        .observe(a, { childList: true, characterData: true, subtree: true }); }""")
    p.start_check("retirement", 25000)  # a new amount: the ladder behind the scenario questions is rebuilt while they open
    p.answer(("A2", "yes"), ("A3", "no"), ("B1", "5to9"), ("B2", "10plus"), ("B4", "10to25"), ("B5", "very"), ("C1", "4"))
    on(p, "C2")
    p.settled()
    assert [n for n in p.notes() if LEVEL_MOVE.search(n)] == []
    assert p.js("robokit.st.level") == 3
    label = p.js(
        "(() => { const A = robokit, s = A.scoredSteps(); return A.L.stepTitle + ': ' + A.L.stepMeta(s.indexOf('C1') + 1, s.length); })()"
    )
    assert sum(t.count(label) for t in p.js("window.__said")) == 1
    p.answer(("C2", "wait"), ("C3", "4"), ("C4", "missing"))
    on(p, "result")
    p.settled()
    moves = [n for n in p.notes() if LEVEL_MOVE.search(n)]
    assert len(moves) == 1 and "level 4" in moves[0]
    assert p.js("robokit.st.level") == 4


def test_a_tray_level_picked_mid_check_is_a_plain_choice(page_factory):
    """A tray level picked mid-check is applied without the explore sheet, and later answers never say 'your answers changed'."""
    p = page_factory()
    p.start_check("retirement", 10000)
    p.answer(*CALM[:6], ("C1", "4"))
    on(p, "C2")
    p.pg.click('#tray-levels .seg[data-l="5"]')
    assert p.js("!!document.querySelector('.sheet-wrap')") is False
    p.settled()
    assert p.js("robokit.st.level") == 5
    before = len(p.notes())
    p.answer(("C2", "sell_some"), ("C3", "3"), ("C4", "both"))
    on(p, "result")
    p.settled()
    assert not [n for n in p.notes()[before:] if "answers changed" in n.lower()]


def test_a_savings_gate_sets_a_choice_aside_and_brings_it_back_after_a_reload(page_factory):
    """A level set aside by the savings gate comes back when the gate lifts, also after a reload and Resume."""
    p = page_factory()
    p.pg.click('#tray-levels .seg[data-l="4"]')
    p.settled()
    p.start_check("retirement", 10000)
    p.answer(("A2", "no"))
    p.pg.wait_for_function("robokit.st.level === 2")
    assert any("savings or debt" in n for n in p.notes())
    p.saved()
    p.reload()
    p.pg.click(".card-resume [data-resume]")
    p.pg.click('.card-check[data-q="A3"] [data-back]')
    p.answer(("A2", "yes"))
    p.pg.wait_for_function("robokit.st.level === 4")
    assert any("earlier choice is back" in n for n in p.notes())


def test_money_needed_soon_is_explained_and_labelled_for_reference(page_factory):
    """Money needed within two years is the stated reason for the move, and the level-1 mix is labelled for reference only."""
    p = page_factory()
    p.start_check("home", 10000)
    p.answer(("A2", "yes"), ("A3", "no"), ("B1", "lt2"), ("B2", "once"))
    on(p, "result")
    assert p.js("robokit.st.profile.status") == "not_ready"
    notes = p.notes()
    assert any("within 2 years" in n for n in notes) and not any("savings or debt" in n for n in notes)
    p.pg.click(".card-check [data-later2]")
    p.pg.wait_for_selector(".card-summary")
    p.settled()
    tray, summary = p.js(
        "[document.querySelector('#tray-sub').textContent, document.querySelector('.card-summary .summary-line').textContent]"
    )
    assert "for reference" in tray and "suggestion from your self-check" not in tray
    assert "for reference" in summary and "suggested 1" not in summary


def test_the_clarifying_card_comes_back_until_it_is_answered(page_factory):
    """The clarifying card waits through 'Continue later', stays settled after 'Keep' and a reload, and returns on new disagreement."""
    p = page_factory()
    p.start_check("retirement", 10000)
    p.answer(*CALM[:9], ("C4", "losing"))
    on(p, "flags")
    p.pg.click('.card-check[data-q="flags"] [data-later]')
    assert "paused" in p.js("document.querySelector('.card-summary .summary-line').textContent")
    p.pg.click(".card-summary [data-resume]")
    on(p, "flags")
    p.pg.click(".card-check [data-keep]")
    on(p, "result")
    p.saved()
    p.reload()
    p.pg.click(".card-resume [data-resume]")
    on(p, "result")
    review(p, "C4")
    p.answer(("C4", "both"))
    on(p, "result")
    review(p, "C4")
    p.answer(("C4", "losing"))
    on(p, "flags")


def test_a_check_paused_with_questions_left_keeps_the_level(page_factory):
    """A check paused with questions left (Resume after a reload, then Continue later) keeps the level and offers Continue."""
    p = page_factory()
    p.start_check("retirement", 10000)
    p.answer(*CALM[:6], ("C1", "1"))  # one comfort answer, pointing to level 1; C2 to C4 are still open
    on(p, "C2")
    p.settled()
    assert p.js("robokit.st.level") == 3
    p.saved()
    p.reload()
    p.pg.click(".card-resume [data-resume]")
    on(p, "C2")
    p.settled()
    assert p.js("robokit.st.level") == 3
    p.pg.click(".card-check [data-later]")
    p.pg.wait_for_selector(".card-summary")
    p.settled()
    assert p.js("robokit.st.level") == 3
    assert [n for n in p.notes() if LEVEL_MOVE.search(n)] == []
    assert "paused" in p.js(SUMMARY)
    p.pg.click(".card-summary [data-resume]")
    on(p, "C2")


def test_the_clarifying_card_waits_while_its_change_is_unanswered(page_factory):
    """Leaving a question opened from the clarifying card unanswered keeps the check paused on that card, also after a reload."""
    p = page_factory()
    p.start_check("retirement", 10000)
    p.answer(*CALM[:9], ("C4", "losing"))
    on(p, "flags")
    p.pg.click('.card-check [data-redo="C4"]')
    on(p, "C4")
    p.pg.click(".card-check [data-later]")
    p.pg.wait_for_selector(".card-summary")
    assert "paused" in p.js(SUMMARY)
    p.saved()
    p.reload()
    p.pg.click(".card-resume [data-resume]")
    p.pg.wait_for_selector(".card-summary")
    p.settled()  # the summary is drawn again when the resumed mix is rebuilt
    assert "paused" in p.js(SUMMARY)
    p.pg.click(".card-summary [data-resume]")
    on(p, "flags")


def test_a_savings_limit_lifted_mid_check_gives_the_level_back(page_factory):
    """A chosen level the savings limit moved down comes back as soon as the limit is lifted mid-check, and stays after a pause."""
    p = page_factory()
    p.pg.click('#tray-levels .seg[data-l="4"]')
    p.settled()
    p.start_check("retirement", 10000)
    p.answer(("A2", "no"), *CALM[1:6], ("C1", "4"))
    on(p, "C2")
    p.settled()
    assert p.js("robokit.st.level") == 2
    before = len(p.notes())
    back_to(p, "A2")
    p.answer(("A2", "yes"))
    p.settled()
    assert p.js("robokit.st.level") == 4
    assert any("earlier choice is back" in n for n in p.notes()[before:])
    p.pg.click(".card-check [data-later]")
    p.pg.wait_for_selector(".card-summary")
    p.settled()
    assert p.js("robokit.st.level") == 4


def test_a_not_ready_check_reopens_on_its_result(page_factory):
    """A not-ready check closes to its summary and reopens on its result from Build; a longer horizon then lifts the level-1 limit."""
    p = page_factory()
    not_ready(p)
    assert p.js("[robokit.st.profile.status, robokit.st.level]") == ["not_ready", 1]
    p.pg.click(".card-check [data-later2]")
    p.pg.wait_for_selector(".card-summary")
    assert "cash-like savings" in p.js(SUMMARY)
    p.pg.click('[data-chip="build"]')
    p.pg.wait_for_function("robokit.st.check.open")
    assert p.js("robokit.st.check.step") == "result"
    assert p.js("document.querySelectorAll('#thread .card-check').length") == 1
    p.pg.click('.card-check [data-change="B2"]')
    p.answer(("B2", "10plus"))
    p.settled()
    assert p.js("robokit.st.level") == 3
    assert p.js("robokit.st.check.step") == "B4"  # the check goes on with the questions it skipped


def test_a_lifted_time_limit_is_explained_as_one(page_factory):
    """When a longer horizon lifts the not-ready limit, the note that brings the level back names the horizon, not savings or debt."""
    p = page_factory()
    not_ready(p)
    before = len(p.notes())
    p.pg.click('.card-check [data-change="B2"]')
    p.answer(("B2", "10plus"))
    p.settled()
    back = [n for n in p.notes()[before:] if "level 3" in n]
    assert back and not [n for n in back if "savings or debt" in n], back


def test_the_resume_card_keeps_its_session_until_a_new_answer(page_factory):
    """While the resume card is offered a level tap keeps the saved session; a new run's first answer replaces it and the card goes."""
    p = page_factory()
    p.start_check("retirement", 25000)
    p.answer(("A2", "yes"))
    p.pg.click(".card-check [data-later]")
    p.pg.wait_for_selector(".card-summary")
    p.saved()
    p.reload()
    p.js(WATCH_SAVES)

    def flushed():
        p.pg.wait_for_function("robokit.__saves.ran === robokit.__saves.asked")

    p.pg.click('#tray-levels .seg[data-l="5"]')
    p.settled()
    flushed()
    assert p.pg.is_visible(".card-resume")
    assert p.js(STORED) == {"goal": "retirement", "savings": "yes", "amount": 25000}
    p.start_check("home", 80000)
    p.answer(("A2", "no"))
    p.settled()
    flushed()
    assert p.js("!!document.querySelector('.card-resume')") is False
    assert p.js(STORED) == {"goal": "home", "savings": "no", "amount": 80000}


def test_a_changed_goal_is_rescored_and_said(page_factory):
    """Wrong quiz answers show on the result, and a goal changed then left with 'Continue later' is rescored and said."""
    p = page_factory()
    p.start_check("retirement", 10000)
    p.answer(*BOLD)
    on(p, "result")
    p.settled()
    assert p.js("[robokit.st.profile.suggested_level, robokit.st.level]") == [4, 4]
    p.pg.click(".card-check [data-quiz]")
    p.answer(("D1", "up"), ("D2", "yes"))
    on(p, "result")
    assert "F_knowledge" in p.js("robokit.st.profile.flags.map(f => f.id)")
    assert p.js("!!document.querySelector('.card-check [data-term=bond_prices_rates]')")
    before = len(p.notes())
    review(p, "setup")
    p.pg.click('.card-check [data-goal="wealth"]')
    p.pg.click(".card-check [data-later]")
    p.pg.wait_for_selector(".card-summary")
    p.settled()
    assert any("suggestion went from 4 to 3" in n for n in p.notes()[before:])
    assert p.js("robokit.levelStatus(robokit.st.level)") != "explore"
    assert "suggested 3" in p.js("document.querySelector('.card-summary .summary-line').textContent")


def test_resume_brings_back_the_saved_check_not_a_new_run(page_factory):
    """Resume, tapped while a new self-check is open, shows the saved check, not the new run's question."""
    p = page_factory()
    p.start_check("retirement", 10000)
    p.answer(*CALM)
    on(p, "result")
    p.pg.click(".card-check [data-use]")
    p.pg.wait_for_selector(".card-summary")
    p.saved()
    p.reload()
    p.pg.wait_for_selector(".card-resume")
    p.pg.click('[data-chip="build"]')  # a new run, still on its first screen
    on(p, "setup")
    p.pg.click('.card-check [data-goal="home"]')
    p.pg.click(".card-resume [data-resume]")
    p.pg.wait_for_function("robokit.st.answers.C4 === 'both'")
    p.settled()
    assert p.js("document.querySelectorAll('#thread .card-check').length") == 1
    assert p.js("!!document.querySelector('#thread .card-check.card-summary')")
    assert p.js("robokit.st.answers.A1") == "retirement"


def test_a_reopened_result_draws_its_numbers(page_factory):
    """A result reopened with Resume after a reload fills its level chooser once its numbers are ready."""
    p = page_factory(init=SLOW_LADDER_AFTER_RELOAD)
    p.start_check("retirement", 10000)
    p.answer(("A2", "no"), *BOLD[1:])  # a savings gate with a high comfort with swings
    on(p, "result")
    p.saved()
    p.js("sessionStorage.setItem('slow-ladder', '1')")
    p.reload()
    p.pg.click(".card-resume [data-resume]")
    p.pg.wait_for_selector(".card-check .ladder")
    p.pg.wait_for_function(
        "(() => { const e = robokit.st.ladder[robokit.st.market]; return e && e.done && !robokit.ladderStale(); })()", timeout=30000
    )
    s = p.js("""() => ({ skel: document.querySelectorAll('.card-check .ladder .skel').length,
      updating: !!document.querySelector('.card-check fieldset.chooser [role=status]'),
      busy: document.querySelector('.card-check .ladder').getAttribute('aria-busy') })""")
    assert s == {"skel": 0, "updating": False, "busy": "false"}


def test_dismissed_level_sheets_put_the_chooser_back(page_factory):
    """Dismissing the explore or savings-gate sheet puts the chooser back on the level in use; a gate-set level is called the gate's."""
    p = page_factory()
    p.start_check("retirement", 10000)
    p.answer(*CALM)
    on(p, "result")
    p.pg.click('.card-check .lad-row[data-l="5"]')
    p.pg.click(".card-check [data-use]")
    p.pg.wait_for_selector(".sheet [data-explore]")
    p.pg.keyboard.press("Escape")
    p.pg.wait_for_selector(".sheet-wrap", state="detached")
    c = p.js(CHOOSER)
    assert c["pressed"] == [c["level"]] and "5" not in c["use"]

    review(p, "A2")
    p.answer(("A2", "no"))
    on(p, "result")
    p.settled()
    assert p.js("robokit.st.level") == 2
    assert "lower of the two" not in p.js("document.querySelector('.card-check p.strong').textContent")
    for close in (lambda: p.pg.click(".sheet [data-close]"), lambda: p.pg.keyboard.press("Escape")):
        p.pg.click('.card-check .lad-row[data-l="4"]')
        p.pg.click(".card-check [data-use]")
        p.pg.wait_for_selector(".sheet [data-close]")
        close()
        p.pg.wait_for_selector(".sheet-wrap", state="detached")
        c = p.js(CHOOSER)
        assert 4 not in c["pressed"] and "4" not in c["use"]


def test_the_assistant_opening_the_check_leaves_the_person_typing(page_factory):
    """When the AI opens the self-check already on screen, the field being typed in keeps its focus and every keystroke."""
    p = page_factory("mock.html")
    p.send("I want to build a portfolio for retirement")
    p.pending()
    on(p, "setup")
    p.pg.fill(".card-check [data-amount]", "")
    p.pg.click(".card-check [data-amount]")
    p.pg.keyboard.type("25")
    p.call("start_self_check")
    p.pg.keyboard.type("000")
    p.reply("The self-check is open below. Tap your answers.")
    assert p.pg.input_value(".card-check [data-amount]") == "25000"


def test_change_in_a_sheet_from_the_phone_tray_shows_the_question(page_factory):
    """On a phone, 'Change' in a sheet opened from the tray closes the tray and puts the question, with focus, on screen."""
    p = page_factory(viewport={"width": 375, "height": 812})
    p.start_check("retirement", 10000)
    p.answer(("A2", "no"), *CALM[1:])
    on(p, "result")
    p.pg.click("#tray-toggle")
    p.pg.wait_for_function("document.body.classList.contains('tray-open')")
    p.pg.click('#tray-levels .seg[data-l="4"]')
    p.pg.click('.sheet [data-change="A2"]')
    p.pg.wait_for_function("robokit.st.check.open && robokit.st.check.step === 'A2'")
    s = p.js("""() => { const q = document.querySelector('.card-check[data-q="A2"]');
      return { trayOpen: document.body.classList.contains('tray-open'), inert: !!q.closest('[inert]') }; }""")
    assert s == {"trayOpen": False, "inert": False}
    assert p.focus() != "BODY"
