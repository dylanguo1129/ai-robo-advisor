"""Number and ticker provenance check for anything a language model writes.

Rule (docs/research/papers-robo-llm.md section G, must 1): every number in a
reply must come from a tool result of the same turn; every ticker must be in
the fund list. This module is the enforcement, not the prompt: the chat loop
calls ``check_reply`` on each answer and, if it fails, asks the model once to
rewrite using only tool numbers, then shows any remaining unsupported numbers
flagged to the user.

A reply number is accepted when it is a rounding of some number in the tool
results, either as written or as a percentage (0.064 -> "6.4%", "6%"), or in
thousands/millions ("25K", "1.2M"). Small counting numbers (0-12) and years
are allowed because they appear in ordinary sentences ("3 funds", "in 2022").
"""

from __future__ import annotations

import json
import math
import re

# Word boundaries are ASCII only: Python's \w also matches non-ASCII letters, so a Unicode
# boundary would silently skip a number or ticker written right against one.
NUM = re.compile(r"(?<![A-Za-z0-9_.])[-−+]?(\$)?\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?\s?(%|k|K|M|B|bn)?(?![A-Za-z0-9_])")
TICKER = re.compile(r"(?<![A-Za-z0-9])([A-Z]{2,5}(?:[.-][A-Z])?(?:\.(?:TO|NE))?)(?![A-Za-z0-9])")
# Capitalised words that are not tickers: account types, agencies, indexes, units and plain English.
COMMON_CAPS = {
    "ETF",
    "ETFS",
    "ETN",
    "ETNS",
    "MER",
    "AUM",
    "NAV",
    "USD",
    "CAD",
    "FX",
    "US",
    "USA",
    "UK",
    "EU",
    "TSX",
    "NYSE",
    "AI",
    "LLM",
    "TFSA",
    "RRSP",
    "RRIF",
    "FHSA",
    "RESP",
    "LIRA",
    "RDSP",
    "CPP",
    "QPP",
    "OAS",
    "GIS",
    "CRA",
    "IRA",
    "ROTH",
    "HSA",
    "IRS",
    "FDIC",
    "CDIC",
    "HISA",
    "GIC",
    "APR",
    "APY",
    "YTD",
    "CPI",
    "PCE",
    "GDP",
    "PMI",
    "EPS",
    "VIX",
    "REIT",
    "REITS",
    "TIPS",
    "OK",
    "FAQ",
    "DIY",
    "CEO",
    "CFO",
    "IPO",
    "ID",
    "EN",
    "PDF",
    "API",
    "MCP",
    "BL",
    "HRP",
    "CAPM",
    "CMA",
    "KYC",
    "ESG",
    "CSA",
    "CIRO",
    "OSC",
    "AMF",
    "SEC",
    "FINRA",
    "FCAC",
    "OBSI",
    "NFCC",
    "FP",
    "IFP",
    "EPU",
    "GPR",
    "GDELT",
    "FRED",
    "BOC",
    "FOMC",
    "FED",
    "ECB",
    "BOJ",
    "IMF",
    "OECD",
    "OPEC",
    "NATO",
    "WTO",
    "CUSMA",
    "USMCA",
    "NAFTA",
    "EV",
    "CDR",
    "BMO",
    "RBC",
    "TD",
    "CIBC",
    "EAFE",
    "MSCI",
    "FTSE",
    "SP",
    "S&P",
    "NOTE",
    "YES",
    "NO",
    "AND",
    "OR",
    "THE",
    "NOT",
    "IT",
    "AM",
    "PM",
    "I",
    "A",
}
# Numbers the rules tell the guide to give that no tool returns: the crisis line (call or text 988).
HELP_NUMBERS = [988.0]
ACCOUNT_NAMES = re.compile(r"\b(?:401|403|457)\s?\(?[kb]\)?", re.IGNORECASE)  # US retirement accounts


# A small count ("3 funds") passes without a source, unless it counts future events ("2 cuts next year").
EVENT_AFTER = re.compile(r"\s*(?:more\s+)?(?:times|cuts?|hikes?|rate\s+cuts?|basis\s+points|bps)", re.IGNORECASE)


