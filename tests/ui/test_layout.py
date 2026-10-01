"""Layout and accessibility: phone widths and large text, long words, the sticky bars, keyboard focus, contrast and
what screen readers hear."""

import pytest

pytestmark = pytest.mark.ui

PHONE = {"width": 375, "height": 812}
TABLET = {"width": 768, "height": 1024}
SIDEWAYS = "() => document.documentElement.scrollWidth - document.documentElement.clientWidth"
# Words or numbers inside `root` that a line break splits ('0.2' and '8%' on two lines).
SPLIT_WORDS = r"""([root, inCells]) => { const out = []; for (const box of document.querySelectorAll(root)) {
  const w = document.createTreeWalker(box, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) {
    const t = w.currentNode, s = t.nodeValue; if (inCells && !t.parentElement.closest('td')) continue;
    const re = /[^\s\-\/,:·]+/g; let m;
    while ((m = re.exec(s))) {
      if (m[0].length < 2) continue;
      const r = document.createRange(); r.setStart(t, m.index); r.setEnd(t, m.index + m[0].length);
      if (new Set([...r.getClientRects()].filter(x => x.width > 0.5).map(x => Math.round(x.top))).size > 1) out.push(m[0]); } } }
  return out; }"""
# How much of an element is hidden behind the sticky composer (and, on narrow screens, the docked tray bar).
BEHIND_DOCK = """el => { const r = el.getBoundingClientRect(), d = document.querySelector('.dock').getBoundingClientRect();
  const tray = document.querySelector('#tray');
  const trayTop = getComputedStyle(tray).position === 'fixed' ? tray.getBoundingClientRect().top : innerHeight;
  return Math.max(0, Math.round(r.bottom - Math.min(d.top, trayTop, innerHeight))); }"""
# WCAG contrast of each element's text against what is painted behind it (backgrounds and opacity included).
CONTRAST = r"""(sel) => {
  const parse = (c) => { const p = c.match(/rgba?\(([^)]+)\)/)[1].split(/[ ,\/]+/).filter(Boolean).map(Number);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const lum = ({ r, g, b }) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b); };
  const blend = (t, u) => ({ r: t.r * t.a + u.r * (1 - t.a), g: t.g * t.a + u.g * (1 - t.a), b: t.b * t.a + u.b * (1 - t.a), a: 1 });
  const out = []; for (const el of document.querySelectorAll(sel)) { if (!el.getBoundingClientRect().width) continue;
    const stack = [];
    for (let e = el; e; e = e.parentElement) {
      const c = parse(getComputedStyle(e).backgroundColor); if (c.a > 0) { stack.push(c); if (c.a >= 1) break; } }
    let bg = parse(getComputedStyle(document.body).backgroundColor); for (let i = stack.length - 1; i >= 0; i--) bg = blend(stack[i], bg);
    let op = 1; for (let e = el; e; e = e.parentElement) op *= Number(getComputedStyle(e).opacity);
    const c = parse(getComputedStyle(el).color), fg = blend({ ...c, a: c.a * op }, bg), a = lum(fg), b = lum(bg);
    out.push([el.textContent.trim(), Math.round((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) * 100) / 100]); }
  return out; }"""
# Everything written to the live regions from now on.
RECORD_LIVE = r"""() => { window.__said = []; const log = (t) => { t = (t || '').trim(); if (t) window.__said.push(t); };
  const watch = (r) => new MutationObserver(() => log(r.textContent)).observe(r, { childList: true, characterData: true, subtree: true });
  watch(document.querySelector('#announcer'));
  const seen = new WeakSet(), regions = '[aria-live]:not(#announcer):not([aria-live=off]), [role=status], [role=alert]';
  const hook = () => document.querySelectorAll(regions).forEach(r => {
    if (!seen.has(r)) { seen.add(r); log(r.textContent); watch(r); } });
  hook(); new MutationObserver(hook).observe(document.body, { childList: true, subtree: true }); }"""
