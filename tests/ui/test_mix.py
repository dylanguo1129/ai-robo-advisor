"""The mix: own weights, the fund shelf, Reset, one mix per market, the notes that follow a rebuild, the tray inputs and
the buy plan."""

import re

import pytest

pytestmark = pytest.mark.ui

TRAY_FUNDS = "() => [...document.querySelectorAll('#tray-funds li b')].map(b => b.textContent)"
WEIGHTS = "() => Object.fromEntries(robokit.st.result.holdings.map(h => [h.ticker, h.weight]))"
HELD = "() => Object.fromEntries(robokit.st.result.holdings.map(h => [h.ticker, Math.round(h.weight * 1000) / 1000]))"
PHONE = {"width": 375, "height": 812}
SIDEWAYS = "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
# Where an element is, and the band of the screen between the top bar and the composer (or the phone's tray bar).
ON_SCREEN = """sel => { const r = document.querySelector(sel).getBoundingClientRect(), t = document.querySelector('#tray');
  const bar = document.querySelector('header.top').getBoundingClientRect().bottom;
  const low = Math.min(document.querySelector('.dock').getBoundingClientRect().top, innerHeight,
    getComputedStyle(t).position === 'fixed' ? t.getBoundingClientRect().top : innerHeight);
  return { top: Math.round(r.top), bottom: Math.round(r.bottom), seen: r.top >= bar - 1 && r.bottom <= low + 1 }; }"""
TO_THIRD = "sel => { const e = document.querySelector(sel); window.scrollBy(0, e.getBoundingClientRect().top - innerHeight / 3); }"
SHELF_SAYS = "() => (document.querySelector('.card-mix [data-shelfmsg]')?.innerText || '').replace(/\\s+/g, ' ').trim()"
# Every build takes 1.5 s longer, as on a slow phone, so a person can act while one runs.
SLOW_BUILDS = """() => { const app = window.robokit, run = app.run.bind(app);
  app.run = (type, ...rest) => type === 'build'
    ? new Promise(r => setTimeout(r, 1500)).then(() => run(type, ...rest)) : run(type, ...rest); }"""


def open_mix(p):
    p.js("robokit.st.adult = true")  # the fund shelf is for adults; the setup screen records it
    p.pg.click("#tray-open")
    p.pg.wait_for_selector(".card-mix")
    p.settled()


def open_shelf(p, row):
    p.js("robokit.st.adult = true")
    p.pg.click("#tray-edit")
    p.pg.wait_for_selector(row)
    p.settled()


def own_weights(p, weights):
    """'Set my own weights' with {ticker: percent} (the others 0), then 'Use these weights'."""
    p.pg.click(".card-mix [data-weights]")
    p.pg.wait_for_selector(".card-mix [data-w]")
    for t in p.js("[...document.querySelectorAll('.card-mix [data-w]')].map(i => i.dataset.w)"):
        p.pg.fill(f'.card-mix [data-w="{t}"]', str(weights.get(t, 0)))
    p.pg.click(".card-mix .weights-box [data-use]")
    p.settled()
    assert p.js("robokit.st.result.mode") == "own_weights"


def switch(p, market):
    p.pg.click(f'[data-market="{market}"]')
    p.pg.wait_for_function("m => robokit.st.market === m", arg=market)
    p.settled()


def toggle(p, t):
    """Remove or Add back the fund class whose row shows `t` in Edit funds (opened if needed)."""
    if not p.js("!!document.querySelector('.card-mix .shelf-box')"):
        p.pg.click(".card-mix [data-shelf]")
        p.pg.wait_for_selector(".card-mix .shelf-box")
    p.pg.click(f'.card-mix .shelf-row[data-cur="{t}"] [data-toggle]')
    p.settled()


def undo_last(p):
    """Tap the newest Undo in the thread."""
    p.pg.locator("#thread [data-undo]").last.click()
    p.settled()


def open_phone_shelf(p):
    """On a phone: Edit funds from the tray, past the age question, with the shelf drawn."""
    p.pg.click("#tray-toggle")
    p.pg.wait_for_function("document.body.classList.contains('tray-open')")
    p.pg.click("#tray-edit")
    p.pg.wait_for_selector(".card-mix .shelf-box")
    if p.pg.is_visible(".card-mix [data-adult2]"):  # 'I am 18 or older'
        p.pg.click(".card-mix [data-adult2]")
    p.pg.wait_for_selector(".card-mix [data-shelfadd]")
    p.settled()
    p.still()


