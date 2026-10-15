"""Browser tests for the guided page (web/index.html): the conversation script, the team's review items and the edge
cases the requirements plan names (conflicting answers, zero-match filters, "just tell me what to buy").

Each test drives a fresh page in headless Chromium. Without Claude the page answers from its own notes; one test plays
Claude with a stand-in for the artifact's `sample` capability.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.ui

ADVICE = "I can't tell you whether to buy at any specific time"

# A stand-in for the claude.ai runtime: `sample` answers in a fixed sentence, other capabilities are absent.
FAKE_CLAUDE = """
window.__asked = [];
const sample = async (input, opts) => { window.__asked.push(input); return { text: 'Your answers so far point to a careful mix, and you can change any of them.', truncated: false, modelTierApplied: 'default' }; };
sample.limits = async () => ({ maxPromptBytes: 65536 });
window.claude = { use: async (name) => (name === 'sample' ? sample : null) };
"""


class Guide:
    def __init__(self, browser, base_url, init=None, **ctx):
        self.ctx = browser.new_context(**({"viewport": {"width": 1280, "height": 900}} | ctx))
        if init:
            self.ctx.add_init_script(init)
        self.pg = self.ctx.new_page()
        self.errors: list[str] = []
        self.pg.on("pageerror", lambda e: self.errors.append(str(e)))
        self.pg.goto(base_url + "index.html")
        self.pg.wait_for_function("window.robokitGuide && document.querySelectorAll('#prompts button').length === 3", timeout=30000)

    def js(self, expr):
        return self.pg.evaluate(expr)

    def say(self, text):
        n = self.js("document.querySelectorAll('#thread .msg').length")
        self.pg.fill("#chat-in", text)
        self.pg.press("#chat-in", "Enter")
        self.pg.wait_for_function(f"document.querySelectorAll('#thread .msg').length > {n} && !window.robokitGuide.st.busy", timeout=15000)

    def tap(self, q, v):
        sel = f'[data-q="{q}"][data-v="{v}"]'
        self.pg.wait_for_selector(f"{sel}:not([disabled])", timeout=30000)
        self.pg.locator(sel).last.click()

    def last(self, n=1):
        return self.js(f"[...document.querySelectorAll('#thread .msg')].slice(-{n}).map(m => m.innerText.replace(/\\s+/g, ' ').trim())")

    def pending_step(self):
        return self.js("[...document.querySelectorAll('#thread .step-card')].at(-1)?.dataset.step")

    def through_core(self, *, comfort="medium", drop="wait"):
        self.pg.click('[data-prompt="1"]')
        self.tap("EXP", "novice")
        self.tap("B1", "20plus")
        self.tap("B2", "10plus")
        self.tap("A2", "yes")
        self.tap("A3", "no")
        self.pg.locator("[data-money='25000']").last.click()
        self.tap("B5", "mostly")
        self.tap("C0", comfort)
        self.tap("C2", drop)

    def to_assessment(self, **kw):
        self.through_core(**kw)
        if self.pending_step() == "RECON":
            self.tap("RECON", "C2")
        self.tap("C1", "3")
        self.tap("FT", "no")
        self.pg.wait_for_selector("#assess .means", timeout=30000)

    def to_mix(self, **kw):
        self.to_assessment(**kw)
        self.pg.check("#ack")
        self.pg.click('[data-act="assess-ok"]')
        self.pg.locator('[data-skip="PREFS"]').last.click()
        self.pg.locator('[data-skip="TICKER"]').last.click()
        self.pg.locator('[data-act="calculate"]').last.click()
        self.pg.wait_for_selector(".fund", timeout=30000)

    def close(self):
        assert not self.errors, self.errors
        self.ctx.close()


@pytest.fixture
def guide(browser, base_url):
    made = []

    def make(**kw):
        g = Guide(browser, base_url, **kw)
        made.append(g)
        return g

    yield make
    for g in made:
        g.close()


def test_a_beginner_reaches_a_portfolio_with_reasons_recap_and_disclosures(guide):
    g = guide()
    g.to_mix()
    text = g.js("document.querySelector('[data-screen=mix]').innerText")
    weights = g.js("[...document.querySelectorAll('.fund .w')].map(w => parseFloat(w.textContent))")
    assert 98 <= sum(weights) <= 102, weights
    assert "Before you go" in text and "Here is what we covered" in text
    assert "Past performance is not reflective of future performance." in text
    assert "educational tool, not a registered advisor" in text
    assert g.js("document.querySelectorAll('.fund .why1').length") == len(weights)  # one line of reasons per fund


def test_the_assessment_explains_the_level_and_tags_no_one(guide):
    g = guide()
    g.to_assessment()
    modal = g.js("document.querySelector('#assess').innerText")
    assert "Suggested risk level" in modal.upper().title() or "SUGGESTED RISK LEVEL" in modal.upper()
    assert "What level" in modal and "stock market's ups and downs" in modal
    assert "NOVICE" not in modal.upper() and "INVESTOR" not in modal.upper()
    assert g.js("document.querySelector('[data-act=\"assess-ok\"]').disabled")  # the disclaimer must be ticked first
    assert g.js("document.querySelectorAll('#assess [data-act=\"change-answers\"]').length") >= 1


def test_typed_answers_are_understood(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.say("I'm new to this")
    g.say("I'm 35 and want to retire at 65")
    assert g.js("window.robokitGuide.st.answers.B1") == "20plus"
    g.say("over more than 10 years")
    g.say("yes")
    g.say("no debt")
    g.say("$20k and 300 a month")
    g.say("I freelance so it varies")
    st = g.js(
        "({a: window.robokitGuide.st.answers, amt: window.robokitGuide.st.amount, mo: window.robokitGuide.st.monthly, depth: window.robokitGuide.st.depth})"
    )
    assert st["depth"] == "novice"
    assert st["a"]["B2"] == "10plus" and st["a"]["A2"] == "yes" and st["a"]["A3"] == "no" and st["a"]["B5"] == "varies"
    assert st["amt"] == 20000 and st["mo"] == 300


def test_a_question_mid_flow_is_answered_then_offers_the_way_back(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "some")
    g.say("what is volatility?")
    assert g.last(2)[0].startswith("Volatility:")
    assert "Back to building your portfolio?" in g.last()[0]
    g.pg.locator('[data-act="resume"]').last.click()
    assert g.pending_step() == "B1"


def test_advice_requests_are_redirected_every_time(guide):
    g = guide()
    g.pg.click('[data-prompt="0"]')
    g.say("Should I buy VFV?")
    assert any(ADVICE in m for m in g.last(4))
    g.say("just tell me what to buy")
    assert any(ADVICE in m for m in g.last(4))
    g.say("What should I actually do?")  # the review's own wording
    assert any(ADVICE in m for m in g.last(4))


def test_conflicting_risk_answers_get_a_second_chance(guide):
    g = guide()
    g.through_core(comfort="low", drop="buy")
    assert g.pending_step() == "RECON"
    assert "Which feels more accurate" in g.last()[0]
    g.tap("RECON", "C2")
    assert g.js("window.robokitGuide.st.setAside") == "C0"


def test_tickers_are_added_and_ineligible_ones_explained(guide):
    g = guide()
    g.to_assessment()
    g.pg.check("#ack")
    g.pg.click('[data-act="assess-ok"]')
    g.pg.locator('[data-skip="PREFS"]').last.click()
    g.say("XEQT")
    assert "XEQT" in g.js("window.robokitGuide.st.picks.join(',')")
    g.say("add AAPU")
    msgs = " ".join(g.last(3))
    assert "can't be added" in msgs and "leverage" in msgs


def test_a_zero_match_asks_before_loosening_a_filter(guide):
    g = guide()
    g.to_assessment()
    g.pg.check("#ack")
    g.pg.click('[data-act="assess-ok"]')
    for sel in ('[data-pref="focus"][data-key="energy"]', '[data-pref="flag"][data-key="lowCost"]', '[data-pref="flag"][data-key="large"]'):
        g.pg.locator(sel).last.click()
    g.pg.locator('[data-act="prefs-apply"]').last.click()
    g.pg.wait_for_selector("[data-zero]", timeout=10000)
    assert "Nothing in our dataset matches" in " ".join(g.last(3))
    g.pg.locator("[data-zero]").last.click()
    assert any(t.endswith(".TO") or t.endswith(".NE") for t in g.js("window.robokitGuide.st.picks"))


def test_choosing_a_higher_level_needs_a_look_and_a_disclosure(guide):
    g = guide()
    g.to_mix()
    suggested = g.js("window.robokitGuide.st.profile.suggested_level")
    higher = min(5, suggested + 2)
    g.pg.click(f'.levels [data-level="{higher}"]')
    assert g.js("document.querySelector('[data-level-ok]').disabled")
    g.pg.check("#lv-ack")
    g.pg.click("[data-level-ok]")
    g.pg.wait_for_function(f"window.robokitGuide.st.base && window.robokitGuide.st.level === {higher}", timeout=30000)
    assert "was not calculated for you based on your responses" in g.js("document.querySelector('[data-screen=mix]').innerText")


def test_adjusting_the_mix_warns_before_saving_a_higher_risk(guide):
    g = guide()
    g.to_mix(comfort="low", drop="sell_some")
    g.pg.click('[data-act="adjust"]')
    for _ in range(6):
        g.pg.click('[data-c="Equity"] [data-cl="+"]')
    g.pg.wait_for_selector(".warnbox", timeout=15000)
    assert g.js("document.querySelector('[data-act=\"adj-save\"]').disabled")
    g.pg.check("#adj-ack")
    g.pg.wait_for_function("!document.querySelector('[data-act=\"adj-save\"]').disabled", timeout=15000)
    text = g.js("document.querySelector('[data-screen=adjust]').innerText")
    assert "Expected return a year" in text and "would not be calculated for you" in text


def test_learn_more_answers_questions_about_a_fund_without_ai(guide):
    g = guide()
    g.to_mix()
    g.pg.locator("[data-lm]").first.click()
    g.pg.wait_for_selector("#lm .holds")
    g.pg.fill("#lm-in", "What does it hold?")
    g.pg.press("#lm-in", "Enter")
    g.pg.wait_for_function("document.querySelectorAll('#lm-qa-list .msg.bot').length > 0", timeout=10000)
    answer = g.js("document.querySelector('#lm-qa-list .msg.bot:last-child').innerText")
    assert "holds" in answer and "In this preview" not in answer


def test_changing_an_earlier_answer_rebuilds_the_portfolio(guide):
    g = guide()
    g.to_mix()
    before = g.js("window.robokitGuide.st.level")
    g.pg.click("details.more summary >> nth=0")
    g.pg.click('[data-change="C2"]')
    g.tap("C2", "sell_all")  # with a 'medium' self-rating this asks the second-chance question, then the assessment again
    g.tap("RECON", "C2")
    g.pg.wait_for_selector("#assess .means", timeout=30000)
    g.pg.check("#ack")
    g.pg.click('[data-act="assess-ok"]')
    g.pg.locator('[data-act="rebuild"]').last.click()
    g.pg.wait_for_selector(".fund", timeout=30000)
    after = g.js(
        "({level: window.robokitGuide.st.level, c2: window.robokitGuide.st.answers.C2, log: window.robokitGuide.st.events.join(' | ')})"
    )
    assert after["c2"] == "sell_all" and after["level"] < before, after
    assert "Reaction to a drop: Sell everything" in after["log"]


def test_the_summary_is_reconfirmed_before_export(guide):
    g = guide()
    g.to_mix()
    g.pg.click('[data-act="export"]')
    assert g.js("document.querySelector('[data-act=\"copy\"]').disabled")
    g.pg.check("#ex-ack")
    assert not g.js("document.querySelector('[data-act=\"copy\"]').disabled")
    assert not g.js("document.querySelector('[data-act=\"download\"]').disabled")  # offered with or without claude.ai
    html = g.js("window.robokitGuide.summary()")
    funds = g.js("document.querySelectorAll('.fund').length")
    assert html.count('<details id="f-') == funds  # each fund opens to its reasons and holdings
    for part in (
        "Market context",
        "Your answers",
        "How it was built",
        "Past performance is not reflective of future performance.",
        "any investment decision I make is my own",
    ):
        assert part in html, part


def test_claude_can_be_connected_and_answers_then_offers_the_way_back(guide):
    g = guide(init=FAKE_CLAUDE)
    g.pg.wait_for_selector('#home-connect [data-act="connect"]', timeout=10000)
    g.pg.click('[data-prompt="1"]')
    g.pg.locator('[data-act="connect"]').last.click()
    g.pg.wait_for_function("window.robokitGuide.ai === 'on'", timeout=10000)
    g.tap("EXP", "some")
    g.say("Can you sum up my situation so far?")
    msgs = g.last(2)
    assert "careful mix" in msgs[0] and "Back to building your portfolio?" in msgs[1]
    g.say("Should I buy VFV?")
    assert any(ADVICE in m for m in g.last(4))  # the redirect never goes to Claude


def test_phone_width_has_no_sideways_scroll(guide):
    g = guide(viewport={"width": 375, "height": 812})
    g.to_mix()
    assert g.js("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_optional_steps_accept_typed_replies(guide):
    g = guide()
    g.through_core()
    g.tap("C1", "3")
    g.say("no")  # the fine-tune offer
    g.pg.wait_for_selector("#assess .means", timeout=30000)
    g.pg.check("#ack")
    g.pg.click('[data-act="assess-ok"]')
    g.say("skip")  # preferences
    g.say("no")  # tickers
    assert g.pending_step() == "SHORTLIST"
    g.pg.fill("#chat-in", "looks good, calculate")  # this one leaves the chat for the mix, so no new message to wait for
    g.pg.press("#chat-in", "Enter")
    g.pg.wait_for_selector(".fund", timeout=30000)
    assert g.js("window.robokitGuide.st.prefsDone && window.robokitGuide.st.tickerDone")


def test_the_emergency_fund_check_caps_the_level(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "some")
    g.tap("B1", "20plus")
    g.tap("B2", "10plus")
    g.tap("A2", "no")
    g.tap("A3", "no")
    g.pg.locator("[data-money='25000']").last.click()
    g.tap("B5", "very")
    g.tap("C0", "high")
    g.tap("C2", "buy")
    g.tap("C1", "5")
    g.tap("FT", "no")
    g.pg.wait_for_selector("#assess .means", timeout=30000)
    assert "emergency fund" in g.js("document.querySelector('#assess').innerText")
    g.pg.check("#ack")
    g.pg.click('[data-act="assess-ok"]')
    g.pg.locator('[data-skip="PREFS"]').last.click()
    g.pg.locator('[data-skip="TICKER"]').last.click()
    g.pg.locator('[data-act="calculate"]').last.click()
    g.pg.wait_for_selector(".fund", timeout=30000)
    assert g.js("window.robokitGuide.st.level") <= 2
    assert g.js("[3, 4, 5].every(L => document.querySelector(`.levels [data-level='${L}']`).disabled)")


def test_required_steps_ask_again_and_requests_get_answers(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.say("skip")
    assert "I do need this one" in " ".join(g.last(3))
    g.tap("EXP", "some")
    g.say("I want to know about fees")
    msgs = " ".join(g.last(3))
    assert "MER" in msgs and "Back to building your portfolio?" in msgs


def test_preferences_can_be_changed_after_the_mix(guide):
    g = guide()
    g.to_mix()
    g.pg.fill("#chat-in", "avoid emerging markets")
    g.pg.press("#chat-in", "Enter")
    g.pg.wait_for_selector('[data-act="rebuild"]', timeout=15000)
    g.pg.locator('[data-act="rebuild"]').last.click()
    g.pg.wait_for_selector(".fund", timeout=30000)
    assert "VEE" not in g.js("[...document.querySelectorAll('.fund b')].map(b => b.textContent).join(' ')")
    assert "VEE.TO" in g.js("[...window.robokitGuide.st.exclude].join(',')")


def test_a_hand_set_mix_does_not_claim_the_optimizer_cap(guide):
    g = guide()
    g.to_mix()
    g.pg.click('[data-act="adjust"]')
    first = g.js("document.querySelector('.adj-row[data-t]').dataset.t")
    for _ in range(40):
        g.pg.click(f'.adj-row[data-t="{first}"] [data-f="+"]')
    g.pg.wait_for_timeout(1200)
    if g.js("!!document.querySelector('#adj-ack')"):
        g.pg.check("#adj-ack")
    g.pg.wait_for_function("!document.querySelector('[data-act=adj-save]').disabled", timeout=15000)
    g.pg.click('[data-act="adj-save"]')
    g.pg.wait_for_selector(".fund", timeout=30000)
    text = g.js("document.querySelector('[data-screen=mix]').innerText")
    assert "no fund is above 50%" not in text and "set these weights by hand" in text


# ------------------------------------------------------------------ found by driving the page (third review lane)


def test_amounts_with_commas_and_both_basics_in_one_line(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "novice")
    g.tap("B1", "20plus")
    g.tap("B2", "10plus")
    g.say("yes, no debt")
    a = g.js("window.robokitGuide.st.answers")
    assert a.get("A2") == "yes" and a.get("A3") == "no", a
    g.say("$15,000 to start and $200 a month")
    got = g.js("({amount: window.robokitGuide.st.amount, monthly: window.robokitGuide.st.monthly})")
    assert got == {"amount": 15000, "monthly": 200}, got


def test_bare_tickers_are_added_at_any_step_and_no_builds_from_the_shortlist(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "expert")
    g.say("XEQT, VFV")
    assert g.js("window.robokitGuide.st.picks") == ["XEQT.TO"]
    assert "VFV is already on your shortlist" in " ".join(g.last(4))  # a default fund
    assert g.pending_step() == "B1"  # the question is asked again, nothing answered by accident
    g.say("show me my mix")  # everyday words that are also tickers are words
    assert g.js("window.robokitGuide.st.picks") == ["XEQT.TO"]


def test_the_shortlist_accepts_no_and_an_unchanged_shortlist_asks_no_rebuild(guide):
    g = guide()
    g.to_assessment()
    g.pg.check("#ack")
    g.pg.click('[data-act="assess-ok"]')
    g.pg.locator('[data-skip="PREFS"]').last.click()
    g.pg.locator('[data-skip="TICKER"]').last.click()
    g.pg.fill("#chat-in", "no, that's fine")
    g.pg.press("#chat-in", "Enter")
    g.pg.wait_for_selector(".fund", timeout=30000)
    held = g.js("window.robokitGuide.st.base.holdings[0].symbol")
    rebuilds = g.js("document.querySelectorAll('[data-act=\"rebuild\"]').length")
    g.pg.fill("#chat-in", f"add {held}")
    g.pg.press("#chat-in", "Enter")
    g.pg.wait_for_timeout(500)
    assert g.js("document.querySelectorAll('[data-act=\"rebuild\"]').length") == rebuilds
    assert not g.js("window.robokitGuide.st.changed")


def test_a_chosen_level_survives_a_changed_answer_and_the_summary_says_so(guide):
    g = guide()
    g.to_mix()
    s = g.js("window.robokitGuide.st.profile.suggested_level")
    higher = min(5, s + 1)
    g.pg.click(f'.levels [data-level="{higher}"]')
    g.pg.check("#lv-ack")
    g.pg.click("[data-level-ok]")
    g.pg.wait_for_function(f"window.robokitGuide.st.base && window.robokitGuide.st.level === {higher}", timeout=30000)
    g.pg.click("details.more summary >> nth=0")
    g.pg.click('[data-change="B5"]')
    g.tap("B5", "very")
    g.pg.wait_for_selector("#assess .means", timeout=30000)
    g.pg.check("#ack")
    g.pg.click('[data-act="assess-ok"]')
    assert "the level you chose" in " ".join(g.last(3))
    g.pg.locator('[data-act="rebuild"]').last.click()
    g.pg.wait_for_selector(".fund", timeout=30000)
    assert g.js("window.robokitGuide.st.level") == higher
    summary = g.js("window.robokitGuide.summary()")
    assert "was not calculated for you based on your responses" in summary


def test_closing_the_assessment_to_change_an_answer_offers_the_way_back(guide):
    g = guide()
    g.to_assessment()
    g.pg.click('[data-act="change-answers"]')
    assert "Back to building your portfolio?" in " ".join(g.last(2))


def test_adjust_opens_on_the_measured_level_of_the_built_mix(guide):
    g = guide()
    g.to_mix()
    g.pg.click('[data-act="adjust"]')
    g.pg.wait_for_function("window.robokitGuide.st.draftP !== null", timeout=15000)
    assert not g.js("!!document.querySelector('.warnbox')")  # the untouched mix never warns about its own level
    assert "Within the level your answers suggest" in g.js("document.querySelector('[data-screen=adjust]').innerText")


def test_tabs_fit_a_phone(guide):
    g = guide(viewport={"width": 360, "height": 780})
    g.to_mix()
    g.pg.locator("[data-lm]").first.click()
    g.pg.wait_for_selector("#lm .holds")
    assert g.js("document.documentElement.scrollWidth <= window.innerWidth + 1")


def test_the_question_shows_at_once_while_claude_thinks(guide):
    slow = FAKE_CLAUDE.replace("window.__asked.push(input);", "window.__asked.push(input); await new Promise((r) => setTimeout(r, 1500));")
    g = guide(init=slow)
    g.pg.wait_for_selector('#home-connect [data-act="connect"]', timeout=10000)
    g.pg.click('[data-prompt="1"]')
    g.pg.locator('[data-act="connect"]').last.click()
    g.pg.wait_for_function("window.robokitGuide.ai === 'on'", timeout=10000)
    g.tap("EXP", "some")
    g.pg.fill("#chat-in", "Can you sum up my situation so far?")
    g.pg.press("#chat-in", "Enter")
    g.pg.wait_for_function("window.robokitGuide.st.busy", timeout=5000)
    assert "Can you sum up my situation so far?" in g.js("document.querySelector('#thread').innerText")
    g.pg.fill("#chat-in", "typed while waiting")
    g.pg.press("#chat-in", "Enter")
    assert g.js("document.querySelector('#chat-in').value") == "typed while waiting"  # not thrown away
    g.pg.wait_for_function("!window.robokitGuide.st.busy", timeout=15000)


def test_learn_more_defines_a_term_asked_about(guide):
    g = guide()
    g.to_mix()
    g.pg.locator("[data-lm]").first.click()
    g.pg.wait_for_selector("#lm .holds")
    g.pg.fill("#lm-in", "what is volatility?")
    g.pg.press("#lm-in", "Enter")
    g.pg.wait_for_function("document.querySelectorAll('#lm-qa-list .msg.bot').length > 0", timeout=10000)
    assert g.js("document.querySelector('#lm-qa-list .msg.bot:last-child').innerText").startswith("Volatility")