SLOW_BUILDS = """() => { const app = window.robokit, run = app.run.bind(app);
  app.run = (type, ...rest) => type === 'build'
    ? new Promise(r => setTimeout(r, 1500)).then(() => run(type, ...rest)) : run(type, ...rest); }"""
LANDSCAPE = {"width": 812, "height": 375}
# Wait until the page, the phone tray's slide and the measured composer cover have all come to rest.
AT_REST = """() => new Promise(done => { let last = null, same = 0;
  const tick = () => { const k = [scrollY, document.querySelector('#tray').getBoundingClientRect().top,
      getComputedStyle(document.documentElement).getPropertyValue('--dock-cover')].join(':');
    same = k === last ? same + 1 : 0; last = k; if (same >= 10) done(); else requestAnimationFrame(tick); };
  requestAnimationFrame(tick); })"""
# The focused control, the phone tray (its top and its bar) and the composer, in pixels from the top of the screen.
DOCKED = """() => { const a = document.activeElement.getBoundingClientRect(), t = document.querySelector('#tray').getBoundingClientRect();
  const d = document.querySelector('.dock').getBoundingClientRect();
  return { focusBottom: Math.round(a.bottom), trayTop: Math.round(t.top), bar: Math.round(innerHeight - t.top),
    toggle: Math.round(document.querySelector('#tray-toggle').getBoundingClientRect().height), dockBottom: Math.round(d.bottom),
    cover: parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--dock-cover')),
    covered: Math.round(innerHeight - Math.min(d.top, t.top)) }; }"""


def largest_text(p):
    p.pg.click("#textsize")
    p.pg.click("#textsize")
    assert p.pg.text_content("#textsize") == "A++"


def test_a_phone_with_the_largest_text_never_scrolls_sideways(page_factory):
    """At A++ on a 375px phone the message box, Assistant popover, mix card and self-check result all fit the screen width."""
    p = page_factory(viewport=PHONE)
    p.pg.click("#q")
    p.pg.keyboard.type("Compare XEQT and VEQT for a twenty year horizon and tell me which one has lower fees")
    largest_text(p)
    box = p.js("""() => { const q = document.querySelector('#q');
      return { fits: q.scrollHeight <= q.clientHeight + 1, scrolls: getComputedStyle(q).overflowY }; }""")
    assert box["fits"] or box["scrolls"] in ("auto", "scroll")
    p.pg.click("#settings-btn")
    r = p.js("""() => { const r = document.querySelector('#settings').getBoundingClientRect();
      return [r.left, r.right, document.documentElement.clientWidth]; }""")
    assert r[0] >= 0 and r[1] <= r[2]
    p.pg.keyboard.press("Escape")
    p.pg.fill("#q", "")

    p.pg.click("#tray-toggle")
    p.pg.click("#tray-open")  # 'Show the full mix'
    p.pg.wait_for_selector(".card-mix .st-row")
    p.settled()
    assert p.js(SIDEWAYS) <= 0
    past_edge = p.js("""() => { const c = document.querySelector('.card-mix');
      const right = c.getBoundingClientRect().right - parseFloat(getComputedStyle(c).borderRightWidth);
      return Math.max(0, ...[...c.children].map(x => x.getBoundingClientRect().right - right)); }""")
    assert past_edge <= 1
    assert p.js(SPLIT_WORDS, [".card-mix .st-row > span:first-child", False]) == []  # crisis names keep whole words

    p.start_check("wealth", 10000)
    p.answer(
        ("A2", "yes"),
        ("A3", "no"),
        ("B1", "5to9"),
        ("B4", "10to25"),
        ("B5", "very"),
        ("C1", "4"),
        ("C2", "wait"),
        ("C3", "4"),
        ("C4", "both"),
    )
    p.pg.wait_for_selector(".card-check[data-q=result] .ladder[aria-busy=false]")
    assert p.js(SIDEWAYS) <= 0


