"""The conversation: each card once, one message at a time and in order, Stop and errors, and chat previews."""

import pytest

pytestmark = pytest.mark.ui

# Cards added after the last assistant reply, by kind.
AFTER_AI = """sel => { const ai = [...document.querySelectorAll('#thread > .turn-ai')].pop(); let n = 0;
  for (let x = ai.nextElementSibling; x; x = x.nextElementSibling) if (x.matches(sel)) n++; return n; }"""
# The last assistant reply: its text, its highlighted figures and its footer.
LAST_AI = """() => { const n = [...document.querySelectorAll('#thread > .turn-ai')].pop(), f = n.querySelector('.ai-foot');
  return { text: n.querySelector('.ai-text').innerText.trim(), marks: [...n.querySelectorAll('.ai-text mark')].map(m => m.textContent),
           items: [...n.querySelectorAll('.ai-text li')].map(li => li.textContent.trim()), foot: f.hidden ? '' : f.innerText.trim() }; }"""
# An AI stand-in that, like the real capability, can hold several requests at once and rejects `cancelled` on abort.
MANY_AT_ONCE = """() => {
  window.__q = [];
  const fake = (input, opts = {}) => new Promise((resolve, reject) => {
    const e = { opts, resolve, reject, done: false }; window.__q.push(e);
    opts.signal?.addEventListener('abort', () => { if (!e.done) { e.done = true; reject({ code: 'cancelled', message: 'cancelled' }); } });
  });
  fake.limits = async () => ({ tools: true });
  window.robokit.ai.sample = fake;
  window.__live = () => window.__q.filter(e => !e.done).length;
  window.__answer = (t) => { const e = window.__q.find(x => !x.done); e.done = true;
    e.resolve({ text: t, truncated: false, modelTierApplied: 'default' }); };
}"""
# The preview build of propose_change made slower, as on a slow phone; it says when it starts.
SLOW_PREVIEW = """() => { const app = window.robokit, run = app.run.bind(app);
  app.run = (type, req, ...rest) => (type === 'build' && req && req.seed === 0)
    ? (window.__slowStarted = true, new Promise(r => setTimeout(r, 2500)).then(() => run(type, req, ...rest)))
    : run(type, req, ...rest); }"""


def test_one_reply_shows_each_card_once_however_the_model_names_it(page_factory):
    """One AI turn, rewrite pass included, shows each fund, comparison, search, term or back-test card once, however it is named."""
    p = page_factory("mock.html")
    p.send("Tell me about VFV and XEQT, gold funds, fees and the back-test")
    p.pending()
    p.call("etf_profile", {"ticker": "VFV"})
    p.call("compare_etfs", {"tickers": ["VFV", "XEQT"]})
    p.call("search_etfs", {"query": "gold"})
    p.call("explain_term", {"term": "mer"})
    p.call("backtest_summary", {})
    p.finish("VFV will return 99% next year.")  # an invented figure: the page asks for one rewrite in the same turn
    p.pending()
    p.call("etf_profile", {"ticker": "VFV.TO"})  # the spellings the tool results themselves use
    p.call("compare_etfs", {"tickers": ["VFV.TO", "XEQT.TO"]})
    p.call("search_etfs", {"query": "gold", "sort_by": "mer"})
    p.call("explain_term", {"term": "management expense ratio"})
    p.call("backtest_summary", {"level": p.js("robokit.st.level")})
    p.finish("The cards below show the facts.")
    p.replied()
    counts = p.js("""() => ({
      fund: document.querySelectorAll('.card-fund[data-fund="VFV.TO"]').length,
      compare: document.querySelectorAll('.card-compare').length,
      search: document.querySelectorAll('.card-results').length,
      term: [...document.querySelectorAll('.card-term h3')].filter(h => /expense/i.test(h.textContent)).length,
      backtest: [...document.querySelectorAll('#thread > section.card')]
        .filter(n => n.firstElementChild?.classList.contains('mech')).length })""")
    assert counts == {"fund": 1, "compare": 1, "search": 1, "term": 1, "backtest": 1}
    assert p.errors == []


