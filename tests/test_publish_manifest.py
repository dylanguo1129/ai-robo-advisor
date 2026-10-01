"""The list of files published as the web page (web/publish.json) matches what the page loads.

A teammate publishes their own copy from this list (.claude/skills/publish-robo-kit), so a module added to web/
without being listed would break every new copy."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("check_publish", ROOT / "scripts" / "check_publish.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def test_the_publish_list_matches_the_page():
    assert check.problems() == []


def test_a_missing_module_is_caught():
    m = check.manifest()
    m["files"] = [f for f in m["files"] if f != "parse.js"]
    assert any("parse.js, which is not listed" in p for p in check.problems(m))


def test_test_and_dev_files_are_refused():
    m = check.manifest()
    m["files"] = [*m["files"], "dev_mock.js", "test_parse.mjs"]
    found = check.problems(m)
    assert any("dev_mock.js is a test or dev file" in p for p in found)
    assert any("test_parse.mjs is a test or dev file" in p for p in found)


def test_capabilities_follow_the_code():
    m = check.manifest()
    m["capabilities"] = {}
    assert any("capabilities declared" in p for p in check.problems(m))


def test_settings_point_at_the_repository_files():
    s = check.settings()
    assert s["file_path"] == "web/index.html"
    assert all(src == f"web/{dst}" and (ROOT / src).is_file() for dst, src in s["files"].items())
    assert s["capabilities"] == {"sample": {}}


def test_data_values_must_be_plain_text():
    assert not check.suspicious("Vanguard FTSE Canada All Cap Index ETF")
    assert not check.suspicious("S&P 500 > 5% drop; bonds < cash")
    assert check.suspicious("<img src=x onerror=alert(1)>")
    assert check.suspicious("javascript:alert(1)")
    assert check.suspicious("ETF\u202eFTE")  # a right-to-left override
    assert check.suspicious("tab\x07bell")