def test_tables_and_amounts_keep_their_words_whole_on_a_phone(page_factory):
    """On a phone, comparison tables keep fees, sizes and names whole, and a minus sign stays on the line of its amount."""
    p = page_factory(viewport=PHONE)
    p.ask("XEQT VEQT ZEB XIC VFV")
    p.pg.wait_for_selector(".card-compare table")
    assert p.js(SPLIT_WORDS, [".card-compare", True]) == []
    largest_text(p)
    p.pg.click("#tray-toggle")
    p.pg.wait_for_function("document.body.classList.contains('tray-open')")
    assert "−" in p.pg.text_content("#tray-nums")  # the bad-year change is a loss
    split = p.js(r"""() => { const out = [], w = document.createTreeWalker(document.querySelector('#tray-nums'), NodeFilter.SHOW_TEXT);
      while (w.nextNode()) { const t = w.currentNode, s = t.nodeValue; let m; const re = /−/g;
        while ((m = re.exec(s))) { const a = document.createRange(); a.setStart(t, m.index); a.setEnd(t, m.index + 1);
          const b = document.createRange(); const j = s.indexOf('$', m.index); if (j < 0) continue; b.setStart(t, j); b.setEnd(t, j + 1);
          if (Math.abs(a.getBoundingClientRect().top - b.getBoundingClientRect().top) > 4) out.push(s.trim()); } }
      return out; }""")
    assert split == []


def test_long_links_wrap_on_a_phone(page_factory):
    """A long unbroken link in a message or an assistant reply wraps inside its bubble; the page never scrolls sideways."""
    link = "https://finance.example.com/quote/XEQT.TO/?guccounter=1&guce_referrer=" + "a" * 240
    p = page_factory(viewport=PHONE)
    p.ask(link)
    assert p.js(SIDEWAYS) <= 0
    assert p.js("document.querySelector('.turn-user').getBoundingClientRect().right <= document.documentElement.clientWidth")
    ai = page_factory("mock.html", viewport=PHONE)
    ai.send("hello")
    ai.pending()
    ai.reply("I am an AI. See " + link)
    assert ai.js(SIDEWAYS) <= 0


def test_new_content_is_never_hidden_behind_the_composer(page_factory):
    """New answer cards, and an assistant reply on a phone, end up fully above the sticky composer."""
    for viewport in (TABLET, {"width": 1280, "height": 900}):
        p = page_factory(viewport=viewport)
        for text in ["XEQT VEQT", "what is volatility", "what is an etf?", "what is a bond?", "what is rebalancing"]:
            p.ask(text)
        p.still()
        assert p.pg.eval_on_selector("#thread > section:last-child", BEHIND_DOCK) <= 2, viewport

    p = page_factory("mock.html", viewport=PHONE)
    p.pg.click('[data-chip="etf"]')
    for t in ["VFV", "ZEB"]:  # a lone ticker opens its card without the assistant
        p.ask(t)
    reply = "Fees are charged as a yearly share of what you hold. The card in the tray shows them in dollars for the mix you have now."
    p.send("How do fees work?")
    p.pending()
    p.still()  # a real reply starts streaming after the page has scrolled to the new bubble
    p.stream(reply)
    p.reply(reply)
    p.still()
    assert p.js(f"(() => ({BEHIND_DOCK})([...document.querySelectorAll('.turn-ai')].pop().querySelector('.ai-text')))()") <= 2


def test_phone_taps_and_questions_land_on_screen(page_factory):
    """On a phone a tray fund tap shows its card (the tray closes); in landscape each new question's heading is on screen."""
    p = page_factory(viewport=PHONE)
    p.pg.click("#tray-toggle")
    p.pg.wait_for_function("document.body.classList.contains('tray-open')")
    t = p.pg.locator("#tray-funds button").first.get_attribute("data-t")
    p.pg.click(f'#tray-funds button[data-t="{t}"]')
    p.pg.wait_for_selector(f'.card-fund[data-fund="{t}"]')
    p.still()
    seen = p.js(
        """t => { const c = document.querySelector(`.card-fund[data-fund='${t}']`), r = c.getBoundingClientRect();
      const y = Math.max(r.top + 10, 70), h = y < innerHeight ? document.elementFromPoint(r.left + r.width / 2, y) : null;
      return { visible: !!h && c.contains(h), trayOpen: document.body.classList.contains('tray-open') }; }""",
        t,
    )
    assert seen == {"visible": True, "trayOpen": False}

    land = page_factory(viewport={"width": 812, "height": 375})
    land.start_check("wealth", 25000)
    land.pg.focus('.card-check[data-q=A2] [data-v="yes"]')
    land.pg.keyboard.press("Enter")
    land.pg.wait_for_function("robokit.st.check.step === 'A3'")
    land.still()
    top, bar = land.js("""[document.querySelector('.card-check h3').getBoundingClientRect().top,
      Math.max(0, document.querySelector('header.top').getBoundingClientRect().bottom)]""")
    assert top >= bar - 1


