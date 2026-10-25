"""The replication kit (scripts/replicate.py, data/replication/, REPRODUCE.md): the archived data is intact, and the
engine reproduces the optimizer tables exactly as our reports print them."""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("replicate", ROOT / "scripts" / "replicate.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)


def test_archive_matches_its_manifest():
    m = json.loads(R.MANIFEST.read_text(encoding="utf-8"))
    files = R.archive_files()  # exits on any hash mismatch
    assert set(files) == set(m["files"])
    assert m["data_snapshot"] == R.SNAPSHOT


def test_the_engine_reproduces_the_reports_tables(capsys):
    from robokit import engine as E

    want = json.loads((R.REPL / "report_tables.json").read_text(encoding="utf-8"))
    got = R.build_tables()
    slack = R.WEIGHT_SLACK if E.data_source() == "snapshot" else 0.0
    assert R.check_tables(got, want, f"tables ({E.data_source()})", slack), capsys.readouterr().out


def test_a_jump_cases_lambda_is_not_compared_but_its_mix_is():
    """On Linux the snapshot rebuild gave reference case 12 (min 20%, max 30% per fund; outcome 'jump') lambda 1.2456
    against the committed 1.6878: the same weights and volatility, a different point on the same side of the jump."""
    core = json.loads((ROOT / "web" / "data" / "core.json").read_text(encoding="utf-8"))
    a, b = json.loads(json.dumps(core)), json.loads(json.dumps(core))
    a["reference_cases"][12]["lambda"] = 1.2456
    a["reference_cases"][12]["calibration"]["evaluations"] += 1
    jumps = R.drop_jump_lambdas(a, b)
    assert jumps == {"n": 3, "narrow": True}
    assert not R.compare(a, b)["mismatches"]
    a["reference_cases"][12]["weights"]["CASH.TO"] = 0.2  # a different mix still fails
    assert R.compare(a, b)["mismatches"]
