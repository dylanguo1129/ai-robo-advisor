"""Write web/mock.html: web/classic.html (the earlier page) with the dev-only `sample` stand-in (web/dev_mock.js) loaded first.

Used to test the chat path locally, where a test agent plays Claude. The generated page is not
committed or published; re-run this after editing web/classic.html.
"""

from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"

if __name__ == "__main__":
    html = (WEB / "classic.html").read_text(encoding="utf-8")
    marker = '<script type="module">'
    i = html.rindex(marker)
    html = html[:i] + '<script type="module" src="dev_mock.js"></script>\n' + html[i:]
    # the artifact wrapper adds these at publish time; the local copy needs them to behave the same on a phone
    html = '<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' + html
    (WEB / "mock.html").write_text(html, encoding="utf-8")
    print("wrote", WEB / "mock.html")
