"""The page without the AI: what a typed message opens (definitions, fund cards, comparisons, searches) and which numbers
in a message it uses."""

import re

import pytest

pytestmark = pytest.mark.ui

# The funds the last message listed (its search-results card), with the fields the word search looks in.
RESULT_FUNDS = """() => { const u = [...document.querySelectorAll('#thread > .turn-user')].pop(); let c = u.nextElementSibling;
  while (c && !c.classList.contains('card-results')) c = c.nextElementSibling; if (!c) return [];
  return [...c.querySelectorAll('.res-main')].map(b => { const f = window.robokit.resolveFund(b.dataset.t);
    return { sym: f.symbol, text: [f.name, f.theme || '', f.issuer || ''].join(' | ') }; }); }"""
OTHER_MARKET_LINE = """t => [...document.querySelector(`.card-fund[data-fund='${t}']`).querySelectorAll('p')]
  .some(p => /trades in the other market/.test(p.textContent))"""
# The funds the last message listed, in order, with the fields the search looks at.
LISTED = """() => { const u = [...document.querySelectorAll('#thread > .turn-user')].pop(); let c = u.nextElementSibling;
  while (c && !c.classList.contains('card-results')) c = c.nextElementSibling; if (!c) return [];
  return [...c.querySelectorAll('.res-main')].map(b => { const f = window.robokit.resolveFund(b.dataset.t);
    return { sym: f.symbol, name: f.name, theme: f.theme || '', region: f.region || '', cls: f.asset_class || '' }; }); }"""
ETF_TERM = "term:ETF (exchange-traded fund)"


def kinds(replies, kind):
    return [r for r in replies if r.startswith(kind)]


def listed(p, text):
    """Send `text` and return the funds its search card lists (failing when it lists none)."""
    p.ask(text)
    funds = p.js(LISTED)
    assert funds, f"{text!r} listed no funds: {p.replies()}"
    return funds


def test_term_questions_open_their_definition(page_factory):
    """A question about a glossary term opens its definition, with or without a question mark, even with an amount in it."""
    p = page_factory()
    p.ask("is a 1% fee on $100,000 a lot?")  # a first message with an amount that is a question, not a build request
    assert "term:MER (management expense ratio)" in p.replies()
    assert p.js("robokit.st.check.open") is False
    for text, term in [
        ("what is duration?", "Duration"),
        ("what is a covered call ETF?", "Covered-call ETF"),
        ("what does AUM mean?", "AUM (assets under management)"),
        ("how does rebalancing work with 20k?", "Rebalancing"),
    ]:
        p.ask(text)
        assert f"term:{term}" in p.replies(), text
    for text in ["what are etfs", "whats an etf", "how do etfs work"]:
        p.ask(text)
        assert [r for r in p.replies() if r.startswith("term:ETF")], text


def test_greetings_and_filler_search_nothing(page_factory):
    """Greetings and filler get the 'nothing matched' help, never unrelated funds, and a results note always has its results."""
    p = page_factory()
    for text in ["hi", "ok", "\U0001f642", "hi there", "thanks", "hello there my friend", "ZZZZ"]:
        p.ask(text)
        r = p.replies()
        assert not kinds(r, "results"), f"{text!r} listed funds: {r}"
        assert any("Nothing matched" in x for x in r), f"{text!r} got {r}"
    dangling = p.js("""() => [...document.querySelectorAll('#thread > .turn-note')]
        .filter(n => /what matches your words/.test(n.textContent) && !n.nextElementSibling?.classList.contains('card-results')).length""")
    assert dangling == 0


def test_fund_search_matches_whole_words(page_factory):
    """Word search matches whole words, and fund requests with 'market' or 'war' inside a word search funds, not the news."""
    p = page_factory(market="US")
    for text, word in [("gold", "gold"), ("Good morning", "morning")]:
        p.ask(text)
        rx = re.compile(rf"\b{word}s?\b", re.I)
        off = [f for f in p.js(RESULT_FUNDS) if not rx.search(f["text"]) and f["sym"].lower() != word]
        assert not off, f"{text!r} listed {off[:3]}"
    p.pg.click('[data-market="CA"]')
    p.pg.wait_for_function("robokit.st.market === 'CA'")
    p.ask("what is a gic?")
    assert not [f for f in p.js(RESULT_FUNDS) if not re.search(r"\bgics?\b", f["text"], re.I)]
    for text in ["emerging markets etf", "software etf", "money market fund"]:
        p.ask(text)
        assert "context" not in p.replies(), text
    for text in ["canadian bond etf", "low volatility etf"]:  # a theme that is also a glossary term still reaches its funds
        p.ask(text)
        offers_funds = p.js("() => !![...document.querySelectorAll('#thread .card-term')].pop()?.querySelector('[data-theme]')")
        assert "results" in p.replies() or offers_funds, text