def test_keyboard_focus_stays_on_a_control_in_the_chat(page_factory):
    """Keyboard focus stays on a control after Send, Stop, Add and Undo; it is never dropped to the page."""
    ai = page_factory("mock.html")
    ai.pg.fill("#q", "What does volatility mean for my mix?")
    ai.pg.focus("#send")
    ai.pg.keyboard.press("Enter")
    ai.pending()
    assert ai.focus() != "BODY"
    ai.pg.focus("#stop")
    ai.pg.keyboard.press("Enter")
    ai.replied()
    assert ai.focus() != "BODY"

    p = page_factory()
    p.ask("vanguard")
    p.pg.focus(".card-results [data-add]:not([aria-disabled=true])")
    p.pg.keyboard.press("Enter")
    assert p.focus() != "BODY"
    p.settled()
    p.ask("ZEB")
    p.pg.focus('.card-fund[data-fund="ZEB.TO"] [data-add]')
    p.pg.keyboard.press("Enter")
    assert p.focus() != "BODY"
    p.settled()
    for monthly in ("-500", "500"):  # a withdrawal that flips to an addition posts a note with Undo
        p.pg.fill("#tray-monthly", monthly)
        p.pg.press("#tray-monthly", "Tab")
        p.settled()
    p.pg.focus("[data-undo]")
    p.pg.keyboard.press("Enter")
    assert p.focus() != "BODY"


def test_keyboard_focus_stays_on_a_control_in_the_self_check(page_factory):
    """Keyboard focus stays on a control after 'Continue later' and after the resume card's 'Start over'."""
    p = page_factory()
    p.start_check("retirement", 10000)
    p.answer(("A2", "yes"))
    p.pg.focus(".card-check [data-later]")
    p.pg.keyboard.press("Enter")
    p.pg.wait_for_selector(".card-summary")
    assert p.js("!!document.activeElement.closest('.card-check')")
    p.saved()
    p.reload()
    p.pg.focus(".card-resume [data-fresh]")
    p.pg.keyboard.press("Enter")
    p.pg.wait_for_selector(".card-resume", state="detached")
    assert p.focus() != "BODY"


