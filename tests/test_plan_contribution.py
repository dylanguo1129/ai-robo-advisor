"""Buy-only contribution plan: rules, and the browser engine agrees with the Python engine."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from robokit.engine import plan_contribution

HOLD = [
    {"ticker": "VFV.TO", "symbol": "VFV", "weight": 0.5, "price": 150.0},
    {"ticker": "XIC.TO", "symbol": "XIC", "weight": 0.3, "price": 40.0},
    {"ticker": "ZAG.TO", "symbol": "ZAG", "weight": 0.2, "price": 14.0},
]


def test_nothing_held_splits_by_weight():
    r = plan_contribution(HOLD, 1000)
    assert [x["buy"] for x in r["rows"]] == [500.0, 300.0, 200.0]
    assert [x["units"] for x in r["rows"]] == [3, 7, 14]
    assert r["drift_before"] is None and r["gap_closed"]


def test_short_money_goes_to_the_gaps_and_never_sells():
    r = plan_contribution(HOLD, 1000, {"VFV.TO": 9000, "XIC.TO": 500, "ZAG.TO": 500})
    buys = {x["ticker"]: x["buy"] for x in r["rows"]}
    assert buys["VFV.TO"] == 0 and all(v >= 0 for v in buys.values())
    assert abs(sum(buys.values()) - 1000) < 0.02
    assert not r["gap_closed"] and r["drift_after"] < r["drift_before"]


def test_enough_money_closes_every_gap_then_follows_the_mix():
    r = plan_contribution(HOLD, 10000, {"VFV.TO": 3000, "XIC.TO": 1000, "ZAG.TO": 1000})
    assert r["gap_closed"] and r["drift_after"] < 1e-9
    assert abs(sum(x["buy"] for x in r["rows"]) - 10000) < 0.02


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_browser_engine_matches():
    cases = [
        (1000, {}),
        (1000, {"VFV.TO": 9000, "XIC.TO": 500, "ZAG.TO": 500}),
        (10000, {"VFV.TO": 3000, "XIC.TO": 1000, "ZAG.TO": 1000}),
        (250, {"ZAG.TO": 800}),
    ]
    web = (Path(__file__).resolve().parents[1] / "web" / "robokit.js").as_uri()
    script = (
        f"import {{ planContribution }} from '{web}';\n"
        f"const H = {json.dumps(HOLD)}; const C = {json.dumps(cases)};\n"
        "console.log(JSON.stringify(C.map(([m, c]) => planContribution(H, m, c))));"
    )
    out = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True, check=True).stdout
    js = json.loads(out)
    for (money, cur), j in zip(cases, js):
        p = plan_contribution(HOLD, money, cur)
        for a, b in zip(p["rows"], j["rows"]):
            assert a["buy"] == pytest.approx(b["buy"], abs=0.011) and a["units"] == b["units"]
        assert p["gap_closed"] == j["gap_closed"]
        assert (p["drift_before"] is None) == (j["drift_before"] is None)
        assert p["drift_after"] == pytest.approx(j["drift_after"], abs=1e-4)
