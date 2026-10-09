"""The regulator's risk rating (v3 Track C2): NI 81-102 Appendix F, Items 1 and 2."""

from __future__ import annotations

import numpy as np
import pytest

from robokit.engine import Request, build_portfolio, ni81_102_rating, rating_check


def _series_with_sd(annual_sd: float, n: int = 120, seed: int = 0) -> np.ndarray:
    """Monthly returns whose sample standard deviation times sqrt(12) is exactly ``annual_sd``."""
    z = np.random.default_rng(seed).normal(size=n)
    z = (z - z.mean()) / z.std(ddof=1)
    return 0.005 + z * annual_sd / np.sqrt(12)


@pytest.mark.parametrize(
    "sd,label",
    [
        (0.0599, "Low"),
        (0.06, "Low to medium"),
        (0.1099, "Low to medium"),
        (0.11, "Medium"),
        (0.1599, "Medium"),
        (0.16, "Medium to high"),
        (0.1999, "Medium to high"),
        (0.20, "High"),
        (0.45, "High"),
    ],
)
def test_bands_follow_the_table(sd, label):
    # "0 to less than 6" Low; "6 to less than 11" Low to medium; "11 to less than 16" Medium;
    # "16 to less than 20" Medium to high; "20 or greater" High
    r = ni81_102_rating(_series_with_sd(sd + 1e-12))
    assert r["rating"] == label and r["months"] == 120


def test_formula_is_the_sample_sd_of_the_last_120_months_times_root_12():
    x = np.random.default_rng(4).normal(0.006, 0.04, size=200)
    want = np.std(x[-120:], ddof=1) * np.sqrt(12)
    assert ni81_102_rating(x)["std_10y"] == round(want, 4)


def test_a_short_history_says_how_many_months_it_used():
    r = ni81_102_rating(_series_with_sd(0.08, n=84))
    assert r["months"] == 84 and "84 months available" in rating_check(r)["en"]


def test_every_build_carries_the_rating_and_its_check():
    p = build_portfolio(Request(market="CA", risk_level=3, resample=False))
    r = p["stats"]["ni81_102"]
    assert r["months"] == 120 and r["rating"] in {"Low", "Low to medium", "Medium", "Medium to high", "High"}
    assert any(c["id"] == "regulator_rating" and r["rating"] in c["en"] for c in p["checks"])


@pytest.mark.parametrize("n,full", [(119, False), (120, True), (150, True)])
def test_the_rating_says_whether_it_has_the_ten_years_appendix_f_asks_for(n, full):
    r = ni81_102_rating(_series_with_sd(0.08, n=n))
    assert r["months"] == min(n, 120) and r["appendix_f"] is full
    assert ("months available" in rating_check(r)["en"]) is (not full)
