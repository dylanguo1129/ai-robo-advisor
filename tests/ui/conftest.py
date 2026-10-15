"""Fixtures for the browser regression tests (marked `ui`; run with `python -m pytest -m ui tests/ui`).

The pages are served from web/ on a free local port, with caching off. The guided page is web/index.html (its tests are
tests/ui/test_guided.py); the earlier page is web/classic.html, which the other test files cover. `/mock.html` is the
classic page with the dev stand-in for the AI (web/dev_mock.js), built in memory the same way scripts/make_mock_page.py
builds it, so nothing is written to disk.
Tests drive a headless Chromium through Playwright: the system Edge or Chrome when present, else Playwright's own
Chromium (`python -m playwright install chromium`). Without Playwright or a browser the tests are skipped.
"""

from __future__ import annotations

import functools
import http.server
import os
import threading
from pathlib import Path

import pytest

# ROBOKIT_UI_WEB serves another copy of web/ (for example an older checkout, to see that a test catches a regression).
WEB = Path(os.environ.get("ROBOKIT_UI_WEB") or Path(__file__).resolve().parents[2] / "web")


def mock_page() -> bytes:
    html = (WEB / "classic.html").read_text(encoding="utf-8")
    marker = '<script type="module">'
    i = html.rindex(marker)
    html = html[:i] + '<script type="module" src="dev_mock.js"></script>\n' + html[i:]
    head = '<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    return (head + html).encode("utf-8")


class Handler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        page = self.path.split("?")[0]
        if page in ("/mock.html", "/index.html", "/classic.html"):
            body = mock_page() if page == "/mock.html" else (WEB / page.lstrip("/")).read_bytes()
            if page != "/mock.html":  # what the artifact wrapper adds at publish time
                body = (
                    b'<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                    + body
                )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def log_message(self, *args):  # keep test output quiet
        pass


@pytest.fixture(scope="session")
def web_dir():
    """The directory the page is served from."""
    return WEB


@pytest.fixture(scope="session")
def base_url():
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(WEB)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/"
    srv.shutdown()


@pytest.fixture(scope="session")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    pw = sync_api.sync_playwright().start()
    b = None
    for kw in ({"channel": "msedge"}, {"channel": "chrome"}, {}):
        try:
            b = pw.chromium.launch(headless=True, **kw)
            break
        except Exception:  # that browser is not installed here; try the next
            continue
    if b is None:
        pw.stop()
        pytest.skip("no Chromium-based browser for Playwright (python -m playwright install chromium)")
    yield b
    b.close()
    pw.stop()


def _before_page(market=None, slow=None):
    """Scripts that run before the page's own code: the saved market, and slow downloads."""
    out = []
    if market:
        out.append(f"try {{ localStorage.setItem('robokit2.market', JSON.stringify('{market}')); }} catch (e) {{}}")
    for name, ms in (slow or {}).items():  # a data file (for example 'us.json') that arrives late, as on a slow connection
        out.append(f"""(() => {{ const f = window.fetch; window.fetch = function (u, ...r) {{
          if (String(u).includes('data/{name}')) return new Promise(res => setTimeout(res, {ms})).then(() => f.call(this, u, ...r));
          return f.call(this, u, ...r); }}; }})();""")
    return out


# One thread entry as 'kind:detail', for order and duplicate checks.
DESCRIBE = """n => n.classList.contains('turn-user') ? 'msg:' + n.textContent.trim()
  : n.classList.contains('card-fund') ? 'fund:' + n.dataset.fund
  : n.classList.contains('card-term') ? 'term:' + n.querySelector('h3').textContent.trim()
  : n.classList.contains('card-compare')
    ? 'compare:' + [...n.querySelectorAll('thead th[scope=col]')].map(t => t.firstChild.textContent.trim()).join('+')
  : n.classList.contains('card-results') ? 'results'
  : n.classList.contains('card-context') ? 'context'
  : n.classList.contains('turn-note') ? 'note:' + n.textContent.trim()
  : (n.className.match(/card-[a-z]+|turn-[a-z]+/) || ['other'])[0]"""

