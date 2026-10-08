"""After the registered run, the shipped constants must equal the defaults it locked (RESEARCH_LOG section 10, Order):
the QIS switch, resampling on or off, and the projection path count, in both engines. Before the run there is
nothing to compare, and the test says so."""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "output" / "v3" / "results.json"


@pytest.mark.skipif(not RESULTS.exists(), reason="the registered evaluation has not been run")
def test_shipped_constants_equal_the_locked_defaults():
    from optimizer.estimators import QIS_SWITCH
    from robokit.engine import Request
    from robokit.projection import project

    locked = json.loads(RESULTS.read_text(encoding="utf-8"))["locked_defaults"]
    js_engine = (ROOT / "web" / "engine.js").read_text(encoding="utf-8")
    js_kit = (ROOT / "web" / "robokit.js").read_text(encoding="utf-8")
    assert QIS_SWITCH == locked["qis_switch"]
    assert float(re.search(r"conc > ([0-9.]+) \? 'qis'", js_engine).group(1)) == locked["qis_switch"]
    assert Request(market="CA").resample is locked["resample"]
    assert re.search(r"views: \[\], resample: (true|false),", js_kit).group(1) == ("true" if locked["resample"] else "false")
    assert inspect.signature(project).parameters["n_paths"].default == locked["projection_paths"]
    assert int(re.search(r"nPaths = (\d+)", js_kit).group(1)) == locked["projection_paths"]


def test_the_patterns_find_todays_constants():
    """The check above reads the browser engine's source: make sure its patterns still match."""
    js_engine = (ROOT / "web" / "engine.js").read_text(encoding="utf-8")
    js_kit = (ROOT / "web" / "robokit.js").read_text(encoding="utf-8")
    assert re.search(r"conc > ([0-9.]+) \? 'qis'", js_engine) and re.search(r"views: \[\], resample: (true|false),", js_kit)
    assert re.search(r"nPaths = (\d+)", js_kit)
