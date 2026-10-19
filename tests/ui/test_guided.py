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
const sample = async (input, opts) => { window.__asked.push(input); return { text: 'Here is a short explanation from the numbers on this page, and you can change any answer.', truncated: false, modelTierApplied: 'default' }; };
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

    def through_core(self, *, comfort="medium", drop="wait", depth="novice"):
        self.pg.click('[data-prompt="1"]')
        self.tap("EXP", depth)
        self.tap("B1", "20plus")
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
    g.pg.wait_for_selector(".changed .cmp", timeout=30000)  # rebuilt at once (O3), with before and after side by side (X3)
    assert "Volatility a year" in g.js("document.querySelector('.changed').innerText")
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
    assert "short explanation" in msgs[0] and "Back to building your portfolio?" in msgs[1]
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
    g.say("no")  # tickers: then the mix is built, with no shortlist preview (v3.3)
    g.pg.wait_for_selector(".fund", timeout=30000)
    assert g.js("window.robokitGuide.st.prefsDone && window.robokitGuide.st.tickerDone")


def test_the_emergency_fund_check_caps_the_level(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "some")
    g.tap("B1", "20plus")
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
    g.pg.wait_for_selector(".fund", timeout=30000)
    assert g.js("window.robokitGuide.st.level") <= 2
    assert g.js("[3, 4, 5].every(L => document.querySelector(`.levels [data-level='${L}']`).disabled)")


def test_required_steps_ask_again_and_requests_get_answers(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "some")  # the experience question itself may be skipped (F1); the horizon may not
    g.say("skip")
    assert "I do need this one" in " ".join(g.last(3))
    g.say("I want to know about fees")
    msgs = " ".join(g.last(3))
    assert "MER" in msgs and "Back to building your portfolio?" in msgs


def test_preferences_can_be_changed_after_the_mix(guide):
    g = guide()
    g.to_mix()
    g.pg.fill("#chat-in", "avoid emerging markets")
    g.pg.press("#chat-in", "Enter")
    g.pg.wait_for_selector(".changed .cmp", timeout=30000)  # the optimizer re-runs at once (O3)
    assert "VEE" not in g.js("[...document.querySelectorAll('.fund b')].map(b => b.textContent).join(' ')")
    assert "VEE.TO" in g.js("[...window.robokitGuide.st.exclude].join(',')")


def test_a_hand_set_mix_does_not_claim_the_optimizer_cap(guide):
    g = guide()
    g.to_mix()
    g.pg.click('[data-act="adjust"]')
    first = g.js("document.querySelector('.adj-row[data-t]').dataset.t")
    for _ in range(60):
        if g.js(f'document.querySelector(\'.adj-row[data-t="{first}"] [data-f="+"]\').disabled'):
            break  # the 50% cap (X4)
        g.pg.click(f'.adj-row[data-t="{first}"] [data-f="+"]')
    g.pg.wait_for_timeout(1200)
    assert g.js("Math.max(...Object.values(window.robokitGuide.st.draft))") <= 0.5 + 1e-9
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


def test_an_unchanged_shortlist_asks_no_rebuild(guide):
    g = guide()
    g.to_mix()
    held = g.js("window.robokitGuide.st.base.holdings[0].symbol")
    events = g.js("window.robokitGuide.st.events.length")
    g.pg.fill("#chat-in", f"add {held}")
    g.pg.press("#chat-in", "Enter")
    g.pg.wait_for_timeout(500)
    assert not g.js("window.robokitGuide.st.changed")
    assert not any("Rebuilt" in e for e in g.js("window.robokitGuide.st.events")[events:])


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
    g.pg.wait_for_selector(".changed .cmp", timeout=30000)
    assert any("the level you chose" in m.get("text", "") for m in g.js("window.robokitGuide.st.log") if m.get("who") == "bot")
    assert f"you chose level {higher}" in g.js("document.querySelector('[data-screen=mix]').innerText")
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