def _collect_numbers(obj, out: list) -> None:
    """Numbers in tool results as (value, is_percent): a figure written with % in a string is a percent;
    a raw number is not, though a fraction (|x| <= 1.5) may be quoted as a percent (0.064 -> 6.4%)."""
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        if math.isfinite(obj):
            out.append((float(obj), False))
        return
    if isinstance(obj, str):
        for m in NUM.finditer(obj):
            v = _parse(m)
            if v is not None:
                out.append((v, m.group(4) == "%"))
        return
    if isinstance(obj, dict):
        for v in obj.values():
            _collect_numbers(v, out)
        return
    if isinstance(obj, (list, tuple)):
        for v in obj:
            _collect_numbers(v, out)


def _parse(m: re.Match) -> float | None:
    whole, frac, unit = m.group(2), m.group(3), m.group(4)
    try:
        v = float(whole.replace(",", "") + ("." + frac if frac else ""))
    except ValueError:
        return None
    if unit in ("k", "K"):
        v *= 1e3
    elif unit == "M":
        v *= 1e6
    elif unit in ("B", "bn"):
        v *= 1e9
    return v


def _decimals(m: re.Match) -> int:
    return len(m.group(3) or "")


def _supported(v: float, dec: int, is_pct: bool, unit: str | None, pool: list) -> bool:
    tol = 0.5 * 10 ** (-dec) + 1e-9
    for a, a_pct in pool:
        frac = (not a_pct) and abs(a) <= 1.5
        if is_pct:  # a percent matches a percent, or a fraction times 100
            cands = [a, abs(a)] if a_pct else ([a * 100, abs(a) * 100] if frac else [])
        else:  # a plain figure matches a plain figure, or a fraction quoted without the % sign ("6.4 percent")
            cands = [a, abs(a)] + ([a * 100, abs(a) * 100] if frac else [])
        if a_pct and not is_pct:
            cands = []
        if unit in ("k", "K"):
            t = 0.5 * 10 ** (-dec) * 1e3 + 1e-9
            if any(abs(v - c) <= t for c in (a, abs(a))):
                return True
        if unit in ("M", "B", "bn"):
            mult = 1e6 if unit == "M" else 1e9
            t = 0.5 * 10 ** (-dec) * mult + 1e-9
            if any(abs(v - c) <= t for c in (a, abs(a))):
                return True
        if any(abs(v - c) <= tol for c in cands):
            return True
        # money rounded to the nearest 10/100 in prose ("about $8,300")
        if not is_pct and not a_pct and v >= 1000 and dec == 0 and abs(v - abs(a)) <= max(0.005 * abs(a), 50):
            return True
    return False


def check_reply(text: str, tool_results: list, universe_tickers: set[str] | None = None, extra_allowed: list[float] | None = None) -> dict:
    """Return {ok, unsupported_numbers, unknown_tickers}. ``tool_results`` is anything JSON-like."""
    text = ACCOUNT_NAMES.sub(lambda m: " " * len(m.group(0)), text or "")  # "401(k)" is an account name, not a figure
    pool: list = []
    _collect_numbers(tool_results, pool)
    pool += [(float(x), False) for x in list(extra_allowed or []) + HELP_NUMBERS]
    bad = []
    for m in NUM.finditer(text or ""):
        v = _parse(m)
        if v is None:
            continue
        unit = m.group(4)
        dec = _decimals(m)
        plain = unit is None and dec == 0 and not m.group(1) and "," not in m.group(2)
        counts_events = bool(EVENT_AFTER.match(text, m.end()))
        if plain and ((v <= 12 and not counts_events) or 1900 <= v <= 2100):
            continue  # counts and years (a "$" or a thousands comma means money, not a year)
        if not _supported(v, dec, unit == "%", unit, pool):
            bad.append(m.group(0).strip())
    unknown = []
    if universe_tickers is not None:
        tool_text = json.dumps(tool_results, default=str)
        for m in TICKER.finditer(text or ""):
            t = m.group(1)
            if t in COMMON_CAPS or len(t) < 2:
                continue
            if t in universe_tickers or t + ".TO" in universe_tickers or t in tool_text:
                continue
            unknown.append(t)
    return {"ok": not bad and not unknown, "unsupported_numbers": sorted(set(bad)), "unknown_tickers": sorted(set(unknown))}


REWRITE_INSTRUCTION = (
    "Your reply contained numbers or tickers that are not in this turn's tool results: {items}. "
    "Rewrite the reply using only numbers and tickers that appear in the tool results, or call a tool to get them. "
    "If the data is not available, say so plainly."
)