# Where keyboard focus is: 'BODY' when it was dropped to the page.
FOCUS = """() => { const a = document.activeElement;
  if (!a || a === document.body || a === document.documentElement) return 'BODY';
  const d = [...a.attributes].find(x => x.name.startsWith('data-') && x.name !== 'data-live');
  return a.id ? '#' + a.id : a.tagName.toLowerCase() + (d ? `[${d.name}${d.value ? '=' + d.value : ''}]` : ''); }"""


class Page:
    """One fresh browser context (fresh localStorage) on the page, with helpers for waiting and for playing the AI."""

    def __init__(self, browser, base_url, path="classic.html", init=None, market=None, slow=None, **ctx):
        self.path = path
        self.ctx = browser.new_context(**({"viewport": {"width": 1280, "height": 900}} | ctx))
        for script in [*_before_page(market, slow), *([init] if init else [])]:
            self.ctx.add_init_script(script)  # runs before the page (saved market, a slow download, saved state)
        self.pg = self.ctx.new_page()
        self.errors: list[str] = []
        self.pg.on("pageerror", lambda e: self.errors.append(str(e)))
        self.pg.goto(base_url + path)
        self.ready()

    def ready(self):
        """Wait until the page has painted its first mix (and, on mock.html, found the AI stand-in)."""
        self.pg.wait_for_selector("#q", timeout=30000)
        self.pg.wait_for_function("window.robokit && window.robokit.st && window.robokit.st.result", timeout=30000)
        if self.path.startswith("mock.html"):
            self.pg.wait_for_function("window.robokit.ai.available === true", timeout=30000)
        self.idle()

    def reload(self):
        """Reload the page (saved state stays in this context's localStorage)."""
        self.pg.reload()
        self.ready()

    def idle(self):
        """Wait until no rebuild is running (the tray drops its busy state)."""
        self.pg.wait_for_function("!document.querySelector('#tray').classList.contains('is-busy')", timeout=30000)

    def settled(self, timeout=30000):
        """Wait until no rebuild is running or queued, and the notes that follow a rebuild are posted."""
        self.pg.wait_for_function(
            "!window.robokit.buildP && !document.querySelector('#tray').classList.contains('is-busy')", timeout=timeout
        )

    def send(self, text):
        self.pg.fill("#q", text)
        self.pg.press("#q", "Enter")

    def ask(self, text):
        """Send a message and wait until the page has handled it (for the page without the AI)."""
        self.send(text)
        self.pg.evaluate("async () => { await window.robokit.inputs; }")

    def js(self, expr, arg=None):
        return self.pg.evaluate(expr, arg)

    def pending(self, timeout=15000):
        """Wait for the next AI request (the page asking the stand-in for a reply)."""
        self.pg.wait_for_function("!!window.__mock.pending", timeout=timeout)

    def call(self, name, args=None):
        return self.pg.evaluate("([n, a]) => window.__mock.call(n, a)", [name, args or {}])

    def stream(self, text):
        self.pg.evaluate("t => window.__mock.stream(t)", text)

    def finish(self, text):
        self.pg.evaluate("t => window.__mock.finish(t)", text)

    def fail(self, code, message=None, text=None):
        """End the pending AI request with an error; `text` is what had already streamed."""
        self.pg.evaluate(
            """([code, message, text]) => { const p = window.__mock.pending; window.__mock.pending = null;
              if (text) p.opts.onText?.({ text, delta: text });
              const e = { code, message: message || code }; if (text) e.text = text; p.reject(e); }""",
            [code, message, text],
        )

    def replied(self, timeout=15000):
        """Wait until the AI turn has ended (the page leaves its streaming state)."""
        self.pg.wait_for_function("!document.body.classList.contains('is-streaming')", timeout=timeout)

    def reply(self, text):
        """Answer the pending request with `text`; if the page asks for a rewrite, the model sends the same text again."""
        self.finish(text)
        self.pg.wait_for_function("!!window.__mock.pending || !document.body.classList.contains('is-streaming')", timeout=15000)
        if self.js("!!window.__mock.pending"):
            self.finish(text)
        self.replied()

    def thread(self):
        """The thread as a list of 'kind:detail' strings, for order and duplicate checks."""
        return self.pg.evaluate("""() => [...document.querySelectorAll('#thread > section')].map(n =>
            n.classList.contains('turn-user') ? 'msg:' + n.textContent.trim()
            : n.classList.contains('card-fund') ? 'fund:' + n.dataset.fund
            : (n.className.match(/card-[a-z]+|turn-[a-z]+/) || ['other'])[0])""")

    def replies(self):
        """What the page added after the last message the person sent, as 'kind:detail' strings."""
        return self.pg.evaluate(f"""() => {{ const u = [...document.querySelectorAll('#thread > .turn-user')].pop(), out = [];
            for (let n = u ? u.nextElementSibling : null; n; n = n.nextElementSibling) out.push(({DESCRIBE})(n));
            return out; }}""")

    def notes(self):
        return self.pg.evaluate(
            "() => [...document.querySelectorAll('#thread .turn-note')].map(n => n.textContent.replace(/\\s+/g, ' ').trim())"
        )

    def focus(self):
        """Where keyboard focus is ('BODY' when it was dropped to the page)."""
        return self.pg.evaluate(FOCUS)

    def still(self):
        """Wait until the page has stopped scrolling (a smooth scroll has landed)."""
        self.pg.evaluate("""() => new Promise(done => { let last = null, same = 0;
            const tick = () => { const y = scrollY; same = y === last ? same + 1 : 0; last = y;
              if (same >= 8) done(); else requestAnimationFrame(tick); };
            requestAnimationFrame(tick); })""")

    def saved(self):
        """Wait until the session saved in this browser matches the page (saving is debounced)."""
        self.pg.wait_for_function("""() => { const s = JSON.parse(localStorage.getItem('robokit2.state') || 'null'), st = window.robokit.st;
            return !!s && JSON.stringify(s.answers) === JSON.stringify(st.answers) && s.level === st.level && s.amount === st.amount
              && JSON.stringify(s.mix) === JSON.stringify(st.mix) && JSON.stringify(s.mixByMarket) === JSON.stringify(st.mixByMarket)
              && (s.flagsSeen ?? !!st.check.flagsSeen) === !!st.check.flagsSeen && s.checked === (!!st.profile && !st.check.open); }""")

    # ---- the self-check
    def start_check(self, goal="retirement", amount=10000):
        """Open the self-check (the Build chip, or the words where a phone hides the chips) and fill in the setup screen.
        The default amount is the page's own, so the numbers behind the scenario questions are not rebuilt."""
        if self.pg.is_visible('[data-chip="build"]'):
            self.pg.click('[data-chip="build"]')
        else:
            self.send("build a portfolio")
        self.pg.wait_for_selector('.card-check[data-q="setup"]')
        self.pg.click(f'.card-check [data-goal="{goal}"]')
        self.pg.fill(".card-check [data-amount]", str(amount))
        self.pg.click(".card-check [data-go]")
        self.pg.wait_for_function("window.robokit.st.check.step !== 'setup'")

    def answer(self, *pairs):
        """Tap answers on the self-check, one (question, value) pair at a time, waiting for each scenario to be ready."""
        for q, v in pairs:
            self.pg.click(f'.card-check[data-q="{q}"] [data-v="{v}"]:not([disabled])', timeout=60000)
            self.pg.wait_for_function("q => !window.robokit.st.check.open || window.robokit.st.check.step !== q", arg=q)

    def close(self):
        self.ctx.close()


@pytest.fixture
def page_factory(browser, base_url):
    pages = []

    def make(path="classic.html", init=None, *, market=None, slow=None, **ctx):
        """A page on `path`. `market` ('US') is stored as the saved market before every load (reloads included); `slow`
        maps a data file to a download delay in ms. Other keywords are Playwright context options (viewport, color_scheme...)."""
        p = Page(browser, base_url, path, init, market, slow, **ctx)
        pages.append(p)
        return p

    yield make
    for p in pages:
        p.close()