# ------------------------------------------------------------------ v3.2: open conversation and explanation depth
LABEL_WORDS = r"\b(?:novice|beginners?|experts?|experienced investor|intermediate|newbie)\b"


def bot_texts(g):
    return g.js("window.robokitGuide.st.log.filter(m => m.who === 'bot' && m.text).map(m => m.text).join(' | ')")


def type_home(g, text):
    g.pg.fill("#ask", text)
    g.pg.press("#ask", "Enter")
    g.pg.wait_for_function(
        "window.robokitGuide.st.screen === 'chat' && document.querySelectorAll('#thread .step-card').length > 0", timeout=15000
    )


def test_a_story_opener_only_asks_whats_missing(guide):
    g = guide()
    type_home(g, "I'm 30, saving for a condo in about 5 years, I have $15k and no debt")
    a = g.js("window.robokitGuide.st.answers")
    assert a.get("A1") == "home" and a.get("B1") == "5to9" and a.get("A3") == "no" and g.js("window.robokitGuide.st.amount") == 15000
    text = " ".join(g.last(4))
    assert "Here's what I have so far" in text and "the condo" in text
    assert g.js("document.querySelectorAll('.noted-chip').length") >= 4
    g.tap("EXP", "some")
    assert g.pending_step() == "BASICS"  # goal, horizon, amount and debt are not asked again; how it comes out follows the goal
    assert g.js("window.robokitGuide.st.answers.B2") == "once" and g.js("window.robokitGuide.st.auto.has('B2')")


