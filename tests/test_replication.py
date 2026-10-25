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