def test_lone_words_are_not_read_as_tickers(page_factory):
    """A lone glossary, filler or common word opens its definition, the help or the market card, never a same-named fund."""
    p = page_factory()
    p.ask("reit")
    assert "term:REIT" in p.replies() and not kinds(p.replies(), "fund:")
    p.ask("QQQ")  # loads the US list, which has more one-word symbols
    assert p.replies() == ["fund:QQQ"]
    p.ask("bond")
    assert "term:Bond" in p.replies() and not kinds(p.replies(), "fund:")
    p.ask("more")
    assert not kinds(p.replies(), "fund:")
    p.pg.click('[data-market="US"]')
    p.pg.wait_for_function("robokit.st.market === 'US'")
    p.ask("war")
    assert "context" in p.replies() and not kinds(p.replies(), "fund:")
    p.ask("cool")
    assert not kinds(p.replies(), "fund:")


def test_lower_case_tickers_are_recognised(page_factory):
    """Tickers typed in lower or mixed case, joined by 'or'/'vs' or ending in '?', open their fund card or a comparison."""
    p = page_factory()
    for text, want in [
        ("xeqt or veqt?", {"XEQT", "VEQT"}),
        ("xeqt or zeqt?", {"XEQT", "ZEQT"}),
        ("vgro or zgro?", {"VGRO", "ZGRO"}),
        ("Xeqt vs veqt", {"XEQT", "VEQT"}),
    ]:
        p.ask(text)
        compares = [set(r[len("compare:") :].split("+")) for r in kinds(p.replies(), "compare:")]
        assert any(c >= want for c in compares), f"{text!r} -> {p.replies()}"
    p.ask("what about vfv?")
    assert "fund:VFV.TO" in p.replies()


def test_tickers_resolve_in_the_selected_market_first(page_factory):
    """Tickers resolve in the selected market first, other-market tickers are still found, and fund cards follow a switch."""
    p = page_factory()
    p.ask("qqqm")  # only on the US list, which is not loaded yet
    assert p.replies() == ["fund:QQQM"]
    p.ask("CIEI")  # on both lists: the Canadian one is selected
    assert p.replies() == ["fund:CIEI.TO"]
    p.ask("VFV vs VOO")
    text = p.js("[...document.querySelectorAll('.card-compare')].pop().innerText")
    assert ("CAD" in text and "USD" in text) or "other market" in text
    assert p.js(OTHER_MARKET_LINE, "QQQM") and not p.js(OTHER_MARKET_LINE, "CIEI.TO")
    p.pg.click('[data-market="US"]')
    p.pg.wait_for_function("robokit.st.market === 'US'")
    p.settled()
    assert not p.js(OTHER_MARKET_LINE, "QQQM")
    if p.js("robokit.resolveFund('QQQM').eligible"):
        assert p.js("!!document.querySelector(`.card-fund[data-fund='QQQM'] [data-add]`)")
    assert p.js(OTHER_MARKET_LINE, "CIEI.TO")
    assert not p.js("!!document.querySelector(`.card-fund[data-fund='CIEI.TO'] [data-add]`)")


def test_first_message_keeps_the_market_unless_it_asks_for_another(page_factory):
    """A first message that says 'us' or asks about the US dollar keeps the page on the Canadian list."""
    p = page_factory()
    p.ask("tell us about XEQT")  # 'us' is a pronoun here
    assert p.js("robokit.st.market") == "CA" and not p.js(OTHER_MARKET_LINE, "XEQT.TO")

    p = page_factory()
    p.ask("should I hedge USD?")
    switched = p.js("robokit.st.market") != "CA"
    assert not switched or any(re.search(r"US market|switched", r) for r in p.replies())


def test_first_message_numbers_are_read_with_care(page_factory):
    """In a first message a monthly need is money taken out, a number in a link is not the amount, and a used number is said."""
    p = page_factory()
    p.ask("I am retired with 400k and need $2,000 a month")
    assert p.js("robokit.st.monthly") <= 0

    p = page_factory()
    before = p.js("robokit.st.amount")
    p.ask("I have 5000 to invest, what should I buy?")
    assert p.js("robokit.st.amount") == before or any("5,000" in r or "5000" in r for r in p.replies())

    p = page_factory()
    p.ask("https://www.blackrock.com/ca/investors/en/products/309480/ishares-core-equity-etf-portfolio")
    assert p.js("robokit.st.amount") != 309480 and p.js("robokit.st.check.open") is False