def test_own_weights_stay_with_their_market(page_factory):
    """Own weights stay with their market: one note per double tap, the editor closes on a switch, Undo never fakes a restore."""
    p = page_factory()
    open_mix(p)
    own_weights(p, {"VFV.TO": 60, "ZAG.TO": 40})
    p.pg.dblclick(".card-mix [data-weights]")  # 'Let the model decide'
    p.settled()
    assert len([n for n in p.notes() if n.startswith("The model sets the weights again")]) == 1
    p.pg.click(".card-mix [data-weights]")  # 'Set my own weights' again: the editor is open
    p.pg.wait_for_selector(".card-mix [data-w]")
    switch(p, "US")
    assert p.js("[...document.querySelectorAll('.card-mix [data-w]')].filter(i => !robokit.markets.US.fund(i.dataset.w)).length") == 0
    p.pg.click("#thread [data-undo]")  # Undo on the note made for the Canadian mix
    p.settled()
    undone = "Undone." in p.notes()
    assert p.js("robokit.st.result.mode") != "own_weights"  # the US mix was not touched
    switch(p, "CA")
    assert undone == (p.js("robokit.st.result.mode") == "own_weights")
    assert not [n for n in p.notes() if n.startswith("Something went wrong")]
    assert p.errors == []


def test_removing_the_only_weighted_fund_hands_the_weights_back(page_factory):
    """Removing the only fund with an own weight hands the weights back to the model, says so, and later rebuilds work."""
    p = page_factory()
    open_mix(p)
    own_weights(p, {"VFV.TO": 100})
    p.pg.click(".card-mix [data-shelf]")
    p.pg.click('.card-mix .shelf-row[data-cur="VFV.TO"] [data-toggle]')
    p.settled()
    p.pg.fill("#tray-amount", "20000")
    p.pg.press("#tray-amount", "Tab")
    p.settled()
    notes = p.notes()
    assert not [n for n in notes if n.startswith("Something went wrong")]
    assert any("the model sets the weights again" in n for n in notes)
    assert p.js("robokit.st.result.mode") != "own_weights"
    assert p.errors == []


def test_shelf_remove_and_add_back(page_factory):
    """A double-tapped Remove on the fund shelf removes the class once, and 'Add your own fund' puts the fund back in the mix."""
    p = page_factory()
    open_shelf(p, '.shelf-row[data-cur="VFV.TO"] [data-toggle]')
    p.pg.dblclick('.shelf-row[data-cur="VFV.TO"] [data-toggle]')
    p.settled()
    assert "VFV.TO" in p.js("robokit.st.mix.exclude") and "VFV.TO" not in p.js(WEIGHTS)
    p.pg.fill("[data-shelfadd]", "VFV")
    p.pg.click("[data-shelfaddbtn]")
    p.settled()
    assert "VFV.TO" not in p.js("robokit.st.mix.exclude") and "VFV.TO" in p.js(WEIGHTS)
    assert not [n for n in p.notes() if n.startswith("VFV was added but is not held")]


def test_reset_resets_only_the_market_on_screen(page_factory):
    """Reset to reference resets only the market on screen; the other market keeps its changes, labelled as such and saved."""
    p = page_factory(market="US")
    open_shelf(p, '.shelf-row[data-cur="VOO"] select')
    p.pg.select_option('.shelf-row[data-cur="VOO"] select', "VTI")
    p.settled()
    switch(p, "CA")
    p.pg.click("#tray-reset")
    p.settled()
    switch(p, "US")
    assert "VTI" in p.js(TRAY_FUNDS)
    assert not p.js("document.querySelector('#tray-sub').textContent").startswith("Reference mix")
    p.saved()  # the saved session still holds the US change
    assert "VTI" in p.js("Object.values(JSON.parse(localStorage.getItem('robokit2.state')).mix.swaps)")