def test_cards_are_matched_by_the_fund_they_show(page_factory):
    """Cards are matched by the funds they show: unknown, extra or other-market spellings never add a copy within one turn."""

    def turn(p, calls):
        p.send("Can you put a few funds side by side for me?")
        p.pending()
        for name, args in calls:
            p.call(name, args)
        p.finish("See the cards below.")
        p.replied()

    ca = page_factory("mock.html")
    turn(
        ca,
        [
            ("compare_etfs", {"tickers": ["VFV", "XEQT", "BOGUSX"]}),
            ("explain_term", {"term": "mer"}),
            ("compare_etfs", {"tickers": ["XEQT", "VFV"]}),
        ],
    )
    assert ca.js(AFTER_AI, ".card-compare") == 1, "an unknown ticker in the first list made a second comparison card"
    six = ["VFV", "XEQT", "VEQT", "ZSP", "XIC", "VCN"]
    turn(ca, [("compare_etfs", {"tickers": six}), ("explain_term", {"term": "volatility"}), ("compare_etfs", {"tickers": six[:5]})])
    assert ca.js(AFTER_AI, ".card-compare") == 1, "six tickers then the five shown made a second comparison card"

    us = page_factory("mock.html", market="US")
    assert us.js("Object.keys(robokit.markets)") == ["US"]  # the Canadian list is not loaded yet
    turn(
        us,
        [
            ("compare_etfs", {"tickers": ["VFV", "XEQT"]}),
            ("explain_term", {"term": "mer"}),
            ("compare_etfs", {"tickers": ["VFV.TO", "XEQT.TO"]}),
        ],
    )
    assert us.js(AFTER_AI, ".card-compare") == 1
    turn(us, [("etf_profile", {"ticker": "VFV"}), ("explain_term", {"term": "mer"}), ("etf_profile", {"ticker": "VFV.TO"})])
    assert us.js(AFTER_AI, ".card-fund") == 1


def test_tapping_the_same_chip_or_tray_row_twice_shows_one_card(page_factory):
    """Tapping the 'What is an ETF?' chip or a tray fund row twice in a row shows one card, not two."""
    p = page_factory()
    p.pg.click('[data-chip="etf"]')
    p.pg.click('[data-chip="etf"]')
    assert p.js("[...document.querySelectorAll('#thread .card-term h3')].filter(h => h.textContent.startsWith('ETF')).length") == 1
    t = p.pg.locator("#tray-funds button").first.get_attribute("data-t")
    for _ in range(2):
        p.pg.click(f'#tray-funds button[data-t="{t}"]')
    assert p.js("t => document.querySelectorAll(`#thread .card-fund[data-fund='${t}']`).length", t) == 1


def test_one_message_at_a_time_in_the_order_sent(page_factory):
    """A message sent while the page is busy stays in the box, only one AI request runs, and the history keeps the order sent."""
    p = page_factory("mock.html", slow={"us.json": 2500})
    p.js(MANY_AT_ONCE)
    first, second = "What about QQQ?", "And is VFV cheaper than XEQT?"
    p.send(first)  # QQQ is a US fund: the US list loads first
    p.send(second)
    assert p.js("document.querySelector('#q').value") == second
    assert p.js("[...document.querySelectorAll('.turn-user')].map(n => n.innerText)") == [first]
    p.pg.wait_for_function("window.__q.length === 1", timeout=15000)  # the first reply has started
    p.pg.press("#q", "Enter")  # tried again while the reply runs
    p.pg.click('[data-chip="compare"]')  # the Compare chip only changes the hint
    assert p.js("document.querySelector('#q').value") == second
    assert p.js("window.__live()") == 1
    assert p.pg.is_visible("#stop")
    p.js("window.__answer('Answer to the first message.')")
    p.replied()
    assert p.js("[...document.querySelectorAll('.turn-user')].map(n => n.innerText)") == [first]  # nothing was sent on its own
    p.pg.press("#q", "Enter")
    p.pg.wait_for_function("window.__q.length === 2")
    assert p.js("robokit.ai.turns.map(t => t.content)") == [first, "Answer to the first message.", second]
    p.js("window.__answer('Answer to the second message.')")
    p.replied()
    assert p.errors == []


