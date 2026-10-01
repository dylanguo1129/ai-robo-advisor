"""Paths and constants shared across Robo-Kit."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("ROBOKIT_DATA_DIR", ROOT / "data" / "v2"))
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = ROOT / "output" / "v2"

USER_AGENT = "Mozilla/5.0 (compatible; robokit/2.2; +https://github.com/dylanguo1129/ai-robo-advisor)"

# Markets the product supports. "CA" = everything you can buy in Canadian dollars
# on a Canadian exchange; "US" = every US-listed ETF, in US dollars.
MARKETS = ("CA", "US")

# Eligibility defaults for the optimizer universe. They are defaults, not rules:
# universe.py applies them and records a reason for every fund it leaves out.
MIN_HISTORY_MONTHS = 36
MIN_AUM = {"CA": 20e6, "US": 50e6}  # in the fund's trading currency
MIN_DOLLAR_VOLUME = {"CA": 50e3, "US": 250e3}  # average daily traded value

RISK_FREE = {"CA": 0.0225, "US": 0.0375}  # annual, used for Sharpe ratios; see docs/METHOD.md
DELTA = 2.5  # market risk aversion for the equilibrium prior (docs/METHOD.md section 2)


def ensure_dirs() -> None:
    for p in (DATA_DIR, RAW_DIR, OUTPUT_DIR):
        p.mkdir(parents=True, exist_ok=True)