def test_reset_to_reference_is_saved(page_factory):
    """After Reset to reference and a reload, nothing brings back the fund changes made before the reset."""
    p = page_factory()
    open_shelf(p, '.shelf-row[data-cur="VFV.TO"] select')
    p.pg.select_option('.shelf-row[data-cur="VFV.TO"] select', "ZSP.TO")
    p.settled()
    p.saved()
    p.pg.click("#tray-reset")
    p.settled()
    assert "ZSP" not in p.js(TRAY_FUNDS)
    p.pg.wait_for_function("""() => { const s = JSON.parse(localStorage.getItem('robokit2.state') || 'null');
      return !s || !Object.keys(s.mix.swaps).length; }""")
    p.reload()
    if p.pg.is_visible(".card-resume [data-resume]"):
        p.pg.click(".card-resume [data-resume]")
        p.pg.wait_for_selector(".card-resume", state="detached")
        p.settled()
    assert "ZSP" not in p.js(TRAY_FUNDS)


def test_the_tray_keeps_what_the_person_is_doing_while_it_rebuilds(page_factory):
    """While the tray rebuilds, a focused fund row keeps focus and a number being typed is kept, with its focus."""
    p = page_factory()
    p.js(SLOW_BUILDS)

    def new_amount(value):
        p.pg.click("#tray-amount")
        p.pg.keyboard.press("Control+A")
        p.pg.keyboard.type(value)
        p.pg.keyboard.press("Tab")  # commits the amount: a rebuild starts; focus moves to 'Each month'
        assert p.focus() == "#tray-monthly"
        assert p.js("document.querySelector('#tray').classList.contains('is-busy')")

    new_amount("25000")
    p.pg.keyboard.press("Tab")  # on to the first fund row while the rebuild runs
    row = p.js("document.activeElement.dataset.t")
    assert row
    p.settled()
    assert p.js("document.activeElement.dataset.t") == row

    new_amount("30000")
    p.pg.keyboard.press("Control+A")
    p.pg.keyboard.type("500")
    p.settled()
    assert p.js("document.querySelector('#tray-monthly').value") == "500"
    assert p.focus() == "#tray-monthly"


def test_tab_out_of_a_changed_monthly_amount_keeps_keyboard_focus(page_factory):
    """Typing a new monthly amount in the tray and pressing Tab moves focus to the next control, not to the page."""
    p = page_factory()
    p.pg.click("#tray-monthly")
    p.pg.keyboard.press("Control+A")
    p.pg.keyboard.type("500")
    p.pg.keyboard.press("Tab")
    p.settled()
    assert p.focus() != "BODY"


def test_the_assistants_buy_plan_is_shown(page_factory):
    """A buy-only plan from the assistant is shown in the mix card, which opens for it if it is not on the page."""
    p = page_factory("mock.html")
    p.send("I have 5000 dollars of new money, how would I split it?")
    p.pending()
    assert p.js("document.querySelectorAll('.card-mix').length") == 0
    out = p.call("plan_contribution", {"new_money": 5000})
    assert out["rows"]
    p.reply("The buy-only split is in the card below. Hypothetical, not an order.")
    shown = p.js("""() => { const t = document.querySelector('.card-mix [data-plan-out] table');
      return !!t && !!t.closest('details[open]') && t.getClientRects().length > 0 ? t.querySelectorAll('tbody tr').length : 0; }""")
    assert shown == len(out["rows"])


def test_the_weights_moved_note_counts_every_move_correctly(page_factory):
    """The note after a fund change names or counts every large weight move, and counts only true small moves as small."""
    p = page_factory()
    open_shelf(p, '.shelf-row[data-cur="VFV.TO"] [data-toggle]')
    before = p.js(WEIGHTS)
    p.pg.click('.shelf-row[data-cur="VFV.TO"] [data-toggle]')
    p.settled()
    after = p.js(WEIGHTS)
    note = next(n for n in p.notes() if n.startswith("Removing VFV"))
    small = [t for t in before if t in after and 0.0005 <= abs(before[t] - after[t]) < 0.005]
    big = [t for t in before if t in after and abs(before[t] - after[t]) >= 0.005]
    m = re.search(r"(\d+) (?:other )?weights? moved by less than half a point", note)
    assert (int(m.group(1)) if m else 0) == len(small), note
    named = [t for t in big if re.search(rf"\b{re.escape(t.split('.')[0])}\b", note)]
    m = re.search(r"(\d+) other weights? moved by half a point or more", note)
    assert len(named) + (int(m.group(1)) if m else 0) == len(big), note


