"""Resolve every URL cited in docs/research/*.md (a deterministic check before anyone relies on a citation)."""

from __future__ import annotations

import concurrent.futures as cf
import datetime
import json
import re
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"}
URL = re.compile(r"https?://[^\s\]>`\"'|,]+")


def _trim(u: str) -> str:
    """Drop trailing punctuation, and a closing parenthesis that belongs to the Markdown, not the URL
    (keeps legal citations such as .../275.206(4)-7 whole)."""
    u = u.rstrip(".;:*")
    while u.endswith(")") and u.count(")") > u.count("("):
        u = u[:-1].rstrip(".;:*")
    return u


def check(u: str):
    try:
        r = requests.get(u, headers=UA, timeout=15, allow_redirects=True, stream=True)
        s = r.status_code
        r.close()
        return u, s
    except Exception as e:  # network error: report its type
        return u, type(e).__name__


def main() -> None:
    urls: dict[str, set] = {}
    for f in sorted((ROOT / "docs" / "research").glob("*.md")):
        for u in URL.findall(f.read_text(encoding="utf-8")):
            urls.setdefault(_trim(u), set()).add(f.name)
    with cf.ThreadPoolExecutor(16) as ex:
        res = dict(ex.map(check, list(urls)))
    bad = {u: s for u, s in res.items() if s != 200}
    print("total", len(res), "ok", len(res) - len(bad), "not-200", len(bad))
    print(Counter(str(s) for s in bad.values()).most_common())
    dead = [{"url": u, "status": s, "cited_in": sorted(urls[u])} for u, s in bad.items() if s in (404, 410)]
    print(json.dumps(dead, indent=1)[:5000])
    (ROOT / "docs" / "research" / "_url_check.json").write_text(
        json.dumps({"checked": datetime.date.today().isoformat(), "status": res}, indent=0)
    )


if __name__ == "__main__":
    main()
