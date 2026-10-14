"""3.0.4: the data checked against independent sources (docs/research/v304_data_verification.md).

The reference funds' MERs come from the issuers' own pages (data/issuer_mer.csv, each row with its URL, quote and
as-of date); the screener's figure can lag an issuer's new fiscal year by a few basis points."""

from __future__ import annotations

import pandas as pd

from robokit import universe
from tests.test_v2 import needs_data

DEFAULTS = ("XIC.TO", "VFV.TO", "FLUR.NE", "VEE.TO", "ZAG.TO", "XSB.TO", "VBU.NE", "XRE.TO", "VALT.TO", "CASH.TO")


def test_the_issuer_file_covers_every_default_fund_with_a_source():
    M = pd.read_csv(universe.ISSUER_MER)
    assert set(DEFAULTS) <= set(M.yahoo)
    assert M.yahoo.is_unique and M.mer.between(0, 0.1).all()
    assert M.url.str.startswith("https://").all() and M.quote.str.len().gt(5).all()


def test_an_issuer_mer_replaces_the_screener_figure(tmp_path):
    p = tmp_path / "issuer_mer.csv"
    pd.DataFrame({"yahoo": ["A.TO"], "mer": [0.0008], "label": ["MER"], "as_of": ["2026-06-30"]}).to_csv(p, index=False)
    U = pd.DataFrame({"yahoo": ["A.TO", "B.TO"], "mer": [0.0009, 0.002], "why": ["", ""]})
    out = universe.apply_issuer_mer(U, p).set_index("yahoo")
    assert out.at["A.TO", "mer"] == 0.0008 and "MER from the issuer (MER, 2026-06-30)" in out.at["A.TO", "why"]
    assert out.at["B.TO", "mer"] == 0.002 and out.at["B.TO", "why"] == ""


def test_without_the_issuer_file_the_universe_is_unchanged(tmp_path):
    U = pd.DataFrame({"yahoo": ["A.TO"], "mer": [0.0009], "why": [""]})
    pd.testing.assert_frame_equal(universe.apply_issuer_mer(U, tmp_path / "none.csv"), U)


@needs_data
def test_the_default_funds_carry_the_issuers_mers():
    U = pd.read_pickle(universe.DATA_DIR / "universe.pkl").set_index("yahoo")
    M = pd.read_csv(universe.ISSUER_MER).set_index("yahoo")
    for t in DEFAULTS:
        assert U.at[t, "mer"] == M.at[t, "mer"], t
    assert U.at["VFV.TO", "mer"] == 0.0008 and U.at["VEE.TO", "mer"] == 0.0024


@needs_data
def test_the_team_layer_inception_follows_tmx():
    U = pd.read_pickle(universe.DATA_DIR / "universe.pkl").set_index("yahoo")
    assert U.at["ZLB.TO", "rk_inception"] == "2012-01-24" and U.at["CASH.TO", "rk_inception"] == "2021-11-03"