def test_answers_given_out_of_order_are_kept(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')  # retirement
    g.say("no debt")
    g.say("all at once")
    a = g.js("window.robokitGuide.st.answers")
    assert a.get("A3") == "no" and a.get("A2") is None and a.get("B2") == "once", a  # said, so it replaces the goal's assumption
    assert not g.js("window.robokitGuide.st.auto.has('B2')")
    assert g.js("window.robokitGuide.st.depthSrc") == "skipped"


def test_depth_changes_words_not_options(guide):
    novice, expert = guide(), guide()
    for g, d in ((novice, "novice"), (expert, "expert")):
        g.pg.click('[data-prompt="1"]')
        g.tap("EXP", d)
    values = "[...document.querySelectorAll('.step-card')].at(-1).querySelectorAll('[data-q=B1]').length && [...[...document.querySelectorAll('.step-card')].at(-1).querySelectorAll('[data-q=B1]')].map(b => b.dataset.v)"
    assert novice.js(values) == expert.js(values)
    assert novice.js("[...[...document.querySelectorAll('.step-card')].at(-1).querySelectorAll('.opt')].every(o => o.querySelector('.ex'))")
    assert novice.js("!![...document.querySelectorAll('.step-card')].at(-1).querySelector('.hint')")
    card = expert.js("[...document.querySelectorAll('.step-card')].at(-1).innerText")
    assert "20+ years" in card and "How this is scored" in card
    assert "tickers" in expert.js("document.querySelector('#chat-in').placeholder")


def test_same_answers_same_math_at_every_depth(guide):
    out = []
    for d in ("novice", "some", "expert"):
        g = guide()
        g.to_mix(depth=d)
        out.append(
            (
                g.js("window.robokitGuide.st.profile.suggested_level"),
                g.js("window.robokitGuide.st.base.holdings.map(h => [h.ticker, h.weight.toFixed(4)])"),
            )
        )
    assert out[0] == out[1] == out[2]


def test_a_vague_answer_gets_a_two_choice_follow_up(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "some")
    g.say("long term")
    assert g.js("[...document.querySelectorAll('.k-clarify [data-q=B1]')].map(b => b.dataset.v)") == ["10to19", "20plus"]
    assert g.js("window.robokitGuide.st.answers.B1") is None


def test_experience_is_inferred_when_skipped_and_never_shown(guide):
    import re

    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.pg.locator('[data-act="skip-exp"]').last.click()
    g.say("20+ years, my target is a 60/40 split with low tracking error")
    g.tap("A2", "yes")
    g.tap("A3", "no")
    g.pg.locator("[data-money='25000']").last.click()
    st = g.js("({d: window.robokitGuide.st.depth, s: window.robokitGuide.st.depthSrc})")
    assert st == {"d": "expert", "s": "inferred"}, st
    assert not re.search(LABEL_WORDS, bot_texts(g), re.I)
    assert not re.search(LABEL_WORDS, " ".join(g.js("window.robokitGuide.st.events")), re.I)


def test_just_learning_is_acknowledged(guide):
    g = guide()
    type_home(g, "hi")
    g.say("I'm just learning")
    assert g.js("window.robokitGuide.st.depth") == "novice"
    assert "Great place to start" in " ".join(g.last(3))
    assert g.js("!![...document.querySelectorAll('.step-card')].at(-1).querySelector('[data-q=A1][data-v=learning].is-pre')")
    g.tap("A1", "learning")
    assert "If this were real money" in g.js("[...document.querySelectorAll('.step-card')].at(-1).innerText")


def test_a_side_question_answers_then_asks_to_go_back(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "some")
    g.say("what is volatility?")
    msgs = g.last(2)
    assert (
        msgs[0].startswith("Volatility:")
        and "Back to building your portfolio?" in msgs[1]
        and "Next: When would you start using the money?" in msgs[1]
    )
    assert g.pending_step() == "B1"


def test_an_unread_reply_is_rephrased_then_explained(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "some")
    g.tap("B1", "20plus")
    g.say("hmm")
    assert "Sorry, I didn't quite follow that." in " ".join(g.last(2))
    g.say("hmm")
    two = " ".join(g.last(2))
    # v3.3: no withdrawal question, so the basics come next
    assert "An emergency fund is money you can reach quickly" in two and "Even a rough guess is fine" in two
    assert "I didn't catch that" not in bot_texts(g)


def test_one_line_answers_fill_several_steps(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "expert")
    g.say("25 years, $50k, high risk, salaried")
    a = g.js("window.robokitGuide.st.answers")
    assert a.get("B1") == "20plus" and a.get("C0") == "high" and a.get("B5") == "very" and g.js("window.robokitGuide.st.amount") == 50000
    assert g.pending_step() not in ("B1", "MONEY", "C0", "B5")


def test_advice_inside_the_flow_never_reaches_any_model(guide):
    g = guide(init=FAKE_CLAUDE)
    g.pg.wait_for_selector('#home-connect [data-act="connect"]', timeout=10000)
    g.pg.click('[data-prompt="1"]')
    g.pg.locator('[data-act="connect"]').last.click()
    g.pg.wait_for_function("window.robokitGuide.ai === 'on'", timeout=10000)
    asked = g.js("window.__asked.length")
    g.tap("EXP", "some")
    for t in ("should I go to level 5?", "should I cut XSP to 25%?", "so which ETF should I buy?"):
        g.say(t)
        assert any(ADVICE in m for m in g.last(4)), t
    assert g.js("window.__asked.length") == asked


def test_noted_chips_can_be_changed(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "some")
    g.say("25 years and $40k")
    g.pg.locator(".noted-chip").first.click()
    assert g.pending_step() == "B1"


def test_no_question_paragraph_repeats_back_to_back(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "some")
    for t in ("hmm", "what is a bond?", "long term", "20 years"):
        g.say(t)
    cards = g.js("[...document.querySelectorAll('#thread > .msg')].map(m => m.classList.contains('step-card') ? m.innerText : '|')")
    assert all(not (a != "|" and a == b) for a, b in zip(cards, cards[1:]))


def test_a_drop_answer_given_early_is_confirmed_with_numbers(guide):
    g = guide()
    type_home(g, "I'm saving for retirement in 25 years and I'd hold through a crash")
    g.tap("EXP", "novice")
    g.tap("A2", "yes")
    g.tap("A3", "no")
    g.pg.locator("[data-money='25000']").last.click()
    g.tap("B5", "mostly")
    g.tap("C0", "medium")
    assert g.js("window.robokitGuide.st.answers.C2") is None
    card = g.js("[...document.querySelectorAll('.step-card')].at(-1).innerText")
    assert "$25,000" in card and "$20,000" in card and "would you still wait it out" in card
    assert g.js("!![...document.querySelectorAll('.step-card')].at(-1).querySelector('[data-q=C2][data-v=wait].is-pre')")
    g.tap("C2", "wait")
    assert g.js("window.robokitGuide.st.answers.C2") == "wait"


def test_the_checkpoint_summarizes_without_a_level(guide):
    import re

    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "novice")
    g.tap("B1", "20plus")
    g.tap("A2", "yes")
    g.tap("A3", "no")
    g.pg.locator("[data-money='25000']").last.click()
    g.tap("B5", "mostly")
    text = g.js("document.querySelector('.k-checkpoint').innerText")
    assert text.startswith("Let me check I have this right") and not re.search(r"level \d", text)
    assert g.pending_step() == "C0"