def test_later_message_numbers_are_offered_one_at_a_time(page_factory):
    """Numbers in a later message are offered separately, and the offer card never says 'Not applied' about one that was."""
    p = page_factory()
    p.ask("hi")
    p.ask("I have 20k and can add 500 a month")
    first = p.pg.locator(".turn-offer").nth(0)
    assert [b.get_attribute("data-fact") for b in first.locator("[data-fact]").all()] == ["amount", "monthly"]
    first.locator("[data-fact=amount]").click()
    assert p.js("robokit.st.amount") == 20000
    assert first.locator("[data-fact=monthly]").is_enabled()
    first.locator("[data-nofact]").click()
    assert first.locator(".offer-status").text_content().strip() != "Not applied."
    assert p.js("robokit.st.monthly") == 0
    p.settled()
    p.ask("I have 50k and I will add $300 a month")
    second = p.pg.locator(".turn-offer").nth(1)
    second.locator("[data-fact=amount]").click()
    second.locator("[data-fact=monthly]").click()
    assert p.js("[robokit.st.amount, robokit.st.monthly]") == [50000, 300]


def test_theme_questions_list_their_funds_and_etf_questions_define_etfs(page_factory):
    """Questions naming a theme, singular or plural, list that theme's funds; general questions about ETFs open the ETF definition."""
    p = page_factory()
    for text, want in [
        ("what is the best canadian dividend etf", r"dividend"),
        ("tell me about gold etfs", r"\bgold\b"),
        ("canadian bonds etf", r"\bbonds?\b|fixed income"),
        ("reits in canada", r"\breits?\b|real estate"),
        ("bond etfs", r"\bbonds?\b|fixed income"),
        ("tech etf", r"\btech"),
        ("S&P500 etf", r"(?=.*s&p)(?=.*\b500\b)"),
    ]:
        off = [f["sym"] for f in listed(p, text) if not re.search(want, f"{f['name']} | {f['theme']} | {f['cls']}", re.I)]
        assert not off, f"{text!r} listed {off[:3]}"
    for text in ["are etfs safe?", "whats the difference between an etf and a mutual fund", "is an etf a good investment"]:
        p.ask(text)
        assert ETF_TERM in p.replies() and not kinds(p.replies(), "results"), f"{text!r} -> {p.replies()}"


def test_market_news_the_us_region_and_stocks_are_read_as_meant(page_factory):
    """'How are markets?' opens the market card while 'total market index' searches funds; 'US' and 'stocks' narrow a fund search."""
    p = page_factory()
    p.ask("how are markets?")
    assert p.replies() == ["context"]
    assert all(re.search(r"total market", f["name"], re.I) for f in listed(p, "total market index"))
    listed(p, "market cap")
    for text in ["US equity etf", "US dividend etf"]:  # on the Canadian list: funds that hold US stocks come first
        first = listed(p, text)[:5]
        assert all(f["region"] == "US" for f in first), f"{text!r} listed {first}"
    assert all(f["cls"] == "Equity" for f in listed(p, "canadian stocks")[:5])
    assert all(re.search(r"\btech", f"{f['name']} | {f['theme']}", re.I) for f in listed(p, "tech stocks"))


def test_extra_words_capitals_and_lone_words_are_read_with_care(page_factory):
    """Extra words list the closest funds, capitals are read as words, and a lone word is searched before it is tried as a ticker."""
    p = page_factory()
    found = listed(p, "which dividend ETFs pay monthly?")  # every word matched, or the closest funds with a note
    assert found and all(re.search(r"dividend|monthly|income", f"{f['name']} | {f['theme']}", re.I) for f in found), found
    names = " | ".join(f["name"] for f in listed(p, "gold or silver etf"))
    assert re.search(r"\bgold\b", names, re.I) and re.search(r"\bsilver\b", names, re.I), names
    for text in ["I WANT TO KNOW WHAT AN ETF IS", "HELLO I AM NEW AT THIS"]:
        p.ask(text)
        assert not kinds(p.replies(), "fund:") and not kinds(p.replies(), "compare:"), f"{text!r} -> {p.replies()}"
    p.ask("SHOULD I BUY VTI OR VOO")  # tickers still count in a message typed in capitals
    assert any(set(c[len("compare:") :].split("+")) >= {"VTI", "VOO"} for c in kinds(p.replies(), "compare:")), p.replies()
    for word in ["bank", "asia"]:  # theme words that are also tickers are searched
        listed(p, word)
        assert not kinds(p.replies(), "fund:"), f"{word!r} -> {p.replies()}"
    for word in ["sure", "ty"]:  # replies, not tickers
        p.ask(word)
        assert not kinds(p.replies(), "fund:"), f"{word!r} -> {p.replies()}"
    p.ask("schg")  # no fund name has this word: it is then tried as a ticker
    assert p.replies() == ["fund:SCHG"]
    p.pg.click('[data-market="US"]')
    p.pg.wait_for_function("robokit.st.market === 'US'")
    p.settled()
    listed(p, "tech")
    assert not kinds(p.replies(), "fund:")