def test_the_bars_never_hide_the_page_or_the_focused_control(page_factory):
    """The top bar stays on screen at any scroll, and Tab or Shift+Tab never leaves focus under the top bar or the composer."""
    for viewport in (TABLET, {"width": 1280, "height": 900}):
        p = page_factory(viewport=viewport)
        for text in ["XEQT VEQT ZEB", "covered call etf", "what is volatility", "QQQ"]:
            p.ask(text)
        p.still()
        p.js("window.scrollTo(0, 0)")
        p.pg.focus("#settings-btn")
        covered = []
        for _ in range(80):
            p.pg.keyboard.press("Tab")
            r = p.js("""() => { const a = document.activeElement; if (!a || a === document.body) return null;
              if (a.closest('.dock') || a.closest('#tray') || a.closest('header.top')) return { outside: true, id: a.id };
              const r = a.getBoundingClientRect(), h = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
              return { outside: false, covered: !h || (!a.contains(h) && !h.contains(a)),
                       text: (a.textContent || '').trim().slice(0, 24) }; }""")
            if r and r["outside"] and r["id"] == "q":
                break
            if r and not r["outside"] and r["covered"]:
                covered.append(r["text"])
        assert covered == [], viewport

    p.js("""() => { const rows = [...document.querySelectorAll('.card-results .res-main')].filter(e => e.offsetParent);
      window.scrollTo(0, scrollY + rows[1].getBoundingClientRect().top + 5); rows[2].focus({ preventScroll: true }); }""")
    p.pg.keyboard.press("Shift+Tab")  # back onto a control just above the screen
    p.still()
    r = p.js("""() => { const a = document.activeElement, r = a.getBoundingClientRect();
      const h = document.querySelector('header.top').getBoundingClientRect();
      const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
      return { top: r.top, bar: h.bottom, under: !!hit?.closest('header.top') }; }""")
    assert not r["under"] and r["top"] >= r["bar"] - 1

    p.pg.click("#tray-open")  # a long card
    p.pg.wait_for_selector(".card-mix .st-row")
    p.settled()
    for y in (400, 1200, 2000):
        p.js(f"window.scrollTo(0, {y})")
        assert p.js("Math.round(scrollY)") > 0
        assert p.js("Math.round(document.querySelector('header.top').getBoundingClientRect().top)") >= 0, y


def test_small_text_meets_aa_contrast(page_factory):
    """The unselected currency label (light) and the selected and locked level-row labels (dark) reach 4.5:1 contrast."""
    light = page_factory(color_scheme="light")
    light.pg.mouse.move(1, 899)
    labels = light.js(CONTRAST, ".mkt button[aria-pressed=false] span")
    assert labels and all(r >= 4.5 for _, r in labels), labels

    dark = page_factory(color_scheme="dark")
    dark.start_check("wealth", 10000)
    dark.answer(
        ("A2", "no"),
        ("A3", "lot"),
        ("B1", "5to9"),
        ("B4", "10to25"),
        ("B5", "very"),
        ("C1", "4"),
        ("C2", "wait"),
        ("C3", "4"),
        ("C4", "both"),
    )
    dark.pg.wait_for_selector(".card-check[data-q=result] .ladder[aria-busy=false]")
    dark.pg.mouse.move(1, 1)  # no hover on a row
    rows = dark.js(
        CONTRAST,
        ".card-check .lad-row.is-on .lad-num small, .card-check .lad-row.is-on .lad-name > b, "
        ".card-check .lad-row.is-locked .lad-num small, .card-check .lad-row.is-locked .lad-name > b",
    )
    assert dark.js("document.querySelectorAll('.card-check .lad-row.is-locked').length") and rows
    assert [x for x in rows if x[1] < 4.5] == []


def test_screen_readers_hear_what_changed(page_factory):
    """Screen readers hear each new card and the 'not from a tool' warning, and hear an Undo result once, not twice."""
    p = page_factory()
    p.js(RECORD_LIVE)
    steps = [
        ("ticker", lambda: p.ask("ZEB")),
        ("term question", lambda: p.ask("what is a bond?")),
        ("two tickers", lambda: p.ask("XEQT VEQT")),
        ("ETF chip", lambda: p.pg.click('[data-chip="etf"]')),
        ("markets chip", lambda: p.pg.click('[data-chip="market"]')),
    ]
    for label, step in steps:
        n = p.js("document.querySelectorAll('#thread > section.card').length")
        p.js("window.__said = []")
        step()
        p.pg.wait_for_function("n => document.querySelectorAll('#thread > section.card').length > n", arg=n)
        try:
            p.pg.wait_for_function(
                """n => window.__said.length > 0
              || [...document.querySelectorAll('#thread > section.card')].slice(n).some(c => c.contains(document.activeElement))""",
                arg=n,
                timeout=3000,
            )
        except Exception:
            pytest.fail(f"{label}: the new card was neither announced nor given focus")

    for monthly in ("-100", "100"):
        p.pg.fill("#tray-monthly", monthly)
        p.pg.press("#tray-monthly", "Tab")
        p.settled()
    p.js("window.__said = []")
    p.pg.focus("[data-undo]")
    p.pg.keyboard.press("Enter")
    p.settled()
    p.pg.wait_for_function("document.activeElement !== document.body")
    focused = p.js("document.activeElement.textContent.trim()")
    if p.js("document.activeElement.tagName") == "P":  # the note took focus, so it is read on focus
        p.pg.wait_for_function("!window.robokit.annPending")  # any announcement has been written to the live region
        assert not [s for s in p.js("window.__said") if focused and focused in s]

    ai = page_factory("mock.html")
    ai.js(RECORD_LIVE)
    ai.send("what is the fee of VFV?")
    ai.pending()
    ai.call("etf_profile", {"ticker": "VFV"})
    ai.reply("VFV charges 0.09% a year. Last year it returned 77.7%.")
    assert "77.7" in ai.js("[...document.querySelectorAll('.turn-ai')].pop().querySelector('.ai-foot').textContent")
    ai.pg.wait_for_function("window.__said.some(s => s.includes('77.7') || /not from a tool/i.test(s))")


