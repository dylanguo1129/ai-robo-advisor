"""The page loads, paints a mix and runs without errors, with and without the AI stand-in."""

import pytest

pytestmark = pytest.mark.ui


def test_page_loads_without_ai(page_factory):
    p = page_factory("index.html")
    assert p.js("window.robokit.ai.available") is False
    assert p.js("document.querySelectorAll('#tray-funds li').length") > 0
    assert p.errors == []


def test_page_loads_with_the_ai_stand_in(page_factory):
    p = page_factory("mock.html")
    p.send("What is an ETF?")
    p.pending()
    p.finish("An ETF is a fund that trades on an exchange like a stock.")
    p.pg.wait_for_function("!document.body.classList.contains('is-streaming')")
    assert p.thread()[:2] == ["msg:What is an ETF?", "turn-ai"]
    assert p.errors == []