def test_the_shortcuts_fill_the_box(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "expert")
    g.pg.locator(".shortcuts [data-fill]").first.click()
    assert g.js("document.querySelector('#chat-in').value").startswith("25 years")
    assert g.pending_step() == "B1"  # nothing was sent


def test_experienced_results_show_more(guide):
    g = guide()
    g.to_mix(depth="expert")
    assert g.js("!!document.querySelector('details.hood[open]')")
    assert g.js("document.querySelector('details.hood ul').querySelectorAll('li').length") == g.js(
        "document.querySelectorAll('.fund').length"
    )
    text = g.js("document.querySelector('[data-screen=mix]').innerText")
    assert "The full reasons are in the summary" not in text
    assert all(t in text for t in ("Chance of a loss in year one", "Risk-rating scale", "Sharpe on equilibrium returns", "of the risk"))


def test_beginner_results_are_plain(guide):
    g = guide()
    g.to_mix(depth="novice")
    why = g.js("document.querySelector('.explain').innerText")
    assert "stocks" in why and "fixed income" not in why.lower() and "equity" not in why.lower()
    assert g.js("!!document.querySelector('details.hood:not([open])')")


def test_local_answers_at_three_depths(guide):
    got = {}
    for d in ("novice", "some", "expert"):
        g = guide()
        g.to_mix(depth=d)
        g.pg.fill("#chat-in", "what is volatility?")
        g.pg.press("#chat-in", "Enter")
        g.pg.wait_for_function("document.querySelectorAll('#qa-mix .msg.bot').length > 0", timeout=10000)
        got[d] = g.js("document.querySelector('#qa-mix .msg.bot:last-child').innerText")
    assert "bumpy" in got["novice"]
    assert "bumpy" not in got["some"] and "standard deviation" not in got["some"]
    assert "standard deviation" in got["expert"] and "Your mix:" in got["expert"]


def test_claude_hears_the_depth_never_a_label_and_is_checked(guide):
    bad = FAKE_CLAUDE.replace(
        "Here is a short explanation from the numbers on this page, and you can change any answer.", "As a beginner, you should buy VFV."
    )
    g = guide(init=bad)
    g.pg.wait_for_selector('#home-connect [data-act="connect"]', timeout=10000)
    g.pg.click('[data-prompt="1"]')
    g.pg.locator('[data-act="connect"]').last.click()
    g.pg.wait_for_function("window.robokitGuide.ai === 'on'", timeout=10000)
    g.tap("EXP", "expert")
    g.say("Can you walk me through the trade-offs in my situation?")
    asked = g.js("JSON.stringify(window.__asked.at(-1))")
    assert "brief and technical" in asked and '"depth"' not in asked
    assert "you should buy VFV" not in " ".join(g.last(3))