def test_add_buttons_follow_the_mix(page_factory):
    """A search result's Add button says whether the added fund is held, and offers Add again once it is removed."""
    p = page_factory()
    p.js("robokit.st.adult = true")
    p.ask("nasdaq")
    t = p.js("document.querySelector('.card-results [data-add]:not([aria-disabled=true])').dataset.add")
    button = f'.card-results [data-add="{t}"]'
    p.pg.click(button)
    p.settled()
    held = t in p.js(WEIGHTS)
    label = p.pg.text_content(button).strip()
    assert label.startswith("In the mix") if held else label == "Added · not held"
    open_shelf(p, f'.shelf-row[data-sat="{t}"] [data-unsat]')
    p.pg.click(f'.shelf-row[data-sat="{t}"] [data-unsat]')
    p.settled()
    assert p.pg.text_content(button).strip() == "Add"
    assert p.pg.get_attribute(button, "aria-disabled") is None


def test_a_bad_year_with_withdrawals_is_never_shown_as_a_gain(page_factory):
    """When withdrawals take out more than the money, the bad-year figure and its change are never shown as a gain."""
    p = page_factory()
    p.pg.fill("#tray-monthly", "-1000")
    p.pg.press("#tray-monthly", "Tab")
    p.settled()
    open_mix(p)
    lines = p.js("""() => [...document.querySelectorAll('#tray-nums div, .card-mix .keynums div')]
      .map(d => d.innerText.replace(/\\s+/g, ' ')).filter(t => t.startsWith('Bad year'))""")
    found = [re.search(r"\$([\d,]+) CAD \(([\u2212-]?)\u2060?\$([\d,]+) CAD\)", t) for t in lines]
    assert [m for m in found if m], lines
    for m in filter(None, found):
        value, neg, change = int(m.group(1).replace(",", "")), bool(m.group(2)), int(m.group(3).replace(",", ""))
        assert not (value == 0 and not neg and change > 0), m.group(0)


def test_add_back_restores_a_removed_funds_own_weight(page_factory):
    """With own weights, Remove sets the fund's weight aside and Add back restores it, so the mix is again the weights typed."""
    p = page_factory()
    open_mix(p)
    own_weights(p, {"VFV.TO": 60, "ZAG.TO": 40})
    toggle(p, "VFV.TO")  # Remove
    assert p.js(HELD) == {"ZAG.TO": 1.0}
    toggle(p, "VFV.TO")  # Add back
    assert p.js("robokit.st.result.mode") == "own_weights"
    assert p.js(HELD) == {"VFV.TO": 0.6, "ZAG.TO": 0.4}


def test_a_set_aside_weight_never_joins_weights_typed_later(page_factory):
    """Once new own weights are typed, Add back on a fund removed from the earlier ones leaves the typed weights as they are."""
    p = page_factory()
    open_mix(p)
    own_weights(p, {"VFV.TO": 60, "ZAG.TO": 40})
    toggle(p, "VFV.TO")  # Remove: VFV's 60% is set aside
    p.pg.click(".card-mix [data-weights]")  # 'Let the model decide'
    p.settled()
    own_weights(p, {"XIC.TO": 40, "ZAG.TO": 60})
    toggle(p, "VFV.TO")  # Add back
    assert p.js(HELD) == {"XIC.TO": 0.4, "ZAG.TO": 0.6}


def test_an_undo_that_no_longer_applies_changes_nothing(page_factory):
    """An Undo whose mix was replaced (new own weights, a fund removed, a later monthly amount) says so and changes nothing."""
    p = page_factory()
    open_mix(p)
    own_weights(p, {"VFV.TO": 60, "ZAG.TO": 40})
    p.pg.click(".card-mix [data-weights]")  # 'Let the model decide': a note with Undo
    p.settled()
    own_weights(p, {"XIC.TO": 50, "ZAG.TO": 50})
    undo_last(p)
    assert p.js("robokit.st.mix.fixedWeights") == {"XIC.TO": 0.5, "ZAG.TO": 0.5}

    p.pg.click(".card-mix [data-weights]")  # 'Let the model decide' again
    p.settled()
    toggle(p, "XIC.TO")  # Remove a fund the own weights held
    undo_last(p)
    assert p.js("robokit.st.result.mode") != "own_weights"
    p.pg.click('#tray-levels .seg[data-l="4"]')  # later changes still rebuild the mix
    p.settled()
    assert p.js("robokit.st.result.risk.level") == 4

    for monthly in ("-1500", "1500", "300"):  # the flip to adding money posts a note with Undo; 300 is typed after it
        p.pg.fill("#tray-monthly", monthly)
        p.pg.press("#tray-monthly", "Tab")
        p.settled()
    undo_last(p)
    assert p.js("robokit.st.monthly") == 300
    assert len([n for n in p.notes() if n.startswith("Nothing to undo")]) == 3
    assert not [n for n in p.notes() if n.startswith("Something went wrong")]
    assert p.errors == []