def test_cards_follow_their_own_message_when_a_list_loads_slowly(page_factory):
    """On a slow connection an other-market ticker's card lands under its own message; the next message waits in the box."""
    p = page_factory(slow={"us.json": 2500})
    p.send("QQQ")
    p.send("XEQT")
    assert p.js("document.querySelector('#q').value") == "XEQT"
    p.pg.wait_for_function("!window.robokit.busy", timeout=15000)
    p.pg.press("#q", "Enter")
    p.pg.wait_for_selector('.card-fund[data-fund="XEQT.TO"]')
    t = p.thread()
    assert t.index("msg:QQQ") < t.index("fund:QQQ") < t.index("msg:XEQT") < t.index("fund:XEQT.TO")


def test_stop_and_errors_keep_what_was_written_and_check_it(page_factory):
    """Stop or a failed reply keeps streamed text with unsupported figures flagged, and never shows an empty bubble or a raw error."""
    p = page_factory("mock.html")
    text = "The mix charges about $9,876 a year in fees and lost 0.99% in its worst month."

    p.send("What is a bond fund?")  # Stop before any text
    p.pending()
    p.pg.click("#stop")
    p.replied()
    assert p.js(LAST_AI)["text"] == "Stopped."

    p.send("What does the mix cost in fees?")  # Stop with part of the reply on screen
    p.pending()
    p.stream(text)
    p.pg.click("#stop")
    p.replied()
    r = p.js(LAST_AI)
    assert "$9,876" in r["text"] and r["marks"] and "Not from a tool" in r["foot"]

    p.send("What does a bond fund cost?")  # Stop while the checker's rewrite is running
    p.pending()
    p.stream("A bond fund costs about 0.99% a year.")
    p.finish("A bond fund costs about 0.99% a year.")
    p.pending()
    p.pg.click("#stop")
    p.replied()
    assert p.js(LAST_AI)["text"]

    p.send("What is an index fund?")  # a failure the person cannot act on: plain words
    p.pending()
    p.fail("session_expired", "SessionExpired: token refresh failed (401)")
    p.replied()
    r = p.js(LAST_AI)
    assert "SessionExpired" not in r["text"] and "could not finish" in r["text"]

    p.send("What does the mix cost in fees?")  # a rate limit after part of the reply streamed
    p.pending()
    p.fail("rate_limited", "usage limit reached", text)
    p.replied()
    r = p.js(LAST_AI)
    assert "$9,876" in r["text"] and "Too many requests" in r["text"]
    assert r["marks"] and "Not from a tool" in r["foot"]
    assert p.errors == []


def test_nothing_from_a_stopped_reply_appears_later(page_factory):
    """Cards and previews still being prepared when Stop is pressed never appear, under the stopped reply or the next message."""
    p = page_factory("mock.html", slow={"us.json": 3000})
    p.js(SLOW_PREVIEW)
    p.send("tell me about a big tech fund and show a level 4 preview")
    p.pending()
    p.js("""() => { window.__done = 0; window.__status = null; const M = window.__mock;
      M.call('etf_profile', { ticker: 'QQQ' }).finally(() => window.__done++);
      M.call('compare_etfs', { tickers: ['QQQ', 'XEQT'] }).finally(() => window.__done++);
      M.call('propose_change', { level: 4 }).then(r => { window.__status = r.status || r.error; }).finally(() => window.__done++); }""")
    p.pg.wait_for_function("window.__slowStarted === true")  # the preview is being computed; the US list is still downloading
    p.pg.click("#stop")
    p.replied()
    p.send("Never mind. What is an index fund?")
    p.pending()
    p.pg.wait_for_function("window.__done === 3", timeout=15000)
    assert p.js("document.querySelectorAll('#thread .card-fund, #thread .card-compare, #thread .card-prop').length") == 0
    assert "stopped" in p.js("window.__status")
    p.reply("An index fund follows a market index.")
    assert p.js("document.querySelectorAll('#thread .card-prop').length") == 0