def test_phone_width_under_the_hood(guide):
    g = guide(viewport={"width": 390, "height": 844})
    g.to_mix(depth="expert")
    assert g.js("document.documentElement.scrollWidth <= window.innerWidth + 1")


def test_a_drop_answer_typed_early_waits_for_its_card(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "some")
    g.say("actually in a drop I'd sell everything")
    assert g.js("window.robokitGuide.st.answers.C2") is None
    assert g.js("window.robokitGuide.st.preselect.C2") == "sell_all"
    assert g.pending_step() == "B1"


def test_none_is_an_answer_to_the_income_question(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "some")
    g.tap("B1", "20plus")
    g.tap("A2", "yes")
    g.tap("A3", "no")
    g.pg.locator("[data-money='25000']").last.click()
    g.say("none")
    assert g.js("window.robokitGuide.st.answers.B5") == "none"


# ------------------------------------------------------------------ v3.3: the team's cleaned-up feedback (Penguru review, tab 3)


def test_v33_the_page_is_penguru_with_the_brand_kit(guide):
    g = guide()
    assert g.pg.title() == "Penguru"
    assert g.js("document.querySelector('.brand b').textContent") == "Penguru" and g.js("!!document.querySelector('.brand svg.logo')")
    assert "Sora" in g.js("getComputedStyle(document.body).fontFamily")
    assert g.js("getComputedStyle(document.documentElement).getPropertyValue('--ink').trim().toUpperCase()") == "#12263F"
    g.to_mix()
    text = g.js("document.body.innerText")
    assert "Robo-Kit" not in text and "Penguru is an educational tool" in text  # the engine's disclosure is renamed too
    assert "Robo-Kit" not in g.js("window.robokitGuide.summary()")