def test_editing_funds_leaves_the_page_where_it_was(page_factory):
    """On a phone, swapping or removing a fund in Edit funds leaves the page where it was, with the control just used on screen."""
    p = page_factory(viewport=PHONE)
    open_phone_shelf(p)
    swap, swapped = '.card-mix .shelf-row[data-cur="VFV.TO"] select', '.card-mix .shelf-row[data-cur="ZSP.TO"] select'
    remove = '.card-mix .shelf-row[data-cur="ZAG.TO"] [data-toggle]'
    for used, act, note, after in [
        (swap, lambda: p.pg.select_option(swap, "ZSP.TO"), "Swapping VFV", swapped),
        (remove, lambda: p.pg.click(remove), "Removing ZAG", remove),
    ]:
        p.js(TO_THIRD, used)
        p.still()
        p.pg.focus(used)
        y = p.js("scrollY")
        act()
        p.pg.wait_for_function("t => [...document.querySelectorAll('#thread .turn-note')].some(n => n.textContent.startsWith(t))", arg=note)
        p.settled()
        p.still()
        assert abs(p.js("scrollY") - y) < 50, note
        assert p.js(ON_SCREEN, after)["seen"], note


def test_a_note_made_while_working_in_the_mix_card_leaves_the_page_still(page_factory):
    """'Let the model decide' posts its Undo note without scrolling the page, so the button just pressed stays on screen."""
    for viewport in ({"width": 1280, "height": 900}, PHONE):
        p = page_factory(viewport=viewport)
        if p.pg.is_visible("#tray-toggle"):
            p.pg.click("#tray-toggle")
            p.pg.wait_for_function("document.body.classList.contains('tray-open')")
        open_mix(p)
        p.pg.click(".card-mix [data-weights]")  # 'Set my own weights', kept as the model's numbers
        p.pg.click(".card-mix .weights-box [data-use]")
        p.pg.wait_for_function("robokit.st.result.mode === 'own_weights' && !document.querySelector('.card-mix .weights-box')")
        p.settled()
        button = ".card-mix [data-weights]"
        p.js(TO_THIRD, button)
        p.still()
        p.pg.click(button)  # 'Let the model decide'
        p.pg.wait_for_selector("#thread > .turn-note [data-undo]")
        p.settled()
        p.still()
        assert p.js(ON_SCREEN, button)["seen"], viewport


def test_add_your_own_fund_answers_next_to_the_box(page_factory):
    """'Add your own fund' answers by the box: words are searched, a ticker is added, another market's fund is named, a link wraps."""
    p = page_factory(market="US", viewport=PHONE)
    open_phone_shelf(p)

    def add(text):
        p.js(TO_THIRD, ".card-mix .shelf-add")
        p.still()
        p.js("() => document.querySelectorAll('.card-mix [data-shelfmsg] > *').forEach(n => n.setAttribute('data-old', ''))")
        p.pg.fill(".card-mix [data-shelfadd]", text)
        p.pg.press(".card-mix [data-shelfadd]", "Enter")

    def answer(text):
        add(text)
        p.pg.wait_for_selector(".card-mix [data-shelfmsg] > p:not([data-old])")
        p.settled()
        p.still()
        assert p.js(ON_SCREEN, ".card-mix [data-shelfmsg] > p")["seen"], text
        return p.js(SHELF_SAYS)

    for words in ("high yield", "tech"):  # theme words, not the tickers HIGH and TECH
        said = answer(words)
        assert re.match(r"\d+ funds? match", said) and p.js("document.querySelectorAll('.card-mix [data-shelfmsg] .res-row').length"), said
        assert "other market" not in said and p.js("robokit.st.mix.satellites") == [], words
    assert "other market" in answer("XEQT")  # a Canadian fund, typed on the US page
    add("SCHD")
    p.pg.wait_for_selector('.card-mix .shelf-row[data-sat="SCHD"]')
    assert p.js("robokit.st.mix.satellites") == ["SCHD"]
    assert answer("https://example.com/quote/" + "a" * 160).startswith("No fund matches")
    assert p.js(SIDEWAYS) <= 0