def test_previews_apply_only_to_the_mix_they_were_made_for(page_factory):
    """Chat previews apply only to the mix they were made for: an empty one shows no card, a later level or market voids one."""
    p = page_factory("mock.html")
    p.send("Could I split my money between VOO and XEQT?")
    p.pending()
    r = p.call("propose_change", {"weights": {"VOO": 0.6, "XEQT": 0.4}})
    assert r["not_added"] and any("VOO" in x for x in r["not_added"])  # VOO is a US fund: said, not silently dropped
    cards = p.js("document.querySelectorAll('.card-prop').length")
    r = p.call("propose_change", {"add": ["VOO"]})
    assert r["status"].startswith("no change") and r["not_added"]
    assert p.js("document.querySelectorAll('.card-prop').length") == cards  # nothing usable: no card
    p.reply("See the preview below.")

    p.send("Could I add a gold fund to the mix?")
    p.pending()
    gold = p.call("search_etfs", {"query": "gold", "asset_class": "Commodity"})["funds"][0]["ticker"]
    p.call("propose_change", {"add": [gold]})
    p.reply("Here is a preview of adding it. Nothing changes until you tap Apply.")
    p.pg.click("#tray-levels .seg[data-l='4']")  # the person picks a level afterwards
    p.settled()
    assert p.js("robokit.st.level") == 4
    p.pg.click(".card-prop:not(.is-done) [data-apply]")
    p.settled()
    assert p.js("robokit.st.level") == 4
    assert p.js("[...document.querySelectorAll('.card-prop .prop-status')].pop().textContent").startswith("Not applied")
    assert gold not in p.js("robokit.st.mix.satellites")

    p.send("Then preview adding it at this level, please.")
    p.pending()
    p.js("() => robokit.loadMarket('US')")  # the US list is here, so the switch lands at once
    p.js(
        "t => { window.__p = window.__mock.call('propose_change', { add: [t] }); document.querySelector('[data-market=US]').click(); }",
        gold,
    )
    p.js("async () => { await window.__p; }")
    p.reply("Here is a preview of adding it.")
    p.pg.wait_for_function("robokit.st.market === 'US'")
    p.settled()
    assert p.js("document.querySelectorAll('.card-prop:not(.is-done) [data-apply]:not([disabled])').length") == 0
    assert not [t for t in p.js("robokit.st.mix.satellites") if t.endswith((".TO", ".NE"))]
    assert p.errors == []


def test_replies_render_as_written(page_factory):
    """Replies keep their lines, bullets and list numbers, and unsupported figures are marked only where they stand alone."""
    p = page_factory("mock.html")
    p.send("I read that a fund fell 15% last year")
    p.pending()
    p.reply("It fell 15% last year, and [a 15% drop](https://example.com/x) could be followed by **another 5%**.")
    marks = p.js("""() => [...[...document.querySelectorAll('.turn-ai')].pop().querySelectorAll('.ai-text mark')].map(m => {
      const prev = m.previousSibling ? m.previousSibling.textContent : ''; return { text: m.textContent, before: prev.slice(-1) }; })""")
    assert marks and all(m["text"] == "5%" and not (m["before"].isdigit() or m["before"] == ".") for m in marks)

    p.send("How is the mix split between stocks and bonds?")
    p.pending()
    p.reply("The mix at level 3 splits like this:\n- 37% in bonds\n- 63% in stocks")
    r = p.js(LAST_AI)
    assert {"37%", "63%"} <= set(r["marks"]) and "- 37%" not in r["foot"]
    assert r["items"] == ["37% in bonds", "63% in stocks"]

    p.send("Which levels take more risk?")
    p.pending()
    p.reply("Two of the levels take more risk:\n4. Growth\n5. Aggressive\nThe tray shows both.")
    shape = p.js("""() => { const t = [...document.querySelectorAll('.turn-ai')].pop().querySelector('.ai-text');
      const ol = t.querySelector('ol');
      return { start: ol?.getAttribute('start'), items: [...t.querySelectorAll('li')].map(li => li.textContent.trim()),
               paras: [...t.querySelectorAll('p')].map(x => x.textContent.trim()) }; }""")
    assert shape == {
        "start": "4",
        "items": ["Growth", "Aggressive"],
        "paras": ["Two of the levels take more risk:", "The tray shows both."],
    }