def test_v33_the_opening_has_no_printed_definitions_and_carries_the_mark(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    hello = g.js("document.querySelector('#thread .k-hello').innerText")
    assert hello.startswith("Hi, I'm Penguru.")
    assert g.js("!!document.querySelector('#thread .k-hello svg.logo')")
    assert g.js("document.querySelectorAll('#thread .defs').length") == 0  # the words are buttons instead
    assert g.js("document.querySelectorAll('#thread .k-hello .term').length") >= 1


def test_v33_a_term_or_learn_more_tapped_twice_is_shown_once(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    term = g.js("document.querySelector('#thread .k-hello .term').dataset.term")
    for _ in range(3):
        g.pg.locator("#thread .k-hello .term").first.click()
    assert g.js(f"window.robokitGuide.st.log.filter(m => m.def === 'term:{term}').length") == 1
    g.pg.wait_for_function("!!document.querySelector('#thread .msg.flash')", timeout=5000)  # the earlier one is pointed to
    g.tap("EXP", "some")
    for _ in range(2):
        g.pg.locator('[data-learn="B1"]').last.click()
    assert g.js("window.robokitGuide.st.log.filter(m => m.def === 'learn:B1').length") == 1


def test_v33_a_suggested_question_tapped_twice_is_answered_once(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "novice")
    chip = '[data-ask="Why does time matter?"]'
    g.pg.locator(chip).last.click()
    g.pg.wait_for_function("window.robokitGuide.st.log.some(m => m.def === 'ask:Why does time matter?')", timeout=10000)
    g.pg.locator(chip).first.click()
    assert g.js("window.robokitGuide.st.log.filter(m => m.who === 'me' && m.text === 'Why does time matter?').length") == 1


def test_v33_factor_is_not_linked_outside_its_investing_sense(guide):
    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "novice")
    g.say("Why does time matter?")
    assert "biggest factor" in " ".join(g.last(3))  # the answer Javed flagged
    assert g.js("document.querySelectorAll('[data-term=factor]').length") == 0


def test_v33_no_risk_level_is_mentioned_before_the_assessment(guide):
    import re

    g = guide()
    g.pg.click('[data-prompt="1"]')
    g.tap("EXP", "novice")
    g.tap("B1", "20plus")
    g.tap("A2", "no")  # the gate that used to say "keeps the level at 2 or below"
    g.tap("A3", "lot")
    g.pg.locator("[data-money='25000']").last.click()
    g.tap("B5", "mostly")
    g.tap("C0", "medium")
    g.tap("C2", "wait")
    seen = g.js("document.querySelector('#thread').innerText")
    assert not re.search(r"\blevels?\b", seen, re.I), re.findall(r".{60}\blevels?\b.{20}", seen, re.I)
    if g.pending_step() == "RECON":
        g.tap("RECON", "C2")
    g.tap("C1", "3")
    assert not re.search(r"\blevels?\b", g.js("[...document.querySelectorAll('.step-card')].at(-1).innerText"), re.I)  # the fine-tune offer
    g.tap("FT", "no")
    g.pg.wait_for_selector("#assess .means", timeout=30000)
    assert "SUGGESTED RISK LEVEL" in g.js("document.querySelector('#assess').innerText").upper()  # introduced here, with what it means


def test_v33_preferences_lead_straight_to_the_tickers_then_the_mix(guide):
    g = guide()
    g.to_assessment()
    g.pg.check("#ack")
    g.pg.click('[data-act="assess-ok"]')
    g.pg.locator('[data-pref="focus"][data-key="esg"]').last.click()
    g.pg.locator('[data-act="prefs-apply"]').last.click()
    g.pg.wait_for_selector('.step-card[data-step="TICKER"]', timeout=15000)
    thread = g.js("document.querySelector('#thread').innerText")
    assert "Quick note" not in thread and "Keep going as planned" not in thread  # no market note mid-flow
    assert g.js("document.querySelectorAll('.step-card[data-step=TICKER]').length") == 1  # the ticker question once
    g.pg.locator('[data-skip="TICKER"]').last.click()
    g.pg.wait_for_selector(".fund", timeout=30000)  # no shortlist preview, no Calculate button
    assert g.js("document.querySelectorAll('[data-act=calculate]').length") == 0
    assert "Market context" in g.js("document.querySelector('[data-screen=mix]').innerText")  # context stays on the mix


def test_v33_the_withdrawal_plan_follows_the_goal_and_can_be_changed(guide):
    g = guide()
    g.to_assessment()
    how = g.js("document.querySelector('#assess').textContent")  # "How this was worked out" is a closed <details>
    assert "more than 10 years, assumed from your goal" in how
    g.pg.check("#ack")
    g.pg.click('[data-act="assess-ok"]')
    g.pg.locator('[data-skip="PREFS"]').last.click()
    g.pg.locator('[data-skip="TICKER"]').last.click()
    g.pg.wait_for_selector(".fund", timeout=30000)
    answers = g.js("document.querySelector('dl.answers').textContent")  # inside the closed "Your answers" panel
    assert "assumed from your goal" in answers
    g.pg.locator("details.more summary").first.click()  # open "Your answers"
    g.pg.locator('dl.answers [data-change="B2"]').click()
    g.pg.wait_for_selector('.step-card[data-step="B2"]', timeout=15000)
    g.tap("B2", "once")
    assert g.js("window.robokitGuide.st.answers.B2") == "once" and not g.js("window.robokitGuide.st.auto.has('B2')")


def test_v33_a_home_needed_within_two_years_gets_no_stock_mix(guide):
    g = guide()
    g.pg.click('[data-prompt="2"]')  # saving for a home: all at once, assumed
    g.tap("EXP", "some")
    g.tap("B1", "lt2")
    assert g.js("window.robokitGuide.st.answers.B2") == "once"
    assert g.pending_step() == "BASICS"  # no withdrawal question