def test_the_desktop_tray_fits_the_window_at_the_largest_text(page_factory):
    """At A++ on a desktop the tray ends at the bottom of the window, so its last button is reached by scrolling the tray."""
    p = page_factory()
    largest_text(p)
    tray = "() => [Math.round(document.querySelector('#tray').getBoundingClientRect().bottom), innerHeight]"
    bottom, height = p.js(tray)
    assert bottom <= height + 1  # on the first view
    p.pg.click("#tray-open")  # a long thread to read
    p.pg.wait_for_selector(".card-mix .st-row")
    p.settled()
    p.js("""() => { window.scrollTo(0, (document.documentElement.scrollHeight - innerHeight) / 2);
      document.querySelector('#tray').scrollTop = 1e6; }""")  # reading mid-thread, the tray scrolled to its end
    p.still()
    bottom, height = p.js(tray)
    assert bottom <= height + 1
    assert p.js("document.querySelector('#tray-reset').getBoundingClientRect().bottom") <= height


def test_the_phone_tray_bar_in_landscape_covers_only_itself(page_factory):
    """In phone landscape the closed tray shows only its bar, focus never hides behind it, and the composer cover is measured at rest."""
    p = page_factory(viewport=LANDSCAPE)

    def tab_to(test):
        p.js("() => { document.activeElement.blur(); window.scrollTo(0, 0); }")
        p.pg.evaluate(AT_REST)
        for _ in range(30):
            p.pg.keyboard.press("Tab")
            if p.js(test):
                p.pg.evaluate(AT_REST)
                return p.js(DOCKED)
        pytest.fail(f"Tab never reached {test}")

    r = tab_to("document.activeElement.dataset.chip === 'build'")  # the first view's suggestion chips
    assert r["focusBottom"] <= r["trayTop"] + 1, r
    largest_text(p)
    r = tab_to("document.activeElement.id === 'q'")
    assert r["focusBottom"] <= r["trayTop"] + 1, r
    for text in ["XEQT VEQT", "what is volatility", "ZEB"]:
        p.ask(text)
    p.js("window.scrollTo(0, 200)")
    p.pg.evaluate(AT_REST)
    r = p.js(DOCKED)
    assert abs(r["bar"] - r["toggle"]) <= 2 and r["dockBottom"] <= r["trayTop"] + 1, r
    for _ in range(2):  # open the tray and close it again
        p.pg.click("#tray-toggle")
        p.pg.evaluate(AT_REST)
    assert not p.js("document.body.classList.contains('tray-open')")
    r = p.js(DOCKED)
    assert abs(r["cover"] - r["covered"]) <= 2, r


def test_page_text_does_not_depend_on_the_servers_character_set(web_dir):
    """web/index.html is plain ASCII or names UTF-8, so its text reads the same whatever character set a server declares."""
    raw = (web_dir / "index.html").read_bytes()
    assert raw.isascii() or b'charset="utf-8"' in raw.lower() or b"charset=utf-8" in raw.lower()
